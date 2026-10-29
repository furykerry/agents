---
title: SandboxUpdateOps InstallerUpdate Strategy
authors:
  - "@TBD"
creation-date: 2026-10-23
last-updated: 2026-10-29
status: provisional
see-also:
  - "/docs/proposals/20251218-sandbox-inplace-update.md"
  - "/docs/proposals/20260616-create-suo-command.md"
  - "/docs/proposals/20260915-checkpoint-api-extension.md"
  - "/docs/proposals/20260506-sandbox-commit.md"
---

# SandboxUpdateOps InstallerUpdate Strategy

## Table of Contents

- [Glossary](#glossary)
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals/Future Work](#non-goalsfuture-work)
- [Background](#background)
  - [How agent harnesses upgrade themselves](#how-agent-harnesses-upgrade-themselves)
  - [Install-location overrides](#install-location-overrides)
  - [Air-gapped and mirrored environments](#air-gapped-and-mirrored-environments)
  - [Example installer image: Hermes Agent](#example-installer-image-hermes-agent)
- [Proposal](#proposal)
  - [Overview](#overview)
  - [API Changes](#api-changes)
  - [Installer Contract](#installer-contract)
  - [SandboxUpdateOps Controller Changes](#sandboxupdateops-controller-changes)
  - [Sandbox Controller Changes](#sandbox-controller-changes)
  - [Validation](#validation)
  - [Durability of the Result](#durability-of-the-result)
  - [Implementation Details/Notes/Constraints](#implementation-detailsnotesconstraints)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Alternatives](#alternatives)
- [Upgrade Strategy](#upgrade-strategy)
- [Additional Details](#additional-details)
  - [Test Plan](#test-plan)
- [Implementation History](#implementation-history)
- [References](#references)

## Glossary

| Term | Meaning |
|---|---|
| SUO | `SandboxUpdateOps`, the batch sandbox update operation CR. |
| Harness | The agent runtime software installed inside a sandbox image (OpenClaw, Claude Code, Codex CLI, Gemini CLI, Hermes Agent, ...). |
| Installer | A customer-supplied OCI image plus command that materialises new harness content into a running sandbox. |
| Installer container | The Kubernetes ephemeral container created from the installer image. |
| Target container | The sandbox container whose filesystem the installer writes into. |
| Writable layer | The container's overlayfs upper directory — everything written to the container rootfs after it started. |
| Namespace targeting | `EphemeralContainer.targetContainerName`, which runs an ephemeral container in another container's PID and IPC namespaces. |

## Summary

This proposal adds a third `SandboxUpdateOps` update strategy, `InstallerUpdate`,
that upgrades the software inside a running sandbox **without replacing its Pod and
without touching its container image**.

Instead of deleting and recreating the Pod (`Recreate`) or checkpointing and
restoring it (`CheckpointRestore`), `InstallerUpdate` injects a Kubernetes
**ephemeral container** built from a customer-supplied installer image into the
sandbox's existing Pod. The ephemeral container uses
`targetContainerName` to join the target sandbox container's PID namespace, which
makes the target's root filesystem reachable at `/proc/1/root`. The installer
command then copies or unpacks the new harness content into that filesystem.

Because the Pod is never replaced and the target container is never restarted, the
container's writable layer survives the upgrade in full: installed packages,
generated artefacts, agent session state, caches and worktrees all persist.

The new content is carried by the **installer image**, not by a new sandbox image.
`spec.patch` is explicitly forbidden from changing any container image under this
strategy, mirroring the existing `CheckpointRestore` restriction.

## Motivation

### The gap

A claimed sandbox is a long-lived, stateful working environment. Two upgrade
strategies exist today, and neither fits a routine harness version bump:

- **`Recreate`** deletes the Pod and creates a new one from the patched template
  (`pkg/controller/sandbox/core/upgrade_control.go:387`). The new container starts
  with an **empty writable layer**. Everything the agent accumulated is lost.

- **`CheckpointRestore`** checkpoints the filesystem, recreates the Pod, and
  restores from the checkpoint. It preserves the writable layer only for
  containers **whose image is unchanged** — the SUO validating webhook rejects any
  image modification under this strategy
  (`pkg/webhook/sandboxupdateops/validating/sandboxupdateops_validate.go:101`). It
  also depends on a checkpoint backend being available and on the Pod being
  recreatable at all, which costs a full restart of every process in the sandbox.

What an operator usually wants when bumping a harness from `1.3.0` to `1.4.0`
across a fleet of active sandboxes is much less invasive:

1. Keep the Pod running.
2. Keep the writable layer.
3. Replace the harness files.
4. Restart the harness process.

Steps 3 and 4 are exactly what the harness's own updater does when a developer
runs it on a laptop. There is currently no way to express that as a batch
operation.

### Why an injected container rather than an exec hook

`Sandbox.spec.lifecycle.preUpgrade` / `postUpgrade` already execute a command
inside the sandbox container via envd
(`pkg/controller/sandbox/core/lifecycle_handler.go:44`). That is sufficient for
step 4 but not for step 3, for three reasons:

- **No payload carrier.** An exec hook can only use files already present in the
  sandbox image, or download them over the network. A hermetic, versioned,
  pre-approved payload has nowhere to come from.
- **No toolchain.** Minimal sandbox images frequently lack the package manager,
  archive tools, or disk space the harness updater needs.
- **No isolation.** The update runs as a child of the sandbox's own runtime,
  competing with the workload and sharing its failure domain.

An ephemeral container solves all three: it brings its own rootfs (the payload and
the tooling), runs as a separate container, and — uniquely — **can be added to an
already-running Pod**. Kubernetes offers no other mechanism for that. In-place Pod
vertical scaling changes resources only; adding a regular container or a sidecar
always requires Pod replacement.

### Survey finding that shapes the design

Every mainstream harness updater is a **file-level replacement into a global
install prefix followed by a process restart** — see
[How agent harnesses upgrade themselves](#how-agent-harnesses-upgrade-themselves).
Their `update` entry points resolve their own install location from the running
process and cannot be aimed at another container's rootfs, but their `install`
entry points and the package managers underneath all accept an explicit prefix,
which *can* be aimed through `/proc/1/root`. OpenClaw goes further and *refuses* to
self-update when it detects a container-managed installation.

This is why the payload must live in the installer image and why the installer
command is customer-supplied: the controller cannot know how any given harness
wants to be installed, but the customer does, and can package exactly that
knowledge — the right package manager, a matching libc, and the vendor's own
prefix-aware installer — into an image.

### Goals

- Add `InstallerUpdate` as a `SandboxUpdateOpsStrategyType` and as a
  `SandboxUpgradePolicyType`.
- Let the operator specify an installer image, an optional installer command, and
  an optional target container name.
- Preserve the target container's writable layer across the upgrade.
- Work in clusters whose sandboxes have no outbound internet access, by carrying
  the payload in the installer image instead of fetching it at upgrade time — see
  [Air-gapped and mirrored environments](#air-gapped-and-mirrored-environments).
- Leave the sandbox container image in `spec.template` unchanged.
- Reuse the existing SUO batching, `maxUnavailable` budget, `paused` gating,
  state filter, tracking labels, fail-stop semantics and finalizer cleanup.
- Reuse the existing `preUpgrade` / `postUpgrade` lifecycle hooks around the
  install step, so harness restart and version verification need no new API.
- Support upgrading `Paused` sandboxes through the existing two-phase
  resume-then-upgrade path.
- Make the outcome observable through the existing `Upgrading` condition, SUO
  status counters and Kubernetes events.

### Non-Goals/Future Work

- **Changing the sandbox container image.** Under `InstallerUpdate` the image in
  `spec.template` is immutable and the running Pod's `spec.containers[].image`
  never changes. Producing a durable image that bakes in the installed content is
  the job of the `Commit` CR (see [Durability](#durability-of-the-result)).
- **Defining the installer's behaviour.** What is copied, where, and how the
  harness is restarted is entirely the customer's responsibility.
- **Making the installed content survive Pod replacement.** The result lives in
  the writable layer and is lost when the Pod is recreated. Documented, not
  solved.
- **Adding Prometheus metrics.** None are introduced by this proposal.
- **Rollback.** There is no automated rollback of a partially applied install.
- **Applying to SandboxSet pool members.** SUO already excludes
  SandboxSet-controlled sandboxes; that exclusion is unchanged.
- **Running an installer with no version change at all.** `spec.patch` may still
  carry non-image changes, but the installer is always the unit of work.

## Background

### How agent harnesses upgrade themselves

Five mainstream harnesses were surveyed — OpenClaw, Claude Code, Codex CLI, Gemini
CLI and Hermes Agent. Three conclusions shape this proposal; the evidence for each
is in the section named after it.

1. **Upgrading is a filesystem mutation, not an image rebuild.** Every harness
   replaces files under an install prefix — `/usr/local/lib/node_modules`,
   `~/.local/bin`, `~/.hermes`, `/opt/hermes`, `/opt/homebrew` — and then expects
   the long-running process to be restarted. OpenClaw exposes `--no-restart`
   precisely to separate the two steps. That maps directly onto the split this
   design makes: the installer container performs the file mutation, and the
   existing `postUpgrade` hook performs the restart through envd, with no
   additional privileges.
2. **The install location can be overridden** — see
   [Install-location overrides](#install-location-overrides). Every harness
   surveyed except Claude Code's native binary installs through a mechanism that
   accepts an explicit prefix, and the exception is a single static file. This is
   what lets the installer run **its own** tooling with its output redirected into
   the target rootfs, reusing the vendor's install logic instead of reimplementing
   it as `cp -a`.
3. **Air-gapped support is weak, but version pinning is universal** — see
   [Air-gapped and mirrored environments](#air-gapped-and-mirrored-environments).
   No harness surveyed can install with zero network access, and a site mirror
   helps only if it is reachable from the sandbox at upgrade time. All of them can
   install an exact version. Carrying a pinned payload in the installer image
   therefore solves the problem the harnesses themselves do not.

One further finding is why the payload cannot simply be the harness's own `update`
command run from inside the sandbox: **container-managed installs are often refused
outright.** OpenClaw skips the update when it detects no install owner, and Hermes
Agent's container installs do not support `hermes update` at all — the image must be
rebuilt. Two independent harnesses converging on the same refusal is the strongest
evidence for this proposal's premise: self-update cannot be depended on, so the
operator must be able to supply the install step, which is what `installer.image`
and `installer.command` are for.

The corollary is that the harness `update` entry points are not usable from the
installer container either. They resolve their own install location from the running
process, so they cannot be aimed at another container's rootfs; their `install`
entry points and the package managers underneath can. See
[Run your own tooling, never the target's](#run-your-own-tooling-never-the-targets).

### Install-location overrides

The detail behind conclusion 2 above. Where a harness accepts an explicit install
prefix, the installer container can run **its own** tooling with its output
redirected into the target's filesystem — reusing the vendor's install logic instead
of reimplementing it as a `cp -a`.

| Harness | Install-location override | Notes |
|---|---|---|
| **OpenClaw** | **First-class.** `install-cli.sh --prefix <path>` (default `~/.openclaw`); env `OPENCLAW_PREFIX`, `OPENCLAW_HOME`. `openclaw update` honours `NPM_CONFIG_PREFIX`, documented as `NPM_CONFIG_PREFIX="$(npm prefix -g)" openclaw update`. | The local-prefix installer is a *fresh install* path, so it sidesteps the `update` owner check that skips container-managed installs. Non-interactive: `--no-prompt`, `--no-onboard`, `--json`, `OPENCLAW_NO_PROMPT=1`. |
| **Hermes Agent** | **First-class, and the cleanest case.** Install-location flags `--dir`, `-InstallDir`, `-HermesHome`; env `HERMES_HOME`. Defaults: `~/.hermes` (Linux/macOS), `%LOCALAPPDATA%\hermes` (Windows), `/opt/hermes` (container), `$PREFIX/lib/hermes` (Termux). | Distributed by installer script, git, or APT — **not** npm or pip. The Python environment is managed by `uv`, which changes the relocatability analysis; see below. The whole install is a **self-contained directory**, so redirecting it does not interleave with the target's shared `/usr/local` the way an npm global prefix does. |
| **Claude Code** | **Partial.** `claude install [version]` — the argument is a *version*, not a path; the native installer targets `~/.local/bin` with no location override. The npm path honours `NPM_CONFIG_PREFIX`. | The config directory is overridable by env var, the install directory is not. For the native binary, write the downloaded artefact straight into the target's `~/.local/bin`. |
| **Codex CLI** | **Indirect.** `codex upgrade` delegates to `npm install -g @openai/codex@…` or `brew upgrade codex`; `NPM_CONFIG_PREFIX` covers the npm path. | Homebrew has no relocatable prefix, so a brew-managed target is not reachable this way. |
| **Gemini CLI** | **Indirect.** `gemini update` runs `npm install -g @google/gemini-cli@latest`; `NPM_CONFIG_PREFIX` applies. | Same Homebrew caveat. |

The npm mechanism was verified empirically rather than assumed. `NPM_CONFIG_PREFIX`,
`PREFIX` and `--prefix` all redirect a global install, and the resulting layout is
`<prefix>/lib/node_modules/<pkg>` with `<prefix>/bin/<name>`:

```
$ NPM_CONFIG_PREFIX=/tmp/a npm root -g
/tmp/a/lib/node_modules
$ NPM_CONFIG_PREFIX=$PREFIX_DIR npm install -g ./faketool-1.2.3.tgz
<prefix>/bin/faketool -> ../lib/node_modules/faketool/cli.js
<prefix>/lib/node_modules/faketool/{cli.js,package.json}
```

Two properties of that output are what make the redirect safe:

- The `bin` entry is a **relative** symlink (`../lib/node_modules/…`), so the tree
  is relocatable and resolves correctly when read from inside the target as
  `/usr/local/bin/…` even though it was written through `/proc/1/root/usr/local`.
- The shebang is `#!/usr/bin/env node`, resolved at **runtime** from PATH. So npm
  executes in the installer's mount namespace while the artefact it produces
  executes against the *target's* interpreter. Verified by running the installed
  `bin` on PATH.

#### Relocatability is the real constraint

Those two properties are not universal, and assuming they are produces a second
silent-failure mode distinct from the `execve` trap. A toolchain that bakes
**absolute paths** into its output at install time will write paths beginning
`/proc/1/root/…` — a prefix that does not exist inside the target container. The
install reports success, the files are all present, and every entry point is
broken.

Hermes Agent is the case that exposes this, because it manages its Python
environment with `uv`. Console scripts in `.venv/bin` get absolute shebangs and
`pyvenv.cfg` records an absolute home path (astral-sh/uv#13350). `uv` provides
`uv venv --relocatable` (env `UV_VENV_RELOCATABLE`), which rewrites both to
relative paths, but it is **not** the stable default — relocatable-by-default
ships only as a uv *preview* feature (astral-sh/uv#17770). It must be requested
explicitly.

Toolchains therefore fall into three classes, and the installer image must know
which class its harness is in:

| Class | Toolchain | What the installer must do |
|---|---|---|
| **Path-relative by construction** | npm / pnpm / bun global installs; a statically linked native binary written with `install(1)` | Nothing beyond redirecting the prefix. |
| **Relocatable only on request** | `uv` and `virtualenv` Python environments; anything writing `pyvenv.cfg`, absolute shebangs, or ELF `RPATH` | Pass the relocatable flag (`uv venv --relocatable`, `virtualenv --relocatable`) and verify no absolute `/proc/1/root` path survived. |
| **Not relocatable** | Homebrew (no relocatable prefix); installers that hardcode their own location | Cannot be installed through the prefix. Either install into a self-contained directory the harness locates by env var (`HERMES_HOME`, `OPENCLAW_HOME`), or fall back to `postUpgrade`. |

The escape hatch for the third class is why the `*_HOME` variables matter more
than the prefixes: a harness that finds itself via `HERMES_HOME` or
`OPENCLAW_HOME` can be installed to *any* directory and then pointed at from
inside the target, sidestepping absolute-path baking entirely.

A cheap post-write assertion catches all three classes at once and belongs in the
installer contract:

```sh
if grep -rq "$SANDBOX_INSTALLER_TARGET_ROOT" "$target" 2>/dev/null; then
  echo "install baked an absolute /proc/1/root path" >&2; exit 126
fi
```

Exit code 126 is reserved for this, mirroring the 125 reserved for failed
namespace targeting.

Consequences for the contract:

1. **Never query the prefix from inside the installer.** `npm prefix -g` there
   returns the *installer's* prefix. It must be constructed as
   `$SANDBOX_INSTALLER_TARGET_ROOT` + the target's known prefix, or read from the
   target's own npmrc through the prefix path.
2. **Match the libc family.** npm runs lifecycle scripts in the *invoking*
   environment, so a `node-gyp` native build compiles against the installer
   image's headers and libc and is then loaded by the target's interpreter. Two
   glibc-based images are fine; an Alpine/musl installer writing into a glibc
   target produces an unusable binary. The installer image's base must match the
   target's.
3. **"Home" is the target's, not the installer's.** Claude Code's `~/.local/bin`
   and OpenClaw's default `~/.openclaw` mean `/proc/1/root/root` or
   `/proc/1/root/home/<user>`. The installer must not use its own `$HOME`.
4. **Prefer the offline form.** `npm install -g <tarball>` against a payload baked
   into the installer image avoids depending on registry reachability from the
   sandbox network namespace, and keeps the installed version pinned and
   reviewable — which is the reason to carry the payload in an image at all.
5. **Prefer a self-contained directory over a shared system prefix.** Installing
   into `$SANDBOX_INSTALLER_TARGET_ROOT/opt/<harness>` and pointing the harness at
   it with its `*_HOME` variable is strictly safer than writing into
   `/usr/local/lib/node_modules`, which is shared with the target's own packages:
   it cannot clobber an unrelated dependency, it is trivially removable on
   rollback, and it makes the relocatability class obvious. Hermes Agent's
   `/opt/hermes` layout and OpenClaw's `install-cli.sh --prefix` both support
   this directly.

### Air-gapped and mirrored environments

Much of the target deployment for this feature is a cluster where sandboxes have
no outbound internet access. That raises two separate questions: can the
harness's installer be pointed at an internal **site mirror**, and can a
**specific version** be pinned? The answers differ sharply, and no harness in the
survey answers "yes, fully offline" to both.

| Harness | Site mirror | Version pinning | True air-gap (no network at all) |
|---|---|---|---|
| **OpenClaw** | **Yes, explicit.** `OPENCLAW_INSTALL_NPM_REGISTRY` "replaces `https://registry.npmjs.org`"; `OPENCLAW_INSTALL_BUN_PIN_URL` and `OPENCLAW_INSTALL_BUN_RELEASE_BASE_URL` redirect the Bun fork runtime. The npm/pnpm/bun path also honours `NPM_CONFIG_REGISTRY`. | **Yes.** `--version <version\|dist-tag\|spec>` (default `latest`), `OPENCLAW_VERSION`, `--tag`; git installs accept a 40-character commit SHA. Sealed releases verify a published Bun pin hash and fail on mismatch. | **No.** The installer scripts "do not support fully offline installation"; pins, archives and metadata require network. Source installs require network unless a local pnpm lockfile is used. |
| **Claude Code** | **No mirror for the native installer** — `curl -fsSL https://claude.ai/install.sh \| bash` is a fixed URL. The npm path inherits `NPM_CONFIG_REGISTRY`. | **Yes.** `claude install [version]`; channel via `autoUpdatesChannel`; npm `@<version>`. | **No.** anthropics/claude-code#39847 requested an offline installer and was closed unimplemented; it also notes that authentication is required even in offline settings. |
| **Codex CLI** | No harness-level mirror; inherits npm's. The Homebrew path can use `HOMEBREW_BOTTLE_DOMAIN` / `HOMEBREW_API_DOMAIN`. | **Yes.** `npm install -g @openai/codex@<version>`. | No documented support and no tracked request. |
| **Gemini CLI** | No harness-level mirror; inherits npm's. | **Yes.** `npm install -g @google/gemini-cli@<version>`. | No documented support and no tracked request. |
| **Hermes Agent** | Not at harness level. Its `uv`-managed Python environment inherits `UV_INDEX_URL`, `UV_EXTRA_INDEX_URL`, `UV_NO_INDEX`, `UV_FIND_LINKS`, `UV_OFFLINE`, `UV_CACHE_DIR`, `UV_PYTHON_INSTALL_DIR` and `UV_PYTHON_DOWNLOADS`. | Via `uv.lock` or `--exact`, or a git SHA for source installs. | **No.** NousResearch/hermes-agent#17696 is **open**: "Hermes Agent cannot be deployed in offline or air-gapped environments … installation cannot be completed at all." The FAQ's affirmative "can I use it offline" answer concerns *runtime* model endpoints (`hermes model` → Custom endpoint), not installation. |

Two conclusions follow, and both shape this proposal.

**A mirror is a weaker guarantee than a baked payload.** Pointing an installer at
an internal registry still requires that registry to be reachable *from the
sandbox's network namespace at upgrade time*. An ephemeral container joins the
Pod's network namespace, so the installer's egress is exactly the sandbox's
egress — in a genuinely air-gapped cluster there is none, and the mirror is
unreachable too.

**Image distribution already has an air-gapped path; in-sandbox package
installation does not.** A node pulls images through the cluster's registry mirror
or from a pre-warmed cache, configured once by the platform and entirely outside
the sandbox's network. Carrying the payload in the installer image therefore
converts an unsolved problem into a solved one: the new harness content arrives
with the image, and no egress from the sandbox is needed at all. This is the
strongest single argument for the design, and it is why the offline form is
preferred in [Install-location overrides](#install-location-overrides) even where
a working mirror exists.

For the npm-distributed harnesses a fully local install is achievable and should
be the default recommendation: bake `npm pack` tarballs into the installer image
and install with `--offline`. Both mechanisms were verified empirically —
`NPM_CONFIG_REGISTRY` overrides the registry, and `--offline` puts npm in
`only-if-cached` mode so it fails with `ENOTCACHED` rather than reaching the
network:

```
$ NPM_CONFIG_REGISTRY=https://nexus.internal/repository/npm/ npm config get registry
https://nexus.internal/repository/npm/

$ npm install --offline --dry-run <uncached-pkg>
npm error code ENOTCACHED
npm error request to https://registry.npmjs.org/<pkg> failed:
npm error cache mode is 'only-if-cached' but no cached response is available.
```

`--offline` requires a populated npm cache (`npm config get cache`, itself
overridable); a tarball install requires none, which is why the tarball form is
preferred. For `uv`-managed harnesses the equivalent is `UV_NO_INDEX` with
`UV_FIND_LINKS` pointing at a local wheelhouse, plus `UV_PYTHON_INSTALL_DIR`
pre-populated if the interpreter must also come from the image.

**Version pinning is universal and should be treated as mandatory.** Every harness
surveyed can install an exact version. An installer image that resolves `latest`
at upgrade time defeats the purpose of carrying a payload in an image: the
installed version would vary with the calendar rather than with the image tag, and
the `postUpgrade` version assertion would have nothing stable to assert against.
Operators should pin explicitly, and the installer image tag should be the record
of what was pinned.

### Example installer image: Hermes Agent

Hermes Agent is the hardest case in the survey and therefore the most instructive
example: it is not distributed through npm or pip, its Python environment is managed
by `uv` (so it falls in the *relocatable only on request* class), its container
installs refuse `hermes update`, and its air-gap support is an open issue. It is
also the cleanest install-location story — `HERMES_HOME` plus `--dir`, and a
self-contained directory rather than a shared system prefix.

This is what an operator's installer image looks like for it. The image is the
payload carrier: everything needed is baked in, so the install requires no egress
from the sandbox.

```dockerfile
# syntax=docker/dockerfile:1
# Base must match the target's libc family. Hermes Agent's venv and any native
# wheels are built against glibc; a musl base would produce unusable binaries.
FROM python:3.12-slim-bookworm

ARG HERMES_VERSION=1.9.2

COPY --from=ghcr.io/astral-sh/uv:0.9.11 /uv /uvx /usr/local/bin/

# A pinned source tree, a local wheelhouse and a pre-downloaded interpreter — all
# baked in, so nothing is fetched at upgrade time.
COPY payload/hermes-src/       /payload/hermes-src/
COPY payload/wheelhouse/       /payload/wheelhouse/
COPY payload/python/           /payload/python/

ENV HERMES_VERSION=${HERMES_VERSION}
COPY install.sh /install.sh
ENTRYPOINT ["/install.sh"]
```

The vendor's own `install-hermes.sh` is deliberately *not* used here: it fetches
over the network, which is exactly what an air-gapped cluster cannot do (see
[Air-gapped and mirrored environments](#air-gapped-and-mirrored-environments)). The
script below reproduces what it does — unpack a pinned tree, build the `uv`
environment, place it under `HERMES_HOME` — from a payload the image already
carries. Where a mirror *is* reachable, baking the vendor script in and calling it
with `--dir "$SANDBOX_INSTALLER_TARGET_ROOT/opt/hermes"` is the shorter form.

```sh
#!/bin/sh
set -eu

version="${HERMES_VERSION:?HERMES_VERSION must be pinned in the image}"
root="${SANDBOX_INSTALLER_TARGET_ROOT:?}"

# Reserved exit 125: prove namespace targeting took effect before writing anything.
# Without it an unsupporting runtime yields a silent no-op that reports success.
[ /proc/1/root -ef / ] && { echo "namespace targeting unavailable" >&2; exit 125; }

# Build entirely in the installer's own filesystem. Nothing here executes a binary
# from under $root -- that is the execve trap, and it would silently install into
# the ephemeral container instead of the sandbox.
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/hermes"
cp -a /payload/hermes-src/. "$work/hermes/"

# Offline uv: no index, local wheelhouse only, interpreter from the image.
export UV_NO_INDEX=1
export UV_FIND_LINKS=/payload/wheelhouse
export UV_OFFLINE=1
export UV_CACHE_DIR="$work/.uv-cache"
export UV_PYTHON_INSTALL_DIR=/payload/python
export UV_PYTHON_DOWNLOADS=never

# Relocatable is NOT uv's stable default. Without it, console scripts in .venv/bin
# get absolute shebangs and pyvenv.cfg records an absolute home -- both prefixed
# /proc/1/root, which does not exist inside the target.
export UV_VENV_RELOCATABLE=1
uv venv --relocatable "$work/hermes/.venv"
uv pip install --python "$work/hermes/.venv/bin/python" \
  -r "$work/hermes/requirements.txt"

# Stage into a versioned directory beside the live one. Writing over a running
# binary fails with ETXTBSY, and a half-copied tree leaves the harness unusable.
mkdir -p "$root/opt"
release="$root/opt/hermes-$version"
rm -rf "$release"
mkdir -p "$release"
cp -a "$work/hermes/." "$release/"
printf '%s\n' "$version" > "$release/INSTALLER_VERSION"

# Switch atomically: rename(2) over the symlink. The running process keeps its old
# inode until postUpgrade restarts it.
ln -s "hermes-$version" "$root/opt/.hermes-current.new"
mv -f "$root/opt/.hermes-current.new" "$root/opt/hermes-current"

# Reserved exit 126: assert no absolute /proc/1/root path was baked into the result.
if grep -rq "$root" "$release" 2>/dev/null; then
  echo "install baked an absolute $root path" >&2
  exit 126
fi
```

The matching `postUpgrade` hook runs inside the sandbox through envd, where
`/opt/hermes-current` is a real path and the harness's own interpreter and service
manager are available — no capability needed:

```yaml
lifecycle:
  postUpgrade:
    exec:
      command:
        - /bin/sh
        - -c
        - |
          set -eu
          export HERMES_HOME=/opt/hermes-current
          [ "$(cat "$HERMES_HOME/INSTALLER_VERSION")" = "1.9.2" ]
          "$HERMES_HOME/.venv/bin/hermes" --version | grep -F 1.9.2
          "$HERMES_HOME/.venv/bin/hermes" gateway restart
    timeoutSeconds: 120
```

What this example demonstrates, and what generalises to any harness:

- **Self-contained directory over shared prefix.** `/opt/hermes-<version>` plus a
  `hermes-current` symlink cannot clobber an unrelated dependency of the target, is
  trivially removable, and makes the relocatability class obvious. `HERMES_HOME` is
  how the harness finds itself, so the target needs no path baked into it.
- **Payload in the image, version pinned at build time.** `HERMES_VERSION` is an
  image build arg, so the image tag *is* the record of what was installed, and the
  `postUpgrade` assertion has something stable to assert against.
- **Both reserved exit codes earned their place.** 125 catches the runtime that
  does not implement targeting; 126 catches the `uv` default that would have
  shipped a broken install reported as success.
- **Nothing is executed from under the target rootfs.** `uv`, `cp`, `ln` and `mv`
  all come from the installer image.
- **Restart and verification are `postUpgrade`'s job**, not the installer's.
- For an npm-distributed harness the same shape applies with `NPM_CONFIG_PREFIX`
  and a `npm pack` tarball in place of `uv` and the wheelhouse — see
  [Run your own tooling, never the target's](#run-your-own-tooling-never-the-targets).

## Proposal

### Overview

```
SandboxUpdateOps                       Sandbox controller                kubelet / runtime
 (spec.updateStrategy.type:               (pkg/controller/sandbox)
  InstallerUpdate)
        |
        | 1. select claimed Sandboxes (unchanged: skips SandboxSet pool members,
        |    honours stateFilter, maxUnavailable, spec.paused)
        |
        | 2. patch Sandbox:
        |      spec.upgradePolicy.type         = InstallerUpdate
        |      spec.upgradePolicy.patchVersion = <ops UID>
        |      spec.upgradePolicy.installer    = <copied from ops>
        |      spec.lifecycle                  = ops.spec.lifecycle
        |      labels[agents.kruise.io/update-ops] = <ops name>
        |    (spec.template is NOT modified)
        v
   Sandbox CR ------------------------------------------------------->
                                     3. trigger: patchVersion != status.completedPatchVersion
                                        -> phase = Upgrading
                                        -> Upgrading condition removed
                                     4. PreUpgrade hook (envd, inside sandbox)
                                     5. verify target container Running
                                     6. POST pods/<name>/ephemeralcontainers
                                          name: installer-<hash8>-<attempt>
                                          image/command/env/securityContext from spec
                                          targetContainerName: <resolved>
                                                                    |
                                                                    | 7. pull image, create
                                                                    |    container in target's
                                                                    |    PID+IPC namespaces
                                                                    |
                                                                    | 8. installer writes into
                                                                    |    /proc/1/root/...
                                                                    |
                                     9. poll pod.status                |
                                        .ephemeralContainerStatuses <----- terminated, exit 0
                                     10. status.completedPatchVersion = patchVersion
                                     11. PostUpgrade hook (envd) — restart harness,
                                         assert new version
                                     12. Upgrading = True/Succeeded, phase = Running
        <-----------------------------------------------------------------
        | 13. count sandbox as updated; clear spec.upgradePolicy
        | 14. when all selected sandboxes are terminal -> phase Completed
```

The Pod is never deleted, the target container is never restarted by Kubernetes,
and `spec.template` is never modified. The only mutations to the Pod are the
appended ephemeral container and its status.

### API Changes

#### `SandboxUpdateOpsStrategyType`

`api/v1alpha1/sandboxupdateops_types.go:73-91` gains a third value:

```go
const (
	SandboxUpdateOpsStrategyRecreate SandboxUpdateOpsStrategyType = "Recreate"

	SandboxUpdateOpsStrategyCheckpointRestore SandboxUpdateOpsStrategyType = "CheckpointRestore"

	// SandboxUpdateOpsStrategyInstallerUpdate means sandboxes will be updated by
	// injecting an ephemeral installer container into the running Pod. The installer
	// writes new content into the target container's filesystem through
	// /proc/1/root, so the Pod is not replaced and the target container's writable
	// layer is preserved. Container images in spec.patch must not be modified.
	SandboxUpdateOpsStrategyInstallerUpdate SandboxUpdateOpsStrategyType = "InstallerUpdate"
)
```

The `+kubebuilder:validation:Enum` marker on
`SandboxUpdateOpsStrategy.Type` becomes `Enum=Recreate;CheckpointRestore;InstallerUpdate`.

#### `SandboxUpdateOpsStrategy.Installer`

```go
type SandboxUpdateOpsStrategy struct {
	// Type specifies the update strategy type.
	// When empty, defaults to Recreate.
	// Supported values: Recreate, CheckpointRestore, InstallerUpdate.
	// +kubebuilder:validation:Enum=Recreate;CheckpointRestore;InstallerUpdate
	// +optional
	Type SandboxUpdateOpsStrategyType `json:"type,omitempty"`

	// MaxUnavailable is the maximum number of sandboxes that can be upgrading at the same time.
	// +optional
	MaxUnavailable *intstr.IntOrString `json:"maxUnavailable,omitempty"`

	// Installer configures the ephemeral container injected into each selected
	// sandbox. Required when Type is InstallerUpdate, forbidden otherwise.
	// +optional
	Installer *InstallerSpec `json:"installer,omitempty"`
}

// InstallerSpec describes the ephemeral container that carries and applies the update.
type InstallerSpec struct {
	// Image is the installer image. It is the carrier of the update payload and of
	// whatever tooling the Command needs.
	// +kubebuilder:validation:Required
	// +kubebuilder:validation:MinLength=1
	Image string `json:"image"`

	// Command is the installer entrypoint, argv-style. When empty the image's
	// ENTRYPOINT and CMD are used. The command must be idempotent: it may be
	// re-executed on a new attempt after an infrastructure failure.
	// +optional
	// +listType=atomic
	Command []string `json:"command,omitempty"`

	// TargetContainerName is the sandbox container whose filesystem is updated.
	// When empty it defaults to the first container of the sandbox Pod template.
	// +optional
	TargetContainerName string `json:"targetContainerName,omitempty"`

	// Env is appended to the environment variables the controller injects. See the
	// Installer Contract for the reserved SANDBOX_INSTALLER_* names.
	// +optional
	// +listType=map
	// +listMapKey=name
	Env []v1.EnvVar `json:"env,omitempty"`

	// SecurityContext overrides the security context of the installer container.
	// The controller defaults capabilities.add to ["SYS_PTRACE"] and inherits the
	// target container's runAsUser when it is set.
	// +optional
	SecurityContext *v1.SecurityContext `json:"securityContext,omitempty"`

	// ImagePullPolicy for the installer image. Defaults to IfNotPresent.
	// +optional
	// +kubebuilder:validation:Enum=Always;IfNotPresent;Never
	ImagePullPolicy v1.PullPolicy `json:"imagePullPolicy,omitempty"`

	// TimeoutSeconds bounds a single install attempt. When the installer container
	// has been running longer than this, the sandbox is marked InstallingFailed.
	// The container itself cannot be stopped; see Risks and Mitigations.
	// Defaults to 600.
	// +optional
	// +kubebuilder:default=600
	// +kubebuilder:validation:Minimum=1
	TimeoutSeconds *int32 `json:"timeoutSeconds,omitempty"`
}
```

`InstallerSpec` is declared in `api/v1alpha1/sandbox_types.go` rather than in
`sandboxupdateops_types.go`, because it is referenced from both
`SandboxUpdateOpsStrategy.Installer` and `SandboxUpgradePolicy.Installer`. That
file already imports `v1 "k8s.io/api/core/v1"` and already carries a
`+kubebuilder:default` on a timeout field (`UpgradeAction.TimeoutSeconds`), so the
markers above follow existing convention in the same file.

#### `SandboxUpgradePolicyType`, `SandboxUpgradePolicy`, `SandboxStatus`

`api/v1alpha1/sandbox_types.go:151-174`:

```go
const (
	SandboxUpgradePolicyRecreate SandboxUpgradePolicyType = "Recreate"

	SandboxUpgradePolicyCheckpointRestore SandboxUpgradePolicyType = "CheckpointRestore"

	// SandboxUpgradePolicyInstallerUpdate means the sandbox will be updated by
	// running an injected ephemeral installer container against the live Pod. The
	// Pod is not replaced and container images are not changed.
	SandboxUpgradePolicyInstallerUpdate SandboxUpgradePolicyType = "InstallerUpdate"
)

type SandboxUpgradePolicy struct {
	// Type specifies the upgrade policy type.
	// When empty (default), upgrading is disabled.
	// Supported values: Recreate, CheckpointRestore, InstallerUpdate.
	// +kubebuilder:validation:Enum=Recreate;CheckpointRestore;InstallerUpdate
	// +optional
	Type SandboxUpgradePolicyType `json:"type,omitempty"`

	// PatchVersion identifies the payload this upgrade installs. It is an opaque
	// token: SandboxUpdateOps sets it to the UID of the owning ops object, so every
	// operation carries a distinct value. The sandbox controller runs an
	// InstallerUpdate upgrade only while PatchVersion differs from
	// status.completedPatchVersion; Recreate and CheckpointRestore ignore it because
	// they key off the Pod template revision instead.
	// Required when Type is InstallerUpdate.
	// +optional
	PatchVersion string `json:"patchVersion,omitempty"`

	// Installer configures the ephemeral container for an InstallerUpdate
	// upgrade. Required when Type is InstallerUpdate, forbidden otherwise.
	// +optional
	Installer *InstallerSpec `json:"installer,omitempty"`
}
```

```go
type SandboxStatus struct {
	// ...existing fields...

	// CompletedPatchVersion is the spec.upgradePolicy.patchVersion of the last
	// InstallerUpdate upgrade that finished successfully. It is what makes the
	// install idempotent: the controller does not re-run a patch it has already
	// completed, and a new ops object carries a new token.
	// +optional
	CompletedPatchVersion string `json:"completedPatchVersion,omitempty"`
}
```

`SandboxUpgradePolicy` exists only on `SandboxSpec`
(`api/v1alpha1/sandbox_types.go:107`); it is not a field of `SandboxSetSpec` or
`SandboxTemplateSpec`, so the pool-level mirroring rule does not apply and
`NewSandboxFromSandboxSet` needs no change.

Why a `PatchVersion` rather than reusing `status.updateRevision`: `updateRevision`
is the hash of `spec.template` and is contractually equal to the Pod's
`pod-template-hash` label (`pkg/controller/sandbox/core/pod_control.go:342`,
`pkg/controller/sandbox/core/util.go:36`). An install changes neither, so folding
the installer into that hash would permanently desynchronise the label from the
revision and break
`pkg/controller/sandbox/sandbox_controller.go:946` and
`pkg/controller/sandbox/core/upgrade_control.go:394`. A separate token avoids
that entirely.

The field is named for what it will carry rather than for how it is generated
today. Deriving it from the ops UID keeps SUO the only writer and guarantees
distinctness across operations, which is all the controller needs. Letting an
operator set it explicitly from the payload version — so that
`status.completedPatchVersion` reads as `1.4.0` rather than as a UID — is a
compatible later extension, since the controller only ever compares the two values
for equality.

Why the token cannot be dropped: the `Upgrading` condition alone is insufficient.
SUO clears `spec.upgradePolicy` only after it observes success, so between
"install succeeded" and "policy cleared" a condition-based trigger would fire
again and loop. And a *second* install requested later would find
`Upgrading=Succeeded` already set and never start.

#### New `Upgrading` condition reasons

`api/v1alpha1/sandbox_types.go:617-630` gains two reasons:

```go
	// SandboxUpgradingReasonInstalling means the installer container has been
	// injected and the controller is waiting for it to terminate.
	SandboxUpgradingReasonInstalling = "Installing"

	// SandboxUpgradingReasonInstallingFailed means the installer container exited
	// non-zero, could not be created, or exceeded its timeout.
	SandboxUpgradingReasonInstallingFailed = "InstallingFailed"
```

`InstallingFailed` is added to the terminal-failure reason set in
`pkg/controller/sandboxupdateops/sandboxupdateops_controller.go:436-441` so SUO
fail-stops on it exactly as it does for `UpgradePodFailed`.

The `Checkpointing` reason is skipped for this policy —
`EnsureCheckpointForUpgrade` already short-circuits when the policy is not
`CheckpointRestore` (`pkg/controller/sandbox/core/checkpoint.go:365`), so the
state machine simply does not enter it.

#### Feature gate

Following `pkg/features/features.go`, add:

```go
	// SandboxInstallerUpdate enables the InstallerUpdate upgrade strategy.
	// It requires a container runtime that implements CRI namespace targeting.
	SandboxInstallerUpdateGate featuregate.Feature = "SandboxInstallerUpdate"
```

registered as `featuregate.FeatureSpec{Default: false, PreRelease: featuregate.Alpha}`.
The gate is checked by the sandbox controller and by the SUO validating webhook,
which rejects `InstallerUpdate` when the gate is disabled. `pkg/features` is
controller-only, and both consumers are controllers or webhooks, so this respects
the layering rule.

### Installer Contract

The controller injects these environment variables into the installer container.
They are a stable contract; operator-supplied `installer.env` entries must not use
the `SANDBOX_INSTALLER_` prefix.

| Variable | Value |
|---|---|
| `SANDBOX_INSTALLER_TARGET_ROOT` | `/proc/1/root` — absolute prefix of the target container's filesystem. |
| `SANDBOX_INSTALLER_TARGET_CONTAINER` | Resolved target container name. |
| `SANDBOX_INSTALLER_PATCH_VERSION` | `spec.upgradePolicy.patchVersion`. |
| `SANDBOX_INSTALLER_ATTEMPT` | 1-based attempt counter. |
| `SANDBOX_NAME`, `SANDBOX_NAMESPACE`, `SANDBOX_UID` | Identity of the sandbox. |

The installer command is expected to:

1. **Verify targeting took effect** before writing anything. If the runtime does
   not implement namespace targeting, `/proc/1/root` resolves to the installer's
   *own* root and the install silently mutates a filesystem that is discarded on
   exit. A POSIX-portable guard is:

   ```sh
   [ /proc/1/root -ef / ] && { echo "namespace targeting unavailable" >&2; exit 125; }
   ```

   Exit code 125 is reserved for this condition so the controller can report it
   distinctly from an installer bug.
2. **Write through the prefix**, e.g.
   `cp -a /payload/. "$SANDBOX_INSTALLER_TARGET_ROOT/opt/harness/"`. A raw copy is
   correct only for a payload with no absolute paths baked into it; where the
   harness has a prefix-aware installer or package manager, prefer redirecting
   that instead — see
   [Run your own tooling, never the target's](#run-your-own-tooling-never-the-targets).
3. **Never overwrite a running executable in place.** Writing to a mapped binary
   fails with `ETXTBSY`. Write to a temporary path in the same directory and
   `rename(2)` over the target; the running process keeps the old inode until it
   is restarted by the `postUpgrade` hook.
4. **Assert that nothing baked in the installer's own view of the path.** If the
   toolchain writes absolute shebangs or config paths, they will contain
   `/proc/1/root`, which does not exist inside the target. The grep guard in
   [Relocatability is the real constraint](#relocatability-is-the-real-constraint)
   covers this; **exit code 126 is reserved** for it, so the controller can
   distinguish "targeting never worked" (125) from "the install landed but is
   unusable" (126) from an ordinary installer bug.
5. **Be idempotent.** It may run more than once.
6. **Exit 0 on success.** stdout and stderr are truncated into the `Upgrading`
   condition message, following the existing hook behaviour
   (`pkg/controller/sandbox/core/upgrade_control.go:516`).

#### PID 1 in the target container

The contract is anchored on `/proc/1/root`, which is the root filesystem of **PID 1
of the target container's PID namespace**. Two constraints follow from that, and
they pull in opposite directions.

**The sandbox entrypoint must not be PID 1.** Vendor updaters stop the service they
are updating. `hermes update` stops every gateway belonging to its install
immediately before it first changes the checkout, unless `--no-gateway-restart` is
passed; `openclaw update` restarts the gateway unless `--no-restart` is passed. If
the harness *is* PID 1, stopping it terminates the container, and the kubelet
creates a new container instance with a **fresh writable layer** — the install is
destroyed moments after it succeeded, and the batch still reports success, because
the installer exited 0 before the stop happened. The same applies to a plain
`kill(1)` from any tooling the updater invokes.

So the sandbox must be authored with an init or supervisor as PID 1 and the harness
as its child. This is already the convention in this repository: the OpenClaw
example injects `tini` and runs `command: ["/mnt/tini/tini", "--"]`
(`examples/openclaw/README.md:106`), so the gateway is a child of `tini` and
stopping it does not end the container. A supervisor is also what reaps the
processes an injected ephemeral container leaves behind in the shared PID
namespace, since PID 1 owns orphan reaping.

Where an image cannot be re-authored, the updater must be told not to stop the
service. The contract's position is that stopping and restarting the workload is
`postUpgrade`'s job rather than the installer's, because `postUpgrade` runs after
the installer has exited and after the controller has observed its exit code — a
restart there is visible and can fail the batch.

**The target container must own its PID namespace.** If the resolved Pod spec sets
`shareProcessNamespace: true` or `hostPID: true`, PID 1 is the `pause` container or
the node's init rather than the target's entrypoint, so `/proc/1/root` names the
wrong rootfs. The step-1 `-ef` guard does **not** catch this: `pause`'s root is not
the installer's root either, so the check passes and the installer writes the
payload into `pause` and exits 0. Nothing in the repository validates either field
today, so the controller must check them itself before injecting — see
[Sandbox Controller Changes](#sandbox-controller-changes).

#### Run your own tooling, never the target's

`targetContainerName` joins the target's **PID and IPC** namespaces only. The mount
namespace is not shared and cannot be — Kubernetes deliberately does not let one
container enter another's, because critical mount points must not leak between
containers. So `/proc/1/root` grants **file access to the target's filesystem, not
execution within it**. This is the single most important constraint on what an
installer command may do.

Writing through the prefix works: `open`, `read`, `write`, `mkdir`, `unlink` and
`rename` all follow the magic symlink and land in the target's mount namespace.

Executing through it does not. If the installer runs
`"$SANDBOX_INSTALLER_TARGET_ROOT/usr/local/bin/openclaw" update`:

- `execve(2)` itself succeeds — the kernel reads the binary through the symlink.
- The ELF interpreter named in `PT_INTERP` (`/lib64/ld-linux-x86-64.so.2`) and
  every shared library it loads are then resolved in the **installer's** mount
  namespace. If the installer image lacks a compatible loader, the failure is the
  misleading `ENOENT` on a binary that plainly exists; if it has one with a
  different libc, the harness may start and behave incorrectly.
- Once running, the process's `/` is still the installer's rootfs. So
  `argv[0]`, `/proc/self/exe`, `getcwd`, `/etc/*`, `which node` and
  `npm root -g` all resolve into the ephemeral container — which is discarded on
  exit.

The net effect is an install that reports success and changes nothing. **The
`-ef` self-check in step 1 does not detect this**, because `/proc/1/root != /` is
true; the guard proves namespace targeting took effect, not that a foreign binary
was executed correctly. Verification is the `postUpgrade` hook's job, which is why
it is mandatory in practice rather than optional.

The correct pattern is the inverse: **execute tooling that ships in the installer
image, and redirect its output prefix into the target rootfs.** The tooling then
runs entirely in the installer's own mount namespace — no `execve` trap — while
every byte it writes lands in the target. Every harness surveyed supports this;
see [Install-location overrides](#install-location-overrides).

```sh
target="$SANDBOX_INSTALLER_TARGET_ROOT/usr/local"

# npm-distributed harnesses (Codex CLI, Gemini CLI, Claude Code legacy path):
NPM_CONFIG_PREFIX="$target" npm install -g --offline /payload/openclaw-1.2.3.tgz

# OpenClaw's own local-prefix installer, shipped in the installer image:
/install-cli.sh --prefix "$SANDBOX_INSTALLER_TARGET_ROOT/opt/openclaw" --no-prompt --json

# Harnesses with no prefix support (Claude Code native binary):
install -m 0755 /payload/claude "$SANDBOX_INSTALLER_TARGET_ROOT/root/.local/bin/claude"
```

This is why the installer image is the payload *carrier* and not merely a file
source: it brings a package manager, a known libc, and optionally the vendor's own
installer, so the operator reuses tested install logic instead of reimplementing
it as `cp -a`. The four consequences in
[Install-location overrides](#install-location-overrides) apply — never query the
prefix from inside the installer, match the libc family, resolve "home" against
the target rootfs, and prefer the offline form.

The corollary is that **`nsenter` is not required, and must not be a controller
default.** Anything that genuinely needs to run inside the target's mount
namespace belongs in `spec.lifecycle.postUpgrade.exec`, which is executed by envd
inside the sandbox container
(`pkg/controller/sandbox/core/lifecycle_handler.go:70`) and therefore already has
the target's rootfs, PATH, service manager and root identity with no additional
capability. Operators who nonetheless want `nsenter` in the installer command can
write it there, but must grant `CAP_SYS_ADMIN` themselves via
`installer.securityContext` and accept the containment trade-off described in
[Alternatives](#alternatives).

#### Payload staging

`postUpgrade` can only run what the sandbox image already contains or what it can
fetch over the network. To let a pinned, offline payload be *executed* rather than
merely copied, the installer stages it at a predictable location in the target's
filesystem:

```sh
stage="$SANDBOX_INSTALLER_TARGET_ROOT/var/lib/sandbox-installer/$SANDBOX_INSTALLER_PATCH_VERSION"
mkdir -p "$stage"
cp -a /payload/. "$stage/"
```

`postUpgrade` then consumes that directory — unpacking a tarball, running a
vendor installer against a local path, or simply asserting the version the
installer already placed. The staging directory is keyed by `patchVersion` so
retries and successive operations cannot collide, and removing it is a normal
`postUpgrade` step.

Restarting the harness and asserting the new version are deliberately *not* the
installer container's job. They belong in `spec.lifecycle.postUpgrade.exec`, which
runs inside the sandbox container via envd as root
(`pkg/controller/sandbox/core/lifecycle_handler.go:79`) and therefore uses the
sandbox's own service manager and PATH. A failing `postUpgrade` drives the sandbox
to `PostUpgradeFailed` and fail-stops the batch, which makes it the verification
gate for the whole operation.

Privileges: reading `/proc/<pid>/root` is guarded by the kernel's
`ptrace_may_access` check, not by ordinary file permissions. Root-to-root across
containers usually passes on UID equality, but only while the target process is
dumpable; a harness that drops privileges or changes credentials will fail with
`EPERM`. The controller therefore defaults the installer container's
`securityContext.capabilities.add` to `["SYS_PTRACE"]`. Blast radius is bounded —
the installer is in the target's PID namespace only, so it can reach that
container's processes and nothing else. `installer.securityContext` fully
overrides this default for clusters whose Pod Security Admission profile forbids
adding capabilities.

Image pulls for the installer container use the Pod's existing `imagePullSecrets`;
there is no per-ephemeral-container credential mechanism. A private installer
registry therefore requires the secret to already be present on the sandbox Pod
template.

### SandboxUpdateOps Controller Changes

All in `pkg/controller/sandboxupdateops/`.

**`patch.go` — `applySandboxPatch` (line 140).** The ops→sandbox policy mapping at
lines 144-150 gains an `InstallerUpdate` case. It sets the policy type, sets
`PatchVersion` to the UID of the owning ops object, and deep-copies
`ops.Spec.UpdateStrategy.Installer` into the policy.

For `InstallerUpdate` the function must **not** call `mergeTemplate`, because
there is no template change to apply. The `Paused` branch at line 170 still sets
`AnnotationUpgradeResumeTrigger`, but now alongside the full policy rather than
instead of it — there is no phase-2 template patch to wait for.

**`sandboxupdateops_controller.go` — `classifySandbox` (line 381).** Three
adjustments, all guarded on the strategy being `InstallerUpdate`:

- Line 398 and line 456 call `isSandboxTemplateMatchPatch`, which short-circuits
  to `sandboxNoNeedUpdate` when the template already matches the patch. With no
  image change — and typically an empty `spec.patch` — that check is meaningless
  here and would let the ops complete without installing anything. Replace it with
  an install-aware check: the sandbox needs no update when
  `sbx.Status.CompletedPatchVersion == string(ops.UID)`.
- Line 467 returns `sandboxResumeSucceed` for a labelled, `Running` sandbox with no
  `Upgrading` condition. That heuristic exists to recover a lost phase-2 template
  patch. `InstallerUpdate` has no phase 2, so this branch must be skipped; such a
  sandbox is simply `sandboxUpdating`.
- Line 436-441 gains `InstallingFailed` in the terminal-failure set.

**`syncSandboxUpgradeState` (line 505)** is unchanged: it already clears
`spec.upgradePolicy` for succeeded sandboxes and manages the
`agents.kruise.io/upgrade-failed` label, both of which are correct for this
strategy. `handleDeletion` (line 558) is likewise unchanged — it strips the
tracking label and the resume trigger, and clears the policy on succeeded
sandboxes.

The namespace-wide mutual exclusion at line 114, the finalizer, `maxUnavailable`
accounting, deterministic candidate ordering and `ResourceVersionExpectations` all
apply unchanged.

### Sandbox Controller Changes

**Trigger** — `pkg/controller/sandbox/sandbox_controller.go:790`. The trigger
condition must split by policy. Today it fires when the computed
`status.updateRevision` differs from the recorded one *and* the policy requires a
Pod replacement; under `InstallerUpdate` neither half holds. For installer policy it
instead fires when `spec.upgradePolicy.patchVersion` is non-empty and differs from
`status.completedPatchVersion`. Both paths keep the existing effect: set
`Phase=Upgrading` and remove the `Upgrading` and `Paused` conditions.

The `SandboxUpgrading` case at line 857, which resets the condition when the
template changes mid-upgrade, needs the same split: for installer policy compare
`PatchVersion` against `CompletedPatchVersion` instead of the template revision, so a
re-issued patch resumes from the right step.

**Gate** — `pkg/controller/sandbox/core/upgrade_control.go:100`. Add a
`RequiresInstallerUpgrade` predicate alongside the existing
`RequiresPodReplacementUpgrade`, returning true when the sandbox's upgrade policy
type is `InstallerUpdate`. `RequiresPodReplacementUpgrade` keeps its current
two-value body, so nothing about `Recreate` or `CheckpointRestore` changes.

**Dispatch** — `pkg/controller/sandbox/core/common_control.go:184`. The in-place
update fast path must exclude installer policy as well, otherwise
`handleInplaceUpdateSandbox` would try to reconcile the Pod against a revision
that the Pod was never created from. Backend-specific control implementations that
duplicate this dispatch must apply the same guard.

**State machine** — `pkg/controller/sandbox/core/upgrade_control.go:116`. For
installer policy the chain becomes `Resuming → ResumeSucceed → PreUpgrade →
Installing → PostUpgrade → Succeeded`; `Checkpointing` and `UpgradePod` are
skipped.

`ResumeSucceed` (line 180) currently waits for SUO to apply a phase-2 template
patch and abandons the upgrade if the resume trigger disappears without a revision
change. Under installer policy there is no phase-2 patch, so this state must
transition directly to `PreUpgrade`; the abandonment check keys off
`PatchVersion != CompletedPatchVersion` instead of `UpdateRevision`.

**New `Installing` step.** A `performInstallerUpgrade` function replaces
`Checkpointing` + `UpgradePod` and does seven things:

1. **Resolve the target container.** `installer.targetContainerName`, or
   `spec.template.spec.containers[0].name` when empty — the same convention
   `Sandbox.SetImage` uses
   (`pkg/sandbox-manager/infra/sandboxcr/sandbox.go:468`). If the name is absent
   from the resolved Pod spec, set `InstallingFailed` with an explanatory message;
   this cannot be caught at admission because the selector may match sandboxes
   that do not exist yet.
2. **Guard PID namespace ownership.** If the resolved Pod spec sets
   `shareProcessNamespace` or `hostPID`, set `InstallingFailed` with an explanatory
   message. PID 1 would then be `pause` or the node's init, so `/proc/1/root` names
   the wrong rootfs and the installer's own `-ef` guard cannot detect it — see
   [PID 1 in the target container](#pid-1-in-the-target-container). Like the target
   name resolution in step 1, this is a controller-side check rather than an
   admission check, because the selector may match sandboxes that do not exist yet.
3. **Require a live target.** The Pod must be `Running` and the target's
   `ContainerStatus.State.Running` must be non-nil. Otherwise wait — do not fail,
   since a transient restart should not abort the batch.
4. **Count prior attempts** by scanning `pod.Spec.EphemeralContainers` for names
   prefixed `installer-<hash8(patchVersion)>`. Attempt numbering and the retry cap
   are derived from this list, so no extra status field is needed. Exceeding the
   cap (`--installer-max-attempts`, default 3) sets `InstallingFailed`.
5. **Inject.** Append one `EphemeralContainer` named
   `installer-<hash8>-<attempt>`, carrying the resolved image, command, env,
   security context and image pull policy, with `TargetContainerName` set. Write it
   through the `ephemeralcontainers` subresource — the same pattern already used
   for `pods/resize` at `pkg/utils/inplaceupdate/inplace_update.go:524`. A
   `Conflict` means the Pod changed underneath us: requeue and retry the whole
   step, recomputing from the fresh Pod rather than injecting twice.
6. **Wait and evaluate** `pod.Status.EphemeralContainerStatuses` for the injected
   name:
   - `State.Waiting.Reason == "ImagePullBackOff" | "ErrImagePull"` → retryable;
     re-inject on the next attempt (the failed entry stays, since ephemeral
     containers cannot be removed).
   - `State.Terminated.ExitCode == 0` → success; proceed.
   - `State.Terminated.ExitCode == 125` → `InstallingFailed`, message "container
     runtime does not support namespace targeting"; **not** retried, because
     retrying cannot change the runtime's capability.
   - `State.Terminated.ExitCode == 126` → `InstallingFailed`, message "installer
     baked an absolute `/proc/1/root` path into the target"; **not** retried,
     because the same toolchain will bake the same path. This is the
     non-relocatable-toolchain failure described in
     [Relocatability is the real constraint](#relocatability-is-the-real-constraint),
     and reporting it distinctly is what stops an operator debugging the runtime
     instead of their installer image.
   - Any other non-zero exit → `InstallingFailed` with truncated stdout/stderr;
     not retried, because a failed installer may have left the target filesystem
     half-updated and blindly re-running it is not obviously safe.
   - `State.Running` past `installer.timeoutSeconds` (measured from
     `State.Running.StartedAt`) → `InstallingFailed`, message noting the container
     cannot be terminated.
7. **Record completion.** Copy `spec.upgradePolicy.patchVersion` into
   `status.completedPatchVersion`, then fall through to `PostUpgrade`.

On success the existing tail of `EnsureSandboxUpgraded` (lines 291-305) already
does the right thing: `Upgrading=True/Succeeded`, `Phase=Running`,
`Ready=True/PodReady`. The `CleanupCheckpoints` call at line 287 stays guarded on
`isCheckpointRestore`.

**Pod recreation is untouched.** `performRecreateUpgrade` is not called, so the
Pod keeps its original `pod-template-hash` label and its original container image,
both of which remain correct because `spec.template` was never modified.

**RBAC.** `config/rbac/role.yaml` gains a `pods/ephemeralcontainers` rule with
`get`, `patch`, `update`, alongside the existing `pods/resize` and `pods/status`
subresource block at lines 38-46.

**Flag.** `--installer-max-attempts` (default 3) on the sandbox controller,
registered next to the existing `--checkpoint-id-annotation-key` flag.

### Validation

In `pkg/webhook/sandboxupdateops/validating/sandboxupdateops_validate.go`:

- **Gate check.** Reject `InstallerUpdate` when `SandboxInstallerUpdateGate` is
  disabled.
- **`installer` presence.** Required when `type == InstallerUpdate`; forbidden
  otherwise.
- **`installer.image`.** Required, non-empty.
- **`installer.command`.** Every element non-empty.
- **`installer.timeoutSeconds`.** Positive.
- **No image change.** Generalise the existing `validateNoImageChange` helper
  (line 138) so its message names the strategy, and apply it to
  `InstallerUpdate` as well as `CheckpointRestore`. Both strategies preserve the
  writable layer, and under `InstallerUpdate` an image change would additionally
  restart the target container and destroy the layer the install just wrote.
- **`installer.env`.** Reject names with the reserved `SANDBOX_INSTALLER_` prefix.
- **`installer.securityContext`.** Reject `privileged: true`. This is a new check —
  nothing in the repository restricts it today, and `--allow-privileged` defaults to
  `true` (`cmd/agent-sandbox-controller/main.go:127`), so the upstream validation
  the webhook borrows permits privileged containers.
  **`CAP_SYS_ADMIN` is deliberately not rejected.** It is strictly worse than what
  the design needs, and the controller never adds it by default — the only
  capability it injects is `SYS_PTRACE`. But an explicit
  `installer.securityContext.capabilities.add: ["SYS_ADMIN"]` is how an operator
  opts into the `nsenter` escape hatch described in
  [Alternatives](#alternatives), so rejecting it would close a documented path.
- **PID namespace ownership.** `shareProcessNamespace` and `hostPID` are Pod-side
  fields that cannot be checked here, because the selector may match sandboxes that
  do not exist yet. They are checked by the sandbox controller at inject time — see
  [Sandbox Controller Changes](#sandbox-controller-changes) and
  [PID 1 in the target container](#pid-1-in-the-target-container).
- **Immutability.** `handleUpdate` (line 152) currently permits changing
  `updateStrategy`. Narrow that for this strategy: `updateStrategy.installer` is
  immutable after creation, like `patch` and `lifecycle`, because mutating it
  mid-batch would leave some sandboxes installed from one payload and some from
  another. `type`, `maxUnavailable` and `stateFilter` remain mutable.
- **Mutual exclusion.** The existing one-active-ops-per-namespace rule (line 113)
  applies unchanged.

### Durability of the Result

The installed content lives in the target container's writable layer. Operators
must understand its lifetime:

| Event | Outcome |
|---|---|
| Sandbox keeps running | Content persists indefinitely. |
| Target container restarts in place (crash, `restartPolicy: Always`, or an updater stopping a harness that is PID 1) | **Lost.** The kubelet creates a new container instance with a fresh writable layer. |
| Pod deleted / node failure / eviction | **Lost.** A new Pod is created from `spec.template`, which still names the original image. |
| `spec.paused` with `pauseStrategy: Stop` | **Lost** — the Pod is deleted. |
| `spec.paused` with `pauseStrategy: Hibernate` and `persistentContents: [filesystem]` | Preserved through the checkpoint/restore path. |
| Recycle back to a warm pool | **Lost.** |

This is inherent to any in-place filesystem mutation, including a developer
running `npm i -g` by hand, and it is the trade the operator is explicitly making:
zero disruption now, at the cost of durability.

Two supported patterns make the result durable, both using mechanisms that already
exist:

1. **Commit, then recreate at a maintenance window.** Use the `Commit` CR
   (`docs/proposals/20260506-sandbox-commit.md`, `SquashLayer` at
   `api/v1alpha1/commit_types.go:66`) to bake the writable layer into a new image,
   then run a normal `Recreate` SUO with a `spec.patch` pointing at it. The fleet
   converges on a real image with no data loss window.
2. **Install onto a PVC.** Mount a `spec.volumeClaimTemplates` PVC into the
   sandbox at the harness prefix and have the installer write there. PVC content
   survives Pod replacement. The installer can reach it either through
   `/proc/1/root/<mountpoint>` or by mounting the same PVC directly, since
   `volumeMounts` are permitted on ephemeral containers (subPath mounts are not).

The proposal deliberately does not automate either pattern; composing them is the
operator's choice.

### Implementation Details/Notes/Constraints

- **`spec.patch` is still allowed**, but under `InstallerUpdate` it should be
  empty or metadata-only. Any template change advances `status.updateRevision`
  without changing the Pod's `pod-template-hash` label, which leaves the Pod
  apparently stale until SUO clears `spec.upgradePolicy` on success; the existing
  in-place handler then reconciles the label through its metadata-only fast path
  (`pkg/controller/sandbox/core/common_inplace_update_handler.go:159`). That works
  but is subtle, so the recommended usage is no patch at all.
- **Empty `spec.patch` is safe for classification.**
  `isSandboxTemplateMatchPatch` returns `false` when `len(ops.Spec.Patch.Raw) == 0`
  (`pkg/controller/sandboxupdateops/patch.go:77`), so an empty patch never
  short-circuits a sandbox to `NoNeedUpdate`. The installer-aware check replaces
  that logic anyway.
- **Ephemeral containers accumulate permanently.** Each attempt appends an entry to
  `pod.spec.ephemeralContainers` that can never be removed, along with its
  `ephemeralContainerStatuses` entry. This is bounded by `--installer-max-attempts`
  and by the one-ops-per-namespace rule, but it does mean a Pod that is installed
  repeatedly grows. The names are deterministic per patch version so the growth is
  auditable.
- **`RestartPolicy` must not be set** on the injected container. Ephemeral
  containers are never restarted; requesting otherwise is rejected by the API
  server.
- **Termination message.** Set `terminationMessagePolicy: FallbackToLogsOnError`
  on the injected container so a failing installer's last log lines surface in
  `ephemeralContainerStatuses[].lastState.terminated.message`, which the
  controller copies into the condition message.
- **Container name validity.** The generated name must be a DNS label: lowercase
  alphanumerics and `-`, at most 63 characters, and unique across the Pod's
  containers, init containers and ephemeral containers. `installer-<8 hex>-<n>`
  satisfies this; hash `patchVersion` rather than embedding it, since the value is
  opaque and today is a 36-character UID, which would crowd the budget.
- **No probes, no ports, no lifecycle hooks** on the installer container — all
  rejected by the API server. Readiness is judged solely from
  `ephemeralContainerStatuses`.
- **envtest cannot exercise this path.** There is no kubelet, so
  `ephemeralContainerStatuses` is never populated. Unit tests must synthesise
  those statuses; only the e2e suite on a real cluster validates end-to-end
  behaviour.
- **All changes land in community-owned files**: `api/v1alpha1`,
  `pkg/controller/sandboxupdateops`, `pkg/controller/sandbox`,
  `pkg/webhook/sandboxupdateops`, `pkg/features/features.go`, `config/rbac`,
  `config/crd`. Backend-specific control implementations need only the dispatch
  guard described above.
- Run `make generate manifests` after the API change, and
  `hack/generate_client.sh` for the typed client.

### Risks and Mitigations

**The runtime does not implement namespace targeting, and the install silently
does nothing.** The API contract for an unsupporting runtime is explicitly
"undefined" (`k8s.io/api` types.go:5242-5243). The installer would see its own
rootfs at `/proc/1/root`, "succeed", and be discarded on exit — a silent no-op
that reports success.
*Mitigation:* the contract requires the `-ef` self-check with reserved exit code
125, which the controller maps to a distinct `InstallingFailed` message. The
`postUpgrade` hook is the second line of defence: it runs inside the real target
container and should assert the new version, turning a silent no-op into a
fail-stopped batch. The feature gate is off by default so the runtime can be
verified before enablement.

**The installer executes a binary from under the prefix instead of copying
files.** This produces the same silent no-op as the risk above but from a
different cause, and **the `-ef` guard does not detect it** — namespace targeting
did take effect, so `/proc/1/root != /`. The foreign binary loads the installer
image's dynamic loader and libraries, and then resolves its own install location
into the ephemeral container's rootfs. See
[Run your own tooling, never the target's](#run-your-own-tooling-never-the-targets).
*Mitigation:* the contract states the rule explicitly and explains the mechanism,
because an operator who has not hit it will otherwise reach for the obvious
`"$SANDBOX_INSTALLER_TARGET_ROOT/usr/bin/<harness>" update`. `postUpgrade`
asserting the new version is the only reliable detector, which is why the test
plan treats a version-asserting `postUpgrade` as required rather than
recommended. `nsenter` is the deliberate escape hatch for operators who must run
the vendor updater, at the cost of `CAP_SYS_ADMIN`.

**The toolchain bakes absolute paths, so the install lands but is unusable.**
Distinct from both risks above and harder to spot: namespace targeting worked, the
files are all in the right place, and the installer exited 0 — but every shebang
and `pyvenv.cfg` entry says `/proc/1/root/…`, a path that does not exist inside
the target. Any Python venv toolchain does this by default; `uv` only produces
relative paths with `--relocatable`, which is not the stable default. See
[Relocatability is the real constraint](#relocatability-is-the-real-constraint).
*Mitigation:* the contract reserves exit code **126** for a post-write
`grep -r "$SANDBOX_INSTALLER_TARGET_ROOT"` assertion, mapped to a distinct
`InstallingFailed` message; the classification table tells operators which class
their toolchain is in and what flag it needs; and preferring a self-contained
directory located by a `*_HOME` variable avoids absolute-path baking altogether.
`postUpgrade` remains the backstop, since the harness will fail to start.

**The install succeeds and is then wiped by a workload restart.** If the harness is
PID 1 of the target container, an updater that stops the service ends the
container, and the kubelet restarts it with a fresh writable layer. The installed
content disappears *after* the batch has already reported success. See
[PID 1 in the target container](#pid-1-in-the-target-container) and
[Durability](#durability-of-the-result).
*Mitigation:* documented as an authoring requirement on the sandbox image — run an
init or supervisor as PID 1 with the harness as its child, which is what the
OpenClaw example already does (`examples/openclaw/README.md:106`). The controller
cannot enforce this, because whether PID 1 is the harness is a property of the
image's entrypoint and not of the Pod spec. Two backstops: the installer shares the
target's PID namespace, so it can read and log `/proc/1/cmdline` and an operator
who knows their harness can assert on it; and a `postUpgrade` that asserts the new
version *after* the restart step turns a wiped install into a fail-stopped batch.

**A hung installer cannot be stopped.** Ephemeral containers have no `lifecycle`,
cannot be removed, and are not restarted. There is no API to kill one.
*Mitigation:* `timeoutSeconds` moves the sandbox to `InstallingFailed` so the
batch fail-stops and the operator is notified. The runaway container keeps running
until the Pod dies. Because it shares the target's PID namespace, its processes
are visible from inside the sandbox container, so an operator can terminate them
manually with `kubectl exec`. The contract recommends wrapping the command in
`timeout(1)`. This is the sharpest limitation of the design and is called out in
user-facing documentation.

**No resource limits, so the installer competes with the workload and can get the
Pod evicted.** `resources` is forbidden on ephemeral containers, and the API
documentation warns "The kubelet may evict a Pod if an ephemeral container causes
the Pod to exceed its resource allocation" (types.go:5226). A payload copy can be
I/O- and page-cache-heavy.
*Mitigation:* document it; recommend the installer prefer `rename` over
whole-tree copies, keep payloads small, and use `nice`/`ionice`; keep
`maxUnavailable` conservative so a node-level problem affects few sandboxes at
once. There is no way to hard-guarantee isolation here.

**Wider attack surface from a customer-supplied image with `SYS_PTRACE`.** The
installer runs arbitrary customer code with ptrace over the harness process.
*Mitigation:* the blast radius is one container's PID namespace, not the node,
because targeting joins exactly one target's PID and IPC namespaces rather than
turning on pod-wide `shareProcessNamespace`. That bound holds only while the
installer is kept off `privileged` and `CAP_SYS_ADMIN`. The controller injects
`SYS_PTRACE` and nothing else, and the `installer.securityContext` check in
[Validation](#validation) rejects `privileged: true` — but that check is new work,
not a restatement of existing behaviour: `--allow-privileged` defaults to `true`
(`cmd/agent-sandbox-controller/main.go:127`), so today nothing stops it. An
operator who grants `SYS_ADMIN` explicitly for `nsenter` widens the radius
knowingly. The operator supplies the image, so this is the same trust decision as
supplying a sandbox image. Documented explicitly so it is a conscious choice.

**Partial install leaves the sandbox inconsistent.** A non-zero exit mid-copy
means some files are new and some are old.
*Mitigation:* no automatic retry on installer failure — the sandbox goes to
`InstallingFailed`, gets the `agents.kruise.io/upgrade-failed` label, consumes
`maxUnavailable` budget and fail-stops the batch, matching existing SUO semantics.
The contract requires idempotent installers and recommends staging into a
temporary directory and switching atomically. Recovery is the operator's decision:
delete and recreate the sandbox, or re-run a corrected ops.

**Result is not durable across Pod replacement.** See
[Durability](#durability-of-the-result).
*Mitigation:* documented, with the Commit and PVC patterns offered as the
supported paths to durability.

**`spec.template` no longer describes what is running.** After an install, the
sandbox image reference is the pre-upgrade one. Anyone reasoning from the spec
alone will draw the wrong conclusion about the harness version.
*Mitigation:* this is inherent to the "do not change the image" requirement. Make
it observable: record the installer image and the patch version in the `Upgrading`
condition message and in an event, and recommend the harness write a version file
that `postUpgrade` asserts on.

**Two controllers touching one Pod.** SUO writes the Sandbox; the sandbox
controller writes the Pod. The design keeps that split intact — SUO never touches
a Pod — which is why the ephemeral container injection lives in
`pkg/controller/sandbox/core` rather than in SUO.
*Mitigation:* none needed beyond preserving the split; the `Conflict`-retry loop
on the subresource update handles concurrent Pod mutation.

## Alternatives

**Pod-level `shareProcessNamespace: true` plus a regular sidecar.** Rejected.
`shareProcessNamespace` can only be set at Pod creation, so it cannot be turned on
for a running sandbox — the Pod would have to be replaced, which is exactly what
this proposal avoids. It would also expose every container's processes to every
other container rather than to one targeted installer, and it breaks the
file-access contract outright: PID 1 becomes the `pause` container, so
`/proc/1/root` no longer names the target's rootfs — see
[PID 1 in the target container](#pid-1-in-the-target-container).

**A pre-installed, always-present sidecar that waits for work.** Rejected. It
consumes resources in every sandbox for the whole fleet lifetime to serve an
occasional operation, it must still be present in the Pod template (so it cannot
be retrofitted to existing sandboxes without replacement), and it would need its
own command channel and authentication. `shareProcessNamespace` would be required
at creation time, with the same PID-1 and immutability problems as above.

**`nsenter` into the target's mount namespace and run the harness's own updater.**
Considered and rejected as the *default*. It is technically possible — an operator
can write `nsenter -t 1 -m -- <updater>` into their installer command — but the
controller must never generate it or default the capabilities it needs, for four
reasons:

- **`CAP_SYS_ADMIN` collapses the containment argument.** `setns(CLONE_NEWNS)`
  requires `CAP_SYS_ADMIN`, a categorically larger grant than `CAP_SYS_PTRACE`.
  With it, plus access to the target's namespace descriptors, the installer is
  close to privileged; the claim in
  [Installer Contract](#installer-contract) that blast radius is bounded by the
  PID namespace no longer holds.
- **The same result is available for free.** `postUpgrade` already executes
  inside the target's mount namespace via envd
  (`pkg/controller/sandbox/core/lifecycle_handler.go:70`) as root, needing no
  capability at all. Anything `nsenter` would enable belongs there.
- **Mechanical fragility.** `nsenter` must be present in the installer image
  (util-linux), the target's `/proc` and `/dev` must be usable from the new mount
  namespace, and `nsenter -m` alone leaves `cwd` and root pointing at paths that
  are now stale — operators routinely need `-t 1 -m -p -i -n` plus an explicit
  `cd /`.
- **The survey shows updaters are not built for it.** OpenClaw actively skips
  container-managed installs. The prefix-redirect contract needs no `SYS_ADMIN`
  and is hermetic precisely because it executes only tooling from the installer
  image, never a binary from under the target rootfs — see
  [Run your own tooling, never the target's](#run-your-own-tooling-never-the-targets).

`nsenter` therefore remains an operator opt-in expressed through their own
`installer.command` and `installer.securityContext`, documented but never
generated.

**Executing the installer through envd inside the sandbox container.** This is
what `lifecycle.*Upgrade.exec` already does
(`pkg/controller/sandbox/core/lifecycle_handler.go:44`). It cannot carry a
payload, cannot bring its own toolchain, and shares the workload's failure domain.
Retained in this design for the restart-and-verify step, where it is the right
tool.

**Defaulting `installer.image` to the sandbox container's image.** Tempting — the
new content would then be exactly the image's rootfs, and a generic `cp -a`
command could do the whole job. Rejected for this proposal because it cannot work
here: the requirement is that `spec.patch` does not change the image, so the
sandbox image is the *old* version and carries nothing new. Revisit only if image
changes are ever permitted under this strategy.

**Reusing `status.updateRevision` as the install token.** Rejected — see the
`PatchVersion` rationale under [API Changes](#api-changes).

**Letting SUO inject the ephemeral container directly.** Simpler, and it removes
the need for `PatchVersion` entirely, since SUO could key idempotency off the
ephemeral container name it created. Rejected because the Sandbox CR owns its Pod:
Pod writes go through `PodControl` with `ScaleExpectation` and
`ResourceVersionExpectations` guards, and SUO deliberately has no Pod RBAC today.
Splitting Pod ownership across two controllers would undermine the stale-cache
protections both rely on.

**Extending the `Commit` CR instead.** `Commit` squashes the writable layer into
an image; it does not put new content into a running sandbox. Complementary, not
an alternative — see the durability pattern above.

## Upgrade Strategy

Existing clusters need no changes. The new strategy is additive and inert until
used:

- `InstallerUpdate` is a new enum value on `SandboxUpdateOpsStrategy.Type` and
  `SandboxUpgradePolicy.Type`. Existing objects carrying `Recreate`,
  `CheckpointRestore`, or an empty type are unaffected; the empty-type default of
  `Recreate` is applied in Go code (`pkg/controller/sandboxupdateops/patch.go:144`),
  not by the API server, and does not change.
- New optional fields only: `updateStrategy.installer`,
  `upgradePolicy.patchVersion`, `upgradePolicy.installer`,
  `status.completedPatchVersion`. Absent means unused.
- `SandboxInstallerUpdateGate` defaults to `false`, so a controller upgraded
  without configuration change behaves exactly as before, and the webhook rejects
  the new strategy.
- Rolling the controller back after an install has completed is safe: the
  installed files are in the container writable layer and are not tracked by any
  controller state. A rollback *during* an install leaves the sandbox with an
  `Installing` condition that an older controller will not advance; the operator
  recovers by clearing `spec.upgradePolicy`, which is what SUO's
  `handleDeletion` already does.
- CRD update requires `make generate manifests` and applying
  `config/crd/bases/agents.kruise.io_sandboxupdateops.yaml` and
  `..._sandboxes.yaml`. New RBAC for `pods/ephemeralcontainers` must be applied
  with the controller; without it the injection fails with `Forbidden` and the
  batch fail-stops rather than silently succeeding.
- To adopt the feature: enable the gate, verify the runtime supports namespace
  targeting (a single-sandbox ops with a no-op installer image that performs the
  `-ef` self-check is a sufficient probe), then roll out with a conservative
  `maxUnavailable`.

## Additional Details

### Test Plan

**Unit — `pkg/controller/sandboxupdateops/`** (table-driven, extending the
existing tables per the repository's test rules):

- `patch_test.go`: `InstallerUpdate` sets `Type`, `PatchVersion = ops.UID` and a
  deep-copied `Installer`; does not merge the template; still sets the tracking
  label and clears the stale failure label; a `Paused` sandbox gets the resume
  trigger *and* the full policy.
- `sandboxupdateops_controller_test.go`: classification of a sandbox whose
  `CompletedPatchVersion` matches (→ `NoNeedUpdate`) and does not match (→
  `Candidate`); an empty `spec.patch` still yields candidates; a labelled
  `Running` sandbox with no `Upgrading` condition classifies as `Updating`, not
  `ResumeSucceed`; `InstallingFailed` classifies as `Failed` and consumes budget;
  `maxUnavailable` and `spec.paused` gating unchanged.

**Unit — `pkg/controller/sandbox/core/upgrade_control_test.go`:**

- `RequiresInstallerUpgrade` truth table across all four policy states (nil,
  `Recreate`, `CheckpointRestore`, `InstallerUpdate`), and
  `RequiresPodReplacementUpgrade` unchanged for the new value.
- `performInstallerUpgrade`: default target resolution to `containers[0].name`;
  unknown target name → `InstallingFailed`; target not `Running` → wait, no
  failure; first injection produces the expected `EphemeralContainer` (name,
  image, command, env including all `SANDBOX_INSTALLER_*` values,
  `TargetContainerName`, default `SYS_PTRACE`); operator `securityContext`
  overrides the default; subresource `Conflict` → error without a second
  injection.
- Status evaluation: exit 0 → `CompletedPatchVersion` set and advance to
  `PostUpgrade`; exit 125 → `InstallingFailed` with the namespace-targeting
  message, no retry; exit 126 → `InstallingFailed` with the absolute-path message,
  no retry; exit 1 → `InstallingFailed`
  with truncated stdout/stderr, no retry; `ImagePullBackOff` → retried up to the
  cap then `InstallingFailed`; running past `timeoutSeconds` → `InstallingFailed`.
- `EnsureSandboxUpgraded` under installer policy: `PreUpgrade` → `Installing` →
  `PostUpgrade` → `Succeeded`, with `Checkpointing` skipped and
  `CleanupCheckpoints` not called; `ResumeSucceed` advances to `PreUpgrade`
  without a template patch.
- `sandbox_controller_test.go`: the upgrade-trigger predicate's truth table; the
  trigger fires on a new `PatchVersion` and does not re-fire once
  `CompletedPatchVersion` matches; the `SandboxUpgrading` re-entry path resets the
  condition for a changed `PatchVersion`.

**Unit — `pkg/webhook/sandboxupdateops/validating/`:** extend the existing
strategy matrix with `installer` required/forbidden, empty `installer.image`,
empty command element, non-positive `timeoutSeconds`, reserved
`SANDBOX_INSTALLER_` env prefix, `privileged: true`, image change rejected under
`InstallerUpdate`, image change allowed under `Recreate`, `installer` immutable
on update, and rejection when the feature gate is off.

**E2E — `test/e2e/sandboxupdateops_test.go`** (real cluster; envtest cannot
populate `ephemeralContainerStatuses`):

- Happy path: a file written into the sandbox before the upgrade still exists
  afterwards, the installer's marker file is present at the expected target path,
  the Pod is never replaced (`pod.UID` and `resourceVersion` continuity,
  `restartCount` unchanged), `spec.template` container image is unchanged, the Pod
  spec container image is unchanged, `Upgrading=Succeeded`,
  `status.completedPatchVersion` matches, `spec.upgradePolicy` is cleared, and the
  ops reaches `Completed` with `updatedReplicas == replicas`.
- Installer exits non-zero → `InstallingFailed`, the `upgrade-failed` label is
  set, the ops fail-stops at `Failed`, and the second sandbox is never touched.
- `postUpgrade` fails → `PostUpgradeFailed`, matching existing behaviour.
- Namespace targeting self-check: an installer that only performs the `-ef` guard
  and exits 0 proves targeting works on the CI runtime; the same image exiting 125
  proves the failure path reports distinctly.
- **PID namespace guard:** a sandbox whose Pod sets `shareProcessNamespace: true`
  must reach `InstallingFailed` with a message naming the field, and no ephemeral
  container may be injected. This is the misconfiguration the installer's own `-ef`
  guard cannot detect, because `pause`'s root differs from the installer's root too.
- **Supervisor requirement:** the same installer and the same `postUpgrade` hook —
  which stops and restarts the harness, as a vendor updater would — run against two
  sandboxes. Where an init is PID 1 with the harness as its child (the OpenClaw
  example's `tini`), the hook succeeds and the installed content survives the
  restart. Where the harness *is* PID 1, stopping it terminates the container
  mid-hook, so the batch must reach `PostUpgradeFailed` and the writable layer must
  be gone. This proves the loss is detected rather than silently shipped.
- **Prefix-redirect pattern:** an installer that runs npm with
  `NPM_CONFIG_PREFIX` set to `$SANDBOX_INSTALLER_TARGET_ROOT/usr/local`,
  installing a local tarball baked into the installer image. Assert from inside
  the target container that the package resolves, that `bin/<name>` is a
  *relative* symlink, and that running it uses the target's interpreter — proving
  the vendor install logic can be reused without `nsenter` and without executing
  anything from under the target rootfs.
- **Relocatable Python control:** the
  [Hermes Agent example image](#example-installer-image-hermes-agent), run twice —
  once without `--relocatable` (must exit 126 on the absolute-path assertion) and
  once with it (must succeed, and `hermes --version` must run inside the target).
  This is the only test that proves the third failure class is caught rather than
  silently shipped.
- **Negative control for the `execve` trap:** an installer that runs a binary from
  under `$SANDBOX_INSTALLER_TARGET_ROOT` and exits 0, paired with a
  `postUpgrade` that asserts a version the binary never actually installed. The
  batch must reach `PostUpgradeFailed`, proving that a foreign-`execve` no-op is
  caught rather than reported as success.
- **Volume traversal:** an installer that writes into a
  `spec.volumeClaimTemplates` mount point *through* `/proc/1/root/<mountpoint>`,
  asserting from inside the target container that the file landed on the PVC and
  not on the image layer. Path resolution through the magic symlink follows the
  target's mount tree, so this is expected to work, but it is runtime-dependent
  and it underpins the PVC durability pattern.
- Batch of two with `maxUnavailable: 1`: strictly serial, and the injected
  ephemeral container names differ per sandbox.
- `Paused` sandbox with `stateFilter: [Running, Paused]`: resumes, installs,
  re-pauses.

**Manual/runtime verification:** confirm namespace targeting on each supported
runtime before enabling the gate, since the API leaves unsupported behaviour
undefined. containerd implements it from v1.5; other runtimes must be checked
individually.

## Implementation History

- [ ] 10/23/2026: Proposal drafted.
- [ ] 10/26/2026: Clarified that namespace targeting shares PID and IPC only,
      never the mount namespace; added the "Run your own tooling, never the
      target's" contract rule, the payload-staging convention, the corresponding
      silent-no-op risk (not caught by the `-ef` guard), and two E2E controls.
      `nsenter` is documented as an operator opt-in requiring `CAP_SYS_ADMIN`,
      never a controller default.
- [ ] 10/26/2026: Researched install-location overrides across the surveyed
      harnesses and added the "Install-location overrides" section. OpenClaw
      supports a first-class prefix (`install-cli.sh --prefix`, `OPENCLAW_PREFIX`,
      and `NPM_CONFIG_PREFIX` on `update`); Codex and Gemini are reachable via
      `NPM_CONFIG_PREFIX`; Claude Code's native installer is not. The npm prefix
      redirect, its `<prefix>/lib/node_modules` + `<prefix>/bin` layout, the
      relative bin symlink and the `#!/usr/bin/env node` shebang were verified by
      an offline install rather than assumed. This replaced the earlier
      "file-level `cp -a`" contract with the stronger prefix-redirect contract.
- [ ] 10/26/2026: Added **Hermes Agent** (NousResearch) to the survey. It has
      first-class install-location flags (`--dir`, `-HermesHome`, `HERMES_HOME`)
      and a self-contained directory layout, but manages its Python environment
      with `uv`, which exposed a third silent-failure class: toolchains that bake
      absolute paths. Added the "Relocatability is the real constraint" section
      with a three-class toolchain table, reserved exit code **126** for the
      absolute-path assertion, and matching controller mapping, risk entry and
      E2E control.
- [ ] 10/27/2026: Added "Air-gapped and mirrored environments". Surveyed site-mirror
      support, version pinning and true offline install across all five harnesses:
      OpenClaw has explicit mirror variables but no offline mode; Claude Code has
      neither for its native installer (#39847 closed unimplemented); Codex and
      Gemini inherit npm's; Hermes Agent has an **open** air-gap request (#17696).
      Conclusion recorded as a design argument: an ephemeral container shares the
      Pod's network namespace, so a mirror is unreachable wherever the sandbox has
      no egress, whereas node-level image distribution already has an air-gapped
      path — which is why the payload belongs in the image. npm registry override
      and `--offline` were verified empirically. Added a matching Goal.
- [ ] 10/28/2026: Restructured. Renamed the strategy `InPlaceInstaller` →
      **`InstallerUpdate`**, and `RequestID`/`CompletedRequestID` →
      **`PatchVersion`/`CompletedPatchVersion`** (with the
      `SANDBOX_INSTALLER_PATCH_VERSION` contract variable to match). Removed the
      standalone ephemeral-container research section, keeping only the constraints
      the design depends on at the point where it depends on them. Condensed the
      harness survey to its three load-bearing conclusions — install-location
      override, air-gapped and mirrored environments, version pinning — and added a
      worked **Hermes Agent** installer image (Dockerfile, install script,
      matching `postUpgrade`) as the reference example. Replaced the code snippets
      in both Controller Changes sections with prose describing the change.
- [ ] 10/29/2026: Added **PID 1 in the target container** to the Installer
      Contract, documenting both directions of the constraint. The sandbox
      entrypoint must not be PID 1: a vendor updater that stops the service it is
      updating (`hermes update` without `--no-gateway-restart`, `openclaw update`
      without `--no-restart`) would terminate the container, and the kubelet would
      restart it with a fresh writable layer, discarding the install after the
      batch had already reported success — so an init or supervisor must be PID 1
      with the harness as its child, which is what the OpenClaw example already
      does (`examples/openclaw/README.md:106`). And the target container must own
      its PID namespace: under `shareProcessNamespace` or `hostPID`, PID 1 is
      `pause` or the node's init, so `/proc/1/root` names the wrong rootfs and the
      installer's own `-ef` guard cannot detect it. Added the matching controller
      pre-flight step, a risk entry, two E2E controls and a durability-table cause.
      Also corrected two false claims found while writing this: the repository has
      no Pod template validator rejecting `shareProcessNamespace` (the previously
      cited `pkg/webhook/utils/extravalidation/pods.go` does not exist), and the
      webhook does not reject `privileged: true` — `--allow-privileged` defaults to
      `true` (`cmd/agent-sandbox-controller/main.go:127`). Both rejections are new
      work; explicit `CAP_SYS_ADMIN` stays permitted so the documented `nsenter`
      opt-in remains expressible.
- [ ] Verify the prefix-redirect pattern end-to-end against a real OpenClaw and a
      real Hermes Agent sandbox, including whether lifecycle scripts and native
      builds survive the libc-family match requirement, and whether
      `uv venv --relocatable` is sufficient for a `HERMES_HOME` redirect.
- [ ] Confirm the minimum runtime versions that implement CRI
      `NamespaceMode_TARGET` for every runtime the project supports, and record
      them here.
- [ ] Confirm the `SANDBOX_INSTALLER_*` environment variable names as a stable
      contract.
- [ ] Open proposal PR.

## References

- Kubernetes, [Ephemeral Containers](https://kubernetes.io/docs/concepts/workloads/pods/ephemeral-containers/) — stable since v1.25.
- Kubernetes, [Share Process Namespace between Containers in a Pod](https://kubernetes.io/docs/tasks/configure-pod-container/share-process-namespace/) — `/proc/$pid/root` access, `SYS_PTRACE` requirement, and why pod-level sharing cannot be enabled on a running Pod.
- Kubernetes, [Debug Running Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-running-pod/) — `kubectl debug --target` and the runtime-support caveat.
- `k8s.io/api v0.35.0`, `core/v1/types.go:5054-5246` — `EphemeralContainerCommon` field restrictions and `TargetContainerName`.
- [KEP-277: Ephemeral Containers](https://github.com/kubernetes/enhancements/blob/master/keps/sig-node/277-ephemeral-containers/README.md).
- [KEP-495: Pod PID namespace sharing](https://github.com/kubernetes/enhancements/blob/master/keps/sig-node/495-pod-pid-namespace/README.md) — "Targeting a Specific Container's Namespace", CRI `NamespaceMode_TARGET`.
- [containerd#5008: Support for TARGET NamespaceMode in CRI implementation](https://github.com/containerd/containerd/issues/5008) — implemented; see `internal/cri/server/container_create.go`.
- [kubernetes#98362: Cannot enter the process namespace using kubectl debug with target parameter](https://github.com/kubernetes/kubernetes/issues/98362) — closed as completed.
- [OpenClaw `update` CLI](https://docs.openclaw.ai/cli/update) — channels, `--yes`, `--no-restart`, `update status --json`, `NPM_CONFIG_PREFIX` override, and container-install behaviour.
- [OpenClaw installer internals](https://docs.openclaw.ai/install/installer) — `install-cli.sh --prefix`, `OPENCLAW_PREFIX`, `OPENCLAW_HOME`, the non-interactive flags, and the mirror variables `OPENCLAW_INSTALL_NPM_REGISTRY`, `OPENCLAW_INSTALL_BUN_PIN_URL`, `OPENCLAW_INSTALL_BUN_RELEASE_BASE_URL`.
- [OpenClaw other update methods](https://docs.openclaw.ai/install/updating/update-methods) — `openclaw update` installs into a temporary npm prefix, verifies the packaged `dist` inventory, then swaps it into the real global prefix; retries once with `--omit=optional`.
- [anthropics/claude-code#39847: Complete Offline Installation](https://github.com/anthropics/claude-code/issues/39847) — requested, closed unimplemented.
- [NousResearch/hermes-agent#17696: Support offline/air-gapped installation](https://github.com/NousResearch/hermes-agent/issues/17696) — **open**; "installation cannot be completed at all" without outbound network.
- [uv settings reference](https://docs.astral.sh/uv/reference/settings/) — `UV_INDEX_URL`, `UV_NO_INDEX`, `UV_FIND_LINKS`, `UV_OFFLINE`, `UV_CACHE_DIR`, `UV_PYTHON_INSTALL_DIR`, `UV_PYTHON_DOWNLOADS`.
- [npm config](https://docs.npmjs.com/cli/v9/using-npm/config) and [npm-pack](https://docs.npmjs.com/cli/v12/commands/npm-pack/) — `prefix` and global-mode install location; `registry`/`NPM_CONFIG_REGISTRY`, `offline`, `prefer-offline`, `cache`, and tarball creation. The prefix redirect, the registry override and `--offline` (`only-if-cached` → `ENOTCACHED`) were all verified empirically.
- [OpenClaw install](https://docs.openclaw.ai/install) — the local-prefix installer as an alternative install method.
- [OpenClaw updating](https://docs.openclaw.ai/install/updating) — `openclaw-install-owner.json`, owner values, and when updates are skipped.
- [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference) — `claude install [version]` takes a version, not a path.
- [Claude Code advanced setup](https://code.claude.com/docs/en/setup) — `claude update`, `autoUpdatesChannel`.
- [openai/codex#9274: Add codex upgrade command for self-updates](https://github.com/openai/codex/issues/9274).
- [google-gemini/gemini-cli#18618: Add 'gemini update' command](https://github.com/google-gemini/gemini-cli/issues/18618) and the [Gemini CLI reference](https://geminicli.com/docs/cli/cli-reference/).
- [NousResearch/hermes-agent](https://github.com/nousresearch/hermes-agent) — "The agent that grows with you"; Python, `uv`-managed environments.
- [Hermes Agent — Installation](https://hermes-agent.nousresearch.com/docs/getting-started/installation) — `~/.hermes`, `/opt/hermes`, `$PREFIX/lib/hermes`, and the `--dir` / `-InstallDir` / `-HermesHome` location flags.
- [Hermes Agent — CLI commands](https://hermes-agent.nousresearch.com/docs/reference/cli-commands) — `hermes update`, `--check`, `--backup` (`HERMES_HOME` snapshot).
- `NousResearch/hermes-agent`, `hermes_cli/update_cmd_posix_pause.py` and `hermes_cli/update_cmd_fleet.py` — `hermes update` stops every gateway belonging to its install immediately before it first changes the checkout; `--no-gateway-restart` makes `arm_pause` return `None`, asserted by `tests/e2e/core/upgrade/git/test_hostile_pause.py::test_no_gateway_restart_stops_nothing_before_the_move`. This is the concrete case behind the PID-1 constraint.
- [astral-sh/uv#13350: Shebang lines in scripts use absolute paths](https://github.com/astral-sh/uv/issues/13350) — the non-relocatable venv failure mode.
- [astral-sh/uv#17770: Use relocatable virtual environments by default](https://github.com/astral-sh/uv/pull/17770) — preview-only, so `--relocatable` / `UV_VENV_RELOCATABLE` must be set explicitly.
- [uv CLI reference](https://docs.astral.sh/uv/reference/cli/) — `uv venv --relocatable`.
- [anthropics/claude-code#20361: claude command unavailable after npm auto-update](https://github.com/anthropics/claude-code/issues/20361) — evidence that file replacement and process restart must be separated.
- This repository: `docs/proposals/20251218-sandbox-inplace-update.md`,
  `docs/proposals/20260616-create-suo-command.md`,
  `docs/proposals/20260915-checkpoint-api-extension.md`,
  `docs/proposals/20260506-sandbox-commit.md`.

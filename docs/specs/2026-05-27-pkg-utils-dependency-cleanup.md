# pkg/utils Dependency Cleanup: Breaking Circular and Layer-Violating References

## Context

`pkg/utils` is intended as a foundational utility layer that upper-level business
packages (`pkg/sandbox-manager`, `pkg/controller`, `pkg/servers`, `pkg/proxy`) depend
on.  However, several `pkg/utils` sub-packages currently **reverse-import** the
business layer, creating architectural cycles and violating the intended dependency
direction.

The Go compiler does not flag these as errors because the cycles span different
sub-packages within `pkg/sandbox-manager` (e.g. `config` vs `infra/sandboxcr`), but
the **architectural dependency graph** contains cycles that hurt build cache efficiency,
hinder testing isolation, and make future refactoring riskier.

### Confirmed Circular / Layer-Violating Paths

| # | From | To | Violation |
|---|------|----|-----------|
| 1 | `pkg/utils/runtime` | `pkg/sandbox-manager/config` | utils → business (types used: `CSIMountOptions`, `MountConfig`, `InitRuntimeOptions`, `DefaultCSIMountConcurrency`) |
| 2 | `pkg/utils/runtime` | `pkg/sandbox-manager/consts` | utils → business (constant used: `DebugLogLevel`) |
| 3 | `pkg/utils/runtime` | `pkg/sandbox-manager/logs` | utils → business (function used: `Extend`) |
| 4 | `pkg/utils/sandbox-manager/utils.go` | `pkg/sandbox-manager/infra` | utils → business (type used: `SandboxResource`) |
| 5 | `pkg/utils/sandboxutils` | `pkg/sandbox-manager/consts` | utils → business (constant used: `RuntimePort`) |
| 6 | `pkg/utils/sidecarutils` | `pkg/sandbox-manager/consts` | utils → business (constant used: `DebugLogLevel`) |
| 7 | `pkg/utils` (root) | `pkg/sandbox-manager/consts` | utils → business (constant used: `DebugLogLevel`) |
| 8 | `pkg/utils/sandboxutils` | `pkg/proxy` | utils → business (type used: `Route`) |
| 9 | `pkg/utils/checkpoint` | `pkg/servers/e2b/models` | utils → API layer (constant used: `ExtensionKeyClaimWithCSIMount_MountConfig`) — resolved by Phase 6 (constant relocation) + Phase 10 (package dissolution) |

After the changes, the dependency direction will be strictly unidirectional:

```
api/v1alpha1 ← pkg/utils ← pkg/sandbox-manager ← cmd/
                            ← pkg/controller
                            ← pkg/servers
                            ← pkg/proxy
```

## Goals

- Eliminate all reverse imports from `pkg/utils` into `pkg/sandbox-manager`,
  `pkg/proxy`, and `pkg/servers`.
- Preserve the public API surface for all callers (import paths may change, but
  function signatures and types remain identical).
- Ensure all existing tests continue to pass after each phase.
- Each phase is independently mergeable: the codebase compiles and all `pkg/`
  unit tests pass after every phase.

## Non-Goals

- Do not refactor function signatures or behavioral logic.
- Do not move packages that have clean dependency graphs.
- Do not rename packages beyond what is necessary for the move.
- Do not change the `cmd/` or `test/` directories.

---

## Execution Phases

### Phase 1: Relocate `DebugLogLevel` and `RuntimePort` constants

**Problem**: `DebugLogLevel` is defined in `pkg/sandbox-manager/consts` but consumed
by 4 `pkg/utils` packages (root, `runtime`, `sidecarutils`, `sandbox-manager/test_utils`).
`RuntimePort` is defined in `pkg/sandbox-manager/consts` but consumed by
`pkg/utils/sandboxutils`.  This makes `pkg/utils` depend on the business layer.

**Steps**:

1. Add `DebugLogLevel = 5` and `RuntimePort = 49983` to `pkg/utils/constant.go`.

2. In `pkg/sandbox-manager/consts/consts.go`:
   - Replace the local `DebugLogLevel` and `RuntimePort` declarations with re-exports
     from `pkg/utils`:
     ```go
     const (
         // Re-export from pkg/utils for backward compatibility within
         // pkg/sandbox-manager. New code should import pkg/utils directly.
         DebugLogLevel = utils.DebugLogLevel
         RuntimePort   = utils.RuntimePort
     )
     ```
   - Add `"github.com/openkruise/agents/pkg/utils"` to the import block.

3. Update all `pkg/utils` internal consumers to use the local constant instead of
   `consts.DebugLogLevel` / `consts.RuntimePort`:
   - `pkg/utils/utils.go`: remove `pkg/sandbox-manager/consts` import, use local `DebugLogLevel`.
   - `pkg/utils/runtime/runtime.go`: remove `pkg/sandbox-manager/consts` import, use `utils.DebugLogLevel`.
   - `pkg/utils/sidecarutils/sidecar_config_inject.go`: remove `pkg/sandbox-manager/consts` import, use `utils.DebugLogLevel`.
   - `pkg/utils/sandboxutils/utils.go`: remove `pkg/sandbox-manager/consts` import, use `utils.RuntimePort`.
   - `pkg/utils/sandbox-manager/test_utils.go`: remove `pkg/sandbox-manager/consts` import, use `utils.DebugLogLevel`.

4. Run `go build ./pkg/...` and `go test ./pkg/utils/... ./pkg/sandbox-manager/...` to verify.

**Files changed**: ~7 files, all within `pkg/utils` and `pkg/sandbox-manager/consts`.

**Backward compatibility**: All existing callers of `consts.DebugLogLevel` and
`consts.RuntimePort` continue to compile because `pkg/sandbox-manager/consts`
re-exports the values. No external breakage.

---

### Phase 2: Relocate `logs.Extend` / `NewContext` / `NewContextFrom` to `pkg/utils/logs`

**Problem**: `pkg/sandbox-manager/logs` defines three context helpers
(`Extend`, `NewContext`, `NewContextFrom`) that are used by 11 packages across the
project, including 2 `pkg/utils` sub-packages (`runtime`, `sandbox-manager/test_utils`).
This forces utils to depend on the business layer.

**Steps**:

1. Create `pkg/utils/logs/context.go` with the content of
   `pkg/sandbox-manager/logs/context.go`, changing the package name from `logs` to `logs`
   (same name, new location).

2. Create `pkg/utils/logs/context_test.go` by copying
   `pkg/sandbox-manager/logs/context_test.go` and adjusting the package name.

3. In `pkg/sandbox-manager/logs/context.go`, replace the function bodies with
   re-exports that delegate to `pkg/utils/logs`:
   ```go
   package logs

   import (
       "context"
       utilslogs "github.com/openkruise/agents/pkg/utils/logs"
   )

   // Re-export for backward compatibility within pkg/sandbox-manager.
   // New code outside pkg/sandbox-manager should import pkg/utils/logs directly.
   func NewContext(keysAndValues ...any) context.Context {
       return utilslogs.NewContext(keysAndValues...)
   }

   func NewContextFrom(parent context.Context, keysAndValues ...any) context.Context {
       return utilslogs.NewContextFrom(parent, keysAndValues...)
   }

   func Extend(ctx context.Context, keysAndValues ...any) context.Context {
       return utilslogs.Extend(ctx, keysAndValues...)
   }
   ```

4. Update the 2 `pkg/utils` internal consumers:
   - `pkg/utils/runtime/runtime.go`: change `"github.com/openkruise/agents/pkg/sandbox-manager/logs"` to `"github.com/openkruise/agents/pkg/utils/logs"`.
   - `pkg/utils/runtime/csi.go`: same change.
   - `pkg/utils/sandbox-manager/test_utils.go`: same change.

5. Update the remaining 9 external consumers (all in `pkg/sandbox-manager` or
   `pkg/servers` or `pkg/cache` or `pkg/peers`). These can keep importing
   `pkg/sandbox-manager/logs` because it still works via re-export. Optionally,
   migrate them to `pkg/utils/logs` in a follow-up cleanup pass.

6. Run `go build ./pkg/...` and `go test ./pkg/utils/logs/... ./pkg/sandbox-manager/logs/... ./pkg/utils/runtime/...` to verify.

**Files changed**: ~15 files (1 new, 1 copy, 2 modifications in utils, 1 modification in sandbox-manager/logs, up to 10 optional caller updates).

---

### Phase 3: Relocate CSI/InitRuntime config types to `pkg/utils/runtime/config`

**Problem**: `pkg/utils/runtime` imports `pkg/sandbox-manager/config` for the types
`CSIMountOptions`, `MountConfig`, `InitRuntimeOptions`, and the constant
`DefaultCSIMountConcurrency`.  Meanwhile `pkg/sandbox-manager/infra/sandboxcr`
imports `pkg/utils/runtime`, forming an architectural cycle.

**Steps**:

1. Create `pkg/utils/runtime/config/types.go` containing:
   - `InitRuntimeOptions` struct (move from `pkg/sandbox-manager/config/infra.go`)
   - `CSIMountOptions` struct (move from `pkg/sandbox-manager/config/infra.go`)
   - `MountConfig` struct (move from `pkg/sandbox-manager/config/infra.go`)
   - `DefaultCSIMountConcurrency` constant (move from `pkg/sandbox-manager/config/infra.go`)
   - `NewDefaultAccessToken` function (move from `pkg/sandbox-manager/config/infra.go`)
   - Apache 2.0 license header.

2. Create `pkg/utils/runtime/config/types_test.go` by moving the relevant test
   (`TestDefaultCSIMountConcurrency`) from `pkg/sandbox-manager/config/infra_test.go`.

3. In `pkg/sandbox-manager/config/infra.go`, replace the moved definitions with
   re-exports:
   ```go
   package config

   import (
       runtimeconfig "github.com/openkruise/agents/pkg/utils/runtime/config"
   )

   // Re-exported types for backward compatibility.
   // New code should import pkg/utils/runtime/config directly.
   type InitRuntimeOptions = runtimeconfig.InitRuntimeOptions
   type CSIMountOptions = runtimeconfig.CSIMountOptions
   type MountConfig = runtimeconfig.MountConfig

   const DefaultCSIMountConcurrency = runtimeconfig.DefaultCSIMountConcurrency

   func NewDefaultAccessToken() string { return runtimeconfig.NewDefaultAccessToken() }
   ```

4. Update `pkg/utils/runtime/runtime.go` and `pkg/utils/runtime/csi.go`:
   - Remove `"github.com/openkruise/agents/pkg/sandbox-manager/config"` import.
   - Add `"github.com/openkruise/agents/pkg/utils/runtime/config"` import.
   - Replace `config.CSIMountOptions` → `config.CSIMountOptions` (same short name,
     different package path — the `config` import alias now resolves to `pkg/utils/runtime/config`).

5. All other consumers of `pkg/sandbox-manager/config.{CSIMountOptions,MountConfig,InitRuntimeOptions}`
   (14 files) continue to compile unchanged because `pkg/sandbox-manager/config`
   re-exports via type aliases.

6. Run `go build ./pkg/...` and `go test ./pkg/utils/runtime/... ./pkg/sandbox-manager/config/...` to verify.

**Files changed**: ~4 files in utils (2 new), 2 files modified in utils/runtime,
1 file modified in sandbox-manager/config.

**Note**: `pkg/sandbox-manager/config/infra.go` also contains `SecurityTokenOptions`,
`InplaceUpdateOptions`, and `InplaceUpdateResourcesOptions` — these stay in
`pkg/sandbox-manager/config` because they are not used by `pkg/utils`.

---

### Phase 4: Relocate `CalculateResourceFromContainers` and `SandboxResource`

**Problem**: `pkg/utils/sandbox-manager/utils.go` defines
`CalculateResourceFromContainers` which returns `infra.SandboxResource`.  This
forces `pkg/utils/sandbox-manager` to import `pkg/sandbox-manager/infra`, creating
an architectural cycle with `pkg/sandbox-manager/infra/sandboxcr` (which imports
`pkg/utils/sandbox-manager`).

**Analysis**: `SandboxResource` is already defined in `pkg/sandbox-manager/infra/interface.go`.
`CalculateResourceFromContainers` is called from:
- `pkg/sandbox-manager/infra/sandboxcr/sandbox.go` (business layer)
- `pkg/servers/e2b/templates.go` (API layer)

Both callers already import `pkg/sandbox-manager/infra`, so moving the function there
does not add new dependencies.

**Steps**:

1. Move `CalculateResourceFromContainers` from `pkg/utils/sandbox-manager/utils.go`
   to `pkg/sandbox-manager/infra/interface.go` (next to the `SandboxResource` type
   it returns).

2. Move the corresponding test from `pkg/utils/sandbox-manager/utils_test.go` to
   `pkg/sandbox-manager/infra/interface_test.go`.

3. Update callers:
   - `pkg/sandbox-manager/infra/sandboxcr/sandbox.go`: remove
     `"github.com/openkruise/agents/pkg/utils/sandbox-manager"` import if it was
     the only symbol used; otherwise keep the import.
   - `pkg/servers/e2b/templates.go`: change from
     `sandboxmanager.CalculateResourceFromContainers` to
     `infra.CalculateResourceFromContainers` (add `infra` import, remove or keep
     `sandbox-manager` import depending on other symbols used).

4. Remove `pkg/utils/sandbox-manager/utils.go` if it becomes empty (after Phase 2
   already removed `test_utils.go`'s dependency on `consts`). If other symbols
   remain, keep the file but remove the `pkg/sandbox-manager/infra` import.

5. Run `go build ./pkg/...` and `go test ./pkg/utils/sandbox-manager/... ./pkg/sandbox-manager/infra/... ./pkg/servers/e2b/...` to verify.

**Files changed**: ~4 files.

---

### Phase 5: Extract `proxy.Route` into `pkg/proxy/types`

**Problem**: `pkg/utils/sandboxutils` imports `pkg/proxy` for the `Route` type.
While not a circular dependency (`pkg/proxy` only imports `pkg/utils/expectations`),
it is a layer violation: utils should not depend on a business package.

**Steps**:

1. Create `pkg/proxy/types/types.go` containing only the `Route` struct definition
   (move from `pkg/proxy/routes.go` or wherever it is currently defined).

2. In `pkg/proxy/routes.go` (and any other files in `pkg/proxy` that define/use `Route`):
   - Replace the local `Route` definition with a type alias:
     ```go
     type Route = types.Route
     ```
   - Import `"github.com/openkruise/agents/pkg/proxy/types"`.

3. Update `pkg/utils/sandboxutils/utils.go`:
   - Change `"github.com/openkruise/agents/pkg/proxy"` to
     `"github.com/openkruise/agents/pkg/proxy/types"`.
   - `Route` references remain the same.

4. All other consumers of `proxy.Route` (12 files) continue to compile via the
   type alias in `pkg/proxy`.

5. Run `go build ./pkg/...` and `go test ./pkg/utils/sandboxutils/... ./pkg/proxy/...` to verify.

**Files changed**: ~4 files (1 new, 3 modified).

---

### Phase 6: Relocate `ExtensionKeyClaimWithCSIMount_MountConfig` constant

**Problem**: `pkg/utils/checkpoint` imports `pkg/servers/e2b/models` for a single
annotation key constant.  This is a layer violation: utils should not depend on the
API layer.

**Steps**:

1. Add `ExtensionKeyClaimWithCSIMount_MountConfig` to `pkg/utils/constant.go` (it is
   an annotation key constant that belongs in the shared constants package):
   ```go
   ExtensionKeyClaimWithCSIMount_MountConfig = "agents.kruise.io/csi-mount-config"
   ```

2. In `pkg/servers/e2b/models`, replace the local definition with a re-export:
   ```go
   const ExtensionKeyClaimWithCSIMount_MountConfig = utils.ExtensionKeyClaimWithCSIMount_MountConfig
   ```

3. In `pkg/utils/checkpoint/utils.go`:
   - Remove `"github.com/openkruise/agents/pkg/servers/e2b/models"` import.
   - Replace `models.ExtensionKeyClaimWithCSIMount_MountConfig` with
     `utils.ExtensionKeyClaimWithCSIMount_MountConfig`.

4. Update all other consumers of `models.ExtensionKeyClaimWithCSIMount_MountConfig`
   (10 additional files). These can continue using the `models` re-export, or be
   migrated to `utils` in a follow-up pass.

5. Run `go build ./pkg/...` and `go test ./pkg/utils/checkpoint/... ./pkg/servers/e2b/...` to verify.

**Files changed**: ~4 files.

---

## Dependency Graph After Phases 1–6

```
pkg/utils/constant.go          ← no internal pkg imports
pkg/utils/logs/                ← no internal pkg imports
pkg/utils/runtime/config/      ← no internal pkg imports (only api/v1alpha1, identity)
pkg/utils/runtime/             ← pkg/utils, pkg/utils/logs, pkg/utils/runtime/config, pkg/utils/csiutils, pkg/utils/sandboxutils
pkg/utils/sandbox-manager/     ← pkg/utils/expectations, pkg/utils/sandboxutils (no sandbox-manager imports)
pkg/utils/sandboxutils/        ← pkg/proxy/types, pkg/utils
pkg/utils/sidecarutils/        ← pkg/utils, pkg/utils/sidecarutils/traffic-proxy, pkg/utils/webhookutils
pkg/utils/checkpoint/          ← api/v1alpha1, pkg/utils (layer violation resolved in Phase 6; package dissolved in Phase 10)
pkg/proxy/types/               ← no internal pkg imports
```

No `pkg/utils/*` package imports `pkg/sandbox-manager`, `pkg/proxy`, or
`pkg/servers`.  All cycles are broken.

---

## Phase 7: Merge `pkg/utils/sandbox-manager/expectationutils` into `pkg/utils/expectations`

**Motivation**: After phases 1–6, `pkg/utils/sandbox-manager` still contains two
sub-packages (`expectationutils` and `proxyutils`) plus three standalone files
(`e2b.go`, `pagination.go`, `utils.go`).  The package name `sandbox-manager` inside
`pkg/utils` is misleading — it suggests a relationship with the business package
`pkg/sandbox-manager`, but after the cycle-breaking phases the two have no structural
connection.  This phase consolidates `expectationutils` into its natural parent
`pkg/utils/expectations`.

### Current state of `expectationutils`

`pkg/utils/sandbox-manager/expectationutils/utils.go` contains a **singleton**
`resourceVersionExpectation` variable (package-level `var`) and five thin wrapper
functions that delegate to it:

| Function | Delegates to |
|----------|-------------|
| `ResourceVersionExpectationObserve(obj)` | `resourceVersionExpectation.Observe(obj)` |
| `ResourceVersionExpectationExpect(obj)` | `resourceVersionExpectation.Expect(obj)` |
| `ResourceVersionExpectationDelete(obj)` | `resourceVersionExpectation.Delete(obj)` |
| `ResourceVersionExpectationSatisfied(obj)` | `resourceVersionExpectation.IsSatisfied(obj)` + timeout check |

The underlying type `ResourceVersionExpectation` and its implementation
`realResourceVersionExpectation` are already in `pkg/utils/expectations`.  The
`expectationutils` package is purely a singleton holder + convenience wrapper — it
adds no new types or logic.

### Consumers of `expectationutils`

| Package | Files | Symbols used |
|---------|-------|-------------|
| `pkg/sandbox-manager/infra/sandboxcr` | `claim.go`, `sandbox.go`, `infra.go` | Expect, Satisfied, Delete |
| `pkg/cache/controllers` | `cache_controllers.go` | Expect |

Total: 5 production files + 4 test files.

### Merge feasibility

**Can it merge without creating cycles?** Yes.  `pkg/utils/expectations` currently
has no internal `pkg/` imports (pure stdlib + k8s apimachinery).  Adding the singleton
and its wrapper functions there does not introduce any new dependency.  All current
consumers of `expectationutils` already import `pkg/utils/expectations` or can safely
add it alongside their existing imports.

**Why merge instead of keep separate?**
- The singleton pattern is a project convention (one global `resourceVersionExpectation`
  shared across controller and manager).  Putting it in the same package as the
  underlying type makes the relationship explicit.
- Eliminates a confusingly-named sub-package (`sandbox-manager` inside `utils`).
- Reduces the import surface: callers only need `pkg/utils/expectations` instead of
  both `pkg/utils/expectations` (for ScaleExpectations) and
  `pkg/utils/sandbox-manager/expectationutils` (for ResourceVersionExpectation).

### Steps

1. Move the `resourceVersionExpectation` singleton variable and the five wrapper
   functions from `pkg/utils/sandbox-manager/expectationutils/utils.go` into
   `pkg/utils/expectations/resource_version_expectation.go` (a new file in the
   existing package).  This keeps the `ResourceVersionExpectation` interface and
   the `realResourceVersionExpectation` implementation in the same file they already
   occupy, while the singleton + wrappers live in a sibling file within the same
   package.

2. Move the test from `pkg/utils/sandbox-manager/expectationutils/utils_test.go`
   (if it exists) into `pkg/utils/expectations/resource_version_expectation_test.go`.

3. Add a re-export file `pkg/utils/sandbox-manager/expectationutils/reexport.go`
   for backward compatibility:
   ```go
   package expectationutils

   import "github.com/openkruise/agents/pkg/utils/expectations"

   // Re-exported for backward compatibility.
   // New code should import pkg/utils/expectations directly.
   var ResourceVersionExpectationObserve = expectations.ResourceVersionExpectationObserve
   // ... etc for all 5 functions
   ```

   Alternatively, use function wrappers (not variable aliases) since these are
   functions, not variables:
   ```go
   func ResourceVersionExpectationObserve(obj metav1.Object) {
       expectations.ResourceVersionExpectationObserve(obj)
   }
   ```

4. Update the 5 production consumers to import
   `pkg/utils/expectations` directly:
   - `pkg/sandbox-manager/infra/sandboxcr/claim.go`: replace `expectationutils` import
     with `expectations`, update call sites (`expectationutils.X` → `expectations.X`).
   - `pkg/sandbox-manager/infra/sandboxcr/sandbox.go`: same.
   - `pkg/sandbox-manager/infra/sandboxcr/infra.go`: same.
   - `pkg/cache/controllers/cache_controllers.go`: same.

5. Delete `pkg/utils/sandbox-manager/expectationutils/` directory once all callers
   have been migrated (or keep the re-export file for a transitional period).

6. Run `go build ./pkg/...` and `go test ./pkg/utils/expectations/... ./pkg/sandbox-manager/infra/... ./pkg/cache/...` to verify.

**Files changed**: ~8 files (1 new in expectations, 4 consumer updates, 1 optional re-export, 1 deletion).

---

## Phase 8: Move `pkg/utils/sandbox-manager/proxyutils` to `pkg/utils/proxyutils`

**Motivation**: `proxyutils` contains HTTP proxy helper functions that are used by
multiple packages.  Its current location under `pkg/utils/sandbox-manager/` is
misleading — the `sandbox-manager` sub-package name implies a dependency on the
business package `pkg/sandbox-manager` that does not actually exist (after phases
1–6 break all reverse imports).  Moving it to `pkg/utils/proxyutils` (a top-level
sub-package under utils) eliminates the confusing nesting while keeping the package
intact as a coherent unit.

### Current state of `proxyutils`

| File | Exports | Dependencies |
|------|---------|-------------|
| `utils.go` | `ProxyRequest(r *http.Request) (*http.Response, error)` | stdlib only (net/http, klog) |
| `default.go` | `DefaultGetRouteFunc`, `DefaultRequestFunc` (package-level vars) | `pkg/utils/sandboxutils`, `api/v1alpha1`, stdlib |

`ProxyRequest` is a thin `http.DefaultClient.Do` wrapper with error checking.
`DefaultRequestFunc` builds an HTTP request from a `*Sandbox` object and delegates to
`ProxyRequest`.  `DefaultGetRouteFunc` delegates to `sandboxutils.GetRouteFromSandbox`.

### Consumers of `proxyutils`

| Package | Files | Symbols used |
|---------|-------|-------------|
| `pkg/utils/runtime` | `runtime.go` | `ProxyRequest` |
| `pkg/sandbox-manager/infra/sandboxcr` | `infra.go`, `sandbox.go` | `DefaultGetRouteFunc`, `DefaultRequestFunc` |
| `pkg/sandbox-gateway/controller` | `gateway_controller.go` | `DefaultGetRouteFunc` |
| `pkg/servers/e2b` (test only) | `services_test.go` | `DefaultRequestFunc` |

Total: 5 production files + 3 test files.

### Why a simple rename (not a split or merge into `pkg/proxy`)

Two alternative approaches were considered and rejected:

1. **Merge into `pkg/proxy`**: Would introduce a new layer violation
   (`pkg/utils/runtime → pkg/proxy`), because `pkg/utils/runtime` currently calls
   `proxyutils.ProxyRequest` and would then need to import the business package
   `pkg/proxy`.  This is worse than the current situation.

2. **Split across `pkg/utils/runtime/` + `pkg/utils/sandboxutils/`** (previously
   Option A in this spec): While this produces the most "normalized" layering, it
   has downsides:
   - Splits a cohesive unit (HTTP proxy helpers) across two packages.
   - Introduces a new internal dependency (`pkg/utils/sandboxutils → pkg/utils/runtime`
     via `requestSandbox` calling `ProxyRequest`).
   - Larger diff: function relocations, new files, call-site renames.

A simple rename to `pkg/utils/proxyutils` is preferred because:

1. **Minimal diff**: Only the import path changes; no code is split, merged, or
   relocated between packages.  This reduces the risk of introducing bugs.
2. **Preserves package coherence**: `ProxyRequest`, `DefaultRequestFunc`, and
   `DefaultGetRouteFunc` form a cohesive unit (HTTP proxy helpers).  Keeping them
   together makes the code easier to navigate.
3. **No new inter-package dependencies**: Splitting would introduce
   `pkg/utils/sandboxutils → pkg/utils/runtime` (via `requestSandbox` calling
   `ProxyRequest`), creating a new internal dependency.  The rename avoids this.
4. **Straightforward rollback**: A single commit changes only import paths.

### Steps

1. Create `pkg/utils/proxyutils/` directory and move all files from
   `pkg/utils/sandbox-manager/proxyutils/` into it:
   - `utils.go` → `pkg/utils/proxyutils/utils.go` (same package name, no code
     change needed).
   - `default.go` → `pkg/utils/proxyutils/default.go` (same).
   - `default_test.go` → `pkg/utils/proxyutils/default_test.go` (same).
   - Internal import paths within the moved files are unchanged
     (`pkg/utils/sandboxutils` remains as-is — it is a sibling package at the
     same level).

2. Update all consumers to use the new import path:
   - `pkg/utils/runtime/runtime.go`: change
     `"github.com/openkruise/agents/pkg/utils/sandbox-manager/proxyutils"` to
     `"github.com/openkruise/agents/pkg/utils/proxyutils"`.
   - `pkg/sandbox-manager/infra/sandboxcr/infra.go`: same import path change.
   - `pkg/sandbox-manager/infra/sandboxcr/sandbox.go`: same.
   - `pkg/sandbox-gateway/controller/gateway_controller.go`: same.
   - `pkg/servers/e2b/services_test.go`: same.
   - All other files importing the old path.

   No function call changes are needed — the exported symbol names remain
   `proxyutils.ProxyRequest`, `proxyutils.DefaultGetRouteFunc`, etc.

3. Delete `pkg/utils/sandbox-manager/proxyutils/` directory.

4. Run `go build ./pkg/...` and
   `go test ./pkg/utils/proxyutils/... ./pkg/utils/runtime/... ./pkg/sandbox-manager/infra/... ./pkg/sandbox-gateway/...` to verify.

**Files changed**: ~8 files (0 new logic, 5 consumer import updates, 1 directory
rename, 2 moved files).

---

## Phase 9: Dissolve `pkg/utils/sandbox-manager` package entirely

**Motivation**: After phases 4, 7, and 8, `pkg/utils/sandbox-manager` contains only:

| File | Exports | Remaining dependencies |
|------|---------|----------------------|
| `e2b.go` | `GetSandboxAddress` | stdlib only (`fmt`) |
| `pagination.go` | `Paginator[T]` | stdlib only (`sort`) |
| `utils.go` | `LockSandbox`, `NewLockString` | `api/v1alpha1`, `client` (after Phase 4 removes `infra` import) |
| `test_utils.go` | `InitLogOutput` | `pkg/utils` (after Phase 1 removes `consts` import) |

None of these have any dependency on `pkg/sandbox-manager`.  The package name
`sandbox-manager` is now misleading — it implies a relationship that no longer
exists.  This phase relocates each remaining file to its natural home and deletes
the `pkg/utils/sandbox-manager` package.

### Destination analysis for each export

| Export | Natural destination | Reasoning |
|--------|--------------------|-----------|
| `GetSandboxAddress` | `pkg/servers/e2b` (or `pkg/utils`) | Only called from `pkg/servers/e2b/services.go`. It formats a WebSocket address string — an E2B-specific concern. Move it to the E2B server package, or to `pkg/utils` if considered general-purpose. |
| `Paginator[T]` | `pkg/utils/pagination` (new sub-package) | A generic pagination utility with no sandbox-specific logic. Used by `pkg/sandbox-manager/api.go` and `pkg/servers/e2b/list.go`. Putting it in `pkg/utils/pagination` makes it discoverable as a shared utility. |
| `LockSandbox` | `pkg/utils` (root) | Operates on generic `client.Object` annotations. Already in the spirit of `pkg/utils/utils.go` (which has `SetSandboxCondition`, `UpdateFinalizer`, etc.). |
| `NewLockString` | `pkg/utils` (root) | Generates a UUID string. Already in the spirit of `pkg/utils/utils.go`. |
| `InitLogOutput` | `pkg/utils/testutils` (new sub-package) | A test helper that sets up klog. Used by 20+ test files across the project. Its own comment says "will be renamed to InitTestEnv in the future and will be moved to test/utils". Creating `pkg/utils/testutils` fulfills this plan. |

### Steps

1. Create `pkg/utils/pagination/pagination.go` with the content of
   `pkg/utils/sandbox-manager/pagination.go` (change package name from `utils` to
   `pagination`).  Create `pkg/utils/pagination/pagination_test.go` from the existing
   test.

2. Move `LockSandbox` and `NewLockString` from
   `pkg/utils/sandbox-manager/utils.go` into `pkg/utils/utils.go` (root package).
   These are 2 short functions that fit naturally alongside the existing sandbox
   helpers in that file.

3. Create `pkg/utils/testutils/init.go` with the content of
   `pkg/utils/sandbox-manager/test_utils.go` (change package name from `utils` to
   `testutils`).  Remove the `consts` import (already done in Phase 1) and use
   `utils.DebugLogLevel` instead.

4. Move `GetSandboxAddress` from `pkg/utils/sandbox-manager/e2b.go` into
   `pkg/servers/e2b/address.go` (new file, E2B-specific).  This function only has
   one production caller (`services.go`) and is E2B-domain logic (WebSocket URL
   formatting).  Alternatively, if it is considered general-purpose, move it to
   `pkg/utils/utils.go`.

5. Update all 18 importers of `pkg/utils/sandbox-manager`:
   - `pkg/sandbox-manager/api.go`: change `utils.Paginator` import to
     `pagination.Paginator`, `utils.InitLogOutput` to `testutils.InitLogOutput`.
   - `pkg/sandbox-manager/api_test.go`: same pattern.
   - `pkg/servers/e2b/list.go`: `utils.Paginator` → `pagination.Paginator`.
   - `pkg/servers/e2b/services.go`: remove `managerutils.GetSandboxAddress`,
     call local `GetSandboxAddress` (now in same package).
   - `pkg/servers/e2b/templates.go`: `managerutils.LockSandbox` → `utils.LockSandbox`,
     `managerutils.CalculateResourceFromContainers` → `infra.CalculateResourceFromContainers`
     (if Phase 4 already moved it).
   - `pkg/controller/sandboxset/rolling_update.go`: `managerutils.LockSandbox` →
     `utils.LockSandbox`.
   - `pkg/controller/sandboxset/sandboxset_controller.go`: same.
   - `pkg/sandbox-manager/infra/sandboxcr/claim.go`: `sandboxManagerUtils.LockSandbox` →
     `utils.LockSandbox`, `sandboxManagerUtils.NewLockString` → `utils.NewLockString`.
   - `pkg/sandbox-manager/infra/sandboxcr/sandbox.go`: remove import if only
     `LockSandbox`/`NewLockString` were used (now in `pkg/utils`).
   - All test files (20+): `utils.InitLogOutput` → `testutils.InitLogOutput`.

6. Delete the entire `pkg/utils/sandbox-manager/` directory (including any re-export
   stubs from phases 7/8 if those were kept transitional).

7. Run `go build ./pkg/...` and `go test ./pkg/utils/... ./pkg/sandbox-manager/... ./pkg/servers/e2b/... ./pkg/controller/...` to verify.

**Files changed**: ~25 files (3 new, 18 consumer updates, 1 directory deletion).

---

## Phase 10: Dissolve `pkg/utils/checkpoint` package

**Motivation**: After Phase 6 relocates `ExtensionKeyClaimWithCSIMount_MountConfig` to
`pkg/utils/constant.go`, `pkg/utils/checkpoint` no longer has any layer-violating
import (its only remaining imports are `api/v1alpha1` and `pkg/utils`).  However, the
package itself should be eliminated because:

1. It contains only 2 functions and 1 unexported variable — too small to justify a
   standalone package.
2. Both functions are clone-specific business logic (propagating/restoring annotations
   between Sandbox and Checkpoint during clone operations), not general-purpose
   utilities.
3. There is only **one** production consumer (`pkg/sandbox-manager/infra/sandboxcr/clone.go`),
   making the indirection through `pkg/utils` unnecessary.

### Current state of `pkg/utils/checkpoint`

| File | Exports | Dependencies |
|------|---------|-------------|
| `utils.go` | `PropagateAnnotationsToCheckpoint`, `RestoreAnnotationsFromCheckpoint`, `necessaryAnnotationKeys` (unexported) | `api/v1alpha1`, `pkg/servers/e2b/models` (layer violation — removed in Phase 6) |
| `utils_test.go` | Tests for both functions | `api/v1alpha1`, `pkg/servers/e2b/models` |

After Phase 6, the `models` import in `utils.go` is replaced by `pkg/utils`, so the
layer violation is already resolved.  This phase focuses on eliminating the package
itself.

### Consumer analysis

| Package | File | Symbols used |
|---------|------|-------------|
| `pkg/sandbox-manager/infra/sandboxcr` | `clone.go` (lines 241, 377) | `RestoreAnnotationsFromCheckpoint`, `PropagateAnnotationsToCheckpoint` |

Total: 1 production file.  No other package in the codebase calls these functions.

### Destination analysis

Both functions operate on `v1alpha1.Sandbox` and `v1alpha1.Checkpoint` objects to
propagate/restore specific annotation keys during clone operations.  This is
clone-specific business logic that belongs in the clone implementation itself —
`pkg/sandbox-manager/infra/sandboxcr/` — rather than in a shared utility package.

Moving the functions into the consumer package:
- Eliminates an unnecessary layer of indirection.
- Co-locates the annotation propagation logic with the clone logic that uses it,
  making the code easier to understand and maintain.
- Does not introduce any new import or dependency, since `pkg/sandbox-manager/infra/sandboxcr`
  already imports `api/v1alpha1` and `pkg/utils`.

### Steps

1. Create `pkg/sandbox-manager/infra/sandboxcr/checkpoint_annotations.go` containing:
   - The `necessaryAnnotationKeys` variable (change from unexported `var` to
     unexported `var` in the new package — same visibility).
   - `PropagateAnnotationsToCheckpoint` function (identical implementation).
   - `RestoreAnnotationsFromCheckpoint` function (identical implementation).
   - Import `pkg/utils` for `utils.ExtensionKeyClaimWithCSIMount_MountConfig` (after
     Phase 6, the constant is already in `pkg/utils`).

2. Move the tests from `pkg/utils/checkpoint/utils_test.go` into
   `pkg/sandbox-manager/infra/sandboxcr/checkpoint_annotations_test.go`:
   - Change package name from `checkpoint` to `sandboxcr`.
   - Replace `models.ExtensionKeyClaimWithCSIMount_MountConfig` with
     `utils.ExtensionKeyClaimWithCSIMount_MountConfig` (consistent with Phase 6).
   - Replace references to `necessaryAnnotationKeys` (now in same package, no import
     change needed).
   - Update the function calls from `PropagateAnnotationsToCheckpoint` /
     `RestoreAnnotationsFromCheckpoint` to the same names (same package).

3. Update the sole production consumer:
   - `pkg/sandbox-manager/infra/sandboxcr/clone.go`: remove the
     `"github.com/openkruise/agents/pkg/utils/checkpoint"` import and the
     `checkpointUtils` alias.  Change:
     - `checkpointUtils.RestoreAnnotationsFromCheckpoint(cp, sbx.Sandbox)` →
       `RestoreAnnotationsFromCheckpoint(cp, sbx.Sandbox)`
     - `checkpointUtils.PropagateAnnotationsToCheckpoint(sbx, cp)` →
       `PropagateAnnotationsToCheckpoint(sbx, cp)`

4. Delete the `pkg/utils/checkpoint/` directory entirely.

5. Run `go build ./pkg/...` and
   `go test ./pkg/sandbox-manager/infra/sandboxcr/...` to verify.

**Prerequisite**: Phase 6 must be completed first (so that
`ExtensionKeyClaimWithCSIMount_MountConfig` is available in `pkg/utils`).

**Files changed**: ~4 files (1 new, 1 consumer update, 1 test move, 1 directory deletion).

---

## Phase 11: Dissolve `pkg/utils/sandboxutils` package

**Motivation**: After Phase 5 extracts `proxy.Route` into `pkg/proxy/types`, the only
remaining reason for `pkg/utils/sandboxutils` to exist as a separate package is that it
imports `pkg/proxy/types` (for `GetRouteFromSandbox`'s return type) and
`pkg/sandbox-manager/consts` (for `RuntimePort` in `GetRuntimeURL` — resolved in
Phase 1).  However, `pkg/utils/sandboxutils` contains many general-purpose sandbox
helper functions (`GetSandboxState`, `IsControlledBySandboxSet`, `GetSandboxID`, etc.)
that have no dependency on `pkg/proxy/types` or `pkg/sandbox-manager/consts`.  The
two proxy-related functions (`GetRuntimeURL`, `GetRouteFromSandbox`) can live in
`pkg/utils/proxyutils`, and the rest belong in `pkg/utils` (root) alongside the
existing sandbox helpers (`SetSandboxCondition`, `UpdateFinalizer`, etc.).

Dissolving this package:
- Eliminates an unnecessary sub-package — most of its contents are general sandbox
  utilities that belong in `pkg/utils` root.
- Co-locates `GetRuntimeURL` and `GetRouteFromSandbox` with the other proxy helpers
  in `pkg/utils/proxyutils`, forming a coherent "proxy/Routing" package.
- Removes the `sandboxutils → pkg/proxy/types` dependency from the utils root,
  making the dependency graph cleaner.

### Current state of `pkg/utils/sandboxutils`

| Export | Dependencies | Category |
|--------|-------------|----------|
| `GetRuntimeURL` | `api/v1alpha1`, `pkg/sandbox-manager/consts` (Phase 1: `pkg/utils`), `GetRouteFromSandbox` (internal) | Proxy/Routing |
| `GetRouteFromSandbox` | `api/v1alpha1`, `pkg/proxy` (Phase 5: `pkg/proxy/types`), `GetSandboxState`, `GetSandboxID` (internal) | Proxy/Routing |
| `GetSandboxState` | `api/v1alpha1`, `time`, `IsSandboxReady`, `IsControlledBySandboxSet` (internal) | State inspection |
| `IsControlledBySandboxSet` | `api/v1alpha1`, `metav1` | State inspection |
| `GetSandboxID` | `api/v1alpha1` | Identification |
| `ValidateNamespaceForSandboxID` | `fmt`, `strings` | Identification |
| `GetAccessToken` | `api/v1alpha1`, `metav1` | Configuration |
| `IsSandboxReady` | `api/v1alpha1`, `metav1`, `pkg/utils` (root) | State inspection |
| `IsSandboxPausable` | `api/v1alpha1`, `GetSandboxState`, `IsControlledBySandboxSet` (internal) | State inspection |
| `IsSandboxResumable` | `api/v1alpha1`, `pkg/utils` (root) | State inspection |
| `GetTemplateSpec` | `api/v1alpha1`, `corev1`, `client` | Configuration |
| `sandboxIDSeparator` (unexported) | none | Identification |

### Consumers of `pkg/utils/sandboxutils`

| Package | Files | Symbols used |
|---------|-------|-------------|
| `pkg/utils/runtime` | `runtime.go` | `GetRuntimeURL`, `GetAccessToken` |
| `pkg/utils/proxyutils` (Phase 8) | `default.go` | `GetRouteFromSandbox` |
| `pkg/servers/e2b` | `routes.go`, `create.go`, `services.go`, `pause_resume.go` | `ValidateNamespaceForSandboxID`, `GetAccessToken` |
| `pkg/cache` | `tasks.go`, `index.go` | `IsSandboxPausable`, `IsSandboxResumable`, `GetSandboxState`, `IsControlledBySandboxSet`, `GetSandboxID` |
| `pkg/controller/sandboxclaim/core` | `common_control.go` | `GetTemplateSpec`, `GetSandboxState` |
| `pkg/controller/sandboxset` | `rolling_update.go`, `sandboxset_controller.go`, `event_handler.go` | `IsControlledBySandboxSet`, `GetSandboxState` |
| `pkg/controller/sandbox/core` | `lifecycle_handler.go`, `util.go` | `GetRuntimeURL`, `GetTemplateSpec` |
| `pkg/sandbox-manager/infra/sandboxcr` | `infra.go`, `sandbox.go`, `claim.go`, `clone.go` | `GetSandboxID`, `GetSandboxState`, `IsSandboxPausable`, `IsSandboxResumable` |

Total: ~20 production files + ~6 test files.

### Destination analysis

| Export | Destination | Reasoning |
|--------|------------|-----------|
| `GetRuntimeURL` | `pkg/utils/proxyutils` | Returns a runtime URL for proxying requests to sandboxes. Calls `GetRouteFromSandbox` and uses `RuntimePort` — both proxy/Routing concerns. Co-locating with `DefaultGetRouteFunc`/`DefaultRequestFunc` creates a coherent proxy utility package. |
| `GetRouteFromSandbox` | `pkg/utils/proxyutils` | Returns `proxy.Route`, the proxy-specific routing struct. Already called by `proxyutils.DefaultGetRouteFunc`; moving it here eliminates the `proxyutils → sandboxutils` internal dependency. |
| `GetSandboxState` | `pkg/utils` (root) | General-purpose sandbox state inspection. No proxy dependency. Fits alongside `SetSandboxCondition`, `IsSandboxReady` in `pkg/utils/utils.go`. |
| `IsControlledBySandboxSet` | `pkg/utils` (root) | General-purpose owner reference check. No external dependencies. |
| `GetSandboxID` | `pkg/utils` (root) | Namespace/name encoding utility. No external dependencies. |
| `ValidateNamespaceForSandboxID` | `pkg/utils` (root) | Validation for sandbox ID encoding. No external dependencies. |
| `GetAccessToken` | `pkg/utils` (root) | Annotation lookup for access tokens. No proxy dependency. Used by `pkg/utils/runtime`, `pkg/servers/e2b`. |
| `IsSandboxReady` | `pkg/utils` (root) | Already calls `utils.GetSandboxCondition` — already closely tied to `pkg/utils` root. |
| `IsSandboxPausable` | `pkg/utils` (root) | State-based pausable check. No proxy dependency. |
| `IsSandboxResumable` | `pkg/utils` (root) | State-based resumable check. No proxy dependency. |
| `GetTemplateSpec` | `pkg/utils` (root) | Template resolution utility. No proxy dependency. Uses `client.Client`, fits in root. |
| `sandboxIDSeparator` | `pkg/utils` (root) | Unexported constant used by `GetSandboxID` and `ValidateNamespaceForSandboxID`. Moves alongside them. |

### Dependency impact

After this move:
- **`pkg/utils/proxyutils`** gains a dependency on `pkg/proxy/types` (for `proxy.Route`)
  and `pkg/utils` (for `utils.RuntimePort` after Phase 1, and `utils.GetSandboxState`,
  `utils.GetSandboxID` which are now in the same `pkg/utils` root).  This replaces the
  current `proxyutils → sandboxutils` dependency — same net effect, cleaner structure.
- **`pkg/utils` (root)** gains several sandbox helper functions.  Its dependencies
  remain: `api/v1alpha1`, `client`, `corev1`, etc. — all already imported.
- **`pkg/utils/sandboxutils`** is deleted entirely.

**Circular dependency check**:
- `pkg/utils/proxyutils → pkg/utils → (no proxyutils import)` ✓
- `pkg/utils/proxyutils → pkg/proxy/types → (none)` ✓
- `pkg/utils/runtime → pkg/utils/proxyutils → pkg/utils, pkg/proxy/types` ✓ (no cycle)

### Steps

1. Move `GetRuntimeURL` and `GetRouteFromSandbox` from
   `pkg/utils/sandboxutils/utils.go` into `pkg/utils/proxyutils/route.go` (new file).
   - `GetRuntimeURL` calls `GetRouteFromSandbox` (now same package) and
     `utils.RuntimePort` (after Phase 1).
   - `GetRouteFromSandbox` calls `utils.GetSandboxState` and `utils.GetSandboxID`
     (now in `pkg/utils` root).  Update the call sites:
     `GetSandboxState(s)` → `utils.GetSandboxState(s)`,
     `GetSandboxID(s)` → `utils.GetSandboxID(s)`.
   - `GetRouteFromSandbox` returns `proxy.Route` — after Phase 5, import
     `pkg/proxy/types` and use `types.Route` (or import with alias).
   - Move the `TestGetRuntimeURL` test into `pkg/utils/proxyutils/route_test.go`.
   - Change package name from `sandboxutils` to `proxyutils_test` (or `proxyutils`
     if internal test).

2. Move the remaining 9 exported functions + 1 unexported constant from
   `pkg/utils/sandboxutils/utils.go` into `pkg/utils/sandbox_utils.go` (new file
   in the root package):
   - `GetSandboxState`, `IsControlledBySandboxSet`, `GetSandboxID`,
     `ValidateNamespaceForSandboxID`, `GetAccessToken`, `IsSandboxReady`,
     `IsSandboxPausable`, `IsSandboxResumable`, `GetTemplateSpec`,
     `sandboxIDSeparator`.
   - Change package name from `sandboxutils` to `utils`.
   - Update internal cross-references within these functions to use the local
     package (no import alias needed — they are now in the same `utils` package):
     - `IsSandboxReady` already calls `utils.GetSandboxCondition` → `GetSandboxCondition`
       (same package).
     - `IsSandboxPausable` calls `IsControlledBySandboxSet`, `GetSandboxState` → same package.
     - `IsSandboxResumable` calls `utils.GetSandboxCondition` → `GetSandboxCondition`.
   - `GetSandboxState` no longer needs `consts.DebugLogLevel` or any sandbox-manager
     import (after Phases 1–2).
   - Move the corresponding tests into `pkg/utils/sandbox_utils_test.go`.

3. Update `pkg/utils/proxyutils/default.go`:
   - Remove `"github.com/openkruise/agents/pkg/utils/sandboxutils"` import.
   - Change `stateutils.GetRouteFromSandbox(s)` → `GetRouteFromSandbox(s)` (same
     package, since `GetRouteFromSandbox` now lives in `proxyutils`).

4. Update `pkg/utils/runtime/runtime.go`:
   - Remove `"github.com/openkruise/agents/pkg/utils/sandboxutils"` import.
   - Change `sandboxutils.GetRuntimeURL(sbx)` → `proxyutils.GetRuntimeURL(sbx)`.
   - Change `sandboxutils.GetAccessToken(sbx)` → `utils.GetAccessToken(sbx)`.
   - Add `"github.com/openkruise/agents/pkg/utils/proxyutils"` import.

5. Update all external consumers (change import path and call-site prefix):
   - Files that used `sandboxutils.GetSandboxState` / `stateutils.GetSandboxState` →
     `utils.GetSandboxState`.
   - Files that used `sandboxutils.GetSandboxID` / `stateutils.GetSandboxID` →
     `utils.GetSandboxID`.
   - Files that used `sandboxutils.IsControlledBySandboxSet` →
     `utils.IsControlledBySandboxSet`.
   - Files that used `sandboxutils.GetAccessToken` → `utils.GetAccessToken`.
   - Files that used `sandboxutils.GetTemplateSpec` → `utils.GetTemplateSpec`.
   - Files that used `sandboxutils.GetRuntimeURL` → `proxyutils.GetRuntimeURL`.
   - Files that used `sandboxutils.ValidateNamespaceForSandboxID` →
     `utils.ValidateNamespaceForSandboxID`.
   - Files that used `sandboxutils.IsSandboxPausable` → `utils.IsSandboxPausable`.
   - Files that used `sandboxutils.IsSandboxResumable` → `utils.IsSandboxResumable`.
   - In each file, replace `"github.com/openkruise/agents/pkg/utils/sandboxutils"` with
     the appropriate new import(s): `"github.com/openkruise/agents/pkg/utils"` and/or
     `"github.com/openkruise/agents/pkg/utils/proxyutils"`.

6. Delete `pkg/utils/sandboxutils/` directory.

7. Run `go build ./pkg/...` and `go test ./pkg/utils/... ./pkg/proxy/... ./pkg/servers/e2b/... ./pkg/controller/... ./pkg/cache/... ./pkg/sandbox-manager/infra/...` to verify.

**Prerequisite**: Phases 1, 5, and 8 must be completed first:
- Phase 1: `consts.RuntimePort` → `utils.RuntimePort`.
- Phase 5: `pkg/proxy.Route` → `pkg/proxy/types.Route`.
- Phase 8: `proxyutils` is at `pkg/utils/proxyutils` (not `pkg/utils/sandbox-manager/proxyutils`).

**Files changed**: ~25 files (2 new in utils root + proxyutils, ~20 consumer import/call updates, 1 directory deletion).

---

## Final Dependency Graph (After All 11 Phases)

```
pkg/utils/                     ← api/v1alpha1, pkg/features, pkg/utils/feature, corev1, client
                                   (includes GetSandboxState, IsControlledBySandboxSet, GetSandboxID,
                                    ValidateNamespaceForSandboxID, GetAccessToken, IsSandboxReady,
                                    IsSandboxPausable, IsSandboxResumable, GetTemplateSpec)
pkg/utils/constant.go          ← no internal pkg imports
pkg/utils/expectations/         ← stdlib + k8s apimachinery (now includes singleton + wrappers)
pkg/utils/feature/              ← no internal pkg imports
pkg/utils/logs/                 ← no internal pkg imports
pkg/utils/pagination/           ← stdlib only (sort)
pkg/utils/testutils/            ← pkg/utils, klog, flag
pkg/utils/runtime/              ← pkg/utils, pkg/utils/logs, pkg/utils/runtime/config,
                                   pkg/utils/csiutils, pkg/utils/proxyutils
pkg/utils/runtime/config/       ← api/v1alpha1, pkg/identity
pkg/utils/proxyutils/           ← pkg/proxy/types, pkg/utils, api/v1alpha1, stdlib
                                   (includes ProxyRequest, DefaultGetRouteFunc, DefaultRequestFunc,
                                    GetRuntimeURL, GetRouteFromSandbox)
pkg/utils/sidecarutils/         ← pkg/utils, pkg/utils/sidecarutils/traffic-proxy, pkg/utils/webhookutils
pkg/utils/webhookutils/         ← self-contained
pkg/proxy/                      ← pkg/proxy/types, pkg/peers, pkg/sandbox-manager/config, pkg/sandbox-manager/consts,
                                   pkg/servers/e2b/adapters, pkg/utils/expectations, pkg/servers/web
pkg/proxy/types/                ← no internal pkg imports
```

**`pkg/utils/sandbox-manager`, `pkg/utils/checkpoint`, and `pkg/utils/sandboxutils` no longer exist.**  All their contents have been
distributed to their natural homes:

| Former location | New location |
|----------------|-------------|
| `pkg/utils/sandbox-manager/expectationutils/` | `pkg/utils/expectations/` (merged into parent) |
| `pkg/utils/sandbox-manager/proxyutils/` | `pkg/utils/proxyutils/` (simple rename, package preserved) |
| `pkg/utils/sandbox-manager/utils.go` (LockSandbox, NewLockString) | `pkg/utils/` (root) |
| `pkg/utils/sandbox-manager/utils.go` (CalculateResourceFromContainers) | `pkg/sandbox-manager/infra/` |
| `pkg/utils/sandbox-manager/pagination.go` | `pkg/utils/pagination/` |
| `pkg/utils/sandbox-manager/test_utils.go` | `pkg/utils/testutils/` |
| `pkg/utils/sandbox-manager/e2b.go` | `pkg/servers/e2b/` |
| `pkg/utils/checkpoint/` | `pkg/sandbox-manager/infra/sandboxcr/` (clone-specific business logic) |
| `pkg/utils/sandboxutils/GetRuntimeURL, GetRouteFromSandbox` | `pkg/utils/proxyutils/` (proxy/Routing helpers) |
| `pkg/utils/sandboxutils/` (remaining 9 functions) | `pkg/utils/` (root — general sandbox helpers) |

No `pkg/utils/*` package imports `pkg/sandbox-manager`, `pkg/proxy`, or
`pkg/servers`.  All cycles are broken.  The `pkg/utils/sandbox-manager`,
`pkg/utils/checkpoint`, and `pkg/utils/sandboxutils` package names — the most
confusing artifacts in the current layout — are eliminated.

## Testing Strategy

- After **each phase**, run `go build ./pkg/...` to verify compilation.
- After each phase, run the relevant package unit tests:
  - Phase 1: `go test ./pkg/utils/... ./pkg/sandbox-manager/consts/...`
  - Phase 2: `go test ./pkg/utils/logs/... ./pkg/utils/runtime/... ./pkg/sandbox-manager/logs/...`
  - Phase 3: `go test ./pkg/utils/runtime/... ./pkg/sandbox-manager/config/...`
  - Phase 4: `go test ./pkg/utils/sandbox-manager/... ./pkg/sandbox-manager/infra/...`
  - Phase 5: `go test ./pkg/utils/sandboxutils/... ./pkg/proxy/...`
  - Phase 6: `go test ./pkg/utils/checkpoint/... ./pkg/servers/e2b/...`
  - Phase 7: `go test ./pkg/utils/expectations/... ./pkg/sandbox-manager/infra/... ./pkg/cache/...`
  - Phase 8: `go test ./pkg/utils/proxyutils/... ./pkg/utils/runtime/... ./pkg/sandbox-manager/infra/... ./pkg/sandbox-gateway/...`
  - Phase 9: `go test ./pkg/utils/... ./pkg/sandbox-manager/... ./pkg/servers/e2b/... ./pkg/controller/...`
  - Phase 10: `go test ./pkg/sandbox-manager/infra/sandboxcr/...`
  - Phase 11: `go test ./pkg/utils/... ./pkg/utils/proxyutils/... ./pkg/servers/e2b/... ./pkg/controller/... ./pkg/cache/... ./pkg/sandbox-manager/infra/...`
- After **all phases**, run `go build ./...` and `go vet ./pkg/...` for a final
  global verification.

## Rollback

Each phase is a self-contained commit.  If a phase introduces a regression, it can
be reverted independently because the re-export pattern preserves backward
compatibility for all callers.

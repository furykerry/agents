# Wake-on-Traffic via Direct Spec Patch (No SystemToken)

## Motivation

PR #495 implements wake-on-traffic by having sandbox-gateway call sandbox-manager's
`/connect` HTTP API using a scoped system credential (systemtoken). This introduces
cross-component HTTP coupling, a new credential type, and credential lifecycle
management. This proposal replaces that mechanism with a direct Go function call,
eliminating the systemtoken entirely while reusing the exact same resume logic.

## Design

The sandbox-gateway directly calls `sandboxcr.AsSandbox(sbx, cache).Resume(ctx, opts)`
— a Go function call, not an HTTP call. This reuses the entire sandbox-manager connect
path: spec patch (`Spec.Paused = false`), wait-for-running (`NewSandboxResumeTask().Wait()`),
concurrent dedup (first-writer-wins via `retryUpdate`), conflict retries, and post-resume
refresh (`InplaceRefresh`).

```
Traffic -> Envoy Filter -> Registry lookup
  |-> sandbox Running: forward (current behavior)
  |-> sandbox Paused + WakeOnTraffic enabled:
       |-> sandboxcr.AsSandbox(sbx, cacheProvider).Resume(ctx, opts)
       |     ^-- reuses existing sandbox-manager connect implementation:
       |         1. refreshFromAPIReader (fresh fetch)
       |         2. IsSandboxResumable check
       |         3. NewSandboxResumeTask (pre-acquired wait task)
       |         4. retryUpdate: patches Spec.Paused=false + setTimeout
       |         5. resumeTask.Wait() -- blocks until Ready condition True
       |         6. InplaceRefresh + expectations
       |     Concurrent dedup: first-writer-wins via retryUpdate
       |-> syncRoute: update local registry + sync to peer gateways
       |-> Forward request or return 503 on timeout/failure
  |-> sandbox Paused + WakeOnTraffic disabled: return 502 (current behavior)
```

"WakeOnTraffic enabled" above is the effective wake decision, sourced from the
Sandbox spec field defined in [Wake Configuration API](#wake-configuration-api).

## Wake Configuration API

Wake-on-traffic is declared on the Sandbox spec, as a resume rule alongside the
probe-driven rules introduced by
[Sandbox Auto-Pause and Resume](./20260626-sandbox-auto-pause.md):

```go
// ResumePolicy defines when to resume the sandbox.
type ResumePolicy struct {
    // WhenProbedScheduleTime resumes the sandbox before a scheduled task
    // by parsing the probe's Condition message as a timestamp.
    // +optional
    WhenProbedScheduleTime *ProbedScheduleTimeRule `json:"whenProbedScheduleTime,omitempty"`

    // WhenIngressTraffic resumes the sandbox when the sandbox-gateway receives
    // inbound traffic addressed to it while it is paused. Unlike the probed
    // rules this one is event-driven: it needs no probe, it produces no
    // Status.Schedules entry, and it is executed by the sandbox-gateway rather
    // than by the sandbox controller.
    // +optional
    WhenIngressTraffic *IngressTrafficRule `json:"whenIngressTraffic,omitempty"`
}

// IngressTrafficRule defines the rule for resuming a paused sandbox when
// ingress traffic reaches the sandbox-gateway. A non-nil rule enables
// wake-on-traffic; there is no separate enable flag, matching the sibling
// rules where nil means "not configured".
type IngressTrafficRule struct {
    // PauseTimeout is the auto-pause timeout re-armed by a traffic wake: the
    // gateway writes Spec.PauseTime = now + PauseTimeout atomically with
    // Spec.Paused = false, so the woken sandbox has running time before its
    // next auto-pause. It applies only to auto-pause sandboxes (those that
    // already carry Spec.PauseTime); never-timeout and shutdown-only
    // sandboxes keep their timeout mode unchanged.
    // When absent or non-positive, the gateway's wake-timeout-seconds
    // configuration (default 60s) is used. The effective value is still
    // subject to the resume timeout floor
    // (timeout.DefaultMinResumeTimeoutSeconds).
    // +optional
    PauseTimeout *metav1.Duration `json:"pauseTimeout,omitempty"`
}
```

YAML:

```yaml
spec:
  autoPausePolicy:
    resume:
      whenIngressTraffic:
        pauseTimeout: 5m
```

### Naming

`WhenIngressTraffic` continues the `When<signal>` shape of the sibling rules
(`WhenProbedIdleState`, `WhenProbedScheduleTime`), and `Ingress` states the
traffic direction that triggers the wake. Alternatives considered:
`WhenInboundTraffic` (consistent with the gateway's inbound-authentication
vocabulary, but less explicit about direction in a Kubernetes context),
`WhenTrafficArrives` (verb phrase, breaks the sibling shape), and
`WhenGatewayTraffic` (binds a specific component into the API contract).

The rule is a struct rather than a bool because it carries `PauseTimeout`, the
re-armed auto-pause timeout, and leaves room for future matchers (for example,
restricting wake to specific ports or paths) without another API break.

### Why this rule must not activate the auto-pause controller

`WhenIngressTraffic` lives under `AutoPausePolicy` but must not be treated as a
probe-driven policy:

- **`checkTimers` guard.** The auto-pause proposal makes `checkTimers` skip the
  one-shot `Spec.PauseTime` auto-pause when `hasActiveAutoPausePolicy(box)` is
  true. That predicate must test only the probe-driven rules
  (`Pause.WhenProbedIdleState`, `Resume.WhenProbedScheduleTime`). If
  `WhenIngressTraffic` counted as an active policy, every sandbox created with
  E2B `autoResume: {"enabled": true}` would silently lose its `timeout`-based
  auto-pause. Wake-on-traffic complements that timer — the wake path itself
  re-arms `PauseTime` — it does not replace it.
- **No `Status.Schedules` entry.** The trigger is a request arrival, so neither
  `NextPauseTime` nor `NextResumeTime` can be computed in advance; a Schedule
  with both timestamps empty carries no information. No new `ScheduleReason`
  constant is added.
- **No probe and no feature gate coupling.** `Spec.Probes` is not required, and
  the controller-only `AutoPauseController` gate does not gate this rule. The
  kill switch stays where the behavior executes: `enable-wake-on-traffic` in the
  sandbox-gateway ConfigMap (`config/sandbox-gateway/configmap.yaml`).
- **No revision churn.** `HashSandbox` hashes only `spec.template`, so writing
  `Spec.AutoPausePolicy` neither changes `Status.UpdateRevision` nor triggers an
  in-place update.

## Read Helpers

One helper pair in `pkg/utils` owns the spec reads so the gateway, the
controller and the route projection cannot drift:

```go
// WakeOnIngressTrafficEnabled reports whether the sandbox opted into
// wake-on-traffic via its spec.
func WakeOnIngressTrafficEnabled(sbx *agentsv1alpha1.Sandbox) bool

// WakeOnIngressTrafficPauseTimeout returns the auto-pause timeout to re-arm
// after a traffic wake, or 0 when the rule does not set a positive value.
func WakeOnIngressTrafficPauseTimeout(sbx *agentsv1alpha1.Sandbox) time.Duration
```

Out-of-band enablement uses a direct spec patch:

```bash
kubectl patch sandbox my-sbx --type=merge -p \
  '{"spec":{"autoPausePolicy":{"resume":{"whenIngressTraffic":{"pauseTimeout":"5m"}}}}}'
```

## Control-Plane Wiring

### Route projection (shared by controller, gateway and manager)

`sandboxroute.RouteFromSandbox` is the single projection consumed by the gateway
registry and by the manager's `syncRoute`. It switches to the helper:

```go
WakeOnTraffic: utils.WakeOnIngressTrafficEnabled(sandbox),
```

`Route.WakeOnTraffic` keeps its field name and JSON tag: gateways exchange
routes with peers during a rolling upgrade, so renaming the wire field would
break route sync between mixed-version gateways. `PauseTimeout` is deliberately
*not* added to `Route` — the wake path already re-reads the Sandbox from the
informer cache, and every extra route field widens the peer-sync contract.

### Sandbox controller: recycle reset

Wake configuration is per-tenant, so a recycled pool CR must not inherit it.
`resetMetadataForPool` (`pkg/controller/sandbox/core/recycle.go`, Part 1, next to
the existing `Spec.ShutdownTime` / `Spec.PauseTime` reset) clears the rule and
prunes the now-empty parents so the pooled spec stays byte-identical to a fresh
one:

```go
if p := box.Spec.AutoPausePolicy; p != nil && p.Resume != nil {
    p.Resume.WhenIngressTraffic = nil
    if p.Resume.WhenProbedScheduleTime == nil {
        p.Resume = nil
    }
    if p.Pause == nil && p.Resume == nil {
        box.Spec.AutoPausePolicy = nil
    }
}
```

The probe-driven rules are intentionally left untouched: they are declared by
the SandboxSet template or by an operator, not by a claim.

### Sandbox controller: `checkTimers`

`hasActiveAutoPausePolicy` — the guard that suppresses the `Spec.PauseTime`
timer — must ignore `WhenIngressTraffic`, for the reason given in
[Why this rule must not activate the auto-pause controller](#why-this-rule-must-not-activate-the-auto-pause-controller).
This is the one cross-feature invariant that a future change to either feature
must preserve.

### Admission

No webhook is added. `metav1.Duration` typing rejects malformed values at
admission time, and a non-positive `PauseTimeout` degrades to the configured
gateway default at read time.

### sandbox-manager write path (API -> Infra)

The API layer must not reach into the CR spec, so the neutral `infra.Sandbox`
interface gains one narrow setter, implemented by `sandboxcr.Sandbox` next to
`SetTimeout`:

```go
// SetWakeOnIngressTraffic enables or clears the wake-on-ingress-traffic resume
// rule. A non-positive pauseTimeout leaves the re-armed timeout unset, so the
// gateway default applies.
SetWakeOnIngressTraffic(enabled bool, pauseTimeout time.Duration)
```

`basicSandboxCreateModifier` (`pkg/servers/e2b/create.go`) calls the setter to
express the wake configuration; the metadata `wake-timeout-seconds` override is
removed along with it.

```go
if request.AutoResume.Enabled {
    var pauseTimeout time.Duration
    // The re-armed timeout only feeds the fresh PauseTime the gateway writes
    // for auto-pause sandboxes; shutdown-only and never-timeout sandboxes
    // never carry a PauseTime, so it stays unset for them.
    if request.AutoPause && !request.Extensions.NeverTimeout && request.Timeout > 0 {
        pauseTimeout = time.Duration(request.Timeout) * time.Second
    }
    sbx.SetWakeOnIngressTraffic(true, pauseTimeout)
} else {
    sbx.SetWakeOnIngressTraffic(false, 0)
}
```

Because the setter is called on both branches, a claimed CR that still holds a
previous delivery's rule is reset even if its recycle was skipped.

The E2B surface does not change: `autoResume: {"enabled": true}` (Python SDK
`lifecycle={"auto_resume": True}`) keeps its meaning and now lands in the spec.

### sandbox-gateway read path

- The `wake.Waker` enable check becomes `wake.Waker.WakeEnabled`, delegating
  to `utils.WakeOnIngressTrafficEnabled`. It stays the informer-cache
  fallback that covers the window between a spec patch and the gateway
  controller reconciling the change into the route registry.
- `wake.Waker.wakeInternal` resolves the re-armed timeout through
  `utils.WakeOnIngressTrafficPauseTimeout`, falling back to the
  `defaultWakeTimeout` passed by the filter. The auto-pause/never-timeout/
  shutdown-only branching and the resume timeout floor are unchanged.
- `filter.shouldWakeSandbox` is unchanged apart from the renamed fallback call;
  `Config.EnableWakeOnTraffic` remains the listener-level kill switch.

## Existing Gateway Components

The pieces below are unchanged by the API migration; they are the wake execution
path introduced by this proposal's first revision.

### Wake Package (`pkg/sandbox-gateway/wake/`)

The `Waker` struct wraps `sandboxcr.AsSandbox(sbx, cache).Resume()` and syncs the route
after Resume succeeds. It does NOT reimplement spec patching or wait-for-running — it
delegates entirely to the existing `Resume()` method.

After Resume succeeds, `syncRoute` mirrors the manager's `syncRoute` flow:
1. Get route from refreshed sandbox (`sandbox.GetRoute()`)
2. Update local gateway registry (`registry.GetRegistry().Update`)
3. Sync route to peer gateways (`proxy.SyncRouteWithPeers`)

### Cache Provider

`cache.NewCache(mgr)` creates the same informer-backed cache + `WaitReconciler` used by
sandbox-manager. The gateway's controller-runtime manager hosts both the existing
`SandboxReconciler` (for local registry updates) and the cache provider's wait
reconciler (for `NewSandboxResumeTask().Wait()`).

### Route Sync

`proxy.SyncRouteWithPeers` was extracted as a package-level function so the gateway can
call it without creating a full `proxy.Server` instance. The gateway's `server.Server`
exposes its `peerManager` via `GetPeerManager()` for use by the Waker.

## Authorization

K8s RBAC grants the gateway ServiceAccount `update`/`patch` on `sandboxes` resources.
No systemtoken, no HTTP call to sandbox-manager.

## Comparison with PR #495

| Aspect | PR #495 | This Proposal |
|--------|---------|---------------|
| Wake trigger | Gateway calls manager `/connect` HTTP API | Gateway calls `sandboxcr.Sandbox.Resume()` directly (Go function) |
| Auth | System key (systemtoken) | K8s RBAC (ServiceAccount) |
| Resume logic | Manager's `ResumeSandbox` HTTP handler | Same `sandboxcr.Sandbox.Resume()` method (imported, not HTTP) |
| Wait mechanism | Manager's `NewSandboxResumeTask().Wait()` | Same (reused via Resume call) |
| Spec patching | Manager's `retryUpdate` inside Resume | Same (reused via Resume call) |
| Concurrent dedup | Manager's first-writer-wins | Same (reused via Resume call) |
| Route sync after wake | Manager's `syncRoute` | Gateway mirrors: `registry.Update` + `proxy.SyncRouteWithPeers` |
| Timeout update | Manager's connect API handles it | Gateway passes `ResumeOptions.Timeout.PauseTime` |
| New components | `systemkey.go`, `wake/client.go`, `wake/wake.go` | `wake/wake.go` (thin wrapper) |
| Cross-component deps | Gateway -> Manager HTTP | Gateway imports `pkg/sandbox-manager/infra/sandboxcr` (Go import) |
| Cache provider | Manager has its own | Gateway creates its own via `cache.NewCache(mgr)` |

## Timeout Handling

`WhenIngressTraffic.PauseTimeout` stores the auto-pause timeout to re-arm. When
the gateway wakes a sandbox:
1. It reads `PauseTimeout` from the spec to determine the fresh `PauseTime`
2. If the spec value is absent or non-positive, it falls back to the filter's
   `WakeTimeoutSeconds` config default (60s)
3. The resume timeout floor (`timeout.DefaultMinResumeTimeoutSeconds`) is applied
   so the fresh `PauseTime` cannot expire while the sandbox is still resuming
4. The timeout is passed as `ResumeOptions.Timeout.PauseTime`, which is written atomically
   with `Spec.Paused = false` inside `retryUpdate` — closing the auto-pause race

Only auto-pause sandboxes (those already carrying `Spec.PauseTime`) get a fresh
`PauseTime`; never-timeout and shutdown-only sandboxes keep their timeout mode.

## Touch Points

| Area | File | Change |
|------|------|--------|
| API types | `api/v1alpha1/sandbox_types.go` | Add `ResumePolicy.WhenIngressTraffic` + `IngressTrafficRule` |
| Read helpers | `pkg/utils/utils.go` | Add the two spec-read helpers shared by gateway, controller and route projection |
| Generated output | `client/`, `config/crd/` | `make generate manifests` (never edited by hand) |
| Route projection | `pkg/sandboxroute/route.go` | `WakeOnTraffic` derived from the helper |
| Recycle | `pkg/controller/sandbox/core/recycle.go` | Clear the rule in `resetMetadataForPool` and prune empty parents |
| Auto-pause guard | sandbox controller `checkTimers` | `hasActiveAutoPausePolicy` ignores `WhenIngressTraffic` |
| Infra setter | `pkg/sandbox-manager/infra/interface.go`, `infra/sandboxcr/sandbox.go` | Add `SetWakeOnIngressTraffic` |
| E2B create | `pkg/servers/e2b/create.go` | Call the setter to express the wake configuration; drop the metadata `wake-timeout-seconds` override |
| E2B model doc | `pkg/servers/e2b/models/sandbox.go` | `SandboxAutoResumeConfig` comment now refers to the spec field |
| Gateway wake | `pkg/sandbox-gateway/wake/wake.go` | Enable check -> `WakeEnabled`; timeout resolution via the helper |
| Gateway filter | `pkg/sandbox-gateway/filter/filter.go` | Renamed fallback call only |

## Test Plan

### Unit

- **Spec-read helpers** (table-driven): rule present with and without
  `PauseTimeout`; nil rule; non-positive `PauseTimeout` treated as unset.
- **Route projection** (`pkg/sandboxroute/route_test.go`): cover wake cases
  driven by the spec rule, asserting `Route.WakeOnTraffic`.
- **E2B create modifier** (`pkg/servers/e2b/create_test.go`): extend the existing
  `autoResume` table — enabled + `autoPause` sets `PauseTimeout` from `timeout`;
  enabled + never-timeout / shutdown-only leaves it unset; disabled clears the
  rule; a recycled CR carrying a previous delivery's rule ends up with none.
- **Recycle** (`pkg/controller/sandbox/core/recycle_test.go`): cover a CR with
  the spec rule (alone, and combined with a probed rule); assert the reset and
  empty-parent pruning.
- **`checkTimers` guard**: a sandbox whose only policy is `WhenIngressTraffic`
  still auto-pauses at `PauseTime`; adding a probed rule suppresses the timer.
- **Wake timeout resolution** (`pkg/sandbox-gateway/wake`): spec value,
  config default, and floor application.

### E2E

`test/e2b/test_wake_on_traffic.py` keeps its flow and switches its assertions
to `spec.autoPausePolicy.resume.whenIngressTraffic`, including the
persists-after-wake check.

## Implementation History

- [x] 2026-06-27: Initial proposal — replace the systemtoken/HTTP wake path with
  a direct `sandboxcr.Sandbox.Resume()` call.
- [x] 2026-08-28: Promote the wake configuration to
  `Spec.AutoPausePolicy.Resume.WhenIngressTraffic`, and define the
  control-plane wiring (route projection, recycle reset, `checkTimers` guard,
  `infra.Sandbox` setter).
- [ ] TODO: Community review and feedback.
- [ ] TODO: API types + `make generate manifests`.
- [ ] TODO: Read/write path migration + unit tests.

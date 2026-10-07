# Change Log

## v0.6.0-alpha4

> Change log since v0.3.0

Version range: v0.3.0 → v0.6.0-alpha4

---

## 1. Features

### 1.1 Security Enhancement

**Ingress & Egress Control**
- Introduced `TrafficPolicy`, `GlobalTrafficPolicy`, and `SecurityProfile` CRDs to drive sandbox ingress and egress control, covering MCP tool access control, L7 network rules, header manipulation, token transformation, and hardened CRD admission validation ([#397](https://github.com/openkruise/agents/pull/397), [#433](https://github.com/openkruise/agents/pull/433), [#445](https://github.com/openkruise/agents/pull/445), [#448](https://github.com/openkruise/agents/pull/448), [#483](https://github.com/openkruise/agents/pull/483), [#494](https://github.com/openkruise/agents/pull/494), [#521](https://github.com/openkruise/agents/pull/521), [#588](https://github.com/openkruise/agents/pull/588), [#610](https://github.com/openkruise/agents/pull/610), [#615](https://github.com/openkruise/agents/pull/615), [#614](https://github.com/openkruise/agents/pull/614), [#838](https://github.com/openkruise/agents/pull/838), [#829](https://github.com/openkruise/agents/pull/829), [#859](https://github.com/openkruise/agents/pull/859), [#745](https://github.com/openkruise/agents/pull/745), [#746](https://github.com/openkruise/agents/pull/746), [#915](https://github.com/openkruise/agents/pull/915), [#919](https://github.com/openkruise/agents/pull/919), [#930](https://github.com/openkruise/agents/pull/930)).
- The gateway now verifies JWTs with optional runtime mTLS, aligns traffic tokens with the E2B SDK, rotates traffic access tokens, and masks access tokens in route logs and debug endpoints ([#561](https://github.com/openkruise/agents/pull/561), [#648](https://github.com/openkruise/agents/pull/648), [#689](https://github.com/openkruise/agents/pull/689), [#742](https://github.com/openkruise/agents/pull/742), [#607](https://github.com/openkruise/agents/pull/607)).

**Identity & Token Framework**
- Introduced a FeatureGate-controlled Security Identity Provider that issues and propagates tokens across the whole sandbox lifecycle — at claim and clone time, after resume, and before CSI re-mount — with proactive token refresh, identity propagation to checkpoints, and security metadata sourced from sandbox annotations instead of the create request ([#324](https://github.com/openkruise/agents/pull/324), [#450](https://github.com/openkruise/agents/pull/450), [#460](https://github.com/openkruise/agents/pull/460), [#463](https://github.com/openkruise/agents/pull/463), [#469](https://github.com/openkruise/agents/pull/469), [#488](https://github.com/openkruise/agents/pull/488), [#642](https://github.com/openkruise/agents/pull/642), [#671](https://github.com/openkruise/agents/pull/671), [#633](https://github.com/openkruise/agents/pull/633), [#637](https://github.com/openkruise/agents/pull/637), [#638](https://github.com/openkruise/agents/pull/638), [#639](https://github.com/openkruise/agents/pull/639), [#475](https://github.com/openkruise/agents/pull/475), [#632](https://github.com/openkruise/agents/pull/632), [#630](https://github.com/openkruise/agents/pull/630), [#501](https://github.com/openkruise/agents/pull/501)).

**TLS & Runtime Transport**
- TLS-capable sandboxes now serve CSI mounts and the `/init` handshake over HTTPS, with CA bundles injected into all containers, tokens delivered over the resolved runtime transport, and upgrade hooks secured by TLS ([#478](https://github.com/openkruise/agents/pull/478), [#552](https://github.com/openkruise/agents/pull/552), [#700](https://github.com/openkruise/agents/pull/700), [#720](https://github.com/openkruise/agents/pull/720), [#702](https://github.com/openkruise/agents/pull/702), [#729](https://github.com/openkruise/agents/pull/729), [#734](https://github.com/openkruise/agents/pull/734), [#752](https://github.com/openkruise/agents/pull/752), [#886](https://github.com/openkruise/agents/pull/886), [#797](https://github.com/openkruise/agents/pull/797)).
- Added memberlist encryption and peer mTLS for the Manager and Gateway control plane ([#967](https://github.com/openkruise/agents/pull/967)).

### 1.2 Operations Enhancement

**Checkpoint, Pause/Resume & Commit**
- Introduced the sandbox checkpoint lifecycle with filesystem checkpoints (`PersistentContents`), selectable checkpoint labels, and a `CheckpointRestore` upgrade strategy ([#508](https://github.com/openkruise/agents/pull/508), [#674](https://github.com/openkruise/agents/pull/674), [#712](https://github.com/openkruise/agents/pull/712), [#714](https://github.com/openkruise/agents/pull/714), [#670](https://github.com/openkruise/agents/pull/670)).
- Matured pause/resume: a selectable `PauseStrategy` (Stop / Snapshot / CloudDisk) exposed on `SandboxSet`, atomic resume with clearer errors, events and conditions for post-resume re-initialization, and pause that waits for active checkpoints ([#713](https://github.com/openkruise/agents/pull/713), [#774](https://github.com/openkruise/agents/pull/774), [#839](https://github.com/openkruise/agents/pull/839), [#435](https://github.com/openkruise/agents/pull/435), [#424](https://github.com/openkruise/agents/pull/424), [#416](https://github.com/openkruise/agents/pull/416), [#913](https://github.com/openkruise/agents/pull/913)).
- Introduced the `Commit` CRD with a controller that snapshots and pushes sandbox images via nerdctl ([#502](https://github.com/openkruise/agents/pull/502), [#533](https://github.com/openkruise/agents/pull/533), [#608](https://github.com/openkruise/agents/pull/608), [#595](https://github.com/openkruise/agents/pull/595)).

**Upgrade & In-Place Update**
- Claimed and paused sandboxes can now be batch-upgraded via `SandboxUpdateOps` with a two-phase flow, eligibility filtering, and resume that continues from the previously failed step ([#710](https://github.com/openkruise/agents/pull/710), [#750](https://github.com/openkruise/agents/pull/750), [#785](https://github.com/openkruise/agents/pull/785), [#482](https://github.com/openkruise/agents/pull/482), [#531](https://github.com/openkruise/agents/pull/531), [#553](https://github.com/openkruise/agents/pull/553), [#511](https://github.com/openkruise/agents/pull/511), [#447](https://github.com/openkruise/agents/pull/447)).
- CPU and memory can be resized in place when claiming warm-pool sandboxes, preserving system-injected fields and init-container consistency ([#519](https://github.com/openkruise/agents/pull/519), [#462](https://github.com/openkruise/agents/pull/462), [#537](https://github.com/openkruise/agents/pull/537), [#538](https://github.com/openkruise/agents/pull/538), [#513](https://github.com/openkruise/agents/pull/513), [#716](https://github.com/openkruise/agents/pull/716), [#470](https://github.com/openkruise/agents/pull/470)).

**Observability & Events**
- Added abnormal-container and duration metrics, lifecycle events and conditions for pod creation failures and controller/manager lifecycles, and moved metric cleanup off the reconcile hot path ([#452](https://github.com/openkruise/agents/pull/452), [#591](https://github.com/openkruise/agents/pull/591), [#461](https://github.com/openkruise/agents/pull/461), [#626](https://github.com/openkruise/agents/pull/626), [#603](https://github.com/openkruise/agents/pull/603), [#658](https://github.com/openkruise/agents/pull/658)).
- Reduced proxy and infra log volume, and added an optional dedicated E2B observability listener ([#579](https://github.com/openkruise/agents/pull/579), [#858](https://github.com/openkruise/agents/pull/858)).

**Controller & SandboxSet**
- `SandboxSet` improvements: auto-creation of `SandboxTemplate`, a legacy revision hash that prevents sandbox recreation on upgrade, a startup-failure budget for `maxUnavailable`, and priority-based scale-down ([#396](https://github.com/openkruise/agents/pull/396), [#514](https://github.com/openkruise/agents/pull/514), [#910](https://github.com/openkruise/agents/pull/910), [#803](https://github.com/openkruise/agents/pull/803)).
- Sandbox lifecycle hardening: a lazy finalizer added on pause and removed on resume, rejection of leftover pods from a previous same-name sandbox, and status persisted during the Pending phase ([#646](https://github.com/openkruise/agents/pull/646), [#757](https://github.com/openkruise/agents/pull/757), [#455](https://github.com/openkruise/agents/pull/455)).
- Sandbox claims gained an effective batch-size flag, namespace scoping, and propagation of designated claim annotations into the pod template ([#656](https://github.com/openkruise/agents/pull/656), [#824](https://github.com/openkruise/agents/pull/824), [#667](https://github.com/openkruise/agents/pull/667)).
- Added the `okactl` CLI for sandbox operations and multi-arch image publishing ([#497](https://github.com/openkruise/agents/pull/497), [#545](https://github.com/openkruise/agents/pull/545)).

**Performance & Caching**
- Reduced hot-path cost and memory across claim, checkpoint, and gateway paths via informer-driven refresh, active-sandbox counting, and definitive cache-miss handling ([#421](https://github.com/openkruise/agents/pull/421), [#517](https://github.com/openkruise/agents/pull/517), [#423](https://github.com/openkruise/agents/pull/423), [#522](https://github.com/openkruise/agents/pull/522), [#442](https://github.com/openkruise/agents/pull/442), [#751](https://github.com/openkruise/agents/pull/751), [#730](https://github.com/openkruise/agents/pull/730), [#724](https://github.com/openkruise/agents/pull/724)).

**E2B Compatibility**
- Aligned with the E2B SDK: Claude Code support, pod-IP metadata, API key encoding for E2B ≥ v2.25.0, named cloned sandboxes, dynamically resolved sandbox domains, and an unlimited default create-server timeout ([#415](https://github.com/openkruise/agents/pull/415), [#436](https://github.com/openkruise/agents/pull/436), [#473](https://github.com/openkruise/agents/pull/473), [#385](https://github.com/openkruise/agents/pull/385), [#649](https://github.com/openkruise/agents/pull/649), [#484](https://github.com/openkruise/agents/pull/484)).
- Added the Volume and Network APIs, dimension-aware API key quota, and a secret-to-MySQL API key migration script ([#580](https://github.com/openkruise/agents/pull/580), [#596](https://github.com/openkruise/agents/pull/596), [#616](https://github.com/openkruise/agents/pull/616), [#565](https://github.com/openkruise/agents/pull/565), [#309](https://github.com/openkruise/agents/pull/309)).

**Storage & Runtime**
- Added RRSA-based storage authentication for on-demand CSI mounts, an agent-runtime client with a CSI mount API, atomic filesystem operations, and a storage CLI binary ([#568](https://github.com/openkruise/agents/pull/568), [#685](https://github.com/openkruise/agents/pull/685), [#723](https://github.com/openkruise/agents/pull/723), [#539](https://github.com/openkruise/agents/pull/539)).

**Miscellaneous**
- Implemented short and stable sandbox IDs that stay unique across lifecycle operations ([#686](https://github.com/openkruise/agents/pull/686), [#766](https://github.com/openkruise/agents/pull/766)).
- Clone failures are retried, sidecar injection moved into pod generation, postStart hooks are merged deterministically, and a `sync-charts` skill keeps the Helm charts in sync with controller and manager manifests ([#437](https://github.com/openkruise/agents/pull/437), [#530](https://github.com/openkruise/agents/pull/530), [#542](https://github.com/openkruise/agents/pull/542), [#520](https://github.com/openkruise/agents/pull/520), [#555](https://github.com/openkruise/agents/pull/555), [#916](https://github.com/openkruise/agents/pull/916)).

### 1.3 Cost Optimization

- **Sandbox recycle / return-to-pool**: released sandboxes are reused to avoid cold starts ([#548](https://github.com/openkruise/agents/pull/548), [#609](https://github.com/openkruise/agents/pull/609), [#569](https://github.com/openkruise/agents/pull/569)).
- **Auto-pause and resume** with a probe-driven `AutoPausePolicy`, probes delivered via PodProbeMarker on real nodes and a serverless annotation on virtual nodes, and an `OnIngressTraffic` wake-on-traffic resume rule ([#612](https://github.com/openkruise/agents/pull/612), [#899](https://github.com/openkruise/agents/pull/899), [#1010](https://github.com/openkruise/agents/pull/1010), [#900](https://github.com/openkruise/agents/pull/900), [#586](https://github.com/openkruise/agents/pull/586)).
- **PoolAutoscaler** for capacity-based and cron-driven pool autoscaling with coordinated scale-up execution ([#625](https://github.com/openkruise/agents/pull/625), [#895](https://github.com/openkruise/agents/pull/895), [#917](https://github.com/openkruise/agents/pull/917)).
- Refined paused-sandbox retention and reduced the default failed-sandbox reserve TTL to 30 minutes ([#566](https://github.com/openkruise/agents/pull/566), [#457](https://github.com/openkruise/agents/pull/457)).

---

## 2. Bug Fixes

**Core Lifecycle & Reconciliation**
- Fixed `ClaimSandbox` returning `(nil, nil)` on cancellation, informer cache corruption from disabled deep copies, a TTL leak by letting Checkpoint own `SandboxTemplate`, invalid `SandboxClaim` retry loops, and sandbox cleanup on network-policy failures ([#399](https://github.com/openkruise/agents/pull/399), [#387](https://github.com/openkruise/agents/pull/387), [#419](https://github.com/openkruise/agents/pull/419), [#840](https://github.com/openkruise/agents/pull/840), [#707](https://github.com/openkruise/agents/pull/707)).
- Corrected pause/resume semantics: resume during pausing returns 400, pausing sandboxes may pause again, resume decouples phase transition from pod readiness, and pause conditions are fixed for checkpoint-disabled and pod-deleted paths ([#404](https://github.com/openkruise/agents/pull/404), [#422](https://github.com/openkruise/agents/pull/422), [#529](https://github.com/openkruise/agents/pull/529), [#524](https://github.com/openkruise/agents/pull/524)).
- Fixed status and clone edge cases: pod status synced before upgrade initialization, security token refresh treating absent `RuntimeInitialized` as serving, clone honoring the requested CSI mount config, checkpoint-delete expectations settling when the checkpoint is already gone, and a checkpoint leak when clone creation fails ([#912](https://github.com/openkruise/agents/pull/912), [#675](https://github.com/openkruise/agents/pull/675), [#641](https://github.com/openkruise/agents/pull/641), [#812](https://github.com/openkruise/agents/pull/812), [#1008](https://github.com/openkruise/agents/pull/1008)).
- Fixed false-positive resource change detection in in-place updates ([#420](https://github.com/openkruise/agents/pull/420), [#557](https://github.com/openkruise/agents/pull/557)).

**E2B Compatibility**
- Dead sandboxes now return 404 from `DescribeSandbox`, `is_running` is polled after kill to avoid async-deletion races, pagination is stable for duplicate timestamps, reserved failed-sandbox cleanup works, and E2B traffic-policy precedence is correct ([#636](https://github.com/openkruise/agents/pull/636), [#692](https://github.com/openkruise/agents/pull/692), [#645](https://github.com/openkruise/agents/pull/645), [#563](https://github.com/openkruise/agents/pull/563), [#589](https://github.com/openkruise/agents/pull/589), [#740](https://github.com/openkruise/agents/pull/740)).
- Generalized claimed-sandbox lookup so dead-but-claimed sandboxes report their real state through Describe/Delete/Connect and resume rejects them; the E2B Volume management endpoints were temporarily disabled ([#544](https://github.com/openkruise/agents/pull/544), [#744](https://github.com/openkruise/agents/pull/744)).
- Hardened resource ownership, key storage validation, admin-key persistence, and unreadable Secret entry handling ([#835](https://github.com/openkruise/agents/pull/835), [#854](https://github.com/openkruise/agents/pull/854)).

**API Keys & Quota**
- Invalid API key creation returns 400, registry secret lookup errors propagate, and API key persistence and owner labels are hardened ([#449](https://github.com/openkruise/agents/pull/449), [#584](https://github.com/openkruise/agents/pull/584), [#677](https://github.com/openkruise/agents/pull/677)).

**Controller / Webhook / CRD**
- Fixed webhook queue bootstrap and CertDir alignment, `SandboxTemplate` webhook registration, ops-template patch sanitization, `SandboxSet` reconcile during deletion, desktop SandboxSet template mismatch, and internal labels leaking into sandbox pod templates ([#654](https://github.com/openkruise/agents/pull/654), [#820](https://github.com/openkruise/agents/pull/820), [#793](https://github.com/openkruise/agents/pull/793), [#856](https://github.com/openkruise/agents/pull/856), [#558](https://github.com/openkruise/agents/pull/558), [#911](https://github.com/openkruise/agents/pull/911)).

**Gateway & Transport**
- Traffic tokens are issued for cloned sandboxes, invalid gateway server ports normalize to the default, the UUID baseline is preserved when JWT auth is enabled, and TrafficPolicy pod selection uses the sandbox UID with a name fallback ([#728](https://github.com/openkruise/agents/pull/728), [#613](https://github.com/openkruise/agents/pull/613), [#885](https://github.com/openkruise/agents/pull/885), [#982](https://github.com/openkruise/agents/pull/982)).

**Storage & Resource Leaks**
- Stale CSI volumes are unmounted before sandbox reuse, and an unclosed `http.Response` body in the BrowserUse endpoint that caused a socket leak is fixed ([#573](https://github.com/openkruise/agents/pull/573), [#708](https://github.com/openkruise/agents/pull/708)).

**Tests / CI Fixes**
- Stabilized flaky tests and CI: sandbox connection method in resume, checkpoint conditions, the quota anti-drift primary-loss test under `-race`, quota fail-open and resume timeout checks, envoy ext_proc timeouts with tolerated transient 504s, Redis/CR state dumps on quota-rebuild E2E failure, E2B Build Image retries, free-disk-space in the e2e-e2b-mysql-latest workflow, the background-command kill test, and the access-token masking test ([#476](https://github.com/openkruise/agents/pull/476), [#592](https://github.com/openkruise/agents/pull/592), [#617](https://github.com/openkruise/agents/pull/617), [#884](https://github.com/openkruise/agents/pull/884), [#906](https://github.com/openkruise/agents/pull/906), [#816](https://github.com/openkruise/agents/pull/816), [#647](https://github.com/openkruise/agents/pull/647), [#643](https://github.com/openkruise/agents/pull/643), [#651](https://github.com/openkruise/agents/pull/651), [#634](https://github.com/openkruise/agents/pull/634)).

---

## 3. Chores

**Dependabot Bumps**
- `aquasecurity/trivy-action` 0.35.0 → 0.36.0 ([#294](https://github.com/openkruise/agents/pull/294)); `github/codeql-action` 4.35.4 → 4.38.0 ([#429](https://github.com/openkruise/agents/pull/429), [#466](https://github.com/openkruise/agents/pull/466), [#499](https://github.com/openkruise/agents/pull/499), [#527](https://github.com/openkruise/agents/pull/527), [#605](https://github.com/openkruise/agents/pull/605), [#618](https://github.com/openkruise/agents/pull/618), [#620](https://github.com/openkruise/agents/pull/620), [#621](https://github.com/openkruise/agents/pull/621), [#623](https://github.com/openkruise/agents/pull/623), [#680](https://github.com/openkruise/agents/pull/680), [#878](https://github.com/openkruise/agents/pull/878), [#1003](https://github.com/openkruise/agents/pull/1003)); `ruby/setup-ruby` 1.307.0 → 1.323.0 ([#430](https://github.com/openkruise/agents/pull/430), [#599](https://github.com/openkruise/agents/pull/599), [#619](https://github.com/openkruise/agents/pull/619), [#652](https://github.com/openkruise/agents/pull/652), [#681](https://github.com/openkruise/agents/pull/681), [#1020](https://github.com/openkruise/agents/pull/1020)); `crate-ci/typos` 1.46.1 → 1.50.2 ([#431](https://github.com/openkruise/agents/pull/431), [#464](https://github.com/openkruise/agents/pull/464), [#498](https://github.com/openkruise/agents/pull/498), [#602](https://github.com/openkruise/agents/pull/602), [#1022](https://github.com/openkruise/agents/pull/1022)); `codecov/codecov-action` 6.0.0 → 7.1.1 ([#432](https://github.com/openkruise/agents/pull/432), [#526](https://github.com/openkruise/agents/pull/526), [#1019](https://github.com/openkruise/agents/pull/1019)); `golangci/golangci-lint-action` 9.2.0 → 9.3.0 ([#465](https://github.com/openkruise/agents/pull/465), [#601](https://github.com/openkruise/agents/pull/601)); `actions/checkout` 6.0.1 → 7.0.1 ([#500](https://github.com/openkruise/agents/pull/500), [#578](https://github.com/openkruise/agents/pull/578), [#624](https://github.com/openkruise/agents/pull/624), [#683](https://github.com/openkruise/agents/pull/683)); `actions/cache` 5.0.5 → 6.1.0 ([#575](https://github.com/openkruise/agents/pull/575), [#600](https://github.com/openkruise/agents/pull/600)); `docker/setup-qemu-action` 3 → 4 ([#622](https://github.com/openkruise/agents/pull/622)); `docker/setup-buildx-action` 4.3.0 → 4.4.1 ([#1021](https://github.com/openkruise/agents/pull/1021)); `helm/kind-action` 1.14.0 → 1.15.0 ([#977](https://github.com/openkruise/agents/pull/977)); `zizmorcore/zizmor-action` 0.6.1 → 0.6.4 ([#877](https://github.com/openkruise/agents/pull/877), [#1006](https://github.com/openkruise/agents/pull/1006)); `spf13/cobra` 1.10.0 → 1.10.2 ([#873](https://github.com/openkruise/agents/pull/873)); `container-storage-interface/spec` 1.9.0 → 1.13.0 ([#876](https://github.com/openkruise/agents/pull/876)); `google.golang.org/protobuf` 1.36.11 → 1.36.12 ([#869](https://github.com/openkruise/agents/pull/869)); `golang-x` group ([#868](https://github.com/openkruise/agents/pull/868)); `otel` group ([#867](https://github.com/openkruise/agents/pull/867)).

**Documentation & Proposals**
- Added design proposals for pause/resume checkpoints, sandbox reuse, CSI mounts, short and stable sandbox IDs, OpenTelemetry distributed tracing, and agent identity for sandbox ingress authn and outbound access; refined agent guidance; published the v0.3.0 changelog ([#467](https://github.com/openkruise/agents/pull/467), [#547](https://github.com/openkruise/agents/pull/547), [#536](https://github.com/openkruise/agents/pull/536), [#635](https://github.com/openkruise/agents/pull/635), [#604](https://github.com/openkruise/agents/pull/604), [#697](https://github.com/openkruise/agents/pull/697), [#655](https://github.com/openkruise/agents/pull/655), [#438](https://github.com/openkruise/agents/pull/438), [#383](https://github.com/openkruise/agents/pull/383), [#673](https://github.com/openkruise/agents/pull/673)).

**CI / Test Infrastructure**
- Expanded E2E coverage for E2B 2.24.0, sandbox-manager, create-with-labels, and command execution; rewrote the pytest plugin architecture; updated the Envoy base image to v1.37.3 ([#471](https://github.com/openkruise/agents/pull/471), [#518](https://github.com/openkruise/agents/pull/518), [#582](https://github.com/openkruise/agents/pull/582), [#594](https://github.com/openkruise/agents/pull/594), [#509](https://github.com/openkruise/agents/pull/509)).
- Added test coverage for open-source storage components (AgenticBucket, BucketSpace, OSS volume KMS BYOK), the access-token opt-in predicate, and time-related error paths; repaired the sandboxcr test build and made the sandbox-manager claim test repeatable ([#817](https://github.com/openkruise/agents/pull/817), [#676](https://github.com/openkruise/agents/pull/676), [#790](https://github.com/openkruise/agents/pull/790), [#532](https://github.com/openkruise/agents/pull/532), [#798](https://github.com/openkruise/agents/pull/798), [#1016](https://github.com/openkruise/agents/pull/1016)).

**Refactors**
- Cleaned up dependency layering and circular references, tidied injection code, simplified the sidecar-injection signature, extracted status-sync as a struct field, and switched E2B request context values to an unexported key type ([#474](https://github.com/openkruise/agents/pull/474), [#454](https://github.com/openkruise/agents/pull/454), [#480](https://github.com/openkruise/agents/pull/480), [#672](https://github.com/openkruise/agents/pull/672), [#902](https://github.com/openkruise/agents/pull/902)).

**Scripts & Runtime Utilities**
- Updated runtime scripts and hardened runtime command timeouts and permissions ([#516](https://github.com/openkruise/agents/pull/516), [#541](https://github.com/openkruise/agents/pull/541), [#486](https://github.com/openkruise/agents/pull/486), [#503](https://github.com/openkruise/agents/pull/503)).

**Supply-Chain Security**
- CI now runs govulncheck, zizmor, and OpenSSF Scorecard with gosec enabled; GitHub Actions were hardened, code-scanning and gosec findings were fixed, and a SECURITY.md policy was added ([#836](https://github.com/openkruise/agents/pull/836), [#921](https://github.com/openkruise/agents/pull/921), [#918](https://github.com/openkruise/agents/pull/918), [#587](https://github.com/openkruise/agents/pull/587), [#606](https://github.com/openkruise/agents/pull/606)).

**Generated Code & Release Management**
- Regenerated clients after API changes, relocated security-related files, and synced master into the release-v0.6 branch for the alpha releases ([#417](https://github.com/openkruise/agents/pull/417), [#456](https://github.com/openkruise/agents/pull/456), [#957](https://github.com/openkruise/agents/pull/957), [#999](https://github.com/openkruise/agents/pull/999)).

**Development Tooling**
- Added an E2B code-path analysis skill and extended the code-reviewer skill with a change-summary section ([#477](https://github.com/openkruise/agents/pull/477), [#583](https://github.com/openkruise/agents/pull/583)).

---

## New Contributors

* @Kuromesi made their first contribution in https://github.com/openkruise/agents/pull/397
* @oindrilakha12-ui made their first contribution in https://github.com/openkruise/agents/pull/387
* @l1b0k made their first contribution in https://github.com/openkruise/agents/pull/433
* @rakshaak29 made their first contribution in https://github.com/openkruise/agents/pull/442
* @delavet made their first contribution in https://github.com/openkruise/agents/pull/483
* @zyl1121 made their first contribution in https://github.com/openkruise/agents/pull/447
* @Jayant-kernel made their first contribution in https://github.com/openkruise/agents/pull/558
* @denverdino made their first contribution in https://github.com/openkruise/agents/pull/587
* @chacha923 made their first contribution in https://github.com/openkruise/agents/pull/563
* @yanghanlin made their first contribution in https://github.com/openkruise/agents/pull/594
* @Liquorice-Ma made their first contribution in https://github.com/openkruise/agents/pull/497
* @googs1025 made their first contribution in https://github.com/openkruise/agents/pull/545
* @singhsrijan46 made their first contribution in https://github.com/openkruise/agents/pull/613
* @ashnaaseth2325-oss made their first contribution in https://github.com/openkruise/agents/pull/584
* @ZeroCoder-dot made their first contribution in https://github.com/openkruise/agents/pull/673
* @AlbeeSo made their first contribution in https://github.com/openkruise/agents/pull/676
* @vishalmore90 made their first contribution in https://github.com/openkruise/agents/pull/708
* @silver-chard made their first contribution in https://github.com/openkruise/agents/pull/537
* @nishantbkl3345-ship-it made their first contribution in https://github.com/openkruise/agents/pull/798
* @HARSHRAJ2789 made their first contribution in https://github.com/openkruise/agents/pull/790
* @DahuK made their first contribution in https://github.com/openkruise/agents/pull/836
* @chrisliu1995 made their first contribution in https://github.com/openkruise/agents/pull/625
* @omlahore made their first contribution in https://github.com/openkruise/agents/pull/902
* @RedZapdos123 made their first contribution in https://github.com/openkruise/agents/pull/886
* @ywExcellent made their first contribution in https://github.com/openkruise/agents/pull/895
* @u7k4rs6 made their first contribution in https://github.com/openkruise/agents/pull/1016

**Full Changelog**: https://github.com/openkruise/agents/compare/v0.3.0...v0.6.0-alpha4

## v0.6.0-alpha1
> Change log since v0.3.0

Version range: v0.3.0 → v0.6.0-alpha1

---

## 1. Features

### 1.1 Security Enhancement

**Ingress & Egress Control**
- Introduced TrafficPolicy, GlobalTrafficPolicy, and SecurityProfile CRDs to drive sandbox egress control (#397, #433, #445, #448, #483, #494, #521, #588, #610, #615, #745, #746), including protocol fields, scheme matching, CRD registration in kustomization (#915), and restored API definitions (#521).
- SecurityProfile gained MCP tool access-control (#614), `headerManipulation` actions (#829), token-transformation headers (#859), and inline E2B L7 network rules (#838).
- CRD admission validation (#919) and validation/status alignment (#930) were hardened.
- Gateway now supports JWT verification with optional Runtime mTLS (#648, #561), keeps the UUID baseline when JWT is enabled (#885), aligns the traffic token header with the E2B SDK (#689), and rotates traffic access tokens (#742).
- AccessToken is masked in route log output and the debug endpoint (#607).

**Identity & Token Framework**
- Introduced a FeatureGate-controlled Security Identity Provider that issues and propagates tokens across the sandbox lifecycle (#324, #450, #460, #463, #469).
- Token issuance is gated on the `agent-name` label (#488) and deferred until the sandbox reaches Ready (#642); tokens are re-issued after resume and before CSI re-mount (#638).
- Access tokens are now issued at claim time by TokenKind (#671) and on clone (#633), with identity annotations propagated to checkpoints (#637) and storage-auth annotations injected into the clone path (#639).
- Added a SecurityTokenRefreshReconciler for proactive rotation (#475), and refactored `IssueToken` so each provider builds its own request (#632).

**TLS & Runtime Transport**
- Added a gateway CA bundle injection framework (#478) and extended `InjectAllCAIntoContainers` to cover InitContainers (#552).
- TLS-capable sandboxes now route CSI mounts (#720) and the `/init` handshake (#700) over HTTPS; a TLS runtime client wired with Secret-based material is used on claim/clone paths (#702), and the claim path is supplied with the runtime TLS bundle (#729).
- Security tokens are delivered over the resolved runtime transport (#734), and every runtime API call logs the resolved transport (#752). Upgrade hooks use TLS (#886), and self-signed leaf certificates now include SKI/AKI for Python 3.13+ compatibility (#797).


### 1.2 Operations Enhancement

**Checkpoint, Pause/Resume & Commit**
- Introduced `CheckpointControl` for the checkpoint lifecycle (#508) with a `CheckpointRestore` upgrade strategy (#670), `PersistentContents` filesystem checkpoints (#674), selectable checkpoint labels (#712, #714), and a pause path that waits for active checkpoints (#913).
- Added a `Commit` CRD (#502), a Commit controller with registry auth and job orchestration (#533), and a nerdctl commit/push execution layer (#608); commits without a CommitID skip provider deletion and pod deletion is rejected (#595).
- Resume became atomic with a placeholder pause time and a minimum timeout floor (#435), with clearer errors on client cancellation (#424). Post-resume re-runtime-init and CSI re-mount are surfaced via events and conditions (#416).
- A `PauseStrategy` (Stop / Snapshot / CloudDisk) was introduced (#713, #774) and exposed on `SandboxSet` (#839).
- Paused retention timeout handling was refined (#566), and the default failed-sandbox reserve TTL reduced to 30 minutes (#457).

**Upgrade & In-Place Update**
- Paused sandboxes can now be upgraded via `SandboxUpdateOps` (#710) using a two-phase upgrade flow (#750), with upgrade policy cleared on success (#785). The filter was relaxed to accept non-SandboxSet-controlled sandboxes (#482) and the `SandboxHashImmutablePart` check is skipped when the annotation is missing (#531). Only Running/Upgrading sandboxes are eligible candidates (#553), and sandboxes whose template already matches the patch target are skipped (#511).
- Sandbox memory now can be resized during sandbox claims (#519)
- Init-container image consistency is verified before post-resume initialization (#538); resume upgrades continue from the previous failed step (#447); init-container injection order was stabilized for backward compatibility (#513); and injected resources are preserved across resize (#462, #537).
- In-place update false-positives were fixed (#420, #557), and `ResourcesEqual` was renamed to `IsResourceSatisfied` with a relaxed comparison (#716). `SandboxInPlaceResourceResizeGate` was removed from the sandbox-manager layer (#470).

**Observability, Events & Lifecycle Tracing**
- New metrics: `sandbox_runtime_container_abnormal` (#452), `_time` metrics for abnormal states with stale-condition fixes (#591), and metric cleanup moved off the reconcile hot path via an async pool (#461).
- Events and conditions were added for pod creation failures (#626), k8s lifecycle events (#603), and controller/manager lifecycle tracing (#658).
- Proxy and infra reconciler log volume was reduced (#579), and E2B gained an optional dedicated observability listener with the empty debug endpoint removed (#858).

**Controller & SandboxSet**
- `SandboxSet` now auto-creates `SandboxTemplate` (#396), uses a legacy revision hash to prevent sandbox recreation on upgrade (#514), scopes `maxUnavailable` to a startup-failure budget (#910), and sorts scale-down candidates by priority (#803).
- Sandbox finalizer became lazy — added on pause, removed on resume (#646), and leftover pods from a previous same-name sandbox are rejected (#757).
- Status is persisted during the Pending phase (#455), and a batch claim size flag was made effective (#656) with claims scoped to namespace (#824).
- The `okactl` CLI was added for sandbox operations (#497), and multi-arch image publishing was enabled (#545).

**Cache, Informer & Performance**
- Secret-backed key storage switched from a ticker to informer-driven refresh (#421); claim hot path uses `CountActiveSandboxes` (#517); `APIReader` fallbacks were added for claimed-sandbox lookup (#423) and checkpoint wait (#522); `SandboxTemplateRef` is supported in runtime checks (#442); cache misses are returned definitively (#751); and the TrafficPolicy cache is skipped when the CRD is absent (#730).
- Gateway informer cache memory usage was reduced (#724).

**E2B Compatibility**
- Added Claude Code support (#415), pod-IP metadata (#436), E2B ≥v2.25.0 SDK-compatible API key encoding (#473), named cloned sandboxes via metadata extensions (#385), dynamically resolved sandbox domains (#649), and an unlimited default create-server timeout (#484).
- Volume API (#580, #596), Network API (#616), dimension-aware API key quota (#565), a secret-to-MySQL API key migration script (#309), and egress control injection (#397) were added.
- The E2B Volume management endpoints were temporarily disabled (#744).

**Storage & Runtime**
- RRSA-based storage authentication for on-demand CSI mounts (#568), an agent-runtime client with CSI mount API (#685), atomic `ListDir`/`Remove` filesystem operations (#723), and a storage CLI binary (#539).

**Short & Stable Sandbox IDs**
- Implemented short and stable sandbox IDs to reduce identifier length while preserving uniqueness across lifecycle operations (#686).
- Added an atomic `max` helper to support lock-free ID generation utilities (#766).

**Miscellaneous**
- Clone failures are retried (#437, #530, #542); sidecar injection moved into `PodGenerateFunc` (#520); postStart hooks are merged using a `--` separator (#555); the security metadata source was moved to sandbox annotations (#630); and a sync-charts skill was added for CRD/webhook/RBAC/identity synchronization (#916).

### 1.3 Cost Optimization

- **Sandbox recycle / return-to-pool** (#548, #609, #569) — reuse released sandboxes to avoid cold starts.
- **CheckpointRestore upgrade strategy** (#670, #674) — upgrade sandboxes via filesystem checkpoints instead of rebuilds.
- **Auto-pause and resume** (#612, #899) with probe-driven `AutoPausePolicy` (#899) and an `OnIngressTraffic` wake-on-traffic resume rule (#900, #586).
- **PoolAutoscaler** (#625) — capacity-based and cron-driven pool autoscaling with coordinated scale-up execution (#895) and a patched webhook service (#917).
- **Paused retention refinement** (#566) and **DefaultReserveFailedSandboxFor reduced to 30 minutes** (#457).
- **Reconcile hot-path async pool** for metric cleanup (#461) and **CountActiveSandboxes** for the claim hot path (#517).

---

## 2. Bug Fixes

**Core Logic**
- Prevented `ClaimSandbox` from returning `(nil, nil)` on context cancellation (#399); removed `UnsafeDisableDeepCopy` in `groupAllSandboxes` to avoid informer cache corruption (#387).
- Fixed false-positive resource change detection in in-place update (#420, #557), preserved system-injected resource fields during resize (#462, #537), and fixed TTL leak by letting Checkpoint own SandboxTemplate (#419).
- Resume during pausing is rejected with 400 (#404); pausing sandboxes are now allowed to pause (#422); `SandboxSet` legacy revision hash prevents sandbox recreation on upgrade (#514); internal labels no longer leak into sandbox pod templates (#911); invalid `SandboxClaim` retry loops are fixed (#840); sandbox cleanup uses `SandboxManager` on network-policy failures (#707).

**Lifecycle & Status**
- Sandbox status is persisted during the Pending phase (#455); resume flow decouples phase transition from pod readiness (#529); checkpoint delete expectation settles when the checkpoint is already gone (#812); pause conditions for checkpoint-disabled and pod-deleted paths are corrected (#524); pod status is synced before upgrade initialization (#912); pause waits for active checkpoints (#913); `SecurityTokenRefresh` treats absent `RuntimeInitialized` as serving (#675); clone honors request CSI mount config over checkpoint annotation (#641).

**E2B Compatibility**
- Dead sandboxes return 404 from `DescribeSandbox` to avoid SDK `ValueError` (#636, #692); `is_running` is polled after kill to avoid an async-deletion race (#645); pagination is stabilized for duplicate timestamps (#563); reserved failed-sandbox cleanup is fixed (#589); E2B traffic policy precedence is corrected (#740); Volume management endpoints are temporarily disabled (#744); resource ownership and key storage validation are hardened (#835); the configured admin key is persisted and unreadable Secret entries are skipped (#854).

**API Keys & Quota**
- Invalid API key creation returns 400 (#449); the quota anti-drift primary-loss test is stabilized under `-race` (#617); API key persistence and owner labels are hardened (#677); registry secret lookup errors are propagated (#584); the claim batch size flag now takes effect (#656); claims are scoped to namespace (#824).

**Controller / Webhook / CRD**
- Webhook controller queue bootstrap and server CertDir alignment (#654); TrafficPolicy cache setup skipped when the CRD is absent (#730); `SandboxTemplate` webhook registration fixed (#820); `PoolAutoscaler` webhook service patched (#917); `SecurityProfiles`, `GlobalSecurityProfiles`, `GlobalTrafficPolicies` registered in kustomization (#915); ops-template patch sanitization and checkpoint resume selection fixed (#793); `SandboxSet` reconcile is skipped while deleting (#856).

**Gateway & Transport**
- Traffic token header aligned with the E2B SDK (#689); traffic tokens are issued for cloned sandboxes (#728); UUID baseline preserved when JWT auth is enabled (#885); upgrade hooks use TLS (#886); self-signed leaf certificates include SKI/AKI for Python 3.13+ (#797).

**HTTP / Resource Leaks**
- Fixed an unclosed `http.Response` body in the BrowserUse endpoint handler that caused a socket leak (#708).

**Tests / CI Fixes**
- Sandbox connection method in resume (#476); checkpoint condition stabilized with `Eventually` (#592); quota fail-open and resume timeout checks hardened (#884); envoy ext_proc timeout raised and transient 504s tolerated (#906); Redis/CR state dumped on quota rebuild E2E failure (#816); E2B Build Image steps retried on runner resource failures (#647); free-disk-space step added to the e2e-e2b-mysql-latest workflow (#643); flaky background-command kill test stabilized (#651); `TestSandboxManager_DebugMaskAccessToken` stabilized (#634).

---

## 3. Chores

**Dependabot Bumps**
- `aquasecurity/trivy-action` 0.35.0 → 0.36.0 (#294); `github/codeql-action` 4.35.4 → 4.37.8 (#429, #466, #499, #527, #621, #680, #878); `ruby/setup-ruby` 1.307.0 → 1.321.0 (#430, #599, #619, #652, #681); `crate-ci/typos` 1.46.1 → 1.48.0 (#431, #464, #498, #602); `codecov/codecov-action` 6.0.0 → 7.0.0 (#432, #526); `golangci/golangci-lint-action` 9.2.0 → 9.3.0 (#465, #601); `actions/checkout` 6.0.1 → 7.0.1 (#500, #578, #624, #683); `actions/cache` 5.0.5 → 6.1.0 (#575, #600); `docker/setup-qemu-action` 3 → 4 (#622); `spf13/cobra` 1.10.0 → 1.10.2 (#873); `container-storage-interface/spec` 1.9.0 → 1.13.0 (#876); `google.golang.org/protobuf` 1.36.11 → 1.36.12 (#869); `golang-x` group (#868); `otel` group (#867); `zizmorcore/zizmor-action` 0.6.1 → 0.6.2 (#877).

**Documentation & Proposals**
- v0.3.0 changelog (#383); multi-agent development limits in AGENTS.md (#438); pause/resume checkpoint design (#467); sandbox reuse & return-to-pool design (#547); CSI mount proposal (#536); short and stable Sandbox IDs proposal (#635); OpenTelemetry distributed tracing proposal (#604); agent guidance hierarchy refined (#655); proposal authors and image reference (#673).

**CI / Test Infrastructure**
- E2E coverage expanded: fixed E2B 2.24.0 tests (#471), sandbox-manager E2E (#518), E2B create-with-labels and command execution (#582); pytest plugin architecture rewrite and CI updates (#594).
- Envoy base image updated to v1.37.3 (#509).

**Refactors**
- Dependency cleanup breaking circular and layer-violating references (#474); `doSidecarInjection` takes `*Sandbox` (#480); `syncStatusFromPod` extracted as a struct field (#672); sandbox reuse terminology renamed to "recycle" (#609); E2B request context values use an unexported key type (#902); security metadata consumed from sandbox annotations (#630); `IssueToken` no longer takes a request parameter (#632).

**Scripts & Runtime Utilities**
- `run_envd.sh` / `envd-run.sh` updates (#516, #541); `chmod` in runtime function (#486); `RunCommandWithRuntime` timeout (#503).

**Supply-Chain Security**
- CI now runs govulncheck, zizmor, and OpenSSF Scorecard, with gosec enabled (#836), and GitHub Actions hardened against zizmor/Scorecard findings (#921). Tier-1 code-scanning findings (command injection, CVEs, dependabot cooldown) were addressed (#918), gosec warnings were fixed (#587), and a SECURITY.md policy was added (#606).

**Generated Code**
- Generated client update (#417); security-related file relocations (#456).

**Open-Source Storage Tests**
- Added `AgenticBucket` and `BucketSpace` test coverage for open-source storage components (#817).


## New Contributors
* @Kuromesi made their first contribution in https://github.com/openkruise/agents/pull/397
* @oindrilakha12-ui made their first contribution in https://github.com/openkruise/agents/pull/387
* @l1b0k made their first contribution in https://github.com/openkruise/agents/pull/433
* @rakshaak29 made their first contribution in https://github.com/openkruise/agents/pull/442
* @delavet made their first contribution in https://github.com/openkruise/agents/pull/483
* @zyl1121 made their first contribution in https://github.com/openkruise/agents/pull/447
* @Jayant-kernel made their first contribution in https://github.com/openkruise/agents/pull/558
* @denverdino made their first contribution in https://github.com/openkruise/agents/pull/587
* @chacha923 made their first contribution in https://github.com/openkruise/agents/pull/563
* @yanghanlin made their first contribution in https://github.com/openkruise/agents/pull/594
* @Liquorice-Ma made their first contribution in https://github.com/openkruise/agents/pull/497
* @googs1025 made their first contribution in https://github.com/openkruise/agents/pull/545
* @singhsrijan46 made their first contribution in https://github.com/openkruise/agents/pull/613
* @ashnaaseth2325-oss made their first contribution in https://github.com/openkruise/agents/pull/584
* @ZeroCoder-dot made their first contribution in https://github.com/openkruise/agents/pull/673
* @AlbeeSo made their first contribution in https://github.com/openkruise/agents/pull/676
* @vishalmore90 made their first contribution in https://github.com/openkruise/agents/pull/708
* @silver-chard made their first contribution in https://github.com/openkruise/agents/pull/537
* @nishantbkl3345-ship-it made their first contribution in https://github.com/openkruise/agents/pull/798
* @HARSHRAJ2789 made their first contribution in https://github.com/openkruise/agents/pull/790
* @DahuK made their first contribution in https://github.com/openkruise/agents/pull/836
* @chrisliu1995 made their first contribution in https://github.com/openkruise/agents/pull/625
* @omlahore made their first contribution in https://github.com/openkruise/agents/pull/902
* @RedZapdos123 made their first contribution in https://github.com/openkruise/agents/pull/886
* @ywExcellent made their first contribution in https://github.com/openkruise/agents/pull/895

**Full Changelog**: https://github.com/openkruise/agents/compare/v0.3.0...v0.6.0-alpha1

## v0.3.0
> Change log since v0.2.0

### Key Features
- Implemented rolling update support for SandboxSet with configurable maxUnavailable policy. ([#256](https://github.com/openkruise/agents/pull/256), [@BITLiutianyang](https://github.com/BITLiutianyang))
- Introduced pluggable KeyStorage with MySQL backend for E2B API key management. ([#291](https://github.com/openkruise/agents/pull/291), [@AiRanthem](https://github.com/AiRanthem))
- Added team-based namespace isolation and team-scoped API key authorization for multi-tenant support. ([#325](https://github.com/openkruise/agents/pull/325), [@AiRanthem](https://github.com/AiRanthem))
- Added Kruise custom path-based routing protocol in sandbox-gateway, supporting `/kruise/{namespace}--{sandbox-name}/{port}/{user-defined-path}` URL format to route requests directly to sandbox pods with path rewrite. ([#278](https://github.com/openkruise/agents/pull/278), [@chengzhycn](https://github.com/chengzhycn))
- Added in-place CPU resize capability when claiming warm pool sandboxes via SandboxClaim or E2B Create API, allowing resource reconfiguration without pod recreation. ([#228](https://github.com/openkruise/agents/pull/228), [@PersistentJZH](https://github.com/PersistentJZH))
- Implemented Recreate upgrade strategy for Sandbox with preUpgrade/postUpgrade lifecycle hooks support. ([#302](https://github.com/openkruise/agents/pull/302), [@zmberg](https://github.com/zmberg))
- Introduced SandboxUpdateOps CR for batch upgrading claimed sandboxes with lifecycle hooks support. ([#307](https://github.com/openkruise/agents/pull/307), [@zmberg](https://github.com/zmberg))
- Added E2B-compatible `GET /templates` and `GET /templates/{templateID}` API endpoints for SandboxTemplate listing and retrieval. ([#265](https://github.com/openkruise/agents/pull/265), [@ZhaoQing7892](https://github.com/ZhaoQing7892))

### Performance Improvements
- Added strategic merge patch markers to CRD types to improve kubectl apply performance and reduce API server load. ([#372](https://github.com/openkruise/agents/pull/372), [@zmberg](https://github.com/zmberg))
- Optimized CSI mounting logic from serial to parallel mounting capability for faster sandbox creation. ([#290](https://github.com/openkruise/agents/pull/290), [@BH4AWS](https://github.com/BH4AWS))
- Added feature gate to cache PodLabelSelector for performance optimization. ([#259](https://github.com/openkruise/agents/pull/259), [@PersistentJZH](https://github.com/PersistentJZH))

### Observability & Metrics
- Added Prometheus metrics for Sandbox, SandboxClaim, SandboxSet and sandbox-manager lifecycle observability. ([#258](https://github.com/openkruise/agents/pull/258), [@liangxiaoping](https://github.com/liangxiaoping); [#292](https://github.com/openkruise/agents/pull/292), [@KeyOfSpectator](https://github.com/KeyOfSpectator))
- Improved claim sandbox failure diagnostics by recording retry pick failures with sandbox key and reason in ClaimMetrics, and exposing aggregated diagnostics in E2B CreateSandbox API errors. ([#356](https://github.com/openkruise/agents/pull/356), [@AiRanthem](https://github.com/AiRanthem))

### Other Notable Changes
#### sandbox-controller
- Added support for negative TTL in SandboxClaim to prevent automatic deletion of the SandboxClaim CR. ([#277](https://github.com/openkruise/agents/pull/277), [@AiRanthem](https://github.com/AiRanthem))
- Introduced SandboxMultiClusterNaming feature gate to embed cluster ID hash in sandbox generateName prefix, preventing name collisions across clusters. ([#370](https://github.com/openkruise/agents/pull/370), [@zmberg](https://github.com/zmberg))
- Added CSI dynamic remounting when resuming sandbox to ensure consistent mount state. ([#305](https://github.com/openkruise/agents/pull/305), [@BH4AWS](https://github.com/BH4AWS))

#### sandbox-manager
- Added custom CDP port support for BrowserUse API, allowing users to specify a cdpPort query parameter to proxy Chrome DevTools Protocol requests. ([#298](https://github.com/openkruise/agents/pull/298), [@AiRanthem](https://github.com/AiRanthem))
- Added support for updating Sandbox and Pod labels during E2B Create Sandbox. ([#201](https://github.com/openkruise/agents/pull/201), [@furykerry](https://github.com/furykerry))

#### Bug Fixes
- Fixed unnecessary InitRuntime execution when no agent-runtime is configured in Sandbox. ([#340](https://github.com/openkruise/agents/pull/340), [@zmberg](https://github.com/zmberg))
- Fixed E2B connect timeout extension semantics to properly handle sandbox lifecycle timeouts. ([#303](https://github.com/openkruise/agents/pull/303), [@AiRanthem](https://github.com/AiRanthem))
- Fixed pause/resume operations to be concurrency-safe under parallel requests. ([#358](https://github.com/openkruise/agents/pull/358), [@AiRanthem](https://github.com/AiRanthem))
- Fixed templateRef sandbox hashing to avoid nil template panic. ([#260](https://github.com/openkruise/agents/pull/260), [@PersistentJZH](https://github.com/PersistentJZH))
- Fixed volume injection issue when user already specified posthook containers. ([#279](https://github.com/openkruise/agents/pull/279), [@BH4AWS](https://github.com/BH4AWS))
- Fixed panic when logging sidecar config errors. ([#301](https://github.com/openkruise/agents/pull/301), [@lxs137](https://github.com/lxs137))
- Updated EnvdVersion from 0.1.1 to 0.2.10 for compatibility. ([#276](https://github.com/openkruise/agents/pull/276), [@AiRanthem](https://github.com/AiRanthem))
- Fixed checkpoint not recording CSI mount state, causing cloned pods to fail mounting. ([#275](https://github.com/openkruise/agents/pull/275), [@BH4AWS](https://github.com/BH4AWS))

#### Security
- Reduced filesystem permissions for certificate and key files to prevent unauthorized access. ([#330](https://github.com/openkruise/agents/pull/330), [@PRAteek-singHWY](https://github.com/PRAteek-singHWY))

### Misc (Chores and tests)
- Added validation for TTLAfterCompleted and WaitReadyTimeout parameters. ([#361](https://github.com/openkruise/agents/pull/361), [@BH4AWS](https://github.com/BH4AWS))
- Implemented validation for SandboxSet volume claim template mounts. ([#359](https://github.com/openkruise/agents/pull/359), [@ajatshatru01](https://github.com/ajatshatru01))
- Added Claude Code deployment guide for AI agent sandbox integration. ([#334](https://github.com/openkruise/agents/pull/334), [@bcfre](https://github.com/bcfre))
- Added comprehensive roadmap for future development. ([#271](https://github.com/openkruise/agents/pull/271), [@furykerry](https://github.com/furykerry))
- Added code-reviewer agents and OWNERS file for maintainership clarity. ([#310](https://github.com/openkruise/agents/pull/310), [@furykerry](https://github.com/furykerry))
- Added fmt-imports.sh script and applied formatting across codebase. ([#272](https://github.com/openkruise/agents/pull/272), [@PersistentJZH](https://github.com/PersistentJZH))

## v0.2.0
> Change log since v0.1.0

### Key Features
- Introduced the sandbox-gateway component to separate the data plane (ingress traffic handling) from the component sandbox-manager, enhancing system stability and fault isolation. ([#203](https://github.com/openkruise/agents/pull/203), [@chengzhycn](https://github.com/chengzhycn))
- Added support for mounting multiple NAS/OSS volumes dynamically. ([#211](https://github.com/openkruise/agents/pull/211), [@BH4AWS](https://github.com/BH4AWS))
- Enhanced E2B APIs with snapshot and clone capabilities. ([#204](https://github.com/openkruise/agents/pull/204), [@AiRanthem](https://github.com/AiRanthem))
- Implemented paginated listing and deletion of snapshots. ([#233](https://github.com/openkruise/agents/pull/233), [@AiRanthem](https://github.com/AiRanthem))
- Added protection to prevent unauthorized deletion of Sandbox Pods, and only the sandbox controller may delete them. ([#214](https://github.com/openkruise/agents/pull/214), [@zmberg](https://github.com/zmberg))
- Enabled CSI volume mounting during sandbox creation via SandboxClaim. ([#229](https://github.com/openkruise/agents/pull/229), [@BH4AWS](https://github.com/BH4AWS))
- Added support for automatically injecting runtime and CSI sidecar containers based on sandbox ConfigMap configuration. ([#232](https://github.com/openkruise/agents/pull/232), [@BH4AWS](https://github.com/BH4AWS))

### Performance Improvements
- Improved performance in large-scale sandbox creation scenarios by optimizing ListSandboxesInPool using singleflight deduplication. ([#186](https://github.com/openkruise/agents/pull/186), [@AiRanthem](https://github.com/AiRanthem))
- Introduced feature gate SandboxCreatePodRateLimitGate to enable prioritized sandbox pod creation. ([#171](https://github.com/openkruise/agents/pull/171), [@zmberg](https://github.com/zmberg))

### Other Notable Changes
#### agents-sandbox-manager
- Extended the E2B CreateSandbox API with the e2b.agents.kruise.io/never-timeout annotation to support sandboxes that never auto-delete. ([#183](https://github.com/openkruise/agents/pull/183), [@AiRanthem](https://github.com/AiRanthem))
- Enabled CreateOnNoStock by default when claiming a sandbox. ([#187](https://github.com/openkruise/agents/pull/187), [@AiRanthem](https://github.com/AiRanthem))
- Removed default timeout assignment for paused sandboxes, preventing automatic deletion. ([#196](https://github.com/openkruise/agents/pull/196), [@AiRanthem](https://github.com/AiRanthem))
- Sandbox Manager now supports filtering sandbox-related custom resources via configurable sandbox-namespace and sandbox-label-selector. ([#217](https://github.com/openkruise/agents/pull/217), [@lxs137](https://github.com/lxs137))

#### agents-sandbox-controller
- Add flag parsing support (e.g., -v) for configurable logging verbosity. ([#184](https://github.com/openkruise/agents/pull/184), [@songtao98](https://github.com/songtao98))
- Add label selector for Pod informer to reduce cache size. ([#198](https://github.com/openkruise/agents/pull/198), [@PersistentJZH](https://github.com/PersistentJZH))

### Misc (Chores and tests)
- Docs: add OpenClaw deployment guide. ([#235](https://github.com/openkruise/agents/pull/235), [@bcfre](https://github.com/bcfre))
- docs(AGENTS): add AGENTS.md. ([#237](https://github.com/openkruise/agents/pull/237), [@AiRanthem](https://github.com/AiRanthem))
- Add sandboxSet Prometheus metrics. ([#223](https://github.com/openkruise/agents/pull/223), [@ZhaoQing7892](https://github.com/ZhaoQing7892))
- agent(skills): add detailed deployment skill for Qoder. ([#170](https://github.com/openkruise/agents/pull/170), [@AiRanthem](https://github.com/AiRanthem))

## v0.1.0
### agents-sandbox-controller
- Define and manage sandboxes declaratively using the new Sandbox, SandboxClaim APIs.
- Improve performance with SandboxSet, allowing for faster sandbox creation.

### agents-sandbox-manager
- Supports the E2B mainstream protocol, providing core capabilities such as Agent sandbox creation, routing, and management.
- Extend the E2B protocol to support in-place update image and dynamic mounting of NAS/OSS within the sandbox.

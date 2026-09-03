# Change Log

## v0.6.0-alpha1
> Change log since v0.3.0

### Key Features

#### Security Identity and TLS
- Introduced security identity provider with FeatureGate-controlled token issuance, propagation, and gateway CA bundle injection. ([#324](https://github.com/openkruise/agents/pull/324), [#478](https://github.com/openkruise/agents/pull/478), [#488](https://github.com/openkruise/agents/pull/488), [#552](https://github.com/openkruise/agents/pull/552), [@BH4AWS](https://github.com/BH4AWS))
- Added SecurityTokenRefreshReconciler for proactive token rotation and deferred refresh until sandbox is Ready. ([#475](https://github.com/openkruise/agents/pull/475), [#642](https://github.com/openkruise/agents/pull/642), [@BH4AWS](https://github.com/BH4AWS))
- Issued sandbox access tokens on claim via TokenKind and re-issued after resume before CSI re-mount. ([#671](https://github.com/openkruise/agents/pull/671), [#638](https://github.com/openkruise/agents/pull/638), [#734](https://github.com/openkruise/agents/pull/734), [@BH4AWS](https://github.com/BH4AWS))
- Routed CSI mounts and /init handshake of TLS-capable sandboxes over HTTPS with Secret-based material. ([#700](https://github.com/openkruise/agents/pull/700), [#720](https://github.com/openkruise/agents/pull/720), [#702](https://github.com/openkruise/agents/pull/702), [#685](https://github.com/openkruise/agents/pull/685), [#723](https://github.com/openkruise/agents/pull/723), [#752](https://github.com/openkruise/agents/pull/752), [@BH4AWS](https://github.com/BH4AWS))
- Added JWT verification and optional Runtime mTLS in sandbox-gateway. ([#648](https://github.com/openkruise/agents/pull/648), [#561](https://github.com/openkruise/agents/pull/561), [@chengzhycn](https://github.com/chengzhycn))
- Delivered security tokens over the resolved runtime transport. ([#734](https://github.com/openkruise/agents/pull/734), [@BH4AWS](https://github.com/BH4AWS))

#### Traffic Policy and Security Profile
- Added TrafficPolicy, GlobalTrafficPolicy, and SecurityProfile CRDs for sandbox egress control and security rules. ([#397](https://github.com/openkruise/agents/pull/397), [#433](https://github.com/openkruise/agents/pull/433), [#588](https://github.com/openkruise/agents/pull/588), [#483](https://github.com/openkruise/agents/pull/483), [#448](https://github.com/openkruise/agents/pull/448), [#610](https://github.com/openkruise/agents/pull/610), [#745](https://github.com/openkruise/agents/pull/745), [#746](https://github.com/openkruise/agents/pull/746), [@Kuromesi](https://github.com/Kuromesi); [@l1b0k](https://github.com/l1b0k); [@delavet](https://github.com/delavet))
- Added MCP tool access control policy and headerManipulation action to SecurityProfile. ([#614](https://github.com/openkruise/agents/pull/614), [#829](https://github.com/openkruise/agents/pull/829), [#859](https://github.com/openkruise/agents/pull/859), [@l1b0k](https://github.com/l1b0k); [@delavet](https://github.com/delavet); [@Kuromesi](https://github.com/Kuromesi))
- Supported E2B inline security rules and network L7 rules. ([#838](https://github.com/openkruise/agents/pull/838), [@delavet](https://github.com/delavet))
- Implemented wake-on-traffic for paused sandboxes with OnIngressTraffic resume rule. ([#586](https://github.com/openkruise/agents/pull/586), [#900](https://github.com/openkruise/agents/pull/900), [@furykerry](https://github.com/furykerry))
- Rotated traffic access tokens and corrected E2B traffic policy precedence. ([#742](https://github.com/openkruise/agents/pull/742), [#740](https://github.com/openkruise/agents/pull/740), [#689](https://github.com/openkruise/agents/pull/689), [@chengzhycn](https://github.com/chengzhycn))

#### Sandbox Pause, Resume, Checkpoint, and Recycle
- Implemented CheckpointControl for pause/resume checkpoint lifecycle with CheckpointRestore upgrade strategy. ([#508](https://github.com/openkruise/agents/pull/508), [#670](https://github.com/openkruise/agents/pull/670), [#674](https://github.com/openkruise/agents/pull/674), [#712](https://github.com/openkruise/agents/pull/712), [#714](https://github.com/openkruise/agents/pull/714), [@zmberg](https://github.com/zmberg); [@AiRanthem](https://github.com/AiRanthem))
- Added PauseStrategy with Stop, Snapshot, and CloudDisk types; supported PauseStrategy on SandboxSet. ([#713](https://github.com/openkruise/agents/pull/713), [#774](https://github.com/openkruise/agents/pull/774), [#839](https://github.com/openkruise/agents/pull/839), [@zmberg](https://github.com/zmberg))
- Implemented sandbox reuse and return-to-pool (recycle) lifecycle with two-phase upgrade for paused sandboxes. ([#548](https://github.com/openkruise/agents/pull/548), [#609](https://github.com/openkruise/agents/pull/609), [#750](https://github.com/openkruise/agents/pull/750), [#710](https://github.com/openkruise/agents/pull/710), [#605](https://github.com/openkruise/agents/pull/605), [@zmberg](https://github.com/zmberg))
- Added Probes and AutoPausePolicy for sandbox auto-pause and resume. ([#612](https://github.com/openkruise/agents/pull/612), [#899](https://github.com/openkruise/agents/pull/899), [@zmberg](https://github.com/zmberg))
- Supported upgrading paused sandboxes via SandboxUpdateOps. ([#710](https://github.com/openkruise/agents/pull/710), [@zmberg](https://github.com/zmberg))

#### Sandbox Commit
- Added Commit CRD type definition and Commit controller with registry auth and job orchestration. ([#502](https://github.com/openkruise/agents/pull/502), [#533](https://github.com/openkruise/agents/pull/533), [#608](https://github.com/openkruise/agents/pull/608), [#595](https://github.com/openkruise/agents/pull/595), [@Luckydog691](https://github.com/Luckydog691))

#### PoolAutoscaler
- Added PoolAutoscaler CRD with capacity-based and cron scaling, coordinated scale-up execution. ([#625](https://github.com/openkruise/agents/pull/625), [#895](https://github.com/openkruise/agents/pull/895), [@chrisliu1995](https://github.com/chrisliu1995); [@ywExcellent](https://github.com/ywExcellent))

#### E2B Protocol Extensions
- Added E2B >=v2.25.0 SDK-compatible API key encoding layer with dimension-aware quota. ([#473](https://github.com/openkruise/agents/pull/473), [#565](https://github.com/openkruise/agents/pull/565), [@AiRanthem](https://github.com/AiRanthem))
- Supported naming cloned sandbox via metadata extensions and resolved sandbox domains dynamically. ([#385](https://github.com/openkruise/agents/pull/385), [#649](https://github.com/openkruise/agents/pull/649), [@AiRanthem](https://github.com/AiRanthem))
- Added short and stable sandbox IDs. ([#686](https://github.com/openkruise/agents/pull/686), [@AiRanthem](https://github.com/AiRanthem))
- Added E2B volume and network API endpoints. ([#580](https://github.com/openkruise/agents/pull/580), [#616](https://github.com/openkruise/agents/pull/616), [#596](https://github.com/openkruise/agents/pull/596), [@ZhaoQing7892](https://github.com/ZhaoQing7892))
- Added okactl command-line tool for sandbox operations. ([#497](https://github.com/openkruise/agents/pull/497), [@Liquorice-Ma](https://github.com/Liquorice-Ma))
- Supported memory resize for sandbox claims. ([#519](https://github.com/openkruise/agents/pull/519), [@PersistentJZH](https://github.com/PersistentJZH))

#### Other Features
- Added egress control injection with followup updates. ([#397](https://github.com/openkruise/agents/pull/397), [#445](https://github.com/openkruise/agents/pull/445), [@Kuromesi](https://github.com/Kuromesi))
- Added sandbox reuse lifecycle: lazy sandbox finalizer (add on pause, remove on resume). ([#646](https://github.com/openkruise/agents/pull/646), [@furykerry](https://github.com/furykerry))
- Auto-created SandboxTemplate for SandboxSet. ([#396](https://github.com/openkruise/agents/pull/396), [@BITLiutianyang](https://github.com/BITLiutianyang))
- Added agent-runtime client with CSI storage mount API and RRSA storage authentication. ([#685](https://github.com/openkruise/agents/pull/685), [#568](https://github.com/openkruise/agents/pull/568), [@BH4AWS](https://github.com/BH4AWS))
- Narrowed maxUnavailable to startup-failure budget. ([#910](https://github.com/openkruise/agents/pull/910), [@furykerry](https://github.com/furykerry))
- Added lifecycle tracing for controller and manager. ([#658](https://github.com/openkruise/agents/pull/658), [@Liquorice-Ma](https://github.com/Liquorice-Ma))
- Added support for Claude Code. ([#415](https://github.com/openkruise/agents/pull/415), [@AiRanthem](https://github.com/AiRanthem))

### Performance Improvements
- Moved metric cleanup off the Reconcile hot path via async pool. ([#461](https://github.com/openkruise/agents/pull/461), [@KeyOfSpectator](https://github.com/KeyOfSpectator))
- Reduced informer cache memory in sandbox-gateway. ([#724](https://github.com/openkruise/agents/pull/724), [@chengzhycn](https://github.com/chengzhycn))
- Added CountActiveSandboxes to optimize claim hot path. ([#517](https://github.com/openkruise/agents/pull/517), [@Luckydog691](https://github.com/Luckydog691))

### Observability and Metrics
- Added sandbox_runtime_container_abnormal metric for runtime containers. ([#452](https://github.com/openkruise/agents/pull/452), [@zmberg](https://github.com/zmberg))
- Fixed stale condition metrics and added _time metrics for abnormal states. ([#591](https://github.com/openkruise/agents/pull/591), [@liangxiaoping](https://github.com/liangxiaoping))
- Added k8s lifecycle events. ([#603](https://github.com/openkruise/agents/pull/603), [@chacha923](https://github.com/chacha923))
- Emitted event and set condition on pod creation failure. ([#626](https://github.com/openkruise/agents/pull/626), [@zmberg](https://github.com/zmberg))

### Bug Fixes

#### sandbox-controller
- Persisted sandbox status during Pending phase. ([#455](https://github.com/openkruise/agents/pull/455), [@zmberg](https://github.com/zmberg))
- Stabilized init container injection order for backward compatibility. ([#513](https://github.com/openkruise/agents/pull/513), [@BH4AWS](https://github.com/BH4AWS))
- Added legacy revision hash compat to prevent sandbox recreation on upgrade. ([#514](https://github.com/openkruise/agents/pull/514), [@zmberg](https://github.com/zmberg))
- Corrected pause condition reasons for checkpoint-disabled and pod-deleted paths. ([#524](https://github.com/openkruise/agents/pull/524), [@zmberg](https://github.com/zmberg))
- Skipped sandboxes whose template already matches patch target. ([#511](https://github.com/openkruise/agents/pull/511), [@zmberg](https://github.com/zmberg))
- Only allowed Running/Upgrading sandboxes as upgrade candidates. ([#553](https://github.com/openkruise/agents/pull/553), [@zmberg](https://github.com/zmberg))
- Handled edge cases in sandbox reuse lifecycle. ([#569](https://github.com/openkruise/agents/pull/569), [@zmberg](https://github.com/zmberg))
- Rejected leftover pod from a previous same-name sandbox. ([#757](https://github.com/openkruise/agents/pull/757), [@furykerry](https://github.com/furykerry))
- Cleared sandbox upgrade policy once upgrade succeeded. ([#785](https://github.com/openkruise/agents/pull/785), [@zmberg](https://github.com/zmberg))
- Ops template patch sanitization and checkpoint resume selection. ([#793](https://github.com/openkruise/agents/pull/793), [@zmberg](https://github.com/zmberg))
- Skipped SandboxSet reconcile when deleting. ([#856](https://github.com/openkruise/agents/pull/856), [@AiRanthem](https://github.com/AiRanthem))
- Prevented internal labels leaking into sandbox pod template. ([#911](https://github.com/openkruise/agents/pull/911), [@Luckydog691](https://github.com/Luckydog691))
- Waited for active checkpoints before pause. ([#913](https://github.com/openkruise/agents/pull/913), [@zmberg](https://github.com/zmberg))
- Synced pod status before upgrade initialization. ([#912](https://github.com/openkruise/agents/pull/912), [@zmberg](https://github.com/zmberg))
- Sorted old candidates by scale-down priority before deletion. ([#803](https://github.com/openkruise/agents/pull/803), [@vishalmore90](https://github.com/vishalmore90))
- Settled the checkpoint delete expectation when the checkpoint is already gone. ([#812](https://github.com/openkruise/agents/pull/812), [@HARSHRAJ2789](https://github.com/HARSHRAJ2789))
- Used TLS for upgrade hooks. ([#886](https://github.com/openkruise/agents/pull/886), [@RedZapdos123](https://github.com/RedZapdos123))

#### sandbox-manager
- Prevented ClaimSandbox returning (nil, nil) on context cancel. ([#399](https://github.com/openkruise/agents/pull/399), [@AiRanthem](https://github.com/AiRanthem))
- Removed UnsafeDisableDeepCopy in groupAllSandboxes to prevent informer cache corruption. ([#387](https://github.com/openkruise/agents/pull/387), [@oindrilakha12-ui](https://github.com/oindrilakha12-ui))
- Bounded create retry behavior and normalized rate limiter deadline error in clone. ([#542](https://github.com/openkruise/agents/pull/542), [#530](https://github.com/openkruise/agents/pull/530), [@AiRanthem](https://github.com/AiRanthem))
- Handled reserved failed sandbox cleanup. ([#589](https://github.com/openkruise/agents/pull/589), [@AiRanthem](https://github.com/AiRanthem))
- Reduced log volume in proxy and infra reconciler. ([#579](https://github.com/openkruise/agents/pull/579), [@AiRanthem](https://github.com/AiRanthem))
- Issued traffic tokens for cloned sandboxes. ([#728](https://github.com/openkruise/agents/pull/728), [@chengzhycn](https://github.com/chengzhycn))
- Scoped claims to namespace. ([#824](https://github.com/openkruise/agents/pull/824), [@googs1025](https://github.com/googs1025))
- Fixed invalid SandboxClaim retry loop. ([#840](https://github.com/openkruise/agents/pull/840), [@googs1025](https://github.com/googs1025))
- Fixed sandbox cleanup to use SandboxManager on network policy failure. ([#707](https://github.com/openkruise/agents/pull/707), [@vishalmore90](https://github.com/vishalmore90))

#### E2B API
- Atomic Resume with placeholder pausetime and min timeout floor. ([#435](https://github.com/openkruise/agents/pull/435), [@AiRanthem](https://github.com/AiRanthem))
- Allowed pause sandboxes in pausing state; rejected resume during pausing with 400. ([#422](https://github.com/openkruise/agents/pull/422), [#404](https://github.com/openkruise/agents/pull/404), [@AiRanthem](https://github.com/AiRanthem))
- Returned 404 for dead sandboxes in DescribeSandbox to avoid SDK ValueError. ([#636](https://github.com/openkruise/agents/pull/636), [@furykerry](https://github.com/furykerry))
- Described dead sandboxes and mapped not-ready running state. ([#692](https://github.com/openkruise/agents/pull/692), [@furykerry](https://github.com/furykerry))
- Stabilized pagination for duplicate timestamps. ([#563](https://github.com/openkruise/agents/pull/563), [@chacha923](https://github.com/chacha923))
- Polled is_running after kill to avoid async deletion race. ([#645](https://github.com/openkruise/agents/pull/645), [@furykerry](https://github.com/furykerry))
- Hardened resource ownership and key storage validation. ([#835](https://github.com/openkruise/agents/pull/835), [@AiRanthem](https://github.com/AiRanthem))
- Persisted configured admin key and skipped unreadable Secret entries. ([#854](https://github.com/openkruise/agents/pull/854), [@AiRanthem](https://github.com/AiRanthem))
- Made create server timeout unlimited by default. ([#484](https://github.com/openkruise/agents/pull/484), [@AiRanthem](https://github.com/AiRanthem))
- Returned pod ip metadata. ([#436](https://github.com/openkruise/agents/pull/436), [@AiRanthem](https://github.com/AiRanthem))
- Returned bad request for invalid API key creation. ([#449](https://github.com/openkruise/agents/pull/449), [@AiRanthem](https://github.com/AiRanthem))

#### In-place Update
- Fixed false-positive resource change detection. ([#420](https://github.com/openkruise/agents/pull/420), [@zmberg](https://github.com/zmberg))
- Merged resource lists to preserve system-injected fields during resize. ([#462](https://github.com/openkruise/agents/pull/462), [@zmberg](https://github.com/zmberg))
- Preserved injected resources during resize. ([#537](https://github.com/openkruise/agents/pull/537), [@silver-chard](https://github.com/silver-chard))
- Avoided triggering in-place update for metadata-only changes. ([#557](https://github.com/openkruise/agents/pull/557), [@furykerry](https://github.com/furykerry))

#### Other Fixes
- Replaced ticker with informer-driven refresh for secret-backed key storage. ([#421](https://github.com/openkruise/agents/pull/421), [@AiRanthem](https://github.com/AiRanthem))
- Avoided misleading wait hook change logs. ([#573](https://github.com/openkruise/agents/pull/573), [@Jayant-kernel](https://github.com/Jayant-kernel))
- Masked AccessToken in Route log output and debug endpoint. ([#607](https://github.com/openkruise/agents/pull/607), [@chengzhycn](https://github.com/chengzhycn))
- Added SKI/AKI to self-signed leaf certs for Python 3.13+. ([#797](https://github.com/openkruise/agents/pull/797), [@AiRanthem](https://github.com/AiRanthem))
- Fixed unclosed http.Response Body in BrowserUse endpoint handler (socket leak). ([#708](https://github.com/openkruise/agents/pull/708), [@vishalmore90](https://github.com/vishalmore90))
- Returned registry secret lookup errors from resolveRegistrySecretName. ([#584](https://github.com/openkruise/agents/pull/584), [@ashnaaseth2325-oss](https://github.com/ashnaaseth2325-oss))
- Webhook registration for SandboxTemplate. ([#820](https://github.com/openkruise/agents/pull/820), [@googs1025](https://github.com/googs1025))
- Bootstrapped controller queue and aligned server CertDir. ([#654](https://github.com/openkruise/agents/pull/654), [@Luckydog691](https://github.com/Luckydog691))
- Made claim batch size flag actually take effect. ([#656](https://github.com/openkruise/agents/pull/656), [@Luckydog691](https://github.com/Luckydog691))
- Kept the UUID baseline when JWT auth is enabled in sandbox-gateway. ([#885](https://github.com/openkruise/agents/pull/885), [@chengzhycn](https://github.com/chengzhycn))
- Normalized invalid gateway server ports to the default port. ([#613](https://github.com/openkruise/agents/pull/613), [@singhsrijan46](https://github.com/singhsrijan46))
- Enforced CRD admission validation and aligned CRD validation and status. ([#919](https://github.com/openkruise/agents/pull/919), [#930](https://github.com/openkruise/agents/pull/930), [@furykerry](https://github.com/furykerry))
- Registered SecurityProfiles, GlobalSecurityProfiles and GlobalTrafficPolicies CRDs in kustomization. ([#915](https://github.com/openkruise/agents/pull/915), [@furykerry](https://github.com/furykerry))
- Patched PoolAutoscaler webhook service. ([#917](https://github.com/openkruise/agents/pull/917), [@furykerry](https://github.com/furykerry))

### Security
- Added govulncheck, zizmor and Scorecard scans; enabled gosec. ([#836](https://github.com/openkruise/agents/pull/836), [@DahuK](https://github.com/DahuK))
- Addressed Tier 1 code-scanning findings (command-injection, CVEs, dependabot cooldown). ([#918](https://github.com/openkruise/agents/pull/918), [@furykerry](https://github.com/furykerry))
- Hardened GitHub Actions against zizmor and Scorecard findings. ([#921](https://github.com/openkruise/agents/pull/921), [@furykerry](https://github.com/furykerry))
- Fixed gosec warnings. ([#587](https://github.com/openkruise/agents/pull/587), [@denverdino](https://github.com/denverdino))
- Added Security Policy. ([#606](https://github.com/openkruise/agents/pull/606), [@denverdino](https://github.com/denverdino))

### Misc (Chores, Tests, Refactoring, and Docs)
- Dependency Cleanup: Breaking Circular and Layer-Violating References. ([#474](https://github.com/openkruise/agents/pull/474), [@furykerry](https://github.com/furykerry))
- Refactored checkpoint to own SandboxTemplate (fix TTL leak). ([#419](https://github.com/openkruise/agents/pull/419), [@AiRanthem](https://github.com/AiRanthem))
- Optimized resume flow by decoupling phase transition from pod readiness. ([#529](https://github.com/openkruise/agents/pull/529), [@zmberg](https://github.com/zmberg))
- Moved sidecar injection into PodGenerateFunc for generator-agnostic control. ([#520](https://github.com/openkruise/agents/pull/520), [@zmberg](https://github.com/zmberg))
- Added multi-arch image publishing. ([#545](https://github.com/openkruise/agents/pull/545), [@googs1025](https://github.com/googs1025))
- Updated envoy base image to v1.37.3. ([#509](https://github.com/openkruise/agents/pull/509), [@chengzhycn](https://github.com/chengzhycn))
- Pytest plugin architecture, test runner rewrite, and CI updates. ([#594](https://github.com/openkruise/agents/pull/594), [@yanghanlin](https://github.com/yanghanlin))
- Expanded sandbox-manager E2E coverage. ([#518](https://github.com/openkruise/agents/pull/518), [#582](https://github.com/openkruise/agents/pull/582), [#816](https://github.com/openkruise/agents/pull/816), [#884](https://github.com/openkruise/agents/pull/884), [#790](https://github.com/openkruise/agents/pull/790), [#817](https://github.com/openkruise/agents/pull/817), [@AiRanthem](https://github.com/AiRanthem); [@furykerry](https://github.com/furykerry); [@HARSHRAJ2789](https://github.com/HARSHRAJ2789); [@AlbeeSo](https://github.com/AlbeeSo))
- Added pause/resume checkpoint design spec. ([#467](https://github.com/openkruise/agents/pull/467), [@zmberg](https://github.com/zmberg))
- Added sandbox reuse and return-to-pool design spec. ([#547](https://github.com/openkruise/agents/pull/547), [@zmberg](https://github.com/zmberg))
- Proposed short and stable Sandbox IDs. ([#635](https://github.com/openkruise/agents/pull/635), [@AiRanthem](https://github.com/AiRanthem))
- Added OpenTelemetry distributed tracing proposal. ([#604](https://github.com/openkruise/agents/pull/604), [@Liquorice-Ma](https://github.com/Liquorice-Ma))
- Added secret-to-mysql API key migration script. ([#309](https://github.com/openkruise/agents/pull/309), [@AiRanthem](https://github.com/AiRanthem))

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

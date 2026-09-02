# API Admission Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce API-server admission semantics for named probes and PoolAutoscaler configuration through generated CRD schemas.

**Architecture:** Change only declarative Kubebuilder markers and JSON field tags in `api/v1alpha1`; controllers and admission webhooks remain unchanged. Run the repository generator so the CRD OpenAPI schemas reflect list-map ownership, required `spec`, and the Probe name contract.

**Tech Stack:** Go, Kubebuilder markers, controller-gen, Kubernetes CustomResourceDefinitions.

---

## File Structure

- Modify: `api/v1alpha1/sandbox_types.go:81-92,227-232` — declare the Sandbox probe list as keyed by `name` and constrain probe names.
- Modify: `api/v1alpha1/sandboxset_types.go:109-115` — declare the SandboxSet probe list as keyed by `name`.
- Modify: `api/v1alpha1/sandboxtemplate_types.go:55-61` — declare the SandboxTemplate probe list as keyed by `name`.
- Modify: `api/v1alpha1/poolautoscaler_types.go:59-62,162-164,226-228` — declare cron-policy lists as keyed by `name` and make the root `spec` required.
- Modify (generated): `api/v1alpha1/zz_generated.deepcopy.go` and generated typed-client files only if `make generate` changes them.
- Modify (generated): `config/crd/bases/agents.kruise.io_sandboxes.yaml`, `config/crd/bases/agents.kruise.io_sandboxsets.yaml`, `config/crd/bases/agents.kruise.io_sandboxtemplates.yaml`, and `config/crd/bases/agents.kruise.io_poolautoscalers.yaml` — regenerated OpenAPI schemas.
- No test source is added, per the approved scope.

### Task 1: Declare API List Semantics and Validation

**Files:**
- Modify: `api/v1alpha1/sandbox_types.go:81-92,227-232`
- Modify: `api/v1alpha1/sandboxset_types.go:109-115`
- Modify: `api/v1alpha1/sandboxtemplate_types.go:55-61`
- Modify: `api/v1alpha1/poolautoscaler_types.go:59-62,162-164,226-228`

- [ ] **Step 1: Make all probe lists map lists keyed by `name`**

  In each `Probes []Probe` declaration, retain `+optional` and use these markers directly above the field:

  ```go
  // +optional
  // +listType=map
  // +listMapKey=name
  Probes []Probe `json:"probes,omitempty"`
  ```

  Replace the existing `+listType=atomic` marker in `SandboxSetSpec.Probes` and `SandboxTemplateSpec.Probes`; add both map-list markers to `SandboxSpec.Probes`.

- [ ] **Step 2: Constrain `Probe.Name` to a condition-type suffix**

  In `Probe.Name`, retain the existing required marker and add the maximum-length and regular-expression markers:

  ```go
  // +kubebuilder:validation:Required
  // +kubebuilder:validation:MaxLength=299
  // +kubebuilder:validation:Pattern=`^[A-Za-z0-9]([-A-Za-z0-9_.]*[A-Za-z0-9])?$`
  Name string `json:"name"`
  ```

  This accepts a single alphanumeric character or an alphanumeric-delimited suffix containing alphanumerics, hyphens, underscores, and dots. It rejects empty values and leading or trailing punctuation, while reserving 17 characters for the `agents.kruise.io/` prefix within the 316-character `metav1.Condition.Type` maximum.

- [ ] **Step 3: Make cron-policy lists map lists keyed by `name`**

  Keep both fields optional and add the list markers directly above them:

  ```go
  // +optional
  // +listType=map
  // +listMapKey=name
  CronPolicies []CronScalingPolicy `json:"cronPolicies,omitempty"`
  ```

  ```go
  // +optional
  // +listType=map
  // +listMapKey=name
  AppliedCronPolicies []CronScalingPolicyStatus `json:"appliedCronPolicies,omitempty"`
  ```

- [ ] **Step 4: Make `PoolAutoscaler.Spec` required**

  Remove its `+optional` marker and change only the JSON tag:

  ```go
  // Spec defines the desired behavior of the autoscaler.
  Spec PoolAutoscalerSpec `json:"spec"`
  ```

  Do not add webhook logic or modify controller behavior.

- [ ] **Step 5: Format the hand-written API files**

  Run:

  ```bash
  gofmt -w api/v1alpha1/sandbox_types.go api/v1alpha1/sandboxset_types.go api/v1alpha1/sandboxtemplate_types.go api/v1alpha1/poolautoscaler_types.go
  ```

  Expected: the command exits with status 0 and changes only Go formatting where needed.

### Task 2: Regenerate and Inspect API Artifacts

**Files:**
- Modify (generated): `api/v1alpha1/zz_generated.deepcopy.go` and generated typed-client files only if the generator updates them.
- Modify (generated): `config/crd/bases/agents.kruise.io_sandboxes.yaml`
- Modify (generated): `config/crd/bases/agents.kruise.io_sandboxsets.yaml`
- Modify (generated): `config/crd/bases/agents.kruise.io_sandboxtemplates.yaml`
- Modify (generated): `config/crd/bases/agents.kruise.io_poolautoscalers.yaml`

- [ ] **Step 1: Regenerate API code and manifests**

  Run:

  ```bash
  make generate manifests
  ```

  Expected: controller-gen completes successfully; generated Go artifacts and CRD YAML reflect the API definitions. Do not edit generated files manually.

- [ ] **Step 2: Inspect the generated OpenAPI changes**

  Run:

  ```bash
  git diff --check
  git diff -- config/crd/bases/agents.kruise.io_sandboxes.yaml config/crd/bases/agents.kruise.io_sandboxsets.yaml config/crd/bases/agents.kruise.io_sandboxtemplates.yaml config/crd/bases/agents.kruise.io_poolautoscalers.yaml
  ```

  Expected CRD schema changes:

  ```yaml
  x-kubernetes-list-type: map
  x-kubernetes-list-map-keys:
  - name
  ```

  appear for all three `probes` schemas, `cronPolicies`, and `appliedCronPolicies`; every generated `Probe.name` schema contains `maxLength: 299` and the requested pattern; and the PoolAutoscaler version schema lists `spec` in `required`.

- [ ] **Step 3: Run focused package validation**

  Run:

  ```bash
  go test ./api/v1alpha1
  ```

  Expected: exit status 0. This confirms the modified API package compiles; no new test source is added in this approved scope.

- [ ] **Step 4: Review the final change set**

  Run:

  ```bash
  git status --short
  git diff --check
  git diff -- api/v1alpha1/sandbox_types.go api/v1alpha1/sandboxset_types.go api/v1alpha1/sandboxtemplate_types.go api/v1alpha1/poolautoscaler_types.go config/crd/bases
  ```

  Expected: only the approved API type markers/tags, regenerated artifacts, and the already-approved specification/plan files are modified. No wake-on-traffic annotation, controller, webhook, or test-code changes are present.

## Plan Self-Review

- **Spec coverage:** Task 1 covers all five map-list declarations, the `PoolAutoscaler.Spec` requiredness change, and the exact Probe name regular expression and length. Task 2 covers generator output and schema inspection.
- **Scope:** The plan explicitly excludes wake annotation changes, controller/webhook changes, manual generated-file edits, test-source additions, and commits.
- **Consistency:** The plan uses the existing `Probe`, `CronScalingPolicy`, and `CronScalingPolicyStatus` fields and the repository's `make generate manifests` command.

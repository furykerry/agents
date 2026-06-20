# Running Qoder CLI Sandbox

This example demonstrates how to deploy [Qoder CLI](https://www.npmjs.com/package/@qoder-ai/qodercli) via OpenKruise Agents. Use the E2B SDK to obtain a Qoder CLI instance from the warm pool and execute programming tasks such as code writing, debugging, and task automation.

## 0. Basic Concepts

### Qoder CLI

`Qoder CLI` is an AI-powered programming assistant CLI tool. By deploying Qoder CLI with OpenKruise Agents, you can provide each user with an independent, securely isolated sandbox environment with persistent workspace storage for programming tasks.

### Data Persistence

This example uses `volumeClaimTemplates` to automatically create independent cloud disks for each Sandbox, ensuring code and data persist across sandbox pause/resume cycles.

---

## 1. Prerequisites

### 1.1 Obtain API Key

Qoder CLI uses an OpenAI-compatible API. You need to provide an API key from your preferred provider:

```bash
# Example: Alibaba Cloud DashScope (Bailian)
export OPENAI_API_KEY="sk-****"
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export OPENAI_MODEL="qwen-plus"
```

Other compatible providers work as well (Azure OpenAI, custom endpoints, etc.).

### 1.2 Install E2B SDK

```bash
pip install e2b-code-interpreter
```

### 1.3 Configure Sandbox Manager Connection

```bash
export E2B_DOMAIN=your.domain
export E2B_API_KEY=your-token
# If using self-signed certificates
export SSL_CERT_FILE=/path/to/ca-fullchain.pem
```

---

## 2. Build and Push the Sandbox Image

### 2.1 Build the Image

Build the Qoder CLI sandbox image using the provided Dockerfile:

```bash
cd examples/qoder-cli
docker build -t your-registry/qoder-cli:v0.1 .
```

### 2.2 Push to Container Registry

```bash
docker push your-registry/qoder-cli:v0.1
```

> **Tip**: Replace `your-registry` with your actual container registry address (e.g., `registry-cn-hangzhou.ack.aliyuncs.com/acs`).

---

## 3. Deploy Qoder CLI Warm Pool

### 3.1 Deploy via SandboxSet

Create a SandboxSet to deploy the Qoder CLI warm pool. Refer to [sandboxset.yaml](sandboxset.yaml):

```yaml
apiVersion: agents.kruise.io/v1alpha1
kind: SandboxSet
metadata:
  name: qoder-cli-sbs
  namespace: default
spec:
  replicas: 3
  runtimes:
  - name: agent-runtime
  template:
    metadata:
      labels:
        app: qoder-cli
    spec:
      containers:
        - name: qoder-cli
          image: your-registry/qoder-cli:v0.1
          resources:
            requests:
              cpu: 2
              memory: 4Gi
            limits:
              cpu: 2
              memory: 4Gi
          volumeMounts:
            - name: qoder-workspace
              mountPath: /workspace
          startupProbe:
            failureThreshold: 20
            httpGet:
              path: /health
              port: 49999
            initialDelaySeconds: 1
            periodSeconds: 2
            timeoutSeconds: 1
  volumeClaimTemplates:
  - metadata:
      name: qoder-workspace
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: "alicloud-disk-ssd"
      resources:
        requests:
          storage: 20Gi
```

**Key fields:**

| Field | Description |
|-------|-------------|
| `runtimes` | Uses the built-in `agent-runtime` injection — the controller automatically injects the envd sidecar for E2B-compatible remote operations |
| `volumeClaimTemplates` | Each sandbox gets its own 20Gi persistent disk mounted at `/workspace` |
| `storageClassName` | Replace with a StorageClass available in your cluster |
| `startupProbe` | Checks the agent-runtime health endpoint on port 49999 |

### 3.2 Verify Deployment

```bash
# Deploy SandboxSet
kubectl apply -f sandboxset.yaml

# Check warm pool status
kubectl get sbs qoder-cli-sbs

# Expected output
NAME              REPLICAS   AVAILABLE   UPDATEREVISION   AGE
qoder-cli-sbs     3          3           xxxxxxxx         2m

# Check available Sandboxes
kubectl get sbx -l agents.kruise.io/sandbox-pool=qoder-cli-sbs \
                -l agents.kruise.io/sandbox-claimed=false
```

---

## 4. Use Qoder CLI via E2B SDK

### 4.1 Claim a Sandbox and Run a Task

```python
import os
import json
from e2b_code_interpreter import Sandbox

# Claim a sandbox instance from the warm pool
sbx = Sandbox.create(template="qoder-cli-sbs", timeout=3600)
print(f"Sandbox ID: {sbx.sandbox_id}")

# Configure LLM environment variables
envs = {
    "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
    "OPENAI_BASE_URL": os.environ.get("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    "OPENAI_MODEL": os.environ.get("OPENAI_MODEL", "qwen-plus"),
}

# Run a coding task
result = sbx.commands.run(
    'qoder --output-format json -p "Create a Python Flask web app with a /health endpoint at /workspace/app.py"',
    envs=envs,
    timeout=600,
    cwd="/workspace",
)

# Parse session ID for multi-turn conversation
output = json.loads(result.stdout)
session_id = output["session_id"]
print(f"Session ID: {session_id}")
```

### 4.2 Multi-Turn Conversation

Use `--resume` with the session ID to continue a conversation:

```python
result = sbx.commands.run(
    f'qoder --output-format json --resume {session_id} -p "Add unit tests for the Flask app using pytest"',
    envs=envs,
    timeout=600,
    cwd="/workspace",
)
print(result.stdout)
```

### 4.3 File Operations

Read and write files in the persistent workspace:

```python
# Read generated files
result = sbx.commands.run("cat /workspace/app.py", timeout=10)
print(result.stdout)

# Write a file via the SDK
sbx.files.write("/workspace/requirements.txt", "flask\npytest\n", user="root")

# List workspace contents
result = sbx.commands.run("ls -la /workspace", timeout=10)
print(result.stdout)
```

### 4.4 Pause and Resume

> Note: Memory state preservation during pause/resume is only supported on Alibaba Cloud ACS.

```python
# Pause the sandbox (state is saved to disk)
sbx.beta_pause()

# Resume the sandbox later (workspace data persists via PVC)
sbx.connect()

# Continue working
result = sbx.commands.run("python /workspace/app.py &", timeout=10)
```

### 4.5 Run the Full Demo

A complete demo script is provided at [demo.py](demo.py):

```bash
python demo.py
```

---

## 5. Best Practices

1. **Pre-install in Image**: The Dockerfile already installs Qoder CLI globally. Avoid `npm install` at runtime to reduce latency.
2. **Timeout Configuration**: Set `timeout` based on expected task duration. Complex coding tasks may need 600+ seconds.
3. **Resource Configuration**: 2 CPU / 4Gi memory is recommended for complex programming tasks. Adjust based on workload.
4. **Session Reuse**: Use `--resume` with session IDs for multi-step tasks to avoid redundant context loading.
5. **Persistent Workspace**: The 20Gi PVC at `/workspace` ensures code persists across pause/resume cycles. Adjust storage size as needed.
6. **Network Isolation**: For production, isolate Qoder CLI sandboxes from other workloads via vSwitch and NetworkPolicy.
7. **Image Updates**: When updating the Qoder CLI version, rebuild the image and update the SandboxSet to trigger a rolling update.

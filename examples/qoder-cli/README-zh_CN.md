# 运行 Qoder CLI 沙箱

本示例演示如何通过 OpenKruise Agents 部署 [Qoder CLI](https://www.npmjs.com/package/@qoder-ai/qodercli)。使用 E2B SDK 从预热池中获取 Qoder CLI 实例，执行代码编写、调试和任务自动化等编程任务。

## 0. 基本概念

### Qoder CLI

`Qoder CLI` 是一个 AI 驱动的编程助手命令行工具。通过 OpenKruise Agents 部署 Qoder CLI，可以为每个用户提供独立的、安全隔离的沙箱环境，并配备持久化的工作区存储，用于编程任务。

### 数据持久化

本示例使用 `volumeClaimTemplates` 为每个 Sandbox 自动创建独立的云盘，确保代码和数据在沙箱暂停/恢复周期中不丢失。

---

## 1. 前提条件

### 1.1 获取 API Key

Qoder CLI 使用 OpenAI 兼容的 API 接口。您需要提供所选提供商的 API Key：

```bash
# 示例：阿里云百炼（DashScope）
export OPENAI_API_KEY="sk-****"
export OPENAI_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export OPENAI_MODEL="qwen-plus"
```

其他兼容的提供商同样适用（Azure OpenAI、自定义端点等）。

### 1.2 安装 E2B SDK

```bash
pip install e2b-code-interpreter
```

### 1.3 配置 Sandbox Manager 连接

```bash
export E2B_DOMAIN=your.domain
export E2B_API_KEY=your-token
# 如果使用自签名证书
export SSL_CERT_FILE=/path/to/ca-fullchain.pem
```

---

## 2. 构建并推送沙箱镜像

### 2.1 构建镜像

使用提供的 Dockerfile 构建 Qoder CLI 沙箱镜像：

```bash
cd examples/qoder-cli
docker build -t your-registry/qoder-cli:v0.1 .
```

### 2.2 推送到容器镜像仓库

```bash
docker push your-registry/qoder-cli:v0.1
```

> **提示**：请将 `your-registry` 替换为实际的容器镜像仓库地址（如 `registry-cn-hangzhou.ack.aliyuncs.com/acs`）。

---

## 3. 部署 Qoder CLI 预热池

### 3.1 通过 SandboxSet 部署

创建 SandboxSet 来部署 Qoder CLI 预热池。参考 [sandboxset.yaml](sandboxset.yaml)：

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

**关键字段说明：**

| 字段 | 说明 |
|------|------|
| `runtimes` | 使用内置的 `agent-runtime` 注入 —— 控制器自动注入 envd sidecar，提供 E2B 兼容的远程操作能力 |
| `volumeClaimTemplates` | 每个沙箱获得独立的 20Gi 持久化磁盘，挂载在 `/workspace` |
| `storageClassName` | 替换为集群中可用的 StorageClass |
| `startupProbe` | 检查 49999 端口上 agent-runtime 的健康检查端点 |

### 3.2 验证部署

```bash
# 部署 SandboxSet
kubectl apply -f sandboxset.yaml

# 检查预热池状态
kubectl get sbs qoder-cli-sbs

# 预期输出
NAME              REPLICAS   AVAILABLE   UPDATEREVISION   AGE
qoder-cli-sbs     3          3           xxxxxxxx         2m

# 查看可用的 Sandbox
kubectl get sbx -l agents.kruise.io/sandbox-pool=qoder-cli-sbs \
                -l agents.kruise.io/sandbox-claimed=false
```

---

## 4. 通过 E2B SDK 使用 Qoder CLI

### 4.1 领取沙箱并执行任务

```python
import os
import json
from e2b_code_interpreter import Sandbox

# 从预热池中领取沙箱实例
sbx = Sandbox.create(template="qoder-cli-sbs", timeout=3600)
print(f"Sandbox ID: {sbx.sandbox_id}")

# 配置 LLM 环境变量
envs = {
    "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
    "OPENAI_BASE_URL": os.environ.get("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    "OPENAI_MODEL": os.environ.get("OPENAI_MODEL", "qwen-plus"),
}

# 执行编程任务
result = sbx.commands.run(
    'qoder --output-format json -p "在 /workspace/app.py 创建一个带有 /health 端点的 Python Flask Web 应用"',
    envs=envs,
    timeout=600,
    cwd="/workspace",
)

# 解析 session ID 用于多轮对话
output = json.loads(result.stdout)
session_id = output["session_id"]
print(f"Session ID: {session_id}")
```

### 4.2 多轮对话

使用 `--resume` 和 session ID 继续对话：

```python
result = sbx.commands.run(
    f'qoder --output-format json --resume {session_id} -p "为 Flask 应用添加 pytest 单元测试"',
    envs=envs,
    timeout=600,
    cwd="/workspace",
)
print(result.stdout)
```

### 4.3 文件操作

在持久化工作区中读写文件：

```python
# 读取生成的文件
result = sbx.commands.run("cat /workspace/app.py", timeout=10)
print(result.stdout)

# 通过 SDK 写入文件
sbx.files.write("/workspace/requirements.txt", "flask\npytest\n", user="root")

# 列出工作区内容
result = sbx.commands.run("ls -la /workspace", timeout=10)
print(result.stdout)
```

### 4.4 暂停与恢复

> 注意：暂停/恢复时的内存状态保存仅在阿里云 ACS 上支持。

```python
# 暂停沙箱（状态保存到磁盘）
sbx.beta_pause()

# 之后恢复沙箱（工作区数据通过 PVC 持久化）
sbx.connect()

# 继续工作
result = sbx.commands.run("python /workspace/app.py &", timeout=10)
```

### 4.5 运行完整演示

完整的演示脚本见 [demo.py](demo.py)：

```bash
python demo.py
```

---

## 5. 最佳实践

1. **镜像内预装**：Dockerfile 已全局安装 Qoder CLI。避免在运行时执行 `npm install` 以减少延迟。
2. **超时配置**：根据预期任务时长设置 `timeout`。复杂的编程任务可能需要 600 秒以上。
3. **资源配置**：复杂编程任务建议使用 2 CPU / 4Gi 内存。根据实际负载调整。
4. **会话复用**：多步骤任务使用 `--resume` 和 session ID，避免重复加载上下文。
5. **持久化工作区**：`/workspace` 的 20Gi PVC 确保代码在暂停/恢复周期中不丢失。根据需要调整存储大小。
6. **网络隔离**：生产环境中，通过 vSwitch 和 NetworkPolicy 将 Qoder CLI 沙箱与其他工作负载隔离。
7. **镜像更新**：更新 Qoder CLI 版本时，重新构建镜像并更新 SandboxSet 以触发滚动更新。

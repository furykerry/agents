"""
Qoder CLI Sandbox Demo

Demonstrates how to use Qoder CLI inside an ACS sandbox managed by
OpenKruise Agents. Claims a sandbox from the pre-warmed pool, executes
coding tasks, manages files, and shows multi-turn conversation support.

Prerequisites:
    pip install e2b-code-interpreter

    export E2B_DOMAIN=your.domain
    export E2B_API_KEY=your-token
    export OPENAI_API_KEY=sk-****
    export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
    export OPENAI_MODEL=qwen-plus
"""

import json
import os
import sys

from e2b_code_interpreter import Sandbox

# ---------------------------------------------------------------------------
# 1. Configure LLM environment variables (OpenAI-compatible provider)
# ---------------------------------------------------------------------------
ENVS = {
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
    "OPENAI_BASE_URL": os.environ.get(
        "OPENAI_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    ),
    "OPENAI_MODEL": os.environ.get("OPENAI_MODEL", "qwen-plus"),
}


def create_sandbox() -> Sandbox:
    """Claim a sandbox from the qoder-cli-sbs warm pool."""
    print("[1/6] Creating sandbox from qoder-cli-sbs warm pool...")
    sbx = Sandbox.create(template="qoder-cli-sbs", timeout=3600)
    print(f"      Sandbox ID: {sbx.sandbox_id}")
    return sbx


def verify_cli(sbx: Sandbox) -> None:
    """Verify Qoder CLI is installed and accessible."""
    print("[2/6] Verifying Qoder CLI installation...")
    result = sbx.commands.run("qoder --version", timeout=30)
    print(f"      Version: {result.stdout.strip()}")


def run_task(sbx: Sandbox) -> str:
    """Execute a coding task with Qoder CLI and return the session ID."""
    print("[3/6] Running a coding task...")
    task = (
        "Create a Python script at /workspace/hello.py that prints "
        "'Hello from Qoder CLI sandbox!' and includes a function that "
        "computes the factorial of a number."
    )
    result = sbx.commands.run(
        f'qoder --output-format json -p "{task}"',
        envs=ENVS,
        timeout=600,
        cwd="/workspace",
    )
    print(f"      Exit code: {result.exit_code}")

    # Parse the session ID for multi-turn conversations
    try:
        output = json.loads(result.stdout)
        session_id = output.get("session_id", "")
        print(f"      Session ID: {session_id}")
        return session_id
    except (json.JSONDecodeError, KeyError):
        print(f"      Raw output: {result.stdout[:500]}")
        return ""


def resume_conversation(sbx: Sandbox, session_id: str) -> None:
    """Continue a conversation using the previous session ID."""
    if not session_id:
        print("[4/6] Skipping multi-turn demo (no session ID available).")
        return

    print("[4/6] Resuming conversation with previous session...")
    follow_up = "Now add a main guard to the script and add a test that calls the factorial function with n=5."
    result = sbx.commands.run(
        f'qoder --output-format json --resume {session_id} -p "{follow_up}"',
        envs=ENVS,
        timeout=600,
        cwd="/workspace",
    )
    print(f"      Exit code: {result.exit_code}")
    print(f"      Output preview: {result.stdout[:300]}")


def read_workspace_files(sbx: Sandbox) -> None:
    """Read the generated file from the workspace volume."""
    print("[5/6] Reading generated files from /workspace...")
    result = sbx.commands.run("cat /workspace/hello.py 2>/dev/null || echo 'File not found'", timeout=10)
    print(f"      File content:\n{result.stdout}")


def cleanup(sbx: Sandbox) -> None:
    """Kill the sandbox to release resources."""
    print("[6/6] Cleaning up sandbox...")
    sbx.kill()
    print(f"      Sandbox {sbx.sandbox_id} killed.")


def main():
    sbx = None
    try:
        sbx = create_sandbox()
        verify_cli(sbx)
        session_id = run_task(sbx)
        resume_conversation(sbx, session_id)
        read_workspace_files(sbx)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if sbx:
            cleanup(sbx)

    print("\nDone! All tasks completed successfully.")


if __name__ == "__main__":
    main()

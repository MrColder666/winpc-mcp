"""DeepSeek Harness 集成：把任务交给电脑上的 DSH 自主执行（agent 模式）。

DSH headless 模式：`dsh --profile headless "任务"` —— 运行一次新会话、
读写工作区文件、执行命令，最终打印回答后退出。
"""
import os
import subprocess

from .tools import CONFIG, tool
from .tools_dev import _submit


def _dsh_cfg():
    return CONFIG.get("dsh", {}) or {}


def _run_dsh(prompt, workspace):
    api_key = _dsh_cfg().get("api_key") or os.environ.get("DEEPSEEK_API_KEY", "")
    env = dict(os.environ)
    if api_key:
        env["DEEPSEEK_API_KEY"] = api_key
    args = ["dsh", "--profile", "headless", prompt]
    try:
        proc = subprocess.run(args, capture_output=True, timeout=1800, text=True,
                              encoding="utf-8", errors="replace", cwd=workspace or None, env=env)
        out = (proc.stdout or "").strip()
        if not out:
            out = (proc.stderr or "").strip()
        return {
            "ok": proc.returncode == 0,
            "final_response": out[:80000],
            "truncated": len(out) > 80000,
            "exit_code": proc.returncode,
            "workspace": workspace,
            "hint": "final_response 是 DSH 自主执行后的最终回答，可直接用于总结",
        }
    except FileNotFoundError:
        return {"ok": False,
                "error": "未找到 dsh 命令。请在 Windows 上安装：npm install -g @deepseek-ai/dsh，"
                         "并配置 DEEPSEEK_API_KEY（或 config.json 的 dsh.api_key）"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "DSH 任务超时（>1800s）"}


@tool
def dsh_run(prompt: str, workspace: str = "", async_mode: bool = True) -> dict:
    """把任务交给电脑上的 DeepSeek Harness (DSH) 自主执行——DSH agent 可读写工作区文件、
    运行命令、维护计划，最终返回它的回答供总结。
    prompt: 任务描述（如 'Inspect this repo and fix the failing tests'）;
    workspace: 工作目录（默认 config 的 dsh.workspace，或 ~/dsh-workspace）;
    async_mode: True=后台运行立即返回 task_id（推荐，用 get_task_status 查询）;
                False=阻塞等待直到 DSH 完成"""
    ws = workspace or _dsh_cfg().get("workspace", "")
    if not ws:
        ws = os.path.expanduser("~/dsh-workspace")
    try:
        os.makedirs(ws, exist_ok=True)
    except OSError:
        pass
    if async_mode:
        tid = _submit(_run_dsh, prompt, ws)
        return {
            "task_id": tid,
            "status": "running",
            "workspace": ws,
            "hint": f"用 get_task_status(task_id='{tid}') 查询 DSH 的最终回答",
        }
    return _run_dsh(prompt, ws)

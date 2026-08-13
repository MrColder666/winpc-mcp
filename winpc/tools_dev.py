"""开发效率工具：git 封装、后台任务（长命令不阻塞）、批量读取、批量命令。"""
import subprocess
import threading
import time

from .tools import tool

IS_WINDOWS = __import__("sys").platform == "win32"

# ---------------------------------------------------------------- 后台任务
# 任务注册表: task_id -> {"status": running/done/error, "result"/"error", ...}
TASKS: dict = {}
_tasks_lock = threading.Lock()
_task_seq = 0


def _submit(fn, *args, **kwargs):
    """在后台线程运行 fn，返回 task_id。"""
    global _task_seq
    with _tasks_lock:
        _task_seq += 1
        tid = f"task-{_task_seq}"
        TASKS[tid] = {"status": "running", "started": time.time(), "result": None, "error": None}
    t0 = time.time()

    def worker():
        try:
            result = fn(*args, **kwargs)
            with _tasks_lock:
                TASKS[tid]["result"] = result
                TASKS[tid]["status"] = "done"
                TASKS[tid]["elapsed_s"] = round(time.time() - t0, 1)
        except Exception as e:
            with _tasks_lock:
                TASKS[tid]["error"] = f"{type(e).__name__}: {e}"
                TASKS[tid]["status"] = "error"
                TASKS[tid]["elapsed_s"] = round(time.time() - t0, 1)

    threading.Thread(target=worker, daemon=True).start()
    return tid


def _cleanup_tasks(max_age=3600):
    """清理超 1 小时的已完成任务，防止内存膨胀。"""
    now = time.time()
    with _tasks_lock:
        for tid in list(TASKS):
            if TASKS[tid]["status"] != "running" and now - TASKS[tid]["started"] > max_age:
                TASKS.pop(tid, None)


def _run_cmd(args, timeout=600, cwd=""):
    try:
        proc = subprocess.run(
            args, capture_output=True, timeout=timeout, text=True,
            encoding="utf-8", errors="replace", cwd=cwd or None,
        )
        return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode, "timed_out": False}
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"命令超时（>{timeout}s）", "exit_code": -1, "timed_out": True}


# ---------------------------------------------------------------- 工具
@tool
def git_status(path: str, short: bool = True) -> dict:
    """查看 git 仓库状态。path: 仓库目录; short: True 用 --short 简洁输出"""
    return _run_cmd(["git", "-C", path, "status", "--short" if short else ""])


@tool
def git_commit(path: str, message: str, add_all: bool = True) -> dict:
    """git add + commit。path: 仓库目录; message: 提交信息; add_all: 是否 git add -A"""
    if add_all:
        _run_cmd(["git", "-C", path, "add", "-A"])
    return _run_cmd(["git", "-C", path, "commit", "-m", message])


@tool
def git_push(path: str, remote: str = "origin", branch: str = "") -> dict:
    """git push。path: 仓库目录; remote: 远程名（默认 origin）; branch: 分支名（默认当前分支）"""
    args = ["git", "-C", path, "push", remote]
    if branch:
        args.append(branch)
    return _run_cmd(args)


@tool
def install_packages(manager: str, packages: str, cwd: str = "") -> dict:
    """后台安装包（不阻塞，返回 task_id 用 get_task_status 查询）。manager: pip 或 npm; packages: 空格分隔的包名; cwd: 工作目录"""
    if manager == "pip":
        args = ["pip", "install"] + packages.split()
    elif manager == "npm":
        args = ["npm", "install"] + packages.split()
    else:
        raise RuntimeError("manager 仅支持 pip 或 npm")
    tid = _submit(lambda: _run_cmd(args, timeout=1800, cwd=cwd))
    _cleanup_tasks()
    return {"task_id": tid, "status": "running", "hint": f"用 get_task_status(task_id='{tid}') 查询结果"}


@tool
def get_task_status(task_id: str) -> dict:
    """查询后台任务状态（install_packages 等返回的 task_id）。task_id: 任务 ID"""
    _cleanup_tasks()
    t = TASKS.get(task_id)
    if not t:
        return {"status": "not_found", "hint": "任务不存在或已被清理（超过1小时）"}
    return dict(t)


@tool
def read_file_batch(paths: list, max_bytes: int = 262144) -> dict:
    """批量读取多个文件（一次调用读 N 个文件，适合查看项目代码）。paths: 绝对路径数组; max_bytes: 每个文件最多字节（默认256KB）"""
    from .tools_files import read_file
    results, errors = [], []
    for p in paths or []:
        try:
            results.append(read_file(p, max_bytes))
        except Exception as e:
            errors.append({"path": p, "error": f"{type(e).__name__}: {e}"})
    return {"read": len(results), "failed": len(errors), "files": results, "errors": errors}


@tool
def batch_run(commands: list, shell: str = "powershell", stop_on_error: bool = False) -> dict:
    """顺序执行多条命令，返回每条结果（一次调用替代多次 run_powershell/run_cmd）。
    commands: 命令字符串数组; shell: powershell 或 cmd; stop_on_error: 出错是否停止"""
    from .tools_command import run_powershell, run_cmd
    results = []
    for cmd in commands or []:
        r = run_powershell(cmd, 300) if shell == "powershell" else run_cmd(cmd, 300)
        results.append({"command": cmd, **r})
        if stop_on_error and r.get("exit_code") not in (0, None):
            break
    return {"executed": len(results), "results": results}

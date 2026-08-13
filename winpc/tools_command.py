"""命令执行工具：PowerShell / CMD / 通用 Shell。"""
import base64
import subprocess
import sys

from .tools import tool

IS_WINDOWS = sys.platform == "win32"


def _run(args, timeout):
    try:
        proc = subprocess.run(
            args, capture_output=True, timeout=timeout, text=True, encoding="utf-8", errors="replace"
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"命令超时（>{timeout}s）", "exit_code": -1, "timed_out": True}


@tool
def run_powershell(command: str, timeout: int = 120) -> dict:
    """在 Windows 上执行 PowerShell 命令并返回 stdout/stderr/退出码。command: 要执行的 PowerShell 代码; timeout: 超时秒数（默认120）"""
    if not IS_WINDOWS:
        raise RuntimeError("run_powershell 仅在 Windows 上可用")
    # 用 UTF-16LE Base64 编码，避免引号转义与中文乱码
    enc = base64.b64encode(command.encode("utf-16-le")).decode()
    return _run(
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", enc],
        timeout,
    )


@tool
def run_cmd(command: str, timeout: int = 120) -> dict:
    """在 Windows 上执行 CMD 命令并返回输出。command: 要执行的 cmd 命令; timeout: 超时秒数（默认120）"""
    if not IS_WINDOWS:
        raise RuntimeError("run_cmd 仅在 Windows 上可用")
    return _run(["cmd", "/c", command], timeout)


@tool
def run_shell(command: str, timeout: int = 120, cwd: str = "") -> dict:
    """执行 Shell 命令（Windows 上等价于 cmd /c，用于通用脚本）。command: 要执行的命令; timeout: 超时秒数; cwd: 工作目录（可选）"""
    return _run_shell(command, timeout, cwd)


@tool
def run_script(script: str, shell: str = "powershell", timeout: int = 300) -> dict:
    """执行一整段多行脚本（一次调用完成复杂操作，避免多次小命令往返）。
    script: 脚本内容（多行）; shell: powershell(默认) 或 cmd; timeout: 超时秒数（默认300）"""
    if shell == "cmd":
        return run_cmd(script, timeout)
    return run_powershell(script, timeout)


def _run_shell(command, timeout, cwd):
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            timeout=timeout,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd or None,
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": f"命令超时（>{timeout}s）", "exit_code": -1, "timed_out": True}

"""应用与窗口工具：打开应用/URL、枚举窗口、切换/关闭窗口。"""
import json
import os
import subprocess
import sys

from .tools import tool


def _ps(cmd):
    """执行 PowerShell 并解析 JSON 输出。"""
    import base64
    enc = base64.b64encode(cmd.encode("utf-16-le")).decode()
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", enc],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        out = proc.stdout.strip()
        if not out:
            return []
        return json.loads(out) if out.startswith(("[", "{")) else []
    except Exception:
        return []


@tool
def open_app(target: str) -> dict:
    """打开应用、文件或文件夹。target: 可执行文件路径、文档路径、文件夹路径或协议URL（如 'C:\\Windows\\System32\\notepad.exe' 或 'ms-settings:display'）"""
    if sys.platform == "win32":
        os.startfile(target)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(target, shell=True)
    return {"ok": True, "target": target}


@tool
def open_url(url: str) -> dict:
    """在电脑默认浏览器中打开网址。url: 完整 URL（如 https://example.com）"""
    if sys.platform == "win32":
        os.startfile(url)  # type: ignore[attr-defined]
    else:
        import webbrowser
        webbrowser.open(url)
    return {"ok": True, "url": url}


@tool
def list_windows() -> list:
    """列出当前所有可见窗口（标题非空的进程）。仅 Windows。"""
    if sys.platform != "win32":
        raise RuntimeError("list_windows 仅在 Windows 上可用")
    ps = """
    [Console]::OutputEncoding = [Text.Encoding]::UTF8
    Get-Process | Where-Object { $_.MainWindowTitle -ne "" } |
      Select-Object Id, ProcessName, MainWindowTitle |
      ConvertTo-Json -Compress
    """
    return _ps(ps)


@tool
def focus_window(title: str) -> dict:
    """将指定窗口置于前台。title: 窗口标题（支持子串匹配）。仅 Windows。"""
    if sys.platform != "win32":
        raise RuntimeError("focus_window 仅在 Windows 上可用")
    ps = f"""
    $w = New-Object -ComObject WScript.Shell
    $ok = $w.AppActivate('{title.replace("'", "''")}')
    if (-not $ok) {{
      Get-Process | Where-Object {{ $_.MainWindowTitle -like '*{title.replace("'", "''")}*' }} |
        ForEach-Object {{ $null = $w.AppActivate($_.Id) }}
    }}
    """
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand",
                    __import__("base64").b64encode(ps.encode("utf-16-le")).decode()],
                   capture_output=True, timeout=15)
    return {"ok": True, "title": title}


@tool
def close_window(title: str) -> dict:
    """关闭指定窗口（先聚焦再发 Alt+F4）。title: 窗口标题（支持子串匹配）。仅 Windows。"""
    if sys.platform != "win32":
        raise RuntimeError("close_window 仅在 Windows 上可用")
    ps = f"""
    $w = New-Object -ComObject WScript.Shell
    $ok = $w.AppActivate('{title.replace("'", "''")}')
    if (-not $ok) {{
      Get-Process | Where-Object {{ $_.MainWindowTitle -like '*{title.replace("'", "''")}*' }} |
        ForEach-Object {{ $ok = $w.AppActivate($_.Id) }}
    }}
    if ($ok) {{ Start-Sleep -Milliseconds 300; $w.SendKeys('%{{F4}}') }}
    """
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand",
                    __import__("base64").b64encode(ps.encode("utf-16-le")).decode()],
                   capture_output=True, timeout=15)
    return {"ok": True, "title": title}

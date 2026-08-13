"""系统管理工具：音量、电源（锁屏/关机/重启/休眠）、网络信息、通知、CPU 温度。"""
import os
import socket
import subprocess
import sys

from .tools import CONFIG, tool

IS_WINDOWS = sys.platform == "win32"


def _require_windows():
    if not IS_WINDOWS:
        raise RuntimeError("该工具仅在 Windows 上可用")


def _confirm_dangerous():
    if CONFIG.get("confirm_dangerous"):
        raise RuntimeError("危险操作需要 confirm=True 确认")


# ---------------------------------------------------------------- 音量
@tool
def get_volume() -> dict:
    """获取系统主音量 (0-100)。"""
    _require_windows()
    import ctypes
    vol = ctypes.c_uint(0)
    ctypes.windll.winmm.waveOutGetVolume(0, ctypes.byref(vol))
    value = (vol.value & 0xFFFF) / 0xFFFF * 100
    return {"volume": round(value), "muted": value < 0.5}


@tool
def set_volume(level: int) -> dict:
    """设置系统主音量。level: 0-100"""
    _require_windows()
    if not 0 <= level <= 100:
        raise RuntimeError("level 必须是 0-100")
    import ctypes
    raw = int(level / 100 * 0xFFFF)
    ctypes.windll.winmm.waveOutSetVolume(0, raw | (raw << 16))
    return {"volume": level}


# ---------------------------------------------------------------- 电源
@tool
def lock_screen() -> dict:
    """锁定电脑屏幕（Win+L）。"""
    _require_windows()
    import ctypes
    ctypes.windll.user32.LockWorkStation()
    return {"locked": True}


@tool
def shutdown(delay: int = 0, force: bool = False, confirm: bool = False) -> dict:
    """关机。delay: 延迟秒数; force: 强制关闭应用; confirm: 危险操作确认（confirm_dangerous 配置开启时必需）"""
    _require_windows()
    if CONFIG.get("confirm_dangerous") and not confirm:
        raise RuntimeError("危险操作需要 confirm=True 确认")
    args = ["shutdown", "/s", "/t", str(delay)]
    if force:
        args.append("/f")
    subprocess.Popen(args)
    return {"shutting_down": True, "delay_s": delay}


@tool
def reboot(delay: int = 0, force: bool = False, confirm: bool = False) -> dict:
    """重启电脑。delay: 延迟秒数; force: 强制; confirm: 危险操作确认"""
    _require_windows()
    if CONFIG.get("confirm_dangerous") and not confirm:
        raise RuntimeError("危险操作需要 confirm=True 确认")
    args = ["shutdown", "/r", "/t", str(delay)]
    if force:
        args.append("/f")
    subprocess.Popen(args)
    return {"rebooting": True, "delay_s": delay}


@tool
def sleep() -> dict:
    """使电脑进入休眠/睡眠状态。"""
    _require_windows()
    subprocess.Popen(["rundll32", "powrprof.dll,SetSuspendState", "0,1,0"])
    return {"sleeping": True}


# ---------------------------------------------------------------- 网络
@tool
def get_network_info() -> dict:
    """获取网络信息：主机名、各网卡 IPv4 地址、累计流量。"""
    import psutil
    addrs = psutil.net_if_addrs()
    io = psutil.net_io_counters()
    interfaces = []
    for name, items in addrs.items():
        for it in items:
            if it.family == socket.AF_INET:
                interfaces.append({"name": name, "ip": it.address, "netmask": it.netmask})
    return {
        "hostname": socket.gethostname(),
        "interfaces": interfaces,
        "bytes_sent": io.bytes_sent,
        "bytes_recv": io.bytes_recv,
    }


# ---------------------------------------------------------------- 通知
@tool
def notify(title: str, message: str) -> dict:
    """在 Windows 桌面右下角弹出系统通知气泡（不阻塞，6 秒后自动消失）。
    title: 标题; message: 内容"""
    _require_windows()
    import base64
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "Add-Type -AssemblyName System.Drawing;"
        f"$n=New-Object System.Windows.Forms.NotifyIcon;"
        f"$n.Icon=[System.Drawing.SystemIcons]::Information;"
        f"$n.Visible=$true;"
        f"$n.ShowBalloonTip(5000,{base64.b64encode(title.encode('utf-16-le')).decode()},"
        f"{base64.b64encode(message.encode('utf-16-le')).decode()},"
        f"[System.Windows.Forms.ToolTipIcon]::Info);"
        "Start-Sleep -Seconds 6;$n.Dispose()"
    )
    # 用 -EncodedCommand 传 UTF-16LE base64，避免中文转义问题
    enc = base64.b64encode(ps.encode("utf-16-le")).decode()
    subprocess.Popen(
        ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-EncodedCommand", enc],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return {"notified": True, "title": title}


# ---------------------------------------------------------------- CPU 温度
@tool
def get_cpu_temp() -> dict:
    """获取 CPU 温度（摄氏度）。依赖 WMI 热区（ACPI），台式机/部分笔记本可能不支持。"""
    _require_windows()
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object -First 1).CurrentTemperature"],
            capture_output=True, timeout=15, text=True,
        )
        raw = proc.stdout.strip()
        if raw:
            celsius = round(float(raw) / 10 - 273.15, 1)
            return {"cpu_temp_c": celsius}
    except Exception:
        pass
    return {"cpu_temp_c": None, "hint": "此设备不支持 ACPI 温度读取（常见于台式机）"}

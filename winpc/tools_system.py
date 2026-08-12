"""系统工具：系统信息、进程管理。"""
import os
import platform

from .tools import tool


@tool
def system_info() -> dict:
    """获取电脑系统信息：系统版本、CPU、内存、磁盘使用率。"""
    try:
        import psutil
        try:
            cpu = psutil.cpu_percent(interval=0.3)
        except Exception:
            cpu = None
        mem = psutil.virtual_memory()
        disks = []
        try:
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append({"drive": part.mountpoint, "total_gb": round(usage.total / 2**30, 1),
                                  "used_gb": round(usage.used / 2**30, 1), "percent": usage.percent})
                except OSError:
                    continue
        except Exception:
            disks = []
        boot = psutil.boot_time()
        import time
        return {
            "platform": platform.platform(),
            "hostname": platform.node(),
            "cpu_cores": os.cpu_count(),
            "cpu_percent": cpu,
            "mem_total_gb": round(mem.total / 2**30, 1),
            "mem_used_gb": round(mem.used / 2**30, 1),
            "mem_percent": mem.percent,
            "disks": disks,
            "uptime_hours": round((time.time() - boot) / 3600, 1),
        }
    except ImportError:
        return {"platform": platform.platform(), "hostname": platform.node(), "python": platform.python_version()}


@tool
def list_process(name: str = "", top: int = 30) -> list:
    """列出电脑进程，可按名称过滤。name: 进程名过滤关键字（如 'chrome'）; top: 最多返回数"""
    try:
        import psutil
    except ImportError:
        raise RuntimeError("缺少 psutil 依赖")
    results = []
    for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent", "create_time"]):
        try:
            pname = p.info["name"] or ""
            if name and name.lower() not in pname.lower():
                continue
            results.append({
                "pid": p.info["pid"],
                "name": pname,
                "mem_mb": round((p.info["memory_info"].rss if p.info["memory_info"] else 0) / 2**20, 1),
                "cpu": round(p.info["cpu_percent"] or 0, 1),
                "started": p.info["create_time"],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    results.sort(key=lambda r: r["mem_mb"], reverse=True)
    return results[:top]


@tool
def kill_process(pid: int = 0, name: str = "", force: bool = True, confirm: bool = False) -> dict:
    """结束进程。pid: 进程ID; name: 按名称结束（全部匹配进程）; force: True强杀; confirm: 当配置 confirm_dangerous=true 时需确认"""
    from .tools import CONFIG
    if CONFIG.get("confirm_dangerous") and not confirm:
        raise RuntimeError("危险操作需要 confirm=True 确认")
    try:
        import psutil
    except ImportError:
        raise RuntimeError("缺少 psutil 依赖")
    killed = []
    if pid:
        try:
            proc = psutil.Process(pid)
            proc.kill() if force else proc.terminate()
            killed.append({"pid": pid, "name": proc.name()})
        except psutil.NoSuchProcess:
            raise RuntimeError(f"进程不存在: {pid}")
    if name:
        for p in psutil.process_iter(["pid", "name"]):
            try:
                if p.info["name"] and p.info["name"].lower() == name.lower():
                    p.kill() if force else p.terminate()
                    killed.append({"pid": p.info["pid"], "name": p.info["name"]})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    if not killed:
        raise RuntimeError(f"未找到匹配的进程: pid={pid} name={name}")
    return {"killed": killed}

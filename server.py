#!/usr/bin/env python3
"""winpc-mcp — 从 iPad (Minis) 通过 MCP 远程控制 Windows 电脑。

运行:  python server.py [--port 8765] [--host 0.0.0.0]
配置:  环境变量 WINPC_TOKEN 或同目录 config.json（见 config.example.json）
认证:  /mcp 与 /files 需 Authorization: Bearer <token>
      Dashboard (/dashboard /api/*) 可选口令 X-Dashboard-Key
"""
import argparse
import asyncio
import base64
import functools
import hashlib
import json
import os
import secrets
import socket
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from mcp.server.fastmcp import FastMCP

import winpc
from winpc import tools
from winpc import tools_network
from winpc.event_bus import bus

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

# 最近截图缓存: id -> png bytes（dashboard 前端拉取用）
SCREENSHOTS: dict = {}


# ---------------------------------------------------------------- 配置
def load_config(port, host) -> dict:
    cfg = {
        "host": "0.0.0.0", "port": 8765, "token": "",
        "allowed_dirs": [], "confirm_dangerous": False,
        "dashboard_password": "",
    }
    if CONFIG_PATH.exists():
        try:
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                cfg.update(loaded)
        except Exception as e:
            print(f"[警告] config.json 解析失败: {e}")
    if host:
        cfg["host"] = host
    if port:
        cfg["port"] = port

    token = os.environ.get("WINPC_TOKEN") or (cfg.get("token") or "").strip()
    if not token:
        token = secrets.token_urlsafe(24)
        cfg["token"] = token
        print("\n" + "=" * 56)
        print("  未配置 Token，已自动生成。请立即保存：")
        print(f"\n      {token}\n")
        print("  建议写入 config.json 或环境变量 WINPC_TOKEN 以固定。")
        print("=" * 56 + "\n")
    cfg["token"] = token

    tools.CONFIG["confirm_dangerous"] = bool(cfg.get("confirm_dangerous"))
    tools.CONFIG["allowed_dirs"] = list(cfg.get("allowed_dirs", []) or [])
    return cfg


def get_lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("223.5.5.5", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


# ---------------------------------------------------------------- 工具调用包装
def summarize(v, limit=800):
    """把工具结果/参数截断为可入日志的摘要。"""
    if isinstance(v, str):
        return v if len(v) <= limit else v[:limit] + f"...(+{len(v)-limit} chars)"
    try:
        s = json.dumps(v, ensure_ascii=False, default=str)
    except Exception:
        s = str(v)
    return s if len(s) <= limit else s[:limit] + f"...(+{len(s)-limit} chars)"


def make_tool_wrapper(fn):
    """包装工具函数：记录调用参数/结果/耗时/成败，发布到事件总线。"""
    name = fn.__name__

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        t0 = time.time()
        start_event = {"type": "tool_call", "tool": name,
                       "args": summarize(kwargs, 400), "status": "running",
                       "ts": t0}
        bus.publish_sync(start_event)
        try:
            result = fn(*args, **kwargs)
            ev = {"type": "tool_call", "tool": name,
                  "args": summarize(kwargs, 400), "status": "ok",
                  "ts": t0, "duration_ms": int((time.time() - t0) * 1000)}
            if name == "screenshot" and isinstance(result, str) and len(result) > 1000:
                shot_id = secrets.token_urlsafe(8)
                try:
                    SCREENSHOTS[shot_id] = base64.b64decode(result)
                    ev["shot_id"] = shot_id
                    ev["result"] = f"截图已捕获 (shot_id={shot_id})"
                    if len(SCREENSHOTS) > 24:
                        SCREENSHOTS.pop(next(iter(SCREENSHOTS)))
                except Exception:
                    ev["result"] = summarize(result)
            else:
                ev["result"] = summarize(result)
            bus.publish_sync(ev)
            return result
        except Exception as e:
            bus.publish_sync({"type": "tool_call", "tool": name,
                         "args": summarize(kwargs, 400), "status": "error",
                         "ts": t0, "duration_ms": int((time.time() - t0) * 1000),
                         "result": f"{type(e).__name__}: {e}"})
            raise
    return wrapper


# ---------------------------------------------------------------- 入口
def main():
    parser = argparse.ArgumentParser(description="winpc-mcp server")
    parser.add_argument("--host", default=None, help="监听地址（默认 0.0.0.0）")
    parser.add_argument("--port", type=int, default=None, help="监听端口（默认 8765）")
    parser.add_argument("--no-dashboard", action="store_true", help="不启用 dashboard")
    args = parser.parse_args()

    cfg = load_config(args.port, args.host)
    tools_network.BASE_URL = f"http://{get_lan_ip()}:{cfg['port']}"

    # -------------------------------------------------- MCP 服务器
    # 关闭 DNS rebinding 防护：新版 MCP SDK 对 localhost host 自动启用 Host 校验，
    # 会拒绝局域网 IP 直连（421 Invalid Host header）。显式关闭以支持局域网访问。
    mcp_kwargs = {"instructions": (
        "远程控制 Windows 电脑的 MCP 服务器。可用工具：执行 PowerShell/CMD 命令、"
        "读写/搜索文件、截屏、键盘鼠标控制、打开应用与网址、窗口管理、进程管理、"
        "HTTP 请求与文件下载、把电脑文件回传给 iPad。"
    )}
    try:
        from mcp.server.transport_security import TransportSecuritySettings
        mcp_kwargs["transport_security"] = TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        )
    except ImportError:
        pass  # 旧版 SDK 无此防护，无需处理

    mcp = FastMCP("winpc", **mcp_kwargs)

    # 注册全部工具（带日志包装）
    for fn in winpc.ALL_TOOLS:
        mcp.tool()(make_tool_wrapper(fn))

    # 对话同步工具（iPad 端 agent 回复后调用 → dashboard 显示对话流）
    def sync_chat(role: str, content: str) -> dict:
        """把一条对话消息同步到电脑端 Dashboard（role: user 或 assistant）"""
        if role not in ("user", "assistant"):
            raise ValueError("role 必须是 user 或 assistant")
        bus.publish_sync({"type": "chat", "role": role, "content": content})
        return {"ok": True, "synced": True}

    mcp.tool()(sync_chat)
    print(f"[工具] 已注册 {len(winpc.ALL_TOOLS) + 1} 个工具")

    # -------------------------------------------------- HTTP 应用
    mcp_app = mcp.streamable_http_app()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        bus.attach_loop(asyncio.get_running_loop())
        async with mcp_app.router.lifespan_context(mcp_app):
            yield

    app = FastAPI(title="winpc-mcp", lifespan=lifespan)

    dash_pwd = cfg.get("dashboard_password", "")

    def _dash_key_ok(request: Request) -> bool:
        if not dash_pwd:
            return True
        expect = hashlib.sha256(dash_pwd.encode()).hexdigest()
        got = request.headers.get("x-dashboard-key", "") or request.query_params.get("key", "")
        return got == expect

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        path = request.url.path
        if path.startswith("/mcp") or path.startswith("/files"):
            if request.headers.get("authorization", "") != f"Bearer {cfg['token']}":
                return JSONResponse(status_code=401, content={"error": "unauthorized"})
        elif path.startswith("/api") and not path.startswith("/api/auth/status"):
            if not _dash_key_ok(request):
                return JSONResponse(status_code=401, content={"error": "dashboard unauthorized"})
        return await call_next(request)

    @app.get("/api/auth/status")
    async def auth_status(request: Request):
        """前端探测：是否启用口令、当前是否已认证。"""
        return {"enabled": bool(dash_pwd), "authed": _dash_key_ok(request)}

    # --- Dashboard 页面与 API ---
    @app.get("/dashboard")
    async def dashboard_page():
        return FileResponse(BASE_DIR / "dashboard" / "index.html")

    @app.post("/api/login")
    async def api_login(request: Request):
        body = await request.json()
        if dash_pwd and body.get("password") == dash_pwd:
            return {"ok": True, "key": hashlib.sha256(dash_pwd.encode()).hexdigest()}
        return JSONResponse(status_code=401, content={"error": "wrong password"})

    @app.get("/api/events")
    async def api_events(request: Request):
        q = await bus.subscribe()

        async def gen():
            try:
                after = float(request.query_params.get("after", 0) or 0)
                for ev in bus.history(limit=300):
                    if ev.get("ts", 0) > after:
                        yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        ev = await asyncio.wait_for(q.get(), timeout=15)
                        yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": ping\n\n"
            finally:
                await bus.unsubscribe(q)

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache",
                                          "X-Accel-Buffering": "no"})

    @app.get("/api/status")
    async def api_status():
        import psutil
        status = {"ts": time.time(), "online": True, "cpu": None, "mem": None, "disks": []}
        try:
            try:
                status["cpu"] = psutil.cpu_percent(interval=0.2)
            except Exception:
                status["cpu"] = None
            try:
                m = psutil.virtual_memory()
                status["mem"] = {"total": m.total, "used": m.used, "percent": m.percent}
            except Exception:
                pass
            try:
                for part in psutil.disk_partitions():
                    try:
                        u = psutil.disk_usage(part.mountpoint)
                        status["disks"].append({"mount": part.mountpoint,
                                                "total": u.total, "used": u.used,
                                                "percent": u.percent})
                    except OSError:
                        continue
            except Exception:
                pass
        except Exception:
            pass
        return status

    @app.get("/api/history")
    async def api_history(limit: int = 100):
        return bus.history(limit=limit)

    @app.get("/api/screenshots/{shot_id}")
    async def api_screenshot(shot_id: str):
        data = SCREENSHOTS.get(shot_id)
        if data is None:
            return JSONResponse(status_code=404, content={"error": "shot not found"})
        return Response(content=data, media_type="image/png")

    @app.post("/api/chat")
    async def api_chat(request: Request):
        body = await request.json()
        role = body.get("role", "user")
        content = body.get("content", "")
        if not content:
            return JSONResponse(status_code=400, content={"error": "empty content"})
        bus.publish_sync({"type": "chat", "role": role, "content": content})
        return {"ok": True}

    @app.post("/api/upload")
    async def api_upload(request: Request):
        """iPad → 电脑 文件上传：multipart/form-data，字段 file + path（目标绝对路径）。"""
        try:
            form = await request.form()
            up = form.get("file")
            path = (form.get("path") or "").strip()
            if up is None or not path:
                return JSONResponse(status_code=400, content={"error": "需要 file 和 path 字段"})
            content = await up.read()
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)
            bus.publish_sync({"type": "tool_call", "tool": "upload_file", "args": {"path": path},
                              "status": "ok", "ts": time.time(), "duration_ms": 0,
                              "result": {"path": str(p), "size": len(content)}})
            return {"ok": True, "path": str(p), "size": len(content)}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"{type(e).__name__}: {e}"})

    @app.get("/api/info")
    async def api_info():
        """返回服务器与工具信息（dashboard 设置页展示）。"""
        return {
            "name": "winpc",
            "version": "1.5.0",
            "tools": [t.__name__ for t in winpc.ALL_TOOLS],
            "token_fixed": bool(cfg.get("token")),
            "dashboard_password": bool(dash_pwd),
        }

    # 文件回传路由
    @app.get("/files/{fid}")
    async def download_file(fid: str):
        path = tools_network.FILE_REGISTRY.get(fid)
        if not path or not Path(path).exists():
            return JSONResponse(status_code=404, content={"error": "file not found"})
        return FileResponse(path, filename=Path(path).name)

    # MCP 挂载（内部路由 /mcp）
    app.mount("/", mcp_app)

    # -------------------------------------------------- 启动信息
    lan_ip = get_lan_ip()
    print()
    print("=" * 56)
    print("  winpc-mcp 已启动")
    print(f"  MCP 端点:   http://{lan_ip}:{cfg['port']}/mcp")
    print(f"  Token:      {cfg['token']}")
    print(f"  Dashboard:  http://{lan_ip}:{cfg['port']}/dashboard"
          + ("  (口令保护)" if dash_pwd else ""))
    print("=" * 56)
    print("  在 iPad 端 (Minis) 添加 MCP 服务器:")
    print(f"    minis-mcp-cli add --name winpc --url http://{lan_ip}:{cfg['port']}/mcp"
          f" --header \"Authorization: Bearer {cfg['token']}\"")
    print()
    uvicorn.run(app, host=cfg["host"], port=cfg["port"], log_level="info")


if __name__ == "__main__":
    main()

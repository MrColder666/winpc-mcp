"""网络工具：HTTP 请求、文件下载、文件回传（电脑文件给 iPad 拉取）。"""
import os
import secrets
from pathlib import Path

from .tools import tool

# server.py 启动时填充为 http://<局域网IP>:<port>
BASE_URL = ""
# fid -> 绝对路径（server.py 的 /files 路由读取）
FILE_REGISTRY: dict = {}


@tool
def http_request(method: str = "GET", url: str = "", headers: dict = None, body: str = "", timeout: int = 30) -> dict:
    """发送任意 HTTP 请求（用于调用 API 或测试连通性）。method: GET/POST/PUT/DELETE; url: 完整地址; headers: 请求头字典; body: 请求体文本"""
    try:
        import requests
    except ImportError:
        raise RuntimeError("缺少 requests 依赖")
    try:
        resp = requests.request(method.upper(), url, headers=headers or {}, data=body or None, timeout=timeout)
        return {"status": resp.status_code, "headers": dict(resp.headers), "body": resp.text[:200000]}
    except requests.RequestException as e:
        raise RuntimeError(f"请求失败: {e}")


@tool
def download_file(url: str, save_path: str, timeout: int = 120) -> dict:
    """下载网络文件到电脑指定路径（自动创建目录）。url: 文件地址; save_path: 保存的绝对路径"""
    try:
        import requests
    except ImportError:
        raise RuntimeError("缺少 requests 依赖")
    p = Path(save_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        resp = requests.get(url, timeout=timeout, stream=True)
        resp.raise_for_status()
        with open(p, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
        return {"path": str(p), "size": p.stat().st_size, "status": resp.status_code}
    except requests.RequestException as e:
        raise RuntimeError(f"下载失败: {e}")


@tool
def serve_file(path: str) -> dict:
    """把电脑上的文件暴露为下载链接，iPad 端可通过该 URL 拉取文件。path: 电脑上的文件绝对路径"""
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise RuntimeError(f"文件不存在: {path}")
    fid = secrets.token_urlsafe(16)
    FILE_REGISTRY[fid] = str(p)
    if not BASE_URL:
        raise RuntimeError("服务器尚未初始化 BASE_URL")
    return {
        "url": f"{BASE_URL}/files/{fid}",
        "filename": p.name,
        "size": p.stat().st_size,
        "hint": "在 iPad 端用 curl 或浏览器下载该 URL",
    }

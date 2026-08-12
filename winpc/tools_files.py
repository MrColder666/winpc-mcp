"""文件系统工具：读、写、列目录、搜索、删除、文件信息。"""
import os
from pathlib import Path

from .tools import CONFIG, tool


def _check_allowed(path: str):
    """若配置了 allowed_dirs，则校验路径必须位于允许目录内。"""
    dirs = [str(d) for d in CONFIG.get("allowed_dirs", []) if d]
    if not dirs:
        return
    p = os.path.abspath(path)
    if not any(os.path.abspath(d) == p or p.startswith(os.path.abspath(d) + os.sep) for d in dirs):
        raise RuntimeError(f"路径不在允许目录内: {p}")


@tool
def read_file(path: str, max_bytes: int = 1048576) -> dict:
    """读取文本文件内容。path: 绝对路径; max_bytes: 最多读取字节数（默认1MB）"""
    _check_allowed(path)
    p = Path(path)
    if not p.exists():
        raise RuntimeError(f"文件不存在: {path}")
    if p.is_dir():
        raise RuntimeError(f"是目录而非文件: {path}")
    data = p.read_bytes()[:max_bytes]
    for enc in ("utf-8", "gbk", "utf-16", "latin-1"):
        try:
            return {"path": str(p), "content": data.decode(enc), "size": p.stat().st_size, "truncated": p.stat().st_size > max_bytes}
        except UnicodeDecodeError:
            continue
    return {"path": str(p), "content": data.decode("latin-1"), "size": p.stat().st_size, "truncated": True}


@tool
def write_file(path: str, content: str, encoding: str = "utf-8", append: bool = False) -> dict:
    """写入/追加文本文件（自动创建父目录）。path: 绝对路径; content: 内容; encoding: 编码（默认utf-8，中文Windows可用gbk）; append: True为追加"""
    _check_allowed(path)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with open(p, mode, encoding=encoding, newline="") as f:
        f.write(content)
    return {"path": str(p), "size": p.stat().st_size, "appended": append}


@tool
def list_dir(path: str = ".", detailed: bool = False) -> dict:
    """列出目录内容。path: 目录路径（默认当前目录）; detailed: True时返回大小/修改时间"""
    p = Path(path)
    if not p.exists():
        raise RuntimeError(f"路径不存在: {path}")
    if not p.is_dir():
        raise RuntimeError(f"不是目录: {path}")
    items = []
    for child in sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
        try:
            if detailed:
                st = child.stat()
                items.append({"name": child.name, "type": "dir" if child.is_dir() else "file", "size": st.st_size, "mtime": st.st_mtime})
            else:
                items.append({"name": child.name, "type": "dir" if child.is_dir() else "file"})
        except OSError:
            continue
    return {"path": str(p), "count": len(items), "items": items}


@tool
def search_files(query: str, root: str = "", max_results: int = 50, max_depth: int = 6) -> dict:
    """按文件名关键字递归搜索文件。query: 文件名包含的关键字; root: 搜索根目录（默认所有盘符，Windows）; max_results: 最多返回数; max_depth: 最大深度"""
    if not root:
        root = _default_root()
    _check_allowed(root)
    matches = []
    base = Path(root)
    base_depth = len(base.parts)
    try:
        for dirpath, dirnames, filenames in os.walk(base):
            depth = len(Path(dirpath).parts) - base_depth
            if depth > max_depth:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if not d.startswith(("$", "System Volume"))]
            for fn in filenames:
                if query.lower() in fn.lower():
                    matches.append(str(Path(dirpath) / fn))
                    if len(matches) >= max_results:
                        return {"query": query, "root": root, "count": len(matches), "matches": matches, "truncated": True}
    except OSError:
        pass
    return {"query": query, "root": root, "count": len(matches), "matches": matches, "truncated": False}


def _default_root():
    if os.name == "nt":
        drives = [f"{chr(c)}:\\" for c in range(ord("C"), ord("Z") + 1) if os.path.exists(f"{chr(c)}:\\")]
        return drives[0] if drives else "C:\\"
    return os.path.expanduser("~")


@tool
def delete_file(path: str, confirm: bool = False) -> dict:
    """删除文件或空目录（永久删除，不进回收站）。path: 绝对路径; confirm: 确认删除，当配置 confirm_dangerous=true 时必需"""
    if CONFIG.get("confirm_dangerous") and not confirm:
        raise RuntimeError("危险操作需要 confirm=True 确认")
    _check_allowed(path)
    p = Path(path)
    if not p.exists():
        raise RuntimeError(f"路径不存在: {path}")
    if p.is_dir():
        try:
            p.rmdir()
        except OSError as e:
            raise RuntimeError(f"目录非空，无法删除: {e}")
    else:
        p.unlink()
    return {"deleted": path}


@tool
def get_file_info(path: str) -> dict:
    """获取文件/目录的详细信息。path: 绝对路径"""
    _check_allowed(path)
    p = Path(path)
    if not p.exists():
        raise RuntimeError(f"路径不存在: {path}")
    st = p.stat()
    return {
        "path": str(p),
        "type": "dir" if p.is_dir() else "file",
        "size": st.st_size,
        "mtime": st.st_mtime,
        "ctime": st.st_ctime,
        "absolute": str(p.absolute()),
    }

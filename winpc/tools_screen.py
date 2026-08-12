"""屏幕工具：截图（多显示器支持）。"""
import base64
import io

from .tools import tool


def _mss_available():
    try:
        import mss  # noqa: F401
        return True
    except ImportError:
        return False


@tool
def screenshot(monitor: int = 0) -> str:
    """截取电脑屏幕，返回 PNG 图片的 base64 编码字符串。monitor: 显示器编号（0=所有显示器合并, 1=主显示器, 2+=扩展显示器）"""
    try:
        import mss
        from PIL import Image
    except ImportError:
        raise RuntimeError("缺少 mss/Pillow 依赖，请运行: pip install mss pillow")

    with mss.mss() as sct:
        monitors = sct.monitors
        idx = monitor if 0 <= monitor < len(monitors) else 0
        shot = sct.grab(monitors[idx])
        img = Image.frombytes("RGB", shot.size, shot.rgb)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()


@tool
def get_screen_size() -> dict:
    """获取屏幕分辨率与显示器列表。"""
    try:
        import mss
    except ImportError:
        raise RuntimeError("缺少 mss 依赖")
    with mss.mss() as sct:
        return {"monitors": [{"index": i, "left": m["left"], "top": m["top"], "width": m["width"], "height": m["height"]} for i, m in enumerate(sct.monitors)]}

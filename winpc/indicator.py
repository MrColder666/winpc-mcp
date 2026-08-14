"""操作指示器：Minis 操控电脑时的视觉反馈。

- 鼠标光标替换为黄色 MINIS 光标（手工构造 .cur 文件 + SetSystemCursor）
- 被操作窗口周围显示黄色边框（topmost layered 窗口 + GDI 绘制）
- 非 Windows 环境（开发/测试）自动降级为 no-op

仅在鼠标/键盘类工具被调用时激活；操作停止数秒后自动恢复。
"""
import os
import struct
import sys
import threading
import time

IS_WINDOWS = sys.platform == "win32"

# ---------------------------------------------------------------- 常量
CURSOR_FILE = os.path.join(os.environ.get("TEMP", "/tmp"), "winpc_minis_cursor.cur")
BORDER_COLOR_RGB = (255, 216, 0)        # 明黄
BORDER_WIDTH = 3
BORDER_HIDE_DELAY = 2.0                 # 无操作 2s 后隐藏边框
CURSOR_RESTORE_DELAY = 8.0              # 无操作 8s 后恢复系统光标
KEY_RGB = (255, 0, 255)                 # colorkey 洋红（透明通道）

# Win32 常量
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_POPUP = 0x80000000
SW_HIDE = 0
HWND_TOPMOST = -1
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
WM_PAINT = 0x000F
WM_DESTROY = 0x0002
OCR_NORMAL = 32512
SPI_SETCURSORS = 0x0057
LWA_COLORKEY = 0x00000001
NULL_BRUSH = 5
HOTSPOT = (2, 2)

_state = {"cursor_on": False, "last_action": 0.0, "border_hwnd": None,
          "ready": False, "starting": False}
_start_lock = threading.Lock()


def _log(msg):
    print(f"[indicator] {msg}", flush=True)


def _colorref(rgb):
    """(R,G,B) -> COLORREF 0x00BBGGRR"""
    return rgb[0] | (rgb[1] << 8) | (rgb[2] << 16)


# ================================================================ 光标
def _ensure_cursor_file():
    """生成黄色 MINIS 光标 .cur（32x32 RGBA，手工构造 CUR 文件格式）。

    CUR = ICONDIR(6) + ICONDIRENTRY(16) + [BITMAPINFOHEADER + XOR + AND mask]
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    if os.path.exists(CURSOR_FILE) and time.time() - os.path.getmtime(CURSOR_FILE) < 86400 * 7:
        return CURSOR_FILE
    try:
        size = 32
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # 黄色箭头（经典光标形状）
        arrow = [(2, 2), (22, 18), (15, 18), (18, 27), (13, 30), (10, 21), (2, 26)]
        d.polygon(arrow, fill=(255, 216, 0, 255), outline=(40, 30, 0, 255))
        # MINIS 文字（光标下方）
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 10)
        except Exception:
            font = ImageFont.load_default()
        d.text((4, 22), "MINIS", fill=(255, 216, 0, 255), font=font,
               stroke_width=1, stroke_fill=(20, 15, 0, 255))

        w, h = img.size
        # ICONDIR：type=2（cursor）
        header = struct.pack("<HHH", 0, 2, 1)
        # 图像数据：BITMAPINFOHEADER(40) + XOR(BGRA 自下而上) + AND(0)
        raw = bytearray()
        for y in range(h - 1, -1, -1):
            for x in range(w):
                r, g, b, a = img.getpixel((x, y))
                raw += bytes((b, g, r, a))
        xor = bytes(raw)
        and_mask = b"\x00" * (w * h // 8)
        img_data_len = 40 + len(xor) + len(and_mask)
        bih = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0,
                          len(xor) + len(and_mask), 0, 0, 0, 0)
        img_data = bih + xor + and_mask
        entry = struct.pack("<BBBBHHII", w, h, 0, 0, HOTSPOT[0], HOTSPOT[1],
                            img_data_len, 22)
        with open(CURSOR_FILE, "wb") as f:
            f.write(header + entry + img_data)
        return CURSOR_FILE
    except Exception as e:
        _log(f"生成光标失败: {e}")
        return None


def _set_cursor():
    if not IS_WINDOWS or _state["cursor_on"]:
        return
    import ctypes
    try:
        cur = _ensure_cursor_file()
        if not cur:
            return
        user32 = ctypes.windll.user32
        hcur = user32.LoadCursorFromFileW(cur)
        if not hcur:
            _log("LoadCursorFromFile 失败")
            return
        if user32.SetSystemCursor(hcur, OCR_NORMAL):
            _state["cursor_on"] = True
    except Exception as e:
        _log(f"设置光标失败: {e}")


def _restore_cursor():
    if not IS_WINDOWS or not _state["cursor_on"]:
        return
    import ctypes
    try:
        ctypes.windll.user32.SystemParametersInfoW(SPI_SETCURSORS, 0, None, 0)
        _state["cursor_on"] = False
    except Exception as e:
        _log(f"恢复光标失败: {e}")


# ================================================================ 边框窗口
def _border_thread():
    """独立线程创建 topmost 边框窗口 + 消息循环 + 定时隐藏/恢复。"""
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    kernel32 = ctypes.windll.kernel32

    WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, wintypes.UINT,
                                 wintypes.WPARAM, wintypes.LPARAM)

    @WNDPROC
    def wndproc(hwnd, msg, wparam, lparam):
        if msg == WM_PAINT:
            try:
                ps = wintypes.PAINTSTRUCT()
                hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
                rect = wintypes.RECT()
                user32.GetClientRect(hwnd, ctypes.byref(rect))
                # 全窗口刷 colorkey 色（透明）
                key_brush = gdi32.CreateSolidBrush(_colorref(KEY_RGB))
                user32.FillRect(hdc, ctypes.byref(rect), key_brush)
                gdi32.DeleteObject(key_brush)
                # 黄色边框
                pen = gdi32.CreatePen(0, BORDER_WIDTH, _colorref(BORDER_COLOR_RGB))
                gdi32.SelectObject(hdc, pen)
                gdi32.SelectObject(hdc, gdi32.GetStockObject(NULL_BRUSH))
                gdi32.Rectangle(hdc, BORDER_WIDTH // 2, BORDER_WIDTH // 2,
                                rect.right - BORDER_WIDTH // 2,
                                rect.bottom - BORDER_WIDTH // 2)
                gdi32.DeleteObject(pen)
                user32.EndPaint(hwnd, ctypes.byref(ps))
            except Exception:
                pass
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    hinst = kernel32.GetModuleHandleW(None)
    cls = wintypes.WNDCLASSW()
    cls.lpfnWndProc = wndproc
    cls.hInstance = hinst
    cls.lpszClassName = "WinpcMinisIndicator"
    cls.hCursor = user32.LoadCursorW(None, OCR_NORMAL)
    cls.hbrBackground = 0
    user32.RegisterClassW(ctypes.byref(cls))

    hwnd = user32.CreateWindowExW(
        WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
        "WinpcMinisIndicator", "MINIS",
        WS_POPUP, 0, 0, 10, 10, None, None, hinst, None)
    if not hwnd:
        _log("创建边框窗口失败")
        return
    _state["border_hwnd"] = hwnd
    user32.SetLayeredWindowAttributes(hwnd, _colorref(KEY_RGB), 0, LWA_COLORKEY)
    _state["ready"] = True

    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
        now = time.time()
        if _state["border_hwnd"]:
            if now - _state["last_action"] > BORDER_HIDE_DELAY:
                user32.ShowWindow(_state["border_hwnd"], SW_HIDE)
            if now - _state["last_action"] > CURSOR_RESTORE_DELAY:
                _restore_cursor()


def _ensure_border():
    if not IS_WINDOWS or _state["ready"]:
        return
    with _start_lock:
        if _state["starting"] or _state["ready"]:
            return
        _state["starting"] = True
    threading.Thread(target=_border_thread, daemon=True).start()
    # 等待窗口就绪（最多 2s）
    for _ in range(20):
        if _state["ready"]:
            break
        time.sleep(0.1)


def _highlight_window_at(x, y):
    """高亮 (x, y) 所在窗口。"""
    if not IS_WINDOWS:
        return
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    _ensure_border()
    hwnd = _state["border_hwnd"]
    if not hwnd:
        return
    target = user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))
    if not target:
        return
    rect = wintypes.RECT()
    if not user32.GetWindowRect(target, ctypes.byref(rect)):
        return
    bw = BORDER_WIDTH
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    user32.SetWindowPos(hwnd, HWND_TOPMOST,
                        rect.left - bw, rect.top - bw, w + 2 * bw, h + 2 * bw,
                        SWP_NOACTIVATE | SWP_SHOWWINDOW)
    user32.InvalidateRect(hwnd, None, True)


# ================================================================ 对外接口
def activate(x=None, y=None):
    """Minis 开始操作：黄色光标 + 高亮鼠标所在窗口。"""
    if not IS_WINDOWS:
        return
    _state["last_action"] = time.time()
    _set_cursor()
    if x is None or y is None:
        import ctypes
        from ctypes import wintypes
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        x, y = pt.x, pt.y
    _highlight_window_at(x, y)


def deactivate():
    """显式结束操作：恢复光标（边框由定时器隐藏）。"""
    if not IS_WINDOWS:
        return
    _state["last_action"] = 0.0
    _restore_cursor()

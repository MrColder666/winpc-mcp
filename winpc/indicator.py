"""操作指示器：Minis 操控电脑时的视觉反馈。

- 鼠标光标替换为黄色 MINIS 光标（SetSystemCursor）
- 被操作窗口周围显示黄色边框（topmost layered 窗口 + GDI 绘制）
- 非 Windows 环境（开发/测试）自动降级为 no-op

仅在鼠标/键盘类工具被调用时激活；操作停止数秒后自动恢复。
"""
import os
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
TRANSPARENT_KEY_RGB = (255, 0, 255)     # colorkey 洋红

# Win32 常量
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_POPUP = 0x80000000
SW_HIDE = 0
SW_SHOWNOACTIVATE = 4
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
WM_PAINT = 0x000F
WM_DESTROY = 0x0002
WM_ERASEBKGND = 0x0014
OCR_NORMAL = 32512
SPI_SETCURSORS = 0x0057
LWA_COLORKEY = 0x00000001
NULL_BRUSH = 5

_state = {"cursor_on": False, "last_action": 0.0, "border_hwnd": None, "ready": False}


def _log(msg):
    print(f"[indicator] {msg}", flush=True)


# ================================================================ 光标
def _ensure_cursor_file():
    """用 PIL 生成黄色 MINIS 光标 .cur（48x48）。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    if os.path.exists(CURSOR_FILE) and time.time() - os.path.getmtime(CURSOR_FILE) < 86400 * 7:
        return CURSOR_FILE
    try:
        size = 48
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # 黄色箭头（经典光标形状：右上尖角）
        arrow = [(2, 2), (30, 26), (21, 26), (25, 38), (18, 41), (14, 29), (2, 36)]
        d.polygon(arrow, fill=(255, 216, 0, 255), outline=(40, 30, 0, 255))
        # MINIS 文字（光标下方右侧）
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 14)
        except Exception:
            font = ImageFont.load_default()
        d.text((8, 30), "MINIS", fill=(255, 216, 0, 255), font=font,
               stroke_width=2, stroke_fill=(20, 15, 0, 255))
        img.save(CURSOR_FILE, format="CUR", sizes=[(48, 48)])
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
        # SetSystemCursor 接管句柄所有权，替换系统箭头光标
        if user32.SetSystemCursor(hcur, OCR_NORMAL):
            _state["cursor_on"] = True
    except Exception as e:
        _log(f"设置光标失败: {e}")


def _restore_cursor():
    if not IS_WINDOWS or not _state["cursor_on"]:
        return
    import ctypes
    try:
        # 重新加载系统默认光标集
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
                # 全窗口刷透明 key 色
                key_brush = gdi32.CreateSolidBrush(
                    0x00FF00 | (TRANSPARENT_KEY_RGB[1] << 8) | (TRANSPARENT_KEY_RGB[2] << 16))
                user32.FillRect(hdc, ctypes.byref(rect), key_brush)
                gdi32.DeleteObject(key_brush)
                # 黄色边框（4 条）
                bw = BORDER_WIDTH
                pen = gdi32.CreatePen(0, bw,
                                      0x00D800 | (BORDER_COLOR_RGB[1] << 8) | (BORDER_COLOR_RGB[2] << 16))
                old = gdi32.SelectObject(hdc, pen)
                old_brush = gdi32.SelectObject(hdc, gdi32.GetStockObject(NULL_BRUSH))
                gdi32.Rectangle(hdc, 1, 1, rect.right - 1, rect.bottom - 1)
                gdi32.SelectObject(hdc, old_brush)
                gdi32.SelectObject(hdc, old)
                gdi32.DeleteObject(pen)
                user32.EndPaint(hwnd, ctypes.byref(ps))
            except Exception:
                pass
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    hinst = user32.GetModuleHandleW(None)
    cls = wintypes.WNDCLASSW()
    cls.lpfnWndProc = wndproc
    cls.hInstance = hinst
    cls.lpszClassName = "WinpcMinisIndicator"
    cls.hCursor = user32.LoadCursorW(None, 32512)
    cls.hbrBackground = 0
    if not user32.RegisterClassW(ctypes.byref(cls)):
        # 已注册则忽略
        pass

    hwnd = user32.CreateWindowExW(
        WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
        "WinpcMinisIndicator", "MINIS",
        WS_POPUP, 0, 0, 10, 10, None, None, hinst, None)
    if not hwnd:
        _log("创建边框窗口失败")
        return
    _state["border_hwnd"] = hwnd
    # colorkey 透明：洋红区域全透明，只露出黄色边框
    user32.SetLayeredWindowAttributes(hwnd, 0x00FF00 | (0 << 8) | (0xFF << 16), 0, LWA_COLORKEY)
    _state["ready"] = True

    # 消息循环 + 定时隐藏/恢复
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
    threading.Thread(target=_border_thread, daemon=True).start()


def _highlight_window_at(x, y):
    """高亮 (x, y) 所在窗口。"""
    if not IS_WINDOWS:
        return
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    if not _state["border_hwnd"]:
        _ensure_border()
        time.sleep(0.2)
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
    _ensure_border()
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

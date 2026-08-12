"""键盘鼠标工具：输入文本、按键、鼠标移动/点击/滚动、剪贴板。"""
import sys

from .tools import tool


def _pg():
    try:
        import pyautogui
    except ImportError:
        raise RuntimeError("缺少 pyautogui 依赖，请运行: pip install pyautogui")
    pyautogui.FAILSAFE = True  # 鼠标甩到左上角紧急停止
    return pyautogui


def _is_ascii(text: str) -> bool:
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


@tool
def type_text(text: str, method: str = "auto") -> dict:
    """向当前焦点窗口输入文本。text: 要输入的内容; method: auto(自动选择)/type(逐字符，仅ASCII)/clipboard(剪贴板粘贴，支持中文)"""
    pg = _pg()
    if method == "auto":
        method = "type" if _is_ascii(text) else "clipboard"
    if method == "clipboard":
        import pyperclip
        pyperclip.copy(text)
        pg.hotkey("ctrl", "v")
    else:
        pg.write(text, interval=0.01)
    return {"ok": True, "method": method, "chars": len(text)}


@tool
def press_key(key: str, modifiers: str = "") -> dict:
    """按下键盘按键，可带修饰键组合。key: 主键(如 'enter','tab','a','F5'); modifiers: 空格分隔的修饰键(如 'ctrl shift' = Ctrl+Shift+key)"""
    pg = _pg()
    mods = [m for m in modifiers.split() if m]
    if mods:
        pg.hotkey(*mods, key)
    else:
        pg.press(key)
    return {"ok": True, "key": key, "modifiers": modifiers}


@tool
def click(x: int = None, y: int = None, button: str = "left", clicks: int = 1, interval: float = 0.1) -> dict:
    """鼠标点击。x/y: 屏幕坐标（省略则点击当前位置）; button: left/right/middle; clicks: 点击次数; interval: 间隔秒"""
    pg = _pg()
    pg.click(x, y, clicks=clicks, interval=interval, button=button)
    return {"ok": True, "x": x, "y": y, "button": button, "clicks": clicks}


@tool
def move_mouse(x: int, y: int, duration: float = 0.3) -> dict:
    """移动鼠标到指定坐标。x/y: 目标坐标; duration: 移动耗时秒"""
    pg = _pg()
    pg.moveTo(x, y, duration=duration)
    return {"ok": True, "x": x, "y": y}


@tool
def scroll(amount: int = -3) -> dict:
    """滚动鼠标滚轮。amount: 正数向上滚，负数向下滚"""
    _pg().scroll(amount)
    return {"ok": True, "amount": amount}


@tool
def get_mouse_position() -> dict:
    """获取当前鼠标坐标。"""
    x, y = _pg().position()
    return {"x": x, "y": y}


@tool
def get_clipboard() -> dict:
    """读取电脑剪贴板内容。"""
    try:
        import pyperclip
        return {"content": pyperclip.paste()}
    except ImportError:
        raise RuntimeError("缺少 pyperclip 依赖")


@tool
def set_clipboard(content: str) -> dict:
    """设置电脑剪贴板内容。content: 要写入剪贴板的文本"""
    import pyperclip
    pyperclip.copy(content)
    return {"ok": True, "chars": len(content)}

"""工具注册装饰器与共享配置。

所有工具函数定义在各 tools_*.py 模块中，用 @tool 装饰标记，
server.py 统一遍历注册到 FastMCP。
"""

# 共享运行时配置（由 server.py 从 config.json 加载后填充）
CONFIG = {
    "confirm_dangerous": False,  # True 时删除文件/杀进程需显式 confirm=True
}


def tool(fn):
    """标记一个函数为 MCP 工具。"""
    fn._WINPC_TOOL = True
    return fn


def is_tool(obj):
    return callable(obj) and getattr(obj, "_WINPC_TOOL", False)


def get_tools(*modules):
    """收集多个模块中所有被 @tool 标记的函数，保持模块顺序。"""
    tools = []
    seen = set()
    for mod in modules:
        for name in dir(mod):
            obj = getattr(mod, name)
            if is_tool(obj) and name not in seen:
                seen.add(name)
                tools.append(obj)
    return tools

"""winpc — Windows PC 远程控制 MCP 工具包。"""

from . import tools_apps, tools_command, tools_dev, tools_dsh, tools_files, tools_input, tools_manage, tools_network, tools_screen, tools_system
from .tools import get_tools

ALL_TOOLS = get_tools(
    tools_command,
    tools_files,
    tools_screen,
    tools_input,
    tools_apps,
    tools_system,
    tools_network,
    tools_dev,
    tools_manage,
    tools_dsh,
)

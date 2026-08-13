# winpc-mcp

**从 iPad（Minis）通过 MCP 远程控制 Windows 电脑。**

在电脑上运行一个 MCP 服务器，iPad 上的 Minis 通过 HTTP 调用它的工具：
执行命令、管理文件、截屏、控制键盘鼠标、打开应用、管理进程、下载文件等 ——
就像在电脑本地跑了一个 agent。

```
┌────────── iPad ──────────┐        ┌────────── Windows 电脑 ──────────┐
│ Minis (MCP 客户端)       │  HTTP  │ winpc-mcp (MCP 服务器)          │
│   minis-mcp-cli 调用工具  │◀──────▶│   :8765/mcp  (Bearer Token)     │
└──────────────────────────┘        └──────────────────────────────────┘
          局域网直连 / Tailscale / 隧道
```

## ✨ 功能

| 类别 | 工具 |
|---|---|
| 命令 | `run_powershell` `run_cmd` `run_shell` |
| 文件 | `read_file` `write_file` `list_dir` `search_files` `delete_file` `get_file_info` |
| 屏幕 | `screenshot` `get_screen_size` |
| 输入 | `type_text` `press_key` `click` `move_mouse` `scroll` `get_mouse_position` `get_clipboard` `set_clipboard` |
| 应用 | `open_app` `open_url` `list_windows` `focus_window` `close_window` |
| 系统 | `system_info` `list_process` `kill_process` |
| 网络 | `http_request` `download_file` `serve_file`（电脑文件回传给 iPad） |

## 🚀 快速开始

### 1. 电脑端（Windows）

```bat
:: 方式一：一键脚本（自动建虚拟环境、装依赖、启动）
start.bat

:: 方式二：手动
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

启动后终端会打印：

```
MCP 地址:    http://192.168.x.x:8765/mcp
Token:       xxxxx（未配置时自动生成，请保存）
Dashboard:   http://192.168.x.x:8765/dashboard
```

> 固定 Token：把 `config.example.json` 复制为 `config.json`，填入你的 token，
> 或设置环境变量 `WINPC_TOKEN`。自动生成的 token 每次重启都会变。

### 2. iPad 端（Minis）

```bash
minis-mcp-cli add --name winpc \
  --url http://<电脑IP>:8765/mcp \
  --header "Authorization: Bearer <token>"

minis-mcp-cli tools winpc        # 查看工具
minis-mcp-cli call winpc system_info   # 测试调用
```

之后在 Minis 对话里直接说“帮我看看电脑的 CPU 占用”即可。

## 📊 Dashboard（电脑端实时监控）

电脑浏览器打开 `http://<电脑IP>:8765/dashboard`（或本机 `localhost:8765`）：

- **DIALOGUE**：实时显示 iPad 端对话（Minis 通过 `sync_chat` 工具同步，或 `POST /api/chat`）
- **TOOL CALLS**：每次工具调用的完整记录——参数、结果、耗时、成功/失败状态
- **SCREEN + SYSTEM**：最近截图画廊（点击放大）+ CPU/内存/磁盘实时状态
- **⌘K** 命令面板：过滤工具调用、跳转面板、暂停/恢复实时流、清空日志、复制地址

可配置 `dashboard_password` 口令保护（开启后首次访问需输入口令）。

## 🔒 安全

- 所有 `/mcp` 和 `/files` 请求必须带 `Authorization: Bearer <token>`
- 默认只监听局域网；**不要**把 8765 端口直接映射到公网
- 异地访问推荐 [Tailscale](https://tailscale.com)（加密隧道），两端装 app 登录同一账号后，
  MCP 地址直接换成 Tailscale IP（`http://100.x.x.x:8765/mcp`）即可
- `config.json` 可配置：
  - `allowed_dirs`：限定文件操作目录（空 = 不限制，完全操控）
  - `confirm_dangerous`：`true` 时删除文件 / 杀进程需显式 `confirm=true`

## ⚙️ 配置

```jsonc
{
  "host": "0.0.0.0",          // 监听地址
  "port": 8765,               // 端口
  "token": "",                // MCP 认证 token（留空则自动生成）
  "allowed_dirs": [],         // 文件操作白名单目录（空=不限制）
  "confirm_dangerous": false, // true=危险操作需确认
  "dashboard_password": ""    // Dashboard 访问口令（空=不设防）
}
```

## 📝 开发

```bash
# 本地（非 Windows）也能启动核心功能测试：
# run_powershell/run_cmd/键盘鼠标/截图等 Windows 专属工具会返回明确错误
pip install -r requirements.txt
python server.py
```

工具代码在 `winpc/` 目录，新增工具 = 在 `tools_*.py` 里加一个带 `@tool` 装饰器和
类型注解 + docstring 的函数即可，启动时自动注册。

## 🛣️ 路线图

- [x] Dashboard：电脑浏览器实时查看对话、工具调用、截图
- [x] 49 个工具（v1.5.0）：新增开发（git/后台任务/批量读写）、系统管理（音量/电源/通知/网络/温度）、批量文件（write_files_batch/serve_file_batch）、iPad→电脑上传端点
- [x] Dashboard 重新设计（v1.2.0）：左侧导航栏 + agent 风格对话流（工具输入/输出内联）+ 右侧 Screens/Files/System 三 Tab + 全量动效
- [ ] 浏览器自动化（CDP 驱动 Chrome）
- [ ] 开机自启（任务计划程序）

## 📄 License

MIT

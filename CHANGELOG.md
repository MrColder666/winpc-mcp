# Changelog

## [v1.1.1] - 2026-08-12

### Changed

- Dashboard 动效升级（find-animation-opportunities 审计 + animate 实施）：
  - 工具卡片状态过渡：RUNNING → OK/ERROR 时背景、左边条、状态点、状态文字 250ms 平滑过渡
  - 完成态内容（耗时 chip、ARGS/RESULT 块）160ms 优雅出现
  - 清空日志：180ms 淡出上移退出过渡后再清空 DOM
  - 统计计数变化：OK/ERR 数字 200ms 闪烁强调色反馈
- 新增 `--ease-out` 动效 token（cubic-bezier(0.23, 1, 0.32, 1)），全部动效尊重 `prefers-reduced-motion`

### Fixed

- README 补充 MCP 接入关键步骤：必须带 `Accept: application/json, text/event-stream` header，否则握手失败；`Session not found` 时执行 `minis-mcp-cli refresh winpc`

## [v1.1.0] - 2026-08-12

### Added

- Dashboard（电脑端实时监控台）：对话流、工具调用日志（参数/结果/耗时/状态）、截图画廊、系统状态（CPU/内存/磁盘）、⌘K 命令面板
- 事件总线：所有 MCP 工具调用自动记录并推送（SSE），`/api/history`、`/api/status`、`/api/screenshots/<id>` 接口
- `sync_chat` 工具：iPad 端对话实时同步到 Dashboard（也可 `POST /api/chat`）
- Dashboard 口令保护（`dashboard_password` 配置项）

### Fixed

- 工具调用事件未发布（同步 wrapper 误用 async publish）
- Dashboard 认证探测流程（无口令配置时不再误弹登录层）

## [v1.0.0] - 2026-08-12

### Added

- MCP 服务器：30 个工具（PowerShell/CMD 命令、文件读写搜索、截屏、键盘鼠标、应用/窗口管理、进程管理、HTTP/下载、文件回传）
- Bearer Token 认证 + 文件回传下载端点
- `start.bat` 一键启动（自动创建 venv 并安装依赖）
- 跨平台：非 Windows 系统也能启动测试核心功能

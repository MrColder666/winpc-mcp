# Changelog

## [v1.3.0] - 2026-08-13

### Added

- Dashboard 全面美化 + 全量动效增强：
  - **数字计数器动效**：统计数字变化时滚动上升（countUp 300ms）
  - **数字闪烁反馈**：OK/ERR 计数变化时缩放 + 变色闪烁（400ms）
  - **running shimmer**：工具运行中气泡整体流光扫过（1.5s linear）
  - **logo 光晕动画**：侧边栏 logo 呼吸光晕（3.4s ease-in-out）
  - **meter 填充动画**：系统仪表进度条 0.8s ease-out 填充 + 光泽扫过
  - **截图 hover 放大**：截图卡片悬浮时图片 scale(1.03)
  - **文件卡片 hover lift**：文件悬浮上移 + 阴影（--ease-out）
  - **tab pill 滑动指示器**：右侧 tab 底部指示条平滑滑动（280ms ease-out）
  - **视图切换动画**：chat/activity 切换时内容上浮淡入（250ms viewIn）
  - **tab 内容切换**：rtab 切换时淡入（200ms）
  - **统计数字 hover**：悬浮时轻微放大
  - **新增 --ease-spring / --ease-bounce 曲线**：logo、截图、cmd+k 使用弹性曲线
  - **地址栏点击复制**：点击服务器地址直接复制
- 全部动效遵循 `prefers-reduced-motion`（降级为瞬变）
- 全局 press feedback（scale 0.97, 160ms）+ hover lift（gated by hover: hover）

## [v1.2.2] - 2026-08-13

### Fixed

- **局域网无法连接 MCP（421 Invalid Host header）**：新版 MCP SDK 在 FastMCP 默认
  host（localhost）下自动启用 DNS rebinding 防护，只放行 127.0.0.1/localhost，
  导致从 iPad 通过局域网 IP 访问 `/mcp` 被拒（421）。
  - `server.py`：显式传入 `TransportSecuritySettings(enable_dns_rebinding_protection=False)`
    关闭防护（带 try/except 兼容旧版 SDK）
  - `requirements.txt`：固定 `fastmcp>=3.4,<3.5`，保证依赖的 MCP SDK 行为可预期

## [v1.2.1] - 2026-08-12

### Fixed

- `start.bat` 在 Windows CMD 下中文乱码：文件为 UTF-8 编码而 CMD 默认 GBK 代码页。
  脚本开头新增 `chcp 65001 >nul` 切换到 UTF-8 代码页，中文提示正常显示（功能不受影响）

## [v1.2.0] - 2026-08-12

### Added

- Dashboard 全新三栏布局（重新设计）：
  - **左侧导航栏（rail）**：winpc logo + 对话/活动视图切换 + 设置/账户抽屉，active 指示器滑动跟随（250ms）
  - **中间对话流（agent 风格）**：对话消息与工具调用气泡交错排列，每个工具显示输入（args）与输出（result），像普通 agent 界面
  - **右侧 Tab 化面板**：Screens（截图）/ Files（文件预览，serve_file 结果自动收集）/ System（系统状态）
  - 设置抽屉：服务器地址复制、实时流暂停/恢复开关、清空日志、版本信息
  - 账户抽屉：Dashboard 认证状态、重新登录
- 动效（find-animation-opportunities 门禁筛选）：
  - 侧边栏 active 指示器滑动（spatial consistency，250ms ease-out）
  - 抽屉滑入（320ms drawer 曲线 cubic-bezier(0.32, 0.72, 0, 1)）+ 行内容 stagger 40ms
  - 工具气泡 running→完成状态 chip 颜色过渡（250ms）+ 结果内容 160ms 出现
  - 工具气泡折叠/展开（grid-template-rows 高度动画 250ms）
  - running 状态骨架扫描条（1.1s 循环反馈）
  - 对话消息组入场 stagger（40ms）
  - 右侧 tab active pill 滑动 + 内容 fade/slide（160-200ms）
  - 全局 press feedback（scale 0.97，160ms）+ 空状态 logo 光晕
  - 全部尊重 prefers-reduced-motion（降级为瞬变）

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

# Changelog

## [v1.6.0] - 2026-08-13

### Added

- **操作指示器（操控可视化）**：Minis 操控电脑时的视觉反馈
  - 鼠标光标替换为**黄色 MINIS 光标**（PIL 生成 .cur，SetSystemCursor 临时替换，8s 无操作自动恢复）
  - 被操作窗口周围显示**黄色边框**（topmost layered 窗口 + GDI 绘制，WindowFromPoint 定位，2s 无操作自动隐藏）
  - 触发工具：move_mouse/click/type_text/press_key/scroll/get_mouse_position/set_clipboard/get_clipboard
  - 非 Windows 环境自动降级 no-op（不影响开发测试）

## [v1.5.0] - 2026-08-13

### Added

- **开发工具（vibe coding 专项）**：
  - `git_status` / `git_commit` / `git_push`：git 封装，一条龙版本管理
  - `install_packages(manager, packages)`：后台安装 pip/npm 包，返回 task_id 不阻塞
  - `get_task_status(task_id)`：查询后台任务结果（1 小时后自动清理）
  - `read_file_batch(paths)`：一次读取 N 个文件（查看项目代码）
  - `batch_run(commands)`：顺序执行多条命令返回数组
- **系统管理**：
  - `get_volume` / `set_volume`：音量控制（0-100）
  - `lock_screen` / `shutdown` / `reboot` / `sleep`：电源管理（危险操作需 confirm）
  - `get_network_info`：网卡 IP / 累计流量
  - `notify(title, message)`：Windows 桌面通知气泡（6 秒自动消失）
  - `get_cpu_temp`：CPU 温度（ACPI，台式机可能不支持）
- **文件传输**：
  - `serve_file_batch(paths)`：一次暴露 N 个文件下载链接
  - **`POST /api/upload`**：iPad → 电脑文件上传（multipart: file + path），上传事件同步到 dashboard
- **Dashboard**：设置抽屉新增"可用工具"数量 + 完整工具清单（来自新 `/api/info` 端点）
- 工具总数 33 → 49

## [v1.4.0] - 2026-08-13

### Added

- **批量工具（解决 MCP 连接延迟导致的低效）**：
  - `write_files_batch(files)`：一次调用批量创建/覆盖 N 个文件（自动建父目录），
    vibe coding 创建项目从"20 次连接"降为"1 次连接"
  - `run_script(script, shell)`：一次执行整段多行 PowerShell/CMD 脚本，
    复杂操作不再拆成多次小调用
- 工具总数 31 → 33
- winpc-mcp skill 新增**操作规范**：禁止终端模拟（open_app+type_text+screenshot）、
  批量优先、读操作用专用工具、screenshot 为最后手段、错误预检

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

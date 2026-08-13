@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo   winpc-mcp 一键启动 (Windows)
echo ============================================
echo.

REM ---- 1. 检查 Python ----
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Python！
    echo 请先安装 Python 3.10+ 并勾选 "Add python.exe to PATH"
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM ---- 2. 创建虚拟环境 ----
if not exist ".venv" (
    echo [1/3] 首次运行，创建虚拟环境...
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
)

REM ---- 3. 安装依赖 ----
call ".venv\Scripts\activate.bat"
echo [2/3] 检查依赖...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络后重试
    pause
    exit /b 1
)

REM ---- 4. 启动 ----
echo [3/3] 启动 MCP 服务器...
echo.
python server.py
pause

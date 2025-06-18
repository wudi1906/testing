@echo off
echo 正在启动UI自动化测试系统前端...
echo.

REM 检查Node.js版本
node --version > nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Node.js，请先安装Node.js 18+
    pause
    exit /b 1
)

REM 检查npm版本
npm --version > nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到npm，请检查Node.js安装
    pause
    exit /b 1
)

REM 检查是否存在node_modules
if not exist "node_modules" (
    echo 正在安装依赖...
    npm install --legacy-peer-deps
    if %errorlevel% neq 0 (
        echo 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
)

REM 启动开发服务器
echo 启动开发服务器...
npm run dev

pause

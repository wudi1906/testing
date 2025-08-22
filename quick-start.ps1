# 🚀 快速启动脚本 - 简化版
# 自动检测目录位置并启动服务

# 设置UTF-8编码解决中文显示问题
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "🚀 快速启动UI自动化测试系统..." -ForegroundColor Green

# 获取当前目录
$currentPath = Get-Location
Write-Host "📍 当前目录: $currentPath" -ForegroundColor Cyan

# 智能路径检测
$backendPath = $null

# 情况1：已经在backend目录
if ($currentPath.Path -like "*\003\ui-automation\backend") {
    $backendPath = $currentPath.Path
    Write-Host "✅ 已在正确目录" -ForegroundColor Green
}
# 情况2：在testing根目录
elseif (Test-Path "003\ui-automation\backend") {
    $backendPath = Join-Path $currentPath "003\ui-automation\backend"
    Write-Host "📁 切换到backend目录" -ForegroundColor Yellow
    cd $backendPath
}
# 情况3：在子目录，需要向上查找
else {
    $testPath = $currentPath
    for ($i = 0; $i -lt 5; $i++) {
        $checkPath = Join-Path $testPath "003\ui-automation\backend"
        if (Test-Path $checkPath) {
            $backendPath = $checkPath
            Write-Host "📁 找到backend目录，切换中..." -ForegroundColor Yellow
            cd $backendPath
            break
        }
        $testPath = Split-Path $testPath -Parent
        if (-not $testPath) { break }
    }
}

if (-not $backendPath) {
    Write-Host "❌ 错误：无法找到backend目录！" -ForegroundColor Red
    Write-Host "💡 请确保在UI自动化项目目录中运行此脚本" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "🎯 目标目录: $backendPath" -ForegroundColor Green

# 设置必要的环境变量
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'

# 启动服务
Write-Host ""
Write-Host "🚀 启动服务器..." -ForegroundColor Green
Write-Host "📖 API文档: http://localhost:8000/api/v1/docs" -ForegroundColor Cyan
Write-Host "🛑 按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
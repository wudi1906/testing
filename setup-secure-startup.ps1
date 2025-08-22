# 🔐 安全启动脚本 - 使用本地环境变量
# 这个脚本不包含任何硬编码密钥，安全可提交

Write-Host "🚀 UI自动化系统 - 安全启动" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Yellow

# 第一步：检查本地环境配置文件
$localEnvFile = "env-setup-local.ps1"
if (Test-Path $localEnvFile) {
    Write-Host "🔧 加载本地环境配置..." -ForegroundColor Cyan
    & ".\$localEnvFile"
} else {
    Write-Host "⚠️  未找到本地环境配置文件: $localEnvFile" -ForegroundColor Yellow
    Write-Host "请先复制 env-setup-example.ps1 为 $localEnvFile 并配置你的密钥" -ForegroundColor Yellow
    Write-Host "或者手动设置环境变量后再运行此脚本" -ForegroundColor Yellow
}

# 第二步：设置基础环境
Write-Host "🔧 设置基础环境..." -ForegroundColor Cyan
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'  # 强制unbuffered输出
$env:FORCE_ADSPOWER_ONLY = "true"

# 验证关键环境变量
Write-Host "🔍 验证环境变量..." -ForegroundColor Cyan
$requiredVars = @("ADSP_TOKEN", "DEEPSEEK_API_KEY", "OPENAI_API_KEY")
$missing = @()

foreach ($var in $requiredVars) {
    $value = [Environment]::GetEnvironmentVariable($var)
    if (-not $value -or $value -like "*your_*_here") {
        $missing += $var
        Write-Host "❌ $var: 未设置或使用示例值" -ForegroundColor Red
    } else {
        $maskedValue = $value.Substring(0, [Math]::Min(10, $value.Length)) + "..."
        Write-Host "✅ $var: $maskedValue" -ForegroundColor Green
    }
}

if ($missing.Count -gt 0) {
    Write-Host "⚠️  警告：缺少必要的环境变量配置" -ForegroundColor Yellow
    Write-Host "系统可能无法正常工作，请配置后重新启动" -ForegroundColor Yellow
}

# 第三步：激活虚拟环境并启动
Write-Host "🔧 激活虚拟环境..." -ForegroundColor Cyan
cd "E:\Program Files\cursorproject\testing"
& ".venv/Scripts/Activate.ps1"

Write-Host "🔧 切换到后端目录..." -ForegroundColor Cyan
cd "003\ui-automation\backend"

Write-Host "=================================================================" -ForegroundColor Yellow
Write-Host "🚀 启动Uvicorn服务器..." -ForegroundColor Green
Write-Host "🌐 服务地址: http://localhost:8000" -ForegroundColor Yellow
Write-Host "📚 API文档: http://localhost:8000/api/v1/docs" -ForegroundColor Yellow
Write-Host "=================================================================" -ForegroundColor Yellow

# 启动服务
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

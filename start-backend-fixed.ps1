# UI自动化测试系统 - 完整启动脚本（修复版）
# 包含所有必要的环境变量设置、编码修复和服务启动

# 修复PowerShell编码问题
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "🚀 正在启动UI自动化测试系统..." -ForegroundColor Green

# 设置基础环境
$env:PYTHONIOENCODING = 'utf-8'

# AdsPower 配置
$env:FORCE_ADSPOWER_ONLY = "true"
# 🔐 API密钥配置 - 请设置你自己的真实密钥
$env:ADSP_TOKEN = $env:ADSP_TOKEN ?? "your_adspower_token_here"
$env:QG_AUTHKEY = $env:QG_AUTHKEY ?? "your_qingguo_authkey_here" 
$env:QG_AUTHPWD = $env:QG_AUTHPWD ?? "your_qingguo_authpwd_here"
$env:QG_TUNNEL_ENDPOINT = $env:QG_TUNNEL_ENDPOINT ?? "your_qingguo_endpoint_here"
$env:DEEPSEEK_API_KEY = $env:DEEPSEEK_API_KEY ?? "sk-your_deepseek_api_key_here"
$env:OPENAI_API_KEY = $env:OPENAI_API_KEY ?? "sk-proj-your_openai_api_key_here"
$env:GEMINI_API_KEY = $env:GEMINI_API_KEY ?? "your_gemini_api_key_here"
$env:UI_TARS_API_KEY = $env:UI_TARS_API_KEY ?? "your_uitars_api_key_here"
$env:QWEN_API_KEY = $env:QWEN_API_KEY ?? "sk-your_qwen_api_key_here"
$env:QWEN_VL_API_KEY = $env:QWEN_VL_API_KEY ?? "sk-your_qwen_vl_api_key_here"
$env:GLM_API_KEY = $env:GLM_API_KEY ?? "your_glm_api_key_here"

# AdsPower配置
$env:ADSP_PREFER_V1 = "true"
$env:ADSP_VERBOSE_LOG = "true"
$env:ADSP_MAX_CONCURRENCY = "15"

Write-Host "✅ 环境变量设置完成" -ForegroundColor Green

# 验证关键环境变量
Write-Host "🔍 验证环境变量..." -ForegroundColor Yellow
Write-Host "ADSP_TOKEN: $($env:ADSP_TOKEN.Substring(0,10))..." -ForegroundColor Cyan
Write-Host "FORCE_ADSPOWER_ONLY: $env:FORCE_ADSPOWER_ONLY" -ForegroundColor Cyan
Write-Host "QG_AUTHKEY: $env:QG_AUTHKEY" -ForegroundColor Cyan

# 激活虚拟环境
Write-Host "🔧 激活虚拟环境..." -ForegroundColor Yellow
& ".venv/Scripts/Activate.ps1"

# 切换到后端目录
$backendPath = "003\ui-automation\backend"
if (Test-Path $backendPath) {
    Set-Location $backendPath
    Write-Host "📁 工作目录: $(Get-Location)" -ForegroundColor Green
} else {
    Write-Host "❌ 后端目录不存在: $backendPath" -ForegroundColor Red
    exit 1
}

# 启动服务
Write-Host ""
Write-Host "🚀 启动 Uvicorn 服务器..." -ForegroundColor Green
Write-Host "服务地址: http://localhost:8000" -ForegroundColor Yellow
Write-Host "API文档: http://localhost:8000/api/v1/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Red
Write-Host "======================================" -ForegroundColor Gray

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

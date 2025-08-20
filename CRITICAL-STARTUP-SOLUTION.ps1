# 🔥🔥🔥 UI自动化系统 - 紧急修复启动脚本 🔥🔥🔥
# 解决所有启动、日志和执行问题的终极方案

Write-Host "🚨 紧急修复：UI自动化系统启动" -ForegroundColor Red
Write-Host "=================================================================" -ForegroundColor Yellow

# 第一步：强制关闭所有相关进程
Write-Host "🔧 步骤1：清理环境..." -ForegroundColor Cyan
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process uvicorn -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep 2

# 第二步：设置完整环境变量
Write-Host "🔧 步骤2：设置环境变量..." -ForegroundColor Cyan
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUNBUFFERED = '1'  # 强制unbuffered输出
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

# 第三步：激活虚拟环境
Write-Host "🔧 步骤3：激活虚拟环境..." -ForegroundColor Cyan
cd "E:\Program Files\cursorproject\testing"
& ".venv/Scripts/Activate.ps1"
Write-Host "✅ 虚拟环境激活完成" -ForegroundColor Green

# 第四步：切换到正确目录
Write-Host "🔧 步骤4：切换到后端目录..." -ForegroundColor Cyan
cd "003\ui-automation\backend"
Write-Host "📁 当前目录: $(Get-Location)" -ForegroundColor Yellow

# 第五步：显示启动信息
Write-Host "🔧 步骤5：准备启动服务..." -ForegroundColor Cyan
Write-Host "🌐 服务地址: http://localhost:8000" -ForegroundColor Yellow
Write-Host "📚 API文档: http://localhost:8000/api/v1/docs" -ForegroundColor Yellow
Write-Host "🔥 执行测试: http://localhost:8000/api/v1/web/execution/execute-by-id" -ForegroundColor Yellow

Write-Host "=================================================================" -ForegroundColor Yellow
Write-Host "🚀 现在启动Uvicorn服务器..." -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Yellow

# 第六步：启动服务（前台运行以便看到所有日志）
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

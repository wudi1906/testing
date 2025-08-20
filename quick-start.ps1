# 快速启动脚本 - 精简版
# 🔐 设置API密钥 - 请替换为你自己的真实密钥
$env:FORCE_ADSPOWER_ONLY="true"
$env:ADSP_TOKEN=$env:ADSP_TOKEN ?? "your_adspower_token_here"
$env:ADSP_PREFER_V1="true"
$env:ADSP_VERBOSE_LOG="true"
$env:QG_AUTHKEY=$env:QG_AUTHKEY ?? "your_qingguo_authkey_here"
$env:QG_AUTHPWD=$env:QG_AUTHPWD ?? "your_qingguo_authpwd_here"
$env:QG_TUNNEL_ENDPOINT=$env:QG_TUNNEL_ENDPOINT ?? "your_qingguo_endpoint_here"
$env:DEEPSEEK_API_KEY=$env:DEEPSEEK_API_KEY ?? "sk-your_deepseek_api_key_here"
$env:OPENAI_API_KEY=$env:OPENAI_API_KEY ?? "sk-proj-your_openai_api_key_here"
$env:GLM_API_KEY=$env:GLM_API_KEY ?? "your_glm_api_key_here"

cd "E:\Program Files\cursorproject\testing\003\ui-automation\backend"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

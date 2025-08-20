# 🔐 环境变量配置模板
# 复制此文件为 env-setup-local.ps1 并填入你的真实密钥
# env-setup-local.ps1 已在 .gitignore 中，不会被提交到Git

# AdsPower配置
$env:ADSP_TOKEN = "your_adspower_token_here"  # 替换为你的AdsPower Token
$env:ADSP_PREFER_V1 = "true"
$env:ADSP_VERBOSE_LOG = "true"
$env:ADSP_MAX_CONCURRENCY = "15"

# 青果代理配置
$env:QG_AUTHKEY = "your_qingguo_authkey_here"  # 替换为你的青果AuthKey
$env:QG_AUTHPWD = "your_qingguo_authpwd_here"  # 替换为你的青果AuthPwd
$env:QG_TUNNEL_ENDPOINT = "your_qingguo_endpoint_here"  # 替换为你的青果Tunnel端点

# AI模型API密钥配置
$env:DEEPSEEK_API_KEY = "sk-your_deepseek_api_key_here"  # 替换为你的DeepSeek API Key
$env:OPENAI_API_KEY = "sk-proj-your_openai_api_key_here"  # 替换为你的OpenAI API Key
$env:GEMINI_API_KEY = "your_gemini_api_key_here"  # 替换为你的Gemini API Key
$env:UI_TARS_API_KEY = "your_uitars_api_key_here"  # 替换为你的UI-TARS API Key
$env:QWEN_API_KEY = "sk-your_qwen_api_key_here"  # 替换为你的Qwen API Key
$env:QWEN_VL_API_KEY = "sk-your_qwen_vl_api_key_here"  # 替换为你的Qwen VL API Key
$env:GLM_API_KEY = "your_glm_api_key_here"  # 替换为你的GLM API Key

Write-Host "✅ 本地环境变量配置完成" -ForegroundColor Green

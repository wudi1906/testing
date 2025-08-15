@echo off
:: API密钥配置模板
:: 复制此文件为 api-keys-local.bat 并填入真实的API密钥
:: api-keys-local.bat 已加入 .gitignore，不会提交到GitHub

echo 设置AI模型API密钥...

:: 方案1：阿里通义千问 (推荐 - 视觉任务最佳)
set QWEN_API_KEY=your-qwen-api-key-here
set QWEN_VL_API_KEY=your-qwen-api-key-here

:: 方案2：智谱AI GLM-4V (备选 - 性能优秀)
set GLM_API_KEY=your-glm-api-key-here

:: 方案3：DeepSeek (文本任务高性价比)
set DEEPSEEK_API_KEY=your-deepseek-api-key-here

:: 方案4：豆包/UI-TARS (UI自动化专用)
set UI_TARS_API_KEY=your-uitars-api-key-here

:: 方案5：OpenAI (兼容性最好，较贵)
set OPENAI_API_KEY=your-openai-api-key-here

echo API密钥配置完成

@echo off
echo 🎭 启用AI模拟模式 - 用于功能测试
echo.

:: 设置模拟模式环境变量
set AI_MOCK_MODE=true
set MOCK_AI_SERVICE=true

:: 使用模拟API密钥
set QWEN_VL_API_KEY=mock-qwen-key-for-testing
set QWEN_API_KEY=mock-qwen-key-for-testing
set GLM_API_KEY=mock-glm-key-for-testing
set DEEPSEEK_API_KEY=mock-deepseek-key-for-testing
set UI_TARS_API_KEY=mock-uitars-key-for-testing
set OPENAI_API_KEY=mock-openai-key-for-testing

echo ✅ 模拟模式已启用
echo 📍 注意: 这是模拟模式，不会调用真实AI服务
echo 🧪 可以用于测试系统功能和界面

:: 启动后端服务
echo.
echo 🚀 启动模拟模式后端服务...
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

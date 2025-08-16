@echo off
echo 🚀 启动UI自动化后端服务 (含AI模型配置)

:: 设置基础环境变量
set DATABASE_URL=mysql+aiomysql://root:123456@localhost:3306/test_case_automation
set PLAYWRIGHT_WORKSPACE=E:\Program Files\cursorproject\testing\003\ui-automation\examples\midscene-playwright
set PYTHONIOENCODING=utf-8

:: AI模型API密钥配置 - 从本地密钥文件读取
:: 注意：请创建 api-keys-local.bat 文件来设置真实密钥
if exist "003\ui-automation\api-keys-local.bat" (
    echo 🔑 加载本地API密钥配置...
    call "003\ui-automation\api-keys-local.bat"
) else (
    echo ⚠️  未找到 api-keys-local.bat 文件
    echo 请参考 api-keys-template.bat 创建您的密钥配置文件
    pause
    exit /b 1
)

:: 通用API基础URL配置
set QWEN_VL_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
set GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4  
set DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
set UI_TARS_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

echo ✅ 环境变量配置完成
echo 📂 工作空间: %PLAYWRIGHT_WORKSPACE%
echo 🔑 使用AI模型: QWen-VL-Plus
echo.

cd /d "E:\Program Files\cursorproject\testing\003\ui-automation\backend"

echo 🌟 启动FastAPI服务器...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause

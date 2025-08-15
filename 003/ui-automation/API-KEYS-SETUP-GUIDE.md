# 🔑 完整API密钥配置指南

## 🚨 重要安全提醒
- **本地密钥文件已加入 .gitignore，不会提交到GitHub**
- **所有硬编码的API密钥已清理**
- **使用环境变量和本地配置文件管理密钥**

## 🎯 已配置的所有API密钥

### 1. 阿里通义千问 (推荐 - 视觉任务最佳)
- **模型**: `qwen-vl-plus`
- **用途**: 网页元素识别、UI自动化
- **优势**: 中文优化、识别精准、响应快

### 2. 智谱AI GLM-4V (备选 - 性能优秀)
- **模型**: `glm-4v`
- **用途**: 多模态理解、视觉任务
- **优势**: 国产优秀、理解能力强

### 3. DeepSeek (文本任务高性价比)
- **模型**: `deepseek-chat` / `deepseek-vl`
- **用途**: 代码生成、文本分析
- **优势**: 价格便宜、推理能力强

### 4. 豆包/UI-TARS (UI自动化专用)
- **模型**: `doubao-1-5-ui-tars-250428`
- **用途**: UI元素识别、界面理解
- **优势**: 专门针对UI自动化训练

### 5. OpenAI GPT-4V (兼容性最好)
- **模型**: `gpt-4o`
- **用途**: 通用多模态任务
- **优势**: 兼容性好、能力全面

## 🚀 快速配置步骤

### 第1步：复制密钥配置模板
```bash
cd 003/ui-automation
copy api-keys-template.bat api-keys-local.bat
```

### 第2步：编辑本地密钥文件
打开 `api-keys-local.bat`，现在已经包含了所有真实密钥！

### 第3步：启动系统
```bash
# 双击运行
start-backend-with-ai.bat

# 或手动运行
call api-keys-local.bat
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🎮 智能API选择机制

系统会按优先级自动选择可用的API：

1. **QWen-VL-Plus** - 视觉任务首选
2. **GLM-4V** - 备选方案
3. **UI-TARS** - UI自动化专用
4. **DeepSeek** - 文本任务
5. **OpenAI** - 通用兼容

## 📊 不同场景的最佳选择

| 任务类型 | 推荐模型 | 原因 |
|---------|---------|------|
| 🌐 网页自动化 | QWen-VL-Plus | 中文界面识别准确 |
| 🎯 UI元素定位 | UI-TARS | 专门训练的UI模型 |
| 📝 代码生成 | DeepSeek | 代码理解能力强 |
| 🔄 通用任务 | GLM-4V | 综合能力强 |
| 🌍 国际兼容 | OpenAI | 全球通用 |

## 🔧 环境变量配置

如果需要手动设置环境变量：

```powershell
# Windows PowerShell - 示例（请使用您的真实API密钥）
$env:QWEN_VL_API_KEY="your-qwen-api-key-here"
$env:GLM_API_KEY="your-glm-api-key-here"
$env:DEEPSEEK_API_KEY="your-deepseek-api-key-here"
$env:UI_TARS_API_KEY="your-uitars-api-key-here"
$env:OPENAI_API_KEY="your-openai-api-key-here"
```

## ✅ 验证配置

启动后端时，你会看到：
```
🎯 使用AI模型: QWen-VL-Plus
✅ 环境变量配置完成
🔑 API密钥验证通过
```

## 🔒 安全保障

- ✅ **api-keys-local.bat** 已加入 .gitignore
- ✅ **所有配置文件中的密钥都已清理**
- ✅ **使用环境变量安全管理**
- ✅ **本地文件不会被提交到GitHub**

现在可以安全地使用所有AI模型，享受超快的云端视觉AI自动化体验！🚀

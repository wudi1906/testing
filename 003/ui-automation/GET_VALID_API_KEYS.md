# 🔑 获取有效AI模型API密钥指南

## ⚠️ 重要提示

**测试显示当前所有API密钥都已过期或无效！** 这就是为什么系统一直报401错误的根本原因。

需要获取新的有效API密钥才能正常使用AI自动化功能。

## 🎯 推荐获取顺序（按性价比排序）

### 1. 🥇 阿里云通义千问 (最推荐)
- **优势**: 中文优化好，视觉模型强，价格便宜
- **获取地址**: https://dashscope.console.aliyun.com/
- **步骤**:
  1. 注册阿里云账号
  2. 开通灵积模型服务
  3. 创建API-KEY
  4. 获取 `sk-xxx` 格式的密钥

**模型推荐**:
- `qwen-vl-plus` - 视觉理解（UI自动化最佳）
- `qwen-plus` - 文本任务

### 2. 🥈 智谱AI GLM (备选)
- **优势**: 多模态能力强，国产可控
- **获取地址**: https://open.bigmodel.cn/
- **步骤**:
  1. 注册智谱AI账号
  2. 实名认证
  3. 创建API密钥
  4. 获取API KEY

**模型推荐**:
- `glm-4v` - 多模态理解

### 3. 🥉 DeepSeek (高性价比)
- **优势**: 代码能力强，价格极低
- **获取地址**: https://platform.deepseek.com/
- **步骤**:
  1. 注册DeepSeek账号
  2. 充值（最低10元）
  3. 创建API Key
  4. 获取 `sk-xxx` 格式密钥

**模型推荐**:
- `deepseek-vl` - 视觉+文本
- `deepseek-chat` - 纯文本

### 4. 豆包/UI-TARS (专用)
- **优势**: 专门针对UI自动化优化
- **获取地址**: https://console.volcengine.com/ark/
- **步骤**:
  1. 注册火山引擎账号
  2. 开通豆包服务
  3. 申请UI-TARS模型权限
  4. 创建API密钥

### 5. OpenAI (最贵但兼容性好)
- **获取地址**: https://platform.openai.com/
- **注意**: 需要国外信用卡，价格较高

## 🛠️ 配置API密钥

### 方法1: 修改 `api-keys-local.bat`
```batch
@echo off
:: 本地API密钥配置

:: 阿里云通义千问 (推荐)
set QWEN_API_KEY=sk-你的新密钥
set QWEN_VL_API_KEY=sk-你的新密钥

:: 智谱AI (备选)
set GLM_API_KEY=你的GLM密钥

:: DeepSeek (高性价比)
set DEEPSEEK_API_KEY=sk-你的DeepSeek密钥

echo API密钥配置完成
```

### 方法2: 环境变量
```powershell
# Windows PowerShell
$env:QWEN_VL_API_KEY="sk-你的新密钥"
$env:GLM_API_KEY="你的GLM密钥"
$env:DEEPSEEK_API_KEY="sk-你的DeepSeek密钥"
```

## 🧪 验证API密钥

配置完成后运行测试：
```bash
python test_ai_models.py
```

应该看到：
```
✅ 可用模型 (X个):
  🔸 阿里通义千问视觉版
     模型: qwen-vl-plus | 响应时间: 1.23s
     性价比: ⭐⭐⭐⭐⭐ | 用途: UI自动化视觉识别
```

## 💰 费用参考

### 推荐配置 (月费用约5-20元)
- **阿里通义千问**: ¥0.008/1K tokens (便宜)
- **智谱GLM-4V**: ¥0.01/1K tokens (中等)
- **DeepSeek**: ¥0.0014/1K tokens (最便宜)

### 用量估算
- **日常开发测试**: 10-50万tokens/月
- **频繁自动化**: 50-100万tokens/月
- **商业项目**: 100万+ tokens/月

## 🚀 快速开始（临时方案）

如果暂时无法获取API密钥，可以使用模拟模式进行功能测试：

```bash
# 启用模拟模式
set AI_MOCK_MODE=true

# 运行测试
python test_ai_models.py
```

模拟模式可以测试系统功能，但无法进行真实的AI识别。

## 📞 技术支持

如果在获取或配置API密钥时遇到问题：

1. **查看测试日志**: `python test_ai_models.py`
2. **检查网络连接**: 确保可以访问对应的API服务
3. **验证密钥格式**: 不同服务商的密钥格式不同
4. **检查余额**: 确保账户有足够余额

---
**重要**: 获取任何一个有效的API密钥后，系统就可以正常工作了！推荐优先获取阿里云通义千问的API密钥。

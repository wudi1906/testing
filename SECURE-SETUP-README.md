# 🔐 安全配置指南

## 📋 问题说明

之前的启动脚本包含硬编码的API密钥，被GitHub的安全扫描检测到。现在已修复为安全的配置方式。

## 🚀 快速设置

### 方法1：使用安全启动脚本（推荐）

1. **复制环境配置文件**：
   ```powershell
   copy env-setup-template.ps1 env-setup-local.ps1
   ```

2. **编辑本地配置文件**：
   打开 `env-setup-local.ps1`，替换所有示例值为你的真实密钥

3. **运行安全启动脚本**：
   ```powershell
   .\setup-secure-startup.ps1
   ```

### 方法2：手动设置环境变量

在PowerShell中手动设置所有必要的环境变量，然后运行任何启动脚本：

```powershell
# 设置你的真实密钥
$env:ADSP_TOKEN = "你的AdsPower Token"
$env:QG_AUTHKEY = "你的青果AuthKey"
$env:QG_AUTHPWD = "你的青果AuthPwd"
$env:QG_TUNNEL_ENDPOINT = "你的青果Tunnel端点"
$env:DEEPSEEK_API_KEY = "你的DeepSeek API Key"
$env:OPENAI_API_KEY = "你的OpenAI API Key"
$env:GEMINI_API_KEY = "你的Gemini API Key"
$env:UI_TARS_API_KEY = "你的UI-TARS API Key"
$env:QWEN_API_KEY = "你的Qwen API Key"
$env:QWEN_VL_API_KEY = "你的Qwen VL API Key"
$env:GLM_API_KEY = "你的GLM API Key"

# 然后运行启动脚本
.\CRITICAL-STARTUP-SOLUTION.ps1
```

## 🔐 安全特性

1. **本地配置文件** - `env-setup-local.ps1` 在 `.gitignore` 中，不会被提交
2. **环境变量优先** - 脚本优先使用已设置的环境变量
3. **示例值保护** - 使用明显的示例值，避免意外提交真实密钥
4. **密钥验证** - 启动时检查密钥是否正确配置

## 📝 密钥获取方式

- **AdsPower Token**: 从AdsPower客户端获取
- **青果代理**: 从青果网络账户获取
- **AI模型密钥**: 从各自的官方平台获取
  - DeepSeek: https://platform.deepseek.com/
  - OpenAI: https://platform.openai.com/
  - Gemini: https://makersuite.google.com/
  - UI-TARS: 豆包平台
  - Qwen: 阿里云平台
  - GLM: 智谱AI平台

## ⚠️ 重要提醒

- **永远不要**将真实密钥提交到Git仓库
- 定期轮换API密钥
- 使用最小权限原则配置密钥权限
- 在团队协作时，每个人使用自己的密钥配置

## 🎯 现在可以安全提交了！

所有硬编码密钥已移除，可以正常提交代码到GitHub。

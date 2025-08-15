# 🔑 AI模型API密钥配置指南

## 🏆 推荐配置：阿里通义千问视觉版

### 1. 获取API密钥
1. 访问 [阿里云 DashScope](https://dashscope.aliyun.com/)
2. 注册/登录账号
3. 创建API密钥
4. 获得类似 `sk-xxx` 格式的密钥

### 2. 配置方法

**方法1：环境变量（推荐）**
```bash
# Windows PowerShell
$env:QWEN_API_KEY="your-actual-qwen-api-key"

# Linux/Mac
export QWEN_API_KEY="your-actual-qwen-api-key"
```

**方法2：直接修改配置文件**
编辑 `midscene.config.ts`，将 `your-qwen-api-key` 替换为实际密钥

### 3. 价格对比 (按1000次调用)

| 模型 | 价格 | 速度 | 中文优化 | 推荐度 |
|------|------|------|----------|--------|
| **QWen-VL-Plus** | ¥8-12 | ⚡⚡⚡ | ✅ | 🌟🌟🌟🌟🌟 |
| GLM-4V | ¥10-15 | ⚡⚡ | ✅ | 🌟🌟🌟🌟 |
| DeepSeek-VL | ¥3-6 | ⚡⚡ | ✅ | 🌟🌟🌟 |
| GPT-4V | $30-50 | ⚡⚡⚡ | ❌ | 🌟🌟 |
| Gemini Pro Vision | $15-25 | ⚡⚡ | ❌ | 🌟🌟🌟 |

## 🔄 备选方案

### 智谱AI GLM-4V
```bash
# 取消注释 midscene.config.ts 中的 GLM-4V 配置
$env:GLM_API_KEY="your-glm-api-key"
```

### DeepSeek VL (最便宜)
```bash
# 取消注释 midscene.config.ts 中的 DeepSeek 配置  
$env:DEEPSEEK_API_KEY="your-deepseek-api-key"
```

## ⚡ 性能优化建议

1. **并发限制**：设置合理的并发请求数
2. **缓存策略**：相似页面可复用识别结果
3. **超时设置**：网络API建议30秒超时
4. **重试机制**：网络问题自动重试

## 🚀 快速测试
配置完成后，运行测试验证：
```bash
npm test -- --grep "问卷填写"
```

看到浏览器打开并自动操作，说明配置成功！

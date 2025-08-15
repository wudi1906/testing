import { defineConfig } from '@midscene/core';

export default defineConfig({
  /**
   * AI 模型服务配置
   * 优先使用高效的云端视觉AI服务
   */
  aiModel: (() => {
    // 自动选择最佳可用的API配置
    const apis = [
      {
        name: 'QWen-VL-Plus',
        key: process.env.QWEN_VL_API_KEY || process.env.QWEN_API_KEY,
        provider: 'openai-compatible',
        baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        model: 'qwen-vl-plus'
      },
      {
        name: 'GLM-4V',
        key: process.env.GLM_API_KEY,
        provider: 'openai-compatible',
        baseURL: 'https://open.bigmodel.cn/api/paas/v4',
        model: 'glm-4v'
      },
      {
        name: 'DeepSeek-VL',
        key: process.env.DEEPSEEK_API_KEY,
        provider: 'openai-compatible',
        baseURL: 'https://api.deepseek.com/v1',
        model: 'deepseek-vl'
      },
      {
        name: 'OpenAI GPT-4V',
        key: process.env.OPENAI_API_KEY,
        provider: 'openai',
        baseURL: 'https://api.openai.com/v1',
        model: 'gpt-4o'
      }
    ];

    // 找到第一个有效的API配置
    for (const api of apis) {
      if (api.key && api.key.trim() && !api.key.includes('your-')) {
        console.log(`🎯 使用AI模型: ${api.name}`);
        return {
          provider: api.provider,
          baseURL: api.baseURL,
          model: api.model,
          apiKey: api.key
        };
      }
    }

    // 如果没有找到有效配置，返回默认配置并警告
    console.warn('⚠️ 未找到有效的AI API密钥，请检查环境变量配置');
    return {
      provider: 'openai-compatible',
      baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
      model: 'qwen-vl-plus',
      apiKey: 'please-set-your-api-key'
    };
  })(),

  /**
   * 执行配置
   */
  execution: {
    // 启用可视模式（显示浏览器窗口）
    headless: false,
    
    // 执行超时时间
    timeout: 30000,
    
    // 详细日志输出
    verbose: true,
    
    // 保存执行截图
    saveScreenshots: true,
  },

  /**
   * 报告配置
   */
  reporting: {
    // 自动打开报告
    openReport: true,
    
    // 报告输出目录
    outputDir: './midscene_run/report',
  },
});

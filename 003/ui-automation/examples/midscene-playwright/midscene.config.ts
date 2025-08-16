import { defineConfig } from '@midscene/core';

export default defineConfig({
  /**
   * AI 模型服务配置
   * 优先使用高效的云端视觉AI服务
   */
  aiModel: (() => {
    // 详细的环境变量调试日志
    console.log('🔍 Midscene配置调试 - 环境变量检查:');
    console.log('  QWEN_VL_API_KEY:', process.env.QWEN_VL_API_KEY ? `存在(${process.env.QWEN_VL_API_KEY.substring(0, 10)}...)` : '❌ 未设置');
    console.log('  QWEN_API_KEY:', process.env.QWEN_API_KEY ? `存在(${process.env.QWEN_API_KEY.substring(0, 10)}...)` : '❌ 未设置');
    console.log('  GLM_API_KEY:', process.env.GLM_API_KEY ? `存在(${process.env.GLM_API_KEY.substring(0, 10)}...)` : '❌ 未设置');
    console.log('  DEEPSEEK_API_KEY:', process.env.DEEPSEEK_API_KEY ? `存在(${process.env.DEEPSEEK_API_KEY.substring(0, 10)}...)` : '❌ 未设置');
    console.log('  OPENAI_API_KEY:', process.env.OPENAI_API_KEY ? `存在(${process.env.OPENAI_API_KEY.substring(0, 10)}...)` : '❌ 未设置');
    
    // 优先级顺序选择API密钥 (按测试验证结果排序)
    const apiOptions = [
      { key: process.env.QWEN_VL_API_KEY || 'sk-741f3076d4f14ba2a9ba75fc59b38938', provider: 'openai-compatible', baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-vl-plus', name: 'QWen-VL (最佳)' },
      { key: process.env.QWEN_API_KEY || 'sk-741f3076d4f14ba2a9ba75fc59b38938', provider: 'openai-compatible', baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-plus', name: 'QWen' },
      { key: process.env.GLM_API_KEY || 'f168fedf2fc14e0e89d50706cdbd6ace.EV4BzLp3IGMwsl1K', provider: 'openai-compatible', baseURL: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4v', name: 'GLM-4V' },
      { key: process.env.DEEPSEEK_API_KEY || 'sk-ce1dd0750e824f369b4833c6ced9835a', provider: 'openai-compatible', baseURL: 'https://api.deepseek.com/v1', model: 'deepseek-chat', name: 'DeepSeek' },
      { key: process.env.OPENAI_API_KEY, provider: 'openai', baseURL: 'https://api.openai.com/v1', model: 'gpt-4o', name: 'OpenAI' },
    ];
    
    // 找到第一个有效的API密钥
    for (const option of apiOptions) {
      if (option.key && option.key.trim() && !option.key.includes('your-')) {
        console.log('🎯 Midscene选择的API配置:', {
          provider: option.provider,
          model: option.model,
          apiKey: option.key.substring(0, 10) + '...'
        });
        return {
          provider: option.provider,
          baseURL: option.baseURL,
          model: option.model,
          apiKey: option.key,
        };
      }
    }
    
    // 如果没有找到有效的API密钥，使用默认值
    console.warn('⚠️ 未找到有效的环境变量API密钥，使用默认配置');
    const defaultKey = 'sk-d20e5a88d7ec47ed8ad29be76b2e6a92';
    console.log('🎯 使用默认API密钥:', defaultKey.substring(0, 10) + '...');
    
    return {
      provider: 'openai-compatible',
      baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
      model: 'qwen-vl-plus',
      apiKey: defaultKey,
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

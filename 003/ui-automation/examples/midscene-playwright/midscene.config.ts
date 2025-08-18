declare const process: any;

function isValidKey(provider: string, key?: string): boolean {
  if (!key || !key.trim()) return false;
  const k = key.trim();
  switch (provider) {
    case 'qwen':
      return !k.includes('你的') && !k.includes('your-') && k.startsWith('sk-') && k.length > 30;
    case 'glm':
      return !k.includes('你的') && !k.includes('your-') && k.includes('.') && k.length > 40;
    case 'deepseek':
      // DeepSeek 的密钥前缀通常为 sk-，但不同账户形态可能不同；排除占位符
      return !k.includes('你的') && !k.includes('your-') && k.length > 20;
    case 'openai':
      // Project Key（sk-proj-）常被判定格式不符，这里仅接受经典 sk-
      return !k.includes('你的') && !k.includes('your-') && k.startsWith('sk-') && !k.startsWith('sk-proj-') && k.length > 30;
    case 'uitars':
      // 豆包 UI-TARS 使用 UUID 样式密钥 8-4-4-4-12
      return !k.includes('你的') && !k.includes('your-') && /^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$/.test(k);
    default:
      return false;
  }
}

const config = {
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
    
    // Mock 开关：用于无真实密钥时的可视化演示
    if (process.env.AI_MOCK_MODE === 'true') {
      console.log('🧪 Mock模式已启用，使用模拟AI服务配置');
      return {
        provider: 'mock',
        apiKey: process.env.MOCK_API_KEY || 'mock-api-key-for-testing',
        baseURL: process.env.MIDSCENE_MOCK_BASE_URL || 'http://localhost:8000/api/v1/mock/ai',
        model: 'mock-ui-model'
      };
    }
    
    // 若后端已通过环境变量强制选择Provider，直接按指定Provider返回配置
    const forced = (process.env.MIDSCENE_FORCE_PROVIDER || '').trim().toLowerCase();
    if (forced) {
      const map: any = {
        'qwen': {
          provider: 'openai-compatible', baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-vl-plus', key: process.env.QWEN_VL_API_KEY
        },
        'glm': {
          provider: 'openai-compatible', baseURL: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4v', key: process.env.GLM_API_KEY
        },
        'deepseek': {
          provider: 'openai-compatible', baseURL: 'https://api.deepseek.com/v1', model: 'deepseek-chat', key: process.env.DEEPSEEK_API_KEY
        },
        'uitars': {
          provider: 'openai-compatible', baseURL: 'https://ark.cn-beijing.volces.com/api/v3', model: 'doubao-1-5-ui-tars-250428', key: process.env.UI_TARS_API_KEY
        },
        'openai': {
          provider: 'openai', baseURL: 'https://api.openai.com/v1', model: 'gpt-4o', key: process.env.OPENAI_API_KEY
        }
      };
      const c = map[forced];
      if (c && c.key && c.key.trim()) {
        console.log('🎯 按后端预检强制选择Provider:', forced);
        return { provider: c.provider, baseURL: c.baseURL, model: c.model, apiKey: c.key };
      }
      console.warn('⚠️ 后端指定的 Provider 缺少密钥，回退到自动选择');
    }

    // 优先级顺序选择API密钥（只使用环境变量，不再使用任何硬编码密钥）
    const apiOptions = [
      { key: process.env.QWEN_VL_API_KEY, provider: 'openai-compatible', baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-vl-plus', name: 'QWen-VL (最佳)', validator: () => isValidKey('qwen', process.env.QWEN_VL_API_KEY) },
      { key: process.env.QWEN_API_KEY, provider: 'openai-compatible', baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1', model: 'qwen-vl-plus', name: 'QWen', validator: () => isValidKey('qwen', process.env.QWEN_API_KEY) },
      { key: process.env.GLM_API_KEY, provider: 'openai-compatible', baseURL: 'https://open.bigmodel.cn/api/paas/v4', model: 'glm-4v', name: 'GLM-4V', validator: () => isValidKey('glm', process.env.GLM_API_KEY) },
      { key: process.env.DEEPSEEK_API_KEY, provider: 'openai-compatible', baseURL: 'https://api.deepseek.com/v1', model: 'deepseek-chat', name: 'DeepSeek', validator: () => isValidKey('deepseek', process.env.DEEPSEEK_API_KEY) },
      { key: process.env.UI_TARS_API_KEY, provider: 'openai-compatible', baseURL: 'https://ark.cn-beijing.volces.com/api/v3', model: 'doubao-1-5-ui-tars-250428', name: 'UI-TARS', validator: () => isValidKey('uitars', process.env.UI_TARS_API_KEY) },
      { key: process.env.OPENAI_API_KEY, provider: 'openai', baseURL: 'https://api.openai.com/v1', model: 'gpt-4o', name: 'OpenAI', validator: () => isValidKey('openai', process.env.OPENAI_API_KEY) },
    ];
    
    // 找到第一个有效的API密钥
    for (const option of apiOptions) {
      // 仅当通过各自的有效性校验时才选择
      // OPENAI 会过滤掉非 sk-/sk-proj- 开头的无效 key（例如 UUID）
      const valid = (option as any).validator ? (option as any).validator() : false;
      if (valid) {
        console.log('🎯 Midscene选择的API配置:', {
          provider: option.provider,
          model: option.model,
          baseURL: option.baseURL,
          apiKey: option.key.substring(0, 10) + '...'
        });
        
        // 返回完整的配置
        return {
          provider: option.provider,
          baseURL: option.baseURL,
          model: option.model,
          apiKey: option.key,
        };
      }
    }
    
    // 没有找到有效密钥时，自动回落到 Mock，保障流程打通
    console.warn('⚠️ 未找到任何有效的API密钥，自动回落到 Mock 配置');
    return {
      provider: 'mock',
      apiKey: process.env.MOCK_API_KEY || 'mock-api-key-for-testing',
      baseURL: process.env.MIDSCENE_MOCK_BASE_URL || 'http://localhost:8000/api/v1/mock/ai',
      model: 'mock-ui-model'
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
};

export default config as any;

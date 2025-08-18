// 不使用 defineConfig，直接导出对象，避免命名导出报错
declare const process: any;

/**
 * Midscene.js 模拟配置文件
 * 用于在API密钥无效时进行功能测试
 */
const mockConfig = {
  /**
   * 模拟AI模型配置 - 不需要真实API密钥
   */
  aiModel: {
    provider: 'mock',
    apiKey: process.env.MOCK_API_KEY || 'mock-api-key-for-testing',
    baseURL: process.env.MIDSCENE_MOCK_BASE_URL || 'http://localhost:8000/api/v1/mock/ai',
    model: 'mock-ui-model'
  },

  /**
   * 执行配置
   */
  execution: {
    // 等待网络空闲的时间（毫秒）
    networkIdleTimeout: 2000,
    
    // 元素查找超时时间（毫秒）
    findElementTimeout: 10000,
    
    // 操作执行间隔（毫秒）
    actionInterval: 500,
  },

  /**
   * 截图配置
   */
  screenshot: {
    // 自动截图
    auto: true,
    
    // 截图质量 (0-100)
    quality: 80,
    
    // 是否包含失败截图
    onFailure: true
  },

  /**
   * 报告配置
   */
  report: {
    // 报告输出目录
    outputDir: './midscene_run/report',
    
    // 是否打开报告
    open: false,
    
    // 报告格式
    format: 'html'
  },

  /**
   * 模拟模式配置
   */
  mock: {
    // 启用模拟模式
    enabled: true,
    
    // 模拟响应延迟（毫秒）
    responseDelay: 100,
    
    // 模拟成功率（0-1）
    successRate: 0.9
  }
};

export default mockConfig as any;

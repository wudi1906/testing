// Midscene.js 配置文件 - 标准模式
// 完全依赖Midscene内置的环境变量机制，不再使用自定义配置

declare const process: any;

console.log('🔍 Midscene标准配置调试:');
console.log('  OPENAI_API_KEY:', process.env.OPENAI_API_KEY ? process.env.OPENAI_API_KEY.substring(0, 10) + '...' : '❌ 未设置');
console.log('  OPENAI_BASE_URL:', process.env.OPENAI_BASE_URL || '❌ 未设置');
console.log('  MIDSCENE_MODEL_NAME:', process.env.MIDSCENE_MODEL_NAME || '❌ 未设置');
console.log('  MIDSCENE_USE_QWEN_VL:', process.env.MIDSCENE_USE_QWEN_VL || '未设置');
console.log('  MIDSCENE_USE_VLM_UI_TARS:', process.env.MIDSCENE_USE_VLM_UI_TARS || '未设置');
console.log('  MIDSCENE_DEBUG_MODE:', process.env.MIDSCENE_DEBUG_MODE || '未设置');

// 如果检测到有效的标准环境变量，输出确认信息
if (process.env.OPENAI_API_KEY && process.env.OPENAI_BASE_URL) {
  console.log('✅ 检测到标准OpenAI兼容配置');
  console.log('   Provider将由Midscene内部自动选择');
} else {
  console.log('⚠️ 标准环境变量不完整，Midscene可能无法正常工作');
}

// Midscene会从以下标准环境变量自动读取配置：
// - OPENAI_API_KEY: API密钥
// - OPENAI_BASE_URL: API端点
// - MIDSCENE_MODEL_NAME: 模型名称
// - MIDSCENE_USE_QWEN_VL: 启用Qwen-VL
// - MIDSCENE_USE_VLM_UI_TARS: 启用UI-TARS
// - MIDSCENE_DEBUG_MODE: 调试模式

// 不再手动配置，让Midscene使用标准机制
export default {};
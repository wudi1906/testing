"""
AI模型可用性测试
测试所有配置的AI大模型是否可正常使用
"""
import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Tuple
from loguru import logger
from app.core.config import settings


class AIModelTester:
    """AI模型测试器 - 验证所有AI模型的可用性和性能"""
    
    def __init__(self):
        self.test_results = {}
        self.models_config = self._get_all_models_config()
        
    def _get_all_models_config(self) -> Dict:
        """获取所有AI模型配置"""
        return {
            "qwen_vl": {
                "name": "阿里通义千问视觉版 (推荐 - 视觉任务最佳)",
                "api_key": getattr(settings, 'QWEN_VL_API_KEY', ''),
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "qwen-vl-plus",
                "provider": "openai-compatible",
                "priority": 1,  # 最高优先级
                "cost_rating": "⭐⭐⭐⭐⭐",  # 性价比最高
                "use_case": "UI自动化视觉识别、OCR、图像理解"
            },
            "qwen": {
                "name": "阿里通义千问文本版",
                "api_key": getattr(settings, 'QWEN_API_KEY', ''),
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "qwen-plus",
                "provider": "openai-compatible",
                "priority": 2,
                "cost_rating": "⭐⭐⭐⭐⭐",
                "use_case": "文本生成、代码生成、逻辑推理"
            },
            "glm_4v": {
                "name": "智谱AI GLM-4V (备选 - 性能优秀)",
                "api_key": getattr(settings, 'GLM_API_KEY', ''),
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "model": "glm-4v",
                "provider": "openai-compatible",
                "priority": 3,
                "cost_rating": "⭐⭐⭐⭐",
                "use_case": "多模态理解、图文混合任务"
            },
            "deepseek_vl": {
                "name": "DeepSeek VL (文本+视觉高性价比)",
                "api_key": getattr(settings, 'DEEPSEEK_API_KEY', ''),
                "base_url": "https://api.deepseek.com/v1",
                "model": "deepseek-vl",
                "provider": "openai-compatible",
                "priority": 4,
                "cost_rating": "⭐⭐⭐⭐⭐",
                "use_case": "代码理解、复杂推理、技术文档"
            },
            "deepseek_chat": {
                "name": "DeepSeek Chat (纯文本高性价比)",
                "api_key": getattr(settings, 'DEEPSEEK_API_KEY', ''),
                "base_url": "https://api.deepseek.com/v1",
                "model": "deepseek-chat",
                "provider": "openai-compatible",
                "priority": 5,
                "cost_rating": "⭐⭐⭐⭐⭐",
                "use_case": "日常对话、文本处理、简单推理"
            },
            "ui_tars": {
                "name": "豆包 UI-TARS (UI自动化专用)",
                "api_key": getattr(settings, 'UI_TARS_API_KEY', ''),
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "model": "doubao-1-5-ui-tars-250428",
                "provider": "openai-compatible",
                "priority": 6,
                "cost_rating": "⭐⭐⭐",
                "use_case": "UI元素识别、界面操作、自动化测试"
            },
            "openai_gpt4o": {
                "name": "OpenAI GPT-4O (兼容性最好，较贵)",
                "api_key": getattr(settings, 'OPENAI_API_KEY', ''),
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o",
                "provider": "openai",
                "priority": 7,
                "cost_rating": "⭐⭐",
                "use_case": "复杂推理、创意写作、通用任务"
            },
            "gemini": {
                "name": "Google Gemini 2.0 Flash (预留)",
                "api_key": getattr(settings, 'GEMINI_API_KEY', ''),
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "model": "gemini-2.0-flash",
                "provider": "google",
                "priority": 8,
                "cost_rating": "⭐⭐⭐",
                "use_case": "多模态理解、实时交互"
            }
        }
    
    async def test_model_connectivity(self, model_id: str, config: Dict) -> Tuple[bool, str, float]:
        """测试单个模型的连接性"""
        if not config["api_key"] or config["api_key"].startswith('your-'):
            return False, "API密钥未设置", 0.0
            
        start_time = time.time()
        
        try:
            # 特殊处理不同的API格式
            if config["provider"] == "google":
                # Gemini API格式不同，暂时跳过实际测试
                return True, "Gemini API格式特殊，待配置", 0.0
            
            # 构建测试请求
            headers = {
                "Authorization": f"Bearer {config['api_key']}",
                "Content-Type": "application/json"
            }
            
            # 针对不同服务商调整请求格式
            if "dashscope.aliyuncs.com" in config["base_url"]:
                # 阿里云通义千问格式
                test_data = {
                    "model": config["model"],
                    "messages": [
                        {"role": "user", "content": "Hi"}
                    ],
                    "max_tokens": 5
                }
            elif "open.bigmodel.cn" in config["base_url"]:
                # 智谱AI格式
                test_data = {
                    "model": config["model"],
                    "messages": [
                        {"role": "user", "content": "Hi"}
                    ],
                    "max_tokens": 5
                }
            elif "api.deepseek.com" in config["base_url"]:
                # DeepSeek格式
                test_data = {
                    "model": config["model"],
                    "messages": [
                        {"role": "user", "content": "Hi"}
                    ],
                    "max_tokens": 5
                }
            elif "ark.cn-beijing.volces.com" in config["base_url"]:
                # 豆包/UI-TARS格式
                test_data = {
                    "model": config["model"],
                    "messages": [
                        {"role": "user", "content": "Hi"}
                    ],
                    "max_tokens": 5
                }
            else:
                # OpenAI标准格式
                test_data = {
                    "model": config["model"],
                    "messages": [
                        {"role": "user", "content": "Hi"}
                    ],
                    "max_tokens": 5,
                    "temperature": 0.1
                }
                
            url = f"{config['base_url']}/chat/completions"
            logger.info(f"   🔗 请求URL: {url}")
            logger.info(f"   🔑 API密钥: {config['api_key'][:10]}...")
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.post(url, headers=headers, json=test_data) as response:
                    response_time = time.time() - start_time
                    response_text = await response.text()
                    
                    logger.info(f"   📡 响应状态: {response.status}")
                    logger.info(f"   📄 响应内容: {response_text[:200]}...")
                    
                    if response.status == 200:
                        try:
                            result = json.loads(response_text)
                            return True, "连接成功", response_time
                        except json.JSONDecodeError:
                            return False, f"响应格式错误: {response_text[:100]}", response_time
                    elif response.status == 401:
                        return False, f"API密钥无效: {response_text[:100]}", response_time
                    elif response.status == 403:
                        return False, f"访问被拒绝: {response_text[:100]}", response_time
                    elif response.status == 429:
                        return False, f"请求频率限制: {response_text[:100]}", response_time
                    elif response.status == 404:
                        return False, f"端点不存在: {response_text[:100]}", response_time
                    else:
                        return False, f"HTTP {response.status}: {response_text[:100]}", response_time
                        
        except asyncio.TimeoutError:
            return False, "请求超时", time.time() - start_time
        except aiohttp.ClientError as e:
            return False, f"网络连接错误: {str(e)}", time.time() - start_time
        except Exception as e:
            return False, f"未知错误: {str(e)}", time.time() - start_time
    
    async def test_all_models(self) -> Dict:
        """测试所有模型"""
        logger.info("🚀 开始AI模型可用性测试...")
        
        results = {}
        successful_models = []
        failed_models = []
        
        for model_id, config in self.models_config.items():
            logger.info(f"📡 测试模型: {config['name']}")
            
            success, message, response_time = await self.test_model_connectivity(model_id, config)
            
            result = {
                "name": config["name"],
                "model": config["model"],
                "provider": config["provider"],
                "priority": config["priority"],
                "cost_rating": config["cost_rating"],
                "use_case": config["use_case"],
                "success": success,
                "message": message,
                "response_time": response_time,
                "api_key_configured": bool(config["api_key"] and not config["api_key"].startswith('your-'))
            }
            
            results[model_id] = result
            
            if success:
                successful_models.append(model_id)
                logger.info(f"✅ {config['name']} - 测试成功 ({response_time:.2f}s)")
            else:
                failed_models.append(model_id)
                logger.error(f"❌ {config['name']} - 测试失败: {message}")
        
        # 生成测试报告
        self.test_results = results
        self._generate_test_report(successful_models, failed_models)
        
        return results
    
    def _generate_test_report(self, successful_models: List[str], failed_models: List[str]):
        """生成测试报告"""
        logger.info("\n" + "="*80)
        logger.info("🎯 AI模型测试报告")
        logger.info("="*80)
        
        # 成功的模型
        if successful_models:
            logger.info(f"✅ 可用模型 ({len(successful_models)}个):")
            sorted_successful = sorted(
                [(mid, self.models_config[mid]) for mid in successful_models],
                key=lambda x: x[1]["priority"]
            )
            
            for model_id, config in sorted_successful:
                result = self.test_results[model_id]
                logger.info(f"  🔸 {config['name']}")
                logger.info(f"     模型: {config['model']} | 响应时间: {result['response_time']:.2f}s")
                logger.info(f"     性价比: {config['cost_rating']} | 用途: {config['use_case']}")
        
        # 失败的模型
        if failed_models:
            logger.info(f"\n❌ 不可用模型 ({len(failed_models)}个):")
            for model_id in failed_models:
                config = self.models_config[model_id]
                result = self.test_results[model_id]
                logger.info(f"  🔸 {config['name']}")
                logger.info(f"     错误: {result['message']}")
                logger.info(f"     API密钥: {'已配置' if result['api_key_configured'] else '未配置'}")
        
        # 推荐配置
        logger.info(f"\n🎯 推荐配置:")
        if successful_models:
            # 找到优先级最高的可用模型
            best_model_id = min(successful_models, key=lambda x: self.models_config[x]["priority"])
            best_config = self.models_config[best_model_id]
            logger.info(f"  主力模型: {best_config['name']}")
            logger.info(f"  原因: 优先级最高且可用，性价比: {best_config['cost_rating']}")
            
            # 找到性价比最高的模型
            high_value_models = [
                mid for mid in successful_models 
                if self.models_config[mid]["cost_rating"] == "⭐⭐⭐⭐⭐"
            ]
            if high_value_models:
                value_model_id = min(high_value_models, key=lambda x: self.models_config[x]["priority"])
                value_config = self.models_config[value_model_id]
                logger.info(f"  性价比之选: {value_config['name']}")
        else:
            logger.error("  ⚠️ 没有可用的模型，请检查API密钥配置！")
        
        logger.info("="*80)
    
    def get_best_available_model(self) -> Optional[str]:
        """获取最佳可用模型"""
        if not self.test_results:
            return None
            
        available_models = [
            (model_id, config) for model_id, config in self.test_results.items()
            if config["success"]
        ]
        
        if not available_models:
            return None
            
        # 按优先级排序，返回最高优先级的模型
        best_model_id = min(available_models, key=lambda x: self.models_config[x[0]]["priority"])[0]
        return best_model_id
    
    def get_models_by_use_case(self, use_case: str) -> List[str]:
        """根据用途获取推荐模型"""
        if not self.test_results:
            return []
            
        matching_models = []
        for model_id, result in self.test_results.items():
            if result["success"] and use_case.lower() in result["use_case"].lower():
                matching_models.append(model_id)
        
        # 按优先级排序
        return sorted(matching_models, key=lambda x: self.models_config[x]["priority"])


async def run_ai_model_tests():
    """运行AI模型测试的主函数"""
    tester = AIModelTester()
    
    logger.info("🔍 AI模型可用性测试开始...")
    results = await tester.test_all_models()
    
    # 获取推荐配置
    best_model = tester.get_best_available_model()
    if best_model:
        logger.info(f"🎯 推荐使用模型: {tester.models_config[best_model]['name']}")
    
    # 获取UI自动化推荐模型
    ui_models = tester.get_models_by_use_case("UI自动化")
    if ui_models:
        logger.info(f"🤖 UI自动化推荐: {tester.models_config[ui_models[0]]['name']}")
    
    return results


if __name__ == "__main__":
    # 直接运行测试
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    asyncio.run(run_ai_model_tests())

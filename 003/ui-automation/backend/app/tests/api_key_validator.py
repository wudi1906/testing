"""
API密钥深度验证工具
检查API密钥格式、权限、余额等详细信息
"""
import asyncio
import aiohttp
import json
import base64
from typing import Dict, Any, Tuple
from loguru import logger


class APIKeyValidator:
    """API密钥深度验证器"""
    
    def __init__(self):
        self.api_configs = {
            "qwen": {
                "api_key": "sk-741f3076d4f14ba2a9ba75fc59b38938",
                "base_url": "https://dashscope.aliyuncs.com",
                "auth_header": "Authorization",
                "auth_format": "Bearer {key}",
                "test_endpoints": [
                    "/compatible-mode/v1/chat/completions",
                    "/api/v1/services/aigc/text-generation/generation",
                    "/api/v1/services/aigc/multimodal-generation/generation"
                ],
                "test_models": ["qwen-vl-plus", "qwen-vl-max", "qwen-plus", "qwen2-vl-72b-instruct"],
                "cost_rating": 5,
                "ui_suitability": 5,
                "description": "阿里通义千问 - UI自动化最佳，中文优化，视觉理解强"
            },
            "glm": {
                "api_key": "f168fedf2fc14e0e89d50706cdbd6ace.EV4BzLp3IGMwsl1K",
                "base_url": "https://open.bigmodel.cn",
                "auth_header": "Authorization", 
                "auth_format": "Bearer {key}",
                "test_endpoints": [
                    "/api/paas/v4/chat/completions"
                ],
                "test_models": ["glm-4v", "glm-4v-plus", "glm-4-plus", "cogview-3"],
                "cost_rating": 4,
                "ui_suitability": 4,
                "description": "智谱AI GLM - 多模态能力强，国产可控"
            },
            "deepseek": {
                "api_key": "sk-ce1dd0750e824f369b4833c6ced9835a",
                "base_url": "https://api.deepseek.com",
                "auth_header": "Authorization",
                "auth_format": "Bearer {key}",
                "test_endpoints": [
                    "/v1/chat/completions"
                ],
                "test_models": ["deepseek-vl", "deepseek-chat", "deepseek-coder"],
                "cost_rating": 5,
                "ui_suitability": 3,
                "description": "DeepSeek - 代码理解强，性价比极高"
            },
            "doubao": {
                "api_key": "ee6ab9f9-a4f1-4cfe-ad04-dd64dfb67e0f",
                "base_url": "https://ark.cn-beijing.volces.com",
                "auth_header": "Authorization",
                "auth_format": "Bearer {key}",
                "test_endpoints": [
                    "/api/v3/chat/completions"
                ],
                "test_models": ["doubao-1-5-ui-tars-250428", "doubao-pro-4k", "doubao-lite-4k"],
                "cost_rating": 3,
                "ui_suitability": 5,
                "description": "豆包 UI-TARS - UI自动化专用模型"
            },
            "gemini": {
                "api_key": "AIzaSyCGiwgvSxkHoXbagTzusxZ_n9Ib6svg8Qc",
                "base_url": "https://generativelanguage.googleapis.com",
                "auth_header": "x-goog-api-key",
                "auth_format": "{key}",
                "test_endpoints": [
                    "/v1beta/models/gemini-2.0-flash-exp:generateContent",
                    "/v1beta/models/gemini-1.5-pro:generateContent"
                ],
                "test_models": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"],
                "cost_rating": 4,
                "ui_suitability": 4,
                "description": "Google Gemini - 多模态能力出色，响应快"
            },
            "openai_1": {
                "api_key": "your-openai-api-key-1-here",
                "base_url": "https://api.openai.com",
                "auth_header": "Authorization",
                "auth_format": "Bearer {key}",
                "test_endpoints": [
                    "/v1/chat/completions"
                ],
                "test_models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
                "cost_rating": 2,
                "ui_suitability": 4,
                "description": "OpenAI GPT-4O - 兼容性最好，理解能力强，但较贵"
            },
            "openai_2": {
                "api_key": "your-openai-api-key-2-here",
                "base_url": "https://api.openai.com",
                "auth_header": "Authorization",
                "auth_format": "Bearer {key}",
                "test_endpoints": [
                    "/v1/chat/completions"
                ],
                "test_models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
                "cost_rating": 2,
                "ui_suitability": 4,
                "description": "OpenAI GPT-4O (备用密钥) - 兼容性最好"
            }
        }
    
    def validate_key_format(self, service: str, api_key: str) -> Tuple[bool, str]:
        """验证API密钥格式"""
        if service == "qwen":
            if api_key.startswith("sk-") and len(api_key) > 30:
                return True, "格式正确"
            else:
                return False, "应该以sk-开头且长度大于30字符"
                
        elif service == "glm":
            if "." in api_key and len(api_key) > 40:
                return True, "格式正确"
            else:
                return False, "应该包含.分隔符且长度大于40字符"
                
        elif service == "deepseek":
            if api_key.startswith("sk-") and len(api_key) > 30:
                return True, "格式正确"
            else:
                return False, "应该以sk-开头且长度大于30字符"
                
        elif service == "doubao":
            if len(api_key) == 36 and api_key.count("-") == 4:
                return True, "格式正确（UUID格式）"
            else:
                return False, "应该是UUID格式(8-4-4-4-12)"
                
        elif service == "gemini":
            if api_key.startswith("AIza") and len(api_key) > 35:
                return True, "格式正确"
            else:
                return False, "应该以AIza开头且长度大于35字符"
                
        elif service in ["openai_1", "openai_2"]:
            if api_key.startswith("sk-proj-") or api_key.startswith("sk-"):
                return True, "格式正确"
            else:
                return False, "应该以sk-或sk-proj-开头"
                
        return True, "未知格式，跳过验证"
    
    async def test_key_permissions(self, service: str, config: Dict) -> Dict[str, Any]:
        """测试API密钥权限"""
        logger.info(f"🔑 测试 {service} API密钥权限...")
        
        api_key = config["api_key"]
        base_url = config["base_url"]
        
        # 格式验证
        format_valid, format_msg = self.validate_key_format(service, api_key)
        logger.info(f"  📝 密钥格式: {format_msg}")
        
        results = {
            "service": service,
            "key_format": {"valid": format_valid, "message": format_msg},
            "endpoints": {},
            "models": {},
            "account_info": {}
        }
        
        # 测试不同端点
        for endpoint in config["test_endpoints"]:
            endpoint_result = await self._test_endpoint(service, base_url, endpoint, api_key)
            results["endpoints"][endpoint] = endpoint_result
            logger.info(f"  📡 {endpoint}: {endpoint_result['status']}")
        
        # 测试不同模型
        for model in config["test_models"]:
            model_result = await self._test_model(service, base_url, config["test_endpoints"][0], api_key, model)
            results["models"][model] = model_result
            logger.info(f"  🤖 {model}: {model_result['status']}")
        
        # 尝试获取账户信息
        account_info = await self._get_account_info(service, base_url, api_key)
        results["account_info"] = account_info
        if account_info.get("success"):
            logger.info(f"  💰 账户信息: {account_info.get('summary', '获取成功')}")
        else:
            logger.info(f"  💰 账户信息: {account_info.get('error', '获取失败')}")
        
        return results
    
    async def _test_endpoint(self, service: str, base_url: str, endpoint: str, api_key: str) -> Dict[str, Any]:
        """测试特定端点 - 严格按照官方文档格式"""
        try:
            # 根据不同服务构建不同的请求头和数据格式
            if service == "qwen":
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "X-DashScope-SSE": "disable"
                }
                
                if "compatible-mode" in endpoint:
                    # OpenAI兼容模式
                    test_data = {
                        "model": "qwen-plus",
                        "messages": [{"role": "user", "content": "Hi"}],
                        "max_tokens": 10,
                        "temperature": 0.1
                    }
                elif "multimodal" in endpoint:
                    # 多模态生成API
                    test_data = {
                        "model": "qwen-vl-plus",
                        "input": {
                            "messages": [
                                {"role": "user", "content": [{"text": "你好"}]}
                            ]
                        },
                        "parameters": {"max_tokens": 10}
                    }
                else:
                    # 原生文本生成API
                    test_data = {
                        "model": "qwen-plus",
                        "input": {"messages": [{"role": "user", "content": "Hi"}]},
                        "parameters": {"max_tokens": 10, "temperature": 0.1}
                    }
                    
            elif service == "glm":
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                test_data = {
                    "model": "glm-4",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 10,
                    "temperature": 0.1
                }
                
            elif service == "deepseek":
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                test_data = {
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 10,
                    "temperature": 0.1
                }
                
            elif service == "doubao":
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                test_data = {
                    "model": "doubao-pro-4k",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 10,
                    "temperature": 0.1
                }
                
            elif service == "gemini":
                headers = {
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json"
                }
                # Gemini特殊格式
                test_data = {
                    "contents": [
                        {"parts": [{"text": "Hi"}]}
                    ],
                    "generationConfig": {
                        "maxOutputTokens": 10,
                        "temperature": 0.1
                    }
                }
                
            elif service in ["openai_1", "openai_2"]:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                test_data = {
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 10,
                    "temperature": 0.1
                }
            
            url = f"{base_url}{endpoint}"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
                async with session.post(url, headers=headers, json=test_data) as response:
                    response_text = await response.text()
                    
                    return {
                        "status": response.status,
                        "response": response_text[:300],
                        "success": response.status == 200,
                        "headers": dict(response.headers)
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "success": False
            }
    
    async def _test_model(self, service: str, base_url: str, endpoint: str, api_key: str, model: str) -> Dict[str, Any]:
        """测试特定模型"""
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            test_data = {
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 1
            }
            
            if service == "qwen" and "generation" in endpoint:
                test_data = {
                    "model": model,
                    "input": {"messages": [{"role": "user", "content": "Hi"}]},
                    "parameters": {"max_tokens": 1}
                }
            
            url = f"{base_url}{endpoint}"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
                async with session.post(url, headers=headers, json=test_data) as response:
                    response_text = await response.text()
                    
                    return {
                        "status": response.status,
                        "success": response.status == 200,
                        "response": response_text[:200]
                    }
                    
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "success": False
            }
    
    async def _get_account_info(self, service: str, base_url: str, api_key: str) -> Dict[str, Any]:
        """获取账户信息"""
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # 不同服务的账户信息端点
            account_endpoints = {
                "openai": "/v1/usage",
                "deepseek": "/v1/user/balance",
                # 其他服务可能没有公开的账户信息端点
            }
            
            if service not in account_endpoints:
                return {"success": False, "error": "该服务不支持账户信息查询"}
            
            url = f"{base_url}{account_endpoints[service]}"
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"success": True, "data": data, "summary": "账户有效"}
                    else:
                        response_text = await response.text()
                        return {"success": False, "error": f"HTTP {response.status}: {response_text[:100]}"}
                        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def validate_all_keys(self) -> Dict[str, Any]:
        """验证所有API密钥"""
        logger.info("🔍 开始API密钥深度验证...")
        
        results = {}
        for service, config in self.api_configs.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"🧪 验证 {service.upper()} API密钥")
            logger.info(f"🔑 密钥: {config['api_key'][:15]}...")
            
            result = await self.test_key_permissions(service, config)
            results[service] = result
        
        # 生成总结报告
        self._generate_validation_report(results)
        
        return results
    
    def _generate_validation_report(self, results: Dict[str, Any]):
        """生成验证报告"""
        logger.info(f"\n{'='*80}")
        logger.info("🎯 AI模型验证报告 - 性价比与UI适配性分析")
        logger.info(f"{'='*80}")
        
        working_services = []
        failed_services = []
        
        for service, result in results.items():
            has_working_endpoint = any(
                ep.get("success", False) for ep in result["endpoints"].values()
            )
            
            config = self.api_configs[service]
            if has_working_endpoint:
                working_services.append(service)
                cost_stars = "⭐" * config["cost_rating"]
                ui_stars = "⭐" * config["ui_suitability"]
                
                logger.info(f"✅ {service.upper()}: API密钥有效")
                logger.info(f"   📊 性价比: {cost_stars} ({config['cost_rating']}/5)")
                logger.info(f"   🎯 UI适配: {ui_stars} ({config['ui_suitability']}/5)")
                logger.info(f"   📝 说明: {config['description']}")
                
                # 显示可用模型
                working_models = [
                    model for model, model_result in result["models"].items()
                    if model_result.get("success", False)
                ]
                if working_models:
                    logger.info(f"   🤖 可用模型: {', '.join(working_models)}")
                else:
                    logger.warning(f"   ⚠️ 连接成功但所有模型都不可用")
                    
            else:
                failed_services.append(service)
                # 分析失败原因
                format_issue = not result["key_format"]["valid"]
                common_errors = []
                
                for endpoint, ep_result in result["endpoints"].items():
                    if not ep_result.get("success", False):
                        if ep_result.get("status") == 401:
                            common_errors.append("认证失败")
                        elif ep_result.get("status") == 403:
                            common_errors.append("权限不足")
                        elif ep_result.get("status") == 429:
                            common_errors.append("超出配额")
                        elif "balance" in ep_result.get("response", "").lower():
                            common_errors.append("余额不足")
                        elif ep_result.get("status") == 400:
                            common_errors.append("请求格式错误")
                
                error_summary = ", ".join(set(common_errors)) if common_errors else "未知错误"
                
                logger.error(f"❌ {service.upper()}: {error_summary}")
                logger.error(f"   📝 说明: {config['description']}")
                if format_issue:
                    logger.error(f"   🔑 格式问题: {result['key_format']['message']}")
        
        # 统计信息
        logger.info(f"\n📊 验证统计:")
        logger.info(f"   ✅ 有效服务: {len(working_services)} 个")
        logger.info(f"   ❌ 无效服务: {len(failed_services)} 个")
        logger.info(f"   📈 成功率: {len(working_services)/len(results)*100:.1f}%")
        
        # 推荐配置
        if working_services:
            logger.info(f"\n🏆 推荐使用排序 (按性价比 × UI适配性):")
            
            # 计算综合评分并排序
            scored_services = []
            for service in working_services:
                config = self.api_configs[service]
                comprehensive_score = config["cost_rating"] * config["ui_suitability"]
                scored_services.append((service, comprehensive_score, config))
            
            scored_services.sort(key=lambda x: x[1], reverse=True)
            
            for i, (service, score, config) in enumerate(scored_services[:5], 1):
                logger.info(f"   {i}. {service.upper()}: 综合评分 {score}/25")
                logger.info(f"      💰 性价比: {config['cost_rating']}/5 | 🎯 UI适配: {config['ui_suitability']}/5")
                logger.info(f"      📝 {config['description']}")
            
            # 特别推荐
            best_service = scored_services[0]
            logger.info(f"\n🥇 最佳推荐: {best_service[0].upper()}")
            logger.info(f"   理由: 综合性价比和UI适配性最高 (评分: {best_service[1]}/25)")
            
            # UI自动化专用推荐
            ui_specialized = [s for s in working_services if self.api_configs[s]["ui_suitability"] == 5]
            if ui_specialized:
                logger.info(f"\n🎯 UI自动化专用推荐: {', '.join(ui_specialized)}")
            
        else:
            logger.error(f"\n⚠️ 所有API密钥都无效！")
            logger.error(f"建议检查:")
            logger.error(f"   1. API密钥是否过期")
            logger.error(f"   2. 账户余额是否充足")
            logger.error(f"   3. API权限是否正确")
        
        logger.info(f"{'='*80}")


async def run_api_validation():
    """运行API密钥验证"""
    validator = APIKeyValidator()
    return await validator.validate_all_keys()


if __name__ == "__main__":
    asyncio.run(run_api_validation())

"""
模拟AI服务 - 用于在API密钥无效时进行功能测试
"""
import json
import random
import time
from typing import Dict, List, Any
from loguru import logger


class MockAIService:
    """模拟AI服务 - 提供基本的AI响应来测试系统功能"""
    
    @staticmethod
    def get_mock_response(messages: List[Dict], task_type: str = "general") -> Dict[str, Any]:
        """生成模拟的AI响应"""
        
        if task_type == "ui_automation":
            # UI自动化任务的模拟响应
            responses = [
                {
                    "action": "click",
                    "target": "提交按钮",
                    "reasoning": "根据页面分析，需要点击提交按钮完成表单提交",
                    "confidence": 0.95
                },
                {
                    "action": "fill",
                    "target": "姓名输入框",
                    "value": "测试用户",
                    "reasoning": "检测到姓名输入字段，自动填入测试数据",
                    "confidence": 0.88
                },
                {
                    "action": "select",
                    "target": "性别选择",
                    "value": "男",
                    "reasoning": "找到性别选择项，随机选择一个选项",
                    "confidence": 0.92
                }
            ]
            
            return {
                "id": f"mock_ui_{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "mock-ui-model",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(random.choice(responses), ensure_ascii=False)
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 50,
                    "completion_tokens": 20,
                    "total_tokens": 70
                }
            }
        
        elif task_type == "vision":
            # 视觉理解任务的模拟响应
            vision_responses = [
                "这是一个包含表单的网页，有姓名、年龄、性别等输入字段",
                "页面显示了一个问卷调查，包含多个选择题和文本输入框",
                "我看到一个登录界面，有用户名和密码输入框，以及登录按钮",
                "这是一个商品列表页面，显示了多个商品卡片和价格信息"
            ]
            
            return {
                "id": f"mock_vision_{int(time.time())}",
                "object": "chat.completion", 
                "created": int(time.time()),
                "model": "mock-vision-model",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": random.choice(vision_responses)
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 30,
                    "total_tokens": 130
                }
            }
        
        else:
            # 通用文本任务的模拟响应
            general_responses = [
                "这是一个模拟的AI响应，用于测试系统功能。",
                "模拟AI服务正常运行，可以处理基本的文本任务。",
                "系统功能测试通过，AI服务接口工作正常。",
                "连接正常，模拟AI模型可以正确响应请求。"
            ]
            
            return {
                "id": f"mock_general_{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "mock-general-model",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": random.choice(general_responses)
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 15,
                    "total_tokens": 35
                }
            }

    @staticmethod
    def is_mock_mode_enabled() -> bool:
        """检查是否启用模拟模式"""
        import os
        return os.getenv("AI_MOCK_MODE", "false").lower() == "true"
    
    @staticmethod
    def get_mock_api_key() -> str:
        """获取模拟API密钥"""
        return "mock-api-key-for-testing"


class MockMidsceneResponse:
    """模拟Midscene AI响应"""
    
    @staticmethod
    def generate_element_location(element_description: str) -> Dict[str, Any]:
        """生成模拟的元素定位响应"""
        return {
            "elements": [
                {
                    "id": f"mock_element_{hash(element_description) % 1000}",
                    "tag": "input",
                    "type": "text",
                    "rect": {
                        "x": random.randint(100, 800),
                        "y": random.randint(100, 600),
                        "width": random.randint(100, 200),
                        "height": random.randint(30, 50)
                    },
                    "text": element_description,
                    "confidence": round(random.uniform(0.8, 0.98), 2)
                }
            ],
            "success": True,
            "timestamp": int(time.time())
        }
    
    @staticmethod
    def generate_action_plan(task_description: str) -> Dict[str, Any]:
        """生成模拟的操作计划"""
        actions = [
            {"type": "click", "target": "按钮", "description": "点击提交按钮"},
            {"type": "fill", "target": "输入框", "value": "测试内容", "description": "填写表单字段"},
            {"type": "select", "target": "下拉框", "value": "选项1", "description": "选择下拉选项"},
            {"type": "wait", "duration": 1000, "description": "等待页面加载"}
        ]
        
        return {
            "plan": random.sample(actions, random.randint(1, 3)),
            "success": True,
            "confidence": round(random.uniform(0.85, 0.95), 2),
            "estimated_time": random.randint(2, 8)
        }

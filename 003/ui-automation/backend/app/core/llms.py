"""
大语言模型客户端配置
根据验证结果优化模型选择和使用：
- QWen-VL: UI自动化最佳，视觉理解、图片处理
- GLM-4V: 多模态任务，复杂场景分析  
- DeepSeek: 代码生成、文本处理，性价比极高
"""
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

from openai import AsyncOpenAI

from autogen_ext.models.openai import OpenAIChatCompletionClient
from loguru import logger

from app.core.config import settings

# 全局客户端实例
_deepseek_model_client = None
_qwenvl_model_client = None
_glm_model_client = None
_uitars_model_client = None

def get_deepseek_model_client() -> OpenAIChatCompletionClient:
    """获取DeepSeek客户端 - 专用于代码生成、文本处理 (性价比极高)"""
    global _deepseek_model_client
    if _deepseek_model_client is None:
        logger.info("💰 初始化DeepSeek客户端 - 代码生成专用")
        _deepseek_model_client = OpenAIChatCompletionClient(
            model=settings.DEEPSEEK_MODEL,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            model_info={
                "vision": False,
                "function_calling": True,
                "json_output": True,
                "structured_output": True,
                "family": "deepseek",
                "multiple_system_messages": True
            }
        )
    return _deepseek_model_client

def get_qwenvl_model_client() -> OpenAIChatCompletionClient:
    """获取QWen-VL客户端 - 最佳推荐，专用于UI自动化、图片分析"""
    global _qwenvl_model_client
    if _qwenvl_model_client is None:
        logger.info("🥇 初始化QWen-VL客户端 - UI自动化最佳选择")
        _qwenvl_model_client = OpenAIChatCompletionClient(
            model=settings.QWEN_VL_MODEL,
            api_key=settings.QWEN_VL_API_KEY,
            base_url=settings.QWEN_VL_BASE_URL,
            model_info={
                "vision": True,
                "function_calling": True,
                "json_output": True,
                "structured_output": True,
                "family": "qwen",
                "multiple_system_messages": True
            }
        )
    return _qwenvl_model_client

def get_glm_model_client() -> OpenAIChatCompletionClient:
    """获取GLM-4V客户端 - 专用于复杂多模态任务"""
    global _glm_model_client
    if _glm_model_client is None:
        logger.info("🥈 初始化GLM-4V客户端 - 多模态任务专用")
        _glm_model_client = OpenAIChatCompletionClient(
            model=settings.GLM_MODEL,
            api_key=settings.GLM_API_KEY,
            base_url=settings.GLM_BASE_URL,
            model_info={
                "vision": True,
                "function_calling": True,
                "json_output": True,
                "structured_output": True,
                "family": "glm",
                "multiple_system_messages": True
            }
        )
    return _glm_model_client

def get_uitars_model_client() -> OpenAIChatCompletionClient:
    """获取UI-TARS客户端 - 豆包UI自动化专用（当前不可用）"""
    global _uitars_model_client
    if _uitars_model_client is None:
        logger.warning("⚠️ UI-TARS客户端当前不可用，使用备用模型")
        # 使用QWen-VL作为备用
        return get_qwenvl_model_client()
    return _uitars_model_client

# 智能模型选择器
def get_optimal_model_for_task(task_type: str) -> OpenAIChatCompletionClient:
    """根据任务类型自动选择最优模型"""
    
    task_model_mapping = {
        # UI相关任务 - 使用QWen-VL (最佳)
        "ui_analysis": get_qwenvl_model_client,
        "image_analysis": get_qwenvl_model_client,
        "page_analysis": get_qwenvl_model_client,
        "element_recognition": get_qwenvl_model_client,
        "visual_testing": get_qwenvl_model_client,
        
        # 代码生成任务 - 使用DeepSeek (性价比极高)
        "code_generation": get_deepseek_model_client,
        "playwright_generation": get_deepseek_model_client,
        "yaml_generation": get_deepseek_model_client,
        "test_script": get_deepseek_model_client,
        "text_processing": get_deepseek_model_client,
        
        # 复杂多模态任务 - 使用GLM-4V (能力强)
        "complex_analysis": get_glm_model_client,
        "multimodal_reasoning": get_glm_model_client,
        "business_analysis": get_glm_model_client,
        
        # 默认选择
        "default": get_qwenvl_model_client
    }
    
    selected_model_fn = task_model_mapping.get(task_type, task_model_mapping["default"])
    model_name = {
        get_qwenvl_model_client: "QWen-VL(最佳)",
        get_deepseek_model_client: "DeepSeek(高性价比)", 
        get_glm_model_client: "GLM-4V(能力强)"
    }.get(selected_model_fn, "未知模型")
    
    logger.info(f"🎯 任务类型: {task_type} -> 选择模型: {model_name}")
    return selected_model_fn()

# 向后兼容的模型获取函数
def get_model_client(model_type: str = "auto") -> OpenAIChatCompletionClient:
    """获取模型客户端 - 支持自动选择和手动指定"""
    
    if model_type == "auto":
        return get_qwenvl_model_client()  # 默认使用最佳模型
    elif model_type == "qwen" or model_type == "qwenvl":
        return get_qwenvl_model_client()
    elif model_type == "deepseek":
        return get_deepseek_model_client()
    elif model_type == "glm":
        return get_glm_model_client()
    elif model_type == "uitars":
        return get_uitars_model_client()
    else:
        logger.warning(f"⚠️ 未知模型类型: {model_type}，使用默认QWen-VL")
        return get_qwenvl_model_client()
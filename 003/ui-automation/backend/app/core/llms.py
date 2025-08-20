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
    """获取UI-TARS客户端 - 豆包UI自动化专用"""
    global _uitars_model_client
    if _uitars_model_client is None:
        try:
            logger.info("🎯 初始化UI-TARS客户端 - 豆包UI自动化专用")
            _uitars_model_client = OpenAIChatCompletionClient(
                model=settings.UI_TARS_MODEL,
                api_key=settings.UI_TARS_API_KEY,
                base_url=settings.UI_TARS_BASE_URL,
                model_info={
                    "vision": True,
                    "function_calling": True,
                    "json_output": True,
                    "structured_output": True,
                    "family": "doubao",
                    "multiple_system_messages": True
                }
            )
            logger.info("✅ UI-TARS客户端初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ UI-TARS客户端初始化失败: {str(e)}，使用QWen-VL备用")
            return get_qwenvl_model_client()
    return _uitars_model_client

# 智能模型选择器
def get_optimal_model_for_task(task_type: str) -> OpenAIChatCompletionClient:
    """根据任务类型自动选择最优模型（带密钥可用性回退）。

    策略：
    - playwright_generation / code_generation: DeepSeek > QWen-VL > GLM
    - ui/image/page 相关: QWen-VL > GLM > DeepSeek
    - complex/multimodal: GLM > QWen-VL > DeepSeek
    - 默认: QWen-VL > GLM > DeepSeek
    """

    status = get_model_config_status()

    def available(name: str) -> bool:
        return bool({
            'qwen_vl': status.get('qwen_vl') or status.get('qwen'),
            'glm': status.get('glm'),
            'deepseek': status.get('deepseek')
        }.get(name, False))

    order_map = {
        'playwright_generation': ['deepseek', 'qwen_vl', 'glm'],
        'code_generation': ['deepseek', 'qwen_vl', 'glm'],
        'ui_analysis': ['qwen_vl', 'glm', 'deepseek'],
        'image_analysis': ['qwen_vl', 'glm', 'deepseek'],
        'page_analysis': ['qwen_vl', 'glm', 'deepseek'],
        'element_recognition': ['qwen_vl', 'glm', 'deepseek'],
        'visual_testing': ['qwen_vl', 'glm', 'deepseek'],
        'complex_analysis': ['glm', 'qwen_vl', 'deepseek'],
        'multimodal_reasoning': ['glm', 'qwen_vl', 'deepseek'],
        'business_analysis': ['glm', 'qwen_vl', 'deepseek'],
        'default': ['qwen_vl', 'glm', 'deepseek']
    }

    for name in order_map.get(task_type, order_map['default']):
        if name == 'deepseek' and available('deepseek'):
            logger.info(f"🎯 任务类型: {task_type} -> 选择模型: DeepSeek(高性价比)")
            return get_deepseek_model_client()
        if name == 'qwen_vl' and available('qwen_vl'):
            logger.info(f"🎯 任务类型: {task_type} -> 选择模型: QWen-VL(最佳)")
            return get_qwenvl_model_client()
        if name == 'glm' and available('glm'):
            logger.info(f"🎯 任务类型: {task_type} -> 选择模型: GLM-4V(能力强)")
            return get_glm_model_client()

    # 若均不可用，抛错以便前端提示配置密钥
    raise RuntimeError("未检测到可用的AI模型密钥，请在后端环境变量中配置至少一个有效密钥（QWEN_VL_API_KEY/GLM_API_KEY/DEEPSEEK_API_KEY）。")

# 模型配置状态检查函数
def get_model_config_status() -> Dict[str, bool]:
    """获取所有AI模型的配置状态"""
    return {
        "qwen_vl": bool(settings.QWEN_VL_API_KEY and settings.QWEN_VL_API_KEY.strip() and not settings.QWEN_VL_API_KEY.startswith('your-')),
        "qwen": bool(settings.QWEN_API_KEY and settings.QWEN_API_KEY.strip() and not settings.QWEN_API_KEY.startswith('your-')),
        "glm": bool(settings.GLM_API_KEY and settings.GLM_API_KEY.strip() and not settings.GLM_API_KEY.startswith('your-')),
        "deepseek": bool(settings.DEEPSEEK_API_KEY and settings.DEEPSEEK_API_KEY.strip() and not settings.DEEPSEEK_API_KEY.startswith('your-')),
        "uitars": bool(settings.UI_TARS_API_KEY and settings.UI_TARS_API_KEY.strip() and not settings.UI_TARS_API_KEY.startswith('your-')),
        "openai": bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip() and not settings.OPENAI_API_KEY.startswith('your-')),
        "gemini": bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip() and not settings.GEMINI_API_KEY.startswith('your-'))
    }

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
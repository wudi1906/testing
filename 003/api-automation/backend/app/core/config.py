"""
核心配置文件
包含AI模型、API自动化、Marker PDF等核心配置
"""
import os
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 基础配置
    APP_NAME: str = "API自动化测试系统"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # AI模型配置
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL: Optional[str] = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    # 默认模型配置
    DEFAULT_MODEL: str = "deepseek"
    
    # API自动化配置
    API_AUTOMATION_ENABLED: bool = True
    MAX_CONCURRENT_TESTS: int = 5
    TEST_TIMEOUT: int = 300  # 5分钟
    
    # 文件上传配置
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "uploads"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # Marker PDF 服务配置
    MARKER_OUTPUT_FORMAT: str = "markdown"
    MARKER_OUTPUT_DIR: str = "output"
    MARKER_USE_LLM: bool = True
    MARKER_DISABLE_IMAGE_EXTRACTION: bool = True

    # Marker LLM 服务配置
    MARKER_LLM_SERVICE: str = "marker.services.openai.OpenAIService"

    # Marker OpenAI 兼容配置（默认使用阿里云通义千问）
    MARKER_OPENAI_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    MARKER_OPENAI_MODEL: str = "qwen-vl-max-latest"
    MARKER_OPENAI_API_KEY: Optional[str] = None

    # Marker Ollama 配置（备用）
    MARKER_OLLAMA_BASE_URL: str = "http://localhost:11434"
    MARKER_OLLAMA_MODEL: str = "llama3.2-vision"

    # Marker 处理器配置
    MARKER_ENABLE_IMAGE_DESCRIPTION: bool = True
    MARKER_ENABLE_META_PROCESSING: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # 忽略额外的环境变量


# 全局配置实例
settings = Settings()


def get_marker_config() -> Dict[str, Any]:
    """
    获取 Marker 配置字典

    Returns:
        Dict[str, Any]: 配置字典
    """
    # 从环境变量获取 API Key，支持多种环境变量名
    api_key = (
        settings.MARKER_OPENAI_API_KEY or
        os.getenv("MARKER_OPENAI_API_KEY") or
        os.getenv("OPENAI_API_KEY") or
        os.getenv("DASHSCOPE_API_KEY") or
        ""
    )

    return {
        "output_format": settings.MARKER_OUTPUT_FORMAT,
        "output_dir": settings.MARKER_OUTPUT_DIR,
        "use_llm": settings.MARKER_USE_LLM,
        "disable_image_extraction": settings.MARKER_DISABLE_IMAGE_EXTRACTION,
        "llm_service": settings.MARKER_LLM_SERVICE,
        "openai_base_url": settings.MARKER_OPENAI_BASE_URL,
        "openai_model": settings.MARKER_OPENAI_MODEL,
        "openai_api_key": api_key,
        "ollama_base_url": settings.MARKER_OLLAMA_BASE_URL,
        "ollama_model": settings.MARKER_OLLAMA_MODEL,
    }


def get_marker_ollama_config() -> Dict[str, Any]:
    """
    获取 Marker Ollama 配置

    Returns:
        Dict[str, Any]: Ollama 配置字典
    """
    return {
        "output_format": settings.MARKER_OUTPUT_FORMAT,
        "output_dir": settings.MARKER_OUTPUT_DIR,
        "use_llm": settings.MARKER_USE_LLM,
        "disable_image_extraction": settings.MARKER_DISABLE_IMAGE_EXTRACTION,
        "llm_service": "marker.services.ollama.OllamaService",
        "ollama_base_url": settings.MARKER_OLLAMA_BASE_URL,
        "ollama_model": settings.MARKER_OLLAMA_MODEL,
    }


def get_marker_no_llm_config() -> Dict[str, Any]:
    """
    获取不使用 LLM 的 Marker 配置（仅基础文本提取）

    Returns:
        Dict[str, Any]: 无 LLM 配置字典
    """
    return {
        "output_format": settings.MARKER_OUTPUT_FORMAT,
        "output_dir": settings.MARKER_OUTPUT_DIR,
        "use_llm": False,
        "disable_image_extraction": True,
    }

"""
核心配置文件
包含AI模型、API自动化等核心配置
"""
import os
from typing import Optional
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
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()

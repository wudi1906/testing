"""
应用配置管理模块

提供统一的配置管理，支持环境变量和配置文件
"""
import os
from typing import Optional, List, Dict
try:
    from pydantic_settings import BaseSettings
    from pydantic import validator
except ImportError:
    from pydantic import BaseSettings, validator
from functools import lru_cache


class ApplicationSettings(BaseSettings):
    """应用基础配置"""

    # 应用信息
    APP_NAME: str = "UI自动化测试系统"
    APP_VERSION: str = "2.0.0"
    APP_DESCRIPTION: str = "基于多模态大模型与多智能体协作的自动化测试系统"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True

    # 安全配置
    SECRET_KEY: str = "your-secret-key-here-please-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    ALGORITHM: str = "HS256"

    # CORS配置
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"

    @property
    def cors_origins_list(self) -> List[str]:
        """获取CORS源列表"""
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]
        return self.BACKEND_CORS_ORIGINS

class DatabaseSettings(BaseSettings):
    """数据库配置"""

    # 主数据库URL（优先使用）
    DATABASE_URL: Optional[str] = None

    # MySQL数据库配置（作为备选）
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "mysql"
    MYSQL_DATABASE: str = "automation_db"

    # 数据库连接池配置
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600

    @property
    def database_url(self) -> str:
        """获取数据库连接URL - 优先使用DATABASE_URL环境变量"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # 如果没有DATABASE_URL，则使用MySQL配置构建
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    @property
    def mysql_database_url(self) -> str:
        """获取MySQL数据库连接URL（兼容性保留）"""
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    # Neo4j图数据库配置
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # Milvus向量数据库配置
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION_NAME: str = "ui_automation_vectors"

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    @property
    def redis_url(self) -> str:
        """获取Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

class AIModelSettings(BaseSettings):
    """AI模型配置"""

    # DeepSeek配置
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Qwen-VL配置 (阿里通义千问视觉版)
    QWEN_API_KEY: str = ""  # 兼容性配置
    QWEN_VL_API_KEY: str = ""
    QWEN_VL_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_VL_MODEL: str = "qwen-vl-plus"  # 更新为推荐模型

    # 智谱AI GLM-4V配置
    GLM_API_KEY: str = ""
    GLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    GLM_MODEL: str = "glm-4v"

    # UI-TARS配置 (豆包UI自动化专用)
    UI_TARS_API_KEY: str = ""
    UI_TARS_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    UI_TARS_MODEL: str = "doubao-1-5-ui-tars-250428"
    UI_TARS_ENDPOINT_URL: str = ""

    # OpenAI配置（备用）
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"

    # Gemini 配置（预留）
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # 自动选择最佳可用API密钥
    @property
    def get_best_available_api(self) -> Dict[str, str]:
        """返回最佳可用的API配置"""
        apis = [
            ("qwen", self.QWEN_VL_API_KEY or self.QWEN_API_KEY, self.QWEN_VL_BASE_URL, self.QWEN_VL_MODEL),
            ("glm", self.GLM_API_KEY, self.GLM_BASE_URL, self.GLM_MODEL),
            ("uitars", self.UI_TARS_API_KEY, self.UI_TARS_BASE_URL, self.UI_TARS_MODEL),
            ("deepseek", self.DEEPSEEK_API_KEY, self.DEEPSEEK_BASE_URL, self.DEEPSEEK_MODEL),
            ("openai", self.OPENAI_API_KEY, self.OPENAI_BASE_URL, self.OPENAI_MODEL),
        ]
        
        for name, key, base_url, model in apis:
            if key and key.strip():
                return {
                    "provider": name,
                    "api_key": key,
                    "base_url": base_url,
                    "model": model
                }
        
        return {"provider": "none", "api_key": "", "base_url": "", "model": ""}

    # 多模态模型优先级配置
    @property
    def multimodal_model_priority(self) -> Dict[str, List[str]]:
        """获取多模态模型优先级配置"""
        return {
            "gui_tasks": ["uitars", "qwen_vl", "deepseek"],
            "general_vision": ["qwen_vl", "uitars", "deepseek"],
            "text_tasks": ["deepseek", "qwen_vl", "uitars"]
        }

    # 默认多模态模型选择策略
    DEFAULT_MULTIMODAL_MODEL: str = "uitars"
class FileStorageSettings(BaseSettings):
    """文件存储配置"""

    # 基础存储配置
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: str = ".pdf,.doc,.docx,.txt,.md,.yaml,.yml"
    ALLOWED_IMAGE_EXTENSIONS: str = ".png,.jpg,.jpeg,.gif,.bmp,.webp"

    @property
    def allowed_extensions_list(self) -> List[str]:
        """获取允许的文件扩展名列表"""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def allowed_image_extensions_list(self) -> List[str]:
        """获取允许的图片扩展名列表"""
        return [ext.strip() for ext in self.ALLOWED_IMAGE_EXTENSIONS.split(",")]

    # 专用目录配置
    IMAGE_UPLOAD_DIR: str = "uploads/images"
    YAML_OUTPUT_DIR: str = "uploads/yaml"
    PLAYWRIGHT_OUTPUT_DIR: str = "uploads/playwright"

    # 文件系统脚本存储目录（独立于执行工作空间）
    FILESYSTEM_SCRIPTS_DIR: str = "filesystem_scripts"

    MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 10MB


class AutomationSettings(BaseSettings):
    """自动化工具配置"""

    # MidScene.js配置
    MIDSCENE_SERVICE_URL: str = "http://localhost:3002"
    MIDSCENE_TIMEOUT: int = 300  # 5分钟
    MIDSCENE_SCRIPT_PATH: str = r"E:\Program Files\cursorproject\testing\003\ui-automation\examples\midscene-playwright"

    # Playwright配置
    PLAYWRIGHT_HEADLESS: bool = True
    PLAYWRIGHT_TIMEOUT: int = 30000  # 30秒
    PLAYWRIGHT_VIEWPORT_WIDTH: int = 1280
    PLAYWRIGHT_VIEWPORT_HEIGHT: int = 960

    # AutoGen配置
    AUTOGEN_CACHE_ENABLED: bool = True
    AUTOGEN_MAX_ROUND: int = 10
    AUTOGEN_TIMEOUT: int = 600  # 10分钟
class LoggingSettings(BaseSettings):
    """日志配置"""

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "30 days"


class MonitoringSettings(BaseSettings):
    """监控配置"""

    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 8001
    ENABLE_MONITORING: bool = True


class FeatureSettings(BaseSettings):
    """功能开关配置"""

    ENABLE_CACHING: bool = True
    ENABLE_RATE_LIMITING: bool = True
    ENABLE_ASYNC_PROCESSING: bool = True

    # 混合检索配置
    HYBRID_RETRIEVAL_ENABLED: bool = True
    VECTOR_SEARCH_TOP_K: int = 10
    SIMILARITY_THRESHOLD: float = 0.7


class Settings(
    ApplicationSettings,
    DatabaseSettings,
    AIModelSettings,
    FileStorageSettings,
    AutomationSettings,
    LoggingSettings,
    MonitoringSettings,
    FeatureSettings
):
    """统一配置类 - 继承所有配置模块"""

    class Config:
        env_file = ".env"
        case_sensitive = True
        # 允许忽略未在模型中声明的额外环境变量，避免用户自定义变量导致启动失败
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例（单例模式）"""
    return Settings()


# 全局配置实例
settings = get_settings()

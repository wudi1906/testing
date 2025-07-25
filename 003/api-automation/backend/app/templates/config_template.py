"""
测试配置模板
提供测试执行的配置信息
"""
import os
from typing import Dict, Any, Optional


class Config:
    """测试配置类"""
    
    # 基础配置
    BASE_URL = os.getenv("API_BASE_URL", "{base_url}")
    ENVIRONMENT = os.getenv("TEST_ENVIRONMENT", "{environment}")
    
    # 认证配置
    USERNAME = os.getenv("TEST_USERNAME", "{username}")
    PASSWORD = os.getenv("TEST_PASSWORD", "{password}")
    API_KEY = os.getenv("API_KEY", "{api_key}")
    TOKEN = os.getenv("AUTH_TOKEN", "{auth_token}")
    
    # 超时配置
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "{request_timeout}"))
    CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "{connection_timeout}"))
    
    # 重试配置
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "{max_retries}"))
    RETRY_DELAY = float(os.getenv("RETRY_DELAY", "{retry_delay}"))
    
    # 并发配置
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "{max_workers}"))
    PARALLEL_EXECUTION = os.getenv("PARALLEL_EXECUTION", "{parallel_execution}").lower() == "true"
    
    # 报告配置
    REPORT_DIR = os.getenv("REPORT_DIR", "{report_dir}")
    ALLURE_RESULTS_DIR = os.getenv("ALLURE_RESULTS_DIR", "{allure_results_dir}")
    ALLURE_REPORT_DIR = os.getenv("ALLURE_REPORT_DIR", "{allure_report_dir}")
    
    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "{log_level}")
    LOG_FILE = os.getenv("LOG_FILE", "{log_file}")
    
    # 数据库配置（如果需要）
    DATABASE_URL = os.getenv("DATABASE_URL", "{database_url}")
    
    # 邮件配置（用于测试报告发送）
    SMTP_SERVER = os.getenv("SMTP_SERVER", "{smtp_server}")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "{smtp_port}"))
    EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "{email_username}")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "{email_password}")
    
    # 默认请求头
    DEFAULT_HEADERS = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "API-Test-Agent/1.0"
    }
    
    # 环境特定配置
    ENVIRONMENT_CONFIGS = {
        "development": {
            "base_url": "http://localhost:8000",
            "debug": True,
            "verify_ssl": False,
            "log_level": "DEBUG"
        },
        "testing": {
            "base_url": "http://test-api.example.com",
            "debug": True,
            "verify_ssl": False,
            "log_level": "INFO"
        },
        "staging": {
            "base_url": "http://staging-api.example.com",
            "debug": False,
            "verify_ssl": True,
            "log_level": "WARNING"
        },
        "production": {
            "base_url": "http://api.example.com",
            "debug": False,
            "verify_ssl": True,
            "log_level": "ERROR"
        }
    }
    
    @classmethod
    def get_environment_config(cls, environment: Optional[str] = None) -> Dict[str, Any]:
        """获取环境特定配置"""
        env = environment or cls.ENVIRONMENT
        return cls.ENVIRONMENT_CONFIGS.get(env, cls.ENVIRONMENT_CONFIGS["development"])
    
    @classmethod
    def get_base_url(cls, environment: Optional[str] = None) -> str:
        """获取基础URL"""
        env_config = cls.get_environment_config(environment)
        return env_config.get("base_url", cls.BASE_URL)
    
    @classmethod
    def is_debug_mode(cls, environment: Optional[str] = None) -> bool:
        """是否为调试模式"""
        env_config = cls.get_environment_config(environment)
        return env_config.get("debug", False)
    
    @classmethod
    def should_verify_ssl(cls, environment: Optional[str] = None) -> bool:
        """是否验证SSL证书"""
        env_config = cls.get_environment_config(environment)
        return env_config.get("verify_ssl", True)
    
    @classmethod
    def get_log_level(cls, environment: Optional[str] = None) -> str:
        """获取日志级别"""
        env_config = cls.get_environment_config(environment)
        return env_config.get("log_level", cls.LOG_LEVEL)
    
    @classmethod
    def get_auth_headers(cls) -> Dict[str, str]:
        """获取认证头"""
        headers = cls.DEFAULT_HEADERS.copy()
        
        if cls.API_KEY:
            headers["X-API-Key"] = cls.API_KEY
        elif cls.TOKEN:
            headers["Authorization"] = f"Bearer {cls.TOKEN}"
        
        return headers
    
    @classmethod
    def get_request_config(cls) -> Dict[str, Any]:
        """获取请求配置"""
        return {
            "timeout": cls.REQUEST_TIMEOUT,
            "verify": cls.should_verify_ssl(),
            "headers": cls.get_auth_headers()
        }
    
    # 测试数据配置
    TEST_DATA_CONFIG = {
        "user": {
            "valid_username_length": (3, 50),
            "valid_email_domains": ["example.com", "test.org", "demo.net"],
            "valid_age_range": (18, 100),
            "valid_phone_pattern": r"^1[3-9]\d{9}$"
        },
        "product": {
            "valid_price_range": (0.01, 999999.99),
            "valid_name_length": (1, 255),
            "valid_categories": ["electronics", "clothing", "books", "home", "sports"],
            "valid_stock_range": (0, 999999)
        },
        "order": {
            "valid_quantity_range": (1, 100),
            "valid_item_count": (1, 50),
            "valid_payment_methods": ["credit_card", "paypal", "bank_transfer", "alipay", "wechat_pay"]
        }
    }
    
    # 性能测试配置
    PERFORMANCE_CONFIG = {
        "load_test": {
            "concurrent_users": 10,
            "test_duration": 60,  # 秒
            "ramp_up_time": 10,   # 秒
            "think_time": 1       # 秒
        },
        "stress_test": {
            "concurrent_users": 100,
            "test_duration": 300,  # 秒
            "ramp_up_time": 30,    # 秒
            "think_time": 0.5      # 秒
        },
        "spike_test": {
            "concurrent_users": 500,
            "test_duration": 120,  # 秒
            "ramp_up_time": 5,     # 秒
            "think_time": 0        # 秒
        }
    }
    
    # 断言配置
    ASSERTION_CONFIG = {
        "response_time": {
            "fast": 1.0,      # 1秒
            "normal": 3.0,    # 3秒
            "slow": 10.0      # 10秒
        },
        "status_codes": {
            "success": [200, 201, 202, 204],
            "client_error": [400, 401, 403, 404, 422],
            "server_error": [500, 502, 503, 504]
        },
        "content_types": {
            "json": "application/json",
            "xml": "application/xml",
            "html": "text/html",
            "text": "text/plain"
        }
    }
    
    # 数据清理配置
    CLEANUP_CONFIG = {
        "enabled": True,
        "cleanup_after_test": True,
        "cleanup_after_suite": True,
        "preserve_on_failure": True,
        "cleanup_timeout": 30  # 秒
    }
    
    # 监控配置
    MONITORING_CONFIG = {
        "enabled": True,
        "metrics_collection": True,
        "performance_monitoring": True,
        "error_tracking": True,
        "alert_thresholds": {
            "error_rate": 0.05,      # 5%
            "response_time_p95": 5.0, # 5秒
            "success_rate": 0.95      # 95%
        }
    }
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """验证配置"""
        errors = []
        warnings = []
        
        # 检查必需配置
        if not cls.BASE_URL:
            errors.append("BASE_URL is required")
        
        if not cls.ENVIRONMENT:
            warnings.append("ENVIRONMENT not set, using default")
        
        # 检查超时配置
        if cls.REQUEST_TIMEOUT <= 0:
            errors.append("REQUEST_TIMEOUT must be positive")
        
        if cls.CONNECTION_TIMEOUT <= 0:
            errors.append("CONNECTION_TIMEOUT must be positive")
        
        # 检查重试配置
        if cls.MAX_RETRIES < 0:
            errors.append("MAX_RETRIES must be non-negative")
        
        if cls.RETRY_DELAY < 0:
            errors.append("RETRY_DELAY must be non-negative")
        
        # 检查并发配置
        if cls.MAX_WORKERS <= 0:
            errors.append("MAX_WORKERS must be positive")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    @classmethod
    def get_config_summary(cls) -> Dict[str, Any]:
        """获取配置摘要"""
        return {
            "environment": cls.ENVIRONMENT,
            "base_url": cls.BASE_URL,
            "timeout": cls.REQUEST_TIMEOUT,
            "max_retries": cls.MAX_RETRIES,
            "parallel_execution": cls.PARALLEL_EXECUTION,
            "max_workers": cls.MAX_WORKERS,
            "debug_mode": cls.is_debug_mode(),
            "ssl_verification": cls.should_verify_ssl(),
            "log_level": cls.LOG_LEVEL
        }


# 环境变量模板
ENV_TEMPLATE = """
# API测试环境配置

# 基础配置
API_BASE_URL={base_url}
TEST_ENVIRONMENT={environment}

# 认证配置
TEST_USERNAME={username}
TEST_PASSWORD={password}
API_KEY={api_key}
AUTH_TOKEN={auth_token}

# 超时配置
REQUEST_TIMEOUT={request_timeout}
CONNECTION_TIMEOUT={connection_timeout}

# 重试配置
MAX_RETRIES={max_retries}
RETRY_DELAY={retry_delay}

# 并发配置
MAX_WORKERS={max_workers}
PARALLEL_EXECUTION={parallel_execution}

# 报告配置
REPORT_DIR={report_dir}
ALLURE_RESULTS_DIR={allure_results_dir}
ALLURE_REPORT_DIR={allure_report_dir}

# 日志配置
LOG_LEVEL={log_level}
LOG_FILE={log_file}

# 数据库配置
DATABASE_URL={database_url}

# 邮件配置
SMTP_SERVER={smtp_server}
SMTP_PORT={smtp_port}
EMAIL_USERNAME={email_username}
EMAIL_PASSWORD={email_password}
"""

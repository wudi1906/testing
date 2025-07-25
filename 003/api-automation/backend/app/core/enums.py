"""
枚举定义
定义接口自动化系统中使用的枚举类型
"""
from enum import Enum


class SessionStatus(Enum):
    """会话状态"""
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InputSource(Enum):
    """输入源类型"""
    API_DOC = "api_doc"
    SWAGGER = "swagger"
    OPENAPI = "openapi"
    POSTMAN = "postman"
    MANUAL = "manual"


class TestLevel(Enum):
    """测试级别"""
    UNIT = "unit"
    INTEGRATION = "integration"
    SYSTEM = "system"
    ACCEPTANCE = "acceptance"


class TestType(Enum):
    """测试类型"""
    FUNCTIONAL = "functional"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    SMOKE = "smoke"
    REGRESSION = "regression"


class Priority(Enum):
    """优先级"""
    P0 = "P0"  # 最高优先级
    P1 = "P1"  # 高优先级
    P2 = "P2"  # 中优先级
    P3 = "P3"  # 低优先级


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class HttpMethod(Enum):
    """HTTP方法"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthType(Enum):
    """认证类型"""
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    JWT = "jwt"


class ContentType(Enum):
    """内容类型"""
    JSON = "application/json"
    XML = "application/xml"
    FORM_DATA = "multipart/form-data"
    URL_ENCODED = "application/x-www-form-urlencoded"
    TEXT = "text/plain"


class ResponseFormat(Enum):
    """响应格式"""
    JSON = "json"
    XML = "xml"
    HTML = "html"
    TEXT = "text"
    BINARY = "binary"


class TestDataType(Enum):
    """测试数据类型"""
    VALID = "valid"
    INVALID = "invalid"
    BOUNDARY = "boundary"
    NULL = "null"
    EMPTY = "empty"
    SPECIAL_CHARS = "special_chars"


class AssertionType(Enum):
    """断言类型"""
    STATUS_CODE = "status_code"
    RESPONSE_TIME = "response_time"
    RESPONSE_BODY = "response_body"
    RESPONSE_HEADERS = "response_headers"
    JSON_SCHEMA = "json_schema"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"


class DependencyType(Enum):
    """依赖类型"""
    DATA_DEPENDENCY = "data_dependency"
    EXECUTION_ORDER = "execution_order"
    AUTHENTICATION = "authentication"
    ENVIRONMENT = "environment"
    PREREQUISITE = "prerequisite"


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ReportFormat(Enum):
    """报告格式"""
    ALLURE = "allure"
    HTML = "html"
    JSON = "json"
    XML = "xml"
    PDF = "pdf"


class EnvironmentType(Enum):
    """环境类型"""
    DEV = "dev"
    TEST = "test"
    STAGING = "staging"
    PROD = "prod"
    LOCAL = "local"

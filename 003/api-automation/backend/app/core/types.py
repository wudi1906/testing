"""
核心类型定义
定义系统中使用的枚举类型和常量
"""
from enum import Enum
from typing import Dict


class AgentTypes(Enum):
    """智能体类型枚举"""
    # 接口自动化智能体
    API_DOC_PARSER = "api_doc_parser"
    API_ANALYZER = "api_analyzer"
    API_DATA_PERSISTENCE = "api_data_persistence"  # 新增数据持久化智能体
    API_TEST_CASE_GENERATOR = "api_test_case_generator"  # 新增测试用例生成智能体
    TEST_SCRIPT_GENERATOR = "test_script_generator"
    TEST_EXECUTOR = "test_executor"
    LOG_RECORDER = "log_recorder"


class AgentPlatform(Enum):
    """智能体平台类型"""
    API_AUTOMATION = "api_automation"


class MessageRegion(Enum):
    """消息区域类型"""
    PROCESS = "process"
    INFO = "info"
    ERROR = "error"
    SUCCESS = "success"
    WARNING = "warning"


class TopicTypes(Enum):
    """主题类型枚举"""
    # 接口自动化相关主题
    API_DOC_PARSER = "api_doc_parser"
    API_ANALYZER = "api_analyzer"  # 修正为与工厂一致的名称
    API_DATA_PERSISTENCE = "api_data_persistence"  # 新增数据持久化主题
    API_TEST_CASE_GENERATOR = "api_test_case_generator"  # 新增测试用例生成主题
    TEST_SCRIPT_GENERATOR = "test_script_generator"
    TEST_EXECUTOR = "test_executor"
    LOG_RECORDER = "log_recorder"

    # 系统主题
    STREAM_OUTPUT = "stream_output"


class TestFramework(Enum):
    """测试框架类型"""
    PYTEST = "pytest"
    UNITTEST = "unittest"
    REQUESTS = "requests"


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


class ApiDocFormat(Enum):
    """API文档格式"""
    SWAGGER = "swagger"
    OPENAPI = "openapi"
    POSTMAN = "postman"
    APIDOC = "apidoc"
    MARKDOWN = "markdown"


# 智能体名称映射
AGENT_NAMES: Dict[str, str] = {
    # 接口自动化智能体
    AgentTypes.API_DOC_PARSER.value: "API文档解析智能体",
    AgentTypes.API_ANALYZER.value: "接口分析智能体",
    AgentTypes.API_DATA_PERSISTENCE.value: "API数据持久化智能体",
    AgentTypes.API_TEST_CASE_GENERATOR.value: "API测试用例生成智能体",
    AgentTypes.TEST_SCRIPT_GENERATOR.value: "测试脚本生成智能体",
    AgentTypes.TEST_EXECUTOR.value: "测试执行智能体",
    AgentTypes.LOG_RECORDER.value: "日志记录智能体",
}


# 测试框架配置
TEST_FRAMEWORK_CONFIG = {
    TestFramework.PYTEST.value: {
        "command": "pytest",
        "report_format": "allure",
        "plugins": ["allure-pytest", "pytest-html", "pytest-json-report"],
        "markers": ["api", "smoke", "regression", "integration"]
    },
    TestFramework.UNITTEST.value: {
        "command": "python -m unittest",
        "report_format": "xml",
        "plugins": [],
        "markers": []
    }
}


# API文档解析配置
API_DOC_PARSER_CONFIG = {
    "supported_formats": [
        ApiDocFormat.SWAGGER.value,
        ApiDocFormat.OPENAPI.value,
        ApiDocFormat.POSTMAN.value,
        ApiDocFormat.MARKDOWN.value
    ],
    "max_file_size": 50 * 1024 * 1024,  # 50MB
    "timeout": 300,  # 5分钟
}


# 测试执行配置
TEST_EXECUTION_CONFIG = {
    "max_parallel_tests": 5,
    "timeout_per_test": 60,  # 60秒
    "retry_count": 3,
    "report_formats": ["allure", "html", "json"],
    "log_level": "INFO"
}

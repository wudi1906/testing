"""
UI自动化测试系统 - 枚举类型定义
统一管理所有枚举类型，避免重复定义
"""
from enum import Enum


class AgentPlatform(Enum):
    """智能体平台类型"""
    WEB = "web"
    ANDROID = "android"
    API = "api"
    COMMON = "common"


class AgentTypes(Enum):
    # 图片分析智能体
    UI_EXPERT = "ui_expert"
    INTERACTION_ANALYST = "interaction_analyst"
    QUALITY_REVIEWER = "quality_reviewer"
    MIDSCENE_EXPERT = "midscene_expert"

    """智能体类型枚举"""
    # 分析类智能体
    MULTIMODAL_ANALYZER = "multimodal_analyzer"      # 多模态分析智能体（图片/URL分析）
    WEB_SCRAPER = "web_scraper"                      # 网页抓取智能体（Crawl4AI）
    API_ANALYZER = "api_analyzer"                    # API接口分析智能体
    IMAGE_ANALYZER = "image_analyzer"                # 图片分析智能体

    # 生成类智能体
    TEST_PLANNER = "test_planner"                    # 测试规划智能体
    YAML_GENERATOR = "yaml_generator"                # YAML生成智能体（MidScene.js）
    PLAYWRIGHT_GENERATOR = "playwright_generator"    # Playwright代码生成智能体
    API_TEST_GENERATOR = "api_test_generator"        # API测试生成智能体
    ACTION_GENERATOR = "action_generator"            # 动作生成智能体（保持兼容性）

    # 执行类智能体
    YAML_EXECUTOR = "yaml_executor"                  # YAML脚本执行智能体
    PLAYWRIGHT_EXECUTOR = "playwright_executor"      # Playwright执行智能体
    API_TEST_EXECUTOR = "api_test_executor"          # API测试执行智能体

    # 管理类智能体
    RESULT_ANALYZER = "result_analyzer"              # 结果分析智能体
    REPORT_GENERATOR = "report_generator"            # 报告生成智能体
    SCRIPT_MANAGER = "script_manager"                # 脚本管理智能体
    SCRIPT_DATABASE_SAVER = "script_database_saver"  # 脚本数据库保存智能体


class TopicTypes(Enum):
    """主题类型枚举"""
    # 分析类主题
    MULTIMODAL_ANALYZER = "multimodal_analyzer"
    WEB_SCRAPER = "web_scraper"
    API_ANALYZER = "api_analyzer"

    # 生成类主题
    TEST_PLANNER = "test_planner"
    YAML_GENERATOR = "yaml_generator"
    PLAYWRIGHT_GENERATOR = "playwright_generator"
    API_TEST_GENERATOR = "api_test_generator"
    ACTION_GENERATOR = "action_generator"            # 动作生成主题（保持兼容性）
    IMAGE_ANALYZER = "image_analyzer"                # Web分析主题

    # 执行类主题
    YAML_EXECUTOR = "yaml_executor"
    PLAYWRIGHT_EXECUTOR = "playwright_executor"
    API_TEST_EXECUTOR = "api_test_executor"

    # 管理类主题
    RESULT_ANALYZER = "result_analyzer"
    REPORT_GENERATOR = "report_generator"
    SCRIPT_MANAGER = "script_manager"
    SCRIPT_DATABASE_SAVER = "script_database_saver"

    # 系统主题
    STREAM_OUTPUT = "stream_output"


class TestTypes(Enum):
    """测试类型枚举"""
    FUNCTIONAL = "functional"                        # 功能测试
    UI_INTERACTION = "ui_interaction"                # UI交互测试
    REGRESSION = "regression"                        # 回归测试
    SMOKE = "smoke"                                  # 冒烟测试
    INTEGRATION = "integration"                      # 集成测试
    PERFORMANCE = "performance"                      # 性能测试
    ACCESSIBILITY = "accessibility"                  # 可访问性测试
    CROSS_BROWSER = "cross_browser"                  # 跨浏览器测试
    MOBILE_RESPONSIVE = "mobile_responsive"          # 移动端响应式测试
    API_INTEGRATION = "api_integration"              # API集成测试


class ActionTypes(Enum):
    """动作类型枚举"""
    CLICK = "click"                                  # 点击
    INPUT = "input"                                  # 输入
    HOVER = "hover"                                  # 悬停
    SCROLL = "scroll"                                # 滚动
    WAIT = "wait"                                    # 等待
    ASSERT = "assert"                                # 断言
    NAVIGATE = "navigate"                            # 导航
    SCREENSHOT = "screenshot"                        # 截图
    KEYBOARD_PRESS = "keyboard_press"                # 按键
    DRAG_DROP = "drag_drop"                          # 拖拽
    SELECT = "select"                                # 选择
    UPLOAD = "upload"                                # 上传文件


class BrowserTypes(Enum):
    """浏览器类型枚举"""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"
    CHROME = "chrome"
    EDGE = "edge"


class DeviceTypes(Enum):
    """设备类型枚举"""
    DESKTOP = "desktop"
    TABLET = "tablet"
    MOBILE = "mobile"
    CUSTOM = "custom"


class MessageRegion(Enum):
    """消息区域类型"""
    PROCESS = "process"
    ANALYSIS = "analysis"
    GENERATION = "generation"
    REVIEW = "review"
    ERROR = "error"
    SUCCESS = "success"
    WARNING = "warning"
    INFO = "info"


class SessionStatus(Enum):
    """会话状态枚举"""
    ACTIVE = "active"
    CLOSED = "closed"
    EXPIRED = "expired"
    SUSPENDED = "suspended"

"""
UI自动化测试系统 - 常量和映射关系定义
统一管理所有常量、映射关系和默认配置
"""
from typing import Dict
from .enums import AgentTypes, TopicTypes, BrowserTypes, DeviceTypes
from .models import TestEnvironment


# 智能体名称映射
AGENT_NAMES: Dict[str, str] = {
    # 图片分析智能体团队
    AgentTypes.UI_EXPERT.value: "UI元素分析智能体",
    AgentTypes.INTERACTION_ANALYST.value: "交互分析师智能体",
    AgentTypes.QUALITY_REVIEWER.value: "质量审查员智能体",
    AgentTypes.MIDSCENE_EXPERT.value: "MidScene用例设计智能体",

    # 分析类智能体
    AgentTypes.MULTIMODAL_ANALYZER.value: "多模态分析智能体",
    AgentTypes.WEB_SCRAPER.value: "网页抓取智能体",
    AgentTypes.API_ANALYZER.value: "API接口分析智能体",
    AgentTypes.IMAGE_ANALYZER.value: "图片分析智能体",
    AgentTypes.PAGE_ANALYZER.value: "页面分析智能体",

    # 生成类智能体
    AgentTypes.TEST_PLANNER.value: "测试规划智能体",
    AgentTypes.YAML_GENERATOR.value: "YAML生成智能体",
    AgentTypes.PLAYWRIGHT_GENERATOR.value: "Playwright代码生成智能体",
    AgentTypes.API_TEST_GENERATOR.value: "API测试生成智能体",
    AgentTypes.ACTION_GENERATOR.value: "动作生成智能体",

    # 执行类智能体
    AgentTypes.YAML_EXECUTOR.value: "YAML脚本执行智能体",
    AgentTypes.PLAYWRIGHT_EXECUTOR.value: "Playwright执行智能体",
    AgentTypes.API_TEST_EXECUTOR.value: "API测试执行智能体",

    # 管理类智能体
    AgentTypes.RESULT_ANALYZER.value: "结果分析智能体",
    AgentTypes.REPORT_GENERATOR.value: "报告生成智能体",
    AgentTypes.SCRIPT_MANAGER.value: "脚本管理智能体",
    AgentTypes.SCRIPT_DATABASE_SAVER.value: "脚本数据库保存智能体",
    AgentTypes.PAGE_ANALYSIS_STORAGE.value: "页面分析存储智能体",

    # 解析类智能体
    AgentTypes.TEST_CASE_ELEMENT_PARSER.value: "测试用例元素解析智能体"
}

# 主题类型映射
TOPIC_TYPES: Dict[str, str] = {
    # 分析类主题
    "multimodal_analyzer": TopicTypes.MULTIMODAL_ANALYZER.value,
    "web_scraper": TopicTypes.WEB_SCRAPER.value,
    "api_analyzer": TopicTypes.API_ANALYZER.value,
    "image_analyzer": TopicTypes.IMAGE_ANALYZER.value,

    # 生成类主题
    "test_planner": TopicTypes.TEST_PLANNER.value,
    "yaml_generator": TopicTypes.YAML_GENERATOR.value,
    "playwright_generator": TopicTypes.PLAYWRIGHT_GENERATOR.value,
    "api_test_generator": TopicTypes.API_TEST_GENERATOR.value,
    "action_generator": TopicTypes.ACTION_GENERATOR.value,

    # 执行类主题
    "yaml_executor": TopicTypes.YAML_EXECUTOR.value,
    "playwright_executor": TopicTypes.PLAYWRIGHT_EXECUTOR.value,
    "api_test_executor": TopicTypes.API_TEST_EXECUTOR.value,

    # 管理类主题
    "result_analyzer": TopicTypes.RESULT_ANALYZER.value,
    "report_generator": TopicTypes.REPORT_GENERATOR.value,
    "script_manager": TopicTypes.SCRIPT_MANAGER.value,
    "script_database_saver": TopicTypes.SCRIPT_DATABASE_SAVER.value,
    "page_analysis_storage": TopicTypes.PAGE_ANALYSIS_STORAGE.value,

    # 解析类主题
    "test_case_element_parser": TopicTypes.TEST_CASE_ELEMENT_PARSER.value,

    # 系统主题
    "stream_output": TopicTypes.STREAM_OUTPUT.value,
}

# 默认配置
DEFAULT_TEST_ENVIRONMENT = TestEnvironment(
    name="默认环境",
    base_url="http://localhost:3000",
    browser=BrowserTypes.CHROMIUM,
    device=DeviceTypes.DESKTOP
)

# 常用设备配置
DEVICE_PRESETS = {
    "iPhone 12": {
        "viewport_width": 390,
        "viewport_height": 844,
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
    },
    "iPad": {
        "viewport_width": 768,
        "viewport_height": 1024,
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
    },
    "Desktop": {
        "viewport_width": 1280,
        "viewport_height": 960,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
}

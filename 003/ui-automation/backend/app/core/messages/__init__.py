"""
UI自动化测试系统 - 消息类型模块
统一管理所有智能体间通信的消息类型
"""

# 导出基础消息类型
from .base import *

# 导出各模块的消息类型
from .web import *
from .android import *
from .api import *

__all__ = [
    # 基础消息类型
    'BaseMessage', 'ResponseMessage', 'StreamMessage',

    # Web模块消息类型 - 主要类型（统一使用多模态分析类型）
    'WebMultimodalAnalysisRequest', 'WebMultimodalAnalysisResponse',
    # 别名导出（向后兼容）
    'WebImageAnalysisRequest', 'WebImageAnalysisResponse',
    # 其他Web消息类型
    'WebUIAnalysisMessage', 'WebYAMLGenerationMessage', 'WebPlaywrightGenerationMessage',
    'WebScriptExecutionMessage', 'WebURLAnalysisRequest', 'WebCrawlAnalysisRequest',
    'PageAnalysis', 'WebGeneratedScript', 'UIElement', 'TestAction',

    # Web执行请求消息类型
    'YAMLExecutionRequest', 'YAMLExecutionConfig',
    'PlaywrightExecutionRequest', 'PlaywrightExecutionConfig',

    # 测试用例元素解析消息类型
    'TestCaseElementParseRequest', 'TestCaseElementParseResponse',
    'ParsedPageElement', 'ParsedPageInfo',



    # Android模块消息类型
    'AndroidAnalysisRequest', 'AndroidAnalysisResponse',
    'AndroidUIAnalysisMessage', 'AndroidTestGenerationMessage',

    # API测试模块消息类型
    'APIAnalysisRequest', 'APIAnalysisResponse',
    'APITestGenerationMessage', 'APITestExecutionMessage',

    # 通用智能体消息类型
    'RequirementMessage', 'TestPlanMessage', 'UIAnalysisMessage',
    'ActionGenerationMessage', 'TestExecutionMessage', 'ResultAnalysisMessage',
    'ReportGenerationMessage',

    # Web模块枚举
    'AnalysisType'
]

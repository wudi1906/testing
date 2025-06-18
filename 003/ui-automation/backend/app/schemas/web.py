"""
Web模块的API模式定义

提供Web平台相关的API请求和响应模式，
这些模式主要用于API接口的数据验证和文档生成。
"""

# 重新导出核心消息类型，保持向后兼容
from app.core.messages.web import (
    # 基础数据模型
    UIElement,
    TestAction,
    PageAnalysis,
    WebGeneratedScript,
    
    # 分析请求和响应（统一使用多模态分析类型）
    WebMultimodalAnalysisRequest,
    WebMultimodalAnalysisResponse,
    # 别名导出（向后兼容）
    WebImageAnalysisRequest,
    WebImageAnalysisResponse,
    
    # URL和爬虫分析
    WebURLAnalysisRequest,
    WebCrawlAnalysisRequest,
    
    # 执行相关
    YAMLExecutionConfig,
    YAMLExecutionRequest,
    PlaywrightExecutionConfig,
    PlaywrightExecutionRequest,
    ScriptExecutionRequest,
    ScriptExecutionStatus,
    
    # 智能体消息
    WebUIAnalysisMessage,
    WebYAMLGenerationMessage,
    WebPlaywrightGenerationMessage,
    WebScriptExecutionMessage,
    
    # 枚举类型
    AnalysisType
)

# 流式消息类型
from app.core.messages import StreamMessage

__all__ = [
    # 基础数据模型
    "UIElement",
    "TestAction", 
    "PageAnalysis",
    "WebGeneratedScript",
    
    # 分析请求和响应（统一使用多模态分析类型）
    "WebMultimodalAnalysisRequest",
    "WebMultimodalAnalysisResponse",
    # 别名导出（向后兼容）
    "WebImageAnalysisRequest",
    "WebImageAnalysisResponse",
    
    # URL和爬虫分析
    "WebURLAnalysisRequest",
    "WebCrawlAnalysisRequest",
    
    # 执行相关
    "YAMLExecutionConfig",
    "YAMLExecutionRequest",
    "PlaywrightExecutionConfig", 
    "PlaywrightExecutionRequest",
    "ScriptExecutionRequest",
    "ScriptExecutionStatus",
    
    # 智能体消息
    "WebUIAnalysisMessage",
    "WebYAMLGenerationMessage",
    "WebPlaywrightGenerationMessage", 
    "WebScriptExecutionMessage",
    
    # 流式消息
    "StreamMessage",
    
    # 枚举类型
    "AnalysisType"
]

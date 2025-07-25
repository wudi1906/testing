"""
消息定义模块
定义智能体之间通信的消息类型
"""

from .base import BaseMessage, StreamMessage
from .api_automation import *

__all__ = [
    "BaseMessage",
    "StreamMessage",
    # API自动化消息
    "ApiDocParseRequest",
    "ApiDocParseResponse",
    "DependencyAnalysisRequest", 
    "DependencyAnalysisResponse",
    "TestScriptGenerationRequest",
    "TestScriptGenerationResponse",
    "TestExecutionRequest",
    "TestExecutionResponse",
    "LogRecordRequest",
    "LogRecordResponse",
    "ApiEndpointInfo",
    "TestCaseInfo",
    "ExecutionResult",
    "DependencyInfo"
]

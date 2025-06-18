"""
Schemas模块
定义API请求和响应的数据模型

提供所有API接口的请求和响应模式定义
"""

# 导出Web模块的模式
from .web import *
from .ui_automation import *

__all__ = [
    # Web模块导出的所有类型（统一使用多模态分析类型）
    "WebMultimodalAnalysisRequest",
    "WebMultimodalAnalysisResponse",
    # 别名导出（向后兼容）
    "WebImageAnalysisRequest",
    "WebImageAnalysisResponse",
    # 其他核心类型
    "StreamMessage",
    "PageAnalysis",
    "UIElement",
    "TestAction",
    "WebGeneratedScript",
    "AnalysisType"
]

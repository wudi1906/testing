"""
Web API端点模块
"""

# Web图片分析API - 集成数据库功能的完整API
from .image_analysis import router as image_analysis_router

# 脚本管理API
from .script_management import router as script_management_router

# 脚本执行API
from .script_execution import router as script_execution_router

__all__ = [
    "image_analysis_router",
    "script_management_router",
    "script_execution_router"
]

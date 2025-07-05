"""
Web API端点模块
"""

# Web图片分析API - 集成数据库功能的完整API
# from .ui_image_analysis import router as image_analysis_router

# 页面分析API - 页面截图智能分析
from .page_element_analysis import router as page_analysis_router

# 脚本管理API
from .test_script_management import router as script_management_router

# 脚本执行API
from .test_script_execution import router as script_execution_router

# 基于文本生成脚本API
from .text_script_generation import router as text_to_script_router

# 图片到描述生成API
from .image_description_generation import router as image_to_description_router

# 测试用例元素解析API
from .test_case_parsing import router as test_case_parser_router

# 定时任务管理API
from .scheduled_tasks import router as scheduled_tasks_router

__all__ = [
    "image_analysis_router",
    "page_analysis_router",
    "script_management_router",
    "script_execution_router",
    "text_to_script_router",
    "image_to_description_router",
    "test_case_parser_router",
    "scheduled_tasks_router"
]

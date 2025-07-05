"""
API v1 路由汇总 - 基于前端功能结构的模块化架构
"""
from fastapi import APIRouter

# 导入各功能模块的路由
from app.api.v1.endpoints.web import (
    # image_analysis_router,
    page_analysis_router,
    script_management_router,
    script_execution_router,
    text_to_script_router,
    image_to_description_router,
    test_case_parser_router,
    scheduled_tasks_router
)
from app.api.v1.endpoints.web.test_execution_reports import router as test_reports_router
from app.api.v1.endpoints.test_execution_history import router as test_execution_history_router
from app.api.v1.endpoints import sessions, system

api_router = APIRouter()

# ==================== Web自动化测试模块 ====================
# 对应前端路径: /web/*

# Web图片分析 - 集成数据库功能的完整API - /web/create/*
# api_router.include_router(
#     image_analysis_router,
#     prefix="/web/create",
#     tags=["Web-图片分析"]
# )

# Web页面分析 - /web/page-analysis/* (页面截图智能分析)
api_router.include_router(
    page_analysis_router,
    prefix="/web/page-analysis",
    tags=["Web-页面分析"]
)

# Web脚本管理 - /web/scripts/* (数据库脚本管理)
api_router.include_router(
    script_management_router,
    prefix="/web",
    tags=["Web-脚本管理"]
)

# Web脚本执行 - /web/execution/* (统一脚本执行，支持基于脚本ID的执行)
api_router.include_router(
    script_execution_router,
    prefix="/web/execution",
    tags=["Web-脚本执行"]
)

# Web测试报告 - /web/reports/* (测试报告管理和查看)
api_router.include_router(
    test_reports_router,
    prefix="/web/reports",
    tags=["Web-测试报告"]
)

# Web文本生成脚本API - /web/create/* (基于自然语言生成脚本)
api_router.include_router(
    text_to_script_router,
    prefix="/web/create",
    tags=["Web-文本生成脚本"]
)

# Web图片描述生成API - /web/create/* (图片分析生成描述)
api_router.include_router(
    image_to_description_router,
    prefix="/web/create",
    tags=["Web-图片描述生成"]
)

# Web测试用例元素解析API - /web/test-case-parser/* (测试用例解析页面元素)
api_router.include_router(
    test_case_parser_router,
    prefix="/web/test-case-parser",
    tags=["Web-测试用例解析"]
)

# Web定时任务管理API - /web/scheduled-tasks/* (定时任务管理和调度)
api_router.include_router(
    scheduled_tasks_router,
    prefix="/web",
    tags=["Web-定时任务"]
)

# ==================== 测试执行历史模块 ====================
# 对应前端路径: /test/*

# 测试执行历史API - /test/* (脚本执行历史查询和管理)
api_router.include_router(
    test_execution_history_router,
    prefix="/test",
    tags=["测试-执行历史"]
)

# ==================== 系统模块 ====================

# 会话管理模块 - 用户会话管理
api_router.include_router(
    sessions.router,
    prefix="/sessions",
    tags=["系统-会话管理"]
)

# 系统管理模块 - 系统状态和配置
api_router.include_router(
    system.router,
    prefix="/system",
    tags=["系统-系统管理"]
)

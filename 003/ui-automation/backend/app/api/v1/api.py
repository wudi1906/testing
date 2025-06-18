"""
API v1 路由汇总 - 基于前端功能结构的模块化架构
"""
from fastapi import APIRouter

# 导入各功能模块的路由
from app.api.v1.endpoints.web import (
    image_analysis_router,
    script_management_router,
    script_execution_router
)
from app.api.v1.endpoints.web.test_reports import router as test_reports_router
from app.api.v1.endpoints import sessions, system

api_router = APIRouter()

# ==================== Web自动化测试模块 ====================
# 对应前端路径: /web/*

# Web图片分析 - 集成数据库功能的完整API - /web/create/*
api_router.include_router(
    image_analysis_router,
    prefix="/web/create",
    tags=["Web-图片分析"]
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

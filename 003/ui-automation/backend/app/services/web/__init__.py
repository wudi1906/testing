"""
Web服务模块
提供Web平台相关的业务服务
"""

from app.services.web.orchestrator_service import WebOrchestrator, get_web_orchestrator

__all__ = [
    "WebOrchestrator",
    "get_web_orchestrator"
]

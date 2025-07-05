"""
Web Service Module
Provides business services related to Web platform
"""

from app.services.web.orchestrator_service import WebAgentOrchestrator, get_web_orchestrator

__all__ = [
    "WebAgentOrchestrator",
    "get_web_orchestrator"
]

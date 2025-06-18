"""
UI自动化测试系统 - 智能体核心组件
统一管理所有智能体的基础类、收集器和工厂
"""

# 导出核心组件
from app.core.agents.base import BaseAgent, StreamMessage
from app.core.agents.collector import StreamResponseCollector

__all__ = [
    'BaseAgent',
    'StreamMessage', 
    'StreamResponseCollector',
]

"""
UI自动化测试系统 - 类型定义模块
统一管理所有枚举、数据模型和常量定义
"""

# 导出所有类型定义
from .enums import *
from .models import *
from .constants import *

__all__ = [
    # 枚举类型
    'AgentPlatform', 'AgentTypes', 'TopicTypes', 'TestTypes', 
    'ActionTypes', 'BrowserTypes', 'DeviceTypes', 'MessageRegion',
    
    # 数据模型
    'TestCase', 'TestAction', 'TestResult', 'UIElement', 'TestEnvironment', 'TestExecutionContext',
    
    # 常量和映射
    'AGENT_NAMES', 'TOPIC_TYPES', 'DEFAULT_TEST_ENVIRONMENT', 'DEVICE_PRESETS'
]

"""
UI自动化测试系统 - 核心类型定义
重构后的统一类型定义，避免重复和混乱
"""

# 重新导出所有类型，保持向后兼容
from .types.enums import *
from .types.models import *
from .types.constants import *

# 为了向后兼容，保留原有的导入方式
__all__ = [
    # 枚举类型
    'AgentPlatform', 'AgentTypes', 'TopicTypes', 'TestTypes',
    'ActionTypes', 'BrowserTypes', 'DeviceTypes', 'MessageRegion',

    # 数据模型
    'TestCase', 'TestAction', 'TestResult', 'UIElement', 'TestEnvironment',

    # 常量和映射
    'AGENT_NAMES', 'TOPIC_TYPES', 'DEFAULT_TEST_ENVIRONMENT', 'DEVICE_PRESETS'
]


# 这个文件现在作为统一的导出点，所有具体定义都在types/子模块中

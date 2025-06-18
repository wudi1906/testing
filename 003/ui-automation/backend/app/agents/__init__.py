"""
UI自动化测试系统 - 智能体模块
提供统一的智能体工厂和所有智能体的导入接口
"""

# 导入智能体工厂
from .factory import AgentFactory, get_agent_factory

# 延迟获取全局工厂实例
def get_global_agent_factory():
    """获取全局智能体工厂实例"""
    return get_agent_factory()

# 保持向后兼容性
agent_factory = get_global_agent_factory()

# 导入Web平台智能体
from .web import (
    ImageAnalyzerAgent,
    YAMLGeneratorAgent,
    YAMLExecutorAgent,
    PlaywrightGeneratorAgent,
    PlaywrightExecutorAgent
)

__all__ = [
    # 工厂类
    'AgentFactory',
    'get_agent_factory',
    'get_global_agent_factory',
    'agent_factory',

    # Web智能体
    'ImageAnalyzerAgent',
    'YAMLGeneratorAgent',
    'YAMLExecutorAgent',
    'PlaywrightGeneratorAgent',
    'PlaywrightExecutorAgent'
]

"""
Web平台相关智能体模块
包含Web UI自动化测试的分析、生成和执行智能体
"""

# Web专用智能体
from app.agents.web.image_analyzer import ImageAnalyzerAgent
from app.agents.web.yaml_generator import YAMLGeneratorAgent
from app.agents.web.yaml_executor import YAMLExecutorAgent
from app.agents.web.playwright_generator import PlaywrightGeneratorAgent
from app.agents.web.playwright_executor import PlaywrightExecutorAgent
from app.agents.web.script_database_saver import ScriptDatabaseSaverAgent

__all__ = [
    'ImageAnalyzerAgent',
    'YAMLGeneratorAgent',
     'YAMLExecutorAgent',
    'PlaywrightGeneratorAgent',
    'PlaywrightExecutorAgent',
    'ScriptDatabaseSaverAgent'
]

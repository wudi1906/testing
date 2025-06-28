"""
Web平台相关智能体模块
包含Web UI自动化测试的分析、生成和执行智能体
"""

# Web专用智能体
from app.agents.web.ui_image_analyzer_agent import ImageAnalyzerAgent
from app.agents.web.yaml_script_generator_agent import YAMLGeneratorAgent
from app.agents.web.yaml_script_executor_agent import YAMLExecutorAgent
from app.agents.web.playwright_script_generator_agent import PlaywrightGeneratorAgent
from app.agents.web.playwright_script_executor_agent import PlaywrightExecutorAgent
from app.agents.web.test_script_storage_agent import ScriptDatabaseSaverAgent
from app.agents.web.page_data_storage_agent import PageAnalysisStorageAgent

__all__ = [
    'ImageAnalyzerAgent',
    'YAMLGeneratorAgent',
     'YAMLExecutorAgent',
    'PlaywrightGeneratorAgent',
    'PlaywrightExecutorAgent',
    'ScriptDatabaseSaverAgent',
    'PageAnalysisStorageAgent'
]

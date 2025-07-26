"""
接口自动化智能体模块 - 重新设计版本
"""
from .api_doc_parser_agent import ApiDocParserAgent
from .api_analyzer_agent import ApiAnalyzerAgent
from .test_case_generator_agent import TestCaseGeneratorAgent
from .script_generator_agent import ScriptGeneratorAgent
from .script_executor_agent import TestExecutorAgent

# 注意：以下智能体暂时注释掉，因为它们依赖被注释的消息类型
# from .log_recorder_agent import LogRecorderAgent

__all__ = [
    "ApiDocParserAgent",
    "ApiAnalyzerAgent",
    "TestCaseGeneratorAgent",
    "ScriptGeneratorAgent",
    "TestExecutorAgent",   # ✅ 已修复
    # "LogRecorderAgent"   # 暂时注释
]

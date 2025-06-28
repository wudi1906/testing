"""
数据库仓库模块
提供数据访问层的抽象
"""

from .base import BaseRepository
from .script_repository import ScriptRepository
from .page_analysis_repository import PageAnalysisRepository, PageElementRepository
# from .session_repository import SessionRepository
# from .project_repository import ProjectRepository
# from .execution_repository import ExecutionRepository
# from .report_repository import ReportRepository

__all__ = [
    'BaseRepository',
    'ScriptRepository',
    'PageAnalysisRepository',
    'PageElementRepository',
    # 'SessionRepository',
    # 'ProjectRepository',
    # 'ExecutionRepository',
    # 'ReportRepository',
]

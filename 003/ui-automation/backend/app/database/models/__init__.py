"""
数据库模型模块
定义所有数据库表的SQLAlchemy模型
"""

from .base import BaseModel
from .projects import Project
from .sessions import Session
from .scripts import TestScript, ScriptTag, ScriptRelationship
from .executions import ScriptExecution, ExecutionArtifact, BatchExecution, ExecutionLog
from .reports import TestReport
# from .templates import ReportTemplate, ScriptCollection, CollectionScript, CollectionTag
# from .settings import SystemSetting, UserPreference

__all__ = [
    'BaseModel',
    'Project',
    'Session',
    'TestScript',
    'ScriptTag',
    'ScriptRelationship',
    'ScriptExecution',
    'ExecutionArtifact',
    'BatchExecution',
    'ExecutionLog',
    'TestReport',
    # 'ReportTag',
    # 'TestCaseResult',
    # 'ReportTemplate',
    # 'ScriptCollection',
    # 'CollectionScript',
    # 'CollectionTag',
    # 'SystemSetting',
    # 'UserPreference',
]

"""
数据库模块初始化
提供数据库连接和基础配置
"""

from .connection import DatabaseManager, get_database
from .models import *
from .repositories import *

__all__ = [
    'DatabaseManager',
    'get_database',
]

"""
数据库启动初始化模块
在应用启动时初始化数据库连接和表结构
"""
import os
import asyncio
from typing import Optional
from sqlalchemy import text

from app.database.connection import init_database, db_manager
from app.core.logging import get_logger

logger = get_logger(__name__)


async def initialize_database_on_startup():
    """应用启动时初始化数据库"""
    try:
        # 检查是否启用数据库
        use_database = os.getenv('USE_DATABASE', 'true').lower() == 'true'
        
        if not use_database:
            logger.info("数据库功能已禁用，跳过数据库初始化")
            return False
        
        logger.info("🚀 开始初始化数据库...")
        
        # 初始化数据库连接和表结构
        await init_database()
        
        # 验证数据库连接
        async with db_manager.get_session() as session:
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
            if test_value == 1:
                logger.info("✅ 数据库连接验证成功")
            else:
                logger.error("❌ 数据库连接验证失败")
                return False
        
        logger.info("🎉 数据库初始化完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        logger.warning("⚠️ 将回退到文件存储模式")
        return False


async def cleanup_database_on_shutdown():
    """应用关闭时清理数据库连接"""
    try:
        logger.info("🔄 正在关闭数据库连接...")
        await db_manager.close()
        logger.info("✅ 数据库连接已关闭")
    except Exception as e:
        logger.error(f"❌ 关闭数据库连接失败: {e}")


def get_database_status() -> dict:
    """获取数据库状态"""
    try:
        use_database = os.getenv('USE_DATABASE', 'true').lower() == 'true'
        
        if not use_database:
            return {
                "enabled": False,
                "status": "disabled",
                "message": "数据库功能已禁用"
            }
        
        if db_manager._initialized:
            return {
                "enabled": True,
                "status": "connected",
                "message": "数据库连接正常",
                "database_url": os.getenv('DATABASE_URL', '').split('@')[-1] if os.getenv('DATABASE_URL') else None
            }
        else:
            return {
                "enabled": True,
                "status": "disconnected",
                "message": "数据库未连接"
            }
            
    except Exception as e:
        return {
            "enabled": True,
            "status": "error",
            "message": f"数据库状态检查失败: {str(e)}"
        }


async def health_check_database() -> bool:
    """数据库健康检查"""
    try:
        if not db_manager._initialized:
            return False
        
        async with db_manager.get_session() as session:
            await session.execute(text("SELECT 1"))
            return True
            
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return False


class DatabaseManager:
    """数据库管理器，用于应用级别的数据库操作"""
    
    def __init__(self):
        self.is_initialized = False
        self.use_database = False
    
    async def startup(self):
        """启动时初始化"""
        self.is_initialized = await initialize_database_on_startup()
        self.use_database = self.is_initialized
        return self.is_initialized
    
    async def shutdown(self):
        """关闭时清理"""
        if self.is_initialized:
            await cleanup_database_on_shutdown()
            self.is_initialized = False
    
    def get_status(self) -> dict:
        """获取状态"""
        return get_database_status()
    
    async def health_check(self) -> bool:
        """健康检查"""
        if not self.is_initialized:
            return False
        return await health_check_database()
    
    def should_use_database(self) -> bool:
        """是否应该使用数据库"""
        return self.use_database and self.is_initialized


# 全局数据库管理器实例
app_database_manager = DatabaseManager()

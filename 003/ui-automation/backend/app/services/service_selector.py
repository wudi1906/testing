"""
服务选择器
根据配置和数据库状态自动选择使用数据库服务还是文件服务
"""
import os
from typing import Union

from app.services.script_service import script_service as file_script_service
from app.services.database_script_service import database_script_service
from app.core.database_startup import app_database_manager
from app.core.logging import get_logger

logger = get_logger(__name__)


class ServiceSelector:
    """服务选择器"""
    
    def __init__(self):
        self._script_service = None
        self._service_type = None
    
    def get_script_service(self):
        """获取脚本服务实例"""
        if self._script_service is None:
            self._initialize_service()
        return self._script_service
    
    def get_service_type(self) -> str:
        """获取当前使用的服务类型"""
        if self._service_type is None:
            self._initialize_service()
        return self._service_type
    
    def _initialize_service(self):
        """初始化服务"""
        try:
            # 检查是否启用数据库
            use_database = os.getenv('USE_DATABASE', 'true').lower() == 'true'
            
            if use_database and app_database_manager.should_use_database():
                # 使用数据库服务
                self._script_service = database_script_service
                self._service_type = "database"
                logger.info("✅ 使用数据库脚本服务")
            else:
                # 使用文件服务
                self._script_service = file_script_service
                self._service_type = "file"
                if use_database:
                    logger.warning("⚠️ 数据库不可用，回退到文件脚本服务")
                else:
                    logger.info("📁 使用文件脚本服务")
                    
        except Exception as e:
            # 出错时回退到文件服务
            logger.error(f"服务初始化失败，回退到文件服务: {e}")
            self._script_service = file_script_service
            self._service_type = "file"
    
    def force_database_service(self):
        """强制使用数据库服务"""
        self._script_service = database_script_service
        self._service_type = "database"
        logger.info("🔄 强制切换到数据库脚本服务")
    
    def force_file_service(self):
        """强制使用文件服务"""
        self._script_service = file_script_service
        self._service_type = "file"
        logger.info("🔄 强制切换到文件脚本服务")
    
    def get_service_info(self) -> dict:
        """获取服务信息"""
        if self._service_type is None:
            self._initialize_service()
        
        return {
            "service_type": self._service_type,
            "service_class": self._script_service.__class__.__name__,
            "database_enabled": os.getenv('USE_DATABASE', 'true').lower() == 'true',
            "database_available": app_database_manager.should_use_database(),
            "database_status": app_database_manager.get_status()
        }


# 全局服务选择器实例
service_selector = ServiceSelector()


def get_script_service():
    """获取脚本服务（全局函数）"""
    return service_selector.get_script_service()


def get_service_type() -> str:
    """获取服务类型（全局函数）"""
    return service_selector.get_service_type()


def get_service_info() -> dict:
    """获取服务信息（全局函数）"""
    return service_selector.get_service_info()


class HybridScriptService:
    """混合脚本服务
    
    在数据库服务不可用时自动回退到文件服务
    提供统一的接口，隐藏底层实现细节
    """
    
    def __init__(self):
        self.selector = service_selector
    
    async def create_script_from_analysis(self, *args, **kwargs):
        """创建脚本"""
        service = self.selector.get_script_service()
        
        if self.selector.get_service_type() == "database":
            return await service.create_script_from_analysis(*args, **kwargs)
        else:
            return service.create_script_from_analysis(*args, **kwargs)
    
    async def get_script(self, script_id: str):
        """获取脚本"""
        service = self.selector.get_script_service()
        
        if self.selector.get_service_type() == "database":
            return await service.get_script(script_id)
        else:
            return service.get_script(script_id)
    
    async def search_scripts(self, request):
        """搜索脚本"""
        service = self.selector.get_script_service()
        
        if self.selector.get_service_type() == "database":
            return await service.search_scripts(request)
        else:
            return service.search_scripts(request)
    
    async def update_script(self, script_id: str, updates: dict):
        """更新脚本"""
        service = self.selector.get_script_service()
        
        if self.selector.get_service_type() == "database":
            return await service.update_script(script_id, updates)
        else:
            return service.update_script(script_id, updates)
    
    async def delete_script(self, script_id: str):
        """删除脚本"""
        service = self.selector.get_script_service()
        
        if self.selector.get_service_type() == "database":
            return await service.delete_script(script_id)
        else:
            return service.delete_script(script_id)
    
    async def get_script_statistics(self):
        """获取脚本统计"""
        service = self.selector.get_script_service()
        
        if self.selector.get_service_type() == "database":
            return await service.get_script_statistics()
        else:
            return service.get_script_statistics()
    
    async def get_script_executions(self, script_id: str, limit: int = 20):
        """获取脚本执行记录"""
        service = self.selector.get_script_service()
        
        if self.selector.get_service_type() == "database":
            return await service.get_script_executions(script_id, limit)
        else:
            return service.get_script_executions(script_id, limit)
    
    def get_current_service_info(self) -> dict:
        """获取当前服务信息"""
        return self.selector.get_service_info()


# 全局混合服务实例
hybrid_script_service = HybridScriptService()

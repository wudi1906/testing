"""
执行记录仓库
管理脚本执行记录数据的数据访问层
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from .base import BaseRepository


class ExecutionRepository(BaseRepository):
    """执行记录数据仓库"""

    def __init__(self, db_session: Session):
        super().__init__(db_session, None)  # 暂时没有ExecutionModel

    def create_execution(self, 
                        script_id: str,
                        execution_id: str,
                        status: str = "running",
                        config: Optional[Dict[str, Any]] = None,
                        environment: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建新的执行记录
        
        Args:
            script_id: 脚本ID
            execution_id: 执行ID
            status: 执行状态
            config: 执行配置
            environment: 执行环境
            
        Returns:
            Dict[str, Any]: 创建的执行记录
        """
        execution_data = {
            "id": execution_id,
            "script_id": script_id,
            "status": status,
            "config": config or {},
            "environment": environment or {},
            "started_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "logs": [],
            "result": None,
            "error_message": None
        }
        
        return execution_data

    def get_execution_by_id(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """根据执行ID获取执行记录
        
        Args:
            execution_id: 执行ID
            
        Returns:
            Optional[Dict[str, Any]]: 执行记录，如果不存在返回None
        """
        # 暂时返回模拟数据
        return {
            "id": execution_id,
            "script_id": "script_001",
            "status": "completed",
            "config": {"browser": "chromium", "headless": True},
            "environment": {"os": "windows", "python_version": "3.12"},
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "logs": [
                {"timestamp": datetime.utcnow(), "level": "INFO", "message": "开始执行脚本"},
                {"timestamp": datetime.utcnow(), "level": "INFO", "message": "脚本执行完成"}
            ],
            "result": {"success": True, "steps_completed": 5},
            "error_message": None
        }

    def get_executions_by_script(self, 
                                script_id: str, 
                                limit: int = 20) -> List[Dict[str, Any]]:
        """获取脚本的执行记录列表
        
        Args:
            script_id: 脚本ID
            limit: 返回数量限制
            
        Returns:
            List[Dict[str, Any]]: 执行记录列表
        """
        # 暂时返回模拟数据
        executions = []
        for i in range(1, min(limit + 1, 6)):
            executions.append({
                "id": f"exec_{script_id}_{i}",
                "script_id": script_id,
                "status": "completed" if i % 2 == 0 else "failed",
                "config": {"browser": "chromium", "headless": True},
                "environment": {"os": "windows", "python_version": "3.12"},
                "started_at": datetime.utcnow(),
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "logs": [],
                "result": {"success": i % 2 == 0, "steps_completed": i * 2},
                "error_message": None if i % 2 == 0 else f"执行错误_{i}"
            })
        return executions

    def update_execution_status(self, 
                               execution_id: str, 
                               status: str,
                               result: Optional[Dict[str, Any]] = None,
                               error_message: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """更新执行状态
        
        Args:
            execution_id: 执行ID
            status: 新状态
            result: 执行结果
            error_message: 错误信息
            
        Returns:
            Optional[Dict[str, Any]]: 更新后的执行记录
        """
        execution = self.get_execution_by_id(execution_id)
        if execution:
            execution.update({
                "status": status,
                "updated_at": datetime.utcnow()
            })
            
            if result:
                execution["result"] = result
                
            if error_message:
                execution["error_message"] = error_message
                
            if status in ["completed", "failed", "cancelled"]:
                execution["completed_at"] = datetime.utcnow()
                
            return execution
        return None

    def add_execution_log(self, 
                         execution_id: str, 
                         level: str, 
                         message: str) -> bool:
        """添加执行日志
        
        Args:
            execution_id: 执行ID
            level: 日志级别
            message: 日志消息
            
        Returns:
            bool: 添加是否成功
        """
        execution = self.get_execution_by_id(execution_id)
        if execution:
            log_entry = {
                "timestamp": datetime.utcnow(),
                "level": level,
                "message": message
            }
            execution["logs"].append(log_entry)
            execution["updated_at"] = datetime.utcnow()
            return True
        return False

    def get_active_executions(self) -> List[Dict[str, Any]]:
        """获取活跃的执行记录
        
        Returns:
            List[Dict[str, Any]]: 活跃执行记录列表
        """
        # 暂时返回模拟数据
        return [
            {
                "id": f"exec_active_{i}",
                "script_id": f"script_{i}",
                "status": "running",
                "config": {"browser": "chromium", "headless": True},
                "environment": {"os": "windows", "python_version": "3.12"},
                "started_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "logs": [],
                "result": None,
                "error_message": None
            }
            for i in range(1, 4)
        ]

    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_executions": 100,
            "successful_executions": 85,
            "failed_executions": 12,
            "cancelled_executions": 3,
            "success_rate": 0.85,
            "average_execution_time": 45.5,
            "executions_by_status": {
                "completed": 85,
                "failed": 12,
                "cancelled": 3,
                "running": 2
            },
            "executions_by_script": {
                "script_001": 25,
                "script_002": 20,
                "script_003": 15,
                "others": 40
            }
        }

    def search_executions(self, 
                         query: str,
                         script_id: Optional[str] = None,
                         status: Optional[str] = None,
                         limit: int = 50) -> List[Dict[str, Any]]:
        """搜索执行记录
        
        Args:
            query: 搜索关键词
            script_id: 脚本ID过滤
            status: 状态过滤
            limit: 返回数量限制
            
        Returns:
            List[Dict[str, Any]]: 搜索结果
        """
        # 暂时返回模拟数据
        results = []
        for i in range(1, min(limit + 1, 6)):
            if not query or query.lower() in f"exec_{i}".lower():
                if not script_id or script_id == f"script_{i}":
                    if not status or status == ("completed" if i % 2 == 0 else "failed"):
                        results.append({
                            "id": f"exec_{i}",
                            "script_id": f"script_{i}",
                            "status": "completed" if i % 2 == 0 else "failed",
                            "config": {"browser": "chromium", "headless": True},
                            "environment": {"os": "windows", "python_version": "3.12"},
                            "started_at": datetime.utcnow(),
                            "completed_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow(),
                            "logs": [],
                            "result": {"success": i % 2 == 0, "steps_completed": i * 2},
                            "error_message": None if i % 2 == 0 else f"执行错误_{i}"
                        })
        return results

    def cleanup_old_executions(self, days: int = 30) -> int:
        """清理旧的执行记录
        
        Args:
            days: 保留天数
            
        Returns:
            int: 清理的记录数量
        """
        # 暂时返回模拟数据
        return 15

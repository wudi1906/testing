"""
定时任务业务服务
提供定时任务的业务逻辑处理
"""
import uuid
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from app.database.connection import db_manager
from app.database.repositories.scheduled_task_repository import ScheduledTaskRepository, TaskExecutionRepository
from app.models.scheduled_tasks import (
    ScheduledTaskCreate, ScheduledTaskUpdate, ScheduledTask, TaskExecution,
    TaskSearchRequest, TaskStatistics
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScheduledTaskService:
    """定时任务业务服务"""
    
    def __init__(self):
        self.task_repo = ScheduledTaskRepository()
        self.execution_repo = TaskExecutionRepository()
    
    def _db_to_pydantic(self, db_task) -> ScheduledTask:
        """将数据库模型转换为Pydantic模型"""
        return ScheduledTask(
            id=db_task.id,
            script_id=db_task.script_id,
            project_id=db_task.project_id,
            created_by=db_task.created_by,
            name=db_task.name,
            description=db_task.description,
            schedule_type=db_task.schedule_type,
            cron_expression=db_task.cron_expression,
            interval_seconds=db_task.interval_seconds,
            scheduled_time=db_task.scheduled_time,
            execution_config=db_task.execution_config,
            environment_variables=db_task.environment_variables,
            timeout_seconds=db_task.timeout_seconds,
            max_retries=db_task.max_retries,
            retry_interval_seconds=db_task.retry_interval_seconds,
            status=db_task.status,
            is_enabled=db_task.is_enabled,
            start_time=db_task.start_time,
            end_time=db_task.end_time,
            total_executions=db_task.total_executions,
            successful_executions=db_task.successful_executions,
            failed_executions=db_task.failed_executions,
            last_execution_time=db_task.last_execution_time,
            last_execution_status=db_task.last_execution_status,
            next_execution_time=db_task.next_execution_time,
            notification_config=db_task.notification_config,
            notify_on_success=db_task.notify_on_success,
            notify_on_failure=db_task.notify_on_failure,
            created_at=db_task.created_at,
            updated_at=db_task.updated_at
        )
    
    def _execution_db_to_pydantic(self, db_execution) -> TaskExecution:
        """将执行记录数据库模型转换为Pydantic模型"""
        return TaskExecution(
            id=db_execution.id,
            task_id=db_execution.task_id,
            script_id=db_execution.script_id,
            session_id=db_execution.session_id,
            execution_id=db_execution.execution_id,
            trigger_type=db_execution.trigger_type,
            execution_config=db_execution.execution_config,
            environment_variables=db_execution.environment_variables,
            status=db_execution.status,
            scheduled_time=db_execution.scheduled_time,
            start_time=db_execution.start_time,
            end_time=db_execution.end_time,
            duration_seconds=db_execution.duration_seconds,
            exit_code=db_execution.exit_code,
            error_message=db_execution.error_message,
            output_log=db_execution.output_log,
            retry_count=db_execution.retry_count,
            is_retry=db_execution.is_retry,
            parent_execution_id=db_execution.parent_execution_id,
            performance_metrics=db_execution.performance_metrics,
            report_path=db_execution.report_path,
            report_url=db_execution.report_url,
            created_at=db_execution.created_at,
            updated_at=db_execution.updated_at
        )
    
    def _pydantic_to_db_dict(self, task_data) -> Dict[str, Any]:
        """将Pydantic模型转换为数据库字典"""
        if isinstance(task_data, ScheduledTaskCreate):
            return {
                'script_id': task_data.script_id,
                'project_id': task_data.project_id,
                'name': task_data.name,
                'description': task_data.description,
                'schedule_type': task_data.schedule_type,
                'cron_expression': task_data.cron_expression,
                'interval_seconds': task_data.interval_seconds,
                'scheduled_time': task_data.scheduled_time,
                'execution_config': task_data.execution_config,
                'environment_variables': task_data.environment_variables,
                'timeout_seconds': task_data.timeout_seconds,
                'max_retries': task_data.max_retries,
                'retry_interval_seconds': task_data.retry_interval_seconds,
                'start_time': task_data.start_time,
                'end_time': task_data.end_time,
                'notification_config': task_data.notification_config,
                'notify_on_success': task_data.notify_on_success,
                'notify_on_failure': task_data.notify_on_failure,
                'status': 'active',
                'is_enabled': True
            }
        elif isinstance(task_data, ScheduledTaskUpdate):
            data = {}
            for field, value in task_data.model_dump(exclude_unset=True).items():
                if value is not None:
                    data[field] = value
            return data
        else:
            return task_data
    
    async def create_task(self, task_data: ScheduledTaskCreate) -> ScheduledTask:
        """创建定时任务"""
        try:
            async with db_manager.get_session() as session:
                # 生成任务ID
                task_id = str(uuid.uuid4())
                
                # 转换数据
                db_data = self._pydantic_to_db_dict(task_data)
                db_data['id'] = task_id
                
                # 创建任务
                db_task = await self.task_repo.create(session, **db_data)
                await session.commit()
                
                # 重新获取完整数据
                result = await self.task_repo.get_by_id(session, task_id)
                return self._db_to_pydantic(result)
                
        except Exception as e:
            logger.error(f"创建定时任务失败: {e}")
            raise
    
    async def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """根据ID获取定时任务"""
        try:
            async with db_manager.get_session() as session:
                db_task = await self.task_repo.get_by_id(session, task_id)
                if db_task:
                    return self._db_to_pydantic(db_task)
                return None
        except Exception as e:
            logger.error(f"获取定时任务失败: {task_id} - {e}")
            raise
    
    async def update_task(self, task_id: str, updates: ScheduledTaskUpdate) -> Optional[ScheduledTask]:
        """更新定时任务"""
        try:
            async with db_manager.get_session() as session:
                # 检查任务是否存在
                existing = await self.task_repo.get_by_id(session, task_id)
                if not existing:
                    raise ValueError(f"定时任务不存在: {task_id}")
                
                # 转换更新数据
                update_data = self._pydantic_to_db_dict(updates)
                
                # 执行更新
                updated = await self.task_repo.update(session, task_id, **update_data)
                if not updated:
                    raise Exception(f"更新定时任务失败: {task_id}")
                
                await session.commit()
                
                # 重新获取完整数据
                result = await self.task_repo.get_by_id(session, task_id)
                return self._db_to_pydantic(result)
                
        except Exception as e:
            logger.error(f"更新定时任务失败: {task_id} - {e}")
            raise
    
    async def delete_task(self, task_id: str) -> bool:
        """删除定时任务"""
        try:
            async with db_manager.get_session() as session:
                success = await self.task_repo.delete(session, task_id)
                await session.commit()
                return success
        except Exception as e:
            logger.error(f"删除定时任务失败: {task_id} - {e}")
            raise
    
    async def search_tasks(self, request: TaskSearchRequest) -> Tuple[List[ScheduledTask], int]:
        """搜索定时任务"""
        try:
            async with db_manager.get_session() as session:
                db_tasks, total = await self.task_repo.search_tasks(session, request)
                tasks = [self._db_to_pydantic(task) for task in db_tasks]
                return tasks, total
        except Exception as e:
            logger.error(f"搜索定时任务失败: {e}")
            raise
    
    async def get_statistics(self) -> TaskStatistics:
        """获取定时任务统计信息"""
        try:
            async with db_manager.get_session() as session:
                return await self.task_repo.get_statistics(session)
        except Exception as e:
            logger.error(f"获取定时任务统计失败: {e}")
            raise
    
    async def get_tasks_by_script_id(self, script_id: str) -> List[ScheduledTask]:
        """根据脚本ID获取定时任务"""
        try:
            async with db_manager.get_session() as session:
                db_tasks = await self.task_repo.get_by_script_id(session, script_id)
                return [self._db_to_pydantic(task) for task in db_tasks]
        except Exception as e:
            logger.error(f"根据脚本ID获取定时任务失败: {script_id} - {e}")
            raise
    
    async def get_task_executions(self, task_id: str, limit: int = 20) -> List[TaskExecution]:
        """获取任务执行历史"""
        try:
            async with db_manager.get_session() as session:
                db_executions = await self.execution_repo.get_by_task_id(session, task_id, limit)
                return [self._execution_db_to_pydantic(exec) for exec in db_executions]
        except Exception as e:
            logger.error(f"获取任务执行历史失败: {task_id} - {e}")
            raise
    
    async def get_recent_executions(self, limit: int = 50) -> List[TaskExecution]:
        """获取最近的执行记录"""
        try:
            async with db_manager.get_session() as session:
                db_executions = await self.execution_repo.get_recent_executions(session, limit)
                return [self._execution_db_to_pydantic(exec) for exec in db_executions]
        except Exception as e:
            logger.error(f"获取最近执行记录失败: {e}")
            raise
    
    async def get_active_tasks(self) -> List[ScheduledTask]:
        """获取所有活跃的定时任务"""
        try:
            async with db_manager.get_session() as session:
                db_tasks = await self.task_repo.get_active_tasks(session)
                return [self._db_to_pydantic(task) for task in db_tasks]
        except Exception as e:
            logger.error(f"获取活跃定时任务失败: {e}")
            raise


# 全局定时任务服务实例
scheduled_task_service = ScheduledTaskService()

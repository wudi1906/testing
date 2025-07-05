"""
定时任务仓库
提供定时任务相关的数据访问操作
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update, delete
from sqlalchemy.orm import selectinload

from app.database.models.scheduled_tasks import ScheduledTask, TaskExecution
from app.models.scheduled_tasks import TaskSearchRequest, TaskStatistics
from .base import BaseRepository
from app.core.logging import get_logger

logger = get_logger(__name__)


class ScheduledTaskRepository(BaseRepository[ScheduledTask]):
    """定时任务仓库"""
    
    def __init__(self):
        super().__init__(ScheduledTask)
    
    async def get_by_id_with_executions(self, session: AsyncSession, task_id: str) -> Optional[ScheduledTask]:
        """获取任务及其执行记录"""
        try:
            result = await session.execute(
                select(ScheduledTask)
                .options(selectinload(ScheduledTask.executions))
                .where(ScheduledTask.id == task_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"获取任务及执行记录失败: {e}")
            raise
    
    async def search_tasks(self, session: AsyncSession, request: TaskSearchRequest) -> tuple[List[ScheduledTask], int]:
        """搜索定时任务"""
        try:
            # 构建查询条件
            conditions = []
            
            if request.query:
                conditions.append(
                    or_(
                        ScheduledTask.name.ilike(f"%{request.query}%"),
                        ScheduledTask.description.ilike(f"%{request.query}%")
                    )
                )
            
            if request.script_id:
                conditions.append(ScheduledTask.script_id == request.script_id)
            
            if request.project_id:
                conditions.append(ScheduledTask.project_id == request.project_id)
            
            if request.status:
                conditions.append(ScheduledTask.status == request.status)
            
            if request.schedule_type:
                conditions.append(ScheduledTask.schedule_type == request.schedule_type)
            
            if request.is_enabled is not None:
                conditions.append(ScheduledTask.is_enabled == request.is_enabled)
            
            if request.created_by:
                conditions.append(ScheduledTask.created_by == request.created_by)
            
            # 构建基础查询
            base_query = select(ScheduledTask)
            if conditions:
                base_query = base_query.where(and_(*conditions))
            
            # 获取总数
            count_query = select(func.count()).select_from(base_query.subquery())
            count_result = await session.execute(count_query)
            total = count_result.scalar()
            
            # 添加排序和分页
            sort_column = getattr(ScheduledTask, request.sort_by, ScheduledTask.created_at)
            if request.sort_order.lower() == 'desc':
                base_query = base_query.order_by(sort_column.desc())
            else:
                base_query = base_query.order_by(sort_column.asc())
            
            base_query = base_query.offset(request.offset).limit(request.limit)
            
            # 执行查询
            result = await session.execute(base_query)
            tasks = result.scalars().all()
            
            return list(tasks), total
            
        except Exception as e:
            logger.error(f"搜索定时任务失败: {e}")
            raise
    
    async def get_statistics(self, session: AsyncSession) -> TaskStatistics:
        """获取任务统计信息"""
        try:
            # 任务总数统计
            total_result = await session.execute(select(func.count(ScheduledTask.id)))
            total_tasks = total_result.scalar()
            
            # 按状态统计
            active_result = await session.execute(
                select(func.count(ScheduledTask.id)).where(ScheduledTask.status == 'active')
            )
            active_tasks = active_result.scalar()
            
            paused_result = await session.execute(
                select(func.count(ScheduledTask.id)).where(ScheduledTask.status == 'paused')
            )
            paused_tasks = paused_result.scalar()
            
            disabled_result = await session.execute(
                select(func.count(ScheduledTask.id)).where(ScheduledTask.status == 'disabled')
            )
            disabled_tasks = disabled_result.scalar()
            
            # 执行统计
            total_exec_result = await session.execute(select(func.sum(ScheduledTask.total_executions)))
            total_executions = total_exec_result.scalar() or 0
            
            success_exec_result = await session.execute(select(func.sum(ScheduledTask.successful_executions)))
            successful_executions = success_exec_result.scalar() or 0
            
            failed_exec_result = await session.execute(select(func.sum(ScheduledTask.failed_executions)))
            failed_executions = failed_exec_result.scalar() or 0
            
            # 计算成功率
            success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
            
            # 最活跃的任务
            most_active_result = await session.execute(
                select(ScheduledTask)
                .order_by(ScheduledTask.total_executions.desc())
                .limit(5)
            )
            most_active_tasks = [
                {
                    "id": task.id,
                    "name": task.name,
                    "total_executions": task.total_executions,
                    "success_rate": (task.successful_executions / task.total_executions * 100) if task.total_executions > 0 else 0
                }
                for task in most_active_result.scalars().all()
            ]
            
            # 最近执行记录
            recent_exec_result = await session.execute(
                select(TaskExecution)
                .order_by(TaskExecution.created_at.desc())
                .limit(5)
            )
            recent_executions = [
                {
                    "id": exec.id,
                    "task_id": exec.task_id,
                    "status": exec.status,
                    "created_at": exec.created_at.isoformat(),
                    "duration_seconds": exec.duration_seconds
                }
                for exec in recent_exec_result.scalars().all()
            ]
            
            # 构建统计结果
            stats = TaskStatistics(
                total_tasks=total_tasks,
                active_tasks=active_tasks,
                paused_tasks=paused_tasks,
                disabled_tasks=disabled_tasks,
                total_executions=total_executions,
                successful_executions=successful_executions,
                failed_executions=failed_executions,
                success_rate=round(success_rate, 2),
                most_active_tasks=most_active_tasks,
                recent_executions=recent_executions
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"获取任务统计信息失败: {e}")
            raise
    
    async def get_active_tasks(self, session: AsyncSession) -> List[ScheduledTask]:
        """获取所有活跃的任务"""
        try:
            result = await session.execute(
                select(ScheduledTask)
                .where(
                    and_(
                        ScheduledTask.status == 'active',
                        ScheduledTask.is_enabled == True
                    )
                )
                .order_by(ScheduledTask.next_execution_time.asc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"获取活跃任务失败: {e}")
            raise
    
    async def get_tasks_to_execute(self, session: AsyncSession, current_time: datetime) -> List[ScheduledTask]:
        """获取需要执行的任务"""
        try:
            result = await session.execute(
                select(ScheduledTask)
                .where(
                    and_(
                        ScheduledTask.status == 'active',
                        ScheduledTask.is_enabled == True,
                        ScheduledTask.next_execution_time <= current_time,
                        or_(
                            ScheduledTask.end_time.is_(None),
                            ScheduledTask.end_time > current_time
                        )
                    )
                )
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"获取待执行任务失败: {e}")
            raise
    
    async def update_execution_stats(self, session: AsyncSession, task_id: str, 
                                   execution_status: str, next_execution_time: Optional[datetime] = None):
        """更新任务执行统计"""
        try:
            # 获取当前任务
            task = await self.get_by_id(session, task_id)
            if not task:
                raise ValueError(f"任务不存在: {task_id}")
            
            # 更新统计数据
            updates = {
                'total_executions': task.total_executions + 1,
                'last_execution_time': datetime.now(),
                'last_execution_status': execution_status
            }
            
            if execution_status == 'completed':
                updates['successful_executions'] = task.successful_executions + 1
            elif execution_status in ['failed', 'timeout', 'cancelled']:
                updates['failed_executions'] = task.failed_executions + 1
            
            if next_execution_time:
                updates['next_execution_time'] = next_execution_time
            
            # 执行更新
            await session.execute(
                update(ScheduledTask)
                .where(ScheduledTask.id == task_id)
                .values(**updates)
            )
            
        except Exception as e:
            logger.error(f"更新任务执行统计失败: {task_id} - {e}")
            raise
    
    async def get_by_script_id(self, session: AsyncSession, script_id: str) -> List[ScheduledTask]:
        """根据脚本ID获取任务"""
        try:
            result = await session.execute(
                select(ScheduledTask)
                .where(ScheduledTask.script_id == script_id)
                .order_by(ScheduledTask.created_at.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"根据脚本ID获取任务失败: {e}")
            raise


class TaskExecutionRepository(BaseRepository[TaskExecution]):
    """任务执行记录仓库"""
    
    def __init__(self):
        super().__init__(TaskExecution)
    
    async def get_by_task_id(self, session: AsyncSession, task_id: str, limit: int = 20) -> List[TaskExecution]:
        """根据任务ID获取执行记录"""
        try:
            result = await session.execute(
                select(TaskExecution)
                .where(TaskExecution.task_id == task_id)
                .order_by(TaskExecution.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"根据任务ID获取执行记录失败: {e}")
            raise
    
    async def get_recent_executions(self, session: AsyncSession, limit: int = 50) -> List[TaskExecution]:
        """获取最近的执行记录"""
        try:
            result = await session.execute(
                select(TaskExecution)
                .order_by(TaskExecution.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"获取最近执行记录失败: {e}")
            raise

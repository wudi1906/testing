"""
定时任务调度服务
基于APScheduler实现的任务调度器
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from app.core.logging import get_logger
from app.database.connection import db_manager
from app.database.repositories.scheduled_task_repository import ScheduledTaskRepository, TaskExecutionRepository
from app.models.scheduled_tasks import ScheduledTask, TaskExecution, ScheduleType, ExecutionStatus, TriggerType
from app.services.database_script_service import database_script_service

logger = get_logger(__name__)


class TaskSchedulerService:
    """定时任务调度服务"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.task_repo = ScheduledTaskRepository()
        self.execution_repo = TaskExecutionRepository()
        self._running_executions: Dict[str, Dict[str, Any]] = {}  # 正在运行的执行记录
        
    async def initialize(self):
        """初始化调度器"""
        try:
            # 配置调度器
            jobstores = {
                'default': MemoryJobStore()
            }
            executors = {
                'default': AsyncIOExecutor()
            }
            job_defaults = {
                'coalesce': False,
                'max_instances': 3,
                'misfire_grace_time': 30
            }
            
            self.scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone='Asia/Shanghai'
            )
            
            # 启动调度器
            self.scheduler.start()
            logger.info("定时任务调度器启动成功")
            
            # 加载现有的活跃任务
            await self._load_active_tasks()
            
        except Exception as e:
            logger.error(f"初始化定时任务调度器失败: {e}")
            raise
    
    async def shutdown(self):
        """关闭调度器"""
        try:
            if self.scheduler:
                self.scheduler.shutdown(wait=True)
                logger.info("定时任务调度器已关闭")
        except Exception as e:
            logger.error(f"关闭定时任务调度器失败: {e}")
    
    async def add_task(self, task: ScheduledTask) -> bool:
        """添加定时任务到调度器"""
        try:
            if not self.scheduler:
                logger.error("调度器未初始化")
                return False
            
            # 根据调度类型创建触发器
            trigger = self._create_trigger(task)
            if not trigger:
                logger.error(f"无法创建触发器: {task.id}")
                return False
            
            # 添加任务到调度器
            self.scheduler.add_job(
                func=self._execute_task,
                trigger=trigger,
                args=[task.id],
                id=task.id,
                name=task.name,
                replace_existing=True
            )
            
            # 更新下次执行时间
            await self._update_next_execution_time(task.id)
            
            logger.info(f"定时任务已添加到调度器: {task.name} ({task.id})")
            return True
            
        except Exception as e:
            logger.error(f"添加定时任务失败: {task.id} - {e}")
            return False
    
    async def remove_task(self, task_id: str) -> bool:
        """从调度器中移除任务"""
        try:
            if not self.scheduler:
                logger.error("调度器未初始化")
                return False
            
            self.scheduler.remove_job(task_id)
            logger.info(f"定时任务已从调度器移除: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"移除定时任务失败: {task_id} - {e}")
            return False
    
    async def pause_task(self, task_id: str) -> bool:
        """暂停任务"""
        try:
            if not self.scheduler:
                logger.error("调度器未初始化")
                return False
            
            self.scheduler.pause_job(task_id)
            logger.info(f"定时任务已暂停: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"暂停定时任务失败: {task_id} - {e}")
            return False
    
    async def resume_task(self, task_id: str) -> bool:
        """恢复任务"""
        try:
            if not self.scheduler:
                logger.error("调度器未初始化")
                return False
            
            self.scheduler.resume_job(task_id)
            
            # 更新下次执行时间
            await self._update_next_execution_time(task_id)
            
            logger.info(f"定时任务已恢复: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"恢复定时任务失败: {task_id} - {e}")
            return False
    
    async def execute_task_manually(self, task_id: str, execution_config: Optional[Dict[str, Any]] = None) -> str:
        """手动执行任务"""
        try:
            execution_id = str(uuid.uuid4())
            
            # 创建执行记录
            async with db_manager.get_session() as session:
                task = await self.task_repo.get_by_id(session, task_id)
                if not task:
                    raise ValueError(f"任务不存在: {task_id}")
                
                # 合并执行配置
                final_config = task.execution_config or {}
                if execution_config:
                    final_config.update(execution_config)
                
                execution = await self.execution_repo.create(session,
                    id=execution_id,
                    task_id=task_id,
                    script_id=task.script_id,
                    trigger_type=TriggerType.MANUAL,
                    execution_config=final_config,
                    environment_variables=task.environment_variables,
                    status=ExecutionStatus.PENDING,
                    scheduled_time=datetime.now()
                )
                await session.commit()
            
            # 异步执行任务
            asyncio.create_task(self._execute_task_by_execution_id(execution_id))
            
            logger.info(f"手动执行任务已启动: {task_id} -> {execution_id}")
            return execution_id
            
        except Exception as e:
            logger.error(f"手动执行任务失败: {task_id} - {e}")
            raise
    
    def _create_trigger(self, task: ScheduledTask):
        """根据任务配置创建触发器"""
        try:
            if task.schedule_type == ScheduleType.CRON:
                if not task.cron_expression:
                    logger.error(f"Cron任务缺少表达式: {task.id}")
                    return None
                return CronTrigger.from_crontab(task.cron_expression)
            
            elif task.schedule_type == ScheduleType.INTERVAL:
                if not task.interval_seconds:
                    logger.error(f"间隔任务缺少间隔时间: {task.id}")
                    return None
                return IntervalTrigger(seconds=task.interval_seconds)
            
            elif task.schedule_type == ScheduleType.ONCE:
                if not task.scheduled_time:
                    logger.error(f"一次性任务缺少执行时间: {task.id}")
                    return None
                return DateTrigger(run_date=task.scheduled_time)
            
            else:
                logger.error(f"不支持的调度类型: {task.schedule_type}")
                return None
                
        except Exception as e:
            logger.error(f"创建触发器失败: {task.id} - {e}")
            return None
    
    async def _execute_task(self, task_id: str):
        """执行定时任务"""
        execution_id = str(uuid.uuid4())
        
        try:
            # 创建执行记录
            async with db_manager.get_session() as session:
                task = await self.task_repo.get_by_id(session, task_id)
                if not task:
                    logger.error(f"任务不存在: {task_id}")
                    return
                
                execution = await self.execution_repo.create(session,
                    id=execution_id,
                    task_id=task_id,
                    script_id=task.script_id,
                    trigger_type=TriggerType.SCHEDULED,
                    execution_config=task.execution_config,
                    environment_variables=task.environment_variables,
                    status=ExecutionStatus.PENDING,
                    scheduled_time=datetime.now()
                )
                await session.commit()
            
            # 执行任务
            await self._execute_task_by_execution_id(execution_id)
            
        except Exception as e:
            logger.error(f"执行定时任务失败: {task_id} - {e}")
            
            # 更新执行记录为失败状态
            try:
                async with db_manager.get_session() as session:
                    await self.execution_repo.update(session, execution_id,
                        status=ExecutionStatus.FAILED,
                        error_message=str(e),
                        end_time=datetime.now()
                    )
                    await session.commit()
            except Exception as update_error:
                logger.error(f"更新执行记录失败: {execution_id} - {update_error}")
    
    async def _execute_task_by_execution_id(self, execution_id: str):
        """根据执行ID执行任务"""
        try:
            # 获取执行记录
            async with db_manager.get_session() as session:
                execution = await self.execution_repo.get_by_id(session, execution_id)
                if not execution:
                    logger.error(f"执行记录不存在: {execution_id}")
                    return
                
                task = await self.task_repo.get_by_id(session, execution.task_id)
                if not task:
                    logger.error(f"任务不存在: {execution.task_id}")
                    return
            
            # 更新执行状态为运行中
            async with db_manager.get_session() as session:
                await self.execution_repo.update(session, execution_id,
                    status=ExecutionStatus.RUNNING,
                    start_time=datetime.now()
                )
                await session.commit()
            
            # 记录运行状态
            self._running_executions[execution_id] = {
                'task_id': execution.task_id,
                'script_id': execution.script_id,
                'start_time': datetime.now()
            }
            
            # 执行脚本
            script_execution_result = await database_script_service.execute_script(
                script_id=execution.script_id,
                execution_config=execution.execution_config or {},
                environment_variables=execution.environment_variables or {}
            )
            
            # 更新执行结果
            end_time = datetime.now()
            duration = int((end_time - execution.start_time).total_seconds()) if execution.start_time else 0
            
            async with db_manager.get_session() as session:
                await self.execution_repo.update(session, execution_id,
                    status=ExecutionStatus.COMPLETED,
                    end_time=end_time,
                    duration_seconds=duration,
                    session_id=script_execution_result.get('session_id'),
                    execution_id=script_execution_result.get('execution_id')
                )
                
                # 更新任务统计
                await self.task_repo.update_execution_stats(
                    session, execution.task_id, ExecutionStatus.COMPLETED
                )
                
                await session.commit()
            
            logger.info(f"定时任务执行完成: {execution.task_id} -> {execution_id}")
            
        except Exception as e:
            logger.error(f"执行任务失败: {execution_id} - {e}")
            
            # 更新执行记录为失败状态
            try:
                end_time = datetime.now()
                start_time = self._running_executions.get(execution_id, {}).get('start_time', end_time)
                duration = int((end_time - start_time).total_seconds())
                
                async with db_manager.get_session() as session:
                    await self.execution_repo.update(session, execution_id,
                        status=ExecutionStatus.FAILED,
                        error_message=str(e),
                        end_time=end_time,
                        duration_seconds=duration
                    )
                    
                    # 更新任务统计
                    execution = await self.execution_repo.get_by_id(session, execution_id)
                    if execution:
                        await self.task_repo.update_execution_stats(
                            session, execution.task_id, ExecutionStatus.FAILED
                        )
                    
                    await session.commit()
            except Exception as update_error:
                logger.error(f"更新失败执行记录失败: {execution_id} - {update_error}")
        
        finally:
            # 清理运行状态
            self._running_executions.pop(execution_id, None)
    
    async def _load_active_tasks(self):
        """加载现有的活跃任务"""
        try:
            async with db_manager.get_session() as session:
                active_tasks = await self.task_repo.get_active_tasks(session)
                
                for task in active_tasks:
                    await self.add_task(task)
                
                logger.info(f"已加载 {len(active_tasks)} 个活跃定时任务")
                
        except Exception as e:
            logger.error(f"加载活跃任务失败: {e}")
    
    async def _update_next_execution_time(self, task_id: str):
        """更新任务的下次执行时间"""
        try:
            if not self.scheduler:
                return
            
            job = self.scheduler.get_job(task_id)
            if job and job.next_run_time:
                async with db_manager.get_session() as session:
                    await self.task_repo.update(session, task_id,
                        next_execution_time=job.next_run_time
                    )
                    await session.commit()
                    
        except Exception as e:
            logger.error(f"更新下次执行时间失败: {task_id} - {e}")


# 全局任务调度器实例
task_scheduler = TaskSchedulerService()

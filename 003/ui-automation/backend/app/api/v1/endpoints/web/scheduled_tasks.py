"""
Web平台定时任务管理API端点
提供定时任务的CRUD操作、调度管理等功能
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.scheduled_tasks import (
    ScheduledTaskCreate, ScheduledTaskUpdate, ScheduledTask, TaskExecution,
    TaskSearchRequest, TaskSearchResponse, TaskStatistics, 
    TaskExecutionRequest, TaskExecutionResponse
)
from app.services.scheduled_task_service import scheduled_task_service
from app.services.task_scheduler_service import task_scheduler
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/scheduled-tasks", response_model=ScheduledTask)
async def create_scheduled_task(request: ScheduledTaskCreate):
    """创建定时任务"""
    try:
        task = await scheduled_task_service.create_task(request)
        
        # 如果任务是活跃状态，添加到调度器
        if task.status == 'active' and task.is_enabled:
            await task_scheduler.add_task(task)
        
        logger.info(f"定时任务创建成功: {task.name} ({task.id})")
        return task
        
    except Exception as e:
        logger.error(f"创建定时任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建定时任务失败: {str(e)}")


@router.get("/scheduled-tasks/search", response_model=TaskSearchResponse)
async def search_scheduled_tasks(
    query: Optional[str] = None,
    script_id: Optional[str] = None,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    schedule_type: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    created_by: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_order: str = "desc"
):
    """搜索定时任务"""
    try:
        search_request = TaskSearchRequest(
            query=query,
            script_id=script_id,
            project_id=project_id,
            status=status,
            schedule_type=schedule_type,
            is_enabled=is_enabled,
            created_by=created_by,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        tasks, total = await scheduled_task_service.search_tasks(search_request)
        
        return TaskSearchResponse(
            tasks=tasks,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        logger.error(f"搜索定时任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索定时任务失败: {str(e)}")


@router.get("/scheduled-tasks/statistics", response_model=TaskStatistics)
async def get_task_statistics():
    """获取定时任务统计信息"""
    try:
        statistics = await scheduled_task_service.get_statistics()
        return statistics
        
    except Exception as e:
        logger.error(f"获取定时任务统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/scheduled-tasks/{task_id}", response_model=ScheduledTask)
async def get_scheduled_task(task_id: str):
    """获取定时任务详情"""
    try:
        task = await scheduled_task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"定时任务不存在: {task_id}")
        
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取定时任务失败: {task_id} - {e}")
        raise HTTPException(status_code=500, detail=f"获取定时任务失败: {str(e)}")


@router.put("/scheduled-tasks/{task_id}", response_model=ScheduledTask)
async def update_scheduled_task(task_id: str, request: ScheduledTaskUpdate):
    """更新定时任务"""
    try:
        # 获取原任务信息
        old_task = await scheduled_task_service.get_task(task_id)
        if not old_task:
            raise HTTPException(status_code=404, detail=f"定时任务不存在: {task_id}")
        
        # 更新任务
        updated_task = await scheduled_task_service.update_task(task_id, request)
        
        # 更新调度器中的任务
        if updated_task.status == 'active' and updated_task.is_enabled:
            await task_scheduler.add_task(updated_task)  # add_job会替换现有任务
        else:
            await task_scheduler.remove_task(task_id)
        
        logger.info(f"定时任务更新成功: {updated_task.name} ({task_id})")
        return updated_task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新定时任务失败: {task_id} - {e}")
        raise HTTPException(status_code=500, detail=f"更新定时任务失败: {str(e)}")


@router.delete("/scheduled-tasks/{task_id}")
async def delete_scheduled_task(task_id: str):
    """删除定时任务"""
    try:
        # 检查任务是否存在
        task = await scheduled_task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"定时任务不存在: {task_id}")
        
        # 从调度器中移除
        await task_scheduler.remove_task(task_id)
        
        # 删除任务
        success = await scheduled_task_service.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=500, detail="删除定时任务失败")
        
        logger.info(f"定时任务删除成功: {task.name} ({task_id})")
        return JSONResponse({"message": "定时任务删除成功"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除定时任务失败: {task_id} - {e}")
        raise HTTPException(status_code=500, detail=f"删除定时任务失败: {str(e)}")


@router.post("/scheduled-tasks/{task_id}/execute", response_model=TaskExecutionResponse)
async def execute_scheduled_task(task_id: str, request: TaskExecutionRequest):
    """手动执行定时任务"""
    try:
        # 检查任务是否存在
        task = await scheduled_task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"定时任务不存在: {task_id}")
        
        # 执行任务
        execution_id = await task_scheduler.execute_task_manually(
            task_id, request.execution_config
        )
        
        response = TaskExecutionResponse(
            execution_id=execution_id,
            task_id=task_id,
            script_id=task.script_id,
            session_id=execution_id,  # 使用execution_id作为session_id
            status="pending",
            message="定时任务手动执行已启动",
            sse_endpoint=f"/api/v1/web/execution/stream/{execution_id}",
            created_at=datetime.now()
        )
        
        logger.info(f"定时任务手动执行启动: {task.name} ({task_id}) -> {execution_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动执行定时任务失败: {task_id} - {e}")
        raise HTTPException(status_code=500, detail=f"手动执行定时任务失败: {str(e)}")


@router.post("/scheduled-tasks/{task_id}/pause")
async def pause_scheduled_task(task_id: str):
    """暂停定时任务"""
    try:
        # 检查任务是否存在
        task = await scheduled_task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"定时任务不存在: {task_id}")
        
        # 更新任务状态
        await scheduled_task_service.update_task(task_id, ScheduledTaskUpdate(status='paused'))
        
        # 暂停调度器中的任务
        await task_scheduler.pause_task(task_id)
        
        logger.info(f"定时任务已暂停: {task.name} ({task_id})")
        return JSONResponse({"message": "定时任务已暂停"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"暂停定时任务失败: {task_id} - {e}")
        raise HTTPException(status_code=500, detail=f"暂停定时任务失败: {str(e)}")


@router.post("/scheduled-tasks/{task_id}/resume")
async def resume_scheduled_task(task_id: str):
    """恢复定时任务"""
    try:
        # 检查任务是否存在
        task = await scheduled_task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"定时任务不存在: {task_id}")
        
        # 更新任务状态
        await scheduled_task_service.update_task(task_id, ScheduledTaskUpdate(status='active'))
        
        # 恢复调度器中的任务
        await task_scheduler.resume_task(task_id)
        
        logger.info(f"定时任务已恢复: {task.name} ({task_id})")
        return JSONResponse({"message": "定时任务已恢复"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复定时任务失败: {task_id} - {e}")
        raise HTTPException(status_code=500, detail=f"恢复定时任务失败: {str(e)}")


@router.post("/scheduled-tasks/{task_id}/enable")
async def enable_scheduled_task(task_id: str):
    """启用定时任务"""
    try:
        # 检查任务是否存在
        task = await scheduled_task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"定时任务不存在: {task_id}")
        
        # 更新任务状态
        updated_task = await scheduled_task_service.update_task(
            task_id, ScheduledTaskUpdate(is_enabled=True, status='active')
        )
        
        # 添加到调度器
        await task_scheduler.add_task(updated_task)
        
        logger.info(f"定时任务已启用: {task.name} ({task_id})")
        return JSONResponse({"message": "定时任务已启用"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启用定时任务失败: {task_id} - {e}")
        raise HTTPException(status_code=500, detail=f"启用定时任务失败: {str(e)}")


@router.post("/scheduled-tasks/{task_id}/disable")
async def disable_scheduled_task(task_id: str):
    """禁用定时任务"""
    try:
        # 检查任务是否存在
        task = await scheduled_task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"定时任务不存在: {task_id}")
        
        # 更新任务状态
        await scheduled_task_service.update_task(
            task_id, ScheduledTaskUpdate(is_enabled=False, status='disabled')
        )
        
        # 从调度器中移除
        await task_scheduler.remove_task(task_id)
        
        logger.info(f"定时任务已禁用: {task.name} ({task_id})")
        return JSONResponse({"message": "定时任务已禁用"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"禁用定时任务失败: {task_id} - {e}")
        raise HTTPException(status_code=500, detail=f"禁用定时任务失败: {str(e)}")


@router.get("/scheduled-tasks/{task_id}/executions", response_model=List[TaskExecution])
async def get_task_executions(task_id: str, limit: int = 20):
    """获取任务执行历史"""
    try:
        # 检查任务是否存在
        task = await scheduled_task_service.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"定时任务不存在: {task_id}")
        
        executions = await scheduled_task_service.get_task_executions(task_id, limit)
        return executions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务执行历史失败: {task_id} - {e}")
        raise HTTPException(status_code=500, detail=f"获取执行历史失败: {str(e)}")


@router.get("/scheduled-tasks/script/{script_id}", response_model=List[ScheduledTask])
async def get_tasks_by_script(script_id: str):
    """根据脚本ID获取定时任务"""
    try:
        tasks = await scheduled_task_service.get_tasks_by_script_id(script_id)
        return tasks
        
    except Exception as e:
        logger.error(f"根据脚本ID获取定时任务失败: {script_id} - {e}")
        raise HTTPException(status_code=500, detail=f"获取定时任务失败: {str(e)}")


@router.get("/task-executions/recent", response_model=List[TaskExecution])
async def get_recent_executions(limit: int = 50):
    """获取最近的任务执行记录"""
    try:
        executions = await scheduled_task_service.get_recent_executions(limit)
        return executions
        
    except Exception as e:
        logger.error(f"获取最近执行记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取执行记录失败: {str(e)}")

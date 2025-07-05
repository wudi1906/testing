"""
测试执行历史API接口
提供脚本执行历史的查询和管理功能
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.services.execution_history_service import execution_history_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/execution/history")
async def get_execution_history(
    limit: int = Query(50, ge=1, le=200, description="返回记录数量限制"),
    status: Optional[str] = Query(None, description="状态过滤"),
    script_id: Optional[str] = Query(None, description="脚本ID过滤")
):
    """获取YAML脚本执行历史
    
    Args:
        limit: 返回记录数量限制
        status: 状态过滤 (pending, running, completed, failed, cancelled)
        script_id: 脚本ID过滤
        
    Returns:
        执行历史记录列表
    """
    try:
        result = await execution_history_service.get_execution_history(
            limit=limit,
            script_type="yaml",  # 过滤YAML脚本
            status=status,
            script_id=script_id
        )
        
        return JSONResponse({
            "history": result["history"],
            "count": result["count"],
            "total_available": result["total_available"],
            "timestamp": result["timestamp"]
        })
        
    except Exception as e:
        logger.error(f"获取YAML执行历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取执行历史失败: {str(e)}")


@router.get("/playwright/executions/history")
async def get_playwright_execution_history(
    limit: int = Query(50, ge=1, le=200, description="返回记录数量限制"),
    status: Optional[str] = Query(None, description="状态过滤"),
    script_id: Optional[str] = Query(None, description="脚本ID过滤")
):
    """获取Playwright脚本执行历史
    
    Args:
        limit: 返回记录数量限制
        status: 状态过滤 (pending, running, completed, failed, cancelled)
        script_id: 脚本ID过滤
        
    Returns:
        执行历史记录列表
    """
    try:
        result = await execution_history_service.get_execution_history(
            limit=limit,
            script_type="playwright",  # 过滤Playwright脚本
            status=status,
            script_id=script_id
        )
        
        return JSONResponse({
            "history": result["history"],
            "count": result["count"],
            "total_available": result["total_available"],
            "timestamp": result["timestamp"]
        })
        
    except Exception as e:
        logger.error(f"获取Playwright执行历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取执行历史失败: {str(e)}")


@router.get("/execution/active")
async def get_active_executions():
    """获取活跃的YAML脚本执行记录
    
    Returns:
        活跃执行记录列表
    """
    try:
        result = await execution_history_service.get_active_executions(
            script_type="yaml"  # 过滤YAML脚本
        )
        
        return JSONResponse({
            "active_executions": result["active_executions"],
            "count": result["count"],
            "timestamp": result["timestamp"]
        })
        
    except Exception as e:
        logger.error(f"获取活跃YAML执行记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取活跃执行记录失败: {str(e)}")


@router.get("/playwright/executions/active")
async def get_active_playwright_executions():
    """获取活跃的Playwright脚本执行记录
    
    Returns:
        活跃执行记录列表
    """
    try:
        result = await execution_history_service.get_active_executions(
            script_type="playwright"  # 过滤Playwright脚本
        )
        
        return JSONResponse({
            "active_executions": result["active_executions"],
            "count": result["count"],
            "timestamp": result["timestamp"]
        })
        
    except Exception as e:
        logger.error(f"获取活跃Playwright执行记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取活跃执行记录失败: {str(e)}")


@router.get("/execution/status/{execution_id}")
async def get_execution_status(execution_id: str):
    """获取指定执行的状态信息
    
    Args:
        execution_id: 执行ID
        
    Returns:
        执行状态信息
    """
    try:
        # 通过执行ID查询单个执行记录
        result = await execution_history_service.get_execution_history(
            limit=1,
            execution_id=execution_id
        )

        if not result["history"]:
            raise HTTPException(status_code=404, detail=f"未找到执行ID {execution_id} 的记录")

        execution = result["history"][0]
        
        return JSONResponse({
            "execution_id": execution["execution_id"],
            "status": execution["status"],
            "start_time": execution["start_time"],
            "end_time": execution["end_time"],
            "duration": execution["duration"],
            "error_message": execution["error_message"],
            "script_name": execution["script_name"],
            "script_type": execution["script_type"],
            "timestamp": result["timestamp"]
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取执行状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取执行状态失败: {str(e)}")


@router.get("/execution/logs/{execution_id}")
async def get_execution_logs(execution_id: str):
    """获取指定执行的日志信息
    
    Args:
        execution_id: 执行ID
        
    Returns:
        执行日志信息
    """
    try:
        # 这里可以扩展为从日志表或文件中获取详细日志
        # 目前返回基本的执行信息
        result = await execution_history_service.get_execution_history(
            limit=1,
            execution_id=execution_id
        )

        if not result["history"]:
            raise HTTPException(status_code=404, detail=f"未找到执行ID {execution_id} 的记录")

        execution = result["history"][0]
        
        # 构造日志信息
        logs = []
        if execution["start_time"]:
            logs.append(f"[{execution['start_time']}] 开始执行脚本: {execution['script_name']}")
        
        if execution["status"] == "completed":
            logs.append(f"[{execution['end_time']}] 脚本执行完成")
        elif execution["status"] == "failed":
            logs.append(f"[{execution['end_time']}] 脚本执行失败")
            if execution["error_message"]:
                logs.append(f"错误信息: {execution['error_message']}")
        elif execution["status"] == "running":
            logs.append("脚本正在执行中...")
        
        return JSONResponse({
            "execution_id": execution_id,
            "logs": logs,
            "timestamp": result["timestamp"]
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取执行日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取执行日志失败: {str(e)}")


@router.get("/execution/results/{execution_id}")
async def get_execution_results(execution_id: str):
    """获取指定执行的结果信息
    
    Args:
        execution_id: 执行ID
        
    Returns:
        执行结果信息
    """
    try:
        result = await execution_history_service.get_execution_history(
            limit=1,
            execution_id=execution_id
        )

        if not result["history"]:
            raise HTTPException(status_code=404, detail=f"未找到执行ID {execution_id} 的记录")

        execution = result["history"][0]
        
        return JSONResponse({
            "execution_id": execution_id,
            "results": {
                "status": execution["status"],
                "duration": execution["duration"],
                "exit_code": execution["exit_code"],
                "error_message": execution["error_message"],
                "performance_metrics": execution["performance_metrics"],
                "execution_config": execution["execution_config"],
                "environment_info": execution["environment_info"]
            },
            "timestamp": result["timestamp"]
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取执行结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取执行结果失败: {str(e)}")


@router.delete("/execution/cleanup/{execution_id}")
async def cleanup_execution(execution_id: str):
    """清理指定执行的数据

    Args:
        execution_id: 执行ID

    Returns:
        清理结果
    """
    try:
        # 实际删除数据库中的执行记录
        deleted_count = await execution_history_service.delete_execution_record(execution_id)

        if deleted_count > 0:
            return JSONResponse({
                "message": f"执行记录 {execution_id} 清理完成",
                "execution_id": execution_id,
                "deleted_count": deleted_count,
                "timestamp": datetime.now().isoformat()
            })
        else:
            raise HTTPException(status_code=404, detail=f"未找到执行ID {execution_id} 的记录")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理执行数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清理执行数据失败: {str(e)}")

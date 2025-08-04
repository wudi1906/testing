"""
脚本管理API模块
专门处理测试脚本的管理和执行功能

主要功能：
1. 脚本查询和详情获取
2. 脚本状态管理
3. 脚本执行和监控
4. 执行历史和日志管理
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger

from app.services.api_automation.interface_script_service import InterfaceScriptService

router = APIRouter(tags=["脚本管理"])

# ==================== 请求和响应模型 ====================

class ScriptExecutionRequest(BaseModel):
    """脚本执行请求"""
    script_ids: List[str] = Field(..., description="要执行的脚本ID列表")
    execution_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="执行配置")
    environment: str = Field(default="test", description="执行环境")
    timeout: int = Field(default=300, description="超时时间（秒）")
    parallel: bool = Field(default=False, description="是否并行执行")
    max_workers: int = Field(default=1, description="最大并行数")


class SingleScriptExecutionRequest(BaseModel):
    """单个脚本执行请求"""
    execution_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="执行配置")
    environment: str = Field(default="test", description="执行环境")
    timeout: int = Field(default=300, description="超时时间（秒）")


class ScriptStatusUpdateRequest(BaseModel):
    """脚本状态更新请求"""
    status: str = Field(..., description="新状态")
    is_executable: Optional[bool] = Field(None, description="是否可执行")


class BatchScriptStatusUpdateRequest(BaseModel):
    """批量脚本状态更新请求"""
    script_ids: List[str] = Field(..., description="脚本ID列表")
    status: str = Field(..., description="新状态")
    is_executable: Optional[bool] = Field(None, description="是否可执行")


# ==================== 接口脚本查询API ====================

@router.get("/interfaces/{interface_id}/scripts", summary="获取接口的所有脚本")
async def get_interface_scripts(
    interface_id: str,
    include_inactive: bool = Query(False, description="是否包含非活跃脚本")
):
    """获取指定接口的所有测试脚本"""
    try:
        script_service = InterfaceScriptService()
        result = await script_service.get_interface_scripts(interface_id, include_inactive)

        return {
            "code": 200,
            "msg": "OK",
            "data": result,
            "success": True
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取接口脚本失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取接口脚本失败: {str(e)}")


@router.get("/interfaces/{interface_id}/scripts/statistics", summary="获取接口脚本统计")
async def get_interface_script_statistics(interface_id: str):
    """获取接口的脚本统计信息"""
    try:
        script_service = InterfaceScriptService()
        result = await script_service.get_interface_script_statistics(interface_id)

        return {
            "code": 200,
            "msg": "OK",
            "data": result,
            "success": True
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取接口脚本统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取接口脚本统计失败: {str(e)}")


@router.get("/interfaces/{interface_id}/scripts/generation-history", summary="获取脚本生成历史")
async def get_script_generation_history(
    interface_id: str,
    limit: int = Query(10, description="返回记录数量限制")
):
    """获取接口的脚本生成历史"""
    try:
        script_service = InterfaceScriptService()
        result = await script_service.get_script_generation_history(interface_id, limit)

        return {
            "code": 200,
            "msg": "OK",
            "data": result,
            "success": True
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取脚本生成历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取脚本生成历史失败: {str(e)}")


@router.get("/documents/{document_id}/scripts/overview", summary="获取文档脚本概览")
async def get_document_script_overview(document_id: str):
    """获取文档的脚本概览信息"""
    try:
        script_service = InterfaceScriptService()
        result = await script_service.get_document_script_overview(document_id)

        return {
            "code": 200,
            "msg": "OK",
            "data": result,
            "success": True
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取文档脚本概览失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档脚本概览失败: {str(e)}")


@router.get("/", summary="获取所有脚本列表")
async def get_all_scripts(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="状态筛选"),
    framework: Optional[str] = Query(None, description="框架筛选"),
    interface_id: Optional[str] = Query(None, description="接口ID筛选"),
    document_id: Optional[str] = Query(None, description="文档ID筛选"),
    include_inactive: bool = Query(False, description="是否包含非活跃脚本")
):
    """获取所有测试脚本列表，支持分页和筛选"""
    try:
        script_service = InterfaceScriptService()
        result = await script_service.get_all_scripts(
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            framework=framework,
            interface_id=interface_id,
            document_id=document_id,
            include_inactive=include_inactive
        )

        return {
            "code": 200,
            "msg": "OK",
            "data": result,
            "success": True
        }

    except Exception as e:
        logger.error(f"获取脚本列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取脚本列表失败: {str(e)}")


# ==================== 脚本基础管理API ====================

@router.get("/{script_id}", summary="获取脚本详细信息")
async def get_script_detail(script_id: str):
    """获取测试脚本的详细信息"""
    try:
        script_service = InterfaceScriptService()
        result = await script_service.get_script_detail(script_id)

        return {
            "code": 200,
            "msg": "OK",
            "data": result,
            "success": True
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取脚本详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取脚本详情失败: {str(e)}")


@router.put("/{script_id}/status", summary="更新脚本状态")
async def update_script_status(script_id: str, request: ScriptStatusUpdateRequest):
    """更新测试脚本的状态"""
    try:
        script_service = InterfaceScriptService()
        success = await script_service.update_script_status(
            script_id=script_id,
            status=request.status,
            is_executable=request.is_executable
        )

        return {
            "code": 200,
            "msg": "脚本状态更新成功",
            "success": success
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"更新脚本状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新脚本状态失败: {str(e)}")


@router.delete("/{script_id}", summary="删除脚本")
async def delete_script(
    script_id: str,
    soft_delete: bool = Query(True, description="是否软删除")
):
    """删除测试脚本"""
    try:
        script_service = InterfaceScriptService()
        success = await script_service.delete_script(script_id, soft_delete)

        return {
            "code": 200,
            "msg": "脚本删除成功",
            "success": success
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"删除脚本失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除脚本失败: {str(e)}")


@router.put("/batch-status", summary="批量更新脚本状态")
async def batch_update_script_status(request: BatchScriptStatusUpdateRequest):
    """批量更新脚本状态"""
    try:
        script_service = InterfaceScriptService()
        result = await script_service.batch_update_script_status(
            script_ids=request.script_ids,
            status=request.status,
            is_executable=request.is_executable
        )

        return {
            "code": 200,
            "msg": "OK",
            "data": result,
            "success": True
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"批量更新脚本状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量更新脚本状态失败: {str(e)}")


# ==================== 脚本执行API ====================

@router.post("/execute", summary="批量执行脚本")
async def execute_scripts(request: ScriptExecutionRequest):
    """执行指定的测试脚本"""
    try:
        script_service = InterfaceScriptService()
        result = await script_service.execute_scripts(
            script_ids=request.script_ids,
            execution_config=request.execution_config,
            environment=request.environment,
            timeout=request.timeout,
            parallel=request.parallel,
            max_workers=request.max_workers
        )

        return {
            "code": 200,
            "msg": "OK",
            "data": result,
            "success": True
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"执行脚本失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"执行脚本失败: {str(e)}")


@router.post("/{script_id}/execute", summary="执行单个脚本")
async def execute_single_script(script_id: str, request: SingleScriptExecutionRequest):
    """执行单个测试脚本 - 通过智能体执行"""
    try:
        # 导入智能体相关模块
        from app.agents.api_automation.schemas import TestExecutionInput, GeneratedScript
        from app.core.agents.runtime_manager import runtime_manager
        from app.core.types import TopicTypes
        from autogen_core import TopicId
        import uuid
        from datetime import datetime

        # 获取脚本详情
        script_service = InterfaceScriptService()
        script_detail = await script_service.get_script_detail(script_id)

        if not script_detail:
            raise ValueError(f"脚本不存在: {script_id}")

        # 准备脚本数据
        import tempfile
        import os

        # 创建跨平台的临时脚本路径
        temp_dir = tempfile.gettempdir()
        scripts_dir = os.path.join(temp_dir, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)  # 确保目录存在
        script_filename = f"{script_id}.py"
        script_file_path = os.path.join(scripts_dir, script_filename)

        script_data = GeneratedScript(
            script_id=script_id,
            script_name=script_detail.get("name", f"script_{script_id}"),
            file_path=script_file_path,
            script_content=script_detail.get("content", ""),
            framework=script_detail.get("framework", "pytest"),
            dependencies=script_detail.get("dependencies", [])
        )

        # 创建执行输入 - 修复字段名和参数
        # 将超时时间添加到执行配置中
        execution_config = request.execution_config or {}
        if request.timeout:
            execution_config["timeout"] = request.timeout

        execution_input = TestExecutionInput(
            session_id=str(uuid.uuid4()),
            document_id=script_detail.get("document_id", ""),
            scripts=[script_data],
            execution_config=execution_config,
            environment=request.environment,
            parallel=False,
            max_workers=1
        )

        # 获取运行时并发送消息给智能体
        runtime = await runtime_manager.get_runtime()

        # 发送执行请求到脚本执行智能体
        await runtime.publish_message(
            execution_input,
            topic_id=TopicId(type=TopicTypes.TEST_EXECUTOR.value, source="api")
        )

        # 返回执行已启动的响应
        return {
            "code": 200,
            "msg": "OK",
            "data": {
                "execution_id": execution_input.session_id,
                "script_id": script_id,
                "status": "STARTED",
                "message": "脚本执行已通过智能体启动",
                "start_time": datetime.now().isoformat()
            },
            "success": True
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"执行脚本失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"执行脚本失败: {str(e)}")


@router.get("/{script_id}/execution/{execution_id}", summary="获取脚本执行结果")
async def get_script_execution_result(script_id: str, execution_id: str):
    """获取脚本执行结果"""
    try:
        # 从响应收集器获取执行结果
        from app.core.agents.runtime_manager import runtime_manager

        collector = runtime_manager.get_response_collector()
        if not collector:
            raise HTTPException(status_code=500, detail="响应收集器未初始化")

        # 查找执行结果
        results = collector.get_results()
        execution_result = None

        for result_key, result_data in results.items():
            if (isinstance(result_data, dict) and
                result_data.get("session_id") == execution_id):
                execution_result = result_data
                break

        if execution_result:
            return {
                "code": 200,
                "msg": "OK",
                "data": execution_result,
                "success": True
            }
        else:
            # 如果没有找到结果，返回执行中状态
            return {
                "code": 200,
                "msg": "OK",
                "data": {
                    "execution_id": execution_id,
                    "script_id": script_id,
                    "status": "RUNNING",
                    "message": "脚本正在执行中..."
                },
                "success": True
            }

    except Exception as e:
        logger.error(f"获取执行结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取执行结果失败: {str(e)}")


# ==================== 执行历史和监控API ====================

@router.get("/{script_id}/executions", summary="获取脚本执行历史")
async def get_script_execution_history(
    script_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """获取脚本的执行历史记录"""
    try:
        script_service = InterfaceScriptService()
        result = await script_service.get_script_execution_history(
            script_id=script_id,
            page=page,
            page_size=page_size
        )

        return {
            "code": 200,
            "msg": "OK",
            "data": result,
            "success": True
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取脚本执行历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取脚本执行历史失败: {str(e)}")


# ==================== 执行详情和日志API ====================

@router.get("/executions/{execution_id}", summary="获取执行详情")
async def get_execution_detail(execution_id: str):
    """获取脚本执行的详细信息"""
    try:
        script_service = InterfaceScriptService()
        result = await script_service.get_execution_detail(execution_id)

        return {
            "code": 200,
            "msg": "OK",
            "data": result,
            "success": True
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取执行详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取执行详情失败: {str(e)}")


@router.get("/executions/{execution_id}/logs", summary="获取执行日志")
async def get_execution_logs(
    execution_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页数量")
):
    """获取脚本执行的日志信息"""
    try:
        script_service = InterfaceScriptService()
        result = await script_service.get_execution_logs(
            execution_id=execution_id,
            page=page,
            page_size=page_size
        )

        return {
            "code": 200,
            "msg": "OK",
            "data": result,
            "success": True
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取执行日志失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取执行日志失败: {str(e)}")


@router.post("/executions/{execution_id}/stop", summary="停止执行")
async def stop_execution(execution_id: str):
    """停止正在执行的脚本"""
    try:
        script_service = InterfaceScriptService()
        result = await script_service.stop_execution(execution_id)

        return {
            "code": 200,
            "msg": "OK",
            "data": result,
            "success": True
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"停止执行失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"停止执行失败: {str(e)}")

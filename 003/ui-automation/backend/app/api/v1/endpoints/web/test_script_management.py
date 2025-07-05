"""
Web平台脚本管理API端点
提供脚本的CRUD操作、搜索、执行等功能
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.models.test_scripts import (
    TestScript, ScriptFormat, ScriptType, ScriptSearchRequest,
    ScriptSearchResponse, ScriptStatistics, BatchExecutionRequest,
    BatchExecutionResponse, ScriptExecutionRecord
)
from app.services.database_script_service import database_script_service
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


class ScriptCreateRequest(BaseModel):
    """创建脚本请求"""
    session_id: str
    name: str
    description: str
    content: str
    script_format: ScriptFormat
    script_type: ScriptType
    test_description: str
    additional_context: Optional[str] = None
    source_url: Optional[str] = None
    source_image_path: Optional[str] = None
    analysis_result_id: Optional[str] = None
    tags: List[str] = []
    category: Optional[str] = None
    priority: int = 1


class ScriptUpdateRequest(BaseModel):
    """更新脚本请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    test_description: Optional[str] = None
    additional_context: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    priority: Optional[int] = None


class ScriptExecuteRequest(BaseModel):
    """执行脚本请求"""
    execution_config: Optional[Dict[str, Any]] = None
    environment_variables: Optional[Dict[str, Any]] = None


@router.post("/scripts", response_model=TestScript)
async def create_script(request: ScriptCreateRequest):
    """创建新脚本"""
    try:
        script = await database_script_service.create_script_from_analysis(
            session_id=request.session_id,
            name=request.name,
            description=request.description,
            content=request.content,
            script_format=request.script_format,
            script_type=request.script_type,
            test_description=request.test_description,
            additional_context=request.additional_context,
            source_url=request.source_url,
            source_image_path=request.source_image_path,
            analysis_result_id=request.analysis_result_id
        )

        # 设置额外属性并更新
        updates = {}
        if request.tags:
            updates['tags'] = request.tags
        if request.category:
            updates['category'] = request.category
        if request.priority:
            updates['priority'] = request.priority

        if updates:
            script = await database_script_service.update_script(script.id, updates)

        logger.info(f"脚本创建成功: {script.id} - {script.name}")
        return script

    except Exception as e:
        logger.error(f"创建脚本失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建脚本失败: {str(e)}")


@router.post("/scripts/search", response_model=ScriptSearchResponse)
async def search_scripts(request: ScriptSearchRequest):
    """搜索脚本"""
    try:
        result = await database_script_service.search_scripts(request)
        return result

    except Exception as e:
        logger.error(f"搜索脚本失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索脚本失败: {str(e)}")


@router.get("/scripts/statistics", response_model=ScriptStatistics)
async def get_script_statistics():
    """获取脚本统计信息"""
    try:
        stats = await database_script_service.get_script_statistics()
        return stats

    except Exception as e:
        logger.error(f"获取脚本统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取脚本统计失败: {str(e)}")


@router.get("/scripts/{script_id}", response_model=TestScript)
async def get_script(script_id: str):
    """获取脚本详情"""
    try:
        script = await database_script_service.get_script(script_id)
        if not script:
            raise HTTPException(status_code=404, detail="脚本不存在")

        return script

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取脚本失败: {script_id} - {e}")
        raise HTTPException(status_code=500, detail=f"获取脚本失败: {str(e)}")


@router.put("/scripts/{script_id}", response_model=TestScript)
async def update_script(script_id: str, request: ScriptUpdateRequest):
    """更新脚本（同时更新数据库和工作空间）"""
    try:
        # 构建更新字典
        updates = {}
        for field, value in request.model_dump(exclude_unset=True).items():
            if value is not None:
                updates[field] = value

        if not updates:
            raise HTTPException(status_code=400, detail="没有提供更新字段")

        script = await database_script_service.update_script(script_id, updates)
        if not script:
            raise HTTPException(status_code=404, detail="脚本不存在")

        logger.info(f"脚本更新成功（已同步到工作空间）: {script_id}")
        return script

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新脚本失败: {script_id} - {e}")
        raise HTTPException(status_code=500, detail=f"更新脚本失败: {str(e)}")


@router.delete("/scripts/{script_id}")
async def delete_script(script_id: str):
    """删除脚本"""
    try:
        success = await database_script_service.delete_script(script_id)
        if not success:
            raise HTTPException(status_code=404, detail="脚本不存在")

        logger.info(f"脚本删除成功: {script_id}")
        return {"message": "脚本删除成功", "script_id": script_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除脚本失败: {script_id} - {e}")
        raise HTTPException(status_code=500, detail=f"删除脚本失败: {str(e)}")


@router.get("/scripts/{script_id}/executions", response_model=List[ScriptExecutionRecord])
async def get_script_executions(script_id: str, limit: int = 20):
    """获取脚本执行记录"""
    try:
        records = await database_script_service.get_script_executions(script_id, limit)
        return records

    except Exception as e:
        logger.error(f"获取脚本执行记录失败: {script_id} - {e}")
        raise HTTPException(status_code=500, detail=f"获取执行记录失败: {str(e)}")


@router.post("/scripts/{script_id}/execute")
async def execute_script(script_id: str, request: ScriptExecuteRequest):
    """执行脚本"""
    try:
        script = await database_script_service.get_script(script_id)
        if not script:
            raise HTTPException(status_code=404, detail="脚本不存在")

        # 调用脚本执行服务
        from app.api.v1.endpoints.web.test_script_execution import create_script_execution_session

        # 创建执行会话
        session_id = await create_script_execution_session(
            script_content=script.content,
            script_name=script.name,
            execution_config=request.execution_config or {},
            environment_variables=request.environment_variables or {}
        )

        logger.info(f"脚本执行启动: {script_id} - {session_id}")
        return {
            "execution_id": session_id,
            "script_id": script_id,
            "status": "started",
            "message": "脚本执行已启动",
            "sse_endpoint": f"/api/v1/web/execution/stream/{session_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行脚本失败: {script_id} - {e}")
        raise HTTPException(status_code=500, detail=f"执行脚本失败: {str(e)}")


@router.post("/scripts/batch-execute", response_model=BatchExecutionResponse)
async def batch_execute_scripts(request: BatchExecutionRequest):
    """批量执行脚本"""
    try:
        # 验证脚本存在
        valid_scripts = []
        for script_id in request.script_ids:
            script = await database_script_service.get_script(script_id)
            if script:
                valid_scripts.append(script)

        if not valid_scripts:
            raise HTTPException(status_code=400, detail="没有找到有效的脚本")

        # 调用脚本执行服务
        from app.api.v1.endpoints.web.script_execution import create_batch_execution_session

        # 创建批量执行会话
        session_id = await create_batch_execution_session(
            scripts=[(script.content, script.name) for script in valid_scripts],
            execution_config=request.execution_config or {},
            parallel=request.parallel or False,
            continue_on_error=request.continue_on_error or True
        )

        # 生成执行ID列表（为了兼容现有响应格式）
        execution_ids = [f"{session_id}_{script.name}" for script in valid_scripts]

        response = BatchExecutionResponse(
            batch_id=session_id,
            script_count=len(valid_scripts),
            execution_ids=execution_ids,
            status="started",
            message=f"批量执行已启动，共{len(valid_scripts)}个脚本",
            timestamp=datetime.now().isoformat()
        )

        logger.info(f"批量执行启动: {session_id} - {len(valid_scripts)}个脚本")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量执行脚本失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量执行失败: {str(e)}")


@router.post("/scripts/upload")
async def upload_script(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(...),
    script_format: str = Form(...),
    category: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)  # JSON字符串
):
    """上传脚本文件（同时保存到数据库和工作空间）"""
    try:
        # 验证文件类型
        allowed_extensions = ['.yaml', '.yml', '.ts', '.js']
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式。支持的格式: {', '.join(allowed_extensions)}"
            )

        # 读取文件内容
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:  # 10MB限制
            raise HTTPException(status_code=400, detail="文件大小不能超过10MB")

        script_content = content.decode('utf-8')

        # 解析标签
        tag_list = []
        if tags:
            import json
            try:
                tag_list = json.loads(tags)
            except json.JSONDecodeError:
                logger.warning(f"标签解析失败: {tags}")

        # 根据文件扩展名确定脚本类型
        if file_extension in ['.yaml', '.yml']:
            script_type = ScriptType.UI_AUTOMATION
        else:
            script_type = ScriptType.PLAYWRIGHT

        # 生成会话ID
        import uuid
        session_id = str(uuid.uuid4())

        # 创建脚本
        script = await database_script_service.create_script_from_analysis(
            session_id=session_id,
            name=name,
            description=description,
            content=script_content,
            script_format=ScriptFormat(script_format),
            script_type=script_type,
            test_description=description,  # 使用描述作为测试描述
            additional_context=f"从文件上传: {file.filename}",
            source_url=None
        )

        # 设置额外属性
        updates = {}
        if tag_list:
            updates['tags'] = tag_list
        if category:
            updates['category'] = category

        if updates:
            script = await database_script_service.update_script(script.id, updates)

        logger.info(f"脚本上传成功（已同步到工作空间）: {script.id} - {script.name}")
        return {
            "status": "success",
            "script_id": script.id,
            "message": "脚本上传成功（已同步到工作空间）",
            "script": script
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传脚本失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传脚本失败: {str(e)}")


@router.post("/scripts/save-from-session")
async def save_script_from_session(
    session_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(...),
    script_format: str = Form(...),
    script_type: str = Form(...),
    test_description: str = Form(...),
    content: str = Form(...),
    additional_context: Optional[str] = Form(None),
    source_url: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)  # JSON字符串
):
    """从会话保存脚本（用于Web创建测试页面）"""
    try:
        # 解析标签
        tag_list = []
        if tags:
            import json
            tag_list = json.loads(tags)

        # 创建脚本
        script = await database_script_service.create_script_from_analysis(
            session_id=session_id,
            name=name,
            description=description,
            content=content,
            script_format=ScriptFormat(script_format),
            script_type=ScriptType(script_type),
            test_description=test_description,
            additional_context=additional_context,
            source_url=source_url
        )

        # 设置标签
        if tag_list:
            script = await database_script_service.update_script(script.id, {"tags": tag_list})

        logger.info(f"从会话保存脚本成功: {script.id} - {script.name}")
        return {
            "status": "success",
            "script_id": script.id,
            "message": "脚本保存成功",
            "script": script
        }

    except Exception as e:
        logger.error(f"从会话保存脚本失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存脚本失败: {str(e)}")


@router.post("/scripts/sync-workspace")
async def sync_all_scripts_to_workspace():
    """手动同步所有脚本到工作空间"""
    try:
        from app.utils.file_utils import sync_script_to_workspace

        # 获取所有脚本
        scripts = await database_script_service.search_scripts(ScriptSearchRequest())

        synced_count = 0
        failed_count = 0

        for script in scripts:
            try:
                await sync_script_to_workspace(
                    script_name=script.name,
                    script_content=script.content,
                    script_format=script.script_format.value
                )
                synced_count += 1
            except Exception as e:
                logger.error(f"同步脚本失败: {script.id} - {e}")
                failed_count += 1

        logger.info(f"工作空间同步完成: 成功 {synced_count}, 失败 {failed_count}")
        return {
            "status": "success",
            "message": f"工作空间同步完成",
            "synced_count": synced_count,
            "failed_count": failed_count,
            "total_scripts": len(scripts)
        }

    except Exception as e:
        logger.error(f"同步工作空间失败: {e}")
        raise HTTPException(status_code=500, detail=f"同步工作空间失败: {str(e)}")

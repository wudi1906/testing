"""
Web脚本执行 - 支持单个和多个脚本批量执行
参考image_analysis.py的架构，支持SSE流式接口和实时状态更新
"""
from autogen_core import CancellationToken, MessageContext, ClosureContext
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
import asyncio
import logging
import uuid
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from app.core.agents import StreamResponseCollector
from app.core.messages import StreamMessage
from app.core.messages.web import PlaywrightExecutionRequest, ScriptExecutionRequest, ScriptExecutionStatus
from app.core.types import AgentPlatform
from app.services.web.orchestrator_service import get_web_orchestrator
from app.services.database_script_service import database_script_service
from app.models.test_scripts import ScriptFormat
from pydantic import BaseModel, Field

router = APIRouter()

# 设置日志记录器
logger = logging.getLogger(__name__)

# 会话存储
active_sessions: Dict[str, Dict[str, Any]] = {}

# 消息队列存储
message_queues: Dict[str, asyncio.Queue] = {}

# 脚本执行状态存储
script_statuses: Dict[str, Dict[str, ScriptExecutionStatus]] = {}

# 会话超时（秒）
SESSION_TIMEOUT = 3600  # 1小时

# Playwright工作空间路径
PLAYWRIGHT_WORKSPACE = Path(r"C:\Users\86134\Desktop\workspace\playwright-workspace")

# 统一执行请求和响应模型
class UnifiedScriptExecutionRequest(BaseModel):
    """统一脚本执行请求"""
    script_id: str = Field(..., description="脚本ID")
    execution_config: Optional[Dict[str, Any]] = Field(None, description="执行配置")
    environment_variables: Optional[Dict[str, Any]] = Field(None, description="环境变量")

class UnifiedBatchExecutionRequest(BaseModel):
    """统一批量脚本执行请求"""
    script_ids: List[str] = Field(..., description="脚本ID列表")
    execution_config: Optional[Dict[str, Any]] = Field(None, description="执行配置")
    environment_variables: Optional[Dict[str, Any]] = Field(None, description="环境变量")
    parallel: bool = Field(False, description="是否并行执行")
    continue_on_error: bool = Field(True, description="遇到错误是否继续")

class UnifiedScriptExecutionResponse(BaseModel):
    """统一脚本执行响应"""
    session_id: str = Field(..., description="执行会话ID")
    script_id: str = Field(..., description="脚本ID")
    script_name: str = Field(..., description="脚本名称")
    status: str = Field(..., description="执行状态")
    message: str = Field(..., description="响应消息")
    sse_endpoint: str = Field(..., description="SSE流端点")
    created_at: str = Field(..., description="创建时间")

class UnifiedBatchExecutionResponse(BaseModel):
    """统一批量执行响应"""
    session_id: str = Field(..., description="批量执行会话ID")
    script_count: int = Field(..., description="脚本数量")
    script_ids: List[str] = Field(..., description="脚本ID列表")
    status: str = Field(..., description="执行状态")
    message: str = Field(..., description="响应消息")
    sse_endpoint: str = Field(..., description="SSE流端点")
    created_at: str = Field(..., description="创建时间")


async def cleanup_session(session_id: str, delay: int = SESSION_TIMEOUT):
    """在指定延迟后清理会话资源"""
    await asyncio.sleep(delay)
    if session_id in active_sessions:
        logger.info(f"清理过期会话: {session_id}")
        active_sessions.pop(session_id, None)
        message_queues.pop(session_id, None)
        script_statuses.pop(session_id, None)


async def resolve_script_by_id(script_id: str) -> Dict[str, Any]:
    """
    根据脚本ID解析脚本信息
    统一处理数据库脚本和文件系统脚本

    Args:
        script_id: 脚本ID

    Returns:
        Dict: 包含脚本信息的字典
    """
    # 首先尝试从数据库获取脚本
    try:
        db_script = await database_script_service.get_script(script_id)
        if db_script:
            # 数据库脚本：使用存储的名称在工作空间中查找文件
            script_path = PLAYWRIGHT_WORKSPACE / "e2e" / db_script.name

            # 如果路径不存在，尝试添加扩展名
            if not script_path.exists():
                if db_script.script_format == ScriptFormat.PLAYWRIGHT:
                    script_path = PLAYWRIGHT_WORKSPACE / "e2e" / f"{db_script.name}.spec.ts"
                else:
                    script_path = PLAYWRIGHT_WORKSPACE / "e2e" / f"{db_script.name}.yaml"

            # 验证文件是否存在
            if not script_path.exists():
                raise FileNotFoundError(f"脚本文件不存在: {script_path}")

            return {
                "script_id": script_id,
                "name": db_script.name,
                "file_name": script_path.name,
                "path": str(script_path),
                "description": db_script.description or f"脚本: {db_script.name}"
            }
    except Exception as e:
        logger.warning(f"从数据库获取脚本失败: {script_id} - {e}")

    # 尝试从文件系统获取脚本（假设script_id是文件名）
    try:
        e2e_dir = PLAYWRIGHT_WORKSPACE / "e2e"
        script_path = e2e_dir / script_id

        # 如果script_id不包含扩展名，尝试添加.spec.ts
        if not script_path.exists() and not script_id.endswith('.spec.ts'):
            script_path = e2e_dir / f"{script_id}.spec.ts"

        if script_path.exists():
            return {
                "script_id": script_id,
                "name": script_path.stem,  # 不包含扩展名的文件名
                "file_name": script_path.name,
                "path": str(script_path),
                "description": f"脚本: {script_path.name}"
            }
    except Exception as e:
        logger.warning(f"从文件系统获取脚本失败: {script_id} - {e}")

    # 脚本不存在
    raise HTTPException(status_code=404, detail=f"脚本不存在: {script_id}")


def get_available_scripts() -> List[Dict[str, Any]]:
    """获取e2e目录下可用的脚本列表"""
    try:
        e2e_dir = PLAYWRIGHT_WORKSPACE / "e2e"
        if not e2e_dir.exists():
            return []
        
        scripts = []
        for script_file in e2e_dir.glob("*.spec.ts"):
            if script_file.name != "fixture.ts":  # 排除fixture文件
                scripts.append({
                    "name": script_file.name,
                    "path": str(script_file),
                    "size": script_file.stat().st_size,
                    "modified": datetime.fromtimestamp(script_file.stat().st_mtime).isoformat()
                })
        
        return sorted(scripts, key=lambda x: x["modified"], reverse=True)
    
    except Exception as e:
        logger.error(f"获取可用脚本列表失败: {str(e)}")
        return []


@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok", 
        "service": "web-script-execution", 
        "timestamp": datetime.now().isoformat(),
        "workspace": str(PLAYWRIGHT_WORKSPACE),
        "workspace_exists": PLAYWRIGHT_WORKSPACE.exists()
    }


@router.get("/scripts")
async def list_available_scripts():
    """获取可用的脚本列表"""
    try:
        scripts = get_available_scripts()
        return JSONResponse({
            "scripts": scripts,
            "total": len(scripts),
            "workspace": str(PLAYWRIGHT_WORKSPACE),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"获取脚本列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取脚本列表失败: {str(e)}")


@router.post("/execute-by-id", response_model=UnifiedScriptExecutionResponse)
async def execute_script_by_id(request: UnifiedScriptExecutionRequest):
    """
    根据脚本ID执行脚本（统一接口）

    Args:
        request: 脚本执行请求

    Returns:
        UnifiedScriptExecutionResponse: 执行响应
    """
    try:
        # 解析脚本信息
        script_info = await resolve_script_by_id(request.script_id)

        # 生成执行会话ID
        session_id = f"exec_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"

        # 创建会话信息
        session_data = {
            "session_id": session_id,
            "type": "single_script",
            "script_id": request.script_id,
            "script_info": script_info,
            "execution_config": request.execution_config or {},
            "environment_variables": request.environment_variables or {},
            "status": "initialized",
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }

        # 注册会话
        active_sessions[session_id] = session_data

        # 初始化脚本状态
        script_statuses[session_id] = {
            script_info["name"]: ScriptExecutionStatus(
                session_id=session_id,
                script_name=script_info["name"],
                status="pending"
            )
        }

        logger.info(f"创建脚本执行会话: {session_id} - {script_info['name']}")

        return UnifiedScriptExecutionResponse(
            session_id=session_id,
            script_id=request.script_id,
            script_name=script_info["name"],
            status="initialized",
            message=f"脚本执行会话已创建: {script_info['name']}",
            sse_endpoint=f"/api/v1/web/execution/stream/{session_id}",
            created_at=session_data["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建脚本执行会话失败: {request.script_id} - {e}")
        raise HTTPException(status_code=500, detail=f"创建执行会话失败: {str(e)}")


@router.post("/batch-execute-by-ids", response_model=UnifiedBatchExecutionResponse)
async def batch_execute_scripts_by_ids(request: UnifiedBatchExecutionRequest):
    """
    根据脚本ID列表批量执行脚本（统一接口）

    Args:
        request: 批量脚本执行请求

    Returns:
        UnifiedBatchExecutionResponse: 批量执行响应
    """
    try:
        # 解析所有脚本信息
        script_infos = []
        for script_id in request.script_ids:
            try:
                script_info = await resolve_script_by_id(script_id)
                script_infos.append(script_info)
            except HTTPException as e:
                logger.warning(f"跳过无效脚本: {script_id} - {e.detail}")
                continue

        if not script_infos:
            raise HTTPException(status_code=400, detail="没有找到有效的脚本")

        # 生成批量执行会话ID
        session_id = f"batch_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"

        # 创建会话信息
        session_data = {
            "session_id": session_id,
            "type": "batch_scripts",
            "script_ids": request.script_ids,
            "script_infos": script_infos,
            "execution_config": request.execution_config or {},
            "environment_variables": request.environment_variables or {},
            "parallel": request.parallel,
            "continue_on_error": request.continue_on_error,
            "status": "initialized",
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }

        # 注册会话
        active_sessions[session_id] = session_data

        # 初始化所有脚本状态
        script_statuses[session_id] = {}
        for script_info in script_infos:
            script_statuses[session_id][script_info["name"]] = ScriptExecutionStatus(
                session_id=session_id,
                script_name=script_info["name"],
                status="pending"
            )

        logger.info(f"创建批量执行会话: {session_id} - {len(script_infos)}个脚本")

        return UnifiedBatchExecutionResponse(
            session_id=session_id,
            script_count=len(script_infos),
            script_ids=request.script_ids,
            status="initialized",
            message=f"批量执行会话已创建，共{len(script_infos)}个脚本",
            sse_endpoint=f"/api/v1/web/execution/stream/{session_id}",
            created_at=session_data["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建批量执行会话失败: {request.script_ids} - {e}")
        raise HTTPException(status_code=500, detail=f"创建批量执行会话失败: {str(e)}")


@router.post("/execute/single")
async def execute_single_script(
    script_name: str = Form(...),
    execution_config: Optional[str] = Form(None),  # JSON字符串
    base_url: Optional[str] = Form(None),
    headed: bool = Form(False),
    timeout: int = Form(90)
):
    """
    执行单个脚本
    
    Args:
        script_name: 脚本文件名（在e2e目录下）
        execution_config: 执行配置（JSON字符串）
        base_url: 测试基础URL
        headed: 是否显示浏览器界面
        timeout: 超时时间（秒）
    
    Returns:
        Dict: 包含session_id的响应
    """
    try:
        # 验证脚本是否存在
        e2e_dir = PLAYWRIGHT_WORKSPACE / "e2e"
        script_path = e2e_dir / script_name
        
        if not script_path.exists():
            raise HTTPException(status_code=404, detail=f"脚本文件不存在: {script_name}")
        
        # 解析执行配置
        config = {}
        if execution_config:
            try:
                config = json.loads(execution_config)
            except json.JSONDecodeError:
                logger.warning(f"执行配置解析失败，使用默认配置: {execution_config}")
        
        # 设置基础配置
        if base_url:
            config["base_url"] = base_url
        config["headed"] = headed
        config["timeout"] = timeout
        
        # 生成会话ID
        session_id = str(uuid.uuid4())
        
        # 存储会话信息
        active_sessions[session_id] = {
            "type": "single_script",
            "script_name": script_name,
            "execution_config": config,
            "status": "initialized",
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
        
        # 初始化脚本状态
        script_statuses[session_id] = {
            script_name: ScriptExecutionStatus(
                session_id=session_id,
                script_name=script_name,
                status="pending"
            )
        }
        
        logger.info(f"单脚本执行任务已创建: {session_id} - {script_name}")
        
        return JSONResponse({
            "session_id": session_id,
            "status": "initialized",
            "script_name": script_name,
            "message": "脚本执行任务已创建，请使用SSE连接获取实时进度",
            "sse_endpoint": f"/api/v1/web/scripts/stream/{session_id}"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建单脚本执行任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建执行任务失败: {str(e)}")


@router.post("/execute/batch")
async def execute_batch_scripts(
    script_names: str = Form(...),  # 逗号分隔的脚本名称
    execution_config: Optional[str] = Form(None),  # JSON字符串
    parallel_execution: bool = Form(False),
    stop_on_failure: bool = Form(True),
    base_url: Optional[str] = Form(None),
    headed: bool = Form(False),
    timeout: int = Form(90)
):
    """
    批量执行多个脚本
    
    Args:
        script_names: 脚本文件名列表（逗号分隔）
        execution_config: 执行配置（JSON字符串）
        parallel_execution: 是否并行执行
        stop_on_failure: 遇到失败时是否停止执行
        base_url: 测试基础URL
        headed: 是否显示浏览器界面
        timeout: 超时时间（秒）
    
    Returns:
        Dict: 包含session_id的响应
    """
    try:
        # 解析脚本名称列表
        script_list = [name.strip() for name in script_names.split(",") if name.strip()]
        
        if not script_list:
            raise HTTPException(status_code=400, detail="至少需要指定一个脚本")
        
        # 验证所有脚本是否存在
        e2e_dir = PLAYWRIGHT_WORKSPACE / "e2e"
        missing_scripts = []
        
        for script_name in script_list:
            script_path = e2e_dir / script_name
            if not script_path.exists():
                missing_scripts.append(script_name)
        
        if missing_scripts:
            raise HTTPException(
                status_code=404, 
                detail=f"以下脚本文件不存在: {', '.join(missing_scripts)}"
            )
        
        # 解析执行配置
        config = {}
        if execution_config:
            try:
                config = json.loads(execution_config)
            except json.JSONDecodeError:
                logger.warning(f"执行配置解析失败，使用默认配置: {execution_config}")
        
        # 设置基础配置
        if base_url:
            config["base_url"] = base_url
        config["headed"] = headed
        config["timeout"] = timeout
        
        # 生成会话ID
        session_id = str(uuid.uuid4())
        
        # 存储会话信息
        active_sessions[session_id] = {
            "type": "batch_scripts",
            "script_names": script_list,
            "execution_config": config,
            "parallel_execution": parallel_execution,
            "stop_on_failure": stop_on_failure,
            "status": "initialized",
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }
        
        # 初始化所有脚本状态
        script_statuses[session_id] = {}
        for script_name in script_list:
            script_statuses[session_id][script_name] = ScriptExecutionStatus(
                session_id=session_id,
                script_name=script_name,
                status="pending"
            )
        
        logger.info(f"批量脚本执行任务已创建: {session_id} - {len(script_list)}个脚本")
        
        return JSONResponse({
            "session_id": session_id,
            "status": "initialized",
            "script_names": script_list,
            "total_scripts": len(script_list),
            "parallel_execution": parallel_execution,
            "stop_on_failure": stop_on_failure,
            "message": "批量脚本执行任务已创建，请使用SSE连接获取实时进度",
            "sse_endpoint": f"/api/v1/web/scripts/stream/{session_id}"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建批量脚本执行任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建执行任务失败: {str(e)}")


@router.get("/stream/{session_id}")
async def stream_script_execution(
    session_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    start_processing: bool = True
):
    """
    脚本执行SSE流式端点

    Args:
        session_id: 会话ID
        request: HTTP请求对象
        background_tasks: 后台任务管理器
        start_processing: 是否立即开始处理

    Returns:
        EventSourceResponse: SSE响应流
    """
    # 验证会话是否存在
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

    logger.info(f"开始脚本执行SSE流: {session_id}")

    # 创建消息队列
    if session_id not in message_queues:
        message_queue = asyncio.Queue()
        message_queues[session_id] = message_queue
        logger.info(f"创建消息队列: {session_id}")
    else:
        message_queue = message_queues[session_id]
        logger.info(f"使用现有消息队列: {session_id}")

    # 设置会话超时清理
    background_tasks.add_task(cleanup_session, session_id)

    # 如果需要开始处理，启动执行任务
    if start_processing and active_sessions[session_id]["status"] == "initialized":
        logger.info(f"启动脚本执行处理任务: {session_id}")
        # 根据会话类型选择处理函数
        session_info = active_sessions[session_id]
        if "script_info" in session_info or "script_infos" in session_info:
            # 统一执行任务
            asyncio.create_task(process_unified_execution_task(session_id))
        else:
            # 传统执行任务
            asyncio.create_task(process_script_execution_task(session_id))

    # 返回SSE响应
    response = EventSourceResponse(
        script_event_generator(session_id, request),
        media_type="text/event-stream"
    )

    # 添加必要的响应头
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"  # 禁用Nginx缓冲

    return response


async def script_event_generator(session_id: str, request: Request):
    """生成脚本执行SSE事件流"""
    logger.info(f"开始生成脚本执行事件流: {session_id}")

    # 发送会话初始化事件
    init_data = json.dumps({
        "session_id": session_id,
        "status": "connected",
        "service": "script_execution"
    })
    yield f"event: session\nid: 0\ndata: {init_data}\n\n"

    # 获取消息队列
    message_queue = message_queues.get(session_id)
    if not message_queue:
        error_data = json.dumps({
            "error": "会话队列不存在"
        })
        yield f"event: error\nid: error-1\ndata: {error_data}\n\n"
        return

    # 消息ID计数器
    message_id = 1

    try:
        # 持续从队列获取消息并发送
        while True:
            # 检查客户端是否断开连接
            if await request.is_disconnected():
                logger.info(f"客户端断开连接: {session_id}")
                break

            # 尝试从队列获取消息（非阻塞）
            try:
                # 使用较短的超时时间，确保更频繁地检查连接状态
                message = await asyncio.wait_for(message_queue.get(), timeout=0.5)

                logger.debug(f"成功从队列获取消息: {message.type} - {message.content[:50]}...")

                # 更新会话最后活动时间
                if session_id in active_sessions:
                    active_sessions[session_id]["last_activity"] = datetime.now().isoformat()

                # 确定事件类型
                event_type = message.type

                # 将消息转换为JSON字符串
                message_json = message.model_dump_json()

                logger.debug(f"发送事件: id={message_id}, type={event_type}, region={message.region}")

                # 使用正确的SSE格式发送消息
                yield f"event: {event_type}\nid: {message_id}\ndata: {message_json}\n\n"
                message_id += 1

                # 如果是最终消息，继续保持连接
                if message.is_final and event_type == "final_result":
                    logger.info(f"收到最终结果，继续保持连接: {session_id}")

            except asyncio.TimeoutError:
                # 发送保持连接的消息
                ping_data = json.dumps({"timestamp": datetime.now().isoformat()})
                yield f"event: ping\nid: ping-{message_id}\ndata: {ping_data}\n\n"
                message_id += 1
                continue

    except Exception as e:
        logger.error(f"生成事件流时出错: {str(e)}")
        error_data = json.dumps({
            "error": f"生成事件流时出错: {str(e)}"
        })
        yield f"event: error\nid: error-{message_id}\ndata: {error_data}\n\n"

    # 发送关闭事件
    close_data = json.dumps({
        "message": "流已关闭"
    })
    logger.info(f"事件流结束: {session_id}")
    yield f"event: close\nid: close-{message_id}\ndata: {close_data}\n\n"


async def process_script_execution_task(session_id: str):
    """处理脚本执行的后台任务"""
    logger.info(f"开始执行脚本任务: {session_id}")

    try:
        # 获取消息队列
        message_queue = message_queues.get(session_id)
        if not message_queue:
            logger.error(f"会话 {session_id} 的消息队列不存在")
            return

        # 获取会话信息
        session_info = active_sessions.get(session_id)
        if not session_info:
            logger.error(f"会话 {session_id} 信息不存在")
            return

        # 更新会话状态
        active_sessions[session_id]["status"] = "processing"

        # 发送开始消息
        start_message = StreamMessage(
            message_id=f"system-{uuid.uuid4()}",
            type="message",
            source="系统",
            content="🚀 开始脚本执行流程...",
            region="process",
            platform="web",
            is_final=False,
        )
        await message_queue.put(start_message)

        # 设置消息回调函数
        async def message_callback(ctx: ClosureContext, message: StreamMessage, message_ctx: MessageContext) -> None:
            try:
                current_queue = message_queues.get(session_id)
                if current_queue:
                    await current_queue.put(message)
                else:
                    logger.error(f"消息回调：会话 {session_id} 的队列不存在")
            except Exception as e:
                logger.error(f"消息回调处理错误: {str(e)}")

        # 创建响应收集器
        collector = StreamResponseCollector(platform=AgentPlatform.WEB)
        collector.set_callback(message_callback)

        # 获取Web编排器
        orchestrator = get_web_orchestrator(collector=collector)

        # 根据执行类型处理
        if session_info["type"] == "single_script":
            await execute_single_script_task(session_id, session_info, orchestrator, message_queue)
        elif session_info["type"] == "batch_scripts":
            await execute_batch_scripts_task(session_id, session_info, orchestrator, message_queue)

        # 发送最终结果
        final_message = StreamMessage(
            message_id=f"final-{uuid.uuid4()}",
            type="final_result",
            source="系统",
            content="✅ 脚本执行流程完成",
            region="process",
            platform="web",
            is_final=True,
        )
        await message_queue.put(final_message)

        # 更新会话状态
        active_sessions[session_id]["status"] = "completed"
        active_sessions[session_id]["completed_at"] = datetime.now().isoformat()

        logger.info(f"脚本执行任务已完成: {session_id}")

    except Exception as e:
        logger.error(f"脚本执行任务失败: {str(e)}")

        # 发送错误消息
        try:
            error_message = StreamMessage(
                message_id=f"error-{uuid.uuid4()}",
                type="error",
                source="系统",
                content=f"❌ 脚本执行过程出错: {str(e)}",
                region="process",
                platform="web",
                is_final=True
            )

            message_queue = message_queues.get(session_id)
            if message_queue:
                await message_queue.put(error_message)

        except Exception as send_error:
            logger.error(f"发送错误消息失败: {str(send_error)}")

        # 更新会话状态
        if session_id in active_sessions:
            active_sessions[session_id]["status"] = "error"
            active_sessions[session_id]["error"] = str(e)
            active_sessions[session_id]["error_at"] = datetime.now().isoformat()


async def execute_single_script_task(session_id: str, session_info: Dict[str, Any],
                                   orchestrator, message_queue: asyncio.Queue):
    """执行单个脚本任务"""
    script_name = session_info["script_name"]
    execution_config = session_info["execution_config"]

    logger.info(f"开始执行单个脚本: {script_name}")

    # 更新脚本状态
    if session_id in script_statuses and script_name in script_statuses[session_id]:
        script_statuses[session_id][script_name].status = "running"
        script_statuses[session_id][script_name].start_time = datetime.now().isoformat()

    # 发送脚本开始执行消息
    script_start_message = StreamMessage(
        message_id=f"script-start-{uuid.uuid4()}",
        type="script_status",
        source="脚本执行器",
        content=f"🎭 开始执行脚本: {script_name}",
        region="process",
        platform="web",
        is_final=False,
        result={
            "script_name": script_name,
            "status": "running",
            "start_time": datetime.now().isoformat()
        }
    )
    await message_queue.put(script_start_message)

    try:
        # 创建Playwright执行请求
        playwright_request = PlaywrightExecutionRequest(
            session_id=session_id,
            script_id=script_name,  # 使用script_name作为script_id
            script_name=script_name,
            execution_config=execution_config
        )

        # 执行脚本
        await orchestrator.execute_playwright_script(playwright_request)

        # 更新脚本状态为成功
        if session_id in script_statuses and script_name in script_statuses[session_id]:
            script_statuses[session_id][script_name].status = "completed"
            script_statuses[session_id][script_name].end_time = datetime.now().isoformat()

        # 发送脚本完成消息
        script_complete_message = StreamMessage(
            message_id=f"script-complete-{uuid.uuid4()}",
            type="script_status",
            source="脚本执行器",
            content=f"✅ 脚本执行完成: {script_name}",
            region="success",
            platform="web",
            is_final=False,
            result={
                "script_name": script_name,
                "status": "completed",
                "end_time": datetime.now().isoformat()
            }
        )
        await message_queue.put(script_complete_message)

    except Exception as e:
        logger.error(f"执行脚本失败: {script_name} - {str(e)}")

        # 更新脚本状态为失败
        if session_id in script_statuses and script_name in script_statuses[session_id]:
            script_statuses[session_id][script_name].status = "failed"
            script_statuses[session_id][script_name].end_time = datetime.now().isoformat()
            script_statuses[session_id][script_name].error_message = str(e)

        # 发送脚本失败消息
        script_error_message = StreamMessage(
            message_id=f"script-error-{uuid.uuid4()}",
            type="script_status",
            source="脚本执行器",
            content=f"❌ 脚本执行失败: {script_name} - {str(e)}",
            region="error",
            platform="web",
            is_final=False,
            result={
                "script_name": script_name,
                "status": "failed",
                "end_time": datetime.now().isoformat(),
                "error_message": str(e)
            }
        )
        await message_queue.put(script_error_message)
        raise


async def execute_batch_scripts_task(session_id: str, session_info: Dict[str, Any],
                                   orchestrator, message_queue: asyncio.Queue):
    """执行批量脚本任务"""
    script_names = session_info["script_names"]
    execution_config = session_info["execution_config"]
    parallel_execution = session_info["parallel_execution"]
    stop_on_failure = session_info["stop_on_failure"]

    logger.info(f"开始执行批量脚本: {len(script_names)}个脚本, 并行={parallel_execution}")

    # 发送批量执行开始消息
    batch_start_message = StreamMessage(
        message_id=f"batch-start-{uuid.uuid4()}",
        type="batch_status",
        source="批量执行器",
        content=f"🚀 开始批量执行 {len(script_names)} 个脚本",
        region="process",
        platform="web",
        is_final=False,
        result={
            "total_scripts": len(script_names),
            "parallel_execution": parallel_execution,
            "stop_on_failure": stop_on_failure
        }
    )
    await message_queue.put(batch_start_message)

    if parallel_execution:
        # 并行执行
        await execute_scripts_parallel(session_id, script_names, execution_config,
                                     orchestrator, message_queue, stop_on_failure)
    else:
        # 串行执行
        await execute_scripts_sequential(session_id, script_names, execution_config,
                                       orchestrator, message_queue, stop_on_failure)


async def execute_scripts_sequential(session_id: str, script_names: List[str],
                                   execution_config: Dict[str, Any], orchestrator,
                                   message_queue: asyncio.Queue, stop_on_failure: bool):
    """串行执行脚本"""
    completed_count = 0
    failed_count = 0

    for i, script_name in enumerate(script_names, 1):
        try:
            # 发送当前脚本开始消息
            progress_message = StreamMessage(
                message_id=f"progress-{uuid.uuid4()}",
                type="progress",
                source="批量执行器",
                content=f"📝 执行脚本 {i}/{len(script_names)}: {script_name}",
                region="process",
                platform="web",
                is_final=False,
                result={
                    "current_script": script_name,
                    "progress": i,
                    "total": len(script_names),
                    "completed": completed_count,
                    "failed": failed_count
                }
            )
            await message_queue.put(progress_message)

            # 更新脚本状态
            if session_id in script_statuses and script_name in script_statuses[session_id]:
                script_statuses[session_id][script_name].status = "running"
                script_statuses[session_id][script_name].start_time = datetime.now().isoformat()

            # 执行脚本
            await execute_single_script_internal(session_id, script_name, execution_config,
                                               orchestrator, message_queue)

            completed_count += 1

            # 更新脚本状态为成功
            if session_id in script_statuses and script_name in script_statuses[session_id]:
                script_statuses[session_id][script_name].status = "completed"
                script_statuses[session_id][script_name].end_time = datetime.now().isoformat()

        except Exception as e:
            failed_count += 1
            logger.error(f"脚本执行失败: {script_name} - {str(e)}")

            # 更新脚本状态为失败
            if session_id in script_statuses and script_name in script_statuses[session_id]:
                script_statuses[session_id][script_name].status = "failed"
                script_statuses[session_id][script_name].end_time = datetime.now().isoformat()
                script_statuses[session_id][script_name].error_message = str(e)

            # 发送脚本失败消息
            error_message = StreamMessage(
                message_id=f"script-error-{uuid.uuid4()}",
                type="script_status",
                source="批量执行器",
                content=f"❌ 脚本执行失败: {script_name} - {str(e)}",
                region="error",
                platform="web",
                is_final=False,
                result={
                    "script_name": script_name,
                    "status": "failed",
                    "error_message": str(e)
                }
            )
            await message_queue.put(error_message)

            # 如果设置了遇到失败就停止，则中断执行
            if stop_on_failure:
                break_message = StreamMessage(
                    message_id=f"break-{uuid.uuid4()}",
                    type="batch_status",
                    source="批量执行器",
                    content=f"⚠️ 遇到失败，停止执行剩余脚本",
                    region="warning",
                    platform="web",
                    is_final=False
                )
                await message_queue.put(break_message)
                break

    # 发送批量执行完成消息
    summary_message = StreamMessage(
        message_id=f"batch-summary-{uuid.uuid4()}",
        type="batch_status",
        source="批量执行器",
        content=f"📊 批量执行完成: 成功 {completed_count}, 失败 {failed_count}",
        region="success" if failed_count == 0 else "warning",
        platform="web",
        is_final=False,
        result={
            "total_scripts": len(script_names),
            "completed": completed_count,
            "failed": failed_count,
            "success_rate": completed_count / len(script_names) if script_names else 0
        }
    )
    await message_queue.put(summary_message)


async def execute_scripts_parallel(session_id: str, script_names: List[str],
                                 execution_config: Dict[str, Any], orchestrator,
                                 message_queue: asyncio.Queue, stop_on_failure: bool):
    """并行执行脚本"""
    # 创建并行任务
    tasks = []
    for script_name in script_names:
        task = asyncio.create_task(
            execute_single_script_internal(session_id, script_name, execution_config,
                                         orchestrator, message_queue)
        )
        tasks.append((script_name, task))

    # 等待所有任务完成
    completed_count = 0
    failed_count = 0

    for script_name, task in tasks:
        try:
            await task
            completed_count += 1

            # 更新脚本状态为成功
            if session_id in script_statuses and script_name in script_statuses[session_id]:
                script_statuses[session_id][script_name].status = "completed"
                script_statuses[session_id][script_name].end_time = datetime.now().isoformat()

        except Exception as e:
            failed_count += 1
            logger.error(f"并行脚本执行失败: {script_name} - {str(e)}")

            # 更新脚本状态为失败
            if session_id in script_statuses and script_name in script_statuses[session_id]:
                script_statuses[session_id][script_name].status = "failed"
                script_statuses[session_id][script_name].end_time = datetime.now().isoformat()
                script_statuses[session_id][script_name].error_message = str(e)

    # 发送并行执行完成消息
    summary_message = StreamMessage(
        message_id=f"parallel-summary-{uuid.uuid4()}",
        type="batch_status",
        source="并行执行器",
        content=f"📊 并行执行完成: 成功 {completed_count}, 失败 {failed_count}",
        region="success" if failed_count == 0 else "warning",
        platform="web",
        is_final=False,
        result={
            "total_scripts": len(script_names),
            "completed": completed_count,
            "failed": failed_count,
            "success_rate": completed_count / len(script_names) if script_names else 0
        }
    )
    await message_queue.put(summary_message)


async def execute_single_script_internal(session_id: str, script_name: str,
                                       execution_config: Dict[str, Any], orchestrator,
                                       message_queue: asyncio.Queue):
    """内部单脚本执行方法"""
    # 更新脚本状态
    if session_id in script_statuses and script_name in script_statuses[session_id]:
        script_statuses[session_id][script_name].status = "running"
        script_statuses[session_id][script_name].start_time = datetime.now().isoformat()

    # 创建Playwright执行请求
    playwright_request = PlaywrightExecutionRequest(
        session_id=session_id,
        script_id=script_name,  # 使用script_name作为script_id
        script_name=script_name,
        execution_config=execution_config
    )

    # 执行脚本
    await orchestrator.execute_playwright_script(playwright_request)


@router.get("/sessions")
async def list_sessions():
    """列出所有活动会话"""
    return JSONResponse({
        "sessions": active_sessions,
        "total": len(active_sessions),
        "timestamp": datetime.now().isoformat()
    })


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """获取指定会话的信息"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

    session_info = active_sessions[session_id]
    script_status_info = script_statuses.get(session_id, {})

    return JSONResponse({
        "session_info": session_info,
        "script_statuses": {name: status.model_dump() for name, status in script_status_info.items()},
        "timestamp": datetime.now().isoformat()
    })


@router.get("/sessions/{session_id}/status")
async def get_script_statuses(session_id: str):
    """获取会话中所有脚本的执行状态"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

    script_status_info = script_statuses.get(session_id, {})

    return JSONResponse({
        "session_id": session_id,
        "script_statuses": {name: status.model_dump() for name, status in script_status_info.items()},
        "total_scripts": len(script_status_info),
        "timestamp": datetime.now().isoformat()
    })


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

    # 删除会话资源
    active_sessions.pop(session_id, None)
    message_queues.pop(session_id, None)
    script_statuses.pop(session_id, None)

    return JSONResponse({
        "status": "success",
        "message": f"会话 {session_id} 已删除",
        "timestamp": datetime.now().isoformat()
    })


@router.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str):
    """停止指定会话的执行"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

    # 更新会话状态
    active_sessions[session_id]["status"] = "stopped"
    active_sessions[session_id]["stopped_at"] = datetime.now().isoformat()

    # 发送停止消息到队列
    message_queue = message_queues.get(session_id)
    if message_queue:
        stop_message = StreamMessage(
            message_id=f"stop-{uuid.uuid4()}",
            type="message",
            source="系统",
            content="⏹️ 执行已被用户停止",
            region="warning",
            platform="web",
            is_final=True
        )
        await message_queue.put(stop_message)

    return JSONResponse({
        "status": "success",
        "message": f"会话 {session_id} 执行已停止",
        "timestamp": datetime.now().isoformat()
    })


@router.get("/workspace/info")
async def get_workspace_info():
    """获取工作空间信息"""
    try:
        scripts = get_available_scripts()

        # 检查工作空间状态
        workspace_status = {
            "path": str(PLAYWRIGHT_WORKSPACE),
            "exists": PLAYWRIGHT_WORKSPACE.exists(),
            "e2e_dir_exists": (PLAYWRIGHT_WORKSPACE / "e2e").exists(),
            "package_json_exists": (PLAYWRIGHT_WORKSPACE / "package.json").exists(),
            "total_scripts": len(scripts),
            "recent_scripts": scripts[:5]  # 最近的5个脚本
        }

        return JSONResponse({
            "workspace": workspace_status,
            "scripts": scripts,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"获取工作空间信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取工作空间信息失败: {str(e)}")


@router.get("/reports/{session_id}")
async def get_session_reports(session_id: str):
    """获取会话的测试报告"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

    try:
        # 查找报告文件
        report_dir = PLAYWRIGHT_WORKSPACE / "midscene_run" / "report"
        reports = []

        if report_dir.exists():
            for report_file in report_dir.glob("*.html"):
                reports.append({
                    "name": report_file.name,
                    "path": str(report_file),
                    "size": report_file.stat().st_size,
                    "created": datetime.fromtimestamp(report_file.stat().st_ctime).isoformat(),
                    "url": f"file:///{str(report_file).replace(chr(92), '/')}"
                })

        return JSONResponse({
            "session_id": session_id,
            "reports": sorted(reports, key=lambda x: x["created"], reverse=True),
            "total_reports": len(reports),
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"获取会话报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取报告失败: {str(e)}")


async def create_script_execution_session(
    script_content: str,
    script_name: str,
    execution_config: Dict[str, Any],
    environment_variables: Dict[str, Any]
) -> str:
    """
    创建脚本执行会话（供脚本管理接口调用）

    Args:
        script_content: 脚本内容
        script_name: 脚本名称
        execution_config: 执行配置
        environment_variables: 环境变量

    Returns:
        str: 会话ID
    """
    try:
        # 生成会话ID
        session_id = f"db_exec_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"

        # 创建临时脚本文件
        import tempfile
        import os

        # 确定脚本文件扩展名
        if script_content.strip().startswith('import') or 'playwright' in script_content.lower():
            file_extension = '.spec.ts'
        else:
            file_extension = '.yaml'

        # 创建临时文件
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, f"{script_name}{file_extension}")

        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        # 创建会话信息
        session_info = {
            "session_id": session_id,
            "type": "single_script",
            "script_name": script_name,
            "script_path": temp_file_path,
            "script_content": script_content,
            "execution_config": execution_config,
            "environment_variables": environment_variables,
            "status": "initialized",
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "source": "database"
        }

        # 注册会话
        active_sessions[session_id] = session_info

        # 初始化脚本状态
        script_statuses[session_id] = {
            script_name: ScriptExecutionStatus(
                session_id=session_id,
                script_name=script_name,
                status="pending"
            )
        }

        logger.info(f"创建数据库脚本执行会话: {session_id} - {script_name}")
        return session_id

    except Exception as e:
        logger.error(f"创建脚本执行会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建执行会话失败: {str(e)}")


async def create_batch_execution_session(
    scripts: List[Tuple[str, str]],  # [(content, name), ...]
    execution_config: Dict[str, Any],
    parallel: bool = False,
    continue_on_error: bool = True
) -> str:
    """
    创建批量脚本执行会话（供脚本管理接口调用）

    Args:
        scripts: 脚本列表，每个元素为(content, name)元组
        execution_config: 执行配置
        parallel: 是否并行执行
        continue_on_error: 遇到错误是否继续

    Returns:
        str: 会话ID
    """
    try:
        # 生成会话ID
        session_id = f"db_batch_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"

        # 创建临时脚本文件
        import tempfile
        import os

        temp_dir = tempfile.mkdtemp()
        script_names = []

        for i, (content, name) in enumerate(scripts):
            # 确定脚本文件扩展名
            if content.strip().startswith('import') or 'playwright' in content.lower():
                file_extension = '.spec.ts'
            else:
                file_extension = '.yaml'

            # 创建临时文件
            temp_file_path = os.path.join(temp_dir, f"{name}{file_extension}")

            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            script_names.append(name)

        # 创建会话信息
        session_info = {
            "session_id": session_id,
            "type": "batch_scripts",
            "script_names": script_names,
            "scripts_dir": temp_dir,
            "execution_config": execution_config,
            "parallel_execution": parallel,
            "stop_on_failure": not continue_on_error,
            "status": "initialized",
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "source": "database"
        }

        # 注册会话
        active_sessions[session_id] = session_info

        # 初始化脚本状态
        script_statuses[session_id] = {}
        for name in script_names:
            script_statuses[session_id][name] = ScriptExecutionStatus(
                session_id=session_id,
                script_name=name,
                status="pending"
            )

        logger.info(f"创建数据库批量脚本执行会话: {session_id} - {len(scripts)}个脚本")
        return session_id

    except Exception as e:
        logger.error(f"创建批量脚本执行会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建批量执行会话失败: {str(e)}")


# ==================== 统一执行处理函数 ====================

async def process_unified_execution_task(session_id: str):
    """处理统一脚本执行的后台任务"""
    logger.info(f"开始处理统一脚本执行任务: {session_id}")

    try:
        # 获取消息队列和会话信息
        message_queue = message_queues.get(session_id)
        session_info = active_sessions.get(session_id)

        if not message_queue or not session_info:
            logger.error(f"会话 {session_id} 信息不完整")
            return

        # 更新会话状态
        active_sessions[session_id]["status"] = "processing"

        # 发送开始消息
        start_message = StreamMessage(
            message_id=f"system-{uuid.uuid4()}",
            type="message",
            source="系统",
            content="🚀 开始脚本执行流程...",
            region="process",
            platform="web",
            is_final=False,
        )
        await message_queue.put(start_message)

        # 设置消息回调函数
        async def message_callback(ctx: ClosureContext, message: StreamMessage, message_ctx: MessageContext) -> None:
            try:
                current_queue = message_queues.get(session_id)
                if current_queue:
                    await current_queue.put(message)
            except Exception as e:
                logger.error(f"消息回调处理错误: {str(e)}")

        # 创建响应收集器和编排器
        collector = StreamResponseCollector(platform=AgentPlatform.WEB)
        collector.set_callback(message_callback)
        orchestrator = get_web_orchestrator(collector=collector)

        # 根据执行类型处理
        if session_info["type"] == "single_script":
            await execute_single_unified_script(session_id, session_info, orchestrator, message_queue)
        elif session_info["type"] == "batch_scripts":
            await execute_batch_unified_scripts(session_id, session_info, orchestrator, message_queue)

        # 发送最终结果
        final_message = StreamMessage(
            message_id=f"final-{uuid.uuid4()}",
            type="final_result",
            source="系统",
            content="✅ 脚本执行流程完成",
            region="process",
            platform="web",
            is_final=True,
        )
        await message_queue.put(final_message)

        # 更新会话状态
        active_sessions[session_id]["status"] = "completed"

    except Exception as e:
        logger.error(f"处理统一脚本执行任务失败: {session_id} - {str(e)}")

        # 发送错误消息
        if session_id in message_queues:
            error_message = StreamMessage(
                message_id=f"error-{uuid.uuid4()}",
                type="error",
                source="系统",
                content=f"❌ 执行失败: {str(e)}",
                region="process",
                platform="web",
                is_final=True,
            )
            await message_queues[session_id].put(error_message)

        # 更新会话状态
        if session_id in active_sessions:
            active_sessions[session_id]["status"] = "failed"


async def execute_single_unified_script(session_id: str, session_info: Dict[str, Any],
                                       orchestrator, message_queue: asyncio.Queue):
    """执行单个统一脚本"""
    script_info = session_info["script_info"]
    script_name = script_info["name"]

    logger.info(f"开始执行统一脚本: {session_id} - {script_name}")

    try:
        # 更新脚本状态
        if session_id in script_statuses and script_name in script_statuses[session_id]:
            script_statuses[session_id][script_name].status = "running"
            script_statuses[session_id][script_name].start_time = datetime.now().isoformat()

        # 发送执行开始消息
        start_msg = StreamMessage(
            message_id=f"script-start-{uuid.uuid4()}",
            type="message",
            source="脚本执行器",
            content=f"📝 开始执行脚本: {script_name}",
            region="execution",
            platform="web",
            is_final=False,
        )
        await message_queue.put(start_msg)

        # 创建Playwright执行请求
        # 使用文件名，让Playwright执行智能体在工作空间中查找
        playwright_request = PlaywrightExecutionRequest(
            session_id=session_id,
            script_id=script_info.get("script_id", script_info["name"]),  # 传递script_id
            script_name=script_info["file_name"],  # 使用文件名
            execution_config=session_info["execution_config"]
        )

        # 执行脚本
        await orchestrator.execute_playwright_script(playwright_request)

        # 更新脚本状态为成功
        if session_id in script_statuses and script_name in script_statuses[session_id]:
            script_statuses[session_id][script_name].status = "completed"
            script_statuses[session_id][script_name].end_time = datetime.now().isoformat()

        # 发送执行完成消息
        complete_msg = StreamMessage(
            message_id=f"script-complete-{uuid.uuid4()}",
            type="message",
            source="脚本执行器",
            content=f"✅ 脚本执行完成: {script_name}",
            region="execution",
            platform="web",
            is_final=False,
        )
        await message_queue.put(complete_msg)

    except Exception as e:
        logger.error(f"执行统一脚本失败: {session_id} - {script_name} - {str(e)}")

        # 更新脚本状态为失败
        if session_id in script_statuses and script_name in script_statuses[session_id]:
            script_statuses[session_id][script_name].status = "failed"
            script_statuses[session_id][script_name].end_time = datetime.now().isoformat()
            script_statuses[session_id][script_name].error_message = str(e)

        # 发送错误消息
        error_msg = StreamMessage(
            message_id=f"script-error-{uuid.uuid4()}",
            type="error",
            source="脚本执行器",
            content=f"❌ 脚本执行失败: {script_name} - {str(e)}",
            region="execution",
            platform="web",
            is_final=False,
        )
        await message_queue.put(error_msg)


async def execute_batch_unified_scripts(session_id: str, session_info: Dict[str, Any],
                                       orchestrator, message_queue: asyncio.Queue):
    """批量执行统一脚本"""
    script_infos = session_info["script_infos"]
    parallel = session_info.get("parallel", False)
    continue_on_error = session_info.get("continue_on_error", True)

    logger.info(f"开始批量执行统一脚本: {session_id} - {len(script_infos)}个脚本")

    try:
        if parallel:
            # 并行执行
            tasks = []
            for script_info in script_infos:
                task = asyncio.create_task(
                    execute_single_script_in_unified_batch(
                        session_id, script_info, orchestrator, message_queue
                    )
                )
                tasks.append(task)

            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 检查结果
            failed_count = sum(1 for result in results if isinstance(result, Exception))
            success_count = len(results) - failed_count

        else:
            # 串行执行
            success_count = 0
            failed_count = 0

            for script_info in script_infos:
                try:
                    await execute_single_script_in_unified_batch(
                        session_id, script_info, orchestrator, message_queue
                    )
                    success_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.error(f"批量执行中的脚本失败: {script_info['name']} - {str(e)}")

                    if not continue_on_error:
                        break

        # 发送批量执行总结
        summary_msg = StreamMessage(
            message_id=f"batch-summary-{uuid.uuid4()}",
            type="message",
            source="批量执行器",
            content=f"📊 批量执行完成: 成功 {success_count}个, 失败 {failed_count}个",
            region="execution",
            platform="web",
            is_final=False,
        )
        await message_queue.put(summary_msg)

    except Exception as e:
        logger.error(f"批量执行统一脚本失败: {session_id} - {str(e)}")
        raise


async def execute_single_script_in_unified_batch(session_id: str, script_info: Dict[str, Any],
                                               orchestrator, message_queue: asyncio.Queue):
    """在统一批量执行中执行单个脚本"""
    script_name = script_info["name"]

    try:
        # 更新脚本状态
        if session_id in script_statuses and script_name in script_statuses[session_id]:
            script_statuses[session_id][script_name].status = "running"
            script_statuses[session_id][script_name].start_time = datetime.now().isoformat()

        # 创建Playwright执行请求
        playwright_request = PlaywrightExecutionRequest(
            session_id=session_id,
            script_id=script_info.get("script_id", script_info["name"]),  # 传递script_id
            script_name=script_info["file_name"],  # 使用文件名
            execution_config={}
        )

        # 执行脚本
        await orchestrator.execute_playwright_script(playwright_request)

        # 更新脚本状态为成功
        if session_id in script_statuses and script_name in script_statuses[session_id]:
            script_statuses[session_id][script_name].status = "completed"
            script_statuses[session_id][script_name].end_time = datetime.now().isoformat()

    except Exception as e:
        # 更新脚本状态为失败
        if session_id in script_statuses and script_name in script_statuses[session_id]:
            script_statuses[session_id][script_name].status = "failed"
            script_statuses[session_id][script_name].end_time = datetime.now().isoformat()
            script_statuses[session_id][script_name].error_message = str(e)

        raise

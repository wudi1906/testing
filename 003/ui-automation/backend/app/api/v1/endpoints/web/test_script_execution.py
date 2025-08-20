"""
Web脚本执行 - 统一执行架构
基于最优性能和完善功能的单一执行流程
"""
from autogen_core import CancellationToken, MessageContext, ClosureContext
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
import asyncio
import uuid
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path

from app.core.agents import StreamResponseCollector
from app.core.messages import StreamMessage
from app.core.messages.web import PlaywrightExecutionRequest, ScriptExecutionStatus
from app.core.types import AgentPlatform
from app.services.web.orchestrator_service import get_web_orchestrator
from app.services.database_script_service import database_script_service
from app.models.test_scripts import ScriptFormat
from pydantic import BaseModel, Field
from app.core.logging import get_logger

router = APIRouter()

# 设置日志记录器（统一走 loguru）
logger = get_logger(__name__)

# 会话存储 - 统一管理所有执行会话
active_sessions: Dict[str, Dict[str, Any]] = {}

# 消息队列存储 - 用于SSE流式通信
message_queues: Dict[str, asyncio.Queue] = {}

# 脚本执行状态存储
script_statuses: Dict[str, Dict[str, ScriptExecutionStatus]] = {}

# 会话超时（秒）
SESSION_TIMEOUT = 3600  # 1小时

# Playwright工作空间路径（可配置）
from app.utils.workspace import resolve_playwright_workspace
PLAYWRIGHT_WORKSPACE = resolve_playwright_workspace()


# ==================== 统一请求和响应模型 ====================

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


# ==================== 会话管理 ====================

async def cleanup_session(session_id: str, delay: int = SESSION_TIMEOUT):
    """在指定延迟后清理会话资源"""
    await asyncio.sleep(delay)
    if session_id in active_sessions:
        logger.info(f"清理过期会话: {session_id}")
        active_sessions.pop(session_id, None)
        message_queues.pop(session_id, None)
        script_statuses.pop(session_id, None)


# ==================== 脚本解析 ====================

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
            # 优先使用数据库中存储的文件路径
            if db_script.file_path and Path(db_script.file_path).exists():
                script_path = Path(db_script.file_path)
                logger.info(f"使用数据库存储的文件路径: {script_path}")
            else:
                # 如果数据库中没有文件路径或文件不存在，尝试重新同步
                logger.warning(f"数据库脚本文件路径无效，尝试重新同步: {db_script.file_path}")
                await database_script_service._sync_script_to_filesystem(db_script)

                # 重新获取更新后的脚本信息
                updated_script = await database_script_service.get_script(script_id)
                if updated_script and updated_script.file_path and Path(updated_script.file_path).exists():
                    script_path = Path(updated_script.file_path)
                    logger.info(f"重新同步后的文件路径: {script_path}")
                else:
                    # 如果仍然无法找到文件，使用默认路径生成逻辑
                    safe_name = "".join(c for c in db_script.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    safe_name = safe_name.replace(' ', '_')

                    if db_script.script_format == ScriptFormat.PLAYWRIGHT:
                        if not safe_name.endswith('.spec'):
                            safe_name = f"{safe_name}.spec"
                        script_path = PLAYWRIGHT_WORKSPACE / "e2e" / f"{safe_name}.ts"
                    else:
                        script_path = PLAYWRIGHT_WORKSPACE / "e2e" / f"{safe_name}.yaml"

                    logger.warning(f"使用默认路径: {script_path}")

            # 验证文件是否存在
            if not script_path.exists():
                raise FileNotFoundError(f"脚本文件不存在: {script_path}")

            return {
                "script_id": script_id,
                "name": db_script.name,
                "file_name": script_path.name,
                "path": str(script_path),
                "description": db_script.description or f"脚本: {db_script.name}",
                "source": "database"
            }
    except Exception as e:
        logger.warning(f"从数据库获取脚本失败: {script_id} - {e}")

    # 尝试从文件系统获取脚本（从独立存储目录）
    try:
        from app.services.filesystem_script_service import filesystem_script_service

        # 如果script_id不包含扩展名，尝试添加.spec.ts
        script_name = script_id
        if not script_name.endswith('.spec.ts'):
            script_name = f"{script_id}.spec.ts"

        script_info = await filesystem_script_service.get_script(script_name)
        if script_info:
            return {
                "script_id": script_id,
                "name": script_info["metadata"]["original_name"],
                "file_name": script_info["name"],
                "path": script_info["file_path"],
                "description": script_info["metadata"]["description"],
                "source": "filesystem"
            }
    except Exception as e:
        logger.warning(f"从文件系统获取脚本失败: {script_id} - {e}")

    # 脚本不存在
    raise HTTPException(status_code=404, detail=f"脚本不存在: {script_id}")


# ==================== 健康检查和工具接口 ====================

@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok", 
        "service": "unified-script-execution", 
        "timestamp": datetime.now().isoformat(),
        "workspace": str(PLAYWRIGHT_WORKSPACE),
        "workspace_exists": PLAYWRIGHT_WORKSPACE.exists()
    }


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


# ==================== 统一执行接口 ====================

@router.post("/execute-batch", response_model=UnifiedBatchExecutionResponse)
async def execute_scripts_batch(request: UnifiedBatchExecutionRequest):
    """
    批量执行脚本（统一接口）

    Args:
        request: 批量脚本执行请求

    Returns:
        UnifiedBatchExecutionResponse: 执行响应
    """
    try:
        # 解析所有脚本信息
        script_infos = []
        for script_id in request.script_ids:
            script_info = await resolve_script_by_id(script_id)
            script_infos.append(script_info)

        # 生成执行会话ID
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

        # 初始化脚本状态
        script_statuses[session_id] = {
            script_info["name"]: ScriptExecutionStatus(
                session_id=session_id,
                script_name=script_info["name"],
                status="pending"
            ) for script_info in script_infos
        }

        logger.info(f"✨ [BATCH] 创建批量脚本执行会话: {session_id} - {len(script_infos)}个脚本")

        # 立即创建消息队列并启动后台执行
        if session_id not in message_queues:
            message_queues[session_id] = asyncio.Queue()

        # 启动统一执行任务
        active_sessions[session_id]["status"] = "processing"
        task = asyncio.create_task(process_unified_execution_task(session_id))

        return UnifiedBatchExecutionResponse(
            session_id=session_id,
            script_count=len(script_infos),
            script_ids=request.script_ids,
            status="initialized",
            message=f"批量脚本执行会话已创建: {len(script_infos)}个脚本",
            sse_endpoint=f"/api/v1/web/execution/stream/{session_id}",
            created_at=session_data["created_at"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [BATCH] 创建批量脚本执行会话失败: {request.script_ids} - {e}")
        raise HTTPException(status_code=500, detail=f"创建批量执行会话失败: {str(e)}")


@router.post("/execute-by-id", response_model=UnifiedScriptExecutionResponse)
async def execute_script_by_id(request: UnifiedScriptExecutionRequest):
    """
    根据脚本ID执行脚本（统一接口）

    Args:
        request: 脚本执行请求

    Returns:
        UnifiedScriptExecutionResponse: 执行响应
    """
    # 🔥🔥🔥 强制输出 - 绝对会出现的日志 🔥🔥🔥
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    
    print("=" * 80, flush=True)
    print("🔥🔥🔥 [CRITICAL] 统一执行接口 /execute-by-id 被调用!", flush=True)
    print(f"🔥🔥🔥 [CRITICAL] 脚本ID: {request.script_id}", flush=True)
    print(f"🔥🔥🔥 [CRITICAL] 时间: {datetime.now()}", flush=True)
    print("=" * 80, flush=True)
    
    try:
        # 添加最详细的入口日志
        logger.error(f"🔥 [UNIFIED-ENTRY] 统一执行接口被调用: script_id={request.script_id}")
        logger.error(f"🔥 [UNIFIED-ENTRY] 请求完整内容: {request}")
        print(f"🔥 [UNIFIED-ENTRY] =============== 统一执行接口入口 ===============", flush=True)
        print(f"🔥 [UNIFIED-ENTRY] 脚本ID: {request.script_id}", flush=True)
        print(f"🔥 [UNIFIED-ENTRY] 执行配置: {request.execution_config}", flush=True)
        print(f"🔥 [UNIFIED-ENTRY] 环境变量: {request.environment_variables}", flush=True)
        print(f"🔥 [UNIFIED-ENTRY] =======================================", flush=True)
        
        print(f"🔍 [DEBUG] 开始解析脚本信息...", flush=True)
        # 解析脚本信息
        script_info = await resolve_script_by_id(request.script_id)
        print(f"✅ [DEBUG] 脚本信息解析成功: {script_info}", flush=True)

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

        logger.info(f"✨ [UNIFIED] 创建脚本执行会话: {session_id} - {script_info['name']}")

        # 立即创建消息队列并启动后台执行
        if session_id not in message_queues:
            message_queues[session_id] = asyncio.Queue()
            logger.info(f"📋 [UNIFIED] 为会话创建消息队列: {session_id}")

        # 启动统一执行任务
        active_sessions[session_id]["status"] = "processing"
        logger.info(f"🚀 [UNIFIED] 即将创建执行任务: {session_id}")
        task = asyncio.create_task(process_unified_execution_task(session_id))
        logger.info(f"✅ [UNIFIED] 执行任务已创建: {session_id}")

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
        logger.error(f"❌ [UNIFIED] 创建脚本执行会话失败: {request.script_id} - {e}")
        raise HTTPException(status_code=500, detail=f"创建执行会话失败: {str(e)}")


# ==================== SSE流式接口 ====================

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

    logger.info(f"🌊 [SSE] 开始脚本执行SSE流: {session_id}")

    # 创建消息队列（如果不存在）
    if session_id not in message_queues:
        message_queue = asyncio.Queue()
        message_queues[session_id] = message_queue
        logger.info(f"📋 [SSE] 创建消息队列: {session_id}")
    else:
        message_queue = message_queues[session_id]
        logger.info(f"📋 [SSE] 使用现有消息队列: {session_id}")

    # 设置会话超时清理
    background_tasks.add_task(cleanup_session, session_id)

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
    logger.info(f"🌊 [SSE] 开始生成脚本执行事件流: {session_id}")

    # 发送会话初始化事件
    init_data = json.dumps({
        "session_id": session_id,
        "status": "connected",
        "service": "unified_script_execution"
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
                logger.info(f"🔌 [SSE] 客户端断开连接: {session_id}")
                break

            # 尝试从队列获取消息（非阻塞）
            try:
                # 使用较短的超时时间，确保更频繁地检查连接状态
                message = await asyncio.wait_for(message_queue.get(), timeout=0.5)

                logger.debug(f"📨 [SSE] 成功从队列获取消息: {message.type} - {message.content[:50]}...")

                # 更新会话最后活动时间
                if session_id in active_sessions:
                    active_sessions[session_id]["last_activity"] = datetime.now().isoformat()

                # 确定事件类型
                event_type = message.type

                # 将消息转换为JSON字符串
                message_json = message.model_dump_json()

                logger.debug(f"📤 [SSE] 发送事件: id={message_id}, type={event_type}, region={message.region}")

                # 使用正确的SSE格式发送消息
                yield f"event: {event_type}\nid: {message_id}\ndata: {message_json}\n\n"
                message_id += 1

                # 如果是最终消息，继续保持连接
                if message.is_final and event_type == "final_result":
                    logger.info(f"🏁 [SSE] 收到最终结果，继续保持连接: {session_id}")

            except asyncio.TimeoutError:
                # 发送保持连接的消息
                ping_data = json.dumps({"timestamp": datetime.now().isoformat()})
                yield f"event: ping\nid: ping-{message_id}\ndata: {ping_data}\n\n"
                message_id += 1
                continue

    except Exception as e:
        logger.error(f"❌ [SSE] 生成事件流时出错: {str(e)}")
        error_data = json.dumps({
            "error": f"生成事件流时出错: {str(e)}"
        })
        yield f"event: error\nid: error-{message_id}\ndata: {error_data}\n\n"

    # 发送关闭事件
    close_data = json.dumps({
        "message": "流已关闭"
    })
    logger.info(f"🔚 [SSE] 事件流结束: {session_id}")
    yield f"event: close\nid: close-{message_id}\ndata: {close_data}\n\n"


# ==================== 统一执行处理函数 ====================

async def process_unified_execution_task(session_id: str):
    """处理统一脚本执行的后台任务"""
    logger.info(f"🚀 [TASK] 开始处理统一脚本执行任务: {session_id}")

    try:
        # 获取消息队列和会话信息
        message_queue = message_queues.get(session_id)
        session_info = active_sessions.get(session_id)

        logger.info(f"🔍 [TASK] 会话检查: message_queue={message_queue is not None}, session_info={session_info is not None}")
        
        if not message_queue or not session_info:
            logger.error(f"❌ [TASK] 会话 {session_id} 信息不完整: queue={message_queue is not None}, info={session_info is not None}")
            return

        # 更新会话状态
        active_sessions[session_id]["status"] = "processing"
        logger.info(f"📝 [TASK] 会话状态更新为: processing")

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
        logger.info(f"📤 [TASK] 已发送开始消息到队列")
        
        # 直接打印关键消息到控制台，确保可见
        print(f"🚀 [EXECUTION] 开始脚本执行流程... (session: {session_id})")
        logger.info(f"🚀 [EXECUTION] 开始脚本执行流程... (session: {session_id})")

        # 设置消息回调函数
        async def message_callback(ctx: ClosureContext, message: StreamMessage, message_ctx: MessageContext) -> None:
            try:
                current_queue = message_queues.get(session_id)
                if current_queue:
                    await current_queue.put(message)

                # 同步打印关键日志到后端控制台，便于在服务端看到全过程
                try:
                    _content = (message.content or "").strip()
                    if len(_content) > 500:
                        _content = _content[:500] + " ..."
                    level = "INFO"
                    if message.type in ("error", "final_result"):
                        level = "ERROR" if message.type == "error" else "SUCCESS"
                    logger.info(f"[{level}] [SSE] {message.type} | {message.source} | {message.region} | final={message.is_final} | {_content}")
                    
                    # 也直接打印到控制台确保可见
                    print(f"[{level}] [SSE] {message.type} | {message.source} | {_content}")
                except Exception as log_e:
                    logger.warning(f"打印SSE消息到控制台失败: {log_e}")
            except Exception as e:
                logger.error(f"消息回调处理错误: {str(e)}")

        # 创建响应收集器和编排器
        collector = StreamResponseCollector(platform=AgentPlatform.WEB)
        collector.set_callback(message_callback)
        orchestrator = get_web_orchestrator(collector=collector)
        logger.info(f"🎛️ [TASK] 编排器和收集器已创建")

        # 根据执行类型处理
        logger.info(f"🎯 [TASK] 执行类型: {session_info['type']}")
        if session_info["type"] == "single_script":
            logger.info(f"📝 [TASK] 开始执行单个脚本")
            await execute_single_unified_script(session_id, session_info, orchestrator, message_queue)
        elif session_info["type"] == "batch_scripts":
            logger.info(f"📦 [TASK] 开始执行批量脚本")
            await execute_batch_unified_scripts(session_id, session_info, orchestrator, message_queue)
        else:
            logger.error(f"❌ [TASK] 未知的执行类型: {session_info['type']}")

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
        logger.info(f"✅ [TASK] 脚本执行任务已完成: {session_id}")

    except Exception as e:
        logger.error(f"❌ [TASK] 处理统一脚本执行任务失败: {session_id} - {str(e)}")

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

    logger.info(f"🎯 [SINGLE] 开始执行统一脚本: {session_id} - {script_name}")
    logger.info(f"🔍 [SINGLE] 脚本信息: {script_info}")
    
    # 确保关键信息显示在控制台
    print(f"🎯 [EXECUTION] 开始执行脚本: {script_name} (session: {session_id})")

    try:
        # 更新脚本状态
        if session_id in script_statuses and script_name in script_statuses[session_id]:
            script_statuses[session_id][script_name].status = "running"
            script_statuses[session_id][script_name].start_time = datetime.now().isoformat()
            logger.info(f"📝 [SINGLE] 脚本状态更新为: running")

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
        logger.info(f"📤 [SINGLE] 已发送开始消息")

        # 创建Playwright执行请求
        playwright_request = PlaywrightExecutionRequest(
            session_id=session_id,
            script_id=script_info.get("script_id", script_info["name"]),
            script_name=script_info["file_name"],
            execution_config=session_info["execution_config"]
        )
        logger.info(f"🎭 [SINGLE] 创建Playwright请求: script_id={playwright_request.script_id}, script_name={playwright_request.script_name}")

        # 执行脚本
        logger.info(f"🚀 [SINGLE] 开始调用编排器执行 Playwright 脚本...")
        print(f"🚀 [EXECUTION] 调用 AdsPower + Playwright 执行脚本: {script_name}")
        await orchestrator.execute_playwright_script(playwright_request)
        logger.info(f"✅ [SINGLE] Playwright 脚本执行完成")
        print(f"✅ [EXECUTION] 脚本执行完成: {script_name}")

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
        logger.error(f"❌ [SINGLE] 执行统一脚本失败: {session_id} - {script_name} - {str(e)}")
        print(f"❌ [EXECUTION] 脚本执行失败: {script_name} - {str(e)}")

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

    logger.info(f"📦 [BATCH] 开始批量执行统一脚本: {session_id} - {len(script_infos)}个脚本")
    print(f"📦 [EXECUTION] 开始批量执行 {len(script_infos)} 个脚本")

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
        print(f"📊 [EXECUTION] 批量执行完成: 成功 {success_count}, 失败 {failed_count}")

    except Exception as e:
        logger.error(f"❌ [BATCH] 批量执行统一脚本失败: {session_id} - {str(e)}")
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
            script_id=script_info.get("script_id", script_info["name"]),
            script_name=script_info["file_name"],
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

"""
图片分析生成自然语言描述的API端点
支持上传图片并生成详细的测试用例描述
基于智能体架构和SSE流式接口
"""
import asyncio
import base64
import uuid
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from autogen_core import MessageContext, ClosureContext
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.core.messages import StreamMessage
from app.core.messages.web import WebMultimodalAnalysisRequest, AnalysisType

# 会话存储
active_sessions: Dict[str, Dict[str, Any]] = {}

# 消息队列存储
message_queues: Dict[str, asyncio.Queue] = {}

# 会话超时（秒）
SESSION_TIMEOUT = 3600  # 1小时

logger = logging.getLogger(__name__)
router = APIRouter()


async def cleanup_session(session_id: str, delay: int = SESSION_TIMEOUT):
    """在指定延迟后清理会话资源"""
    await asyncio.sleep(delay)
    if session_id in active_sessions:
        logger.info(f"清理过期会话: {session_id}")
        active_sessions.pop(session_id, None)
        message_queues.pop(session_id, None)


@router.get("/health")
async def health_check():
    """图片描述生成健康检查端点"""
    return {"status": "ok", "service": "image-to-description", "timestamp": datetime.now().isoformat()}


@router.post("/analyze-image-to-description")
async def analyze_image_to_description(
    file: UploadFile = File(...),
    analysis_type: str = Form("description_generation"),
    additional_context: Optional[str] = Form(None)
):
    """
    上传图片并启动AI描述生成任务
    
    Args:
        file: 上传的图片文件
        analysis_type: 分析类型，默认为description_generation
        additional_context: 额外上下文信息
        
    Returns:
        Dict: 包含session_id和SSE端点的响应
    """
    try:
        # 验证文件
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传有效的图片文件")
        
        # 读取文件内容
        file_content = await file.read()
        file_size = len(file_content)
        
        # 检查文件大小（限制为10MB）
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            raise HTTPException(status_code=400, detail=f"文件大小超过限制（{max_size // (1024*1024)}MB）")
        
        # 转换为base64
        image_base64 = base64.b64encode(file_content).decode('utf-8')
        
        # 生成会话ID
        session_id = str(uuid.uuid4())
        
        # 记录当前时间
        current_time = datetime.now()
        
        # 存储会话信息
        active_sessions[session_id] = {
            "status": "processing",  # 直接设置为处理中
            "created_at": current_time.isoformat(),
            "last_activity": current_time.isoformat(),
            "file_info": {
                "filename": file.filename,
                "content_type": file.content_type,
                "size": file_size,
                "image_data": image_base64
            },
            "analysis_type": analysis_type,
            "additional_context": additional_context or "",
            "progress": 0,
            "description_result": None
        }

        # 创建消息队列
        message_queue = asyncio.Queue()
        message_queues[session_id] = message_queue

        # 立即启动后台分析任务
        asyncio.create_task(process_description_generation_task(session_id))

        logger.info(f"图片描述生成任务已创建并启动: {session_id}, 文件: {file.filename}")

        return JSONResponse({
            "status": "success",
            "session_id": session_id,
            "sse_endpoint": f"/api/v1/web/create/stream-description/{session_id}",
            "message": "图片描述生成任务已启动",
            "analysis_type": analysis_type,
            "file_info": {
                "filename": file.filename,
                "size": file_size
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建图片描述生成任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/stream-description/{session_id}")
async def stream_description_generation(
    session_id: str,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    图片描述生成SSE流式端点

    Args:
        session_id: 会话ID
        request: HTTP请求对象
        background_tasks: 后台任务管理器

    Returns:
        EventSourceResponse: SSE响应流
    """
    # 验证会话是否存在
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

    logger.info(f"开始图片描述生成SSE流: {session_id}")

    async def event_generator():
        """事件生成器"""
        try:
            # 发送初始连接消息
            yield {
                "event": "connected",
                "data": json.dumps({
                    "session_id": session_id,
                    "status": "connected",
                    "message": "已连接到描述生成流"
                })
            }

            # 获取消息队列
            message_queue = message_queues.get(session_id)
            if not message_queue:
                yield {
                    "event": "error",
                    "data": json.dumps({
                        "session_id": session_id,
                        "error": "消息队列不存在",
                        "message": "会话已过期或无效"
                    })
                }
                return

            # 持续监听消息队列
            while True:
                try:
                    # 检查客户端是否断开连接
                    if await request.is_disconnected():
                        logger.info(f"客户端断开连接: {session_id}")
                        break

                    # 等待消息，设置超时
                    try:
                        message = await asyncio.wait_for(message_queue.get(), timeout=1.0)
                        
                        # 发送消息
                        yield {
                            "event": message.type,
                            "data": json.dumps({
                                "session_id": session_id,
                                "message_id": message.message_id,
                                "source": message.source,
                                "content": message.content,
                                "region": message.region,
                                "is_final": message.is_final,
                                "timestamp": datetime.now().isoformat()
                            })
                        }

                        # 如果是最终消息，结束流
                        if message.is_final:
                            break

                    except asyncio.TimeoutError:
                        # 发送心跳消息
                        yield {
                            "event": "heartbeat",
                            "data": json.dumps({
                                "session_id": session_id,
                                "timestamp": datetime.now().isoformat()
                            })
                        }

                except Exception as e:
                    logger.error(f"处理消息时出错: {str(e)}")
                    yield {
                        "event": "error",
                        "data": json.dumps({
                            "session_id": session_id,
                            "error": str(e),
                            "message": "处理消息时出错"
                        })
                    }
                    break

        except Exception as e:
            logger.error(f"事件生成器错误: {str(e)}")
            yield {
                "event": "error",
                "data": json.dumps({
                    "session_id": session_id,
                    "error": str(e),
                    "message": "流式传输错误"
                })
            }

    # 设置会话清理任务
    background_tasks.add_task(cleanup_session, session_id)

    # 返回SSE响应
    response = EventSourceResponse(event_generator(), media_type="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"  # 禁用Nginx缓冲
    
    return response


async def process_description_generation_task(session_id: str):
    """
    处理图片描述生成任务
    
    Args:
        session_id: 会话ID
    """
    try:
        logger.info(f"开始处理图片描述生成任务: {session_id}")
        
        # 获取会话信息
        if session_id not in active_sessions:
            raise Exception(f"会话 {session_id} 不存在")
        
        session_info = active_sessions[session_id]
        message_queue = message_queues.get(session_id)
        
        if not message_queue:
            raise Exception(f"消息队列 {session_id} 不存在")

        # 发送开始消息
        start_message = StreamMessage(
            message_id=f"start-{uuid.uuid4()}",
            type="message",
            source="图片描述生成器",
            content="🔍 开始分析图片，生成测试用例描述...",
            region="analysis",
            platform="web",
            is_final=False,
        )
        await message_queue.put(start_message)

        # 更新进度
        active_sessions[session_id]["progress"] = 10
        active_sessions[session_id]["last_activity"] = datetime.now().isoformat()

        # 设置消息回调函数
        async def message_callback(ctx: ClosureContext, message: StreamMessage, message_ctx: MessageContext) -> None:
            """处理来自智能体的消息"""
            try:
                await message_queue.put(message)
                logger.debug(f"收到智能体消息: {message.content[:100]}...")
            except Exception as e:
                logger.error(f"消息回调处理错误: {str(e)}")

        # 创建响应收集器
        from app.core.agents import StreamResponseCollector
        from app.core.types import AgentPlatform
        collector = StreamResponseCollector(platform=AgentPlatform.WEB)
        collector.set_callback(message_callback)

        # 获取Web编排器
        from app.services.web.orchestrator_service import get_web_orchestrator
        orchestrator = get_web_orchestrator(collector=collector)

        # 获取文件信息
        file_info = session_info["file_info"]
        additional_context = session_info["additional_context"]

        # 更新进度
        active_sessions[session_id]["progress"] = 30

        # 使用编排器执行图片描述生成
        await orchestrator.generate_description_from_image(
            session_id=session_id,
            image_data=file_info["image_data"],
            additional_context=additional_context
        )

        # 发送完成消息
        final_message = StreamMessage(
            message_id=f"final-{uuid.uuid4()}",
            type="final_result",
            source="图片描述生成器",
            content="✅ 图片分析完成，测试用例描述已生成",
            region="analysis",
            platform="web",
            is_final=True,
        )
        await message_queue.put(final_message)

        # 更新会话状态
        active_sessions[session_id]["status"] = "completed"
        active_sessions[session_id]["progress"] = 100
        active_sessions[session_id]["completed_at"] = datetime.now().isoformat()
        active_sessions[session_id]["last_activity"] = datetime.now().isoformat()

        logger.info(f"图片描述生成任务已完成: {session_id}")
        
    except Exception as e:
        logger.error(f"图片描述生成任务失败: {str(e)}")
        
        # 发送错误消息
        try:
            error_message = StreamMessage(
                message_id=f"error-{uuid.uuid4()}",
                type="error",
                source="图片描述生成器",
                content=f"❌ 分析过程出错: {str(e)}",
                region="analysis",
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


@router.get("/status/{session_id}")
async def get_description_status(session_id: str):
    """获取描述生成状态"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

    session_info = active_sessions[session_id]

    return JSONResponse({
        "success": True,
        "data": {
            "session_id": session_id,
            "status": session_info["status"],
            "progress": session_info.get("progress", 0),
            "created_at": session_info["created_at"],
            "last_activity": session_info["last_activity"],
            "error": session_info.get("error"),
            "completed_at": session_info.get("completed_at"),
            "file_info": {
                "filename": session_info["file_info"]["filename"],
                "size": session_info["file_info"]["size"]
            }
        }
    })

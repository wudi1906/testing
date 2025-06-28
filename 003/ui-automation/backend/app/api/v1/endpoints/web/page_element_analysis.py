"""
Web页面分析 - 页面截图智能分析API
支持SSE流式接口和页面元素识别
"""
from autogen_core import CancellationToken, MessageContext, ClosureContext
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks, File, UploadFile, Form
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
import asyncio
import logging
import uuid
import json
import base64
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.messages import StreamMessage
from app.core.messages.web import WebMultimodalAnalysisRequest
from app.database.connection import db_manager
from app.database.repositories.page_analysis_repository import PageAnalysisRepository, PageElementRepository

router = APIRouter()

# 设置日志记录器
logger = logging.getLogger(__name__)

# 会话存储
active_sessions: Dict[str, Dict[str, Any]] = {}

# 消息队列存储
message_queues: Dict[str, asyncio.Queue] = {}

# 会话超时（秒）
SESSION_TIMEOUT = 3600  # 1小时


async def get_db_session():
    """获取数据库会话"""
    try:
        logger.info("正在获取数据库会话...")
        async with db_manager.get_session() as session:
            logger.info("数据库会话获取成功")
            yield session
    except Exception as e:
        logger.error(f"获取数据库会话失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        raise


async def cleanup_session(session_id: str, delay: int = SESSION_TIMEOUT):
    """在指定延迟后清理会话资源"""
    await asyncio.sleep(delay)
    if session_id in active_sessions:
        logger.info(f"清理过期会话: {session_id}")
        active_sessions.pop(session_id, None)
        message_queues.pop(session_id, None)


@router.get("/health")
async def health_check():
    """页面分析健康检查端点"""
    return {"status": "ok", "service": "web-page-analysis", "timestamp": datetime.now().isoformat()}


@router.post("/upload-and-analyze")
async def upload_and_analyze_pages(
    files: List[UploadFile] = File(...),
    description: Optional[str] = Form(None),
    page_url: Optional[str] = Form(None),
    page_name: Optional[str] = Form(None)
):
    """
    上传页面截图并启动AI分析任务
    
    Args:
        files: 上传的图片文件列表
        description: 页面描述
        page_url: 页面URL（可选）
        page_name: 页面名称（可选）
        
    Returns:
        Dict: 包含session_id的响应
    """
    try:
        # 验证文件
        if not files:
            raise HTTPException(status_code=400, detail="请至少上传一个文件")
        
        # 验证每个文件
        validated_files = []
        for file in files:
            # 验证文件类型
            if not file.content_type or not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail=f"文件 {file.filename} 不是有效的图片文件")
            
            # 验证文件大小（10MB限制）
            content = await file.read()
            file_size = len(content)
            if file_size > 10 * 1024 * 1024:  # 10MB
                raise HTTPException(status_code=400, detail=f"图片文件 {file.filename} 大小不能超过10MB")
            
            # 转换为base64
            image_base64 = base64.b64encode(content).decode('utf-8')
            
            validated_files.append({
                "filename": file.filename,
                "content_type": file.content_type,
                "size": file_size,
                "image_data": image_base64
            })
        
        # 生成会话ID
        session_id = str(uuid.uuid4())

        # 记录当前时间
        current_time = datetime.now()

        # 不设置默认值，保持用户输入的原始值（可能为空）
        final_page_name = page_name.strip() if page_name else None
        final_description = description.strip() if description else None

        # 存储会话信息
        active_sessions[session_id] = {
            "status": "processing",  # 直接设置为处理中
            "created_at": current_time.isoformat(),
            "last_activity": current_time.isoformat(),
            "files": validated_files,
            "page_info": {
                "description": final_description,
                "page_url": page_url.strip() if page_url else None,
                "page_name": final_page_name
            },
            "analysis_results": [],
            "progress": 0,
            "total_files": len(validated_files),
            "processed_files": 0
        }

        # 创建消息队列
        message_queue = asyncio.Queue()
        message_queues[session_id] = message_queue

        # 立即启动后台分析任务
        asyncio.create_task(process_page_analysis_task(session_id))

        logger.info(f"页面分析任务已创建并启动: {session_id}, 文件数量: {len(validated_files)}")

        return JSONResponse({
            "success": True,
            "message": "页面分析任务已启动，正在后台处理",
            "data": {
                "session_id": session_id,
                "status": "processing",
                "uploaded_files": [f["filename"] for f in validated_files],
                "analysis_started": True,
                "sse_endpoint": f"/api/v1/web/page-analysis/stream/{session_id}",
                "status_endpoint": f"/api/v1/web/page-analysis/status/{session_id}",
                "files_info": [
                    {
                        "filename": f["filename"],
                        "size": f["size"]
                    } for f in validated_files
                ]
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建页面分析任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建分析任务失败: {str(e)}")


@router.get("/stream/{session_id}")
async def stream_page_analysis(
    session_id: str,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    页面分析SSE流式端点

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

    logger.info(f"开始页面分析SSE流: {session_id}")

    # 确保消息队列存在
    if session_id not in message_queues:
        message_queue = asyncio.Queue()
        message_queues[session_id] = message_queue
        logger.info(f"创建消息队列: {session_id}")
    else:
        message_queue = message_queues[session_id]
        logger.info(f"使用现有消息队列: {session_id}")

    # 设置会话超时清理
    background_tasks.add_task(cleanup_session, session_id)
    
    # 返回SSE响应
    response = EventSourceResponse(
        page_analysis_event_generator(session_id, request),
        media_type="text/event-stream"
    )
    
    # 添加必要的响应头
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"  # 禁用Nginx缓冲
    
    return response


async def page_analysis_event_generator(session_id: str, request: Request):
    """生成页面分析SSE事件流"""
    logger.info(f"开始生成页面分析事件流: {session_id}")
    
    # 发送会话初始化事件
    init_data = json.dumps({
        "session_id": session_id,
        "status": "connected",
        "service": "web_page_analysis"
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


async def process_page_analysis_task(session_id: str):
    """处理页面分析的后台任务"""
    logger.info(f"开始执行页面分析任务: {session_id}")
    
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
        
        # 会话状态已在上传时设置为processing

        # 发送开始消息
        message = StreamMessage(
            message_id=f"system-{uuid.uuid4()}",
            type="message",
            source="系统",
            content="🚀 开始页面分析流程...",
            region="process",
            platform="web",
            is_final=False,
        )
        await message_queue.put(message)


        # 设置消息回调函数
        async def message_callback(ctx: ClosureContext, message: StreamMessage, message_ctx: MessageContext) -> None:
            try:
                # 获取当前队列（确保使用最新的队列引用）
                current_queue = message_queues.get(session_id)
                if current_queue:
                    await current_queue.put(message)
                else:
                    logger.error(f"消息回调：会话 {session_id} 的队列不存在")

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

        # 获取页面信息
        page_info = session_info["page_info"]
        files = session_info["files"]

        # 处理每个上传的文件
        for i, file_info in enumerate(files):
            try:
                # 更新进度
                progress = int((i / len(files)) * 100)
                active_sessions[session_id]["progress"] = progress
                active_sessions[session_id]["processed_files"] = i
                active_sessions[session_id]["last_activity"] = datetime.now().isoformat()

                # 发送处理进度消息
                progress_message = StreamMessage(
                    message_id=f"progress-{uuid.uuid4()}",
                    type="message",
                    source="系统",
                    content=f"📸 正在分析第 {i+1}/{len(files)} 个页面截图: {file_info['filename']} ({progress}%)",
                    region="process",
                    platform="web",
                    is_final=False,
                )
                await message_queue.put(progress_message)

                # 为每个文件生成独立的分析ID，但保持原始session_id
                file_analysis_id = f"{session_id}_file_{i}"

                # 使用编排器执行页面分析
                await orchestrator.analyze_page_elements(
                    session_id=file_analysis_id,  # 使用独立的分析ID
                    image_data=file_info["image_data"],
                    page_name=page_info.get("page_name", "") if page_info.get("page_name", "") else "",
                    page_description=page_info.get("description", "") if page_info.get("description", "") else "",
                    page_url=page_info.get("page_url", "")
                )

                # 更新完成的文件数
                active_sessions[session_id]["processed_files"] = i + 1

            except Exception as e:
                logger.error(f"处理文件 {file_info['filename']} 失败: {str(e)}")
                # 发送错误消息但继续处理其他文件
                error_message = StreamMessage(
                    message_id=f"error-{uuid.uuid4()}",
                    type="message",
                    source="系统",
                    content=f"❌ 文件 {file_info['filename']} 分析失败: {str(e)}",
                    region="process",
                    platform="web",
                    is_final=False,
                )
                await message_queue.put(error_message)
        
        # 发送最终结果
        final_message = StreamMessage(
            message_id=f"final-{uuid.uuid4()}",
            type="final_result",
            source="系统",
            content="✅ 页面分析流程完成，分析结果已保存到数据库",
            region="process",
            platform="web",
            is_final=True,
        )
        await message_queue.put(final_message)

        # 更新会话状态
        active_sessions[session_id]["status"] = "completed"
        active_sessions[session_id]["progress"] = 100
        active_sessions[session_id]["processed_files"] = len(files)
        active_sessions[session_id]["completed_at"] = datetime.now().isoformat()
        active_sessions[session_id]["last_activity"] = datetime.now().isoformat()

        logger.info(f"页面分析任务已完成: {session_id}")
        
    except Exception as e:
        logger.error(f"页面分析任务失败: {str(e)}")
        
        # 发送错误消息
        try:
            error_message = StreamMessage(
                message_id=f"error-{uuid.uuid4()}",
                type="error",
                source="系统",
                content=f"❌ 分析过程出错: {str(e)}",
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





@router.get("/sessions")
async def list_sessions():
    """列出所有活动会话"""
    return JSONResponse({
        "sessions": active_sessions,
        "total": len(active_sessions)
    })


@router.get("/status/{session_id}")
async def get_analysis_status(session_id: str):
    """获取分析状态"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

    session_info = active_sessions[session_id]

    return JSONResponse({
        "success": True,
        "data": {
            "session_id": session_id,
            "status": session_info["status"],
            "progress": session_info.get("progress", 0),
            "total_files": session_info.get("total_files", 0),
            "processed_files": session_info.get("processed_files", 0),
            "created_at": session_info["created_at"],
            "last_activity": session_info["last_activity"],
            "error": session_info.get("error"),
            "completed_at": session_info.get("completed_at"),
            "page_info": session_info["page_info"]
        }
    })

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """获取指定会话的信息"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

    return JSONResponse(active_sessions[session_id])


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除指定会话"""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

    # 删除会话资源
    active_sessions.pop(session_id, None)
    message_queues.pop(session_id, None)

    return JSONResponse({
        "status": "success",
        "message": f"会话 {session_id} 已删除"
    })


@router.get("/pages")
async def get_page_list(
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_db_session)
):
    """获取页面列表"""
    try:
        logger.info(f"开始获取页面列表，页码: {page}, 页面大小: {page_size}")

        repo = PageAnalysisRepository()

        if search:
            logger.info(f"搜索页面，关键词: {search}")
            pages = await repo.search_by_page_name(session, search, limit=page_size)
        else:
            # 获取所有页面
            logger.info("获取所有页面")
            from sqlalchemy import select, desc
            from app.database.models.page_analysis import PageAnalysisResult

            query = select(PageAnalysisResult).order_by(desc(PageAnalysisResult.created_at))
            result = await session.execute(query.limit(page_size).offset((page - 1) * page_size))
            pages = result.scalars().all()

        logger.info(f"查询到 {len(pages)} 条页面记录")

        # 转换为响应格式
        page_data = []
        for page_obj in pages:
            try:
                logger.debug(f"处理页面: {page_obj.id}")

                # 使用改进后的to_dict方法
                page_dict = page_obj.to_dict()

                # 添加分析状态（基于置信度和元素数量推断）
                elements_count = page_dict.get('elements_count', 0) or 0
                confidence_score = page_dict.get('confidence_score', 0) or 0

                if elements_count > 0 and confidence_score > 0:
                    page_dict['analysis_status'] = 'completed'
                elif elements_count == 0:
                    page_dict['analysis_status'] = 'pending'
                else:
                    page_dict['analysis_status'] = 'analyzing'

                page_data.append(page_dict)
                logger.debug(f"页面 {page_obj.id} 处理成功")

            except Exception as page_error:
                logger.error(f"处理页面 {page_obj.id} 时出错: {page_error}")
                import traceback
                logger.error(f"页面处理详细错误: {traceback.format_exc()}")

                # 创建一个最小的安全字典
                safe_dict = {
                    "id": str(page_obj.id) if hasattr(page_obj, 'id') and page_obj.id else None,
                    "page_name": str(page_obj.page_name) if hasattr(page_obj, 'page_name') and page_obj.page_name else "未知页面",
                    "analysis_status": "error",
                    "error": "数据处理错误",
                    "confidence_score": 0.0,
                    "elements_count": 0,
                    "created_at": None,
                    "updated_at": None
                }
                page_data.append(safe_dict)

        # 构建响应数据
        response_data = {
            "success": True,
            "data": page_data,
            "total": len(page_data),
            "page": page,
            "page_size": page_size
        }

        logger.info(f"成功获取页面列表，共 {len(page_data)} 条记录")
        return response_data

    except Exception as e:
        logger.error(f"获取页面列表失败: {e}")
        import traceback
        logger.error(f"详细错误信息: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取页面列表失败: {str(e)}")


@router.get("/pages/{page_id}/elements")
async def get_page_elements(
    page_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """获取页面元素列表"""
    try:
        element_repo = PageElementRepository()
        elements = await element_repo.get_by_analysis_id(session, page_id)
        
        element_data = [element.to_dict() for element in elements]
        
        return JSONResponse({
            "success": True,
            "data": element_data,
            "total": len(element_data)
        })
        
    except Exception as e:
        logger.error(f"获取页面元素失败: {e}")
        raise HTTPException(status_code=500, detail="获取页面元素失败")


@router.delete("/pages/{page_id}")
async def delete_page(
    page_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """删除页面"""
    try:
        repo = PageAnalysisRepository()
        page = await repo.get_by_id(session, page_id)
        
        if not page:
            raise HTTPException(status_code=404, detail="页面不存在")
        
        # 删除页面记录（级联删除元素）
        await session.delete(page)
        await session.commit()
        
        return JSONResponse({
            "success": True,
            "message": "页面删除成功"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除页面失败: {e}")
        await session.rollback()
        raise HTTPException(status_code=500, detail="删除页面失败")

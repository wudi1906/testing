"""
基于自然语言文本生成测试脚本的API端点
支持从纯文本描述生成YAML和Playwright测试脚本
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.messages.web import WebMultimodalAnalysisRequest
from app.services.web.orchestrator_service import get_web_orchestrator
from app.core.agents import StreamResponseCollector
from app.core.types import AgentPlatform
# 会话存储
active_sessions: Dict[str, Dict[str, Any]] = {}

logger = get_logger(__name__)
router = APIRouter()


class TextToScriptRequest(BaseModel):
    """基于文本生成脚本的请求模型"""
    test_description: str
    generate_formats: List[str] = ["playwright"]
    additional_context: Optional[str] = None


@router.post("/generate-from-text")
async def generate_test_from_text(
    request: TextToScriptRequest,
    background_tasks: BackgroundTasks
):
    """
    基于自然语言文本生成测试脚本
    
    Args:
        request: 文本生成请求
        background_tasks: 后台任务管理器
        
    Returns:
        生成结果，包含session_id和SSE端点
    """
    try:
        # 生成会话ID
        session_id = str(uuid.uuid4())
        
        logger.info(f"开始基于文本生成测试脚本: {session_id}")
        logger.info(f"测试描述: {request.test_description[:100]}...")
        logger.info(f"生成格式: {request.generate_formats}")
        
        # 验证生成格式
        supported_formats = ["yaml", "playwright"]
        invalid_formats = [f for f in request.generate_formats if f not in supported_formats]
        if invalid_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的生成格式: {invalid_formats}，支持的格式: {supported_formats}"
            )
        
        # 创建分析请求（模拟图片分析的结构，但不包含图片数据）
        analysis_request = WebMultimodalAnalysisRequest(
            session_id=session_id,
            image_data="",  # 空图片数据，表示基于文本生成
            test_description=request.test_description,
            additional_context=request.additional_context or "",
            generate_formats=request.generate_formats
        )
        
        # 存储会话信息
        active_sessions[session_id] = {
            "request": analysis_request.model_dump(),
            "status": "initialized",
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "generation_type": "text_to_script",
            "database_config": {
                "save_to_database": True,
                "script_name": f"AI文本生成_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "script_description": request.test_description[:100] + "...",
                "tags": ["AI生成", "文本生成", "自动化测试"],
                "category": "文本生成",
                "priority": 1
            }
        }
        
        # 构建SSE端点URL
        sse_endpoint = f"/api/v1/web/create/stream-text-generation/{session_id}"
        
        logger.info(f"文本生成会话创建成功: {session_id}")
        
        return JSONResponse({
            "status": "success",
            "session_id": session_id,
            "sse_endpoint": sse_endpoint,
            "message": "文本生成任务已启动",
            "generation_type": "text_to_script",
            "supported_formats": request.generate_formats
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建文本生成任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/stream-text-generation/{session_id}")
async def stream_text_generation(
    session_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    start_processing: bool = True
):
    """
    文本生成SSE流式端点
    
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
    
    session_info = active_sessions[session_id]
    
    # 验证是否为文本生成会话
    if session_info.get("generation_type") != "text_to_script":
        raise HTTPException(status_code=400, detail="会话类型不匹配")
    
    logger.info(f"开始文本生成SSE流: {session_id}")
    
    async def text_generation_event_generator():
        """文本生成事件生成器"""
        try:
            # 发送初始连接消息
            yield {
                "event": "connected",
                "data": {
                    "session_id": session_id,
                    "status": "connected",
                    "message": "已连接到文本生成流"
                }
            }
            
            # 等待处理完成或客户端断开连接
            max_wait_time = 300  # 5分钟超时
            wait_interval = 1
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                # 检查客户端是否断开连接
                if await request.is_disconnected():
                    logger.info(f"客户端断开连接: {session_id}")
                    break
                
                # 检查会话状态
                if session_id not in active_sessions:
                    logger.warning(f"会话已被清理: {session_id}")
                    break
                
                current_session = active_sessions[session_id]
                status = current_session.get("status", "unknown")
                
                # 发送状态更新
                yield {
                    "event": "status",
                    "data": {
                        "session_id": session_id,
                        "status": status,
                        "elapsed_time": elapsed_time
                    }
                }
                
                # 如果处理完成，发送完成消息
                if status == "completed":
                    result = current_session.get("result", {})
                    yield {
                        "event": "completed",
                        "data": {
                            "session_id": session_id,
                            "status": "completed",
                            "result": result,
                            "message": "文本生成完成"
                        }
                    }
                    break
                
                # 如果处理失败，发送错误消息
                if status == "failed":
                    error = current_session.get("error", "未知错误")
                    yield {
                        "event": "error",
                        "data": {
                            "session_id": session_id,
                            "status": "failed",
                            "error": error,
                            "message": "文本生成失败"
                        }
                    }
                    break
                
                await asyncio.sleep(wait_interval)
                elapsed_time += wait_interval
            
            # 超时处理
            if elapsed_time >= max_wait_time:
                yield {
                    "event": "timeout",
                    "data": {
                        "session_id": session_id,
                        "status": "timeout",
                        "message": "文本生成超时"
                    }
                }
                
        except Exception as e:
            logger.error(f"文本生成事件生成器错误: {str(e)}")
            yield {
                "event": "error",
                "data": {
                    "session_id": session_id,
                    "status": "error",
                    "error": str(e),
                    "message": "流式传输错误"
                }
            }
    
    # 设置会话超时清理
    async def cleanup_session(session_id: str):
        """清理会话"""
        await asyncio.sleep(3600)  # 1小时后清理
        if session_id in active_sessions:
            logger.info(f"清理文本生成会话: {session_id}")
            del active_sessions[session_id]
    
    background_tasks.add_task(cleanup_session, session_id)
    
    # 如果需要开始处理，启动生成任务
    if start_processing and active_sessions[session_id]["status"] == "initialized":
        logger.info(f"启动文本生成处理任务: {session_id}")
        asyncio.create_task(
            process_text_generation_task(session_id)
        )
    
    # 返回SSE响应
    response = EventSourceResponse(
        text_generation_event_generator(),
        media_type="text/event-stream"
    )
    
    # 添加必要的响应头
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"  # 禁用Nginx缓冲
    
    return response


async def process_text_generation_task(session_id: str):
    """
    处理文本生成任务
    
    Args:
        session_id: 会话ID
    """
    try:
        logger.info(f"开始处理文本生成任务: {session_id}")
        
        # 获取会话信息
        if session_id not in active_sessions:
            raise Exception(f"会话 {session_id} 不存在")
        
        session_info = active_sessions[session_id]
        
        # 更新状态为处理中
        active_sessions[session_id]["status"] = "processing"
        active_sessions[session_id]["last_activity"] = datetime.now().isoformat()
        
        # 创建流响应收集器
        collector = StreamResponseCollector(platform=AgentPlatform.WEB)
        
        # 获取Web编排器
        orchestrator = get_web_orchestrator(collector=collector)
        
        # 获取请求数据
        request_data = session_info["request"]
        
        # 执行文本到脚本生成流程
        generate_formats = request_data.get("generate_formats", ["yaml"])
        await orchestrator.generate_scripts_from_text(
            session_id=session_id,
            test_description=request_data["test_description"],
            additional_context=request_data.get("additional_context", ""),
            generate_formats=generate_formats
        )
        
        # 更新状态为完成
        active_sessions[session_id]["status"] = "completed"
        active_sessions[session_id]["last_activity"] = datetime.now().isoformat()
        
        logger.info(f"文本生成任务完成: {session_id}")
        
    except Exception as e:
        logger.error(f"文本生成任务失败: {session_id}, 错误: {str(e)}")
        
        # 更新状态为失败
        if session_id in active_sessions:
            active_sessions[session_id]["status"] = "failed"
            active_sessions[session_id]["error"] = str(e)
            active_sessions[session_id]["last_activity"] = datetime.now().isoformat()
        
        raise

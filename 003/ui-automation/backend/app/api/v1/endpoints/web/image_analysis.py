"""
Web图片分析 - 集成数据库的完整API
支持SSE流式接口和数据库脚本保存
"""
from autogen_core import CancellationToken, MessageContext, ClosureContext
from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
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

from app.core.agents import StreamResponseCollector
from app.core.messages import StreamMessage
from app.core.messages.web import WebMultimodalAnalysisRequest
from app.core.types import AgentPlatform
from app.services.web.orchestrator_service import get_web_orchestrator


router = APIRouter()

# 设置日志记录器
logger = logging.getLogger(__name__)

# 会话存储
active_sessions: Dict[str, Dict[str, Any]] = {}

# 消息队列存储
message_queues: Dict[str, asyncio.Queue] = {}

# 反馈队列存储
feedback_queues: Dict[str, asyncio.Queue] = {}

# 会话超时（秒）
SESSION_TIMEOUT = 3600  # 1小时

ssss = ""
async def cleanup_session(session_id: str, delay: int = SESSION_TIMEOUT):
    """在指定延迟后清理会话资源"""
    await asyncio.sleep(delay)
    if session_id in active_sessions:
        logger.info(f"清理过期会话: {session_id}")
        active_sessions.pop(session_id, None)
        message_queues.pop(session_id, None)
        feedback_queues.pop(session_id, None)


@router.get("/health")
async def health_check():
    """SSE健康检查端点"""
    return {"status": "ok", "service": "web-image-analysis-sse", "timestamp": datetime.now().isoformat()}


@router.get("/platforms")
async def get_supported_platforms():
    """获取支持的平台列表"""
    return {
        "platforms": [
            {
                "id": "web",
                "name": "Web平台",
                "description": "Web应用UI自动化测试",
                "status": "active",
                "features": ["图片分析", "YAML生成", "Playwright生成", "脚本执行"]
            },
            {
                "id": "android",
                "name": "Android平台",
                "description": "Android应用UI自动化测试",
                "status": "development",
                "features": ["图片分析", "测试用例生成"]
            },
            {
                "id": "api",
                "name": "API测试",
                "description": "API接口自动化测试",
                "status": "planned",
                "features": ["接口分析", "测试用例生成"]
            }
        ],
        "total": 3,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/analyze/image")
async def start_web_image_analysis(
    file: UploadFile = File(...),
    test_description: str = Form(...),
    additional_context: Optional[str] = Form(None),
    generate_formats: str = Form("yaml"),
    save_to_database: bool = Form(True),
    script_name: Optional[str] = Form(None),
    script_description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON字符串格式的标签列表
    category: Optional[str] = Form(None),
    priority: int = Form(1)
):
    """
    启动Web图片分析任务，支持自动保存到数据库

    Args:
        file: 上传的图片文件
        test_description: 测试需求描述
        additional_context: 额外上下文信息
        generate_formats: 生成格式，逗号分隔（如: "yaml,playwright"）
        save_to_database: 是否自动保存到数据库
        script_name: 脚本名称（可选）
        script_description: 脚本描述（可选）
        tags: 标签列表（JSON字符串格式）
        category: 脚本分类
        priority: 优先级（1-5）

    Returns:
        Dict: 包含session_id的响应
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请上传有效的图片文件")
        
        # 验证文件大小（5MB限制）
        file_size = 0
        content = await file.read()
        file_size = len(content)
        if file_size > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(status_code=400, detail="图片文件大小不能超过5MB")
        
        # 转换为base64
        image_base64 = base64.b64encode(content).decode('utf-8')
        
        # 解析生成格式
        try:
            formats_list = [f.strip() for f in generate_formats.split(",")]
        except:
            formats_list = ["yaml"]
        
        # 生成会话ID
        session_id = str(uuid.uuid4())
        
        # 解析标签
        tag_list = []
        if tags:
            try:
                tag_list = json.loads(tags)
            except json.JSONDecodeError:
                logger.warning(f"标签解析失败，使用空列表: {tags}")

        # 创建分析请求
        analysis_request = WebMultimodalAnalysisRequest(
            session_id=session_id,
            image_data=image_base64,
            test_description=test_description,
            additional_context=additional_context or "",
            generate_formats=formats_list
        )

        # 存储会话信息，包含数据库配置
        active_sessions[session_id] = {
            "request": analysis_request.model_dump(),
            "status": "initialized",
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "file_info": {
                "filename": file.filename,
                "content_type": file.content_type,
                "size": file_size
            },
            "database_config": {
                "save_to_database": save_to_database,
                "script_name": script_name,
                "script_description": script_description,
                "tags": tag_list,
                "category": category,
                "priority": priority
            }
        }
        
        logger.info(f"Web图片分析任务已创建: {session_id}")
        
        return JSONResponse({
            "session_id": session_id,
            "status": "initialized",
            "message": "分析任务已创建，请使用SSE连接获取实时进度",
            "sse_endpoint": f"/api/v1/web/create/stream/{session_id}",
            "file_info": {
                "filename": file.filename,
                "size": file_size
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建Web图片分析任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建分析任务失败: {str(e)}")


@router.get("/stream/{session_id}")
async def stream_web_analysis(
    session_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    start_processing: bool = True
):
    """
    Web图片分析SSE流式端点
    
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
    
    logger.info(f"开始Web图片分析SSE流: {session_id}")
    
    # 创建消息队列
    if session_id not in message_queues:
        message_queue = asyncio.Queue()
        message_queues[session_id] = message_queue
        logger.info(f"创建消息队列: {session_id}, 队列ID: {id(message_queue)}")
    else:
        message_queue = message_queues[session_id]
        logger.info(f"使用现有消息队列: {session_id}, 队列ID: {id(message_queue)}")
    
    # 创建反馈队列
    if session_id not in feedback_queues:
        feedback_queue = asyncio.Queue()
        feedback_queues[session_id] = feedback_queue
        logger.info(f"创建反馈队列: {session_id}")
    
    # 设置会话超时清理
    background_tasks.add_task(cleanup_session, session_id)
    
    # 如果需要开始处理，启动分析任务
    if start_processing and active_sessions[session_id]["status"] == "initialized":
        logger.info(f"启动Web图片分析处理任务: {session_id}")
        asyncio.create_task(
            process_web_analysis_task(session_id)
        )
    
    # 返回SSE响应
    response = EventSourceResponse(
        web_event_generator(session_id, request),
        media_type="text/event-stream"
    )
    
    # 添加必要的响应头
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"  # 禁用Nginx缓冲
    
    return response


async def web_event_generator(session_id: str, request: Request):
    """生成Web分析SSE事件流"""
    logger.info(f"开始生成Web分析事件流: {session_id}")
    
    # 发送会话初始化事件
    init_data = json.dumps({
        "session_id": session_id,
        "status": "connected",
        "service": "web_image_analysis"
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
                # 记录队列状态
                logger.debug(f"尝试从队列获取消息，队列ID: {id(message_queue)}, 队列大小: {message_queue.qsize()}")

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
                # 记录发送的消息（截断长消息以避免日志过大）
                content_preview = message.content
                if content_preview and len(content_preview) > 100:
                    content_preview = content_preview[:100] + "..."
                
                logger.debug(f"发送事件: id={message_id}, type={event_type}, region={message.region}, content={content_preview}")
                
                # 使用正确的SSE格式发送消息
                yield f"event: {event_type}\nid: {message_id}\ndata: {message_json}\n\n"
                message_id += 1
                
                # 如果是最终消息，可以选择是否结束流
                if message.is_final and event_type == "final_result":
                    logger.info(f"收到最终结果，继续保持连接: {session_id}")
                    # 不立即结束，让前端决定何时断开
                
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


async def process_web_analysis_task(session_id: str):
    """处理Web图片分析的后台任务"""
    logger.info(f"开始执行Web图片分析任务: {session_id}")
    
    try:
        # 获取消息队列
        message_queue = message_queues.get(session_id)
        if not message_queue:
            logger.error(f"会话 {session_id} 的消息队列不存在")
            return

        logger.info(f"获取到消息队列: {session_id}, 队列ID: {id(message_queue)}, 队列大小: {message_queue.qsize()}")
        
        # 获取会话信息
        session_info = active_sessions.get(session_id)
        if not session_info:
            logger.error(f"会话 {session_id} 信息不存在")
            return
        
        # 更新会话状态
        active_sessions[session_id]["status"] = "processing"
        
        # 发送开始消息
        message = StreamMessage(
            message_id=f"system-{uuid.uuid4()}",
            type="message",
            source="系统",
            content="🚀 开始Web图片分析流程...",
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

        # 是否开启回调
        collector = StreamResponseCollector(platform=AgentPlatform.WEB)

        collector.set_callback(message_callback)

        # 获取Web编排器
        orchestrator = get_web_orchestrator(collector=collector)
        # 获取请求数据
        request_data = session_info["request"]
        
        # 执行分析流程（支持多种格式）
        generate_formats = request_data.get("generate_formats", ["yaml"])
        await orchestrator.analyze_image_to_scripts(
            session_id=session_id,
            image_data=request_data["image_data"],
            test_description=request_data["test_description"],
            additional_context=request_data.get("additional_context", ""),
            generate_formats=generate_formats
        )
        
        # # 数据库保存现在由智能体架构处理，这里只需要记录配置
        # # database_config = session_info.get("database_config", {})
        # saved_scripts = []  # 将由智能体填充
        # #
        # # # 发送最终结果
        # final_result = dict()
        # final_result["saved_scripts"] = saved_scripts
        # #
        final_message = StreamMessage(
            message_id=f"final-{uuid.uuid4()}",
            type="final_result",
            source="系统",
            content="✅ Web图片分析流程完成",
            region="process",
            platform="web",
            is_final=True,
        )
        await message_queue.put(final_message)
        # #
        # # # 更新会话状态
        active_sessions[session_id]["status"] = "completed"
        active_sessions[session_id]["completed_at"] = datetime.now().isoformat()
        # active_sessions[session_id]["result"] = final_result
        # active_sessions[session_id]["saved_scripts"] = saved_scripts

        logger.info(f"Web图片分析任务已完成")
        
    except Exception as e:
        logger.error(f"Web图片分析任务失败: {str(e)}")
        
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
    feedback_queues.pop(session_id, None)

    return JSONResponse({
        "status": "success",
        "message": f"会话 {session_id} 已删除"
    })


@router.get("/download/yaml/{session_id}")
async def download_yaml_file(session_id: str):
    """
    下载生成的YAML文件

    Args:
        session_id: 会话ID

    Returns:
        FileResponse: YAML文件下载响应
    """
    try:
        # 检查会话是否存在
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

        session_info = active_sessions[session_id]

        # 检查会话是否已完成
        if session_info.get("status") != "completed":
            raise HTTPException(status_code=400, detail="分析尚未完成，无法下载文件")

        # 从结果中获取文件路径
        result = session_info.get("result", {})
        generated_scripts = result.get("generated_scripts", [])

        # 查找YAML文件
        yaml_script = None
        for script in generated_scripts:
            if script.get("format") == "yaml":
                yaml_script = script
                break

        if not yaml_script:
            raise HTTPException(status_code=404, detail="未找到YAML文件")

        file_path = yaml_script.get("file_path")
        if not file_path or not Path(file_path).exists():
            # 如果文件路径不存在，尝试在默认目录查找
            file_dir = Path("generated_scripts/web")
            yaml_files = list(file_dir.glob(f"*{session_id[:8]}*.yaml"))

            if not yaml_files:
                raise HTTPException(status_code=404, detail="YAML文件不存在")

            # 使用最新的文件
            file_path = max(yaml_files, key=lambda p: p.stat().st_mtime)
        else:
            file_path = Path(file_path)

        # 生成下载文件名
        download_filename = f"web_test_{session_id[:8]}.yaml"

        return FileResponse(
            path=str(file_path),
            filename=download_filename,
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": f"attachment; filename={download_filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载YAML文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}")


@router.post("/save-script")
async def save_script_file(
    content: str = Form(...),
    filename: str = Form(...),
    format: str = Form(...)
):
    """
    保存编辑后的脚本文件

    Args:
        content: 脚本内容
        filename: 文件名
        format: 脚本格式 (yaml/playwright)

    Returns:
        dict: 保存结果
    """
    try:
        from app.utils.file_utils import save_yaml_content, save_playwright_content
        from app.core.config import settings

        # 根据格式选择保存方法
        if format.lower() == 'yaml':
            file_path = await save_yaml_content(
                content=content,
                session_id=f"edited_{int(time.time())}",
                filename=filename
            )
        elif format.lower() == 'playwright':
            file_path = await save_playwright_content(
                content=content,
                session_id=f"edited_{int(time.time())}",
                filename=filename
            )
        else:
            raise HTTPException(status_code=400, detail=f"不支持的脚本格式: {format}")

        logger.info(f"脚本文件保存成功: {file_path}")

        return JSONResponse({
            "status": "success",
            "message": f"{format.upper()}脚本保存成功",
            "file_path": file_path,
            "filename": filename
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存脚本文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存脚本文件失败: {str(e)}")


@router.get("/scripts/{session_id}")
async def get_generated_scripts(session_id: str):
    """
    获取指定会话生成的脚本内容

    Args:
        session_id: 会话ID

    Returns:
        dict: 包含生成的脚本内容
    """
    try:
        # 检查会话是否存在
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在或已过期")

        session_info = active_sessions[session_id]

        # 检查会话是否已完成
        if session_info.get("status") != "completed":
            raise HTTPException(status_code=400, detail="分析尚未完成，无法获取脚本")

        # 从结果中获取脚本数据
        result = session_info.get("result", {})
        scripts = []

        # 检查是否有generated_scripts
        if "generated_scripts" in result:
            for script in result["generated_scripts"]:
                scripts.append({
                    "format": script.get("format", "yaml"),
                    "content": script.get("content", ""),
                    "filename": script.get("filename", f"script_{session_id[:8]}.{script.get('format', 'yaml')}"),
                    "file_path": script.get("file_path", "")
                })

        # 兼容旧格式 - 检查yaml_content
        elif "yaml_content" in result and result["yaml_content"]:
            scripts.append({
                "format": "yaml",
                "content": result["yaml_content"],
                "filename": f"test_{session_id[:8]}.yaml",
                "file_path": result.get("file_path", "")
            })

        # 如果没有找到脚本内容，返回空数组
        if not scripts:
            logger.warning(f"会话 {session_id} 没有找到生成的脚本内容")

        logger.info(f"获取会话 {session_id} 的脚本成功，共 {len(scripts)} 个脚本")

        return JSONResponse({
            "status": "success",
            "session_id": session_id,
            "scripts": scripts,
            "total_scripts": len(scripts),
            "saved_scripts": session_info.get("saved_scripts", []),
            "message": f"成功获取 {len(scripts)} 个生成的脚本"
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取生成的脚本失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取脚本失败: {str(e)}")


@router.get("/templates")
async def get_web_test_templates():
    """
    获取Web测试模板

    Returns:
        Dict: 包含模板列表的响应
    """
    try:
        templates = [
            {
                "id": "web_login_test",
                "name": "Web登录测试",
                "description": "测试Web应用的用户登录功能",
                "category": "authentication",
                "platform": "web",
                "template": {
                    "test_description": "测试Web登录功能：1) 使用aiInput输入用户名和密码 2) 使用aiTap点击登录按钮 3) 使用aiAssert验证登录成功 4) 测试错误密码场景",
                    "additional_context": "Web登录测试，包含正常登录和异常情况验证"
                }
            },
            {
                "id": "web_form_test",
                "name": "Web表单测试",
                "description": "测试Web表单的填写和提交",
                "category": "forms",
                "platform": "web",
                "template": {
                    "test_description": "测试Web表单功能：1) 使用aiInput填写各个表单字段 2) 使用aiTap选择下拉选项 3) 使用aiTap提交表单 4) 使用aiAssert验证提交结果",
                    "additional_context": "Web表单测试，验证表单验证和提交流程"
                }
            },
            {
                "id": "web_navigation_test",
                "name": "Web导航测试",
                "description": "测试Web页面导航和链接跳转",
                "category": "navigation",
                "platform": "web",
                "template": {
                    "test_description": "测试Web导航功能：1) 使用aiTap点击导航菜单 2) 验证页面跳转 3) 测试面包屑导航 4) 验证返回功能",
                    "additional_context": "Web导航测试，确保页面间跳转正常"
                }
            },
            {
                "id": "web_search_test",
                "name": "Web搜索测试",
                "description": "测试Web应用的搜索功能",
                "category": "search",
                "platform": "web",
                "template": {
                    "test_description": "测试Web搜索功能：1) 使用aiInput输入搜索关键词 2) 使用aiTap点击搜索按钮 3) 使用aiAssert验证搜索结果 4) 测试搜索过滤和排序",
                    "additional_context": "Web搜索测试，验证搜索功能的准确性和性能"
                }
            }
        ]

        return {
            "templates": templates,
            "total": len(templates),
            "platform": "web",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取Web测试模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模板失败: {str(e)}")


# 注意：脚本保存功能现在通过智能体架构处理
# 相关API端点已移至 /web/scripts/ 路径下的脚本管理模块

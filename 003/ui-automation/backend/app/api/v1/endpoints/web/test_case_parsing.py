"""
测试用例元素解析API端点
提供测试用例解析功能的HTTP接口
基于智能体架构和SSE流式接口
"""
import asyncio
import uuid
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from autogen_core import MessageContext, ClosureContext
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Form
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel, Field

from app.core.messages import StreamMessage
from app.core.messages.web import TestCaseElementParseRequest

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


class TestCaseParseRequestModel(BaseModel):
    """测试用例解析请求模型"""
    test_case_content: str = Field(..., description="用户编写的测试用例内容")
    test_description: Optional[str] = Field(None, description="测试描述")
    target_format: str = Field(default="yaml", description="目标脚本格式: yaml, playwright")
    additional_context: Optional[str] = Field(None, description="额外上下文信息")


class TestCaseParseResponse(BaseModel):
    """测试用例解析响应模型"""
    success: bool = Field(..., description="是否成功")
    session_id: str = Field(..., description="会话ID")
    message: str = Field(..., description="响应消息")
    data: Optional[dict] = Field(None, description="解析结果数据")


@router.get("/health")
async def health_check():
    """测试用例解析健康检查端点"""
    return {"status": "ok", "service": "test-case-parser", "timestamp": datetime.now().isoformat()}


@router.post("/parse", response_model=TestCaseParseResponse)
async def parse_test_case_elements(
    test_case_content: str = Form(...),
    test_description: Optional[str] = Form(None),
    target_format: str = Form(default="yaml"),
    additional_context: Optional[str] = Form(None)
):
    """
    解析测试用例中的页面元素

    根据用户编写的测试用例内容，智能分析并从数据库中获取相应的页面元素信息，
    对返回的数据进行整理分类，为脚本生成智能体提供结构化的页面元素数据。
    """
    try:
        # 验证输入
        if not test_case_content or len(test_case_content.strip()) < 10:
            raise HTTPException(status_code=400, detail="测试用例内容不能为空且至少包含10个字符")

        if target_format not in ["yaml", "playwright"]:
            raise HTTPException(status_code=400, detail="目标格式必须是 'yaml' 或 'playwright'")

        # 生成会话ID
        session_id = str(uuid.uuid4())

        # 记录当前时间
        current_time = datetime.now()

        # 存储会话信息
        active_sessions[session_id] = {
            "status": "processing",
            "created_at": current_time.isoformat(),
            "last_activity": current_time.isoformat(),
            "test_case_info": {
                "content": test_case_content,
                "description": test_description or "",
                "target_format": target_format,
                "additional_context": additional_context or "",
                "content_length": len(test_case_content)
            },
            "progress": 0,
            "parse_result": None
        }

        # 创建消息队列
        message_queue = asyncio.Queue()
        message_queues[session_id] = message_queue

        # 立即启动后台解析任务
        asyncio.create_task(process_test_case_parse_task(session_id))

        logger.info(f"测试用例解析任务已创建并启动: {session_id}")
        logger.info(f"测试用例内容长度: {len(test_case_content)} 字符")
        logger.info(f"目标格式: {target_format}")

        return JSONResponse({
            "status": "success",
            "session_id": session_id,
            "sse_endpoint": f"/api/v1/web/test-case-parser/stream/{session_id}",
            "message": "测试用例解析任务已启动",
            "target_format": target_format,
            "test_case_info": {
                "content_length": len(test_case_content),
                "has_description": bool(test_description),
                "has_context": bool(additional_context)
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建测试用例解析任务失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.get("/stream/{session_id}")
async def stream_test_case_parsing(
    session_id: str,
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    测试用例解析SSE流式端点

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

    logger.info(f"开始测试用例解析SSE流: {session_id}")

    async def event_generator():
        """事件生成器"""
        try:
            # 发送初始连接消息
            yield {
                "event": "connected",
                "data": json.dumps({
                    "session_id": session_id,
                    "status": "connected",
                    "message": "已连接到测试用例解析流"
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


async def process_test_case_parse_task(session_id: str):
    """
    处理测试用例解析任务

    Args:
        session_id: 会话ID
    """
    try:
        logger.info(f"开始处理测试用例解析任务: {session_id}")

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
            source="测试用例元素解析器",
            content="🔍 开始分析测试用例内容，提取页面元素信息...",
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

        # 获取测试用例信息
        test_case_info = session_info["test_case_info"]

        # 更新进度
        active_sessions[session_id]["progress"] = 30

        # 使用编排器执行测试用例元素解析（业务流程6）
        await orchestrator.parse_test_case_elements(
            session_id=session_id,
            test_case_content=test_case_info["content"],
            test_description=test_case_info["description"],
            target_format=test_case_info["target_format"],
            additional_context=test_case_info["additional_context"]
        )

        # 发送完成消息
        final_message = StreamMessage(
            message_id=f"final-{uuid.uuid4()}",
            type="final_result",
            source="测试用例元素解析器",
            content="✅ 测试用例解析完成，页面元素信息已提取并发送给脚本生成智能体",
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

        logger.info(f"测试用例解析任务已完成: {session_id}")

    except Exception as e:
        logger.error(f"测试用例解析任务失败: {str(e)}")

        # 发送错误消息
        try:
            error_message = StreamMessage(
                message_id=f"error-{uuid.uuid4()}",
                type="error",
                source="测试用例元素解析器",
                content=f"❌ 解析过程出错: {str(e)}",
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

    finally:
        # 编排器会自动清理运行时
        pass


@router.get("/status/{session_id}")
async def get_parse_status(session_id: str):
    """获取解析状态"""
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
            "test_case_info": {
                "content_length": session_info["test_case_info"]["content_length"],
                "target_format": session_info["test_case_info"]["target_format"],
                "has_description": bool(session_info["test_case_info"]["description"]),
                "has_context": bool(session_info["test_case_info"]["additional_context"])
            }
        }
    })


@router.delete("/session/{session_id}")
async def cleanup_parse_session(session_id: str):
    """清理解析会话"""
    try:
        if session_id in active_sessions:
            active_sessions.pop(session_id, None)
        if session_id in message_queues:
            message_queues.pop(session_id, None)

        return JSONResponse({
            "success": True,
            "message": f"会话 {session_id} 已清理"
        })

    except Exception as e:
        logger.error(f"清理解析会话失败: {session_id}, 错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"清理解析会话失败: {str(e)}"
        )


@router.get("/sessions")
async def list_active_sessions():
    """列出所有活跃会话"""
    try:
        sessions_info = []
        for session_id, session_data in active_sessions.items():
            sessions_info.append({
                "session_id": session_id,
                "status": session_data["status"],
                "progress": session_data.get("progress", 0),
                "created_at": session_data["created_at"],
                "last_activity": session_data["last_activity"],
                "target_format": session_data["test_case_info"]["target_format"]
            })

        return JSONResponse({
            "success": True,
            "data": {
                "total_sessions": len(sessions_info),
                "sessions": sessions_info
            }
        })

    except Exception as e:
        logger.error(f"获取活跃会话列表失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取活跃会话列表失败: {str(e)}"
        )


@router.post("/test")
async def test_parser_agent():
    """测试解析智能体功能"""
    try:
        # 创建测试用例
        test_case_content = """
        测试场景：用户登录功能测试

        步骤：
        1. 打开登录页面
        2. 在用户名输入框中输入 "testuser"
        3. 在密码输入框中输入 "password123"
        4. 点击登录按钮
        5. 验证是否成功跳转到首页
        6. 检查页面是否显示用户欢迎信息

        预期结果：
        - 登录成功后跳转到首页
        - 页面显示 "欢迎, testuser" 信息
        - 页面右上角显示用户头像和退出按钮
        """

        # 生成测试会话ID
        session_id = str(uuid.uuid4())
        current_time = datetime.now()

        # 存储会话信息
        active_sessions[session_id] = {
            "status": "processing",
            "created_at": current_time.isoformat(),
            "last_activity": current_time.isoformat(),
            "test_case_info": {
                "content": test_case_content,
                "description": "用户登录功能的完整测试流程",
                "target_format": "yaml",
                "additional_context": "这是一个标准的Web应用登录测试用例",
                "content_length": len(test_case_content)
            },
            "progress": 0,
            "parse_result": None
        }

        # 创建消息队列
        message_queue = asyncio.Queue()
        message_queues[session_id] = message_queue

        # 启动后台任务
        asyncio.create_task(process_test_case_parse_task(session_id))

        return JSONResponse({
            "success": True,
            "message": "测试请求已发送",
            "data": {
                "session_id": session_id,
                "sse_endpoint": f"/api/v1/web/test-case-parser/stream/{session_id}",
                "test_case_length": len(test_case_content),
                "target_format": "yaml"
            }
        })

    except Exception as e:
        logger.error(f"测试解析智能体失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"测试解析智能体失败: {str(e)}"
        )



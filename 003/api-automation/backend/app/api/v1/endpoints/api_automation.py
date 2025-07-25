"""
接口自动化API端点
提供API文档上传、解析、测试生成和执行的REST接口
"""
import os
import uuid
import asyncio
import json
import mimetypes
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from loguru import logger

from app.services.api_automation import ApiAutomationOrchestrator
from app.core.agents.collector import StreamResponseCollector
from app.core.types import AgentPlatform


# 请求模型
class ApiDocUploadRequest(BaseModel):
    """API文档上传请求"""
    doc_format: str = Field("auto", description="文档格式")
    config: Dict[str, Any] = Field(default_factory=dict, description="解析配置")


class TestExecutionRequest(BaseModel):
    """测试执行请求"""
    session_id: str = Field(..., description="会话ID")
    script_files: List[str] = Field(..., description="测试脚本文件列表")
    config: Dict[str, Any] = Field(default_factory=dict, description="执行配置")


class SessionStatusResponse(BaseModel):
    """会话状态响应"""
    success: bool = Field(..., description="是否成功")
    session_id: str = Field(..., description="会话ID")
    session_info: Optional[Dict[str, Any]] = Field(None, description="会话信息")
    message: str = Field("", description="消息")


# 全局编排器实例
orchestrator: Optional[ApiAutomationOrchestrator] = None
active_sessions: Dict[str, Dict[str, Any]] = {}

# 支持的API文档文件类型配置
SUPPORTED_API_DOC_TYPES = {
    "openapi": {
        "name": "OpenAPI/Swagger规范",
        "extensions": [".json", ".yaml", ".yml"],
        "maxSize": 10,  # MB
        "description": "支持OpenAPI 3.0和Swagger 2.0规范文件",
        "content_types": ["application/json", "application/x-yaml", "text/yaml", "text/plain"]
    },
    "postman": {
        "name": "Postman集合",
        "extensions": [".json"],
        "maxSize": 10,  # MB
        "description": "支持Postman Collection导出文件",
        "content_types": ["application/json"]
    },
    "api_doc": {
        "name": "API文档",
        "extensions": [".pdf", ".docx", ".doc", ".txt", ".md"],
        "maxSize": 50,  # MB
        "description": "支持PDF、Word、Markdown等格式的API文档",
        "content_types": ["application/pdf", "application/msword", "text/plain", "text/markdown"]
    }
}

def get_api_doc_category(filename: str) -> tuple[str, dict]:
    """根据文件名获取API文档分类"""
    file_ext = Path(filename).suffix.lower()

    for category, config in SUPPORTED_API_DOC_TYPES.items():
        if file_ext in config["extensions"]:
            return category, config

    return "unknown", {}

def is_api_doc_supported(filename: str, file_size: int) -> tuple[bool, str]:
    """检查API文档文件是否支持"""
    category, config = get_api_doc_category(filename)

    if category == "unknown":
        return False, "不支持的API文档文件类型"

    max_size_bytes = config["maxSize"] * 1024 * 1024  # 转换为字节

    if file_size > max_size_bytes:
        return False, f"文件大小超过限制 ({config['maxSize']}MB)"

    return True, "文件支持"

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "API自动化服务正常运行"}


@router.get("/supported-types")
async def get_supported_file_types():
    """获取支持的API文档文件类型"""
    return {
        "supported_types": SUPPORTED_API_DOC_TYPES,
        "total_categories": len(SUPPORTED_API_DOC_TYPES),
        "message": "API自动化支持的文档类型"
    }


@router.post("/simple-upload")
async def simple_upload(file: UploadFile = File(...)):
    """最简单的文件上传测试"""
    logger.info(f"=== 简单上传接口被调用 ===")
    logger.info(f"收到文件: {file.filename}")
    logger.info(f"文件类型: {file.content_type}")

    try:
        content = await file.read()
        logger.info(f"文件大小: {len(content)} 字节")

        return {
            "success": True,
            "message": "文件上传成功",
            "filename": file.filename,
            "size": len(content),
            "content_type": file.content_type
        }
    except Exception as e:
        logger.error(f"文件读取失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件读取失败: {str(e)}")


@router.post("/test-raw-upload")
async def test_raw_upload(request: Request):
    """测试原始上传请求"""
    logger.info(f"=== 原始上传测试 ===")
    logger.info(f"Content-Type: {request.headers.get('content-type')}")
    logger.info(f"Method: {request.method}")

    try:
        # 尝试解析表单数据
        form = await request.form()
        logger.info(f"表单字段: {list(form.keys())}")

        for key, value in form.items():
            if hasattr(value, 'filename'):
                logger.info(f"文件字段 {key}: {value.filename}, 类型: {value.content_type}")
                content = await value.read()
                logger.info(f"文件大小: {len(content)} 字节")
            else:
                logger.info(f"普通字段 {key}: {value}")

        return {"success": True, "message": "原始上传测试成功", "fields": list(form.keys())}

    except Exception as e:
        logger.error(f"原始上传测试失败: {str(e)}")
        return {"success": False, "error": str(e)}


@router.post("/debug-form", summary="调试表单数据")
async def debug_form(
    request: Request,
    file: UploadFile = File(None),
    doc_format: str = Form(None)
):
    """调试表单数据"""
    logger.info("=== 调试表单数据 ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Content-Type: {request.headers.get('content-type', 'None')}")
    logger.info(f"Content-Length: {request.headers.get('content-length', 'None')}")

    logger.info(f"File parameter: {file}")
    logger.info(f"File filename: {file.filename if file else 'None'}")
    logger.info(f"File size: {file.size if file else 'None'}")
    logger.info(f"Doc format: {doc_format}")

    if file:
        # 读取文件内容的前100字节
        content = await file.read(100)
        await file.seek(0)  # 重置文件指针
        logger.info(f"File content (first 100 bytes): {content}")

    return {
        "success": True,
        "file_received": file is not None,
        "filename": file.filename if file else None,
        "doc_format": doc_format
    }


@router.post("/test-upload", summary="测试文件上传")
async def test_upload(
    file: UploadFile = File(...),
    doc_format: str = Form("auto")
):
    """简单的测试上传端点"""
    logger.info(f"测试上传收到文件: {file.filename if file else 'None'}")
    logger.info(f"文件大小: {file.size if file else 'None'}")
    logger.info(f"文档格式: {doc_format}")

    return {
        "success": True,
        "filename": file.filename,
        "size": file.size,
        "doc_format": doc_format
    }


def get_orchestrator() -> ApiAutomationOrchestrator:
    """获取编排器实例（同步版本，编排器已在应用启动时初始化）"""
    global orchestrator
    if orchestrator is None:
        raise RuntimeError("编排器未初始化，请检查应用启动流程")
    return orchestrator


async def initialize_orchestrator():
    """初始化编排器（在应用启动时调用）"""
    global orchestrator
    if orchestrator is None:
        logger.info("开始初始化API自动化编排器...")

        # 创建响应收集器
        collector = StreamResponseCollector(platform=AgentPlatform.API_AUTOMATION)

        # 创建编排器
        orchestrator = ApiAutomationOrchestrator(collector=collector)

        # 初始化编排器
        await orchestrator.initialize()

        logger.info("API自动化编排器初始化完成")


@router.post("/analyze-document")
async def analyze_api_document(file: UploadFile = File(...)):
    """分析API文档文件"""
    try:
        logger.info(f"=== 开始分析API文档 ===")
        logger.info(f"文件名: {file.filename}")
        logger.info(f"内容类型: {file.content_type}")

        # 读取文件内容
        content = await file.read()
        file_size = len(content)

        # 获取文件信息
        category, config = get_api_doc_category(file.filename)
        supported, message = is_api_doc_supported(file.filename, file_size)

        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(file.filename)

        logger.info(f"文件分析结果: 分类={category}, 支持={supported}, 消息={message}")

        return {
            "success": True,
            "data": {
                "file_name": file.filename,
                "file_size": file_size,
                "file_type": Path(file.filename).suffix.lower(),
                "category": category,
                "supported": supported,
                "mime_type": mime_type,
                "message": message,
                "category_info": config
            }
        }

    except Exception as e:
        logger.error(f"API文档分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档分析失败: {str(e)}")


@router.post("/upload-document")
async def upload_api_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_format: str = Form("auto"),
    config: str = Form("{}"),
    auto_parse: bool = Form(True)
):
    """上传API文档"""
    try:
        logger.info(f"=== 开始上传API文档 ===")
        logger.info(f"文件名: {file.filename}")
        logger.info(f"内容类型: {file.content_type}")
        logger.info(f"文档格式: {doc_format}")
        logger.info(f"配置: {config}")

        # 验证文件
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="未选择文件")

        # 读取文件内容
        content = await file.read()
        file_size = len(content)

        logger.info(f"文件大小: {file_size} 字节")

        if file_size == 0:
            raise HTTPException(status_code=400, detail="文件内容为空")

        # 检查文件是否支持
        supported, message = is_api_doc_supported(file.filename, file_size)
        if not supported:
            raise HTTPException(status_code=400, detail=message)

        # 生成会话ID和存储文件名
        session_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix
        stored_name = f"{session_id}_{file.filename}"

        # 创建上传目录
        upload_dir = Path("./uploads")
        upload_dir.mkdir(exist_ok=True)

        # 保存文件
        file_path = upload_dir / stored_name
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"文件保存到: {file_path}")

        # 解析配置
        try:
            parse_config = json.loads(config) if config != "{}" else {}
        except json.JSONDecodeError:
            logger.warning(f"配置JSON解析失败，使用默认配置: {config}")
            parse_config = {}

        # 获取MIME类型和文件分类
        mime_type, _ = mimetypes.guess_type(file.filename)
        category, category_config = get_api_doc_category(file.filename)

        # 记录会话信息
        active_sessions[session_id] = {
            "session_id": session_id,
            "file_name": file.filename,
            "stored_name": stored_name,
            "file_path": str(file_path),
            "file_size": file_size,
            "file_type": file_ext.lower(),
            "mime_type": mime_type,
            "category": category,
            "doc_format": doc_format,
            "config": parse_config,
            "status": "uploaded",
            "created_at": datetime.now().isoformat()
        }

        logger.info(f"=== API文档上传成功 ===")
        logger.info(f"会话ID: {session_id}")

        # 如果启用自动解析，则启动后台解析任务
        if auto_parse:
            logger.info(f"启动自动解析任务: {session_id}")

            # 获取编排器
            orch = get_orchestrator()

            # 启动后台解析任务
            background_tasks.add_task(
                process_document_background,
                orch,
                session_id,
                str(file_path),
                file.filename,
                doc_format,
                parse_config
            )

            # 更新会话状态
            active_sessions[session_id]["status"] = "parsing"
            active_sessions[session_id]["auto_parse"] = True

            message = "API文档上传成功，正在后台解析"
        else:
            message = "API文档上传成功，等待手动解析"

        return {
            "success": True,
            "data": {
                "docId": session_id,
                "sessionId": session_id,
                "fileName": file.filename,
                "storedName": stored_name,
                "fileSize": file_size,
                "fileType": file_ext.lower(),
                "mimeType": mime_type,
                "category": category,
                "docFormat": doc_format,
                "autoParse": auto_parse,
                "status": active_sessions[session_id]["status"]
            },
            "message": message
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API文档上传失败: {str(e)}")
        logger.exception("详细错误信息:")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


async def process_document_background(
    orch: ApiAutomationOrchestrator,
    session_id: str,
    file_path: str,
    file_name: str,
    doc_format: str,
    config: Dict[str, Any]
) -> None:
    """后台处理文档"""
    try:
        # 更新会话状态
        if session_id in active_sessions:
            active_sessions[session_id]["status"] = "processing"
            active_sessions[session_id]["started_at"] = datetime.now().isoformat()
        
        # 处理文档
        result = await orch.process_api_document(
            session_id=session_id,
            file_path=file_path,
            file_name=file_name,
            doc_format=doc_format,
            config=config
        )
        
        # 更新会话状态
        if session_id in active_sessions:
            active_sessions[session_id]["status"] = "completed"
            active_sessions[session_id]["completed_at"] = datetime.now().isoformat()
            active_sessions[session_id]["result"] = result
        
        logger.info(f"文档处理完成: {session_id}")
        
    except Exception as e:
        logger.error(f"后台处理文档失败: {str(e)}")
        
        # 更新会话状态
        if session_id in active_sessions:
            active_sessions[session_id]["status"] = "failed"
            active_sessions[session_id]["error"] = str(e)
            active_sessions[session_id]["failed_at"] = datetime.now().isoformat()


@router.get("/parse-status/{session_id}", summary="获取解析状态")
async def get_parse_status(session_id: str):
    """获取文档解析状态"""
    try:
        logger.info(f"查询解析状态: {session_id}")

        # 检查会话是否存在
        if session_id not in active_sessions:
            return {
                "success": False,
                "message": "会话不存在",
                "sessionId": session_id
            }

        session_info = active_sessions[session_id]
        status = session_info.get("status", "unknown")

        # 构建响应数据
        response_data = {
            "success": True,
            "data": {
                "sessionId": session_id,
                "status": status,
                "fileName": session_info.get("file_name"),
                "fileSize": session_info.get("file_size"),
                "docFormat": session_info.get("doc_format"),
                "createdAt": session_info.get("created_at"),
                "startedAt": session_info.get("started_at"),
                "completedAt": session_info.get("completed_at"),
                "failedAt": session_info.get("failed_at")
            }
        }

        # 根据状态添加不同的信息
        if status == "uploaded":
            response_data["message"] = "文档已上传，等待解析"
            response_data["data"]["progress"] = 0
        elif status == "parsing":
            response_data["message"] = "正在解析文档..."
            response_data["data"]["progress"] = 30
        elif status == "processing":
            response_data["message"] = "正在处理文档..."
            response_data["data"]["progress"] = 60
        elif status == "completed":
            response_data["message"] = "文档解析完成"
            response_data["data"]["progress"] = 100
            response_data["data"]["result"] = session_info.get("result")
        elif status == "failed":
            response_data["message"] = f"解析失败: {session_info.get('error', '未知错误')}"
            response_data["data"]["progress"] = 0
            response_data["data"]["error"] = session_info.get("error")
        else:
            response_data["message"] = f"未知状态: {status}"
            response_data["data"]["progress"] = 0

        return response_data

    except Exception as e:
        logger.error(f"查询解析状态失败: {str(e)}")
        return {
            "success": False,
            "message": f"查询状态失败: {str(e)}",
            "sessionId": session_id
        }


@router.post("/parse-document/{session_id}", summary="手动触发文档解析")
async def trigger_document_parse(
    session_id: str,
    background_tasks: BackgroundTasks,
    config: dict = None
):
    """手动触发文档解析"""
    try:
        logger.info(f"手动触发文档解析: {session_id}")

        # 检查会话是否存在
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="会话不存在")

        session_info = active_sessions[session_id]
        current_status = session_info.get("status")

        # 检查当前状态是否允许解析
        if current_status in ["parsing", "processing"]:
            return {
                "success": False,
                "message": "文档正在解析中，请稍后再试",
                "sessionId": session_id,
                "currentStatus": current_status
            }

        # 获取文件信息
        file_path = session_info.get("file_path")
        file_name = session_info.get("file_name")
        doc_format = session_info.get("doc_format", "auto")

        # 使用传入的配置或会话中的配置
        parse_config = config if config is not None else session_info.get("config", {})

        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="原始文件不存在")

        logger.info(f"开始手动解析文档: {file_name}")

        # 获取编排器
        orch = get_orchestrator()

        # 启动后台解析任务
        background_tasks.add_task(
            process_document_background,
            orch,
            session_id,
            file_path,
            file_name,
            doc_format,
            parse_config
        )

        # 更新会话状态
        active_sessions[session_id]["status"] = "parsing"
        active_sessions[session_id]["manual_parse"] = True
        active_sessions[session_id]["parse_triggered_at"] = datetime.now().isoformat()

        return {
            "success": True,
            "data": {
                "sessionId": session_id,
                "fileName": file_name,
                "status": "parsing",
                "message": "文档解析已启动"
            },
            "message": "文档解析已启动，请查询状态获取进度"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动触发解析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"触发解析失败: {str(e)}")


@router.get("/session/{session_id}/status", summary="获取会话状态")
async def get_session_status(session_id: str) -> SessionStatusResponse:
    """获取指定会话的处理状态"""
    try:
        # 检查本地会话记录
        if session_id not in active_sessions:
            return SessionStatusResponse(
                success=False,
                session_id=session_id,
                message="会话不存在"
            )
        
        session_info = active_sessions[session_id].copy()
        
        # 获取编排器状态
        orch = get_orchestrator()
        orchestrator_status = await orch.get_session_status(session_id)
        
        # 合并状态信息
        if orchestrator_status.get("success"):
            session_info.update(orchestrator_status.get("session_info", {}))
        
        return SessionStatusResponse(
            success=True,
            session_id=session_id,
            session_info=session_info,
            message="获取状态成功"
        )
        
    except Exception as e:
        logger.error(f"获取会话状态失败: {str(e)}")
        return SessionStatusResponse(
            success=False,
            session_id=session_id,
            message=f"获取状态失败: {str(e)}"
        )


@router.post("/execute-tests", summary="执行测试")
async def execute_tests(request: TestExecutionRequest) -> JSONResponse:
    """执行生成的测试脚本"""
    try:
        # 获取编排器
        orch = get_orchestrator()
        
        # 执行测试
        result = await orch.execute_test_suite(
            session_id=request.session_id,
            script_files=request.script_files,
            test_config=request.config
        )
        
        logger.info(f"测试执行启动成功: {request.session_id}")
        
        return JSONResponse(
            status_code=200,
            content=result
        )
        
    except Exception as e:
        logger.error(f"执行测试失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"执行测试失败: {str(e)}")


@router.get("/sessions", summary="获取所有会话")
async def get_all_sessions() -> JSONResponse:
    """获取所有活跃会话的列表"""
    try:
        sessions = []
        for session_id, session_info in active_sessions.items():
            sessions.append({
                "session_id": session_id,
                "file_name": session_info.get("file_name"),
                "status": session_info.get("status"),
                "created_at": session_info.get("created_at"),
                "doc_format": session_info.get("doc_format")
            })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "total_sessions": len(sessions),
                "sessions": sessions
            }
        )
        
    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@router.get("/metrics", summary="获取系统指标")
async def get_system_metrics() -> JSONResponse:
    """获取系统运行指标和健康状态"""
    try:
        # 获取编排器指标
        orch = get_orchestrator()
        orchestrator_metrics = await orch.get_orchestrator_metrics()
        
        # 添加会话统计
        session_stats = {
            "total_sessions": len(active_sessions),
            "sessions_by_status": {}
        }
        
        for session_info in active_sessions.values():
            status = session_info.get("status", "unknown")
            session_stats["sessions_by_status"][status] = \
                session_stats["sessions_by_status"].get(status, 0) + 1
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "orchestrator_metrics": orchestrator_metrics,
                "session_stats": session_stats,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"获取系统指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取系统指标失败: {str(e)}")


@router.get("/session/{session_id}/reports", summary="获取测试报告")
async def get_test_reports(session_id: str) -> JSONResponse:
    """获取指定会话的测试报告文件列表"""
    try:
        reports_dir = Path("./reports")
        if not reports_dir.exists():
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "报告目录不存在"
                }
            )
        
        # 查找相关的报告文件
        report_files = []
        for file_path in reports_dir.rglob("*"):
            if file_path.is_file() and session_id in file_path.name:
                report_files.append({
                    "file_name": file_path.name,
                    "file_path": str(file_path),
                    "file_size": file_path.stat().st_size,
                    "created_at": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat()
                })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "session_id": session_id,
                "report_count": len(report_files),
                "reports": report_files
            }
        )
        
    except Exception as e:
        logger.error(f"获取测试报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取测试报告失败: {str(e)}")


@router.get("/download/report/{file_name}", summary="下载报告文件")
async def download_report(file_name: str) -> FileResponse:
    """下载指定的报告文件"""
    try:
        reports_dir = Path("./reports")
        file_path = reports_dir / file_name
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="报告文件不存在")
        
        return FileResponse(
            path=str(file_path),
            filename=file_name,
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"下载报告文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@router.delete("/session/{session_id}", summary="删除会话")
async def delete_session(session_id: str) -> JSONResponse:
    """删除指定的会话和相关文件"""
    try:
        if session_id not in active_sessions:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        session_info = active_sessions[session_id]
        
        # 删除上传的文件
        if "file_path" in session_info:
            file_path = Path(session_info["file_path"])
            if file_path.exists():
                file_path.unlink()
        
        # 删除会话记录
        del active_sessions[session_id]
        
        logger.info(f"会话删除成功: {session_id}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "session_id": session_id,
                "message": "会话删除成功"
            }
        )
        
    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")


@router.post("/cleanup", summary="清理系统资源")
async def cleanup_system() -> JSONResponse:
    """清理系统资源和临时文件"""
    try:
        global orchestrator
        
        # 清理编排器
        if orchestrator:
            await orchestrator.cleanup()
            orchestrator = None
        
        # 清理会话
        active_sessions.clear()
        
        # 清理临时文件
        cleanup_count = 0
        for temp_dir in ["./uploads", "./reports", "./logs"]:
            temp_path = Path(temp_dir)
            if temp_path.exists():
                for file_path in temp_path.rglob("*"):
                    if file_path.is_file():
                        file_path.unlink()
                        cleanup_count += 1
        
        logger.info("系统资源清理完成")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "系统资源清理完成",
                "cleaned_files": cleanup_count
            }
        )
        
    except Exception as e:
        logger.error(f"清理系统资源失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")

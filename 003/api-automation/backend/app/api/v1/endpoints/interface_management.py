"""
接口管理API端点
提供接口信息的查询、管理和操作功能
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File
from pydantic import BaseModel, Field
from loguru import logger

from app.agents.api_automation.schemas import DocumentFormat, DocumentParseInput
from app.models.api_automation import ApiDocument, ApiInterface, ApiParameter as DbApiParameter, ApiResponse as DbApiResponse
from app.core.enums import HttpMethod, SessionStatus
from app.services.api_automation import ApiAutomationOrchestrator
from app.core.agents.collector import StreamResponseCollector
from app.core.types import AgentPlatform
import os
import uuid
import asyncio
import mimetypes


router = APIRouter(tags=["接口管理"])

# 全局编排器实例
orchestrator: Optional[ApiAutomationOrchestrator] = None


def get_orchestrator() -> ApiAutomationOrchestrator:
    """获取编排器实例"""
    global orchestrator
    if orchestrator is None:
        raise RuntimeError("编排器未初始化，请检查应用启动流程")
    return orchestrator


async def initialize_orchestrator():
    """初始化编排器（在应用启动时调用）"""
    global orchestrator
    if orchestrator is None:
        logger.info("开始初始化接口管理编排器...")

        # 创建响应收集器
        collector = StreamResponseCollector(platform=AgentPlatform.API_AUTOMATION)

        # 创建编排器
        orchestrator = ApiAutomationOrchestrator(collector=collector)

        # 初始化编排器
        await orchestrator.initialize()

        logger.info("接口管理编排器初始化完成")


# 请求和响应模型
class InterfaceListResponse(BaseModel):
    """接口列表响应"""
    code: int = 200
    msg: str = "获取成功"
    data: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class InterfaceDetailResponse(BaseModel):
    """接口详情响应"""
    code: int = 200
    msg: str = "获取成功"
    data: Optional[Dict[str, Any]] = None


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    code: int = 200
    msg: str = "上传成功"
    session_id: str = ""
    file_name: str = ""


class ParseStatusResponse(BaseModel):
    """解析状态响应"""
    code: int = 200
    msg: str = ""
    status: str = ""
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None


class StatisticsResponse(BaseModel):
    """统计信息响应"""
    code: int = 200
    msg: str = "获取成功"
    data: Dict[str, Any] = Field(default_factory=dict)


class ScriptGenerationResponse(BaseModel):
    """脚本生成响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    session_id: Optional[str] = Field(None, description="会话ID")
    task_id: Optional[str] = Field(None, description="任务ID")


@router.get("/documents", response_model=InterfaceListResponse)
async def get_api_documents(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    doc_format: Optional[str] = Query(None, description="文档格式筛选")
):
    """获取API文档列表"""
    try:
        # 构建查询条件
        query = ApiDocument.filter(is_deleted=False)
        
        if search:
            query = query.filter(
                file_name__icontains=search
            )
        
        if doc_format:
            query = query.filter(doc_format=doc_format)
        
        # 分页查询
        total = await query.count()
        offset = (page - 1) * page_size
        documents = await query.offset(offset).limit(page_size).order_by("-created_at")
        
        # 格式化返回数据
        data = []
        for doc in documents:
            data.append({
                "doc_id": doc.doc_id,
                "session_id": doc.session_id,
                "file_name": doc.file_name,
                "doc_format": doc.doc_format,
                "api_title": doc.api_info.get("title", "") if doc.api_info else "",
                "api_version": doc.api_info.get("version", "") if doc.api_info else "",
                "endpoints_count": doc.endpoints_count,
                "confidence_score": doc.confidence_score,
                "parse_status": doc.parse_status.value,
                "created_at": doc.created_at.isoformat(),
                "updated_at": doc.updated_at.isoformat()
            })
        
        return InterfaceListResponse(
            data=data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"获取API文档列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.get("/documents/{doc_id}", response_model=InterfaceDetailResponse)
async def get_document_detail(doc_id: str):
    """获取API文档详情"""
    try:
        document = await ApiDocument.filter(doc_id=doc_id, is_deleted=False).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 获取关联的接口信息
        interfaces = await ApiInterface.filter(document=document, is_active=True).prefetch_related("parameters", "responses")
        
        # 格式化接口数据
        interfaces_data = []
        for interface in interfaces:
            # 获取参数信息
            parameters = []
            for param in interface.parameters:
                parameters.append({
                    "name": param.name,
                    "location": param.location,
                    "data_type": param.data_type,
                    "required": param.required,
                    "description": param.description,
                    "example": param.example,
                    "constraints": param.constraints
                })
            
            # 获取响应信息
            responses = []
            for resp in interface.responses:
                responses.append({
                    "status_code": resp.status_code,
                    "description": resp.description,
                    "content_type": resp.content_type,
                    "response_schema": resp.response_schema,
                    "example": resp.example
                })
            
            interfaces_data.append({
                "interface_id": interface.interface_id,
                "name": interface.name,
                "path": interface.path,
                "method": interface.method.value,
                "summary": interface.summary,
                "description": interface.description,
                "tags": interface.tags,
                "auth_required": interface.auth_required,
                "is_deprecated": interface.is_deprecated,
                "confidence_score": interface.confidence_score,
                "parameters": parameters,
                "responses": responses,
                "created_at": interface.created_at.isoformat()
            })
        
        # 构建返回数据
        data = {
            "doc_id": document.doc_id,
            "session_id": document.session_id,
            "file_name": document.file_name,
            "doc_format": document.doc_format,
            "api_info": document.api_info,
            "endpoints_count": document.endpoints_count,
            "confidence_score": document.confidence_score,
            "parse_status": document.parse_status.value,
            "parse_errors": document.parse_errors,
            "parse_warnings": document.parse_warnings,
            "processing_time": document.processing_time,
            "interfaces": interfaces_data,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat()
        }
        
        return InterfaceDetailResponse(data=data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档详情失败: {str(e)}")


@router.get("/interfaces", response_model=InterfaceListResponse)
async def get_interfaces(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    method: Optional[str] = Query(None, description="HTTP方法筛选"),
    doc_id: Optional[str] = Query(None, description="文档ID筛选"),
    tags: Optional[str] = Query(None, description="标签筛选")
):
    """获取接口列表"""
    try:
        # 构建查询条件
        query = ApiInterface.filter(is_active=True).select_related("document")
        
        if search:
            query = query.filter(
                name__icontains=search
            )
        
        if method:
            try:
                http_method = HttpMethod(method.upper())
                query = query.filter(method=http_method)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的HTTP方法: {method}")
        
        if doc_id:
            query = query.filter(document__doc_id=doc_id)
        
        if tags:
            query = query.filter(tags__contains=[tags])
        
        # 分页查询
        total = await query.count()
        offset = (page - 1) * page_size
        interfaces = await query.offset(offset).limit(page_size).order_by("-created_at")
        
        # 格式化返回数据
        data = []
        for interface in interfaces:
            data.append({
                "interface_id": interface.interface_id,
                "name": interface.name,
                "path": interface.path,
                "method": interface.method.value,
                "summary": interface.summary,
                "description": interface.description,
                "tags": interface.tags,
                "auth_required": interface.auth_required,
                "is_deprecated": interface.is_deprecated,
                "confidence_score": interface.confidence_score,
                "api_title": interface.api_title,
                "api_version": interface.api_version,
                "document_id": interface.document.doc_id,
                "document_name": interface.document.file_name,
                "created_at": interface.created_at.isoformat()
            })
        
        return InterfaceListResponse(
            data=data,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取接口列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取接口列表失败: {str(e)}")


@router.get("/interfaces/{interface_id}", response_model=InterfaceDetailResponse)
async def get_interface_detail(interface_id: str):
    """获取接口详情"""
    try:
        interface = await ApiInterface.filter(
            interface_id=interface_id, 
            is_active=True
        ).select_related("document").prefetch_related("parameters", "responses").first()
        
        if not interface:
            raise HTTPException(status_code=404, detail="接口不存在")
        
        # 获取参数信息
        parameters = []
        for param in interface.parameters:
            parameters.append({
                "parameter_id": param.parameter_id,
                "name": param.name,
                "location": param.location,
                "data_type": param.data_type,
                "required": param.required,
                "description": param.description,
                "example": param.example,
                "constraints": param.constraints,
                "schema": param.schema
            })
        
        # 获取响应信息
        responses = []
        for resp in interface.responses:
            responses.append({
                "response_id": resp.response_id,
                "status_code": resp.status_code,
                "description": resp.description,
                "content_type": resp.content_type,
                "response_schema": resp.response_schema,
                "example": resp.example,
                "headers": resp.headers
            })
        
        # 构建返回数据
        data = {
            "interface_id": interface.interface_id,
            "name": interface.name,
            "path": interface.path,
            "method": interface.method.value,
            "summary": interface.summary,
            "description": interface.description,
            "tags": interface.tags,
            "category": interface.category,
            "auth_required": interface.auth_required,
            "auth_type": interface.auth_type,
            "security_schemes": interface.security_schemes,
            "is_deprecated": interface.is_deprecated,
            "confidence_score": interface.confidence_score,
            "complexity_score": interface.complexity_score,
            "api_title": interface.api_title,
            "api_version": interface.api_version,
            "base_url": interface.base_url,
            "extended_info": interface.extended_info,
            "raw_data": interface.raw_data,
            "parameters": parameters,
            "responses": responses,
            "document": {
                "doc_id": interface.document.doc_id,
                "file_name": interface.document.file_name,
                "doc_format": interface.document.doc_format
            },
            "created_at": interface.created_at.isoformat(),
            "updated_at": interface.updated_at.isoformat()
        }
        
        return InterfaceDetailResponse(data=data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取接口详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取接口详情失败: {str(e)}")


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """删除API文档（软删除）"""
    try:
        document = await ApiDocument.filter(doc_id=doc_id, is_deleted=False).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        # 软删除文档
        document.is_deleted = True
        await document.save()
        
        # 软删除关联的接口
        await ApiInterface.filter(document=document).update(is_active=False)
        
        return {"code": 200, "msg": "文档删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics():
    """获取接口管理统计信息"""
    try:
        # 统计文档数量
        total_documents = await ApiDocument.filter(is_deleted=False).count()
        
        # 统计接口数量
        total_interfaces = await ApiInterface.filter(is_active=True).count()
        
        # 按HTTP方法统计
        method_stats = {}
        for method in HttpMethod:
            count = await ApiInterface.filter(method=method, is_active=True).count()
            method_stats[method.value] = count
        
        # 按文档格式统计
        format_stats = {}
        documents = await ApiDocument.filter(is_deleted=False).values("doc_format")
        for doc in documents:
            format = doc["doc_format"]
            format_stats[format] = format_stats.get(format, 0) + 1
        
        # 最近上传的文档
        recent_documents = await ApiDocument.filter(is_deleted=False).order_by("-created_at").limit(5)
        recent_docs_data = []
        for doc in recent_documents:
            recent_docs_data.append({
                "doc_id": doc.doc_id,
                "file_name": doc.file_name,
                "doc_format": doc.doc_format,
                "endpoints_count": doc.endpoints_count,
                "created_at": doc.created_at.isoformat()
            })
        
        return {
            "code": 200,
            "msg": "获取成功",
            "data": {
                "total_documents": total_documents,
                "total_interfaces": total_interfaces,
                "method_statistics": method_stats,
                "format_statistics": format_stats,
                "recent_documents": recent_docs_data
            }
        }
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post("/upload-document", response_model=DocumentUploadResponse)
async def upload_api_document(file: UploadFile = File(...)):
    """上传API文档文件"""
    try:
        logger.info(f"开始上传API文档: {file.filename}")

        # 验证文件类型
        allowed_extensions = ['.json', '.yaml', '.yml', '.pdf', '.md', '.txt']
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}. 支持的类型: {', '.join(allowed_extensions)}"
            )

        # 验证文件大小 (50MB)
        max_size = 50 * 1024 * 1024
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail="文件大小超过50MB限制")

        # 生成会话ID和文档ID
        session_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())

        # 确定文档格式
        doc_format = _detect_document_format(file.filename, content)

        # 保存文件
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{session_id}_{file.filename}")

        with open(file_path, "wb") as f:
            f.write(content)

        # 创建文档记录
        document = await ApiDocument.create(
            doc_id=doc_id,
            session_id=session_id,
            file_name=file.filename,
            file_path=file_path,
            file_size=len(content),
            doc_format=doc_format.value,
            api_info={},
            parse_status=SessionStatus.CREATED
        )

        logger.info(f"文档上传成功: {file.filename}, session_id: {session_id}")

        return DocumentUploadResponse(
            session_id=session_id,
            file_name=file.filename,
            msg=f"文件上传成功，会话ID: {session_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传文档失败: {str(e)}")


@router.get("/parse-status/{session_id}", response_model=ParseStatusResponse)
async def get_parse_status(session_id: str):
    """获取解析状态"""
    try:
        document = await ApiDocument.filter(session_id=session_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 构建响应数据
        result = None
        if document.parse_status == SessionStatus.COMPLETED:
            # 获取解析结果
            interfaces = await ApiInterface.filter(document=document, is_active=True).count()
            result = {
                "doc_id": document.doc_id,
                "api_info": document.api_info,
                "endpoints_count": document.endpoints_count,
                "interfaces_count": interfaces,
                "confidence_score": document.confidence_score,
                "processing_time": document.processing_time,
                "parse_errors": document.parse_errors,
                "parse_warnings": document.parse_warnings
            }

        return ParseStatusResponse(
            status=document.parse_status.value,
            progress=100.0 if document.parse_status == SessionStatus.COMPLETED else 50.0,
            result=result,
            msg=_get_status_message(document.parse_status)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取解析状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取解析状态失败: {str(e)}")


def _detect_document_format(filename: str, content: bytes) -> DocumentFormat:
    """检测文档格式"""
    file_ext = os.path.splitext(filename)[1].lower()

    if file_ext == '.pdf':
        return DocumentFormat.PDF
    elif file_ext in ['.json']:
        # 尝试检测是否为OpenAPI或Postman
        try:
            import json
            data = json.loads(content.decode('utf-8'))
            if 'openapi' in data or 'swagger' in data:
                return DocumentFormat.OPENAPI
            elif 'info' in data and 'item' in data:
                return DocumentFormat.POSTMAN
            else:
                return DocumentFormat.OPENAPI  # 默认为OpenAPI
        except:
            return DocumentFormat.OPENAPI
    elif file_ext in ['.yaml', '.yml']:
        return DocumentFormat.OPENAPI
    elif file_ext in ['.md', '.txt']:
        return DocumentFormat.MARKDOWN
    else:
        return DocumentFormat.AUTO


def _get_status_message(status: SessionStatus) -> str:
    """获取状态消息"""
    status_messages = {
        SessionStatus.CREATED: "文档已上传，等待解析",
        SessionStatus.PROCESSING: "正在解析文档...",
        SessionStatus.COMPLETED: "解析完成",
        SessionStatus.FAILED: "解析失败",
        SessionStatus.CANCELLED: "解析已取消"
    }
    return status_messages.get(status, "未知状态")


@router.post("/interfaces/{interface_id}/generate-script", response_model=ScriptGenerationResponse)
async def generate_interface_script(interface_id: str):
    """为指定接口生成测试脚本"""
    try:
        # 1. 获取接口信息
        interface = await ApiInterface.filter(
            interface_id=interface_id,
            is_active=True
        ).select_related("document").prefetch_related("parameters", "responses").first()

        if not interface:
            raise HTTPException(status_code=404, detail="接口不存在")

        # 2. 获取文档信息
        document = interface.document

        # 3. 生成会话ID
        session_id = str(uuid.uuid4())

        # 4. 获取编排器实例
        orch = get_orchestrator()

        # 5. 直接传递数据库对象给编排器，避免重复封装
        result = await orch.generate_interface_script(
            session_id=session_id,
            interface_obj=interface,  # 直接传递接口对象
            document_obj=document     # 直接传递文档对象
        )

        logger.info(f"已启动接口脚本生成任务: interface_id={interface_id}, session_id={session_id}")

        return ScriptGenerationResponse(
            success=result["success"],
            message=result["message"],
            session_id=result["session_id"],
            task_id=result.get("interface_id", interface_id)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成接口脚本失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成脚本失败: {str(e)}")


@router.get("/script-generation/{session_id}/status")
async def get_script_generation_status(session_id: str):
    """获取脚本生成状态"""
    try:
        # 获取编排器实例
        orch = get_orchestrator()

        # 获取会话状态
        status_info = await orch.get_session_status(session_id)

        return {
            "success": status_info.get("success", False),
            "session_id": session_id,
            "status": status_info.get("status", "unknown"),
            "message": status_info.get("message", ""),
            "data": status_info.get("data", {})
        }

    except Exception as e:
        logger.error(f"获取脚本生成状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")

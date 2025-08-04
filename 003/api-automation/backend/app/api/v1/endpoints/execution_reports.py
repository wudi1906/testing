"""
执行报告API端点
提供脚本执行报告的查询、生成、预览、下载等功能
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse, HTMLResponse
from loguru import logger

from app.schemas.execution_report import (
    ExecutionReportQuery, ExecutionReportListResponse, ExecutionReportDetail,
    ExecutionStatistics, ReportGenerationRequest, ReportPreviewResponse,
    ExecutionLogsResponse
)
from app.services.api_automation.execution_report_service import ExecutionReportService
from app.core.response import success_response, error_response

router = APIRouter(prefix="/execution-reports", tags=["执行报告"])


@router.get("/", summary="获取执行报告列表")
async def get_execution_reports(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="执行状态"),
    environment: Optional[str] = Query(None, description="执行环境"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    document_id: Optional[int] = Query(None, description="文档ID"),
    script_id: Optional[str] = Query(None, description="脚本ID")
) -> dict:
    """获取执行报告列表"""
    try:
        query = ExecutionReportQuery(
            page=page,
            page_size=page_size,
            status=status,
            environment=environment,
            start_time=start_time,
            end_time=end_time,
            keyword=keyword,
            document_id=document_id,
            script_id=script_id
        )
        
        service = ExecutionReportService()
        result = await service.get_execution_reports(query)
        
        return success_response(data=result.dict())
        
    except Exception as e:
        logger.error(f"获取执行报告列表失败: {str(e)}")
        return error_response(message=f"获取执行报告列表失败: {str(e)}")


@router.get("/{execution_id}", summary="获取执行报告详情")
async def get_execution_report_detail(execution_id: str) -> dict:
    """获取执行报告详情"""
    try:
        service = ExecutionReportService()
        detail = await service.get_execution_report_detail(execution_id)
        
        return success_response(data=detail.dict())
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"获取执行报告详情失败: {str(e)}")
        return error_response(message=f"获取执行报告详情失败: {str(e)}")


@router.get("/statistics/summary", summary="获取执行统计信息")
async def get_execution_statistics(
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    environment: Optional[str] = Query(None, description="执行环境")
) -> dict:
    """获取执行统计信息"""
    try:
        service = ExecutionReportService()
        stats = await service.get_execution_statistics(
            start_date=start_date,
            end_date=end_date,
            environment=environment
        )
        
        return success_response(data=stats.dict())
        
    except Exception as e:
        logger.error(f"获取执行统计信息失败: {str(e)}")
        return error_response(message=f"获取执行统计信息失败: {str(e)}")


@router.post("/{execution_id}/generate", summary="生成执行报告")
async def generate_execution_report(
    execution_id: str,
    request: ReportGenerationRequest
) -> dict:
    """生成执行报告"""
    try:
        service = ExecutionReportService()
        generated_files = []
        
        for format_type in request.formats:
            if format_type.lower() == "html":
                file_path = await service.generate_html_report(
                    execution_id, 
                    request.include_details
                )
                generated_files.append({
                    "format": "html",
                    "path": file_path,
                    "name": f"execution_report_{execution_id}.html"
                })
            elif format_type.lower() == "json":
                file_path = await service.generate_json_report(
                    execution_id,
                    request.include_details
                )
                generated_files.append({
                    "format": "json", 
                    "path": file_path,
                    "name": f"execution_report_{execution_id}.json"
                })
        
        return success_response(
            data={
                "execution_id": execution_id,
                "generated_files": generated_files,
                "message": f"成功生成 {len(generated_files)} 个报告文件"
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"生成执行报告失败: {str(e)}")
        return error_response(message=f"生成执行报告失败: {str(e)}")


@router.get("/{execution_id}/preview/{file_name}", summary="预览报告文件")
async def preview_report_file(execution_id: str, file_name: str):
    """预览报告文件"""
    try:
        service = ExecutionReportService()
        content, content_type = await service.get_report_content(execution_id, file_name)
        
        if content_type == "text/html":
            return HTMLResponse(content=content)
        else:
            return Response(content=content, media_type=content_type)
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"预览报告文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"预览报告文件失败: {str(e)}")


@router.get("/{execution_id}/download/{file_name}", summary="下载报告文件")
async def download_report_file(execution_id: str, file_name: str):
    """下载报告文件"""
    try:
        service = ExecutionReportService()
        file_path = service.reports_dir / execution_id / file_name
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="报告文件不存在")
        
        return FileResponse(
            path=str(file_path),
            filename=file_name,
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"下载报告文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载报告文件失败: {str(e)}")


@router.get("/{execution_id}/logs", summary="获取执行日志")
async def get_execution_logs(
    execution_id: str,
    limit: int = Query(1000, ge=1, le=10000, description="日志条数限制")
) -> dict:
    """获取执行日志"""
    try:
        service = ExecutionReportService()
        logs = await service.get_execution_logs(execution_id, limit)
        
        response = ExecutionLogsResponse(
            logs=logs,
            total=len(logs),
            execution_id=execution_id
        )
        
        return success_response(data=response.dict())
        
    except Exception as e:
        logger.error(f"获取执行日志失败: {str(e)}")
        return error_response(message=f"获取执行日志失败: {str(e)}")


@router.delete("/{execution_id}", summary="删除执行报告")
async def delete_execution_report(execution_id: str) -> dict:
    """删除执行报告"""
    try:
        service = ExecutionReportService()
        
        # 删除报告文件
        report_dir = service.reports_dir / execution_id
        if report_dir.exists():
            import shutil
            shutil.rmtree(report_dir)
        
        # 这里可以选择是否删除数据库记录
        # 通常只删除报告文件，保留执行记录
        
        return success_response(
            data={
                "execution_id": execution_id,
                "message": "执行报告已删除"
            }
        )
        
    except Exception as e:
        logger.error(f"删除执行报告失败: {str(e)}")
        return error_response(message=f"删除执行报告失败: {str(e)}")


@router.get("/{execution_id}/export", summary="导出执行报告")
async def export_execution_report(
    execution_id: str,
    format: str = Query("json", description="导出格式: json, csv, excel")
) -> dict:
    """导出执行报告"""
    try:
        service = ExecutionReportService()
        detail = await service.get_execution_report_detail(execution_id)
        
        if format.lower() == "json":
            # 生成JSON报告
            file_path = await service.generate_json_report(execution_id, True)
            return success_response(
                data={
                    "execution_id": execution_id,
                    "export_format": "json",
                    "file_path": file_path,
                    "download_url": f"/api/v1/execution-reports/{execution_id}/download/{file_path.split('/')[-1]}"
                }
            )
        else:
            # 其他格式暂不支持
            return error_response(message=f"不支持的导出格式: {format}")
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"导出执行报告失败: {str(e)}")
        return error_response(message=f"导出执行报告失败: {str(e)}")


@router.post("/{execution_id}/share", summary="分享执行报告")
async def share_execution_report(execution_id: str) -> dict:
    """分享执行报告"""
    try:
        # 生成分享链接
        import uuid
        share_token = str(uuid.uuid4())
        
        # 这里应该将分享信息存储到数据库
        # 暂时返回模拟的分享链接
        
        return success_response(
            data={
                "execution_id": execution_id,
                "share_token": share_token,
                "share_url": f"/shared-reports/{share_token}",
                "expires_at": "2024-12-31T23:59:59",
                "message": "报告分享链接已生成"
            }
        )
        
    except Exception as e:
        logger.error(f"分享执行报告失败: {str(e)}")
        return error_response(message=f"分享执行报告失败: {str(e)}")


@router.get("/shared/{share_token}", summary="访问分享的报告")
async def get_shared_report(share_token: str):
    """访问分享的报告"""
    try:
        # 这里应该根据分享token查找对应的执行报告
        # 暂时返回错误
        raise HTTPException(status_code=404, detail="分享链接不存在或已过期")
        
    except Exception as e:
        logger.error(f"访问分享报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"访问分享报告失败: {str(e)}")

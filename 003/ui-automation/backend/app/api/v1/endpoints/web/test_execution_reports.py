"""
测试报告API接口
"""
import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy import desc

from app.database.connection import db_manager
from app.database.models.reports import TestReport
from app.services.test_report_service import test_report_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/script/{script_id}/latest")
async def get_latest_report_by_script_id(script_id: str):
    """根据脚本ID获取最新的测试报告"""
    try:
        report = await test_report_service.get_report_by_script_id(script_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"未找到脚本 {script_id} 的测试报告")
        
        return {
            "success": True,
            "data": report.to_dict(),
            "message": "获取测试报告成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取测试报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取测试报告失败: {str(e)}")


@router.get("/execution/{execution_id}")
async def get_report_by_execution_id(execution_id: str):
    """根据执行ID获取测试报告"""
    try:
        report = await test_report_service.get_report_by_execution_id(execution_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"未找到执行ID {execution_id} 的测试报告")
        
        return {
            "success": True,
            "data": report.to_dict(),
            "message": "获取测试报告成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取测试报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取测试报告失败: {str(e)}")


@router.get("/session/{session_id}")
async def get_reports_by_session_id(session_id: str):
    """根据会话ID获取所有测试报告"""
    try:
        reports = await test_report_service.get_reports_by_session_id(session_id)
        
        return {
            "success": True,
            "data": [report.to_dict() for report in reports],
            "total": len(reports),
            "message": "获取测试报告列表成功"
        }
    except Exception as e:
        logger.error(f"获取测试报告列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取测试报告列表失败: {str(e)}")


@router.get("/view/{execution_id}")
async def view_report_html(execution_id: str):
    """查看HTML测试报告"""
    try:
        # 获取报告记录
        report = await test_report_service.get_report_by_execution_id(execution_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"未找到执行ID {execution_id} 的测试报告")

        # 获取报告文件路径
        report_path = await test_report_service.get_report_file_path(execution_id)
        if not report_path or not os.path.exists(report_path):
            # 如果找不到报告文件，返回详细错误信息
            error_msg = f"测试报告文件不存在"
            if report.report_path:
                error_msg += f"，数据库中记录的路径: {report.report_path}"
            raise HTTPException(status_code=404, detail=error_msg)

        logger.info(f"返回测试报告文件: {report_path}")

        # 读取HTML文件内容并直接返回
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            return HTMLResponse(
                content=html_content,
                media_type="text/html"
            )
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试其他编码
            try:
                with open(report_path, 'r', encoding='gbk') as f:
                    html_content = f.read()
                return HTMLResponse(
                    content=html_content,
                    media_type="text/html"
                )
            except Exception as e:
                logger.error(f"读取报告文件失败: {str(e)}")
                raise HTTPException(status_code=500, detail=f"读取报告文件失败: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查看测试报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查看测试报告失败: {str(e)}")


@router.get("/script/{script_id}/check")
async def check_latest_report_by_script_id(script_id: str):
    """检查脚本是否有最新的测试报告"""
    try:
        # 获取最新报告记录
        report = await test_report_service.get_report_by_script_id(script_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"未找到脚本 {script_id} 的测试报告")

        return {
            "exists": True,
            "report_id": report.id,
            "execution_id": report.execution_id,
            "status": report.status,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "report_url": f"/api/v1/web/reports/view/script/{script_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查测试报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"检查测试报告失败: {str(e)}")


@router.get("/view/script/{script_id}")
async def view_latest_report_by_script_id(script_id: str):
    """根据脚本ID查看最新的HTML测试报告"""
    try:
        # 获取最新报告记录
        report = await test_report_service.get_report_by_script_id(script_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"未找到脚本 {script_id} 的测试报告")

        # 获取报告文件路径
        report_path = await test_report_service.get_report_file_path_by_script_id(script_id)
        if not report_path or not os.path.exists(report_path):
            # 如果找不到报告文件，返回详细错误信息
            error_msg = f"脚本 {script_id} 的测试报告文件不存在"
            if report.report_path:
                error_msg += f"，数据库中记录的路径: {report.report_path}"
            raise HTTPException(status_code=404, detail=error_msg)

        logger.info(f"返回脚本 {script_id} 的测试报告文件: {report_path}")

        # 读取HTML文件内容并直接返回
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            return HTMLResponse(
                content=html_content,
                media_type="text/html"
            )
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试其他编码
            try:
                with open(report_path, 'r', encoding='gbk') as f:
                    html_content = f.read()
                return HTMLResponse(
                    content=html_content,
                    media_type="text/html"
                )
            except Exception as e:
                logger.error(f"读取报告文件失败: {str(e)}")
                raise HTTPException(status_code=500, detail=f"读取报告文件失败: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查看测试报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"查看测试报告失败: {str(e)}")


@router.get("/list")
async def list_reports(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    script_id: Optional[str] = Query(None, description="脚本ID过滤"),
    status: Optional[str] = Query(None, description="状态过滤")
):
    """获取测试报告列表"""
    try:
        async with db_manager.get_session() as session:
            from sqlalchemy import select, func

            # 构建基础查询
            stmt = select(TestReport)
            count_stmt = select(func.count(TestReport.id))

            # 添加过滤条件
            if script_id:
                stmt = stmt.filter(TestReport.script_id == script_id)
                count_stmt = count_stmt.filter(TestReport.script_id == script_id)
            if status:
                stmt = stmt.filter(TestReport.status == status)
                count_stmt = count_stmt.filter(TestReport.status == status)

            # 计算总数
            total_result = await session.execute(count_stmt)
            total = total_result.scalar()

            # 分页查询
            stmt = stmt.order_by(desc(TestReport.created_at)).offset(
                (page - 1) * page_size
            ).limit(page_size)

            result = await session.execute(stmt)
            reports = result.scalars().all()

            return {
                "success": True,
                "data": [report.to_dict() for report in reports],
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": (total + page_size - 1) // page_size
                },
                "message": "获取测试报告列表成功"
            }
            
    except Exception as e:
        logger.error(f"获取测试报告列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取测试报告列表失败: {str(e)}")


@router.delete("/{report_id}")
async def delete_report(report_id: int):
    """删除测试报告"""
    try:
        async with db_manager.get_session() as session:
            from sqlalchemy import select

            # 查找报告
            stmt = select(TestReport).filter(TestReport.id == report_id)
            result = await session.execute(stmt)
            report = result.scalar_one_or_none()

            if not report:
                raise HTTPException(status_code=404, detail=f"未找到ID为 {report_id} 的测试报告")

            # 删除报告文件（可选）
            if report.report_path and os.path.exists(report.report_path):
                try:
                    os.remove(report.report_path)
                    logger.info(f"已删除报告文件: {report.report_path}")
                except Exception as e:
                    logger.warning(f"删除报告文件失败: {str(e)}")

            # 删除MySQL数据库记录
            await session.delete(report)
            await session.commit()

            return {
                "success": True,
                "message": f"测试报告 {report_id} 删除成功"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除测试报告失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除测试报告失败: {str(e)}")


@router.get("/stats")
async def get_report_stats():
    """获取测试报告统计信息"""
    try:
        async with db_manager.get_session() as session:
            from sqlalchemy import select, func

            # 总报告数
            total_stmt = select(func.count(TestReport.id))
            total_result = await session.execute(total_stmt)
            total_reports = total_result.scalar()

            # 按状态统计
            passed_stmt = select(func.count(TestReport.id)).filter(TestReport.status == "passed")
            passed_result = await session.execute(passed_stmt)
            passed_reports = passed_result.scalar()

            failed_stmt = select(func.count(TestReport.id)).filter(TestReport.status == "failed")
            failed_result = await session.execute(failed_stmt)
            failed_reports = failed_result.scalar()

            error_stmt = select(func.count(TestReport.id)).filter(TestReport.status == "error")
            error_result = await session.execute(error_stmt)
            error_reports = error_result.scalar()

            # 成功率
            success_rate = (passed_reports / total_reports * 100) if total_reports > 0 else 0

            # 最近的报告
            recent_stmt = select(TestReport).order_by(desc(TestReport.created_at)).limit(5)
            recent_result = await session.execute(recent_stmt)
            recent_reports = recent_result.scalars().all()

            return {
                "success": True,
                "data": {
                    "total_reports": total_reports,
                    "passed_reports": passed_reports,
                    "failed_reports": failed_reports,
                    "error_reports": error_reports,
                    "success_rate": round(success_rate, 2),
                    "recent_reports": [report.to_dict() for report in recent_reports]
                },
                "message": "获取统计信息成功"
            }
            
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

"""
执行报告服务
负责处理脚本执行报告的查询、生成、预览等功能
"""

import os
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import asyncio

from tortoise.expressions import Q
from tortoise.functions import Count, Avg, Sum
from tortoise.queryset import QuerySet

from app.models.api_automation import (
    TestExecution, ScriptExecutionResult, TestScript, 
    ApiDocument, ApiInterface
)
from app.schemas.execution_report import (
    ExecutionReportQuery, ExecutionReportSummary, ExecutionReportDetail,
    ExecutionReportListResponse, ScriptResultSummary, ReportFile,
    ExecutionStatistics, TestResultDetail, ExecutionLogEntry
)
from app.core.enums import ExecutionStatus


class ExecutionReportService:
    """执行报告服务"""
    
    def __init__(self):
        self.service_name = "ExecutionReportService"
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
    
    async def get_execution_reports(
        self, 
        query: ExecutionReportQuery
    ) -> ExecutionReportListResponse:
        """获取执行报告列表"""
        try:
            # 构建查询条件
            filters = Q()
            
            if query.status:
                filters &= Q(status=query.status)
            
            if query.environment:
                filters &= Q(environment=query.environment)
            
            if query.start_time:
                filters &= Q(start_time__gte=query.start_time)
            
            if query.end_time:
                filters &= Q(end_time__lte=query.end_time)
            
            if query.document_id:
                filters &= Q(document_id=query.document_id)
            
            if query.keyword:
                filters &= (
                    Q(execution_id__icontains=query.keyword) |
                    Q(session_id__icontains=query.keyword) |
                    Q(description__icontains=query.keyword)
                )
            
            # 查询总数
            total = await TestExecution.filter(filters).count()
            
            # 分页查询
            offset = (query.page - 1) * query.page_size
            executions = await TestExecution.filter(filters).select_related(
                "document"
            ).order_by("-created_at").offset(offset).limit(query.page_size)
            
            # 转换为响应格式
            items = []
            for execution in executions:
                item = ExecutionReportSummary(
                    execution_id=execution.execution_id,
                    session_id=execution.session_id,
                    document_id=execution.document.id,
                    document_name=execution.document.title,
                    environment=execution.environment,
                    status=execution.status.value,
                    start_time=execution.start_time,
                    end_time=execution.end_time,
                    execution_time=execution.execution_time,
                    total_tests=execution.total_tests,
                    passed_tests=execution.passed_tests,
                    failed_tests=execution.failed_tests,
                    success_rate=execution.success_rate,
                    description=execution.description,
                    created_at=execution.created_at
                )
                items.append(item)
            
            total_pages = (total + query.page_size - 1) // query.page_size
            
            return ExecutionReportListResponse(
                items=items,
                total=total,
                page=query.page,
                page_size=query.page_size,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error(f"获取执行报告列表失败: {str(e)}")
            raise
    
    async def get_execution_report_detail(
        self, 
        execution_id: str
    ) -> ExecutionReportDetail:
        """获取执行报告详情"""
        try:
            # 查询执行记录
            execution = await TestExecution.filter(
                execution_id=execution_id
            ).select_related("document").first()
            
            if not execution:
                raise ValueError(f"执行记录不存在: {execution_id}")
            
            # 查询脚本执行结果
            script_results = await ScriptExecutionResult.filter(
                execution=execution
            ).select_related("script")
            
            # 转换脚本结果
            script_summaries = []
            for result in script_results:
                summary = ScriptResultSummary(
                    script_id=result.script.script_id,
                    script_name=result.script_name,
                    status=result.status,
                    duration=result.duration,
                    total_tests=result.total_tests,
                    passed_tests=result.passed_tests,
                    failed_tests=result.failed_tests,
                    skipped_tests=result.skipped_tests,
                    error_tests=result.error_tests,
                    success_rate=(result.passed_tests / result.total_tests * 100) if result.total_tests > 0 else 0,
                    response_time=result.response_time,
                    error_message=result.error_message
                )
                script_summaries.append(summary)
            
            # 处理报告文件
            report_files = []
            for file_info in execution.report_files:
                if isinstance(file_info, dict):
                    file_path = Path(file_info.get("path", ""))
                    if file_path.exists():
                        report_file = ReportFile(
                            name=file_info.get("name", file_path.name),
                            path=str(file_path),
                            format=file_info.get("format", file_path.suffix.lstrip(".")),
                            size=file_path.stat().st_size,
                            created_at=datetime.fromtimestamp(file_path.stat().st_ctime),
                            download_url=f"/api/v1/execution-reports/{execution_id}/download/{file_path.name}"
                        )
                        report_files.append(report_file)
            
            # 构建详情响应
            detail = ExecutionReportDetail(
                execution_id=execution.execution_id,
                session_id=execution.session_id,
                document_id=execution.document.id,
                document_name=execution.document.title,
                environment=execution.environment,
                status=execution.status.value,
                start_time=execution.start_time,
                end_time=execution.end_time,
                execution_time=execution.execution_time,
                execution_config=execution.execution_config,
                parallel=execution.parallel,
                max_workers=execution.max_workers,
                total_tests=execution.total_tests,
                passed_tests=execution.passed_tests,
                failed_tests=execution.failed_tests,
                skipped_tests=execution.skipped_tests,
                error_tests=execution.error_tests,
                success_rate=execution.success_rate,
                avg_response_time=execution.avg_response_time,
                max_response_time=execution.max_response_time,
                min_response_time=execution.min_response_time,
                script_results=script_summaries,
                report_files=report_files,
                error_details=execution.error_details,
                summary=execution.summary,
                description=execution.description,
                created_at=execution.created_at,
                updated_at=execution.updated_at
            )
            
            return detail
            
        except Exception as e:
            logger.error(f"获取执行报告详情失败: {str(e)}")
            raise
    
    async def get_execution_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        environment: Optional[str] = None
    ) -> ExecutionStatistics:
        """获取执行统计信息"""
        try:
            # 构建查询条件
            filters = Q()
            
            if start_date:
                filters &= Q(created_at__gte=start_date)
            
            if end_date:
                filters &= Q(created_at__lte=end_date)
            
            if environment:
                filters &= Q(environment=environment)
            
            # 统计查询
            stats = await TestExecution.filter(filters).aggregate(
                total_executions=Count("id"),
                successful_executions=Count("id", _filter=Q(status=ExecutionStatus.COMPLETED)),
                failed_executions=Count("id", _filter=Q(status=ExecutionStatus.FAILED)),
                avg_execution_time=Avg("execution_time"),
                avg_success_rate=Avg("success_rate"),
                total_tests=Sum("total_tests"),
                total_passed=Sum("passed_tests"),
                total_failed=Sum("failed_tests")
            )
            
            return ExecutionStatistics(
                total_executions=stats["total_executions"] or 0,
                successful_executions=stats["successful_executions"] or 0,
                failed_executions=stats["failed_executions"] or 0,
                avg_execution_time=stats["avg_execution_time"] or 0.0,
                avg_success_rate=stats["avg_success_rate"] or 0.0,
                total_tests=stats["total_tests"] or 0,
                total_passed=stats["total_passed"] or 0,
                total_failed=stats["total_failed"] or 0
            )
            
        except Exception as e:
            logger.error(f"获取执行统计信息失败: {str(e)}")
            raise

    async def generate_html_report(
        self,
        execution_id: str,
        include_details: bool = True
    ) -> str:
        """生成HTML格式报告"""
        try:
            # 获取执行详情
            detail = await self.get_execution_report_detail(execution_id)

            # 生成HTML内容
            html_content = self._generate_html_content(detail, include_details)

            # 保存报告文件
            report_dir = self.reports_dir / execution_id
            report_dir.mkdir(exist_ok=True)

            report_file = report_dir / f"execution_report_{execution_id}.html"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # 更新执行记录的报告文件列表
            await self._update_report_files(execution_id, {
                "name": report_file.name,
                "path": str(report_file),
                "format": "html",
                "size": report_file.stat().st_size,
                "created_at": datetime.now().isoformat()
            })

            return str(report_file)

        except Exception as e:
            logger.error(f"生成HTML报告失败: {str(e)}")
            raise

    async def generate_json_report(
        self,
        execution_id: str,
        include_details: bool = True
    ) -> str:
        """生成JSON格式报告"""
        try:
            # 获取执行详情
            detail = await self.get_execution_report_detail(execution_id)

            # 转换为JSON格式
            report_data = detail.dict()

            # 保存报告文件
            report_dir = self.reports_dir / execution_id
            report_dir.mkdir(exist_ok=True)

            report_file = report_dir / f"execution_report_{execution_id}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)

            # 更新执行记录的报告文件列表
            await self._update_report_files(execution_id, {
                "name": report_file.name,
                "path": str(report_file),
                "format": "json",
                "size": report_file.stat().st_size,
                "created_at": datetime.now().isoformat()
            })

            return str(report_file)

        except Exception as e:
            logger.error(f"生成JSON报告失败: {str(e)}")
            raise

    async def get_report_content(
        self,
        execution_id: str,
        file_name: str
    ) -> Tuple[str, str]:
        """获取报告文件内容"""
        try:
            report_file = self.reports_dir / execution_id / file_name

            if not report_file.exists():
                raise FileNotFoundError(f"报告文件不存在: {file_name}")

            # 根据文件扩展名确定内容类型
            content_type_map = {
                '.html': 'text/html',
                '.json': 'application/json',
                '.xml': 'application/xml',
                '.txt': 'text/plain'
            }

            content_type = content_type_map.get(
                report_file.suffix.lower(),
                'application/octet-stream'
            )

            # 读取文件内容
            with open(report_file, 'r', encoding='utf-8') as f:
                content = f.read()

            return content, content_type

        except Exception as e:
            logger.error(f"获取报告内容失败: {str(e)}")
            raise

    async def get_execution_logs(
        self,
        execution_id: str,
        limit: int = 1000
    ) -> List[ExecutionLogEntry]:
        """获取执行日志"""
        try:
            # 这里应该从日志文件或数据库中读取日志
            # 暂时返回模拟数据
            logs = []

            # 查找日志文件
            log_dir = Path("logs") / execution_id
            if log_dir.exists():
                for log_file in log_dir.glob("*.log"):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                # 简单的日志解析
                                parts = line.strip().split(' ', 3)
                                if len(parts) >= 4:
                                    timestamp_str = f"{parts[0]} {parts[1]}"
                                    level = parts[2].strip('[]')
                                    message = parts[3]

                                    try:
                                        timestamp = datetime.fromisoformat(timestamp_str)
                                    except:
                                        timestamp = datetime.now()

                                    log_entry = ExecutionLogEntry(
                                        timestamp=timestamp,
                                        level=level,
                                        message=message,
                                        source=log_file.name,
                                        execution_id=execution_id
                                    )
                                    logs.append(log_entry)

            # 按时间排序并限制数量
            logs.sort(key=lambda x: x.timestamp, reverse=True)
            return logs[:limit]

        except Exception as e:
            logger.error(f"获取执行日志失败: {str(e)}")
            return []

    def _generate_html_content(
        self,
        detail: ExecutionReportDetail,
        include_details: bool
    ) -> str:
        """生成HTML报告内容"""
        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>执行报告 - {detail.execution_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ border-bottom: 2px solid #007bff; padding-bottom: 20px; margin-bottom: 30px; }}
        .title {{ color: #007bff; margin: 0; }}
        .subtitle {{ color: #666; margin: 5px 0 0 0; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        .section {{ margin: 30px 0; }}
        .section-title {{ color: #333; border-bottom: 1px solid #ddd; padding-bottom: 10px; }}
        .script-result {{ background: #f8f9fa; margin: 10px 0; padding: 15px; border-radius: 6px; border-left: 4px solid #007bff; }}
        .status-success {{ border-left-color: #28a745; }}
        .status-failed {{ border-left-color: #dc3545; }}
        .status-pending {{ border-left-color: #ffc107; }}
        .progress-bar {{ background: #e9ecef; height: 20px; border-radius: 10px; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: #007bff; transition: width 0.3s; }}
        .error-message {{ background: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; margin: 10px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; font-weight: bold; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">接口脚本执行报告</h1>
            <p class="subtitle">执行ID: {detail.execution_id} | 文档: {detail.document_name}</p>
            <p class="timestamp">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{detail.total_tests}</div>
                <div class="stat-label">总测试数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #28a745;">{detail.passed_tests}</div>
                <div class="stat-label">通过测试</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #dc3545;">{detail.failed_tests}</div>
                <div class="stat-label">失败测试</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{detail.success_rate:.1f}%</div>
                <div class="stat-label">成功率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{detail.execution_time:.2f}s</div>
                <div class="stat-label">执行时间</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{detail.avg_response_time:.0f}ms</div>
                <div class="stat-label">平均响应时间</div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">执行信息</h2>
            <table>
                <tr><th>执行环境</th><td>{detail.environment}</td></tr>
                <tr><th>执行状态</th><td>{detail.status}</td></tr>
                <tr><th>开始时间</th><td>{detail.start_time.strftime('%Y-%m-%d %H:%M:%S') if detail.start_time else 'N/A'}</td></tr>
                <tr><th>结束时间</th><td>{detail.end_time.strftime('%Y-%m-%d %H:%M:%S') if detail.end_time else 'N/A'}</td></tr>
                <tr><th>并行执行</th><td>{'是' if detail.parallel else '否'}</td></tr>
                <tr><th>最大工作线程</th><td>{detail.max_workers}</td></tr>
                <tr><th>执行描述</th><td>{detail.description or 'N/A'}</td></tr>
            </table>
        </div>

        <div class="section">
            <h2 class="section-title">脚本执行结果</h2>
            {''.join([self._generate_script_result_html(script) for script in detail.script_results])}
        </div>

        {self._generate_error_details_html(detail.error_details) if detail.error_details else ''}
    </div>
</body>
</html>
        """
        return html_template

    def _generate_script_result_html(self, script: ScriptResultSummary) -> str:
        """生成脚本结果HTML"""
        status_class = f"status-{script.status.lower()}"
        return f"""
        <div class="script-result {status_class}">
            <h3>{script.script_name}</h3>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{script.total_tests}</div>
                    <div class="stat-label">总测试</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: #28a745;">{script.passed_tests}</div>
                    <div class="stat-label">通过</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: #dc3545;">{script.failed_tests}</div>
                    <div class="stat-label">失败</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{script.success_rate:.1f}%</div>
                    <div class="stat-label">成功率</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{script.duration:.2f}s</div>
                    <div class="stat-label">执行时间</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{script.response_time:.0f}ms</div>
                    <div class="stat-label">响应时间</div>
                </div>
            </div>
            {f'<div class="error-message">{script.error_message}</div>' if script.error_message else ''}
        </div>
        """

    def _generate_error_details_html(self, error_details: List[Dict[str, Any]]) -> str:
        """生成错误详情HTML"""
        if not error_details:
            return ""

        error_html = '<div class="section"><h2 class="section-title">错误详情</h2>'
        for error in error_details:
            error_html += f"""
            <div class="error-message">
                <strong>错误类型:</strong> {error.get('type', 'Unknown')}<br>
                <strong>错误信息:</strong> {error.get('message', 'N/A')}<br>
                <strong>发生时间:</strong> {error.get('timestamp', 'N/A')}
            </div>
            """
        error_html += '</div>'
        return error_html

    async def _update_report_files(self, execution_id: str, file_info: Dict[str, Any]):
        """更新执行记录的报告文件列表"""
        try:
            execution = await TestExecution.get(execution_id=execution_id)
            report_files = execution.report_files or []

            # 检查是否已存在同名文件
            existing_index = None
            for i, existing_file in enumerate(report_files):
                if existing_file.get("name") == file_info["name"]:
                    existing_index = i
                    break

            if existing_index is not None:
                report_files[existing_index] = file_info
            else:
                report_files.append(file_info)

            execution.report_files = report_files
            await execution.save(update_fields=["report_files"])

        except Exception as e:
            logger.error(f"更新报告文件列表失败: {str(e)}")
            raise

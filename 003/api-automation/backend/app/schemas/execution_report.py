"""
执行报告相关的数据模式定义
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ExecutionReportQuery(BaseModel):
    """执行报告查询参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    status: Optional[str] = Field(default=None, description="执行状态")
    environment: Optional[str] = Field(default=None, description="执行环境")
    start_time: Optional[datetime] = Field(default=None, description="开始时间")
    end_time: Optional[datetime] = Field(default=None, description="结束时间")
    keyword: Optional[str] = Field(default=None, description="关键词搜索")
    document_id: Optional[int] = Field(default=None, description="文档ID")
    script_id: Optional[str] = Field(default=None, description="脚本ID")


class ScriptResultSummary(BaseModel):
    """脚本执行结果摘要"""
    script_id: str = Field(description="脚本ID")
    script_name: str = Field(description="脚本名称")
    status: str = Field(description="执行状态")
    duration: float = Field(description="执行时长")
    total_tests: int = Field(description="总测试数")
    passed_tests: int = Field(description="通过测试数")
    failed_tests: int = Field(description="失败测试数")
    skipped_tests: int = Field(description="跳过测试数")
    error_tests: int = Field(description="错误测试数")
    success_rate: float = Field(description="成功率")
    response_time: float = Field(description="响应时间")
    error_message: Optional[str] = Field(default=None, description="错误信息")


class TestResultDetail(BaseModel):
    """测试结果详情"""
    test_id: str = Field(description="测试ID")
    test_name: str = Field(description="测试名称")
    status: str = Field(description="测试状态")
    duration: float = Field(description="执行时长")
    response_time: float = Field(description="响应时间")
    assertions_passed: int = Field(description="通过的断言数")
    assertions_total: int = Field(description="总断言数")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    failure_reason: Optional[str] = Field(default=None, description="失败原因")
    request_data: Optional[Dict[str, Any]] = Field(default=None, description="请求数据")
    response_data: Optional[Dict[str, Any]] = Field(default=None, description="响应数据")
    response_status_code: Optional[int] = Field(default=None, description="响应状态码")


class ReportFile(BaseModel):
    """报告文件信息"""
    name: str = Field(description="文件名")
    path: str = Field(description="文件路径")
    format: str = Field(description="文件格式")
    size: int = Field(description="文件大小")
    created_at: datetime = Field(description="创建时间")
    download_url: str = Field(description="下载链接")


class ExecutionStatistics(BaseModel):
    """执行统计信息"""
    total_executions: int = Field(description="总执行次数")
    successful_executions: int = Field(description="成功执行次数")
    failed_executions: int = Field(description="失败执行次数")
    avg_execution_time: float = Field(description="平均执行时间")
    avg_success_rate: float = Field(description="平均成功率")
    total_tests: int = Field(description="总测试数")
    total_passed: int = Field(description="总通过数")
    total_failed: int = Field(description="总失败数")


class ExecutionReportSummary(BaseModel):
    """执行报告摘要"""
    execution_id: str = Field(description="执行ID")
    session_id: str = Field(description="会话ID")
    document_id: int = Field(description="文档ID")
    document_name: str = Field(description="文档名称")
    environment: str = Field(description="执行环境")
    status: str = Field(description="执行状态")
    start_time: Optional[datetime] = Field(description="开始时间")
    end_time: Optional[datetime] = Field(description="结束时间")
    execution_time: float = Field(description="执行时间")
    total_tests: int = Field(description="总测试数")
    passed_tests: int = Field(description="通过测试数")
    failed_tests: int = Field(description="失败测试数")
    success_rate: float = Field(description="成功率")
    description: str = Field(description="执行描述")
    created_at: datetime = Field(description="创建时间")


class ExecutionReportDetail(BaseModel):
    """执行报告详情"""
    execution_id: str = Field(description="执行ID")
    session_id: str = Field(description="会话ID")
    document_id: int = Field(description="文档ID")
    document_name: str = Field(description="文档名称")
    environment: str = Field(description="执行环境")
    status: str = Field(description="执行状态")
    start_time: Optional[datetime] = Field(description="开始时间")
    end_time: Optional[datetime] = Field(description="结束时间")
    execution_time: float = Field(description="执行时间")
    
    # 执行配置
    execution_config: Dict[str, Any] = Field(description="执行配置")
    parallel: bool = Field(description="是否并行执行")
    max_workers: int = Field(description="最大工作线程数")
    
    # 统计信息
    total_tests: int = Field(description="总测试数")
    passed_tests: int = Field(description="通过测试数")
    failed_tests: int = Field(description="失败测试数")
    skipped_tests: int = Field(description="跳过测试数")
    error_tests: int = Field(description="错误测试数")
    success_rate: float = Field(description="成功率")
    
    # 性能统计
    avg_response_time: float = Field(description="平均响应时间")
    max_response_time: float = Field(description="最大响应时间")
    min_response_time: float = Field(description="最小响应时间")
    
    # 脚本执行结果
    script_results: List[ScriptResultSummary] = Field(description="脚本执行结果")
    
    # 报告文件
    report_files: List[ReportFile] = Field(description="报告文件")
    
    # 错误详情
    error_details: List[Dict[str, Any]] = Field(description="错误详情")
    
    # 执行摘要
    summary: Dict[str, Any] = Field(description="执行摘要")
    description: str = Field(description="执行描述")
    
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")


class ExecutionReportListResponse(BaseModel):
    """执行报告列表响应"""
    items: List[ExecutionReportSummary] = Field(description="报告列表")
    total: int = Field(description="总数量")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total_pages: int = Field(description="总页数")


class ReportGenerationRequest(BaseModel):
    """报告生成请求"""
    execution_id: str = Field(description="执行ID")
    formats: List[str] = Field(default=["html", "json"], description="报告格式")
    include_details: bool = Field(default=True, description="是否包含详细信息")
    include_logs: bool = Field(default=True, description="是否包含日志")


class ReportPreviewResponse(BaseModel):
    """报告预览响应"""
    content: str = Field(description="报告内容")
    content_type: str = Field(description="内容类型")
    format: str = Field(description="报告格式")


class ExecutionLogEntry(BaseModel):
    """执行日志条目"""
    timestamp: datetime = Field(description="时间戳")
    level: str = Field(description="日志级别")
    message: str = Field(description="日志消息")
    source: str = Field(description="日志来源")
    execution_id: str = Field(description="执行ID")
    script_id: Optional[str] = Field(default=None, description="脚本ID")


class ExecutionLogsResponse(BaseModel):
    """执行日志响应"""
    logs: List[ExecutionLogEntry] = Field(description="日志列表")
    total: int = Field(description="总日志数")
    execution_id: str = Field(description="执行ID")

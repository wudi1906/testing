"""
测试报告数据模型
用于管理测试执行生成的HTML报告
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from app.schemas.ui_automation import TestStatus


class ReportFormat(str, Enum):
    """报告格式枚举"""
    HTML = "html"
    JSON = "json"
    XML = "xml"
    PDF = "pdf"


class TestCaseResult(BaseModel):
    """测试用例结果模型"""
    name: str = Field(..., description="测试用例名称")
    status: TestStatus = Field(..., description="执行状态")
    duration: float = Field(..., description="执行时长（秒）")
    error_message: Optional[str] = Field(None, description="错误信息")
    screenshots: List[str] = Field(default_factory=list, description="截图路径")
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="执行步骤")


class TestReport(BaseModel):
    """测试报告模型"""
    id: str = Field(..., description="报告唯一标识")
    name: str = Field(..., description="报告名称")
    execution_id: str = Field(..., description="执行ID")
    script_id: Optional[str] = Field(None, description="脚本ID")
    script_name: str = Field(..., description="脚本名称")
    script_format: str = Field(..., description="脚本格式")
    
    # 执行信息
    status: TestStatus = Field(..., description="整体执行状态")
    start_time: str = Field(..., description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")
    duration: float = Field(0.0, description="总执行时长（秒）")
    
    # 测试用例统计
    test_cases: Dict[str, int] = Field(default_factory=lambda: {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0
    }, description="测试用例统计")
    
    # 报告文件
    html_report_path: str = Field(..., description="HTML报告文件路径")
    json_report_path: Optional[str] = Field(None, description="JSON报告文件路径")
    xml_report_path: Optional[str] = Field(None, description="XML报告文件路径")
    
    # 附件
    screenshots: List[str] = Field(default_factory=list, description="截图列表")
    videos: List[str] = Field(default_factory=list, description="视频列表")
    logs: List[str] = Field(default_factory=list, description="日志文件")
    
    # 详细结果
    test_case_results: List[TestCaseResult] = Field(default_factory=list, description="测试用例详细结果")
    
    # 环境信息
    environment: Dict[str, Any] = Field(default_factory=dict, description="执行环境信息")
    browser_info: Dict[str, Any] = Field(default_factory=dict, description="浏览器信息")
    
    # 元数据
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = Field(default_factory=list, description="标签")
    category: Optional[str] = Field(None, description="分类")


class ReportSearchRequest(BaseModel):
    """报告搜索请求模型"""
    query: Optional[str] = Field(None, description="搜索关键词")
    status: Optional[TestStatus] = Field(None, description="状态过滤")
    script_format: Optional[str] = Field(None, description="脚本格式过滤")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    tags: List[str] = Field(default_factory=list, description="标签过滤")
    category: Optional[str] = Field(None, description="分类过滤")
    limit: int = Field(20, ge=1, le=100, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")


class ReportSearchResponse(BaseModel):
    """报告搜索响应模型"""
    reports: List[TestReport] = Field(default_factory=list, description="报告列表")
    total_count: int = Field(0, description="总数量")
    has_more: bool = Field(False, description="是否有更多")


class ReportStatistics(BaseModel):
    """报告统计模型"""
    total_reports: int = Field(0, description="总报告数")
    recent_reports: int = Field(0, description="最近7天报告数")
    success_rate: float = Field(0.0, description="成功率")
    average_duration: float = Field(0.0, description="平均执行时间")
    total_test_cases: int = Field(0, description="总测试用例数")
    
    # 按状态统计
    status_distribution: Dict[str, int] = Field(default_factory=dict, description="状态分布")
    
    # 按格式统计
    format_distribution: Dict[str, int] = Field(default_factory=dict, description="格式分布")
    
    # 趋势数据
    daily_reports: List[Dict[str, Any]] = Field(default_factory=list, description="每日报告数据")
    success_trend: List[Dict[str, Any]] = Field(default_factory=list, description="成功率趋势")


class ReportGenerationRequest(BaseModel):
    """报告生成请求模型"""
    execution_id: str = Field(..., description="执行ID")
    report_name: Optional[str] = Field(None, description="报告名称")
    formats: List[ReportFormat] = Field(default_factory=lambda: [ReportFormat.HTML], description="生成格式")
    include_screenshots: bool = Field(True, description="是否包含截图")
    include_videos: bool = Field(False, description="是否包含视频")
    include_logs: bool = Field(True, description="是否包含日志")
    template: Optional[str] = Field(None, description="报告模板")


class ReportGenerationResponse(BaseModel):
    """报告生成响应模型"""
    report_id: str = Field(..., description="报告ID")
    generation_status: str = Field(..., description="生成状态")
    report_paths: Dict[str, str] = Field(default_factory=dict, description="报告文件路径")
    message: str = Field(..., description="响应消息")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ReportTemplate(BaseModel):
    """报告模板模型"""
    id: str = Field(..., description="模板ID")
    name: str = Field(..., description="模板名称")
    description: str = Field(..., description="模板描述")
    template_path: str = Field(..., description="模板文件路径")
    preview_image: Optional[str] = Field(None, description="预览图片")
    supported_formats: List[ReportFormat] = Field(default_factory=list, description="支持的格式")
    is_default: bool = Field(False, description="是否为默认模板")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ReportExportRequest(BaseModel):
    """报告导出请求模型"""
    report_ids: List[str] = Field(..., description="要导出的报告ID列表")
    export_format: str = Field("zip", description="导出格式")
    include_attachments: bool = Field(True, description="是否包含附件")
    compress: bool = Field(True, description="是否压缩")


class ReportExportResponse(BaseModel):
    """报告导出响应模型"""
    export_id: str = Field(..., description="导出ID")
    download_url: str = Field(..., description="下载链接")
    file_size: int = Field(..., description="文件大小（字节）")
    expires_at: str = Field(..., description="过期时间")
    message: str = Field(..., description="响应消息")


class ReportAnalytics(BaseModel):
    """报告分析模型"""
    report_id: str = Field(..., description="报告ID")
    
    # 性能指标
    page_load_times: List[float] = Field(default_factory=list, description="页面加载时间")
    action_durations: List[Dict[str, float]] = Field(default_factory=list, description="操作耗时")
    memory_usage: List[Dict[str, Any]] = Field(default_factory=list, description="内存使用")
    
    # 错误分析
    error_patterns: List[Dict[str, Any]] = Field(default_factory=list, description="错误模式")
    failure_reasons: Dict[str, int] = Field(default_factory=dict, description="失败原因统计")
    
    # 覆盖率信息
    element_coverage: Dict[str, float] = Field(default_factory=dict, description="元素覆盖率")
    action_coverage: Dict[str, float] = Field(default_factory=dict, description="操作覆盖率")
    
    # 建议
    optimization_suggestions: List[str] = Field(default_factory=list, description="优化建议")
    stability_score: float = Field(0.0, description="稳定性评分")
    performance_score: float = Field(0.0, description="性能评分")

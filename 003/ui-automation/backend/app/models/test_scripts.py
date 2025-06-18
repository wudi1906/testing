"""
测试脚本数据模型
用于管理生成的测试脚本的存储和检索
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from app.schemas.ui_automation import TestStatus


class ScriptFormat(str, Enum):
    """脚本格式枚举"""
    YAML = "yaml"
    PLAYWRIGHT = "playwright"


class ScriptType(str, Enum):
    """脚本类型枚举"""
    IMAGE_ANALYSIS = "image_analysis"
    URL_ANALYSIS = "url_analysis"
    MIXED_ANALYSIS = "mixed_analysis"
    MANUAL_CREATION = "manual_creation"


class TestScript(BaseModel):
    """测试脚本模型"""
    id: str = Field(..., description="脚本唯一标识")
    session_id: str = Field(..., description="会话ID")
    name: str = Field(..., description="脚本名称")
    description: str = Field(..., description="脚本描述")
    script_format: ScriptFormat = Field(..., description="脚本格式")
    script_type: ScriptType = Field(..., description="脚本类型")
    content: str = Field(..., description="脚本内容")
    file_path: str = Field(..., description="文件路径")
    
    # 元数据
    test_description: str = Field(..., description="测试需求描述")
    additional_context: Optional[str] = Field(None, description="额外上下文")
    source_url: Optional[str] = Field(None, description="源URL（URL分析时）")
    source_image_path: Optional[str] = Field(None, description="源图片路径（图片分析时）")
    
    # 执行统计
    execution_count: int = Field(0, description="执行次数")
    last_execution_time: Optional[str] = Field(None, description="最后执行时间")
    last_execution_status: Optional[TestStatus] = Field(None, description="最后执行状态")
    
    # 时间戳
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # 标签和分类
    tags: List[str] = Field(default_factory=list, description="标签")
    category: Optional[str] = Field(None, description="分类")
    priority: int = Field(1, ge=1, le=5, description="优先级")
    
    # 关联信息
    analysis_result_id: Optional[str] = Field(None, description="分析结果ID")
    related_scripts: List[str] = Field(default_factory=list, description="相关脚本ID列表")


class ScriptExecutionRecord(BaseModel):
    """脚本执行记录模型"""
    id: str = Field(..., description="执行记录ID")
    script_id: str = Field(..., description="脚本ID")
    execution_id: str = Field(..., description="执行ID")
    status: TestStatus = Field(..., description="执行状态")
    
    # 执行配置
    execution_config: Dict[str, Any] = Field(default_factory=dict, description="执行配置")
    environment_info: Dict[str, Any] = Field(default_factory=dict, description="环境信息")
    
    # 执行结果
    start_time: str = Field(..., description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")
    duration: Optional[float] = Field(None, description="执行时长（秒）")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    # 产物
    logs: List[str] = Field(default_factory=list, description="执行日志")
    screenshots: List[str] = Field(default_factory=list, description="截图路径")
    reports: List[str] = Field(default_factory=list, description="报告路径")
    artifacts: Dict[str, str] = Field(default_factory=dict, description="其他产物")
    
    # 性能指标
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="性能指标")


class ScriptCollection(BaseModel):
    """脚本集合模型"""
    id: str = Field(..., description="集合ID")
    name: str = Field(..., description="集合名称")
    description: str = Field(..., description="集合描述")
    script_ids: List[str] = Field(default_factory=list, description="脚本ID列表")
    
    # 元数据
    created_by: Optional[str] = Field(None, description="创建者")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # 标签和分类
    tags: List[str] = Field(default_factory=list, description="标签")
    category: Optional[str] = Field(None, description="分类")


class ScriptSearchRequest(BaseModel):
    """脚本搜索请求模型"""
    query: Optional[str] = Field(None, description="搜索关键词")
    script_format: Optional[ScriptFormat] = Field(None, description="脚本格式过滤")
    script_type: Optional[ScriptType] = Field(None, description="脚本类型过滤")
    tags: List[str] = Field(default_factory=list, description="标签过滤")
    category: Optional[str] = Field(None, description="分类过滤")
    date_from: Optional[str] = Field(None, description="创建时间起始")
    date_to: Optional[str] = Field(None, description="创建时间结束")
    limit: int = Field(20, ge=1, le=100, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")


class ScriptSearchResponse(BaseModel):
    """脚本搜索响应模型"""
    scripts: List[TestScript] = Field(default_factory=list, description="脚本列表")
    total_count: int = Field(0, description="总数量")
    has_more: bool = Field(False, description="是否有更多")


class BatchExecutionRequest(BaseModel):
    """批量执行请求模型"""
    script_ids: List[str] = Field(..., description="要执行的脚本ID列表")
    execution_config: Optional[Dict[str, Any]] = Field(None, description="执行配置")
    parallel: bool = Field(False, description="是否并行执行")
    max_concurrent: int = Field(3, ge=1, le=10, description="最大并发数")
    continue_on_error: bool = Field(True, description="出错时是否继续")


class BatchExecutionResponse(BaseModel):
    """批量执行响应模型"""
    batch_id: str = Field(..., description="批次ID")
    script_count: int = Field(..., description="脚本数量")
    execution_ids: List[str] = Field(default_factory=list, description="执行ID列表")
    status: str = Field("started", description="批次状态")
    message: str = Field(..., description="响应消息")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ScriptStatistics(BaseModel):
    """脚本统计模型"""
    total_scripts: int = Field(0, description="总脚本数")
    yaml_scripts: int = Field(0, description="YAML脚本数")
    playwright_scripts: int = Field(0, description="Playwright脚本数")
    total_executions: int = Field(0, description="总执行次数")
    successful_executions: int = Field(0, description="成功执行次数")
    failed_executions: int = Field(0, description="失败执行次数")
    success_rate: float = Field(0.0, description="成功率")
    average_execution_time: float = Field(0.0, description="平均执行时间")
    most_used_scripts: List[Dict[str, Any]] = Field(default_factory=list, description="最常用脚本")
    recent_scripts: List[Dict[str, Any]] = Field(default_factory=list, description="最近创建脚本")

"""
UI自动化测试相关的数据模型和枚举
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class TestStatus(str, Enum):
    """测试状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class ExecutionStatus(str, Enum):
    """执行状态枚举"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ERROR = "error"


class PlatformType(str, Enum):
    """平台类型枚举"""
    WEB = "web"
    ANDROID = "android"
    IOS = "ios"
    DESKTOP = "desktop"


class AnalysisType(str, Enum):
    """分析类型枚举"""
    IMAGE_ANALYSIS = "image_analysis"
    URL_ANALYSIS = "url_analysis"
    MIXED_ANALYSIS = "mixed_analysis"
    MANUAL_CREATION = "manual_creation"


class UIElement(BaseModel):
    """UI元素模型"""
    id: str = Field(..., description="元素ID")
    name: str = Field(..., description="元素名称")
    element_type: str = Field(..., description="元素类型")
    description: str = Field(..., description="元素描述")
    selector: Optional[str] = Field(None, description="元素选择器")
    position: Optional[Dict[str, Any]] = Field(None, description="元素位置")
    confidence_score: float = Field(0.0, description="置信度分数")
    interaction_hint: Optional[str] = Field(None, description="交互提示")


class TestStep(BaseModel):
    """测试步骤模型"""
    step_id: str = Field(..., description="步骤ID")
    action: str = Field(..., description="动作类型")
    target: Optional[str] = Field(None, description="目标元素")
    value: Optional[str] = Field(None, description="输入值")
    description: str = Field(..., description="步骤描述")
    expected_result: Optional[str] = Field(None, description="预期结果")
    timeout: Optional[int] = Field(None, description="超时时间(秒)")


class TestScenario(BaseModel):
    """测试场景模型"""
    scenario_id: str = Field(..., description="场景ID")
    name: str = Field(..., description="场景名称")
    description: str = Field(..., description="场景描述")
    steps: List[TestStep] = Field(default_factory=list, description="测试步骤")
    priority: int = Field(1, ge=1, le=5, description="优先级")
    tags: List[str] = Field(default_factory=list, description="标签")


class PageAnalysis(BaseModel):
    """页面分析结果模型"""
    page_title: Optional[str] = Field(None, description="页面标题")
    page_type: str = Field(..., description="页面类型")
    page_url: Optional[str] = Field(None, description="页面URL")
    main_content: str = Field(..., description="主要内容")
    ui_elements: List[UIElement] = Field(default_factory=list, description="UI元素列表")
    user_flows: List[str] = Field(default_factory=list, description="用户流程")
    test_scenarios: List[str] = Field(default_factory=list, description="测试场景")
    complexity_score: float = Field(0.0, description="复杂度分数")


class AnalysisResult(BaseModel):
    """分析结果模型"""
    analysis_id: str = Field(..., description="分析ID")
    analysis_type: AnalysisType = Field(..., description="分析类型")
    platform_type: PlatformType = Field(..., description="平台类型")
    page_analysis: PageAnalysis = Field(..., description="页面分析结果")
    confidence_score: float = Field(0.0, description="整体置信度")
    processing_time: float = Field(0.0, description="处理时间(秒)")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ExecutionConfig(BaseModel):
    """执行配置模型"""
    headed: bool = Field(False, description="是否显示浏览器界面")
    keep_window: bool = Field(False, description="执行完成后是否保持窗口")
    debug_mode: bool = Field(False, description="是否启用调试模式")
    timeout: Optional[int] = Field(None, description="超时时间(秒)")
    viewport_width: int = Field(1280, description="视口宽度")
    viewport_height: int = Field(960, description="视口高度")
    environment_variables: Dict[str, Any] = Field(default_factory=dict, description="环境变量")


class ExecutionResult(BaseModel):
    """执行结果模型"""
    execution_id: str = Field(..., description="执行ID")
    status: ExecutionStatus = Field(..., description="执行状态")
    start_time: str = Field(..., description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")
    duration: Optional[float] = Field(None, description="执行时长(秒)")
    test_results: List[Dict[str, Any]] = Field(default_factory=list, description="测试结果")
    logs: List[str] = Field(default_factory=list, description="执行日志")
    screenshots: List[str] = Field(default_factory=list, description="截图路径")
    error_message: Optional[str] = Field(None, description="错误信息")
    artifacts: Dict[str, str] = Field(default_factory=dict, description="产物文件")


class TestReport(BaseModel):
    """测试报告模型"""
    report_id: str = Field(..., description="报告ID")
    execution_id: str = Field(..., description="执行ID")
    script_id: Optional[str] = Field(None, description="脚本ID")
    report_type: str = Field("execution", description="报告类型")
    summary: Dict[str, Any] = Field(default_factory=dict, description="执行摘要")
    detailed_results: List[Dict[str, Any]] = Field(default_factory=list, description="详细结果")
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="性能指标")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    file_path: Optional[str] = Field(None, description="报告文件路径")

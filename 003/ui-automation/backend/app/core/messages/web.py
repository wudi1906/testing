"""
UI自动化测试系统 - Web模块消息类型
定义Web平台智能体间通信的消息结构
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

from .base import BaseMessage


# ============ Web模块枚举类型 ============

class AnalysisType(str, Enum):
    """分析类型枚举"""
    IMAGE = "image"
    URL = "url"
    TEXT = "text"
    MIXED = "mixed"


# ============ Web模块基础数据模型 ============

class UIElement(BaseModel):
    """Web UI元素信息"""
    element_type: str = Field(..., description="元素类型")
    description: str = Field(..., description="元素描述")
    location: Optional[str] = Field(None, description="元素位置")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="元素属性")
    selector: Optional[str] = Field(None, description="CSS选择器或XPath")
    confidence_score: float = Field(default=0.0, description="AI识别置信度")


class TestAction(BaseModel):
    """Web测试步骤"""
    step_number: int = Field(..., description="步骤序号")
    action: str = Field(..., description="操作类型")
    target: str = Field(..., description="目标元素")
    description: str = Field(..., description="步骤描述")
    expected_result: Optional[str] = Field(None, description="预期结果")
    selector: Optional[str] = Field(None, description="元素选择器")
    input_value: Optional[str] = Field(None, description="输入值")


class PageAnalysis(BaseModel):
    """Web图片分析结果"""
    page_title: Optional[str] = Field(None, description="页面标题")
    page_type: str = Field(default="unknown", description="页面类型")
    main_content: str = Field(default="", description="主要内容描述")
    ui_elements: List[str] = Field(default_factory=list, description="识别的UI元素")
    user_flows: List[str] = Field(default_factory=list, description="用户流程")
    test_scenarios: List[str] = Field(default_factory=list, description="测试场景")
    test_steps: List[TestAction] = Field(default_factory=list, description="测试步骤")
    analysis_summary: str = Field(..., description="分析总结")
    confidence_score: float = Field(default=0.0, description="置信度分数")


class WebGeneratedScript(BaseModel):
    """Web生成的脚本"""
    format: str = Field(..., description="脚本格式: yaml, playwright")
    content: str = Field(..., description="脚本内容")
    file_path: Optional[str] = Field(None, description="文件路径")
    estimated_duration: Optional[str] = Field(None, description="预估执行时间")
    script_type: str = Field(default="automation", description="脚本类型")


# ============ Web智能体消息类型 ============

class WebMultimodalAnalysisRequest(BaseMessage):
    """Web多模态分析请求消息（统一的图像和多模态分析请求）"""
    session_id: str = Field(..., description="会话ID")
    analysis_type: AnalysisType = Field(default=AnalysisType.IMAGE, description="分析类型")

    # 图像输入选项（三选一）
    image_data: Optional[str] = Field(None, description="Base64编码的图片数据")
    image_url: Optional[str] = Field(None, description="图片URL")
    image_path: Optional[str] = Field(None, description="图片文件路径")

    # URL分析选项
    web_url: Optional[str] = Field(None, description="网页URL")
    target_url: Optional[str] = Field(None, description="目标网页URL")

    # 分析配置
    test_description: str = Field(..., description="测试需求描述")
    additional_context: Optional[str] = Field(None, description="额外上下文信息")
    generate_formats: List[str] = Field(default=["yaml"], description="生成格式列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "uuid-string",
                "image_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                "test_description": "测试用户登录功能",
                "additional_context": "需要验证表单验证和错误提示",
                "generate_formats": ["yaml", "playwright"],
                "target_url": "https://example.com/login"
            }
        }


class WebMultimodalAnalysisResponse(BaseMessage):
    """Web多模态分析响应消息"""
    session_id: str = Field(..., description="会话ID")
    analysis_id: str = Field(..., description="分析ID")
    analysis_type: AnalysisType = Field(..., description="分析类型")
    page_analysis: PageAnalysis = Field(..., description="页面分析结果")
    generated_scripts: List[WebGeneratedScript] = Field(default_factory=list, description="生成的脚本")
    confidence_score: float = Field(default=0.0, description="置信度分数")
    status: str = Field(..., description="处理状态")
    message: str = Field(..., description="响应消息")
    processing_time: float = Field(default=0.0, description="处理时间（秒）")


class WebUIAnalysisMessage(BaseMessage):
    """Web UI分析消息"""
    session_id: str = Field(..., description="会话ID")
    requirement_id: str = Field(..., description="需求ID")
    image_data: str = Field(..., description="图片数据")
    test_description: str = Field(..., description="测试描述")
    analysis_context: Dict[str, Any] = Field(default_factory=dict, description="分析上下文")


class WebYAMLGenerationMessage(BaseMessage):
    """Web YAML生成消息"""
    session_id: str = Field(..., description="会话ID")
    requirement_id: str = Field(..., description="需求ID")
    analysis_result: PageAnalysis = Field(..., description="分析结果")
    test_description: str = Field(..., description="测试描述")
    target_url: Optional[str] = Field(None, description="目标URL")
    generation_config: Dict[str, Any] = Field(default_factory=dict, description="生成配置")


class WebPlaywrightGenerationMessage(BaseMessage):
    """Web Playwright生成消息"""
    session_id: str = Field(..., description="会话ID")
    requirement_id: str = Field(..., description="需求ID")
    analysis_result: PageAnalysis = Field(..., description="分析结果")
    test_description: str = Field(..., description="测试描述")
    target_url: Optional[str] = Field(None, description="目标URL")
    generation_config: Dict[str, Any] = Field(default_factory=dict, description="生成配置")


class WebScriptExecutionMessage(BaseMessage):
    """Web脚本执行消息"""
    session_id: str = Field(..., description="会话ID")
    execution_id: str = Field(..., description="执行ID")
    script_type: str = Field(..., description="脚本类型: yaml, playwright")
    script_content: str = Field(..., description="脚本内容")
    execution_config: Dict[str, Any] = Field(default_factory=dict, description="执行配置")
    environment_config: Dict[str, Any] = Field(default_factory=dict, description="环境配置")


class WebURLAnalysisRequest(BaseMessage):
    """Web URL分析请求消息"""
    session_id: str = Field(..., description="会话ID")
    url: str = Field(..., description="要分析的网页URL")
    test_description: str = Field(..., description="测试需求描述")
    additional_context: Optional[str] = Field(None, description="额外上下文")
    wait_for_load: bool = Field(default=True, description="是否等待页面完全加载")
    viewport_width: int = Field(default=1280, description="视口宽度")
    viewport_height: int = Field(default=960, description="视口高度")
    generate_formats: List[str] = Field(default=["yaml"], description="生成格式列表")


class WebCrawlAnalysisRequest(BaseMessage):
    """Web爬虫分析请求消息"""
    session_id: str = Field(..., description="会话ID")
    homepage_url: str = Field(..., description="主页URL")
    crawl_mode: str = Field(default="single", description="爬取模式: single, multi")
    max_pages: int = Field(default=10, description="最大爬取页面数")
    test_description: str = Field(..., description="测试需求描述")
    additional_context: Optional[str] = Field(None, description="额外上下文")
    generate_formats: List[str] = Field(default=["yaml"], description="生成格式列表")


# ============ Web执行请求消息类型 ============

class YAMLExecutionConfig(BaseMessage):
    """YAML执行配置"""
    headed: bool = Field(False, description="是否在有界面模式下运行")
    keep_window: bool = Field(False, description="执行完成后是否保持浏览器窗口打开")
    timeout: Optional[int] = Field(None, description="执行超时时间（秒）")
    output_dir: Optional[str] = Field(None, description="输出目录路径")
    environment_variables: Dict[str, str] = Field(default_factory=dict, description="环境变量")
    env_file_path: Optional[str] = Field(None, description=".env文件路径")
    parallel: bool = Field(False, description="是否并行执行多个文件")
    retry_count: int = Field(0, description="失败重试次数")
    retry_interval: int = Field(1000, description="重试间隔（毫秒）")


class YAMLExecutionRequest(BaseMessage):
    """YAML执行请求消息"""
    session_id: str = Field(..., description="会话ID")
    yaml_content: str = Field(..., description="YAML脚本内容")
    execution_config: Optional[YAMLExecutionConfig] = Field(None, description="执行配置")
    legacy_config: Optional[Dict[str, Any]] = Field(None, description="旧版配置格式")


class PlaywrightExecutionConfig(BaseMessage):
    """Playwright执行配置"""
    headed: bool = Field(False, description="是否在有界面模式下运行")
    timeout: int = Field(90, description="测试超时时间（秒）")
    viewport_width: int = Field(1280, description="视口宽度")
    viewport_height: int = Field(960, description="视口高度")
    network_idle_timeout: int = Field(2000, description="网络空闲等待超时时间（毫秒）")
    base_url: Optional[str] = Field(None, description="测试基础URL")
    environment_variables: Dict[str, str] = Field(default_factory=dict, description="环境变量")
    generate_report: bool = Field(True, description="是否生成测试报告")
    screenshot_on_failure: bool = Field(True, description="失败时是否截图")
    video_on_failure: bool = Field(True, description="失败时是否录制视频")
    debug_mode: bool = Field(False, description="是否启用调试模式")
    keep_files: bool = Field(False, description="是否保留临时文件")
    browser_type: str = Field("chromium", description="浏览器类型：chromium, firefox, webkit")
    device_name: Optional[str] = Field(None, description="设备名称（移动端测试）")


class PlaywrightExecutionRequest(BaseMessage):
    """Playwright执行请求消息"""
    session_id: str = Field(..., description="会话ID")
    script_id: Optional[str] = Field(None, description="脚本ID（用于报告关联）")
    script_name: Optional[str] = Field(None, description="要执行的脚本文件名（在e2e目录下）")
    test_content: Optional[str] = Field(None, description="测试脚本内容（JavaScript/TypeScript）")
    execution_config: Optional[PlaywrightExecutionConfig] = Field(None, description="执行配置")
    test_type: str = Field("javascript", description="测试类型：javascript, yaml")

    def model_post_init(self, __context) -> None:
        """验证script_name和test_content至少有一个"""
        if not self.script_name and not self.test_content:
            raise ValueError("script_name和test_content至少需要提供一个")


class ScriptExecutionRequest(BaseMessage):
    """脚本执行请求消息（支持多脚本批量执行）"""
    session_id: str = Field(..., description="会话ID")
    scripts: List[Dict[str, Any]] = Field(..., description="要执行的脚本列表")
    execution_config: Optional[Dict[str, Any]] = Field(None, description="全局执行配置")
    parallel_execution: bool = Field(False, description="是否并行执行")
    stop_on_failure: bool = Field(True, description="遇到失败时是否停止执行")


class ScriptExecutionStatus(BaseMessage):
    """脚本执行状态消息"""
    session_id: str = Field(..., description="会话ID")
    script_name: str = Field(..., description="脚本名称")
    status: str = Field(..., description="执行状态：pending, running, completed, failed")
    start_time: Optional[str] = Field(None, description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")
    duration: Optional[float] = Field(None, description="执行时长（秒）")
    error_message: Optional[str] = Field(None, description="错误信息")
    report_path: Optional[str] = Field(None, description="报告路径")


# ============ 页面分析存储消息类型 ============

class PageAnalysisStorageRequest(BaseMessage):
    """页面分析结果存储请求消息"""
    session_id: str = Field(..., description="会话ID")
    analysis_id: str = Field(..., description="分析ID")
    page_name: str = Field(..., description="页面名称")
    page_url: Optional[str] = Field(None, description="页面URL")
    page_type: str = Field(default="unknown", description="页面类型")
    page_description: str = Field(..., description="页面描述")
    analysis_result: PageAnalysis = Field(..., description="页面分析结果")
    confidence_score: float = Field(default=0.0, description="置信度分数")
    analysis_metadata: Dict[str, Any] = Field(default_factory=dict, description="分析元数据")


class PageAnalysisStorageResponse(BaseMessage):
    """页面分析结果存储响应消息"""
    session_id: str = Field(..., description="会话ID")
    analysis_id: str = Field(..., description="分析ID")
    storage_id: str = Field(..., description="存储记录ID")
    status: str = Field(..., description="存储状态: success, failed")
    message: str = Field(..., description="响应消息")
    stored_elements_count: int = Field(default=0, description="存储的元素数量")


# ============ 测试用例元素解析消息类型 ============

class TestCaseElementParseRequest(BaseMessage):
    """测试用例元素解析请求消息"""
    session_id: str = Field(..., description="会话ID")
    test_case_content: str = Field(..., description="用户编写的测试用例内容")
    test_description: Optional[str] = Field(None, description="测试描述")
    target_format: str = Field(default="yaml", description="目标脚本格式: yaml, playwright")
    additional_context: Optional[str] = Field(None, description="额外上下文信息")
    page_filter: Optional[List[str]] = Field(None, description="页面过滤条件")


class ParsedPageElement(BaseModel):
    """解析后的页面元素信息"""
    element_id: str = Field(..., description="元素ID")
    element_name: str = Field(..., description="元素名称")
    element_type: str = Field(..., description="元素类型")
    element_description: str = Field(..., description="元素描述")
    selector: Optional[str] = Field(None, description="元素选择器")
    position: Optional[Dict[str, Any]] = Field(None, description="元素位置信息")
    visual_features: Optional[Dict[str, Any]] = Field(None, description="视觉特征")
    functionality: Optional[str] = Field(None, description="功能描述")
    interaction_state: Optional[str] = Field(None, description="交互状态")
    confidence_score: float = Field(default=0.0, description="置信度分数")
    is_testable: bool = Field(default=True, description="是否可测试")
    test_priority: str = Field(default="medium", description="测试优先级")


class ParsedPageInfo(BaseModel):
    """解析后的页面信息"""
    page_id: str = Field(..., description="页面ID")
    page_name: str = Field(..., description="页面名称")
    page_description: str = Field(..., description="页面描述")
    page_type: str = Field(..., description="页面类型")
    page_url: Optional[str] = Field(None, description="页面URL")
    confidence_score: float = Field(default=0.0, description="置信度分数")
    elements: List[ParsedPageElement] = Field(default_factory=list, description="页面元素列表")
    element_categories: Dict[str, List[str]] = Field(default_factory=dict, description="元素分类")


class TestCaseElementParseResponse(BaseMessage):
    """测试用例元素解析响应消息"""
    session_id: str = Field(..., description="会话ID")
    parse_id: str = Field(..., description="解析ID")
    test_case_content: str = Field(..., description="原始测试用例内容")
    parsed_pages: List[ParsedPageInfo] = Field(default_factory=list, description="解析的页面信息")
    element_summary: Dict[str, Any] = Field(default_factory=dict, description="元素汇总信息")
    analysis_insights: List[str] = Field(default_factory=list, description="分析洞察")
    recommendations: List[str] = Field(default_factory=list, description="建议")
    confidence_score: float = Field(default=0.0, description="整体置信度")
    processing_time: float = Field(default=0.0, description="处理时间（秒）")
    status: str = Field(..., description="处理状态")
    message: str = Field(..., description="响应消息")


# ============ 统一的图像分析消息类型 ============
# 注意：WebImageAnalysisRequest 和 WebImageAnalysisResponse 已合并到 WebMultimodalAnalysisRequest 和 WebMultimodalAnalysisResponse
# 为了向后兼容，创建别名

# 别名定义，指向统一的多模态分析类型
WebImageAnalysisRequest = WebMultimodalAnalysisRequest
WebImageAnalysisResponse = WebMultimodalAnalysisResponse




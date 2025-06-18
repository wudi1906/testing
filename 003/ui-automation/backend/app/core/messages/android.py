"""
UI自动化测试系统 - Android模块消息类型
定义Android平台智能体间通信的消息结构
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from .base import BaseMessage


# ============ Android模块基础数据模型 ============

class AndroidUIElement(BaseModel):
    """Android UI元素信息"""
    element_type: str = Field(..., description="元素类型: button, edittext, textview等")
    description: str = Field(..., description="元素描述")
    resource_id: Optional[str] = Field(None, description="资源ID")
    text: Optional[str] = Field(None, description="元素文本")
    content_desc: Optional[str] = Field(None, description="内容描述")
    class_name: Optional[str] = Field(None, description="类名")
    package_name: Optional[str] = Field(None, description="包名")
    bounds: Optional[Dict[str, int]] = Field(None, description="元素边界坐标")
    clickable: bool = Field(default=False, description="是否可点击")
    scrollable: bool = Field(default=False, description="是否可滚动")
    enabled: bool = Field(default=True, description="是否启用")
    confidence_score: float = Field(default=0.0, description="AI识别置信度")


class AndroidTestStep(BaseModel):
    """Android测试步骤"""
    step_number: int = Field(..., description="步骤序号")
    action: str = Field(..., description="操作类型: click, input, swipe, scroll等")
    target: str = Field(..., description="目标元素描述")
    description: str = Field(..., description="步骤描述")
    expected_result: Optional[str] = Field(None, description="预期结果")
    selector: Optional[str] = Field(None, description="元素选择器")
    input_value: Optional[str] = Field(None, description="输入值")
    coordinates: Optional[Dict[str, int]] = Field(None, description="坐标位置")
    swipe_direction: Optional[str] = Field(None, description="滑动方向")


class AndroidAnalysisResult(BaseModel):
    """Android界面分析结果"""
    ui_elements: List[AndroidUIElement] = Field(default_factory=list, description="识别的UI元素")
    test_scenarios: List[str] = Field(default_factory=list, description="测试场景")
    test_steps: List[AndroidTestStep] = Field(default_factory=list, description="测试步骤")
    analysis_summary: str = Field(..., description="分析总结")
    confidence_score: float = Field(default=0.0, description="置信度分数")
    activity_name: Optional[str] = Field(None, description="当前Activity名称")
    package_name: Optional[str] = Field(None, description="应用包名")
    screen_resolution: Optional[Dict[str, int]] = Field(None, description="屏幕分辨率")


class AndroidGeneratedScript(BaseModel):
    """Android生成的脚本"""
    format: str = Field(..., description="脚本格式: appium, uiautomator2, yaml")
    content: str = Field(..., description="脚本内容")
    file_path: Optional[str] = Field(None, description="文件路径")
    estimated_duration: Optional[str] = Field(None, description="预估执行时间")
    script_type: str = Field(default="automation", description="脚本类型")
    framework: str = Field(default="appium", description="测试框架")


# ============ Android智能体消息类型 ============

class AndroidAnalysisRequest(BaseMessage):
    """Android界面分析请求消息"""
    session_id: str = Field(..., description="会话ID")
    screenshot_data: str = Field(..., description="Base64编码的截图数据")
    ui_hierarchy: Optional[str] = Field(None, description="UI层次结构XML")
    test_description: str = Field(..., description="测试需求描述")
    additional_context: Optional[str] = Field(None, description="额外上下文信息")
    generate_formats: List[str] = Field(default=["appium"], description="生成格式列表")
    device_info: Optional[Dict[str, Any]] = Field(None, description="设备信息")
    app_package: Optional[str] = Field(None, description="应用包名")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "uuid-string",
                "screenshot_data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                "test_description": "测试Android应用登录功能",
                "additional_context": "需要验证输入验证和错误提示",
                "generate_formats": ["appium", "uiautomator2"],
                "device_info": {
                    "platform_name": "Android",
                    "platform_version": "11",
                    "device_name": "Pixel_4"
                },
                "app_package": "com.example.app"
            }
        }


class AndroidAnalysisResponse(BaseMessage):
    """Android界面分析响应消息"""
    session_id: str = Field(..., description="会话ID")
    analysis_result: AndroidAnalysisResult = Field(..., description="分析结果")
    generated_scripts: List[AndroidGeneratedScript] = Field(default_factory=list, description="生成的脚本")
    status: str = Field(..., description="处理状态")
    message: str = Field(..., description="响应消息")
    processing_time: float = Field(default=0.0, description="处理时间（秒）")


class AndroidUIAnalysisMessage(BaseMessage):
    """Android UI分析消息"""
    session_id: str = Field(..., description="会话ID")
    requirement_id: str = Field(..., description="需求ID")
    screenshot_data: str = Field(..., description="截图数据")
    ui_hierarchy: Optional[str] = Field(None, description="UI层次结构")
    test_description: str = Field(..., description="测试描述")
    analysis_context: Dict[str, Any] = Field(default_factory=dict, description="分析上下文")


class AndroidTestGenerationMessage(BaseMessage):
    """Android测试生成消息"""
    session_id: str = Field(..., description="会话ID")
    requirement_id: str = Field(..., description="需求ID")
    analysis_result: AndroidAnalysisResult = Field(..., description="分析结果")
    test_description: str = Field(..., description="测试描述")
    target_app: Optional[str] = Field(None, description="目标应用包名")
    generation_config: Dict[str, Any] = Field(default_factory=dict, description="生成配置")


class AndroidScriptExecutionMessage(BaseMessage):
    """Android脚本执行消息"""
    session_id: str = Field(..., description="会话ID")
    execution_id: str = Field(..., description="执行ID")
    script_type: str = Field(..., description="脚本类型: appium, uiautomator2")
    script_content: str = Field(..., description="脚本内容")
    execution_config: Dict[str, Any] = Field(default_factory=dict, description="执行配置")
    device_config: Dict[str, Any] = Field(default_factory=dict, description="设备配置")


class AndroidDeviceConnectionMessage(BaseMessage):
    """Android设备连接消息"""
    session_id: str = Field(..., description="会话ID")
    device_id: str = Field(..., description="设备ID")
    connection_type: str = Field(default="adb", description="连接类型: adb, wifi")
    device_capabilities: Dict[str, Any] = Field(default_factory=dict, description="设备能力")
    app_package: Optional[str] = Field(None, description="目标应用包名")
    app_activity: Optional[str] = Field(None, description="目标Activity")


class AndroidAppInstallMessage(BaseMessage):
    """Android应用安装消息"""
    session_id: str = Field(..., description="会话ID")
    device_id: str = Field(..., description="设备ID")
    apk_path: str = Field(..., description="APK文件路径")
    package_name: str = Field(..., description="应用包名")
    install_options: Dict[str, Any] = Field(default_factory=dict, description="安装选项")


class AndroidPerformanceTestMessage(BaseMessage):
    """Android性能测试消息"""
    session_id: str = Field(..., description="会话ID")
    device_id: str = Field(..., description="设备ID")
    package_name: str = Field(..., description="应用包名")
    test_duration: int = Field(default=60, description="测试持续时间（秒）")
    metrics: List[str] = Field(default=["cpu", "memory", "battery"], description="监控指标")
    test_scenarios: List[str] = Field(default_factory=list, description="测试场景")

"""
基础消息类型定义
"""
from datetime import datetime
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """基础消息类"""
    session_id: str = Field(..., description="会话ID")
    message_id: str = Field(default_factory=lambda: f"msg_{datetime.now().timestamp()}", description="消息ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    source_agent: str = Field("", description="源智能体")
    target_agent: str = Field("", description="目标智能体")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class StreamMessage(BaseModel):
    """流式消息类"""
    content: str = Field(..., description="消息内容")
    message_type: str = Field("info", description="消息类型")
    is_final: bool = Field(False, description="是否为最终消息")
    result: Optional[Dict[str, Any]] = Field(None, description="结果数据")
    error: Optional[str] = Field(None, description="错误信息")
    region: str = Field("process", description="消息区域")
    agent_name: str = Field("", description="智能体名称")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class ErrorMessage(BaseMessage):
    """错误消息"""
    error_code: str = Field(..., description="错误代码")
    error_message: str = Field(..., description="错误信息")
    error_details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    stack_trace: Optional[str] = Field(None, description="堆栈跟踪")


class SuccessMessage(BaseMessage):
    """成功消息"""
    result: Dict[str, Any] = Field(..., description="结果数据")
    message: str = Field("", description="成功信息")


class ProgressMessage(BaseMessage):
    """进度消息"""
    current_step: int = Field(..., description="当前步骤")
    total_steps: int = Field(..., description="总步骤数")
    step_description: str = Field("", description="步骤描述")
    progress_percentage: float = Field(0.0, description="进度百分比")
    estimated_remaining_time: Optional[int] = Field(None, description="预估剩余时间(秒)")


class ValidationMessage(BaseMessage):
    """验证消息"""
    is_valid: bool = Field(..., description="是否有效")
    validation_errors: List[str] = Field(default_factory=list, description="验证错误列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")


class ConfigurationMessage(BaseMessage):
    """配置消息"""
    config_type: str = Field(..., description="配置类型")
    config_data: Dict[str, Any] = Field(..., description="配置数据")
    is_update: bool = Field(False, description="是否为更新操作")


class StatusMessage(BaseMessage):
    """状态消息"""
    status: str = Field(..., description="状态")
    status_details: Optional[Dict[str, Any]] = Field(None, description="状态详情")
    previous_status: Optional[str] = Field(None, description="前一个状态")
    status_changed_at: datetime = Field(default_factory=datetime.now, description="状态变更时间")


class MetricsMessage(BaseMessage):
    """指标消息"""
    metrics_type: str = Field(..., description="指标类型")
    metrics_data: Dict[str, Any] = Field(..., description="指标数据")
    collection_time: datetime = Field(default_factory=datetime.now, description="收集时间")
    tags: Dict[str, str] = Field(default_factory=dict, description="标签")


class NotificationMessage(BaseMessage):
    """通知消息"""
    notification_type: str = Field(..., description="通知类型")
    title: str = Field(..., description="通知标题")
    content: str = Field(..., description="通知内容")
    priority: str = Field("normal", description="优先级")
    recipients: List[str] = Field(default_factory=list, description="接收者列表")

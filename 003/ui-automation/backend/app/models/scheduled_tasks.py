"""
定时任务相关的Pydantic模型
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ScheduleType(str, Enum):
    """调度类型枚举"""
    CRON = "cron"
    INTERVAL = "interval"
    ONCE = "once"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    EXPIRED = "expired"


class ExecutionStatus(str, Enum):
    """执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class TriggerType(str, Enum):
    """触发类型枚举"""
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    RETRY = "retry"


class ScheduledTaskCreate(BaseModel):
    """创建定时任务请求模型"""
    script_id: str = Field(..., description="脚本ID")
    project_id: Optional[str] = Field(None, description="项目ID")
    name: str = Field(..., description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    
    # 调度配置
    schedule_type: ScheduleType = Field(..., description="调度类型")
    cron_expression: Optional[str] = Field(None, description="Cron表达式")
    interval_seconds: Optional[int] = Field(None, description="间隔秒数")
    scheduled_time: Optional[datetime] = Field(None, description="一次性任务执行时间")
    
    # 执行配置
    execution_config: Optional[Dict[str, Any]] = Field(None, description="执行配置")
    environment_variables: Optional[Dict[str, str]] = Field(None, description="环境变量")
    timeout_seconds: int = Field(300, description="超时时间（秒）")
    max_retries: int = Field(0, description="最大重试次数")
    retry_interval_seconds: int = Field(60, description="重试间隔（秒）")
    
    # 时间范围
    start_time: Optional[datetime] = Field(None, description="任务开始时间")
    end_time: Optional[datetime] = Field(None, description="任务结束时间")
    
    # 通知配置
    notification_config: Optional[Dict[str, Any]] = Field(None, description="通知配置")
    notify_on_success: bool = Field(False, description="成功时通知")
    notify_on_failure: bool = Field(True, description="失败时通知")


class ScheduledTaskUpdate(BaseModel):
    """更新定时任务请求模型"""
    name: Optional[str] = Field(None, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    
    # 调度配置
    schedule_type: Optional[ScheduleType] = Field(None, description="调度类型")
    cron_expression: Optional[str] = Field(None, description="Cron表达式")
    interval_seconds: Optional[int] = Field(None, description="间隔秒数")
    scheduled_time: Optional[datetime] = Field(None, description="一次性任务执行时间")
    
    # 执行配置
    execution_config: Optional[Dict[str, Any]] = Field(None, description="执行配置")
    environment_variables: Optional[Dict[str, str]] = Field(None, description="环境变量")
    timeout_seconds: Optional[int] = Field(None, description="超时时间（秒）")
    max_retries: Optional[int] = Field(None, description="最大重试次数")
    retry_interval_seconds: Optional[int] = Field(None, description="重试间隔（秒）")
    
    # 状态
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    
    # 时间范围
    start_time: Optional[datetime] = Field(None, description="任务开始时间")
    end_time: Optional[datetime] = Field(None, description="任务结束时间")
    
    # 通知配置
    notification_config: Optional[Dict[str, Any]] = Field(None, description="通知配置")
    notify_on_success: Optional[bool] = Field(None, description="成功时通知")
    notify_on_failure: Optional[bool] = Field(None, description="失败时通知")


class ScheduledTask(BaseModel):
    """定时任务响应模型"""
    id: str
    script_id: str
    project_id: Optional[str]
    created_by: Optional[str]
    
    # 基本信息
    name: str
    description: Optional[str]
    
    # 调度配置
    schedule_type: ScheduleType
    cron_expression: Optional[str]
    interval_seconds: Optional[int]
    scheduled_time: Optional[datetime]
    
    # 执行配置
    execution_config: Optional[Dict[str, Any]]
    environment_variables: Optional[Dict[str, str]]
    timeout_seconds: int
    max_retries: int
    retry_interval_seconds: int
    
    # 状态信息
    status: TaskStatus
    is_enabled: bool
    
    # 时间范围
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    
    # 执行统计
    total_executions: int
    successful_executions: int
    failed_executions: int
    last_execution_time: Optional[datetime]
    last_execution_status: Optional[ExecutionStatus]
    next_execution_time: Optional[datetime]
    
    # 通知配置
    notification_config: Optional[Dict[str, Any]]
    notify_on_success: bool
    notify_on_failure: bool
    
    # 时间戳
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaskExecution(BaseModel):
    """任务执行记录响应模型"""
    id: str
    task_id: str
    script_id: str
    session_id: Optional[str]
    execution_id: Optional[str]
    
    # 执行信息
    trigger_type: TriggerType
    execution_config: Optional[Dict[str, Any]]
    environment_variables: Optional[Dict[str, str]]
    
    # 状态和结果
    status: ExecutionStatus
    
    # 时间信息
    scheduled_time: Optional[datetime]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: Optional[int]
    
    # 结果信息
    exit_code: Optional[int]
    error_message: Optional[str]
    output_log: Optional[str]
    
    # 重试信息
    retry_count: int
    is_retry: bool
    parent_execution_id: Optional[str]
    
    # 性能指标
    performance_metrics: Optional[Dict[str, Any]]
    
    # 报告信息
    report_path: Optional[str]
    report_url: Optional[str]
    
    # 时间戳
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TaskSearchRequest(BaseModel):
    """任务搜索请求模型"""
    query: Optional[str] = Field(None, description="搜索关键词")
    script_id: Optional[str] = Field(None, description="脚本ID")
    project_id: Optional[str] = Field(None, description="项目ID")
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    schedule_type: Optional[ScheduleType] = Field(None, description="调度类型")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    created_by: Optional[str] = Field(None, description="创建者")
    
    # 分页参数
    limit: int = Field(20, ge=1, le=100, description="每页数量")
    offset: int = Field(0, ge=0, description="偏移量")
    
    # 排序参数
    sort_by: str = Field("created_at", description="排序字段")
    sort_order: str = Field("desc", description="排序方向")


class TaskSearchResponse(BaseModel):
    """任务搜索响应模型"""
    tasks: List[ScheduledTask]
    total: int
    limit: int
    offset: int


class TaskStatistics(BaseModel):
    """任务统计信息模型"""
    total_tasks: int
    active_tasks: int
    paused_tasks: int
    disabled_tasks: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    most_active_tasks: List[Dict[str, Any]]
    recent_executions: List[Dict[str, Any]]


class TaskExecutionRequest(BaseModel):
    """手动执行任务请求模型"""
    execution_config: Optional[Dict[str, Any]] = Field(None, description="执行配置")
    environment_variables: Optional[Dict[str, str]] = Field(None, description="环境变量")


class TaskExecutionResponse(BaseModel):
    """任务执行响应模型"""
    execution_id: str
    task_id: str
    script_id: str
    session_id: str
    status: str
    message: str
    sse_endpoint: str
    created_at: datetime

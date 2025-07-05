"""
定时任务相关数据库模型
"""
from sqlalchemy import (
    Column, String, Text, Enum, Integer, ForeignKey, Index, 
    DateTime, Boolean, JSON, CheckConstraint
)
from sqlalchemy.orm import relationship
from .base import BaseModel


class ScheduledTask(BaseModel):
    """定时任务表模型"""
    
    __tablename__ = 'scheduled_tasks'
    
    # 关联信息
    script_id = Column(String(36), ForeignKey('test_scripts.id', ondelete='CASCADE'), nullable=False)
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='CASCADE'))
    created_by = Column(String(36))  # 创建者ID
    
    # 任务基本信息
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # 调度配置
    schedule_type = Column(Enum('cron', 'interval', 'once'), nullable=False)
    cron_expression = Column(String(100))  # cron表达式，如 "0 9 * * 1-5"
    interval_seconds = Column(Integer)  # 间隔秒数
    scheduled_time = Column(DateTime)  # 一次性任务的执行时间
    
    # 执行配置
    execution_config = Column(JSON)  # 执行配置参数
    environment_variables = Column(JSON)  # 环境变量
    timeout_seconds = Column(Integer, default=300)  # 超时时间（秒）
    max_retries = Column(Integer, default=0)  # 最大重试次数
    retry_interval_seconds = Column(Integer, default=60)  # 重试间隔（秒）
    
    # 状态信息
    status = Column(Enum('active', 'paused', 'disabled', 'expired'), default='active')
    is_enabled = Column(Boolean, default=True)
    
    # 时间范围
    start_time = Column(DateTime)  # 任务开始时间
    end_time = Column(DateTime)  # 任务结束时间
    
    # 执行统计
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    last_execution_time = Column(DateTime)
    last_execution_status = Column(Enum('pending', 'running', 'completed', 'failed', 'timeout', 'cancelled'))
    next_execution_time = Column(DateTime)
    
    # 通知配置
    notification_config = Column(JSON)  # 通知配置
    notify_on_success = Column(Boolean, default=False)
    notify_on_failure = Column(Boolean, default=True)
    
    # 关系
    script = relationship("TestScript", back_populates="scheduled_tasks")
    project = relationship("Project", back_populates="scheduled_tasks")
    executions = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")
    
    # 约束和索引
    __table_args__ = (
        CheckConstraint('timeout_seconds > 0', name='ck_task_timeout_positive'),
        CheckConstraint('max_retries >= 0', name='ck_task_retries_non_negative'),
        CheckConstraint('retry_interval_seconds > 0', name='ck_task_retry_interval_positive'),
        Index('idx_scheduled_tasks_status', 'status'),
        Index('idx_scheduled_tasks_enabled', 'is_enabled'),
        Index('idx_scheduled_tasks_next_execution', 'next_execution_time'),
        Index('idx_scheduled_tasks_script_id', 'script_id'),
        Index('idx_scheduled_tasks_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ScheduledTask(id={self.id}, name={self.name}, status={self.status})>"


class TaskExecution(BaseModel):
    """任务执行记录表模型"""
    
    __tablename__ = 'task_executions'
    
    # 关联信息
    task_id = Column(String(36), ForeignKey('scheduled_tasks.id', ondelete='CASCADE'), nullable=False)
    script_id = Column(String(36), ForeignKey('test_scripts.id', ondelete='CASCADE'), nullable=False)
    session_id = Column(String(36))  # 执行会话ID
    execution_id = Column(String(36))  # 脚本执行ID
    
    # 执行信息
    trigger_type = Column(Enum('scheduled', 'manual', 'retry'), default='scheduled')
    execution_config = Column(JSON)  # 执行时的配置
    environment_variables = Column(JSON)  # 执行时的环境变量
    
    # 状态和结果
    status = Column(Enum('pending', 'running', 'completed', 'failed', 'timeout', 'cancelled'), default='pending')
    
    # 时间信息
    scheduled_time = Column(DateTime)  # 计划执行时间
    start_time = Column(DateTime)  # 实际开始时间
    end_time = Column(DateTime)  # 结束时间
    duration_seconds = Column(Integer)  # 执行时长（秒）
    
    # 结果信息
    exit_code = Column(Integer)
    error_message = Column(Text)
    output_log = Column(Text)  # 执行输出日志
    
    # 重试信息
    retry_count = Column(Integer, default=0)
    is_retry = Column(Boolean, default=False)
    parent_execution_id = Column(String(36))  # 原始执行记录ID（用于重试）
    
    # 性能指标
    performance_metrics = Column(JSON)
    
    # 报告信息
    report_path = Column(String(500))  # 测试报告路径
    report_url = Column(String(1000))  # 测试报告URL
    
    # 关系
    task = relationship("ScheduledTask", back_populates="executions")
    script = relationship("TestScript")
    
    # 约束和索引
    __table_args__ = (
        Index('idx_task_executions_task_id', 'task_id'),
        Index('idx_task_executions_status', 'status'),
        Index('idx_task_executions_scheduled_time', 'scheduled_time'),
        Index('idx_task_executions_start_time', 'start_time'),
        Index('idx_task_executions_session_id', 'session_id'),
    )
    
    def __repr__(self):
        return f"<TaskExecution(id={self.id}, task_id={self.task_id}, status={self.status})>"

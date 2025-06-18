"""
脚本执行相关数据库模型
包含脚本执行记录、执行工件、批量执行等模型
"""
from sqlalchemy import Column, String, Text, Enum, Integer, DateTime, ForeignKey, Index, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from .base import BaseModel


class ScriptExecution(BaseModel):
    """脚本执行记录表模型"""
    
    __tablename__ = 'script_executions'
    
    # 关联信息
    script_id = Column(String(36), ForeignKey('test_scripts.id', ondelete='CASCADE'), nullable=False)
    batch_id = Column(String(36), ForeignKey('batch_executions.id', ondelete='SET NULL'))
    
    # 执行标识
    execution_id = Column(String(100), nullable=False)  # 外部执行系统的ID
    
    # 执行状态
    status = Column(
        Enum('pending', 'running', 'completed', 'failed', 'cancelled'), 
        nullable=False, 
        default='pending'
    )
    
    # 执行配置
    execution_config = Column(JSON)  # 执行配置参数
    environment_info = Column(JSON)  # 执行环境信息
    
    # 时间信息
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    
    # 结果信息
    error_message = Column(Text)
    exit_code = Column(Integer)
    
    # 性能指标
    performance_metrics = Column(JSON)
    
    # 关系
    script = relationship("TestScript", back_populates="executions")
    batch = relationship("BatchExecution", back_populates="executions")
    artifacts = relationship("ExecutionArtifact", back_populates="execution", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_executions_script_id', 'script_id'),
        Index('idx_executions_status', 'status'),
        Index('idx_executions_start_time', 'start_time'),
        Index('idx_executions_execution_id', 'execution_id'),
        Index('idx_executions_batch_id', 'batch_id'),
    )
    
    def __repr__(self):
        return f"<ScriptExecution(id={self.id}, script_id={self.script_id}, status={self.status})>"


class ExecutionArtifact(BaseModel):
    """执行工件表模型"""
    
    __tablename__ = 'execution_artifacts'
    
    # 关联信息
    execution_id = Column(String(36), ForeignKey('script_executions.id', ondelete='CASCADE'), nullable=False)
    
    # 工件信息
    artifact_type = Column(
        Enum('screenshot', 'video', 'log', 'report', 'data', 'other'), 
        nullable=False
    )
    artifact_name = Column(String(255), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    
    # 工件描述
    description = Column(Text)
    artifact_metadata = Column(JSON)  # 重命名避免与SQLAlchemy的metadata冲突
    
    # 关系
    execution = relationship("ScriptExecution", back_populates="artifacts")
    
    # 索引
    __table_args__ = (
        Index('idx_artifacts_execution_id', 'execution_id'),
        Index('idx_artifacts_type', 'artifact_type'),
        Index('idx_artifacts_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ExecutionArtifact(id={self.id}, name={self.artifact_name}, type={self.artifact_type})>"


class BatchExecution(BaseModel):
    """批量执行表模型"""
    
    __tablename__ = 'batch_executions'
    
    # 批量执行信息
    batch_name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # 执行配置
    execution_config = Column(JSON)
    parallel_execution = Column(Enum('true', 'false'), default='false')
    max_concurrent = Column(Integer, default=1)
    continue_on_error = Column(Enum('true', 'false'), default='true')
    
    # 执行状态
    status = Column(
        Enum('pending', 'running', 'completed', 'failed', 'cancelled'), 
        nullable=False, 
        default='pending'
    )
    
    # 时间信息
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    
    # 统计信息
    total_scripts = Column(Integer, default=0)
    completed_scripts = Column(Integer, default=0)
    failed_scripts = Column(Integer, default=0)
    cancelled_scripts = Column(Integer, default=0)
    
    # 结果信息
    error_message = Column(Text)
    summary_report = Column(JSON)
    
    # 关系
    executions = relationship("ScriptExecution", back_populates="batch", cascade="all, delete-orphan")
    
    # 约束和索引
    __table_args__ = (
        CheckConstraint('max_concurrent > 0', name='ck_batch_max_concurrent'),
        CheckConstraint('total_scripts >= 0', name='ck_batch_total_scripts'),
        CheckConstraint('completed_scripts >= 0', name='ck_batch_completed_scripts'),
        CheckConstraint('failed_scripts >= 0', name='ck_batch_failed_scripts'),
        CheckConstraint('cancelled_scripts >= 0', name='ck_batch_cancelled_scripts'),
        Index('idx_batch_status', 'status'),
        Index('idx_batch_start_time', 'start_time'),
        Index('idx_batch_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<BatchExecution(id={self.id}, name={self.batch_name}, status={self.status})>"


class ExecutionLog(BaseModel):
    """执行日志表模型"""
    
    __tablename__ = 'execution_logs'
    
    # 关联信息
    execution_id = Column(String(36), ForeignKey('script_executions.id', ondelete='CASCADE'), nullable=False)
    
    # 日志信息
    log_level = Column(
        Enum('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'), 
        nullable=False, 
        default='INFO'
    )
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    
    # 上下文信息
    step_number = Column(Integer)
    step_name = Column(String(255))
    component = Column(String(100))  # 执行组件名称
    
    # 额外数据
    extra_data = Column(JSON)
    
    # 关系
    execution = relationship("ScriptExecution")
    
    # 索引
    __table_args__ = (
        Index('idx_logs_execution_id', 'execution_id'),
        Index('idx_logs_level', 'log_level'),
        Index('idx_logs_timestamp', 'timestamp'),
        Index('idx_logs_step', 'step_number'),
    )
    
    def __repr__(self):
        return f"<ExecutionLog(id={self.id}, level={self.log_level}, execution_id={self.execution_id})>"

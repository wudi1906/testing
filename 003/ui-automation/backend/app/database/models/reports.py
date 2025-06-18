"""
测试报告数据库模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON
from sqlalchemy.sql import func
from .base import BaseModel


class TestReport(BaseModel):
    """测试报告数据库模型"""
    __tablename__ = "test_reports"

    id = Column(Integer, primary_key=True, index=True)
    
    # 基本信息
    script_id = Column(String(255), nullable=False, index=True, comment="脚本ID")
    script_name = Column(String(255), nullable=False, comment="脚本名称")
    session_id = Column(String(255), nullable=False, index=True, comment="执行会话ID")
    execution_id = Column(String(255), nullable=False, index=True, comment="执行ID")
    
    # 执行结果
    status = Column(String(50), nullable=False, comment="执行状态: passed/failed/error")
    return_code = Column(Integer, default=0, comment="返回码")
    
    # 时间信息
    start_time = Column(DateTime, nullable=True, comment="开始时间")
    end_time = Column(DateTime, nullable=True, comment="结束时间")
    duration = Column(Float, default=0.0, comment="执行时长(秒)")
    
    # 测试结果统计
    total_tests = Column(Integer, default=0, comment="总测试数")
    passed_tests = Column(Integer, default=0, comment="通过测试数")
    failed_tests = Column(Integer, default=0, comment="失败测试数")
    skipped_tests = Column(Integer, default=0, comment="跳过测试数")
    success_rate = Column(Float, default=0.0, comment="成功率")
    
    # 报告文件信息
    report_path = Column(Text, nullable=True, comment="报告文件路径")
    report_url = Column(Text, nullable=True, comment="报告访问URL")
    report_size = Column(Integer, default=0, comment="报告文件大小(字节)")
    
    # 产物信息
    screenshots = Column(JSON, nullable=True, comment="截图文件列表")
    videos = Column(JSON, nullable=True, comment="视频文件列表")
    artifacts = Column(JSON, nullable=True, comment="其他产物文件列表")
    
    # 错误信息
    error_message = Column(Text, nullable=True, comment="错误信息")
    logs = Column(JSON, nullable=True, comment="执行日志")
    
    # 环境信息
    execution_config = Column(JSON, nullable=True, comment="执行配置")
    environment_variables = Column(JSON, nullable=True, comment="环境变量")
    
    def __repr__(self):
        return f"<TestReport(id={self.id}, script_name='{self.script_name}', status='{self.status}')>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "script_id": self.script_id,
            "script_name": self.script_name,
            "session_id": self.session_id,
            "execution_id": self.execution_id,
            "status": self.status,
            "return_code": self.return_code,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "success_rate": self.success_rate,
            "report_path": self.report_path,
            "report_url": self.report_url,
            "report_size": self.report_size,
            "screenshots": self.screenshots,
            "videos": self.videos,
            "artifacts": self.artifacts,
            "error_message": self.error_message,
            "logs": self.logs,
            "execution_config": self.execution_config,
            "environment_variables": self.environment_variables,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

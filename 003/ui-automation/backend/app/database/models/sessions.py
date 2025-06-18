"""
会话管理相关数据库模型
"""
from sqlalchemy import Column, String, Text, Enum, Integer, DECIMAL, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from .base import BaseModel


class Session(BaseModel):
    """分析会话表模型"""
    
    __tablename__ = 'sessions'
    
    # 关联项目
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='SET NULL'))
    
    # 会话信息
    session_type = Column(Enum('image_analysis', 'url_analysis', 'multi_crawl'), nullable=False)
    status = Column(Enum('pending', 'processing', 'completed', 'failed'), default='pending')
    platform = Column(Enum('web', 'android', 'api'), default='web')
    
    # 请求和结果数据
    request_data = Column(JSON)
    analysis_result = Column(JSON)
    confidence_score = Column(DECIMAL(5, 2))
    
    # 时间信息
    duration_seconds = Column(Integer)
    
    # 错误信息
    error_message = Column(Text)
    
    # 关系
    project = relationship("Project", back_populates="sessions")
    test_scripts = relationship("TestScript", back_populates="session")
    
    # 索引
    __table_args__ = (
        Index('idx_sessions_type', 'session_type'),
        Index('idx_sessions_status', 'status'),
        Index('idx_sessions_platform', 'platform'),
        Index('idx_sessions_started_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Session(id={self.id}, type={self.session_type}, status={self.status})>"

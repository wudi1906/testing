"""
项目管理相关数据库模型
"""
from sqlalchemy import Column, String, Text, Enum, Index
from sqlalchemy.orm import relationship
from .base import BaseModel


class Project(BaseModel):
    """项目表模型"""
    
    __tablename__ = 'projects'
    
    # 基本信息
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum('active', 'inactive', 'archived'), default='active')
    created_by = Column(String(100))
    
    # 关系
    sessions = relationship("Session", back_populates="project", cascade="all, delete-orphan")
    test_scripts = relationship("TestScript", back_populates="project", cascade="all, delete-orphan")
    
    # 索引
    __table_args__ = (
        Index('idx_projects_status', 'status'),
        Index('idx_projects_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name}, status={self.status})>"

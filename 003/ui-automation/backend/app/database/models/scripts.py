"""
测试脚本相关数据库模型
"""
from sqlalchemy import (
    Column, String, Text, Enum, Integer, ForeignKey, Index, 
    DateTime, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import relationship
from .base import BaseModel


class TestScript(BaseModel):
    """测试脚本表模型"""
    
    __tablename__ = 'test_scripts'
    
    # 关联信息
    session_id = Column(String(36), ForeignKey('sessions.id', ondelete='SET NULL'))
    project_id = Column(String(36), ForeignKey('projects.id', ondelete='CASCADE'))
    
    # 基本信息
    name = Column(String(255), nullable=False)
    description = Column(Text)
    script_format = Column(Enum('yaml', 'playwright'), nullable=False)
    script_type = Column(Enum('image_analysis', 'url_analysis', 'mixed_analysis', 'manual_creation'), nullable=False)
    
    # 脚本内容
    content = Column(Text, nullable=False)
    file_path = Column(String(500))
    
    # 测试信息
    test_description = Column(Text, nullable=False)
    additional_context = Column(Text)
    source_url = Column(String(1000))
    source_image_path = Column(String(500))
    
    # 执行统计
    execution_count = Column(Integer, default=0)
    last_execution_time = Column(DateTime)
    last_execution_status = Column(Enum('pending', 'running', 'completed', 'failed', 'cancelled'))
    
    # 分类和标签
    category = Column(String(100))
    priority = Column(Integer, default=1)
    
    # 关联信息
    analysis_result_id = Column(String(36))
    
    # 关系
    session = relationship("Session", back_populates="test_scripts")
    project = relationship("Project", back_populates="test_scripts")
    tags = relationship("ScriptTag", back_populates="script", cascade="all, delete-orphan")
    executions = relationship("ScriptExecution", back_populates="script", cascade="all, delete-orphan")
    source_relationships = relationship(
        "ScriptRelationship", 
        foreign_keys="ScriptRelationship.source_script_id",
        back_populates="source_script",
        cascade="all, delete-orphan"
    )
    target_relationships = relationship(
        "ScriptRelationship",
        foreign_keys="ScriptRelationship.target_script_id",
        back_populates="target_script"
    )
    # collection_memberships = relationship("CollectionScript", back_populates="script")  # 暂时注释，等待CollectionScript模型实现
    
    # 约束和索引
    __table_args__ = (
        CheckConstraint('priority BETWEEN 1 AND 5', name='ck_script_priority'),
        Index('idx_scripts_format', 'script_format'),
        Index('idx_scripts_type', 'script_type'),
        Index('idx_scripts_category', 'category'),
        Index('idx_scripts_created_at', 'created_at'),
        Index('idx_scripts_execution_count', 'execution_count'),
    )
    
    def __repr__(self):
        return f"<TestScript(id={self.id}, name={self.name}, format={self.script_format})>"


class ScriptTag(BaseModel):
    """脚本标签表模型"""
    
    __tablename__ = 'script_tags'
    
    # 使用自增ID作为主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联脚本
    script_id = Column(String(36), ForeignKey('test_scripts.id', ondelete='CASCADE'), nullable=False)
    tag_name = Column(String(100), nullable=False)
    
    # 关系
    script = relationship("TestScript", back_populates="tags")
    
    # 约束和索引
    __table_args__ = (
        UniqueConstraint('script_id', 'tag_name', name='uk_script_tag'),
        Index('idx_script_tags_name', 'tag_name'),
    )
    
    def __repr__(self):
        return f"<ScriptTag(script_id={self.script_id}, tag={self.tag_name})>"


class ScriptRelationship(BaseModel):
    """脚本关系表模型"""
    
    __tablename__ = 'script_relationships'
    
    # 使用自增ID作为主键
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 关联脚本
    source_script_id = Column(String(36), ForeignKey('test_scripts.id', ondelete='CASCADE'), nullable=False)
    target_script_id = Column(String(36), ForeignKey('test_scripts.id', ondelete='CASCADE'), nullable=False)
    relationship_type = Column(Enum('derived_from', 'similar_to', 'depends_on'), nullable=False)
    
    # 关系
    source_script = relationship("TestScript", foreign_keys=[source_script_id], back_populates="source_relationships")
    target_script = relationship("TestScript", foreign_keys=[target_script_id], back_populates="target_relationships")
    
    # 约束
    __table_args__ = (
        UniqueConstraint('source_script_id', 'target_script_id', 'relationship_type', name='uk_script_relationship'),
    )
    
    def __repr__(self):
        return f"<ScriptRelationship(source={self.source_script_id}, target={self.target_script_id}, type={self.relationship_type})>"

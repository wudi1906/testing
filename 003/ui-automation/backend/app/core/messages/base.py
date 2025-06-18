"""
UI自动化测试系统 - 基础消息类型
定义所有智能体间通信的基础消息结构
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.core.types import TestTypes, TestCase, TestResult, TestEnvironment, TestExecutionContext


class BaseMessage(BaseModel):
    """基础消息模型"""
    id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    source: Optional[str] = None


class ResponseMessage(BaseMessage):
    """响应消息模型"""
    content: str
    is_final: bool = False
    result: Optional[Dict[str, Any]] = None
    message_type: str = "info"
    agent_id: Optional[str] = None


class StreamMessage(BaseModel):
    """流式消息模型"""
    type: str = Field(..., description="消息类型")
    source: str = Field(..., description="消息来源")
    content: str = Field(..., description="消息内容")
    region: str = Field(default="process", description="消息区域")
    is_final: bool = Field(default=False, description="是否最终消息")
    result: Optional[Dict[str, Any]] = Field(None, description="结果数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    message_id: Optional[str] = Field(None, description="消息ID")
    platform: str = Field(default="web", description="平台类型")


# ============ 通用智能体间通信消息 ============

class RequirementMessage(BaseMessage):
    """需求消息模型"""
    requirement_id: str
    requirement: str = Field(..., description="测试需求描述")
    app_name: Optional[str] = Field(None, description="应用名称")
    app_url: Optional[str] = Field(None, description="应用URL")
    app_type: Optional[str] = Field(None, description="应用类型")
    special_requirements: Optional[str] = Field(None, description="特殊要求")


class TestPlanMessage(BaseMessage):
    """测试计划消息模型"""
    requirement_id: str
    test_plan: Dict[str, Any]
    app_url: Optional[str] = None
    app_name: Optional[str] = None


class UIAnalysisMessage(BaseMessage):
    """UI分析消息模型"""
    requirement_id: str
    test_plan: Dict[str, Any]
    ui_analysis: Dict[str, Any]
    page_data: Optional[Dict[str, Any]] = None


class ActionGenerationMessage(BaseMessage):
    """动作生成消息模型"""
    requirement_id: str
    test_plan: Dict[str, Any]
    ui_analysis: Dict[str, Any]
    test_cases: List[TestCase]


class TestExecutionMessage(BaseMessage):
    """测试执行消息模型"""
    requirement_id: str
    test_cases: List[TestCase]
    ui_analysis: Dict[str, Any]
    environment: TestEnvironment
    execution_config: Dict[str, Any] = Field(default_factory=dict)


class ResultAnalysisMessage(BaseMessage):
    """结果分析消息模型"""
    requirement_id: str
    test_results: List[TestResult]
    execution_context: TestExecutionContext


class ReportGenerationMessage(BaseMessage):
    """报告生成消息模型"""
    requirement_id: str
    test_results: List[TestResult]
    analysis_summary: Dict[str, Any]
    execution_context: TestExecutionContext

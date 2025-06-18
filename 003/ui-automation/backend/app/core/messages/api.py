"""
UI自动化测试系统 - API测试模块消息类型
定义API测试智能体间通信的消息结构
"""
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime

from .base import BaseMessage


# ============ API测试模块基础数据模型 ============

class APIEndpoint(BaseModel):
    """API端点信息"""
    method: str = Field(..., description="HTTP方法: GET, POST, PUT, DELETE等")
    url: str = Field(..., description="API端点URL")
    path: str = Field(..., description="API路径")
    description: str = Field(..., description="端点描述")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="请求参数")
    headers: Dict[str, str] = Field(default_factory=dict, description="请求头")
    body_schema: Optional[Dict[str, Any]] = Field(None, description="请求体结构")
    response_schema: Optional[Dict[str, Any]] = Field(None, description="响应体结构")
    auth_required: bool = Field(default=False, description="是否需要认证")
    tags: List[str] = Field(default_factory=list, description="标签")


class APITestCase(BaseModel):
    """API测试用例"""
    test_id: str = Field(..., description="测试用例ID")
    name: str = Field(..., description="测试用例名称")
    description: str = Field(..., description="测试用例描述")
    endpoint: APIEndpoint = Field(..., description="测试的API端点")
    test_data: Dict[str, Any] = Field(default_factory=dict, description="测试数据")
    expected_status: int = Field(default=200, description="期望的HTTP状态码")
    expected_response: Optional[Dict[str, Any]] = Field(None, description="期望的响应内容")
    assertions: List[str] = Field(default_factory=list, description="断言列表")
    setup_steps: List[str] = Field(default_factory=list, description="前置步骤")
    cleanup_steps: List[str] = Field(default_factory=list, description="清理步骤")
    dependencies: List[str] = Field(default_factory=list, description="依赖的测试用例")


class APITestResult(BaseModel):
    """API测试结果"""
    test_id: str = Field(..., description="测试用例ID")
    status: str = Field(..., description="测试状态: PASS, FAIL, SKIP, ERROR")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    duration: float = Field(..., description="执行时间（秒）")
    request_data: Dict[str, Any] = Field(default_factory=dict, description="实际请求数据")
    response_data: Dict[str, Any] = Field(default_factory=dict, description="实际响应数据")
    response_status: int = Field(..., description="响应状态码")
    response_time: float = Field(..., description="响应时间（毫秒）")
    error_message: Optional[str] = Field(None, description="错误信息")
    assertion_results: List[Dict[str, Any]] = Field(default_factory=list, description="断言结果")


class APIAnalysisResult(BaseModel):
    """API分析结果"""
    endpoints: List[APIEndpoint] = Field(default_factory=list, description="发现的API端点")
    test_scenarios: List[str] = Field(default_factory=list, description="测试场景")
    test_cases: List[APITestCase] = Field(default_factory=list, description="生成的测试用例")
    analysis_summary: str = Field(..., description="分析总结")
    confidence_score: float = Field(default=0.0, description="置信度分数")
    api_documentation: Optional[str] = Field(None, description="API文档链接")
    authentication_info: Optional[Dict[str, Any]] = Field(None, description="认证信息")


class APIGeneratedScript(BaseModel):
    """API生成的测试脚本"""
    format: str = Field(..., description="脚本格式: postman, newman, pytest, requests")
    content: str = Field(..., description="脚本内容")
    file_path: Optional[str] = Field(None, description="文件路径")
    estimated_duration: Optional[str] = Field(None, description="预估执行时间")
    script_type: str = Field(default="api_test", description="脚本类型")
    framework: str = Field(default="requests", description="测试框架")


# ============ API测试智能体消息类型 ============

class APIAnalysisRequest(BaseMessage):
    """API分析请求消息"""
    session_id: str = Field(..., description="会话ID")
    analysis_type: str = Field(..., description="分析类型: swagger, postman, url, manual")
    api_source: str = Field(..., description="API源: URL, 文件内容或描述")
    test_description: str = Field(..., description="测试需求描述")
    additional_context: Optional[str] = Field(None, description="额外上下文信息")
    generate_formats: List[str] = Field(default=["postman"], description="生成格式列表")
    base_url: Optional[str] = Field(None, description="API基础URL")
    auth_config: Optional[Dict[str, Any]] = Field(None, description="认证配置")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "uuid-string",
                "analysis_type": "swagger",
                "api_source": "https://api.example.com/swagger.json",
                "test_description": "测试用户管理API的CRUD操作",
                "additional_context": "需要测试权限验证和数据验证",
                "generate_formats": ["postman", "pytest"],
                "base_url": "https://api.example.com",
                "auth_config": {
                    "type": "bearer",
                    "token": "{{auth_token}}"
                }
            }
        }


class APIAnalysisResponse(BaseMessage):
    """API分析响应消息"""
    session_id: str = Field(..., description="会话ID")
    analysis_result: APIAnalysisResult = Field(..., description="分析结果")
    generated_scripts: List[APIGeneratedScript] = Field(default_factory=list, description="生成的脚本")
    status: str = Field(..., description="处理状态")
    message: str = Field(..., description="响应消息")
    processing_time: float = Field(default=0.0, description="处理时间（秒）")


class APITestGenerationMessage(BaseMessage):
    """API测试生成消息"""
    session_id: str = Field(..., description="会话ID")
    requirement_id: str = Field(..., description="需求ID")
    analysis_result: APIAnalysisResult = Field(..., description="分析结果")
    test_description: str = Field(..., description="测试描述")
    generation_config: Dict[str, Any] = Field(default_factory=dict, description="生成配置")


class APITestExecutionMessage(BaseMessage):
    """API测试执行消息"""
    session_id: str = Field(..., description="会话ID")
    execution_id: str = Field(..., description="执行ID")
    test_cases: List[APITestCase] = Field(..., description="要执行的测试用例")
    execution_config: Dict[str, Any] = Field(default_factory=dict, description="执行配置")
    environment_config: Dict[str, Any] = Field(default_factory=dict, description="环境配置")


class APISwaggerAnalysisMessage(BaseMessage):
    """API Swagger文档分析消息"""
    session_id: str = Field(..., description="会话ID")
    swagger_url: Optional[str] = Field(None, description="Swagger文档URL")
    swagger_content: Optional[str] = Field(None, description="Swagger文档内容")
    test_requirements: str = Field(..., description="测试需求")
    analysis_depth: str = Field(default="standard", description="分析深度: basic, standard, detailed")


class APIPostmanCollectionMessage(BaseMessage):
    """API Postman集合分析消息"""
    session_id: str = Field(..., description="会话ID")
    collection_data: str = Field(..., description="Postman集合JSON数据")
    environment_data: Optional[str] = Field(None, description="Postman环境变量JSON数据")
    test_requirements: str = Field(..., description="测试需求")


class APIPerformanceTestMessage(BaseMessage):
    """API性能测试消息"""
    session_id: str = Field(..., description="会话ID")
    endpoints: List[APIEndpoint] = Field(..., description="要测试的API端点")
    load_config: Dict[str, Any] = Field(..., description="负载配置")
    duration: int = Field(default=60, description="测试持续时间（秒）")
    concurrent_users: int = Field(default=10, description="并发用户数")
    ramp_up_time: int = Field(default=10, description="加压时间（秒）")


class APISecurityTestMessage(BaseMessage):
    """API安全测试消息"""
    session_id: str = Field(..., description="会话ID")
    endpoints: List[APIEndpoint] = Field(..., description="要测试的API端点")
    security_tests: List[str] = Field(default_factory=list, description="安全测试类型")
    auth_config: Optional[Dict[str, Any]] = Field(None, description="认证配置")
    vulnerability_scan: bool = Field(default=True, description="是否进行漏洞扫描")

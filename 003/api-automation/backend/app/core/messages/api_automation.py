# """
# 接口自动化相关消息定义 - 重新设计版本
# 支持新的数据流转模型和智能体通信
# """
# from datetime import datetime
# from typing import Any, Dict, List, Optional, Union
# from pydantic import BaseModel, Field
#
# from .base import BaseMessage
#
# # 导入重新设计的数据模型作为消息类型
# from app.core.messages.api_automation.schemas import (
#     DocumentParseInput, DocumentParseOutput,
#     AnalysisInput, AnalysisOutput,
#     TestCaseGenerationInput, TestCaseGenerationOutput,
#     ScriptGenerationInput, ScriptGenerationOutput
# )
#
#
# class ApiDocumentInfo(BaseModel):
#     """API文档信息"""
#     title: str = Field(..., description="API标题")
#     version: str = Field(..., description="API版本")
#     description: str = Field("", description="API描述")
#     base_url: str = Field("", description="基础URL")
#     contact_info: Dict[str, Any] = Field(default_factory=dict, description="联系信息")
#     license_info: Dict[str, Any] = Field(default_factory=dict, description="许可证信息")
#     tags: List[str] = Field(default_factory=list, description="标签列表")
#     external_docs: Dict[str, Any] = Field(default_factory=dict, description="外部文档")
#
#
# class ApiEndpointInfo(BaseModel):
#     """API端点信息"""
#     path: str = Field(..., description="API路径")
#     method: HttpMethod = Field(..., description="HTTP方法")
#     summary: str = Field("", description="API摘要")
#     description: str = Field("", description="API描述")
#     tags: List[str] = Field(default_factory=list, description="标签")
#     parameters: List[Dict[str, Any]] = Field(default_factory=list, description="参数列表")
#     request_body: Optional[Dict[str, Any]] = Field(None, description="请求体")
#     responses: Dict[str, Any] = Field(default_factory=dict, description="响应定义")
#     auth_required: bool = Field(False, description="是否需要认证")
#     auth_type: AuthType = Field(AuthType.NONE, description="认证类型")
#     content_type: ContentType = Field(ContentType.JSON, description="内容类型")
#
#
# class TestCaseInfo(BaseModel):
#     """测试用例信息"""
#     test_id: str = Field(..., description="测试用例ID")
#     name: str = Field(..., description="测试用例名称")
#     description: str = Field("", description="测试用例描述")
#     endpoint: ApiEndpointInfo = Field(..., description="关联的API端点")
#     test_type: TestType = Field(..., description="测试类型")
#     test_level: TestLevel = Field(..., description="测试级别")
#     priority: Priority = Field(..., description="优先级")
#     test_data: List[Dict[str, Any]] = Field(default_factory=list, description="测试数据")
#     assertions: List[Dict[str, Any]] = Field(default_factory=list, description="断言列表")
#     setup_steps: List[str] = Field(default_factory=list, description="前置步骤")
#     teardown_steps: List[str] = Field(default_factory=list, description="后置步骤")
#     dependencies: List[str] = Field(default_factory=list, description="依赖的测试用例")
#     tags: List[str] = Field(default_factory=list, description="标签")
#     timeout: int = Field(30, description="超时时间(秒)")
#     retry_count: int = Field(0, description="重试次数")
#
#
# class TestScriptInfo(BaseModel):
#     """测试脚本信息"""
#     script_id: str = Field(..., description="脚本ID")
#     name: str = Field(..., description="脚本名称")
#     description: str = Field("", description="脚本描述")
#     file_path: str = Field(..., description="脚本文件路径")
#     content: str = Field(..., description="脚本内容")
#     test_cases: List[TestCaseInfo] = Field(default_factory=list, description="包含的测试用例")
#     dependencies: List[str] = Field(default_factory=list, description="依赖的脚本")
#     framework: str = Field("pytest", description="测试框架")
#     language: str = Field("python", description="编程语言")
#     tags: List[str] = Field(default_factory=list, description="标签")
#
#
# class TestResultInfo(BaseModel):
#     """测试结果信息"""
#     test_id: str = Field(..., description="测试ID")
#     test_name: str = Field(..., description="测试名称")
#     status: ExecutionStatus = Field(..., description="测试状态")
#     start_time: datetime = Field(..., description="开始时间")
#     end_time: Optional[datetime] = Field(None, description="结束时间")
#     duration: float = Field(0.0, description="执行时长")
#     error_message: Optional[str] = Field(None, description="错误信息")
#     stack_trace: Optional[str] = Field(None, description="堆栈跟踪")
#     response_code: Optional[int] = Field(None, description="响应状态码")
#     response_time: Optional[float] = Field(None, description="响应时间")
#     response_body: Optional[str] = Field(None, description="响应体")
#     assertions: List[Dict[str, Any]] = Field(default_factory=list, description="断言结果")
#     screenshots: List[str] = Field(default_factory=list, description="截图路径")
#     logs: List[str] = Field(default_factory=list, description="测试日志")
#
#
# class DependencyInfo(BaseModel):
#     """依赖信息"""
#     dependency_id: str = Field(..., description="依赖ID")
#     dependency_type: DependencyType = Field(..., description="依赖类型")
#     source_test: str = Field(..., description="源测试用例")
#     target_test: str = Field(..., description="目标测试用例")
#     dependency_data: Dict[str, Any] = Field(default_factory=dict, description="依赖数据")
#     is_required: bool = Field(True, description="是否必需")
#     description: str = Field("", description="依赖描述")
#
#
# class ExecutionResult(BaseModel):
#     """执行结果"""
#     test_id: str = Field(..., description="测试用例ID")
#     status: ExecutionStatus = Field(..., description="执行状态")
#     start_time: datetime = Field(..., description="开始时间")
#     end_time: Optional[datetime] = Field(None, description="结束时间")
#     duration: float = Field(0.0, description="执行时长(秒)")
#     request_data: Optional[Dict[str, Any]] = Field(None, description="请求数据")
#     response_data: Optional[Dict[str, Any]] = Field(None, description="响应数据")
#     assertion_results: List[Dict[str, Any]] = Field(default_factory=list, description="断言结果")
#     error_message: Optional[str] = Field(None, description="错误信息")
#     logs: List[str] = Field(default_factory=list, description="执行日志")
#     screenshots: List[str] = Field(default_factory=list, description="截图路径")
#     attachments: List[str] = Field(default_factory=list, description="附件路径")
#
#
# # API文档解析相关消息
# class ApiDocParseRequest(BaseMessage):
#     """API文档解析请求"""
#     file_path: str = Field(..., description="文件路径")
#     file_name: str = Field(..., description="文件名")
#     file_content: Optional[str] = Field(None, description="文件内容")
#     doc_format: str = Field("auto", description="文档格式")
#     parse_config: Dict[str, Any] = Field(default_factory=dict, description="解析配置")
#
#
# class ApiDocParseResponse(BaseMessage):
#     """API文档解析响应"""
#     doc_id: str = Field(..., description="文档ID")
#     file_name: str = Field(..., description="文件名")
#     doc_format: str = Field(..., description="文档格式")
#     api_info: Dict[str, Any] = Field(..., description="API基本信息")
#     endpoints: List[ApiEndpointInfo] = Field(..., description="API端点列表")
#     schemas: Dict[str, Any] = Field(default_factory=dict, description="数据模型")
#     security_schemes: Dict[str, Any] = Field(default_factory=dict, description="安全方案")
#     parse_errors: List[str] = Field(default_factory=list, description="解析错误")
#     parse_warnings: List[str] = Field(default_factory=list, description="解析警告")
#     confidence_score: float = Field(0.0, description="解析置信度")
#     processing_time: float = Field(0.0, description="处理时间")
#
#
# # 依赖分析相关消息
# class DependencyAnalysisRequest(BaseMessage):
#     """依赖分析请求"""
#     doc_id: str = Field(..., description="文档ID")
#     endpoints: List[ApiEndpointInfo] = Field(..., description="API端点列表")
#     analysis_config: Dict[str, Any] = Field(default_factory=dict, description="分析配置")
#
#
# class DependencyAnalysisResponse(BaseMessage):
#     """依赖分析响应"""
#     doc_id: str = Field(..., description="文档ID")
#     dependencies: List[DependencyInfo] = Field(..., description="依赖列表")
#     execution_order: List[str] = Field(..., description="执行顺序")
#     dependency_graph: Dict[str, Any] = Field(default_factory=dict, description="依赖图")
#     analysis_summary: Dict[str, Any] = Field(default_factory=dict, description="分析摘要")
#     processing_time: float = Field(0.0, description="处理时间")
#
#
# # 测试用例生成相关消息
# class TestCaseGenerationRequest(BaseMessage):
#     """测试用例生成请求"""
#     doc_id: str = Field(..., description="文档ID")
#     endpoints: List[ApiEndpointInfo] = Field(..., description="API端点列表")
#     dependencies: List[DependencyInfo] = Field(default_factory=list, description="依赖列表")
#     analysis_result: Dict[str, Any] = Field(default_factory=dict, description="接口分析结果")
#     generation_config: Dict[str, Any] = Field(default_factory=dict, description="生成配置")
#
#
# class TestCaseGenerationResponse(BaseMessage):
#     """测试用例生成响应"""
#     doc_id: str = Field(..., description="文档ID")
#     test_cases: List[TestCaseInfo] = Field(..., description="测试用例列表")
#     coverage_analysis: Dict[str, Any] = Field(default_factory=dict, description="覆盖度分析")
#     generation_summary: Dict[str, Any] = Field(default_factory=dict, description="生成摘要")
#     processing_time: float = Field(0.0, description="处理时间")
#
#
# # 测试脚本生成相关消息
# class TestScriptGenerationRequest(BaseMessage):
#     """测试脚本生成请求"""
#     doc_id: str = Field(..., description="文档ID")
#     endpoints: List[ApiEndpointInfo] = Field(..., description="API端点列表")
#     dependencies: List[DependencyInfo] = Field(default_factory=list, description="依赖列表")
#     test_config: Dict[str, Any] = Field(default_factory=dict, description="测试配置")
#     framework: str = Field("pytest", description="测试框架")
#     output_path: str = Field("", description="输出路径")
#
#
# class TestScriptGenerationResponse(BaseMessage):
#     """测试脚本生成响应"""
#     doc_id: str = Field(..., description="文档ID")
#     test_cases: List[TestCaseInfo] = Field(..., description="测试用例列表")
#     script_files: List[str] = Field(..., description="生成的脚本文件路径")
#     config_files: List[str] = Field(default_factory=list, description="配置文件路径")
#     requirements_file: Optional[str] = Field(None, description="依赖文件路径")
#     generation_summary: Dict[str, Any] = Field(default_factory=dict, description="生成摘要")
#     processing_time: float = Field(0.0, description="处理时间")
#
#
# # 测试执行相关消息
# class TestExecutionRequest(BaseMessage):
#     """测试执行请求"""
#     doc_id: str = Field(..., description="文档ID")
#     test_cases: List[TestCaseInfo] = Field(..., description="测试用例列表")
#     script_files: List[str] = Field(..., description="脚本文件路径")
#     execution_config: Dict[str, Any] = Field(default_factory=dict, description="执行配置")
#     environment: str = Field("test", description="执行环境")
#     parallel: bool = Field(False, description="是否并行执行")
#     max_workers: int = Field(1, description="最大工作线程数")
#
#
# class TestExecutionResponse(BaseMessage):
#     """测试执行响应"""
#     doc_id: str = Field(..., description="文档ID")
#     execution_id: str = Field(..., description="执行ID")
#     results: List[ExecutionResult] = Field(..., description="执行结果列表")
#     summary: Dict[str, Any] = Field(..., description="执行摘要")
#     report_files: List[str] = Field(default_factory=list, description="报告文件路径")
#     log_files: List[str] = Field(default_factory=list, description="日志文件路径")
#     execution_time: float = Field(0.0, description="总执行时间")
#     start_time: datetime = Field(..., description="开始时间")
#     end_time: datetime = Field(..., description="结束时间")
#
#
# # 日志记录相关消息
# class LogRecordRequest(BaseMessage):
#     """日志记录请求"""
#     agent_name: str = Field(..., description="智能体名称")
#     log_level: str = Field(..., description="日志级别")
#     log_message: str = Field(..., description="日志消息")
#     log_data: Dict[str, Any] = Field(default_factory=dict, description="日志数据")
#     execution_context: Dict[str, Any] = Field(default_factory=dict, description="执行上下文")
#
#
# class LogRecordResponse(BaseMessage):
#     """日志记录响应"""
#     log_id: str = Field(..., description="日志ID")
#     recorded_at: datetime = Field(..., description="记录时间")
#     success: bool = Field(..., description="是否成功")
#     error_message: Optional[str] = Field(None, description="错误信息")

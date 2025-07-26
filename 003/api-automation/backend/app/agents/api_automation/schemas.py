"""
API自动化智能体数据模型 - 重新设计版本
清晰的数据流转：文档解析 -> 接口分析 -> 测试用例生成 -> 脚本生成

设计原则：
1. 每个智能体有明确的输入输出模型
2. 数据传递简洁高效，避免冗余
3. 命名统一规范，易于理解和维护
4. 支持扩展，便于后续功能增强
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# ============================================================================
# 基础枚举定义
# ============================================================================

class DocumentFormat(str, Enum):
    """文档格式"""
    AUTO = "auto"
    OPENAPI = "openapi"
    SWAGGER = "swagger"
    POSTMAN = "postman"
    PDF = "pdf"
    MARKDOWN = "markdown"


class HttpMethod(str, Enum):
    """HTTP方法"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ParameterLocation(str, Enum):
    """参数位置"""
    QUERY = "query"
    PATH = "path"
    HEADER = "header"
    BODY = "body"
    FORM = "form"
    COOKIE = "cookie"


class DataType(str, Enum):
    """数据类型"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class DependencyType(str, Enum):
    """依赖类型"""
    DATA_FLOW = "data_flow"      # 数据流依赖：需要前一个接口的返回数据
    AUTH_TOKEN = "auth_token"    # 认证依赖：需要认证token
    AUTH = "auth"                # 认证依赖：简化版本
    SEQUENCE = "sequence"        # 序列依赖：必须按顺序执行
    BUSINESS = "business"        # 业务依赖：业务逻辑相关
    DATA = "data"                # 数据依赖：数据相关
    FUNCTIONAL = "functional"    # 功能依赖：功能相关
    CONDITIONAL = "conditional"  # 条件依赖：根据条件决定是否执行


class TestCaseType(str, Enum):
    """测试用例类型"""
    POSITIVE = "positive"        # 正向测试
    NEGATIVE = "negative"        # 负向测试
    BOUNDARY = "boundary"        # 边界测试
    SECURITY = "security"        # 安全测试
    PERFORMANCE = "performance"  # 性能测试


class AssertionType(str, Enum):
    """断言类型"""
    STATUS_CODE = "status_code"
    RESPONSE_BODY = "response_body"
    RESPONSE_HEADER = "response_header"
    RESPONSE_TIME = "response_time"
    JSON_SCHEMA = "json_schema"


# ============================================================================
# 1. 文档解析智能体 - 输入输出模型
# ============================================================================

class DocumentParseInput(BaseModel):
    """文档解析输入"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="会话ID")
    file_path: str = Field(..., description="文件路径")
    file_name: str = Field(..., description="文件名")
    file_content: Optional[str] = Field(None, description="文件内容")
    doc_format: DocumentFormat = Field(DocumentFormat.AUTO, description="文档格式")
    parse_options: Dict[str, Any] = Field(default_factory=dict, description="解析选项")


class ApiParameter(BaseModel):
    """API参数"""
    name: str = Field(..., description="参数名称")
    location: ParameterLocation = Field(..., description="参数位置")
    data_type: DataType = Field(..., description="数据类型")
    required: bool = Field(False, description="是否必需")
    description: str = Field("", description="参数描述")
    example: Any = Field(None, description="示例值")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="参数约束")


class ApiResponse(BaseModel):
    """API响应"""
    status_code: str = Field(..., description="状态码")
    description: str = Field("", description="响应描述")
    content_type: str = Field("application/json", description="内容类型")
    response_schema: Dict[str, Any] = Field(default_factory=dict, description="响应结构")
    example: Any = Field(None, description="响应示例")


class ParsedEndpoint(BaseModel):
    """解析后的API端点"""
    endpoint_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="端点ID")
    path: str = Field(..., description="API路径")
    method: HttpMethod = Field(..., description="HTTP方法")
    summary: str = Field("", description="端点摘要")
    description: str = Field("", description="端点描述")
    tags: List[str] = Field(default_factory=list, description="标签")
    parameters: List[ApiParameter] = Field(default_factory=list, description="参数列表")
    responses: List[ApiResponse] = Field(default_factory=list, description="响应列表")
    auth_required: bool = Field(False, description="是否需要认证")
    deprecated: bool = Field(False, description="是否已废弃")

    # 扩展信息字段 - 用于传递更丰富的接口信息给智能体
    extended_info: Dict[str, Any] = Field(default_factory=dict, description="扩展信息")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="原始数据")
    security_schemes: Dict[str, Any] = Field(default_factory=dict, description="安全方案")
    complexity_score: float = Field(0.0, description="复杂度评分")
    confidence_score: float = Field(0.0, description="置信度评分")

    # 接口分类和标识信息
    interface_name: str = Field("", description="接口名称")
    category: str = Field("", description="接口分类")
    auth_type: str = Field("", description="认证类型")


class ParsedApiInfo(BaseModel):
    """解析后的API信息"""
    title: str = Field(..., description="API标题")
    version: str = Field(..., description="API版本")
    description: str = Field("", description="API描述")
    base_url: str = Field("", description="基础URL")
    contact: Dict[str, str] = Field(default_factory=dict, description="联系信息")
    license: Dict[str, str] = Field(default_factory=dict, description="许可证信息")


class DocumentParseOutput(BaseModel):
    """文档解析输出 - 增强版本，保留更多信息"""
    session_id: str = Field(..., description="会话ID")
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="文档ID")
    file_name: str = Field(..., description="文件名")
    doc_format: DocumentFormat = Field(..., description="文档格式")
    api_info: ParsedApiInfo = Field(..., description="API基本信息")
    endpoints: List[ParsedEndpoint] = Field(default_factory=list, description="端点列表")
    parse_errors: List[str] = Field(default_factory=list, description="解析错误")
    parse_warnings: List[str] = Field(default_factory=list, description="解析警告")
    confidence_score: float = Field(0.0, description="解析置信度")
    processing_time: float = Field(0.0, description="处理时间")

    # 新增：扩展信息字段，保留大模型解析的丰富数据
    extended_info: Dict[str, Any] = Field(default_factory=dict, description="扩展信息")
    raw_parsed_data: Dict[str, Any] = Field(default_factory=dict, description="原始解析数据")

    # 新增：质量评估信息
    quality_assessment: Dict[str, Any] = Field(default_factory=dict, description="质量评估")
    testing_recommendations: List[Dict[str, Any]] = Field(default_factory=list, description="测试建议")

    # 新增：错误代码映射
    error_codes: Dict[str, str] = Field(default_factory=dict, description="错误代码说明")

    # 新增：全局配置信息
    global_headers: Dict[str, Any] = Field(default_factory=dict, description="全局请求头")
    security_schemes: Dict[str, Any] = Field(default_factory=dict, description="安全方案")
    servers: List[Dict[str, Any]] = Field(default_factory=list, description="服务器列表")


# ============================================================================
# 2. 接口分析智能体 - 输入输出模型
# ============================================================================

class AnalysisInput(BaseModel):
    """接口分析输入"""
    session_id: str = Field(..., description="会话ID")
    document_id: str = Field(..., description="文档ID")
    api_info: ParsedApiInfo = Field(..., description="API基本信息")
    endpoints: List[ParsedEndpoint] = Field(..., description="端点列表")
    analysis_options: Dict[str, Any] = Field(default_factory=dict, description="分析选项")


class EndpointDependency(BaseModel):
    """端点依赖关系"""
    dependency_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="依赖ID")
    source_endpoint_id: str = Field(..., description="源端点ID")
    target_endpoint_id: str = Field(..., description="目标端点ID")
    dependency_type: DependencyType = Field(..., description="依赖类型")
    description: str = Field("", description="依赖描述")
    data_mapping: Dict[str, str] = Field(default_factory=dict, description="数据映射关系")
    condition: Optional[str] = Field(None, description="依赖条件")


class ExecutionGroup(BaseModel):
    """执行组"""
    group_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="组ID")
    group_name: str = Field("", description="组名称")  # 改为可选，有默认值
    endpoint_ids: List[str] = Field(default_factory=list, description="端点ID列表")  # 改为可选
    endpoints: List[ParsedEndpoint] = Field(default_factory=list, description="端点对象列表")  # 新增
    execution_order: int = Field(0, description="执行顺序")  # 改为有默认值
    parallel_execution: bool = Field(False, description="是否可并行执行")
    prerequisites: List[str] = Field(default_factory=list, description="前置条件")  # 新增
    description: str = Field("", description="执行组描述")  # 新增


class AnalysisOutput(BaseModel):
    """接口分析输出"""
    session_id: str = Field(..., description="会话ID")
    document_id: str = Field(..., description="文档ID")
    dependencies: List[EndpointDependency] = Field(default_factory=list, description="依赖关系")
    execution_groups: List[ExecutionGroup] = Field(default_factory=list, description="执行组")
    test_strategy: List[str] = Field(default_factory=list, description="测试策略建议")
    risk_assessment: Dict[str, Any] = Field(default_factory=dict, description="风险评估")
    processing_time: float = Field(0.0, description="处理时间")


# ============================================================================
# 3. 测试用例生成智能体 - 输入输出模型
# ============================================================================

class TestCaseGenerationInput(BaseModel):
    """测试用例生成输入"""
    session_id: str = Field(..., description="会话ID")
    document_id: str = Field(..., description="文档ID")
    api_info: ParsedApiInfo = Field(..., description="API基本信息")
    endpoints: List[ParsedEndpoint] = Field(..., description="端点列表")
    dependencies: List[EndpointDependency] = Field(default_factory=list, description="依赖关系")
    execution_groups: List[ExecutionGroup] = Field(default_factory=list, description="执行组")
    generation_options: Dict[str, Any] = Field(default_factory=dict, description="生成选项")


class TestDataItem(BaseModel):
    """测试数据项"""
    parameter_name: str = Field(..., description="参数名称")
    test_value: Any = Field(..., description="测试值")
    value_description: str = Field("", description="值描述")


class TestAssertion(BaseModel):
    """测试断言"""
    assertion_type: AssertionType = Field(..., description="断言类型")
    expected_value: Any = Field(..., description="期望值")
    comparison_operator: str = Field("equals", description="比较操作符")
    description: str = Field("", description="断言描述")


class GeneratedTestCase(BaseModel):
    """生成的测试用例"""
    test_case_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="测试用例ID")
    test_name: str = Field(..., description="测试用例名称")
    endpoint_id: str = Field(..., description="关联端点ID")
    test_type: TestCaseType = Field(..., description="测试类型")
    description: str = Field("", description="测试描述")
    test_data: List[TestDataItem] = Field(default_factory=list, description="测试数据")
    assertions: List[TestAssertion] = Field(default_factory=list, description="断言列表")
    setup_steps: List[str] = Field(default_factory=list, description="前置步骤")
    cleanup_steps: List[str] = Field(default_factory=list, description="清理步骤")
    priority: int = Field(1, description="优先级")
    tags: List[str] = Field(default_factory=list, description="标签")


class TestCaseGenerationOutput(BaseModel):
    """测试用例生成输出"""
    session_id: str = Field(..., description="会话ID")
    document_id: str = Field(..., description="文档ID")
    test_cases: List[GeneratedTestCase] = Field(default_factory=list, description="测试用例列表")
    coverage_report: Dict[str, Any] = Field(default_factory=dict, description="覆盖度报告")
    generation_summary: Dict[str, Any] = Field(default_factory=dict, description="生成摘要")
    processing_time: float = Field(0.0, description="处理时间")


# ============================================================================
# 4. 脚本生成智能体 - 输入输出模型
# ============================================================================

class ScriptGenerationInput(BaseModel):
    """脚本生成输入"""
    session_id: str = Field(..., description="会话ID")
    document_id: str = Field(..., description="文档ID")
    interface_id: Optional[str] = Field(None, description="接口ID")
    api_info: ParsedApiInfo = Field(..., description="API基本信息")
    endpoints: List[ParsedEndpoint] = Field(..., description="端点列表")
    test_cases: List[GeneratedTestCase] = Field(..., description="测试用例列表")
    execution_groups: List[ExecutionGroup] = Field(default_factory=list, description="执行组")
    generation_options: Dict[str, Any] = Field(default_factory=dict, description="生成选项")


class GeneratedScript(BaseModel):
    """生成的测试脚本"""
    script_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="脚本ID")
    script_name: str = Field(..., description="脚本名称")
    file_path: str = Field(..., description="文件路径")
    script_content: str = Field(..., description="脚本内容")
    test_case_ids: List[str] = Field(default_factory=list, description="包含的测试用例ID")
    framework: str = Field("pytest", description="测试框架")
    dependencies: List[str] = Field(default_factory=list, description="依赖包")
    execution_order: int = Field(1, description="执行顺序")


class ScriptGenerationOutput(BaseModel):
    """脚本生成输出"""
    session_id: str = Field(..., description="会话ID")
    document_id: str = Field(..., description="文档ID")
    scripts: List[GeneratedScript] = Field(default_factory=list, description="脚本列表")
    config_files: Dict[str, str] = Field(default_factory=dict, description="配置文件")
    requirements_txt: str = Field("", description="依赖文件内容")
    readme_content: str = Field("", description="README内容")
    generation_summary: Dict[str, Any] = Field(default_factory=dict, description="生成摘要")
    processing_time: float = Field(0.0, description="处理时间")


class ScriptPersistenceInput(BaseModel):
    """脚本持久化输入"""
    session_id: str = Field(..., description="会话ID")
    document_id: str = Field(..., description="文档ID")
    interface_id: str = Field(..., description="接口ID")
    scripts: List[GeneratedScript] = Field(..., description="脚本列表")
    config_files: Dict[str, str] = Field(default_factory=dict, description="配置文件")
    requirements_txt: str = Field("", description="依赖文件内容")
    readme_content: str = Field("", description="README内容")
    generation_summary: Dict[str, Any] = Field(default_factory=dict, description="生成摘要")
    processing_time: float = Field(0.0, description="处理时间")


# ============================================================================
# 5. 测试执行智能体 - 输入输出模型
# ============================================================================

class TestExecutionInput(BaseModel):
    """测试执行输入"""
    session_id: str = Field(..., description="会话ID")
    document_id: str = Field(..., description="文档ID")
    scripts: List[GeneratedScript] = Field(..., description="要执行的脚本列表")
    execution_config: Dict[str, Any] = Field(default_factory=dict, description="执行配置")
    environment: str = Field("test", description="执行环境")
    parallel: bool = Field(False, description="是否并行执行")
    max_workers: int = Field(1, description="最大并发数")


class TestResult(BaseModel):
    """单个测试结果"""
    test_id: str = Field(..., description="测试ID")
    test_name: str = Field(..., description="测试名称")
    status: str = Field(..., description="执行状态")  # passed, failed, skipped, error
    duration: float = Field(0.0, description="执行时间(秒)")
    error_message: Optional[str] = Field(None, description="错误信息")
    failure_reason: Optional[str] = Field(None, description="失败原因")
    stdout: str = Field("", description="标准输出")
    stderr: str = Field("", description="标准错误")
    assertions: List[Dict[str, Any]] = Field(default_factory=list, description="断言结果")


class ScriptExecutionResult(BaseModel):
    """脚本执行结果"""
    script_id: str = Field(..., description="脚本ID")
    script_name: str = Field(..., description="脚本名称")
    status: str = Field(..., description="执行状态")  # success, failed, error
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    duration: float = Field(0.0, description="执行时间(秒)")
    test_results: List[TestResult] = Field(default_factory=list, description="测试结果列表")
    total_tests: int = Field(0, description="总测试数")
    passed_tests: int = Field(0, description="通过测试数")
    failed_tests: int = Field(0, description="失败测试数")
    skipped_tests: int = Field(0, description="跳过测试数")
    error_tests: int = Field(0, description="错误测试数")
    coverage_report: Dict[str, Any] = Field(default_factory=dict, description="覆盖率报告")


class TestExecutionOutput(BaseModel):
    """测试执行输出"""
    session_id: str = Field(..., description="会话ID")
    document_id: str = Field(..., description="文档ID")
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="执行ID")
    overall_status: str = Field(..., description="总体状态")  # success, failed, partial
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    total_duration: float = Field(0.0, description="总执行时间(秒)")
    script_results: List[ScriptExecutionResult] = Field(default_factory=list, description="脚本执行结果")
    summary: Dict[str, Any] = Field(default_factory=dict, description="执行摘要")
    reports: Dict[str, str] = Field(default_factory=dict, description="测试报告")
    artifacts: List[str] = Field(default_factory=list, description="生成的文件列表")
    processing_time: float = Field(0.0, description="处理时间")


# ============================================================================
# 智能体提示词模板 - 专业化设计
# ============================================================================

class AgentPrompts:
    """智能体提示词模板集合"""

    # 1. 文档解析智能体提示词
    DOCUMENT_PARSER_SYSTEM_PROMPT = """你是一个专业的API文档解析专家，具备以下核心能力：

1. **多格式文档解析**：精通OpenAPI/Swagger、Postman Collection、PDF等格式
2. **智能信息提取**：准确识别API端点、参数、响应结构
3. **数据标准化**：将不同格式的文档统一转换为标准结构
4. **质量评估**：对解析结果进行置信度评估

## 解析任务要求：
- 提取API基本信息（标题、版本、描述、基础URL）
- 识别所有API端点及其详细信息
- 分析参数类型、约束条件和示例值
- 提取响应格式和状态码定义
- 识别认证要求和安全配置

## 输出格式：
严格按照JSON格式输出，包含完整的API信息和端点列表。
确保数据结构清晰、字段完整、类型正确。"""

    DOCUMENT_PARSER_TASK_PROMPT = """请解析以下API文档内容：

## 文档信息
- 文件名：{file_name}
- 格式：{doc_format}

## 文档内容
{document_content}

## 解析要求
1. 提取API基本信息（标题、版本、描述、基础URL等）
2. 识别所有API端点，包括：
   - 路径和HTTP方法
   - 参数列表（查询参数、路径参数、请求体等）
   - 响应定义（状态码、响应结构、示例）
   - 认证要求
3. 分析参数约束和验证规则
4. 提取示例数据和默认值

请按照标准JSON格式输出解析结果，确保数据完整性和准确性。"""

    # 2. 接口分析智能体提示词
    API_ANALYZER_SYSTEM_PROMPT = """你是一个API依赖关系分析专家，专门负责：

1. **依赖关系识别**：分析API端点之间的数据流和调用依赖
2. **执行顺序规划**：确定最优的测试执行顺序
3. **风险评估**：识别潜在的测试风险和注意事项
4. **策略建议**：提供专业的测试策略建议

## 分析维度：
- **数据流依赖**：识别需要前置接口返回数据的端点
- **认证依赖**：识别需要认证token的端点
- **序列依赖**：识别必须按特定顺序执行的端点
- **条件依赖**：识别基于条件判断的依赖关系

## 输出要求：
提供清晰的依赖关系图和执行计划，确保测试的可靠性和效率。"""

    API_ANALYZER_TASK_PROMPT = """请分析以下API端点的依赖关系：

## API基本信息
{api_info}

## 端点列表
{endpoints}

## 分析任务
1. **依赖关系分析**：
   - 识别数据流依赖（哪些接口需要其他接口的返回数据）
   - 识别认证依赖（哪些接口需要先获取认证token）
   - 识别序列依赖（哪些接口必须按特定顺序执行）
   - 识别条件依赖（基于业务逻辑的依赖关系）

2. **执行计划制定**：
   - 将端点分组，确定执行顺序
   - 识别可并行执行的端点组
   - 制定数据传递方案

3. **风险评估**：
   - 识别潜在的测试风险点
   - 提供风险缓解建议

4. **测试策略建议**：
   - 推荐测试覆盖策略
   - 提供性能测试建议

请输出详细的分析结果，包括依赖关系、执行组和测试策略。"""

    # 3. 测试用例生成智能体提示词
    TEST_CASE_GENERATOR_SYSTEM_PROMPT = """你是一个测试用例设计专家，专精于API测试用例的设计和生成：

1. **全面测试覆盖**：设计正向、负向、边界、安全等多种类型的测试用例
2. **数据驱动测试**：为每个测试用例生成合适的测试数据
3. **断言设计**：设计准确有效的测试断言
4. **场景化测试**：基于业务场景设计端到端测试用例

## 测试用例类型：
- **正向测试**：验证正常业务流程
- **负向测试**：验证异常处理和错误响应
- **边界测试**：测试参数边界值和极限情况
- **安全测试**：验证权限控制和数据安全
- **性能测试**：验证响应时间和并发处理

## 设计原则：
- 测试用例应具备独立性和可重复性
- 测试数据应覆盖各种场景和边界情况
- 断言应准确验证预期结果
- 优先级设置应合理，便于测试执行规划"""

    TEST_CASE_GENERATOR_TASK_PROMPT = """请为以下API端点生成全面的测试用例：

## API基本信息
{api_info}

## 端点信息
{endpoints}

## 依赖关系
{dependencies}

## 执行组信息
{execution_groups}

## 生成要求
1. **测试用例设计**：
   - 为每个端点生成多种类型的测试用例
   - 正向测试：验证正常功能和业务流程
   - 负向测试：验证错误处理和异常情况
   - 边界测试：测试参数边界值和极限情况
   - 安全测试：验证权限控制和数据验证

2. **测试数据生成**：
   - 为每个测试用例生成合适的测试数据
   - 考虑参数约束和业务规则
   - 包含有效数据、无效数据和边界数据

3. **断言设计**：
   - 设计准确的状态码断言
   - 设计响应体结构和内容断言
   - 设计响应头和性能断言

4. **依赖处理**：
   - 处理端点间的数据依赖关系
   - 设计前置步骤和清理步骤

请生成详细的测试用例列表，确保测试覆盖度和质量。"""

    # 4. 脚本生成智能体提示词
    SCRIPT_GENERATOR_SYSTEM_PROMPT = """你是一个测试脚本生成专家，专门负责将测试用例转换为可执行的自动化测试脚本：

1. **代码生成**：生成高质量的pytest测试脚本
2. **框架集成**：集成pytest、requests、allure等测试框架
3. **最佳实践**：遵循测试代码的最佳实践和规范
4. **可维护性**：生成结构清晰、易于维护的测试代码

## 技术要求：
- 使用pytest作为测试框架
- 使用requests进行HTTP请求
- 集成allure进行测试报告
- 支持参数化测试和数据驱动
- 包含完整的错误处理和日志记录

## 代码质量：
- 代码结构清晰，注释完整
- 遵循PEP8编码规范
- 包含适当的异常处理
- 支持配置管理和环境切换"""

    SCRIPT_GENERATOR_TASK_PROMPT = """请基于以下测试用例生成可执行的pytest测试脚本：

## API基本信息
{api_info}

## 端点信息
{endpoints}

## 测试用例
{test_cases}

## 执行组信息
{execution_groups}

## 生成要求
1. **脚本结构**：
   - 生成完整的pytest测试脚本
   - 包含测试类和测试方法
   - 支持测试用例的组织和分类

2. **功能实现**：
   - 实现HTTP请求发送
   - 实现响应验证和断言
   - 实现数据依赖处理
   - 实现前置和清理步骤

3. **框架集成**：
   - 集成pytest框架特性
   - 集成allure测试报告
   - 支持参数化测试
   - 支持并发执行

4. **辅助功能**：
   - 生成配置文件
   - 生成依赖文件(requirements.txt)
   - 生成README文档
   - 生成测试工具类

请生成完整的测试脚本和相关配置文件，确保代码可以直接运行。"""

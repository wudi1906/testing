"""
API自动化智能体的数据模式定义
"""
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ApiDocParseRequest:
    """API文档解析请求"""
    doc_id: str
    session_id: str
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_content: Optional[str] = None
    doc_format: str = "auto"  # auto, openapi, swagger, postman, pdf
    options: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.options is None:
            self.options = {}


@dataclass
class ApiDocParseResponse:
    """API文档解析响应"""
    doc_id: str
    session_id: str
    status: str  # success, error, processing
    message: str = ""
    document_info: Optional['ApiDocumentInfo'] = None
    endpoints: List['ApiEndpointInfo'] = None
    errors: List[str] = None
    warnings: List[str] = None
    processing_time: float = 0.0
    confidence_score: float = 0.0
    
    def __post_init__(self):
        if self.endpoints is None:
            self.endpoints = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class ApiDocumentInfo:
    """API文档信息"""
    title: str
    version: str
    description: str = ""
    base_url: str = ""
    contact_info: Dict[str, Any] = None
    license_info: Dict[str, Any] = None
    tags: List[str] = None
    external_docs: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.contact_info is None:
            self.contact_info = {}
        if self.license_info is None:
            self.license_info = {}
        if self.tags is None:
            self.tags = []
        if self.external_docs is None:
            self.external_docs = {}


@dataclass
class ApiParameterInfo:
    """API参数信息"""
    name: str
    param_in: str  # query, path, header, body, formData
    param_type: str  # string, integer, boolean, array, object
    required: bool = False
    description: str = ""
    default_value: Any = None
    enum_values: List[Any] = None
    format: str = ""  # date, date-time, email, etc.
    pattern: str = ""
    minimum: Union[int, float] = None
    maximum: Union[int, float] = None
    min_length: int = None
    max_length: int = None
    
    def __post_init__(self):
        if self.enum_values is None:
            self.enum_values = []


@dataclass
class ApiResponseInfo:
    """API响应信息"""
    status_code: str
    description: str = ""
    schema: Dict[str, Any] = None
    headers: Dict[str, Any] = None
    examples: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.schema is None:
            self.schema = {}
        if self.headers is None:
            self.headers = {}
        if self.examples is None:
            self.examples = {}


@dataclass
class ApiEndpointInfo:
    """API端点信息"""
    path: str
    method: str
    operation_id: str = ""
    summary: str = ""
    description: str = ""
    tags: List[str] = None
    parameters: List[ApiParameterInfo] = None
    request_body: Dict[str, Any] = None
    responses: Dict[str, ApiResponseInfo] = None
    security: List[Dict[str, Any]] = None
    deprecated: bool = False
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.parameters is None:
            self.parameters = []
        if self.request_body is None:
            self.request_body = {}
        if self.responses is None:
            self.responses = {}
        if self.security is None:
            self.security = []


@dataclass
class ApiAnalysisRequest:
    """API分析请求"""
    doc_id: str
    session_id: str
    endpoints: List[ApiEndpointInfo]
    analysis_options: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.analysis_options is None:
            self.analysis_options = {}


@dataclass
class ApiAnalysisResponse:
    """API分析响应"""
    doc_id: str
    session_id: str
    status: str
    analysis_result: Dict[str, Any] = None
    recommendations: List[str] = None
    security_issues: List[str] = None
    performance_issues: List[str] = None
    complexity_score: float = 0.0
    
    def __post_init__(self):
        if self.analysis_result is None:
            self.analysis_result = {}
        if self.recommendations is None:
            self.recommendations = []
        if self.security_issues is None:
            self.security_issues = []
        if self.performance_issues is None:
            self.performance_issues = []


@dataclass
class TestGenerationRequest:
    """测试生成请求"""
    doc_id: str
    session_id: str
    endpoints: List[ApiEndpointInfo]
    generation_options: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.generation_options is None:
            self.generation_options = {}


@dataclass
class TestGenerationResponse:
    """测试生成响应"""
    doc_id: str
    session_id: str
    status: str
    test_scripts: List[Dict[str, Any]] = None
    test_cases: List[Dict[str, Any]] = None
    coverage_report: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.test_scripts is None:
            self.test_scripts = []
        if self.test_cases is None:
            self.test_cases = []
        if self.coverage_report is None:
            self.coverage_report = {}


@dataclass
class TestExecutionRequest:
    """测试执行请求"""
    session_id: str
    test_scripts: List[str]
    execution_options: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.execution_options is None:
            self.execution_options = {}


@dataclass
class TestExecutionResponse:
    """测试执行响应"""
    session_id: str
    execution_id: str
    status: str
    results: List[Dict[str, Any]] = None
    summary: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = []
        if self.summary is None:
            self.summary = {}


@dataclass
class LogRecordRequest:
    """日志记录请求"""
    session_id: str
    agent_type: str
    operation: str
    level: str = "INFO"
    message: str = ""
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


@dataclass
class LogRecordResponse:
    """日志记录响应"""
    log_id: str
    status: str
    message: str = ""


# 工具函数
def convert_dict_to_dataclass(data: Dict[str, Any], target_class):
    """将字典转换为数据类实例"""
    if not isinstance(data, dict):
        return data
    
    # 获取目标类的字段
    import inspect
    if hasattr(target_class, '__dataclass_fields__'):
        fields = target_class.__dataclass_fields__
        kwargs = {}
        
        for field_name, field_info in fields.items():
            if field_name in data:
                field_type = field_info.type
                field_value = data[field_name]
                
                # 处理嵌套的数据类
                if hasattr(field_type, '__dataclass_fields__'):
                    kwargs[field_name] = convert_dict_to_dataclass(field_value, field_type)
                elif hasattr(field_type, '__origin__') and field_type.__origin__ is list:
                    # 处理列表类型
                    if field_value and isinstance(field_value, list):
                        item_type = field_type.__args__[0] if field_type.__args__ else None
                        if item_type and hasattr(item_type, '__dataclass_fields__'):
                            kwargs[field_name] = [convert_dict_to_dataclass(item, item_type) for item in field_value]
                        else:
                            kwargs[field_name] = field_value
                    else:
                        kwargs[field_name] = field_value or []
                else:
                    kwargs[field_name] = field_value
        
        return target_class(**kwargs)
    
    return data

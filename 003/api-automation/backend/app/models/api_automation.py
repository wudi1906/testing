"""
接口自动化相关数据模型
优化版本 - 支持完整的API自动化功能
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from tortoise.models import Model
from tortoise import fields

from app.models.base import BaseModel, TimestampMixin
from app.core.enums import (
    SessionStatus, ExecutionStatus, TestType, Priority,
    TestLevel, HttpMethod, AuthType, ContentType, DependencyType,
    LogLevel, ReportFormat, EnvironmentType
)


class ApiDocument(BaseModel, TimestampMixin):
    """API文档模型 - 优化版"""
    doc_id = fields.CharField(max_length=100, unique=True, description="文档ID", index=True)
    session_id = fields.CharField(max_length=100, description="会话ID", index=True)

    # 文件信息
    file_name = fields.CharField(max_length=255, description="文件名")
    file_path = fields.CharField(max_length=500, description="文件路径")
    file_size = fields.BigIntField(default=0, description="文件大小(字节)")
    file_hash = fields.CharField(max_length=64, null=True, description="文件哈希值")

    # 文档格式和版本
    doc_format = fields.CharField(max_length=50, description="文档格式", index=True)  # openapi, swagger, postman
    doc_version = fields.CharField(max_length=20, null=True, description="文档版本")

    # API基本信息
    api_info = fields.JSONField(description="API基本信息")
    schemas = fields.JSONField(default=dict, description="数据模型定义")
    security_schemes = fields.JSONField(default=dict, description="安全方案")

    # 统计信息
    endpoints_count = fields.IntField(default=0, description="端点数量")
    schemas_count = fields.IntField(default=0, description="模型数量")

    # 解析状态和结果
    parse_status = fields.CharEnumField(SessionStatus, default=SessionStatus.CREATED, description="解析状态", index=True)
    parse_errors = fields.JSONField(default=list, description="解析错误")
    parse_warnings = fields.JSONField(default=list, description="解析警告")
    confidence_score = fields.FloatField(default=0.0, description="解析置信度")
    processing_time = fields.FloatField(default=0.0, description="处理时间(秒)")

    # 用户和权限
    uploaded_by = fields.CharField(max_length=100, null=True, description="上传用户", index=True)
    is_public = fields.BooleanField(default=False, description="是否公开")

    # 标签和分类
    tags = fields.JSONField(default=list, description="标签")
    category = fields.CharField(max_length=50, null=True, description="分类")

    # 状态管理
    is_active = fields.BooleanField(default=True, description="是否激活")
    is_deleted = fields.BooleanField(default=False, description="是否删除")

    class Meta:
        table = "api_documents"
        table_description = "API文档表"
        indexes = [
            ("doc_id", "session_id"),
            ("parse_status", "created_at"),
            ("uploaded_by", "is_active")
        ]


class ApiEndpoint(BaseModel, TimestampMixin):
    """API端点模型 - 优化版"""
    endpoint_id = fields.CharField(max_length=100, unique=True, description="端点ID", index=True)
    document = fields.ForeignKeyField("models.ApiDocument", related_name="endpoints", description="关联文档", index=True)

    # 基本信息
    path = fields.CharField(max_length=500, description="API路径", index=True)
    method = fields.CharEnumField(HttpMethod, description="HTTP方法", index=True)
    operation_id = fields.CharField(max_length=200, null=True, description="操作ID")

    # 描述信息
    summary = fields.TextField(default="", description="API摘要")
    description = fields.TextField(default="", description="API详细描述")
    tags = fields.JSONField(default=list, description="标签")

    # 参数和请求体
    parameters = fields.JSONField(default=list, description="参数列表")
    request_body = fields.JSONField(null=True, description="请求体定义")
    responses = fields.JSONField(default=dict, description="响应定义")

    # 认证和安全
    auth_required = fields.BooleanField(default=False, description="是否需要认证")
    auth_type = fields.CharEnumField(AuthType, default=AuthType.NONE, description="认证类型")
    security_requirements = fields.JSONField(default=list, description="安全要求")

    # 内容类型
    content_type = fields.CharEnumField(ContentType, default=ContentType.JSON, description="内容类型")
    produces = fields.JSONField(default=list, description="生产的媒体类型")
    consumes = fields.JSONField(default=list, description="消费的媒体类型")

    # 分析结果
    complexity_score = fields.FloatField(default=0.0, description="复杂度评分")
    security_level = fields.CharField(max_length=20, default="LOW", description="安全等级")
    performance_impact = fields.CharField(max_length=20, default="LOW", description="性能影响")

    # 依赖统计
    dependency_count = fields.IntField(default=0, description="依赖数量")
    dependent_count = fields.IntField(default=0, description="被依赖数量")

    # 测试统计
    test_case_count = fields.IntField(default=0, description="测试用例数量")
    last_test_time = fields.DatetimeField(null=True, description="最后测试时间")
    test_success_rate = fields.FloatField(default=0.0, description="测试成功率")

    # 状态
    is_deprecated = fields.BooleanField(default=False, description="是否已废弃")
    is_active = fields.BooleanField(default=True, description="是否激活")

    class Meta:
        table = "api_endpoints"
        table_description = "API端点表"
        indexes = [
            ("document_id", "method", "path"),
            ("tags", "is_active"),
            ("complexity_score", "security_level")
        ]


class TestCase(Model):
    """测试用例模型"""
    id = fields.IntField(pk=True)
    test_id = fields.CharField(max_length=100, unique=True, description="测试用例ID")
    document = fields.ForeignKeyField("models.ApiDocument", related_name="test_cases", description="关联文档")
    endpoint = fields.ForeignKeyField("models.ApiEndpoint", related_name="test_cases", description="关联端点")
    name = fields.CharField(max_length=255, description="测试用例名称")
    description = fields.TextField(default="", description="测试用例描述")
    test_type = fields.CharEnumField(TestType, description="测试类型")
    test_level = fields.CharEnumField(TestLevel, description="测试级别")
    priority = fields.CharEnumField(Priority, description="优先级")
    test_data = fields.JSONField(default=list, description="测试数据")
    assertions = fields.JSONField(default=list, description="断言列表")
    setup_steps = fields.JSONField(default=list, description="前置步骤")
    teardown_steps = fields.JSONField(default=list, description="后置步骤")
    dependencies = fields.JSONField(default=list, description="依赖的测试用例")
    tags = fields.JSONField(default=list, description="标签")
    timeout = fields.IntField(default=30, description="超时时间(秒)")
    retry_count = fields.IntField(default=0, description="重试次数")
    is_active = fields.BooleanField(default=True, description="是否激活")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "test_cases"
        table_description = "测试用例表"


class TestExecution(Model):
    """测试执行记录模型"""
    id = fields.IntField(pk=True)
    execution_id = fields.CharField(max_length=100, unique=True, description="执行ID")
    session_id = fields.CharField(max_length=100, description="会话ID")
    document = fields.ForeignKeyField("models.ApiDocument", related_name="executions", description="关联文档")
    execution_config = fields.JSONField(default=dict, description="执行配置")
    environment = fields.CharField(max_length=50, default="test", description="执行环境")
    parallel = fields.BooleanField(default=False, description="是否并行执行")
    max_workers = fields.IntField(default=1, description="最大工作线程数")
    status = fields.CharEnumField(ExecutionStatus, default=ExecutionStatus.PENDING, description="执行状态")
    start_time = fields.DatetimeField(null=True, description="开始时间")
    end_time = fields.DatetimeField(null=True, description="结束时间")
    execution_time = fields.FloatField(default=0.0, description="总执行时间")

    # 执行结果统计
    total_tests = fields.IntField(default=0, description="总测试数")
    passed_tests = fields.IntField(default=0, description="通过测试数")
    failed_tests = fields.IntField(default=0, description="失败测试数")
    skipped_tests = fields.IntField(default=0, description="跳过测试数")
    error_tests = fields.IntField(default=0, description="错误测试数")
    success_rate = fields.FloatField(default=0.0, description="成功率")

    # 性能统计
    avg_response_time = fields.FloatField(default=0.0, description="平均响应时间(ms)")
    max_response_time = fields.FloatField(default=0.0, description="最大响应时间(ms)")
    min_response_time = fields.FloatField(default=0.0, description="最小响应时间(ms)")

    # 报告和日志
    summary = fields.JSONField(default=dict, description="执行摘要")
    report_files = fields.JSONField(default=list, description="报告文件路径")
    log_files = fields.JSONField(default=list, description="日志文件路径")
    error_details = fields.JSONField(default=list, description="错误详情")

    # 执行描述
    description = fields.TextField(default="", description="执行描述")

    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "test_executions"
        table_description = "测试执行记录表"
        indexes = [
            ("execution_id",),
            ("session_id",),
            ("status", "created_at"),
            ("environment", "status"),
            ("document_id", "status")
        ]


class ScriptExecutionResult(Model):
    """脚本执行结果详情模型"""
    id = fields.IntField(pk=True)
    result_id = fields.CharField(max_length=100, unique=True, description="结果ID")
    execution = fields.ForeignKeyField("models.TestExecution", related_name="script_results", description="关联执行记录")
    script = fields.ForeignKeyField("models.TestScript", related_name="execution_results", description="关联脚本")

    # 执行信息
    script_name = fields.CharField(max_length=200, description="脚本名称")
    script_path = fields.CharField(max_length=500, description="脚本路径")
    start_time = fields.DatetimeField(description="开始时间")
    end_time = fields.DatetimeField(null=True, description="结束时间")
    duration = fields.FloatField(default=0.0, description="执行时长(秒)")

    # 执行状态
    status = fields.CharField(max_length=20, default="PENDING", description="执行状态")
    exit_code = fields.IntField(default=0, description="退出码")

    # 测试结果统计
    total_tests = fields.IntField(default=0, description="总测试数")
    passed_tests = fields.IntField(default=0, description="通过测试数")
    failed_tests = fields.IntField(default=0, description="失败测试数")
    skipped_tests = fields.IntField(default=0, description="跳过测试数")
    error_tests = fields.IntField(default=0, description="错误测试数")

    # 输出信息
    stdout = fields.TextField(default="", description="标准输出")
    stderr = fields.TextField(default="", description="标准错误")

    # 测试详情
    test_details = fields.JSONField(default=list, description="测试详情")
    assertions = fields.JSONField(default=list, description="断言结果")

    # 性能数据
    response_time = fields.FloatField(default=0.0, description="响应时间(ms)")
    request_data = fields.JSONField(default=dict, description="请求数据")
    response_data = fields.JSONField(default=dict, description="响应数据")
    response_status_code = fields.IntField(null=True, description="响应状态码")

    # 错误信息
    error_message = fields.TextField(default="", description="错误信息")
    failure_reason = fields.TextField(default="", description="失败原因")

    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "script_execution_results"
        table_description = "脚本执行结果详情表"
        indexes = [
            ("execution_id", "status"),
            ("script_id", "status"),
            ("status", "created_at")
        ]


class TestResult(Model):
    """测试结果模型"""
    id = fields.IntField(pk=True)
    result_id = fields.CharField(max_length=100, unique=True, description="结果ID")
    execution = fields.ForeignKeyField("models.TestExecution", related_name="results", description="关联执行记录")
    test_case = fields.ForeignKeyField("models.TestCase", related_name="results", description="关联测试用例")
    status = fields.CharEnumField(ExecutionStatus, description="执行状态")
    start_time = fields.DatetimeField(description="开始时间")
    end_time = fields.DatetimeField(null=True, description="结束时间")
    duration = fields.FloatField(default=0.0, description="执行时长(秒)")
    request_data = fields.JSONField(null=True, description="请求数据")
    response_data = fields.JSONField(null=True, description="响应数据")
    assertion_results = fields.JSONField(default=list, description="断言结果")
    error_message = fields.TextField(default="", description="错误信息")
    logs = fields.JSONField(default=list, description="执行日志")
    screenshots = fields.JSONField(default=list, description="截图路径")
    attachments = fields.JSONField(default=list, description="附件路径")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "test_results"
        table_description = "测试结果表"


class DependencyRelation(Model):
    """依赖关系模型"""
    id = fields.IntField(pk=True)
    dependency_id = fields.CharField(max_length=100, unique=True, description="依赖ID")
    document = fields.ForeignKeyField("models.ApiDocument", related_name="dependencies", description="关联文档")
    source_endpoint = fields.ForeignKeyField("models.ApiEndpoint", related_name="source_dependencies", description="源端点")
    target_endpoint = fields.ForeignKeyField("models.ApiEndpoint", related_name="target_dependencies", description="目标端点")
    dependency_type = fields.CharField(max_length=50, description="依赖类型")
    dependency_data = fields.JSONField(default=dict, description="依赖数据")
    is_required = fields.BooleanField(default=True, description="是否必需")
    description = fields.TextField(default="", description="依赖描述")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "dependency_relations"
        table_description = "依赖关系表"


class AgentLog(Model):
    """智能体日志模型 - 增强版"""
    id = fields.IntField(pk=True)
    log_id = fields.CharField(max_length=100, unique=True, description="日志ID")
    session_id = fields.CharField(max_length=100, description="会话ID", index=True)

    # 智能体信息
    agent_type = fields.CharField(max_length=50, description="智能体类型", index=True)
    agent_name = fields.CharField(max_length=100, description="智能体名称")

    # 日志内容
    log_level = fields.CharField(max_length=20, description="日志级别", index=True)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message = fields.TextField(description="日志消息")  # 修改字段名以匹配数据库
    operation_data = fields.JSONField(default=dict, description="详细日志数据")  # 修改字段名以匹配数据库

    # 上下文信息
    request_id = fields.CharField(max_length=100, null=True, description="请求ID", index=True)
    user_id = fields.CharField(max_length=100, null=True, description="用户ID", index=True)
    operation = fields.CharField(max_length=100, null=True, description="操作类型")

    # 性能指标
    execution_time = fields.FloatField(null=True, description="执行时间(秒)")
    memory_usage = fields.FloatField(null=True, description="内存使用(MB)")
    cpu_usage = fields.FloatField(null=True, description="CPU使用率(%)")

    # 错误信息
    error_code = fields.CharField(max_length=50, null=True, description="错误代码")
    error_type = fields.CharField(max_length=100, null=True, description="错误类型")
    stack_trace = fields.TextField(null=True, description="堆栈跟踪")

    # 标签和分类
    tags = fields.JSONField(default=list, description="标签")
    category = fields.CharField(max_length=50, null=True, description="日志分类")

    # 时间戳
    timestamp = fields.DatetimeField(description="日志时间戳", index=True)
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:
        table = "agent_logs"
        table_description = "智能体日志表"


class SystemMetrics(Model):
    """系统指标模型"""
    id = fields.IntField(pk=True)
    metric_id = fields.CharField(max_length=100, unique=True, description="指标ID")
    metric_type = fields.CharField(max_length=50, description="指标类型")
    metric_name = fields.CharField(max_length=100, description="指标名称")
    metric_value = fields.FloatField(description="指标值")
    metric_data = fields.JSONField(default=dict, description="指标数据")
    tags = fields.JSONField(default=list, description="标签")
    timestamp = fields.DatetimeField(description="时间戳")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:
        table = "system_metrics"
        table_description = "系统指标表"


class LogAnalysis(Model):
    """日志分析结果模型"""
    id = fields.IntField(pk=True)
    analysis_id = fields.CharField(max_length=100, unique=True, description="分析ID")
    session_id = fields.CharField(max_length=100, description="会话ID", index=True)

    # 分析范围
    log_count = fields.IntField(description="分析的日志数量")
    analysis_start_time = fields.DatetimeField(description="分析开始时间")
    analysis_end_time = fields.DatetimeField(description="分析结束时间")

    # 统计结果
    error_rate = fields.FloatField(null=True, description="错误率")
    warning_rate = fields.FloatField(null=True, description="警告率")
    avg_response_time = fields.FloatField(null=True, description="平均响应时间")

    # 异常检测
    anomalies_detected = fields.IntField(default=0, description="检测到的异常数量")
    anomaly_details = fields.JSONField(default=list, description="异常详情")

    # AI分析结果
    ai_summary = fields.TextField(null=True, description="AI生成的摘要")
    recommendations = fields.JSONField(default=list, description="AI建议")
    risk_level = fields.CharField(max_length=20, null=True, description="风险等级")  # LOW, MEDIUM, HIGH, CRITICAL

    # 时间信息
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:
        table = "log_analyses"
        table_description = "日志分析结果表"


class TestScript(BaseModel, TimestampMixin):
    """测试脚本模型 - 优化版：直接关联接口"""
    script_id = fields.CharField(max_length=100, unique=True, description="脚本ID", index=True)

    # 基本信息
    name = fields.CharField(max_length=200, description="脚本名称")
    description = fields.TextField(default="", description="脚本描述")
    file_name = fields.CharField(max_length=255, description="脚本文件名")

    # 关联信息 - 优化：直接关联接口而不是测试用例
    interface = fields.ForeignKeyField("models.ApiInterface", related_name="scripts", description="关联接口", index=True)
    document = fields.ForeignKeyField("models.ApiDocument", related_name="scripts", description="关联文档", index=True)

    # 脚本内容
    content = fields.TextField(description="脚本源代码")
    file_path = fields.CharField(max_length=500, null=True, description="文件路径")

    # 技术信息
    framework = fields.CharField(max_length=50, description="测试框架", index=True)  # pytest, unittest, etc.
    language = fields.CharField(max_length=20, default="python", description="编程语言")
    version = fields.CharField(max_length=20, default="1.0", description="脚本版本")

    # 依赖信息
    dependencies = fields.JSONField(default=list, description="依赖包列表")
    requirements = fields.TextField(null=True, description="requirements.txt内容")

    # 执行配置
    timeout = fields.IntField(default=300, description="超时时间(秒)")
    retry_count = fields.IntField(default=0, description="重试次数")
    parallel_execution = fields.BooleanField(default=False, description="是否支持并行执行")

    # 状态信息
    status = fields.CharField(max_length=20, default="ACTIVE", description="状态", index=True)  # ACTIVE, INACTIVE, DEPRECATED
    is_executable = fields.BooleanField(default=True, description="是否可执行")

    # 统计信息
    execution_count = fields.IntField(default=0, description="执行次数")
    success_count = fields.IntField(default=0, description="成功次数")
    last_execution_time = fields.DatetimeField(null=True, description="最后执行时间")

    # 创建信息
    generated_by = fields.CharField(max_length=50, null=True, description="生成方式")  # AI, MANUAL
    generation_session_id = fields.CharField(max_length=100, null=True, description="生成会话ID", index=True)

    # 质量评估
    code_quality_score = fields.CharField(max_length=5, default="A", description="代码质量评分")  # A, B, C, D, F
    test_coverage_score = fields.FloatField(default=0.0, description="测试覆盖率评分")
    complexity_score = fields.FloatField(default=0.0, description="复杂度评分")

    # 状态管理
    is_active = fields.BooleanField(default=True, description="是否激活")

    class Meta:
        table = "test_scripts"
        table_description = "测试脚本表 - 优化版"
        indexes = [
            ("interface_id", "framework"),
            ("document_id", "status"),
            ("generation_session_id", "created_at"),
            ("is_active", "status")
        ]


class AlertRule(Model):
    """告警规则模型"""
    id = fields.IntField(pk=True)
    rule_id = fields.CharField(max_length=100, unique=True, description="规则ID")

    # 规则信息
    name = fields.CharField(max_length=200, description="规则名称")
    description = fields.TextField(default="", description="规则描述")
    rule_type = fields.CharField(max_length=50, description="规则类型")  # ERROR_RATE, RESPONSE_TIME, MEMORY_USAGE, etc.

    # 条件配置
    threshold_value = fields.FloatField(description="阈值")
    comparison_operator = fields.CharField(max_length=10, description="比较操作符")  # >, <, >=, <=, ==
    time_window = fields.IntField(description="时间窗口(分钟)")

    # 触发配置
    trigger_count = fields.IntField(default=1, description="触发次数")
    severity = fields.CharField(max_length=20, description="严重程度")  # LOW, MEDIUM, HIGH, CRITICAL

    # 状态
    is_active = fields.BooleanField(default=True, description="是否激活")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")
    updated_at = fields.DatetimeField(auto_now=True, description="更新时间")

    class Meta:
        table = "alert_rules"
        table_description = "告警规则表"


class Alert(Model):
    """告警记录模型"""
    id = fields.IntField(pk=True)
    alert_id = fields.CharField(max_length=100, unique=True, description="告警ID")

    # 关联信息
    rule = fields.ForeignKeyField("models.AlertRule", related_name="alerts", description="关联规则")
    session_id = fields.CharField(max_length=100, null=True, description="会话ID", index=True)

    # 告警信息
    title = fields.CharField(max_length=200, description="告警标题")
    message = fields.TextField(description="告警消息")
    severity = fields.CharField(max_length=20, description="严重程度")

    # 状态
    status = fields.CharField(max_length=20, default="OPEN", description="状态")  # OPEN, ACKNOWLEDGED, RESOLVED
    acknowledged_by = fields.CharField(max_length=100, null=True, description="确认人")
    acknowledged_at = fields.DatetimeField(null=True, description="确认时间")
    resolved_at = fields.DatetimeField(null=True, description="解决时间")

    # 时间信息
    triggered_at = fields.DatetimeField(auto_now_add=True, description="触发时间")
    created_at = fields.DatetimeField(auto_now_add=True, description="创建时间")

    class Meta:
        table = "alerts"
        table_description = "告警记录表"


class WorkflowSession(BaseModel, TimestampMixin):
    """工作流会话模型"""
    session_id = fields.CharField(max_length=100, unique=True, description="会话ID", index=True)
    workflow_type = fields.CharField(max_length=50, description="工作流类型", index=True)
    status = fields.CharEnumField(SessionStatus, default=SessionStatus.CREATED, description="会话状态", index=True)
    current_step = fields.CharField(max_length=100, default="", description="当前步骤")
    config = fields.JSONField(default=dict, description="配置信息")
    metadata = fields.JSONField(default=dict, description="元数据")
    start_time = fields.DatetimeField(null=True, description="开始时间")
    end_time = fields.DatetimeField(null=True, description="结束时间")
    duration = fields.FloatField(default=0.0, description="持续时间")
    error_message = fields.TextField(default="", description="错误信息")

    class Meta:
        table = "workflow_sessions"
        table_description = "工作流会话表"


# 新增表结构

class ApiAnalysisResult(BaseModel, TimestampMixin):
    """API分析结果模型"""
    analysis_id = fields.CharField(max_length=100, unique=True, description="分析ID", index=True)
    document = fields.ForeignKeyField("models.ApiDocument", related_name="analysis_results", description="关联文档")
    session_id = fields.CharField(max_length=100, description="会话ID", index=True)

    # 分析配置
    analysis_config = fields.JSONField(default=dict, description="分析配置")
    analysis_type = fields.CharField(max_length=50, description="分析类型")  # FULL, SECURITY, PERFORMANCE, DEPENDENCY

    # 分析结果
    summary = fields.JSONField(default=dict, description="分析摘要")
    categories = fields.JSONField(default=list, description="接口分类")
    dependencies = fields.JSONField(default=list, description="依赖关系")
    security_assessment = fields.JSONField(default=dict, description="安全评估")
    performance_analysis = fields.JSONField(default=dict, description="性能分析")

    # 统计信息
    total_endpoints = fields.IntField(default=0, description="总接口数")
    get_count = fields.IntField(default=0, description="GET接口数")
    post_count = fields.IntField(default=0, description="POST接口数")
    put_count = fields.IntField(default=0, description="PUT接口数")
    delete_count = fields.IntField(default=0, description="DELETE接口数")
    dependencies_count = fields.IntField(default=0, description="依赖关系数")

    # 质量评分
    overall_score = fields.FloatField(default=0.0, description="总体评分")
    security_score = fields.FloatField(default=0.0, description="安全评分")
    complexity_score = fields.FloatField(default=0.0, description="复杂度评分")
    maintainability_score = fields.FloatField(default=0.0, description="可维护性评分")

    # 处理信息
    processing_time = fields.FloatField(default=0.0, description="处理时间(秒)")
    status = fields.CharEnumField(SessionStatus, default=SessionStatus.CREATED, description="分析状态")
    error_message = fields.TextField(default="", description="错误信息")

    class Meta:
        table = "api_analysis_results"
        table_description = "API分析结果表"
        indexes = [
            ("document_id", "analysis_type"),
            ("session_id", "status"),
            ("overall_score", "created_at")
        ]


class ScriptGenerationTask(BaseModel, TimestampMixin):
    """脚本生成任务模型"""
    task_id = fields.CharField(max_length=100, unique=True, description="任务ID", index=True)
    session_id = fields.CharField(max_length=100, description="会话ID", index=True)
    interface_id = fields.CharField(max_length=100, description="接口ID", index=True)

    # 任务状态
    status = fields.CharEnumField(SessionStatus, default=SessionStatus.CREATED, description="任务状态")
    progress = fields.FloatField(default=0.0, description="进度百分比")
    current_step = fields.CharField(max_length=100, default="", description="当前步骤")

    # 处理信息
    start_time = fields.DatetimeField(null=True, description="开始时间")
    end_time = fields.DatetimeField(null=True, description="结束时间")
    processing_time = fields.FloatField(default=0.0, description="处理时间(秒)")
    error_message = fields.TextField(default="", description="错误信息")

    # 结果信息
    generated_files_count = fields.IntField(default=0, description="生成文件数")
    result_data = fields.JSONField(default=dict, description="结果数据")

    class Meta:
        table = "script_generation_tasks"
        table_description = "脚本生成任务表"
        indexes = [
            ("interface_id", "status"),
            ("session_id", "status"),
            ("status", "created_at")
        ]


class TestGenerationTask(BaseModel, TimestampMixin):
    """测试生成任务模型"""
    task_id = fields.CharField(max_length=100, unique=True, description="任务ID", index=True)
    document = fields.ForeignKeyField("models.ApiDocument", related_name="generation_tasks", description="关联文档")
    analysis_result = fields.ForeignKeyField("models.ApiAnalysisResult", related_name="generation_tasks", null=True, description="关联分析结果")
    session_id = fields.CharField(max_length=100, description="会话ID", index=True)

    # 生成配置
    framework = fields.CharField(max_length=50, default="pytest", description="测试框架")
    test_types = fields.JSONField(default=list, description="测试类型")
    test_level = fields.CharField(max_length=20, default="integration", description="测试级别")
    generate_options = fields.JSONField(default=list, description="生成选项")

    # 生成结果
    generated_test_cases = fields.JSONField(default=list, description="生成的测试用例")
    generated_scripts = fields.JSONField(default=list, description="生成的脚本")
    generation_summary = fields.JSONField(default=dict, description="生成摘要")

    # 统计信息
    total_test_files = fields.IntField(default=0, description="测试文件数")
    total_test_cases = fields.IntField(default=0, description="测试用例数")
    total_assertions = fields.IntField(default=0, description="断言数")
    total_mock_data = fields.IntField(default=0, description="模拟数据数")

    # 质量评估
    coverage_score = fields.FloatField(default=0.0, description="覆盖率评分")
    completeness_score = fields.FloatField(default=0.0, description="完整性评分")
    code_quality_score = fields.CharField(max_length=5, default="A", description="代码质量评分")

    # 处理信息
    processing_time = fields.FloatField(default=0.0, description="处理时间(秒)")
    status = fields.CharEnumField(SessionStatus, default=SessionStatus.CREATED, description="生成状态")
    error_message = fields.TextField(default="", description="错误信息")

    class Meta:
        table = "test_generation_tasks"
        table_description = "测试生成任务表"
        indexes = [
            ("document_id", "framework"),
            ("session_id", "status"),
            ("created_at", "status")
        ]


class TestExecutionSession(BaseModel, TimestampMixin):
    """测试执行会话模型"""
    execution_session_id = fields.CharField(max_length=100, unique=True, description="执行会话ID", index=True)
    document = fields.ForeignKeyField("models.ApiDocument", related_name="execution_sessions", description="关联文档")
    generation_task = fields.ForeignKeyField("models.TestGenerationTask", related_name="execution_sessions", null=True, description="关联生成任务")

    # 执行配置
    environment = fields.CharEnumField(EnvironmentType, default=EnvironmentType.TEST, description="执行环境")
    parallel_execution = fields.BooleanField(default=False, description="是否并行执行")
    max_workers = fields.IntField(default=1, description="最大工作线程数")
    timeout = fields.IntField(default=300, description="超时时间(秒)")

    # 执行状态
    status = fields.CharEnumField(ExecutionStatus, default=ExecutionStatus.PENDING, description="执行状态")
    current_test = fields.CharField(max_length=200, default="", description="当前测试")
    progress = fields.FloatField(default=0.0, description="执行进度")

    # 统计信息
    total_tests = fields.IntField(default=0, description="总测试数")
    executed_tests = fields.IntField(default=0, description="已执行测试数")
    passed_tests = fields.IntField(default=0, description="通过测试数")
    failed_tests = fields.IntField(default=0, description="失败测试数")
    skipped_tests = fields.IntField(default=0, description="跳过测试数")

    # 性能指标
    total_execution_time = fields.FloatField(default=0.0, description="总执行时间(秒)")
    avg_response_time = fields.FloatField(default=0.0, description="平均响应时间(毫秒)")
    success_rate = fields.FloatField(default=0.0, description="成功率")

    # 报告文件
    report_formats = fields.JSONField(default=list, description="报告格式")
    report_files = fields.JSONField(default=list, description="报告文件路径")
    log_files = fields.JSONField(default=list, description="日志文件路径")

    # 时间信息
    start_time = fields.DatetimeField(null=True, description="开始时间")
    end_time = fields.DatetimeField(null=True, description="结束时间")

    # 错误信息
    error_message = fields.TextField(default="", description="错误信息")

    class Meta:
        table = "test_execution_sessions"
        table_description = "测试执行会话表"
        indexes = [
            ("document_id", "environment"),
            ("status", "created_at"),
            ("success_rate", "total_execution_time")
        ]


class TestReport(BaseModel, TimestampMixin):
    """测试报告模型"""
    report_id = fields.CharField(max_length=100, unique=True, description="报告ID", index=True)
    execution_session = fields.ForeignKeyField("models.TestExecutionSession", related_name="reports", description="关联执行会话")
    document = fields.ForeignKeyField("models.ApiDocument", related_name="reports", description="关联文档")

    # 报告基本信息
    report_name = fields.CharField(max_length=200, description="报告名称")
    report_type = fields.CharField(max_length=50, description="报告类型")  # SUMMARY, DETAILED, PERFORMANCE
    report_format = fields.CharEnumField(ReportFormat, description="报告格式")

    # 报告内容
    summary = fields.JSONField(default=dict, description="执行摘要")
    detailed_results = fields.JSONField(default=list, description="详细结果")
    performance_metrics = fields.JSONField(default=dict, description="性能指标")
    error_analysis = fields.JSONField(default=list, description="错误分析")

    # 统计数据
    total_tests = fields.IntField(default=0, description="总测试数")
    passed_tests = fields.IntField(default=0, description="通过测试数")
    failed_tests = fields.IntField(default=0, description="失败测试数")
    success_rate = fields.FloatField(default=0.0, description="成功率")
    execution_time = fields.FloatField(default=0.0, description="执行时间(秒)")

    # 文件信息
    file_path = fields.CharField(max_length=500, null=True, description="报告文件路径")
    file_size = fields.BigIntField(default=0, description="文件大小(字节)")

    # 状态
    generation_status = fields.CharField(max_length=20, default="COMPLETED", description="生成状态")
    is_public = fields.BooleanField(default=False, description="是否公开")

    class Meta:
        table = "test_reports"
        table_description = "测试报告表"
        indexes = [
            ("execution_session_id", "report_format"),
            ("document_id", "created_at"),
            ("success_rate", "execution_time")
        ]


class AgentMetrics(BaseModel, TimestampMixin):
    """智能体指标模型"""
    metric_id = fields.CharField(max_length=100, unique=True, description="指标ID", index=True)
    agent_type = fields.CharField(max_length=50, description="智能体类型", index=True)
    agent_name = fields.CharField(max_length=100, description="智能体名称")

    # 性能指标
    cpu_usage = fields.FloatField(default=0.0, description="CPU使用率(%)")
    memory_usage = fields.FloatField(default=0.0, description="内存使用(MB)")
    disk_usage = fields.FloatField(default=0.0, description="磁盘使用(MB)")
    network_io = fields.FloatField(default=0.0, description="网络IO(KB/s)")

    # 业务指标
    requests_count = fields.IntField(default=0, description="请求数量")
    success_count = fields.IntField(default=0, description="成功数量")
    error_count = fields.IntField(default=0, description="错误数量")
    avg_response_time = fields.FloatField(default=0.0, description="平均响应时间(毫秒)")

    # 状态信息
    status = fields.CharField(max_length=20, default="ONLINE", description="状态")  # ONLINE, OFFLINE, ERROR
    last_heartbeat = fields.DatetimeField(null=True, description="最后心跳时间")
    uptime = fields.FloatField(default=0.0, description="运行时间(小时)")

    # 时间戳
    timestamp = fields.DatetimeField(description="指标时间戳", index=True)

    class Meta:
        table = "agent_metrics"
        table_description = "智能体指标表"
        indexes = [
            ("agent_type", "timestamp"),
            ("status", "last_heartbeat"),
            ("created_at", "agent_type")
        ]


class UserSession(BaseModel, TimestampMixin):
    """用户会话模型"""
    session_id = fields.CharField(max_length=100, unique=True, description="会话ID", index=True)
    user_id = fields.CharField(max_length=100, description="用户ID", index=True)
    user_name = fields.CharField(max_length=100, null=True, description="用户名")

    # 会话信息
    ip_address = fields.CharField(max_length=45, null=True, description="IP地址")
    user_agent = fields.TextField(null=True, description="用户代理")
    login_time = fields.DatetimeField(description="登录时间")
    last_activity = fields.DatetimeField(description="最后活动时间")

    # 活动统计
    documents_uploaded = fields.IntField(default=0, description="上传文档数")
    analyses_performed = fields.IntField(default=0, description="执行分析数")
    tests_generated = fields.IntField(default=0, description="生成测试数")
    tests_executed = fields.IntField(default=0, description="执行测试数")

    # 状态
    is_active = fields.BooleanField(default=True, description="是否活跃")
    logout_time = fields.DatetimeField(null=True, description="登出时间")

    class Meta:
        table = "user_sessions"
        table_description = "用户会话表"
        indexes = [
            ("user_id", "login_time"),
            ("session_id", "is_active"),
            ("last_activity", "is_active")
        ]


class SystemConfiguration(BaseModel, TimestampMixin):
    """系统配置模型"""
    config_id = fields.CharField(max_length=100, unique=True, description="配置ID", index=True)
    config_key = fields.CharField(max_length=100, description="配置键", index=True)
    config_value = fields.TextField(description="配置值")
    config_type = fields.CharField(max_length=20, description="配置类型")  # STRING, INTEGER, FLOAT, BOOLEAN, JSON

    # 分类和描述
    category = fields.CharField(max_length=50, description="配置分类")
    description = fields.TextField(default="", description="配置描述")

    # 验证规则
    validation_rules = fields.JSONField(default=dict, description="验证规则")
    default_value = fields.TextField(null=True, description="默认值")

    # 状态
    is_active = fields.BooleanField(default=True, description="是否激活")
    is_system = fields.BooleanField(default=False, description="是否系统配置")

    # 修改信息
    modified_by = fields.CharField(max_length=100, null=True, description="修改人")

    class Meta:
        table = "system_configurations"
        table_description = "系统配置表"
        indexes = [
            ("config_key", "is_active"),
            ("category", "is_system"),
            ("modified_by", "updated_at")
        ]


class OperationLog(BaseModel, TimestampMixin):
    """操作日志模型"""
    log_id = fields.CharField(max_length=100, unique=True, description="日志ID", index=True)
    user_id = fields.CharField(max_length=100, null=True, description="用户ID", index=True)
    session_id = fields.CharField(max_length=100, null=True, description="会话ID", index=True)

    # 操作信息
    operation_type = fields.CharField(max_length=50, description="操作类型", index=True)  # UPLOAD, ANALYZE, GENERATE, EXECUTE, DELETE
    operation_target = fields.CharField(max_length=100, description="操作目标")  # DOCUMENT, ENDPOINT, TEST_CASE, etc.
    operation_target_id = fields.CharField(max_length=100, null=True, description="目标ID")

    # 操作详情
    operation_description = fields.TextField(description="操作描述")
    operation_data = fields.JSONField(default=dict, description="操作数据")

    # 结果信息
    result_status = fields.CharField(max_length=20, description="结果状态")  # SUCCESS, FAILED, PARTIAL
    result_message = fields.TextField(default="", description="结果消息")

    # 环境信息
    ip_address = fields.CharField(max_length=45, null=True, description="IP地址")
    user_agent = fields.TextField(null=True, description="用户代理")

    # 性能信息
    execution_time = fields.FloatField(default=0.0, description="执行时间(秒)")

    class Meta:
        table = "operation_logs"
        table_description = "操作日志表"
        indexes = [
            ("user_id", "operation_type"),
            ("session_id", "created_at"),
            ("operation_type", "result_status"),
            ("created_at", "operation_type")
        ]


# 新增接口管理相关模型

class ApiInterface(BaseModel, TimestampMixin):
    """接口信息表 - 存储解析后的接口详细信息"""
    interface_id = fields.CharField(max_length=100, unique=True, description="接口ID", index=True)
    document = fields.ForeignKeyField("models.ApiDocument", related_name="interfaces", description="关联文档", index=True)
    endpoint_id = fields.CharField(max_length=100, null=True, description="原始端点ID", index=True)

    # 基本信息
    name = fields.CharField(max_length=200, description="接口名称")
    path = fields.CharField(max_length=500, description="接口路径", index=True)
    method = fields.CharEnumField(HttpMethod, description="HTTP方法", index=True)
    summary = fields.TextField(default="", description="接口摘要")
    description = fields.TextField(default="", description="接口详细描述")

    # API信息
    api_title = fields.CharField(max_length=200, null=True, description="API标题")
    api_version = fields.CharField(max_length=50, null=True, description="API版本")
    base_url = fields.CharField(max_length=500, null=True, description="基础URL")

    # 分类和标签
    tags = fields.JSONField(default=list, description="标签列表")
    category = fields.CharField(max_length=100, null=True, description="接口分类")

    # 认证和安全
    auth_required = fields.BooleanField(default=False, description="是否需要认证")
    auth_type = fields.CharField(max_length=50, null=True, description="认证类型")
    security_schemes = fields.JSONField(default=dict, description="安全方案")

    # 状态和质量
    is_deprecated = fields.BooleanField(default=False, description="是否已废弃")
    confidence_score = fields.FloatField(default=0.0, description="解析置信度")
    complexity_score = fields.FloatField(default=0.0, description="复杂度评分")

    # 测试统计
    test_script_count = fields.IntField(default=0, description="测试脚本数量")
    last_script_generation_time = fields.DatetimeField(null=True, description="最后脚本生成时间")

    # 扩展信息
    extended_info = fields.JSONField(default=dict, description="扩展信息")
    raw_data = fields.JSONField(default=dict, description="原始解析数据")

    # 状态管理
    is_active = fields.BooleanField(default=True, description="是否激活")

    class Meta:
        table = "api_interfaces"
        table_description = "接口信息表"
        indexes = [
            ("document_id", "method", "path"),
            ("name", "is_active"),
            ("category", "tags"),
            ("confidence_score", "complexity_score")
        ]


class ApiParameter(BaseModel, TimestampMixin):
    """接口参数表"""
    parameter_id = fields.CharField(max_length=100, unique=True, description="参数ID", index=True)
    interface = fields.ForeignKeyField("models.ApiInterface", related_name="parameters", description="关联接口", index=True)

    # 参数基本信息
    name = fields.CharField(max_length=100, description="参数名称", index=True)
    location = fields.CharField(max_length=20, description="参数位置")  # header, query, path, body, form
    data_type = fields.CharField(max_length=50, description="数据类型")  # string, integer, boolean, object, array
    required = fields.BooleanField(default=False, description="是否必需")

    # 参数描述
    description = fields.TextField(default="", description="参数描述")
    example = fields.TextField(null=True, description="示例值")
    default_value = fields.TextField(null=True, description="默认值")

    # 约束条件
    constraints = fields.JSONField(default=dict, description="约束条件")  # min, max, pattern, enum等

    # 嵌套结构（用于object类型）
    schema = fields.JSONField(null=True, description="参数结构定义")

    class Meta:
        table = "api_parameters"
        table_description = "接口参数表"
        indexes = [
            ("interface_id", "location"),
            ("name", "required"),
            ("data_type", "location")
        ]


class ApiResponse(BaseModel, TimestampMixin):
    """接口响应表"""
    response_id = fields.CharField(max_length=100, unique=True, description="响应ID", index=True)
    interface = fields.ForeignKeyField("models.ApiInterface", related_name="responses", description="关联接口", index=True)

    # 响应基本信息
    status_code = fields.CharField(max_length=10, description="状态码", index=True)  # 200, 400, 500等
    description = fields.TextField(default="", description="响应描述")
    content_type = fields.CharField(max_length=100, default="application/json", description="内容类型")

    # 响应结构
    response_schema = fields.JSONField(null=True, description="响应结构定义")
    example = fields.JSONField(null=True, description="响应示例")

    # 响应头
    headers = fields.JSONField(default=dict, description="响应头定义")

    class Meta:
        table = "api_responses"
        table_description = "接口响应表"
        indexes = [
            ("interface_id", "status_code"),
            ("status_code", "content_type")
        ]

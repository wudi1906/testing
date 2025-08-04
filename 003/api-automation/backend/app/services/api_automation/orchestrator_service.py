"""
接口自动化智能体编排服务 - 重新设计版本
负责协调各个智能体的工作流程，使用新的数据模型
"""
from typing import Dict, List, Any, Optional
from datetime import datetime

from autogen_core import SingleThreadedAgentRuntime, TopicId
# from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime  # 临时注释掉，避免grpc版本冲突
from loguru import logger

from app.core.agents.collector import StreamResponseCollector
from app.core.types import AgentPlatform, TopicTypes
from app.core.enums import LogLevel
from app.agents.factory import agent_factory

# 导入重新设计的数据模型
from app.agents.api_automation.schemas import (
    DocumentParseInput, DocumentFormat,
    AnalysisInput, TestCaseGenerationInput, ScriptGenerationInput
)

# 导入基础消息类型
from app.core.messages.base import BaseMessage
from pydantic import Field


# 简单的日志记录消息类型
class LogRecordRequest(BaseMessage):
    """日志记录请求"""
    agent_name: str = Field(..., description="智能体名称")
    log_level: str = Field(..., description="日志级别")
    log_message: str = Field(..., description="日志消息")
    log_data: Dict[str, Any] = Field(default_factory=dict, description="日志数据")
    execution_context: Dict[str, Any] = Field(default_factory=dict, description="执行上下文")


class ApiAutomationOrchestrator:
    """
    接口自动化智能体编排器 - 重新设计版本

    负责协调以下智能体的工作流程：
    1. API文档解析智能体 - 解析API文档，输出 DocumentParseOutput
    2. 接口分析智能体 - 分析接口依赖关系，输出 AnalysisOutput
    3. 测试用例生成智能体 - 生成测试用例，输出 TestCaseGenerationOutput
    4. 脚本生成智能体 - 生成pytest测试脚本，输出 ScriptGenerationOutput
    5. 日志记录智能体 - 记录执行日志

    数据流转：DocumentParseInput → AnalysisInput → TestCaseGenerationInput → ScriptGenerationInput
    """

    def __init__(self, collector: Optional[StreamResponseCollector] = None):
        """
        初始化接口自动化编排器
        
        Args:
            collector: 可选的StreamResponseCollector用于捕获智能体响应
        """
        self.response_collector = collector or StreamResponseCollector(
            platform=AgentPlatform.API_AUTOMATION
        )
        self.runtime: Optional[SingleThreadedAgentRuntime] = None
        self.agent_factory = agent_factory
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # 编排器性能指标
        self.orchestrator_metrics = {
            "total_workflows": 0,
            "successful_workflows": 0,
            "failed_workflows": 0,
            "active_sessions": 0
        }
        
        logger.info("接口自动化智能体编排器初始化完成")

    async def initialize(self, **agent_kwargs) -> None:
        """
        初始化编排器和智能体
        
        Args:
            **agent_kwargs: 智能体初始化参数
        """
        try:
            logger.info("🚀 初始化接口自动化智能体编排器...")
            
            if self.runtime is None:
                # 如果是分布式运行时
                # self.runtime = GrpcWorkerAgentRuntime(host_address="localhost:50051")
                # 创建运行时

                self.runtime = SingleThreadedAgentRuntime()
                
                # 注册智能体到运行时
                await self.agent_factory.register_agents_to_runtime(self.runtime)
                
                # 设置响应收集器
                await self.agent_factory.register_stream_collector(
                    runtime=self.runtime,
                    collector=self.response_collector
                )
                
                # 启动运行时
                self.runtime.start()
                
                logger.info("✅ 接口自动化智能体编排器初始化完成")
                
        except Exception as e:
            logger.error(f"❌ 接口自动化智能体编排器初始化失败: {str(e)}")
            raise

    async def process_api_document(
        self, 
        session_id: str,
        file_path: str,
        file_name: str,
        file_content: Optional[str] = None,
        doc_format: str = "auto",
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理API文档的完整流程
        
        Args:
            session_id: 会话ID
            file_path: 文件路径
            file_name: 文件名
            file_content: 文件内容（可选）
            doc_format: 文档格式
            config: 配置参数
            
        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            self.orchestrator_metrics["total_workflows"] += 1
            self.orchestrator_metrics["active_sessions"] += 1
            
            # 记录会话信息
            self.active_sessions[session_id] = {
                "start_time": datetime.now(),
                "status": "processing",
                "current_step": "document_parsing",
                "file_name": file_name,
                "config": config or {}
            }
            
            logger.info(f"开始处理API文档: {file_name} (会话: {session_id})")
            
            # 记录开始日志
            await self._log_workflow_event(
                session_id, 
                "workflow_started", 
                f"开始处理API文档: {file_name}",
                {"file_path": file_path, "doc_format": doc_format}
            )
            
            # 步骤1: 解析API文档
            await self._parse_api_document(
                session_id, file_path, file_name, file_content, doc_format, config
            )
            
            # 更新会话状态
            self.active_sessions[session_id]["current_step"] = "completed"
            self.active_sessions[session_id]["status"] = "completed"
            self.active_sessions[session_id]["end_time"] = datetime.now()
            
            self.orchestrator_metrics["successful_workflows"] += 1
            self.orchestrator_metrics["active_sessions"] -= 1
            
            # 记录完成日志
            await self._log_workflow_event(
                session_id,
                "workflow_completed",
                f"API文档处理完成: {file_name}",
                {"duration": (datetime.now() - self.active_sessions[session_id]["start_time"]).total_seconds()}
            )
            
            return {
                "success": True,
                "session_id": session_id,
                "message": "API文档处理完成",
                "session_info": self.active_sessions[session_id],
                "note": "完整的工作流程包括：文档解析 → 接口分析 → 测试用例生成 → 脚本生成"
            }
            
        except Exception as e:
            self.orchestrator_metrics["failed_workflows"] += 1
            self.orchestrator_metrics["active_sessions"] -= 1
            
            # 更新会话状态
            if session_id in self.active_sessions:
                self.active_sessions[session_id]["status"] = "failed"
                self.active_sessions[session_id]["error"] = str(e)
                self.active_sessions[session_id]["end_time"] = datetime.now()
            
            # 记录错误日志
            await self._log_workflow_event(
                session_id,
                "workflow_failed",
                f"API文档处理失败: {str(e)}",
                {"error": str(e), "file_name": file_name}
            )
            
            logger.error(f"处理API文档失败: {str(e)}")
            raise

    async def _parse_api_document(
        self,
        session_id: str,
        file_path: str,
        file_name: str,
        file_content: Optional[str],
        doc_format: str,
        config: Optional[Dict[str, Any]]
    ) -> None:
        """发送API文档解析请求 - 使用新的数据模型"""
        try:
            # 检测文档格式
            detected_format = DocumentFormat.AUTO
            if doc_format.lower() in [fmt.value for fmt in DocumentFormat]:
                detected_format = DocumentFormat(doc_format.lower())

            # 构建解析请求 - 使用新的数据模型
            parse_request = DocumentParseInput(
                session_id=session_id,
                file_path=file_path,
                file_name=file_name,
                file_content=file_content,
                doc_format=detected_format,
                parse_options=config or {}
            )

            # 发送到API文档解析智能体
            await self.runtime.publish_message(
                parse_request,
                topic_id=TopicId(type=TopicTypes.API_DOC_PARSER.value, source="orchestrator")
            )

            logger.info(f"已发送API文档解析请求: {session_id}")
            logger.debug(f"解析请求详情: 文件={file_name}, 格式={detected_format.value}")

        except Exception as e:
            logger.error(f"发送API文档解析请求失败: {str(e)}")
            raise

    async def execute_test_suite(
        self,
        session_id: str,
        script_files: List[str],
        test_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行测试套件 - 适配新的数据流

        注意：在新的架构中，测试脚本是由脚本生成智能体自动生成的，
        这个方法主要用于手动执行已生成的测试脚本。

        Args:
            session_id: 会话ID
            script_files: 测试脚本文件列表
            test_config: 测试配置

        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            logger.info(f"开始执行测试套件: {session_id}")

            # 在新架构中，我们可能需要创建一个简化的执行请求
            # 或者直接调用测试执行器
            execution_config = test_config or {
                "framework": "pytest",
                "parallel": False,
                "max_workers": 1,
                "timeout": 300,
                "report_formats": ["allure", "html"]
            }

            # 记录执行日志
            await self._log_workflow_event(
                session_id,
                "test_execution_started",
                f"开始执行测试套件，包含 {len(script_files)} 个脚本文件",
                {"script_files": script_files, "config": execution_config}
            )

            # TODO: 在新架构中，可能需要重新设计测试执行的消息模型
            # 目前先返回成功状态，实际执行逻辑需要根据新的数据模型调整
            logger.warning("测试执行功能需要根据新的数据模型重新实现")

            return {
                "success": True,
                "session_id": session_id,
                "message": "测试执行功能正在适配新的数据模型",
                "script_count": len(script_files),
                "note": "此功能需要重新实现以适配新的智能体架构"
            }

        except Exception as e:
            logger.error(f"执行测试套件失败: {str(e)}")
            await self._log_workflow_event(
                session_id,
                "test_execution_failed",
                f"测试执行失败: {str(e)}",
                {"error": str(e)}
            )
            raise

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        获取会话状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            Dict[str, Any]: 会话状态信息
        """
        try:
            if session_id not in self.active_sessions:
                return {
                    "success": False,
                    "message": "会话不存在",
                    "session_id": session_id
                }
            
            session_info = self.active_sessions[session_id].copy()
            
            # 添加运行时间
            if "start_time" in session_info:
                if session_info.get("status") == "processing":
                    session_info["running_time"] = (
                        datetime.now() - session_info["start_time"]
                    ).total_seconds()
                elif "end_time" in session_info:
                    session_info["total_time"] = (
                        session_info["end_time"] - session_info["start_time"]
                    ).total_seconds()
            
            return {
                "success": True,
                "session_id": session_id,
                "session_info": session_info
            }
            
        except Exception as e:
            logger.error(f"获取会话状态失败: {str(e)}")
            return {
                "success": False,
                "message": str(e),
                "session_id": session_id
            }

    async def get_orchestrator_metrics(self) -> Dict[str, Any]:
        """获取编排器指标"""
        try:
            # 获取智能体健康状态
            agent_health = await self.agent_factory.health_check_all()
            
            # 获取性能摘要
            performance_summary = await self.agent_factory.get_performance_summary()
            
            return {
                "orchestrator_metrics": self.orchestrator_metrics,
                "agent_health": agent_health,
                "performance_summary": performance_summary,
                "active_sessions_count": len(self.active_sessions),
                "active_sessions": list(self.active_sessions.keys()),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取编排器指标失败: {str(e)}")
            return {"error": str(e)}

    async def _log_workflow_event(
        self,
        session_id: str,
        event_type: str,
        message: str,
        data: Dict[str, Any]
    ) -> None:
        """记录工作流事件日志"""
        try:
            # 使用loguru直接记录日志，避免依赖日志记录智能体
            logger.info(
                f"[{session_id}] {event_type}: {message}",
                extra={
                    "session_id": session_id,
                    "event_type": event_type,
                    "event_data": data,
                    "orchestrator": "api_automation"
                }
            )

            # 如果需要发送到日志记录智能体，可以尝试发送（但不强制要求成功）
            try:
                if self.runtime and hasattr(TopicTypes, 'LOG_RECORDER'):
                    log_request = LogRecordRequest(
                        session_id=session_id,
                        agent_name="ApiAutomationOrchestrator",
                        log_level="INFO",
                        log_message=message,
                        log_data=data,
                        execution_context={
                            "event_type": event_type,
                            "orchestrator": "api_automation"
                        }
                    )

                    await self.runtime.publish_message(
                        log_request,
                        topic_id=TopicId(type=TopicTypes.LOG_RECORDER.value, source="orchestrator")
                    )
            except Exception as inner_e:
                # 日志记录智能体不可用时，不影响主流程
                logger.debug(f"发送到日志记录智能体失败（非关键错误）: {str(inner_e)}")

        except Exception as e:
            logger.error(f"记录工作流事件失败: {str(e)}")

    async def cleanup(self) -> None:
        """清理编排器资源"""
        try:
            # 清理智能体
            await self.agent_factory.cleanup_all()
            
            # 清理响应收集器
            if self.response_collector:
                self.response_collector.cleanup()
            
            # 停止运行时
            if self.runtime:
                self.runtime.stop()
            
            # 清理会话
            self.active_sessions.clear()
            
            logger.info("接口自动化编排器资源清理完成")
            
        except Exception as e:
            logger.error(f"清理编排器资源失败: {str(e)}")

    def get_factory_status(self) -> Dict[str, Any]:
        """获取工厂状态"""
        return self.agent_factory.get_factory_status()

    async def run_complete_workflow(
        self,
        session_id: str,
        file_path: str,
        file_name: str,
        file_content: Optional[str] = None,
        doc_format: str = "auto",
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        运行完整的API自动化工作流程

        这个方法启动完整的工作流：
        文档解析 → 接口分析 → 测试用例生成 → 脚本生成

        Args:
            session_id: 会话ID
            file_path: 文件路径
            file_name: 文件名
            file_content: 文件内容（可选）
            doc_format: 文档格式
            config: 配置参数

        Returns:
            Dict[str, Any]: 工作流启动结果
        """
        try:
            logger.info(f"🚀 启动完整的API自动化工作流: {file_name}")

            # 记录工作流开始
            self.active_sessions[session_id] = {
                "start_time": datetime.now(),
                "status": "running_complete_workflow",
                "current_step": "document_parsing",
                "file_name": file_name,
                "config": config or {},
                "workflow_type": "complete"
            }

            # 启动文档解析（这将触发整个工作流链）
            await self._parse_api_document(
                session_id, file_path, file_name, file_content, doc_format, config
            )

            # 记录工作流启动日志
            await self._log_workflow_event(
                session_id,
                "complete_workflow_started",
                f"完整工作流已启动: {file_name}",
                {
                    "file_path": file_path,
                    "doc_format": doc_format,
                    "workflow_steps": [
                        "document_parsing",
                        "api_analysis",
                        "test_case_generation",
                        "script_generation"
                    ]
                }
            )

            return {
                "success": True,
                "session_id": session_id,
                "message": "完整的API自动化工作流已启动",
                "workflow_steps": [
                    "1. 文档解析 - 提取API端点信息",
                    "2. 接口分析 - 分析依赖关系和执行顺序",
                    "3. 测试用例生成 - 生成全面的测试用例",
                    "4. 脚本生成 - 生成可执行的pytest脚本"
                ],
                "note": "工作流将自动在智能体之间传递数据，请通过 get_session_status 监控进度"
            }

        except Exception as e:
            logger.error(f"启动完整工作流失败: {str(e)}")
            await self._log_workflow_event(
                session_id,
                "complete_workflow_failed",
                f"完整工作流启动失败: {str(e)}",
                {"error": str(e)}
            )
            raise

    async def generate_interface_script(
        self,
        session_id: str,
        interface_obj,  # 直接传递数据库对象
        document_obj    # 直接传递文档对象
    ) -> Dict[str, Any]:
        """
        为单个接口生成测试脚本

        Args:
            session_id: 会话ID
            interface_obj: 接口数据库对象 (ApiInterface)
            document_obj: 文档数据库对象 (ApiDocument)

        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            # 从数据库对象中提取基本信息
            interface_id = interface_obj.interface_id
            document_id = document_obj.doc_id

            logger.info(f"🚀 开始为接口生成脚本: interface_id={interface_id}")

            # 记录会话信息
            self.active_sessions[session_id] = {
                "session_id": session_id,
                "document_id": document_id,
                "interface_id": interface_id,
                "workflow_type": "interface_script_generation",
                "status": "processing",
                "current_step": "analysis",
                "started_at": datetime.now().isoformat(),
                "interface_name": interface_obj.name,
                "interface_path": f"{interface_obj.method} {interface_obj.path}"
            }

            # 更新指标
            self.orchestrator_metrics["total_workflows"] += 1
            self.orchestrator_metrics["active_sessions"] += 1

            # 记录工作流事件
            await self._log_workflow_event(
                session_id,
                "interface_script_generation_started",
                f"开始为接口 {interface_id} 生成脚本",
                {"interface_id": interface_id, "document_id": document_id}
            )

            # 构建分析输入
            from app.agents.api_automation.schemas import (
                AnalysisInput, ParsedApiInfo, ParsedEndpoint,
                ApiParameter, ApiResponse, ParameterLocation, DataType
            )

            # 直接从文档对象构建API信息 - 只使用ParsedApiInfo中实际存在的字段
            parsed_api_info = ParsedApiInfo(
                title=document_obj.api_info.get("title", "API") if document_obj.api_info else "API",
                version=document_obj.api_info.get("version", "1.0") if document_obj.api_info else "1.0",
                description=document_obj.api_info.get("description", "") if document_obj.api_info else "",
                base_url=document_obj.api_info.get("base_url", "") if document_obj.api_info else "",
                contact=document_obj.api_info.get("contact", {}) if document_obj.api_info else {},
                license=document_obj.api_info.get("license", {}) if document_obj.api_info else {}
            )

            # 直接从接口对象构建参数信息
            parameters = []
            for param in interface_obj.parameters:
                # 构建参数约束信息
                constraints = {}
                if hasattr(param, 'constraints') and param.constraints:
                    constraints = param.constraints
                else:
                    # 从其他字段构建约束信息
                    if hasattr(param, 'format') and param.format:
                        constraints['format'] = param.format
                    if hasattr(param, 'pattern') and param.pattern:
                        constraints['pattern'] = param.pattern
                    if hasattr(param, 'min_length') and param.min_length is not None:
                        constraints['min_length'] = param.min_length
                    if hasattr(param, 'max_length') and param.max_length is not None:
                        constraints['max_length'] = param.max_length
                    if hasattr(param, 'minimum') and param.minimum is not None:
                        constraints['minimum'] = param.minimum
                    if hasattr(param, 'maximum') and param.maximum is not None:
                        constraints['maximum'] = param.maximum

                parameters.append(ApiParameter(
                    name=param.name,
                    location=ParameterLocation(param.location),
                    data_type=DataType(param.data_type),
                    required=param.required,
                    description=param.description or "",
                    example=param.example,
                    constraints=constraints
                ))

            # 直接从接口对象构建响应信息
            responses = []
            for resp in interface_obj.responses:
                responses.append(ApiResponse(
                    status_code=resp.status_code,
                    description=resp.description or "",
                    content_type=resp.content_type or "application/json",
                    response_schema=resp.response_schema or {},
                    example=resp.example
                ))

            # 直接从接口对象构建完整的端点对象
            parsed_endpoint = ParsedEndpoint(
                endpoint_id=interface_obj.endpoint_id or interface_obj.interface_id,
                path=interface_obj.path,
                method=interface_obj.method,
                summary=interface_obj.summary or "",
                description=interface_obj.description or "",
                parameters=parameters,
                responses=responses,
                tags=interface_obj.tags or [],
                auth_required=interface_obj.auth_required,
                deprecated=interface_obj.is_deprecated,
                # 直接从数据库对象获取扩展信息
                extended_info=interface_obj.extended_info or {},
                raw_data=interface_obj.raw_data or {},
                security_schemes=interface_obj.security_schemes or {},
                complexity_score=interface_obj.complexity_score,
                confidence_score=interface_obj.confidence_score,
                interface_name=interface_obj.name,
                category=interface_obj.category or "",
                auth_type=interface_obj.auth_type or ""
            )

            # 构建分析输入，包含丰富的上下文信息
            analysis_options = {
                "interface_id": interface_id,
                "single_interface_mode": True,  # 标识这是单接口脚本生成
                "generation_focus": "comprehensive",  # 生成全面的测试脚本
                "include_edge_cases": True,  # 包含边界情况测试
                "include_error_handling": True,  # 包含错误处理测试
                "use_extended_info": True,  # 使用扩展信息
                # 直接从数据库对象获取文档级别的信息
                "document_format": document_obj.doc_format,
                "document_version": document_obj.doc_version,
                "api_title": interface_obj.api_title,
                "api_version": interface_obj.api_version,
                # 直接从接口对象获取质量评估信息
                "complexity_score": interface_obj.complexity_score,
                "confidence_score": interface_obj.confidence_score,
                # 直接从接口对象获取扩展信息的关键字段
                "extended_info": interface_obj.extended_info,
                "raw_data": interface_obj.raw_data,
                "auth_type": interface_obj.auth_type,
                "category": interface_obj.category,
                # 额外的接口信息
                "interface_name": interface_obj.name,
                "base_url": interface_obj.base_url
            }

            analysis_input = AnalysisInput(
                session_id=session_id,
                document_id=document_id,
                interface_id=interface_id,  # 传递interface_id
                api_info=parsed_api_info,
                endpoints=[parsed_endpoint],
                analysis_options=analysis_options
            )

            # 发送到接口分析智能体
            await self.runtime.publish_message(
                analysis_input,
                topic_id=TopicId(type=TopicTypes.API_ANALYZER.value, source="orchestrator")
            )

            logger.info(f"✅ 接口脚本生成任务已启动: {interface_id}")

            return {
                "success": True,
                "session_id": session_id,
                "interface_id": interface_id,
                "message": "接口脚本生成任务已启动",
                "status": "processing"
            }

        except Exception as e:
            # 更新指标
            self.orchestrator_metrics["failed_workflows"] += 1
            if session_id in self.active_sessions:
                self.active_sessions[session_id]["status"] = "failed"
                self.active_sessions[session_id]["error"] = str(e)
                self.active_sessions[session_id]["failed_at"] = datetime.now().isoformat()

            # 记录错误事件
            await self._log_workflow_event(
                session_id,
                "interface_script_generation_failed",
                f"接口脚本生成失败: {str(e)}",
                {"error": str(e), "interface_id": interface_id}
            )

            logger.error(f"❌ 接口脚本生成失败: {str(e)}")
            raise

    async def trigger_analysis_step(
        self,
        session_id: str,
        document_id: str,
        api_info: Dict[str, Any],
        endpoints: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        手动触发接口分析步骤

        这个方法可以用于测试或手动控制工作流
        """
        try:
            # 构建分析输入（需要根据实际的数据结构调整）
            # 这里需要将字典转换为相应的数据模型对象
            logger.info(f"手动触发接口分析步骤: {session_id}")

            # TODO: 实现数据转换逻辑
            logger.warning("手动触发分析步骤功能需要完善数据转换逻辑")

            return {
                "success": True,
                "session_id": session_id,
                "message": "接口分析步骤触发功能需要完善",
                "note": "需要实现从字典到数据模型的转换逻辑"
            }

        except Exception as e:
            logger.error(f"触发接口分析步骤失败: {str(e)}")
            raise

    def get_workflow_status(self, session_id: str) -> Dict[str, Any]:
        """
        获取工作流状态（增强版本）

        提供更详细的工作流进度信息
        """
        try:
            if session_id not in self.active_sessions:
                return {
                    "success": False,
                    "message": "会话不存在",
                    "session_id": session_id
                }

            session_info = self.active_sessions[session_id].copy()

            # 添加工作流进度信息
            if session_info.get("workflow_type") == "complete":
                workflow_steps = [
                    {"step": "document_parsing", "name": "文档解析", "status": "completed" if session_info.get("current_step") != "document_parsing" else "running"},
                    {"step": "api_analysis", "name": "接口分析", "status": "pending"},
                    {"step": "test_case_generation", "name": "测试用例生成", "status": "pending"},
                    {"step": "script_generation", "name": "脚本生成", "status": "pending"}
                ]

                # 根据当前步骤更新状态
                current_step = session_info.get("current_step", "")
                for i, step in enumerate(workflow_steps):
                    if step["step"] == current_step:
                        step["status"] = "running"
                        # 标记之前的步骤为已完成
                        for j in range(i):
                            workflow_steps[j]["status"] = "completed"
                        break

                session_info["workflow_progress"] = workflow_steps
                session_info["progress_percentage"] = (
                    len([s for s in workflow_steps if s["status"] == "completed"]) / len(workflow_steps) * 100
                )

            return {
                "success": True,
                "session_id": session_id,
                "session_info": session_info
            }

        except Exception as e:
            logger.error(f"获取工作流状态失败: {str(e)}")
            return {
                "success": False,
                "message": str(e),
                "session_id": session_id
            }

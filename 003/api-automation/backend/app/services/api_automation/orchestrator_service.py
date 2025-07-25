"""
接口自动化智能体编排服务
负责协调各个智能体的工作流程
"""
from typing import Dict, List, Any, Optional
from datetime import datetime

from autogen_core import SingleThreadedAgentRuntime, TopicId
from loguru import logger

from app.core.agents.collector import StreamResponseCollector
from app.core.types import AgentPlatform, TopicTypes
from app.core.messages.api_automation import (
    ApiDocParseRequest, DependencyAnalysisRequest,
    TestScriptGenerationRequest, TestExecutionRequest,
    LogRecordRequest
)
from app.core.enums import LogLevel
from app.agents.factory import agent_factory


class ApiAutomationOrchestrator:
    """
    接口自动化智能体编排器
    
    负责协调以下智能体的工作流程：
    1. API文档解析智能体 - 解析API文档
    2. 接口依赖分析智能体 - 分析接口依赖关系
    3. 测试脚本生成智能体 - 生成pytest测试脚本
    4. 测试执行智能体 - 执行测试并生成报告
    5. 日志记录智能体 - 记录执行日志
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
                "session_info": self.active_sessions[session_id]
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
        """发送API文档解析请求"""
        try:
            # 构建解析请求
            parse_request = ApiDocParseRequest(
                session_id=session_id,
                file_path=file_path,
                file_name=file_name,
                file_content=file_content,
                doc_format=doc_format,
                parse_config=config or {}
            )
            
            # 发送到API文档解析智能体
            await self.runtime.publish_message(
                parse_request,
                topic_id=TopicId(type=TopicTypes.API_DOC_PARSER.value, source="orchestrator")
            )
            
            logger.info(f"已发送API文档解析请求: {session_id}")
            
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
        执行测试套件
        
        Args:
            session_id: 会话ID
            script_files: 测试脚本文件列表
            test_config: 测试配置
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            logger.info(f"开始执行测试套件: {session_id}")
            
            # 构建执行请求
            execution_request = TestExecutionRequest(
                session_id=session_id,
                doc_id=session_id,  # 简化处理
                test_cases=[],  # 将在执行智能体中处理
                script_files=script_files,
                execution_config=test_config or {
                    "framework": "pytest",
                    "parallel": False,
                    "max_workers": 1,
                    "timeout": 300,
                    "report_formats": ["allure", "html"]
                },
                environment="test",
                parallel=test_config.get("parallel", False) if test_config else False,
                max_workers=test_config.get("max_workers", 1) if test_config else 1
            )
            
            # 发送到测试执行智能体
            await self.runtime.publish_message(
                execution_request,
                topic_id=TopicId(type=TopicTypes.TEST_EXECUTOR.value, source="orchestrator")
            )
            
            # 记录执行日志
            await self._log_workflow_event(
                session_id,
                "test_execution_started",
                f"开始执行测试套件，包含 {len(script_files)} 个脚本文件",
                {"script_files": script_files, "config": test_config}
            )
            
            return {
                "success": True,
                "session_id": session_id,
                "message": "测试执行已启动",
                "script_count": len(script_files)
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
            log_request = LogRecordRequest(
                session_id=session_id,
                agent_name="ApiAutomationOrchestrator",
                log_level=LogLevel.INFO.value,
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

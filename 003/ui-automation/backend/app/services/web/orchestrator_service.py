"""
Web编排器
负责协调Web智能体的执行流程，支持完整的业务流程编排
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from autogen_core import SingleThreadedAgentRuntime, TopicId, ClosureAgent, TypeSubscription

# 导入智能体工厂
from app.agents.factory import AgentFactory, agent_factory
from app.core.types import TopicTypes, AgentTypes
from app.core.agents import StreamResponseCollector
# 导入消息类型
from app.core.messages import (
    WebMultimodalAnalysisRequest, WebMultimodalAnalysisResponse, YAMLExecutionRequest, PlaywrightExecutionRequest,
    AnalysisType, PageAnalysis, TestCaseElementParseRequest
)
import uuid


class WebOrchestrator:
    """Web智能体编排器 - 支持完整业务流程"""

    def __init__(self, collector: Optional[StreamResponseCollector]=None):
        self.runtime: Optional[SingleThreadedAgentRuntime] = None

        # 使用智能体工厂
        self.agent_factory = agent_factory
        self.response_collector = collector

        # 会话管理
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        logger.info("Web智能体编排器初始化完成，使用智能体工厂模式")
        
    async def _setup_runtime(self, session_id: str) -> None:
        """设置运行时和所有智能体"""
        try:
            # 创建运行时
            self.runtime = SingleThreadedAgentRuntime()
            # 启动运行时
            self.runtime.start()
            # 创建响应收集器
            if self.response_collector is None:
                self.response_collector = StreamResponseCollector()

            # 使用智能体工厂注册Web平台智能体
            await self.agent_factory.register_web_agents(
                runtime=self.runtime,
                collector=self.response_collector,
                enable_user_feedback=False
            )
            # 使用智能体工厂注册流式响应收集器
            await self.agent_factory.register_stream_collector(
                runtime=self.runtime,
                collector=self.response_collector
            )
            # 记录会话信息
            self.active_sessions[session_id] = {
                "status": "running",
                "started_at": datetime.now().isoformat(),
                "runtime_id": id(self.runtime),
                "registered_agents": len(self.agent_factory.list_registered_agents())
            }

            logger.info(f"Web运行时设置完成，已注册 {len(self.agent_factory.list_registered_agents())} 个智能体: {session_id}")

        except Exception as e:
            logger.error(f"设置Web运行时失败: {session_id}, 错误: {str(e)}")
            raise

    def get_agent_factory_info(self) -> Dict[str, Any]:
        """获取智能体工厂信息"""
        try:
            return {
                "available_agents": self.agent_factory.list_available_agents(),
                "registered_agents": self.agent_factory.list_registered_agents(),
                "factory_status": "active"
            }
        except Exception as e:
            logger.error(f"获取智能体工厂信息失败: {str(e)}")
            return {
                "available_agents": [],
                "registered_agents": [],
                "factory_status": "error",
                "error": str(e)
            }

    async def _cleanup_runtime(self) -> None:
        """清理运行时"""
        try:
            if self.runtime:
                await self.runtime.stop_when_idle()
                await self.runtime.close()
                self.runtime = None

            # 清理智能体工厂注册记录
            self.agent_factory.clear_registered_agents()

            # 重置响应收集器
            if self.response_collector:
                self.response_collector = None

            logger.debug("Web运行时清理完成")

        except Exception as e:
            logger.error(f"清理Web运行时失败: {str(e)}")

    # ==================== 业务流程1: 图片分析 → 脚本生成（支持格式选择） ====================

    async def analyze_image_to_scripts(
        self,
        session_id: str,
        image_data: str,
        test_description: str,
        additional_context: Optional[str] = None,
        generate_formats: Optional[List[str]] = None
    ):
        """
        业务流程1: 图片分析 → 脚本生成（支持多种格式）

        Args:
            session_id: 会话ID
            image_data: Base64图片数据
            test_description: 测试描述
            additional_context: 额外上下文
            generate_formats: 生成格式列表，如 ["yaml", "playwright"]

        Returns:
            Dict[str, Any]: 包含分析结果和生成脚本的完整结果
        """
        try:
            if generate_formats is None:
                generate_formats = ["yaml"]

            logger.info(f"开始业务流程1 - 图片分析→脚本生成: {session_id}, 格式: {generate_formats}")

            # 设置运行时
            await self._setup_runtime(session_id)

            # 构建图片分析请求
            analysis_request = WebMultimodalAnalysisRequest(
                session_id=session_id,
                analysis_type=AnalysisType.IMAGE,
                image_data=image_data,
                test_description=test_description,
                additional_context=additional_context,
                generate_formats=generate_formats
            )

            # 发送到图片分析智能体
            await self.runtime.publish_message(
                analysis_request,
                topic_id=TopicId(type=TopicTypes.IMAGE_ANALYZER.value, source="user")
            )
            logger.info(f"业务流程1完成: {session_id}")

        except Exception as e:
            logger.error(f"业务流程1失败: {session_id}, 错误: {str(e)}")
            raise
        finally:
            await self._cleanup_runtime()

    # ==================== 业务流程2: 页面分析（纯分析，不生成脚本） ====================

    async def analyze_page_elements(
        self,
        session_id: str,
        image_data: str,
        page_name: str,
        page_description: str,
        page_url: Optional[str] = None
    ):
        """
        业务流程2: 页面分析（纯分析，不生成脚本）

        专门用于页面元素识别和分析，不生成测试脚本
        分析结果会自动保存到数据库中

        Args:
            session_id: 会话ID
            image_data: Base64图片数据
            page_name: 页面名称
            page_description: 页面描述
            page_url: 页面URL（可选）

        Returns:
            Dict[str, Any]: 包含页面分析结果
        """
        try:
            logger.info(f"开始业务流程2 - 页面元素分析: {session_id}, 页面: {page_name}")

            # 设置运行时
            await self._setup_runtime(session_id)

            # 构建页面分析请求
            analysis_request = WebMultimodalAnalysisRequest(
                session_id=session_id,
                analysis_type=AnalysisType.IMAGE,
                image_data=image_data,
                test_description=page_description,
                additional_context=f"页面名称: {page_name}\n页面URL: {page_url}" if page_url else f"页面名称: {page_name}",
                web_url=page_url,
                target_url=page_url,
                generate_formats=[]  # 不生成脚本，只进行页面分析
            )

            # 发送到页面分析智能体
            await self.runtime.publish_message(
                analysis_request,
                topic_id=TopicId(type=TopicTypes.PAGE_ANALYZER.value, source="user")
            )

            logger.info(f"业务流程2完成: {session_id}")

        except Exception as e:
            logger.error(f"业务流程2失败: {session_id}, 错误: {str(e)}")
            raise
        finally:
            await self._cleanup_runtime()

    # ==================== 业务流程4: 基于文本生成脚本 ====================

    async def generate_scripts_from_text(
        self,
        session_id: str,
        test_description: str,
        additional_context: Optional[str] = None,
        generate_formats: Optional[List[str]] = None
    ):
        """
        业务流程4: 基于自然语言文本生成测试脚本

        Args:
            session_id: 会话ID
            test_description: 测试描述文本
            additional_context: 额外上下文
            generate_formats: 生成格式列表，如 ["yaml", "playwright"]
        """
        try:
            logger.info(f"开始业务流程4 - 文本生成脚本: {session_id}")

            if generate_formats is None:
                generate_formats = ["yaml"]

            # 设置运行时
            await self._setup_runtime(session_id)

            # 创建虚拟的多模态分析请求（不包含图片数据）
            text_analysis_request = WebMultimodalAnalysisRequest(
                session_id=session_id,
                analysis_type=AnalysisType.TEXT,
                image_data="",  # 空图片数据，表示基于文本生成
                test_description=test_description,
                additional_context=additional_context or "",
                generate_formats=generate_formats
            )

            # 创建虚拟的分析结果（模拟图片分析的输出结构）
            mock_analysis_result = WebMultimodalAnalysisResponse(
                analysis_id=str(uuid.uuid4()),
                session_id=session_id,
                page_analysis=PageAnalysis(
                    page_title="基于文本生成的测试",
                    page_type="文本描述",
                    main_content=test_description,
                    ui_elements=[],
                    test_actions=[],
                    confidence_score=0.9
                ),
                ui_elements=[],
                test_actions=[],
                confidence_score=0.9,
                analysis_time=datetime.now().isoformat(),
                metadata={
                    "generation_type": "text_to_script",
                    "source": "natural_language_description"
                }
            )

            # 根据用户选择的格式发送到相应的脚本生成智能体
            await self._route_to_script_generators_from_text(
                mock_analysis_result,
                generate_formats,
                test_description,
                additional_context
            )

            logger.info(f"业务流程4完成: {session_id}")

        except Exception as e:
            logger.error(f"业务流程4失败: {session_id}, 错误: {str(e)}")
            raise
        finally:
            await self._cleanup_runtime()

    async def _route_to_script_generators_from_text(
        self,
        analysis_result: WebMultimodalAnalysisResponse,
        generate_formats: List[str],
        test_description: str,
        additional_context: Optional[str] = None
    ) -> None:
        """根据用户选择的格式路由到相应的脚本生成智能体（文本生成模式）"""
        try:
            # 支持的格式映射
            format_topic_mapping = {
                "yaml": TopicTypes.YAML_GENERATOR.value,
                "playwright": TopicTypes.PLAYWRIGHT_GENERATOR.value
            }

            # 为每种格式发送消息
            for format_name in generate_formats:
                if format_name in format_topic_mapping:
                    topic_type = format_topic_mapping[format_name]

                    # 增强分析结果，添加文本生成的特殊标记
                    enhanced_result = analysis_result.model_copy()
                    enhanced_result.metadata = enhanced_result.metadata or {}
                    enhanced_result.metadata.update({
                        "generation_mode": "text_to_script",
                        "original_text": test_description,
                        "additional_context": additional_context or "",
                        "target_format": format_name
                    })

                    # 发送到对应的脚本生成智能体
                    await self.runtime.publish_message(
                        enhanced_result,
                        topic_id=TopicId(type=topic_type, source="user")
                    )

                    logger.info(f"已发送文本生成请求到 {format_name} 生成器")
                else:
                    logger.warning(f"不支持的生成格式: {format_name}")

        except Exception as e:
            logger.error(f"路由到脚本生成智能体失败: {str(e)}")
            raise

    # ==================== 业务流程5: 图片生成描述 ====================

    async def generate_description_from_image(
        self,
        session_id: str,
        image_data: str,
        additional_context: Optional[str] = None
    ):
        """
        业务流程5: 基于图片生成自然语言测试用例描述

        Args:
            session_id: 会话ID
            image_data: Base64编码的图片数据
            additional_context: 额外上下文
        """
        try:
            logger.info(f"开始业务流程5 - 图片生成描述: {session_id}")

            # 设置运行时
            await self._setup_runtime(session_id)

            # 创建图片分析请求
            image_analysis_request = WebMultimodalAnalysisRequest(
                session_id=session_id,
                analysis_type=AnalysisType.IMAGE,
                image_data=image_data,
                test_description="生成测试用例描述",
                additional_context=additional_context or "",
                generate_formats=[]  # 不生成脚本，只生成描述
            )

            # 发送到图片描述生成智能体
            await self.runtime.publish_message(
                image_analysis_request,
                topic_id=TopicId(type=TopicTypes.IMAGE_DESCRIPTION_GENERATOR.value, source="user")
            )

            logger.info(f"业务流程5完成: {session_id}")

        except Exception as e:
            logger.error(f"业务流程5失败: {session_id}, 错误: {str(e)}")
            raise
        finally:
            await self._cleanup_runtime()

    # ==================== 业务流程6: 测试用例元素解析 ====================

    async def parse_test_case_elements(
        self,
        session_id: str,
        test_case_content: str,
        test_description: Optional[str] = None,
        target_format: str = "playwright",
        additional_context: Optional[str] = None
    ):
        """
        业务流程6: 测试用例元素解析

        根据用户编写的测试用例内容，智能分析并从数据库中获取相应的页面元素信息，
        对返回的数据进行整理分类，为脚本生成智能体提供结构化的页面元素数据。

        Args:
            session_id: 会话ID
            test_case_content: 用户编写的测试用例内容
            test_description: 测试描述
            target_format: 目标脚本格式 (yaml, playwright)
            additional_context: 额外上下文信息

        Returns:
            Dict[str, Any]: 包含解析结果
        """
        try:
            logger.info(f"开始业务流程6 - 测试用例元素解析: {session_id}, 格式: {target_format}")

            # 设置运行时
            await self._setup_runtime(session_id)

            # 构建测试用例解析请求
            parse_request = TestCaseElementParseRequest(
                session_id=session_id,
                test_case_content=test_case_content,
                test_description=test_description,
                target_format=target_format,
                additional_context=additional_context
            )

            # 发送到测试用例元素解析智能体
            await self.runtime.publish_message(
                parse_request,
                topic_id=TopicId(type=TopicTypes.TEST_CASE_ELEMENT_PARSER.value, source="orchestrator")
            )

            logger.info(f"业务流程6完成: {session_id}")

        except Exception as e:
            logger.error(f"业务流程6失败: {session_id}, 错误: {str(e)}")
            raise
        finally:
            await self._cleanup_runtime()

    # ==================== 兼容性方法：保持向后兼容 ====================

    async def analyze_image_to_yaml(
        self,
        session_id: str,
        image_data: str,
        test_description: str,
        additional_context: Optional[str] = None
    ):
        """
        兼容性方法: 图片分析 → YAML脚本生成
        """
        return await self.analyze_image_to_scripts(
            session_id=session_id,
            image_data=image_data,
            test_description=test_description,
            additional_context=additional_context,
            generate_formats=["yaml"]
        )

    async def analyze_image_to_playwright(
        self,
        session_id: str,
        image_data: str,
        test_description: str,
        additional_context: Optional[str] = None
    ):
        """
        兼容性方法: 图片分析 → Playwright脚本生成
        """
        return await self.analyze_image_to_scripts(
            session_id=session_id,
            image_data=image_data,
            test_description=test_description,
            additional_context=additional_context,
            generate_formats=["playwright"]
        )

    # ==================== 业务流程3: YAML脚本执行 ====================

    async def execute_yaml_script(
        self,
        session_id: str,
        yaml_content: str,
        execution_config: Optional[Dict[str, Any]] = None
    ):
        """
        业务流程3: YAML脚本执行

        Args:
            session_id: 会话ID
            yaml_content: YAML脚本内容
            execution_config: 执行配置

        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            logger.info(f"开始业务流程3 - YAML脚本执行: {session_id}")

            # 设置运行时
            await self._setup_runtime(session_id)

            # 构建YAML执行请求（使用正确的消息类型）
            execution_request = YAMLExecutionRequest(
                yaml_content=yaml_content,
                execution_config=execution_config
            )

            # 发送到YAML执行智能体
            await self.runtime.publish_message(
                execution_request,
                topic_id=TopicId(type=TopicTypes.YAML_EXECUTOR.value, source="orchestrator")
            )

            # 等待执行完成
            await self.runtime.stop_when_idle()

            logger.info(f"业务流程3完成: {session_id}")
        except Exception as e:
            logger.error(f"业务流程3失败: {session_id}, 错误: {str(e)}")
            raise
        finally:
            await self._cleanup_runtime()

    # ==================== 业务流程4: Playwright脚本执行 ====================

    async def execute_playwright_script(
        self,
        request: PlaywrightExecutionRequest
    ):
        """
        业务流程4: Playwright脚本执行（支持script_name和test_content）

        Args:
            request: Playwright执行请求

        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            logger.info(f"开始业务流程4 - Playwright脚本执行: {request.session_id}")

            if request.script_name:
                logger.info(f"执行现有脚本: {request.script_name}")
            else:
                logger.info(f"执行动态脚本内容")

            # 设置运行时
            await self._setup_runtime(request.session_id)

            # 发送到Playwright执行智能体
            await self.runtime.publish_message(
                request,
                topic_id=TopicId(type=TopicTypes.PLAYWRIGHT_EXECUTOR.value, source="orchestrator")
            )

            logger.info(f"业务流程4完成: {request.session_id}")

        except Exception as e:
            logger.error(f"业务流程4失败: {request.session_id}, 错误: {str(e)}")
            raise
        finally:
            await self._cleanup_runtime()

    # 兼容性方法
    async def execute_playwright_script_legacy(
        self,
        session_id: str,
        playwright_content: str,
        execution_config: Optional[Dict[str, Any]] = None
    ):
        """
        兼容性方法: Playwright脚本执行（旧版本接口）
        """
        request = PlaywrightExecutionRequest(
            session_id=session_id,
            test_content=playwright_content,
            execution_config=execution_config
        )
        return await self.execute_playwright_script(request)

    # ==================== 会话管理方法 ====================

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话状态"""
        session_info = self.active_sessions.get(session_id)
        if session_info:
            # 添加智能体工厂信息
            session_info["agent_factory_info"] = self.get_agent_factory_info()
        return session_info

    def list_active_sessions(self) -> List[str]:
        """列出活跃会话"""
        return list(self.active_sessions.keys())

    def get_available_agents(self) -> List[Dict[str, Any]]:
        """获取可用的智能体列表"""
        return self.agent_factory.list_available_agents()

    def get_registered_agents(self) -> List[Dict[str, Any]]:
        """获取已注册的智能体列表"""
        return self.agent_factory.list_registered_agents()

    async def create_custom_agent_workflow(self,
                                         session_id: str,
                                         agent_types: List[str],
                                         workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """创建自定义智能体工作流

        Args:
            session_id: 会话ID
            agent_types: 要使用的智能体类型列表
            workflow_config: 工作流配置

        Returns:
            Dict[str, Any]: 工作流执行结果
        """
        try:
            logger.info(f"开始创建自定义智能体工作流: {session_id}")

            # 设置运行时
            await self._setup_runtime(session_id)

            # 验证智能体类型
            available_types = [agent["agent_type"] for agent in self.agent_factory.list_available_agents()]
            invalid_types = [t for t in agent_types if t not in available_types]

            if invalid_types:
                raise ValueError(f"无效的智能体类型: {invalid_types}")

            # 记录工作流信息
            workflow_info = {
                "agent_types": agent_types,
                "config": workflow_config,
                "status": "running",
                "started_at": datetime.now().isoformat()
            }

            self.active_sessions[session_id]["custom_workflow"] = workflow_info

            logger.info(f"自定义智能体工作流创建完成: {session_id}")

            return {
                "status": "success",
                "workflow_id": session_id,
                "agent_types": agent_types,
                "message": "自定义工作流创建成功"
            }

        except Exception as e:
            logger.error(f"创建自定义智能体工作流失败: {session_id}, 错误: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "workflow_id": session_id
            }

    async def cancel_session(self, session_id: str) -> bool:
        """取消会话"""
        try:
            if session_id in self.active_sessions:
                self.active_sessions[session_id]["status"] = "cancelled"
                self.active_sessions[session_id]["cancelled_at"] = datetime.now().isoformat()

                # 如果是当前运行的会话，停止运行时
                if self.runtime:
                    await self.runtime.close()

                logger.info(f"会话已取消: {session_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"取消会话失败: {str(e)}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 简单的运行时创建测试
            test_runtime = SingleThreadedAgentRuntime()
            test_runtime.start()
            await test_runtime.stop_when_idle()
            await test_runtime.close()

            # 获取智能体工厂信息
            factory_info = self.get_agent_factory_info()

            return {
                "status": "healthy",
                "message": "Web编排器运行正常",
                "active_sessions": len(self.active_sessions),
                "agent_factory": factory_info,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Web编排器异常: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }


# ==================== 全局实例管理 ====================

# 全局编排器实例
_web_orchestrator: Optional[WebOrchestrator] = None


def get_web_orchestrator(collector: Optional[StreamResponseCollector] = None) -> WebOrchestrator:
    """获取Web编排器实例"""
    # global _web_orchestrator
    # if _web_orchestrator is None:
    _web_orchestrator = WebOrchestrator(collector)
    return _web_orchestrator

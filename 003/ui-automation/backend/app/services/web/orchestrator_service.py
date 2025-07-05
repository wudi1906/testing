"""
Web智能体编排服务
协调Web智能体的执行流程，支持完整的业务流程编排
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
from autogen_core import SingleThreadedAgentRuntime, TopicId

# 导入智能体工厂
from app.agents.factory import AgentFactory, agent_factory
from app.core.types import TopicTypes, AgentTypes
from app.core.agents import StreamResponseCollector
# 导入消息类型
from app.core.messages import (
    WebMultimodalAnalysisRequest, WebMultimodalAnalysisResponse, PlaywrightExecutionRequest,
    AnalysisType, PageAnalysis, TestCaseElementParseRequest
)
import uuid


class WebAgentOrchestrator:
    """Web智能体编排器 - 支持完整的业务流程编排"""

    def __init__(self, collector: Optional[StreamResponseCollector] = None):
        self.runtime: Optional[SingleThreadedAgentRuntime] = None
        self.agent_factory = agent_factory
        self.response_collector = collector
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

        logger.info("Web智能体编排器初始化成功")

    async def _initialize_runtime(self, session_id: str) -> None:
        """
        初始化运行时并注册所有智能体

        智能体注册流程:
        1. 创建并启动SingleThreadedAgentRuntime
        2. 如果未提供则初始化StreamResponseCollector
        3. 通过AgentFactory注册Web平台智能体:
           - IMAGE_ANALYZER 图片分析智能体
           - PAGE_ANALYZER 页面分析智能体
           - PAGE_ANALYSIS_STORAGE 页面数据存储智能体
           - YAML_GENERATOR YAML脚本生成智能体
           - YAML_EXECUTOR YAML脚本执行智能体
           - PLAYWRIGHT_GENERATOR Playwright脚本生成智能体
           - PLAYWRIGHT_EXECUTOR Playwright脚本执行智能体
           - SCRIPT_DATABASE_SAVER 脚本数据库保存智能体
           - IMAGE_DESCRIPTION_GENERATOR 图片描述生成智能体
           - TEST_CASE_ELEMENT_PARSER 测试用例元素解析智能体
        4. 注册StreamResponseCollector用于消息处理
        5. 记录会话信息用于跟踪

        此方法为智能体消息通信准备运行时环境。
        """
        try:
            # 创建并启动运行时
            self.runtime = SingleThreadedAgentRuntime()
            self.runtime.start()

            # 如果未提供则初始化响应收集器
            if self.response_collector is None:
                self.response_collector = StreamResponseCollector()

            # 使用智能体工厂注册Web平台智能体
            await self.agent_factory.register_web_agents(
                runtime=self.runtime,
                collector=self.response_collector,
                enable_user_feedback=False
            )

            # 注册流式响应收集器
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

            logger.info(f"运行时初始化成功，已注册 {len(self.agent_factory.list_registered_agents())} 个智能体: {session_id}")

        except Exception as e:
            logger.error(f"会话 {session_id} 运行时初始化失败: {str(e)}")
            raise

    def get_agent_factory_status(self) -> Dict[str, Any]:
        """
        获取智能体工厂状态信息

        返回智能体工厂状态的综合信息:
        - available_agents: 可创建的所有智能体类型列表
        - registered_agents: 当前已注册的智能体实例列表
        - factory_status: 当前状态 ("active" 或 "error")

        此方法提供智能体生态系统的可见性，不会触发任何消息流或智能体通信。
        """
        try:
            return {
                "available_agents": self.agent_factory.list_available_agents(),
                "registered_agents": self.agent_factory.list_registered_agents(),
                "factory_status": "active"
            }
        except Exception as e:
            logger.error(f"获取智能体工厂状态失败: {str(e)}")
            return {
                "available_agents": [],
                "registered_agents": [],
                "factory_status": "error",
                "error": str(e)
            }

    async def _cleanup_runtime(self) -> None:
        """
        清理运行时资源

        清理流程:
        1. 停止运行时当空闲时 (等待所有智能体完成当前任务)
        2. 关闭运行时并释放资源
        3. 清除智能体工厂注册记录
        4. 重置响应收集器为None
        5. 设置运行时为None

        这确保智能体工作流完成后的适当资源清理。
        """
        try:
            if self.runtime:
                await self.runtime.stop_when_idle()
                await self.runtime.close()
                self.runtime = None

            # 清除智能体工厂注册记录
            self.agent_factory.clear_registered_agents()

            # 重置响应收集器
            if self.response_collector:
                self.response_collector = None

            logger.debug("运行时清理成功完成")

        except Exception as e:
            logger.error(f"运行时清理失败: {str(e)}")

    # ==================== 核心业务工作流 ====================

    async def analyze_image_to_scripts(
        self,
        session_id: str,
        image_data: str,
        test_description: str,
        additional_context: Optional[str] = None,
        generate_formats: Optional[List[str]] = None
    ) -> None:
        """
        分析图片并生成指定格式的测试脚本

        智能体消息流:
        1. 发送 WebMultimodalAnalysisRequest → IMAGE_ANALYZER 智能体
        2. ImageAnalyzerAgent 处理图片并提取UI元素
        3. ImageAnalyzerAgent 根据 generate_formats 路由到脚本生成器:
           - 如果格式包含 "yaml" → 发送 WebMultimodalAnalysisResponse → YAML_GENERATOR 智能体
           - 如果格式包含 "playwright" → 发送 WebMultimodalAnalysisResponse → PLAYWRIGHT_GENERATOR 智能体
        4. 脚本生成器创建测试脚本并发送到 SCRIPT_DATABASE_SAVER 智能体
        5. SCRIPT_DATABASE_SAVER 将脚本保存到数据库

        消息类型:
        - 输入: WebMultimodalAnalysisRequest (发送到 IMAGE_ANALYZER)
        - 内部: WebMultimodalAnalysisResponse (发送到脚本生成器)
        - 内部: WebGeneratedScript (发送到 SCRIPT_DATABASE_SAVER)

        Args:
            session_id: 会话标识符
            image_data: Base64编码的图片数据
            test_description: 测试描述
            additional_context: 额外上下文信息
            generate_formats: 要生成的格式列表，例如 ["yaml", "playwright"]
        """
        try:
            if generate_formats is None:
                generate_formats = ["yaml"]

            logger.info(f"开始图片分析到脚本生成工作流: {session_id}, 格式: {generate_formats}")

            # 初始化运行时
            await self._initialize_runtime(session_id)

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
            logger.info(f"图片分析工作流完成: {session_id}")

        except Exception as e:
            logger.error(f"会话 {session_id} 图片分析工作流失败: {str(e)}")
            raise
        finally:
            await self._cleanup_runtime()

    async def analyze_page_elements(
        self,
        session_id: str,
        image_data: str,
        page_name: str,
        page_description: str,
        page_url: Optional[str] = None
    ) -> None:
        """
        分析页面元素但不生成测试脚本

        智能体消息流:
        1. 发送 WebMultimodalAnalysisRequest → PAGE_ANALYZER 智能体
        2. PageAnalyzerAgent 分析页面结构并提取UI元素
        3. PageAnalyzerAgent 发送 PageAnalysis → PAGE_ANALYSIS_STORAGE 智能体
        4. PAGE_ANALYSIS_STORAGE 将页面分析结果保存到数据库
        5. PAGE_ANALYSIS_STORAGE 将单个页面元素保存到数据库

        消息类型:
        - 输入: WebMultimodalAnalysisRequest (发送到 PAGE_ANALYZER)
        - 内部: PageAnalysis (发送到 PAGE_ANALYSIS_STORAGE)
        - 内部: PageElement[] (发送到 PAGE_ANALYSIS_STORAGE)

        注意: generate_formats 为空，因此不会发生脚本生成

        Args:
            session_id: 会话标识符
            image_data: Base64编码的图片数据
            page_name: 页面名称
            page_description: 页面描述
            page_url: 页面URL (可选)
        """
        try:
            logger.info(f"开始页面元素分析工作流: {session_id}, 页面: {page_name}")

            # 初始化运行时
            await self._initialize_runtime(session_id)

            # 构建页面分析请求
            context = f"页面名称: {page_name}"
            if page_url:
                context += f"\n页面URL: {page_url}"

            analysis_request = WebMultimodalAnalysisRequest(
                session_id=session_id,
                analysis_type=AnalysisType.IMAGE,
                image_data=image_data,
                test_description=page_description,
                additional_context=context,
                web_url=page_url,
                target_url=page_url,
                generate_formats=[]  # 不生成脚本，仅分析
            )

            # 发送到页面分析智能体
            await self.runtime.publish_message(
                analysis_request,
                topic_id=TopicId(type=TopicTypes.PAGE_ANALYZER.value, source="user")
            )

            logger.info(f"页面元素分析工作流完成: {session_id}")

        except Exception as e:
            logger.error(f"会话 {session_id} 页面元素分析工作流失败: {str(e)}")
            raise
        finally:
            await self._cleanup_runtime()

    async def generate_scripts_from_text(
        self,
        session_id: str,
        test_description: str,
        additional_context: Optional[str] = None,
        generate_formats: Optional[List[str]] = None
    ) -> None:
        """
        从自然语言文本描述生成测试脚本

        智能体消息流:
        1. 创建带有基于文本元数据的模拟 WebMultimodalAnalysisResponse
        2. 根据 generate_formats 路由到脚本生成器:
           - 如果格式包含 "yaml" → 发送增强的 WebMultimodalAnalysisResponse → YAML_GENERATOR 智能体
           - 如果格式包含 "playwright" → 发送增强的 WebMultimodalAnalysisResponse → PLAYWRIGHT_GENERATOR 智能体
        3. 脚本生成器处理文本描述并生成测试脚本
        4. 生成的脚本发送到 SCRIPT_DATABASE_SAVER 智能体
        5. SCRIPT_DATABASE_SAVER 将脚本保存到数据库

        消息类型:
        - 内部: WebMultimodalAnalysisResponse (发送到脚本生成器，带有 text_to_script 元数据)
        - 内部: WebGeneratedScript (发送到 SCRIPT_DATABASE_SAVER)

        注意: 不进行图片分析，脚本纯粹从文本描述生成

        Args:
            session_id: 会话标识符
            test_description: 测试描述文本
            additional_context: 额外上下文信息
            generate_formats: 要生成的格式列表，例如 ["yaml", "playwright"]
        """
        try:
            logger.info(f"开始文本到脚本生成工作流: {session_id}")

            if generate_formats is None:
                generate_formats = ["yaml"]

            # 初始化运行时
            await self._initialize_runtime(session_id)

            # 为基于文本的生成创建分析结果
            analysis_result = WebMultimodalAnalysisResponse(
                analysis_id=str(uuid.uuid4()),
                session_id=session_id,
                page_analysis=PageAnalysis(
                    page_title="基于文本的测试生成",
                    page_type="自然语言描述",
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

            # 路由到适当的脚本生成器
            await self._route_to_script_generators(
                analysis_result,
                generate_formats,
                test_description,
                additional_context
            )

            logger.info(f"文本到脚本生成工作流完成: {session_id}")

        except Exception as e:
            logger.error(f"会话 {session_id} 文本到脚本生成工作流失败: {str(e)}")
            raise
        finally:
            await self._cleanup_runtime()

    async def _route_to_script_generators(
        self,
        analysis_result: WebMultimodalAnalysisResponse,
        generate_formats: List[str],
        test_description: str,
        additional_context: Optional[str] = None
    ) -> None:
        """
        根据选定格式将分析结果路由到适当的脚本生成器

        智能体消息流:
        对于 generate_formats 中的每种格式:
        1. 使用文本生成元数据增强 WebMultimodalAnalysisResponse
        2. 路由到特定生成器:
           - "yaml" → 发送增强的 WebMultimodalAnalysisResponse → YAML_GENERATOR 智能体
           - "playwright" → 发送增强的 WebMultimodalAnalysisResponse → PLAYWRIGHT_GENERATOR 智能体
        3. 每个生成器处理分析结果并创建测试脚本
        4. 生成的脚本自动发送到 SCRIPT_DATABASE_SAVER 智能体

        消息类型:
        - 输入: WebMultimodalAnalysisResponse (增强了元数据)
        - 输出: WebMultimodalAnalysisResponse (发送到 YAML_GENERATOR/PLAYWRIGHT_GENERATOR)
        """
        try:
            # 支持的格式映射
            format_topic_mapping = {
                "yaml": TopicTypes.YAML_GENERATOR.value,
                "playwright": TopicTypes.PLAYWRIGHT_GENERATOR.value
            }

            # 向每个格式生成器发送消息
            for format_name in generate_formats:
                if format_name in format_topic_mapping:
                    topic_type = format_topic_mapping[format_name]

                    # 使用文本生成元数据增强分析结果
                    enhanced_result = analysis_result.model_copy()
                    enhanced_result.metadata = enhanced_result.metadata or {}
                    enhanced_result.metadata.update({
                        "generation_mode": "text_to_script",
                        "original_text": test_description,
                        "additional_context": additional_context or "",
                        "target_format": format_name
                    })

                    # 发送到对应的脚本生成器智能体
                    await self.runtime.publish_message(
                        enhanced_result,
                        topic_id=TopicId(type=topic_type, source="user")
                    )

                    logger.info(f"已将文本生成请求路由到 {format_name} 生成器")
                else:
                    logger.warning(f"不支持的生成格式: {format_name}")

        except Exception as e:
            logger.error(f"路由到脚本生成器失败: {str(e)}")
            raise

    async def generate_description_from_image(
        self,
        session_id: str,
        image_data: str,
        additional_context: Optional[str] = None
    ) -> None:
        """
        从图片生成自然语言测试用例描述

        智能体消息流:
        1. 发送 WebMultimodalAnalysisRequest → IMAGE_DESCRIPTION_GENERATOR 智能体
        2. IMAGE_DESCRIPTION_GENERATOR 分析图片并生成自然语言描述
        3. 生成的描述通过响应收集器流式返回

        消息类型:
        - 输入: WebMultimodalAnalysisRequest (发送到 IMAGE_DESCRIPTION_GENERATOR)
        - 输出: StreamMessage (通过响应收集器的自然语言描述)

        注意: generate_formats 为空，因此不会发生脚本生成
        此工作流纯粹专注于生成人类可读的描述

        Args:
            session_id: 会话标识符
            image_data: Base64编码的图片数据
            additional_context: 额外上下文信息
        """
        try:
            logger.info(f"开始图片到描述生成工作流: {session_id}")

            # 初始化运行时
            await self._initialize_runtime(session_id)

            # 为描述生成创建图片分析请求
            image_analysis_request = WebMultimodalAnalysisRequest(
                session_id=session_id,
                analysis_type=AnalysisType.IMAGE,
                image_data=image_data,
                test_description="生成测试用例描述",
                additional_context=additional_context or "",
                generate_formats=[]  # 不生成脚本，仅生成描述
            )

            # 发送到图片描述生成器智能体
            await self.runtime.publish_message(
                image_analysis_request,
                topic_id=TopicId(type=TopicTypes.IMAGE_DESCRIPTION_GENERATOR.value, source="user")
            )

            logger.info(f"图片到描述生成工作流完成: {session_id}")

        except Exception as e:
            logger.error(f"会话 {session_id} 图片到描述生成工作流失败: {str(e)}")
            raise
        finally:
            await self._cleanup_runtime()

    async def parse_test_case_elements(
        self,
        session_id: str,
        test_case_content: str,
        test_description: Optional[str] = None,
        target_format: str = "playwright",
        additional_context: Optional[str] = None,
        selected_page_ids: Optional[List[str]] = None
    ) -> None:
        """
        解析测试用例元素并从数据库检索页面信息

        智能体消息流:
        1. 发送 TestCaseElementParseRequest → TEST_CASE_ELEMENT_PARSER 智能体
        2. TEST_CASE_ELEMENT_PARSER 分析测试用例内容并识别所需的页面元素
        3. TEST_CASE_ELEMENT_PARSER 查询数据库以匹配页面元素
        4. TEST_CASE_ELEMENT_PARSER 按页面/类别组织页面元素
        5. TEST_CASE_ELEMENT_PARSER 路由到目标脚本生成器:
           - 如果 target_format="yaml" → 发送组织的数据 → YAML_GENERATOR 智能体
           - 如果 target_format="playwright" → 发送组织的数据 → PLAYWRIGHT_GENERATOR 智能体
        6. 脚本生成器使用检索到的页面元素创建测试脚本
        7. 生成的脚本发送到 SCRIPT_DATABASE_SAVER 智能体

        消息类型:
        - 输入: TestCaseElementParseRequest (发送到 TEST_CASE_ELEMENT_PARSER)
        - 内部: PageElementData (发送到脚本生成器)
        - 内部: WebGeneratedScript (发送到 SCRIPT_DATABASE_SAVER)

        Args:
            session_id: 会话标识符
            test_case_content: 用户编写的测试用例内容
            test_description: 测试描述
            target_format: 目标脚本格式 (yaml, playwright)
            additional_context: 额外上下文信息
            selected_page_ids: 选定的页面ID列表
        """
        try:
            logger.info(f"开始测试用例元素解析工作流: {session_id}, 格式: {target_format}")

            # 初始化运行时
            await self._initialize_runtime(session_id)

            # 构建测试用例解析请求
            parse_request = TestCaseElementParseRequest(
                session_id=session_id,
                test_case_content=test_case_content,
                test_description=test_description,
                target_format=target_format,
                additional_context=additional_context,
                selected_page_ids=selected_page_ids or []
            )

            # 发送到测试用例元素解析器智能体
            await self.runtime.publish_message(
                parse_request,
                topic_id=TopicId(type=TopicTypes.TEST_CASE_ELEMENT_PARSER.value, source="orchestrator")
            )

            logger.info(f"测试用例元素解析工作流完成: {session_id}")

        except Exception as e:
            logger.error(f"会话 {session_id} 测试用例元素解析工作流失败: {str(e)}")
            raise
        finally:
            await self._cleanup_runtime()

    async def execute_playwright_script(
        self,
        request: PlaywrightExecutionRequest
    ) -> None:
        """
        执行Playwright测试脚本

        智能体消息流:
        1. 发送 PlaywrightExecutionRequest → PLAYWRIGHT_EXECUTOR 智能体
        2. PLAYWRIGHT_EXECUTOR 准备执行环境
        3. PLAYWRIGHT_EXECUTOR 如需要则复制脚本到工作空间
        4. PLAYWRIGHT_EXECUTOR 使用Node.js执行Playwright脚本
        5. PLAYWRIGHT_EXECUTOR 监控执行进度并收集结果
        6. PLAYWRIGHT_EXECUTOR 生成测试报告并保存执行结果
        7. 执行状态和结果通过响应收集器流式返回

        消息类型:
        - 输入: PlaywrightExecutionRequest (发送到 PLAYWRIGHT_EXECUTOR)
        - 输出: StreamMessage (通过响应收集器的执行进度和结果)
        - 输出: TestExecutionResult (最终执行结果)

        执行流程:
        - 脚本验证和准备
        - 环境设置 (浏览器、依赖项)
        - 实时监控的脚本执行
        - 结果收集和报告生成

        Args:
            request: 包含脚本详情和配置的Playwright执行请求
        """
        try:
            logger.info(f"开始Playwright脚本执行工作流: {request.session_id}")

            if request.script_name:
                logger.info(f"执行现有脚本: {request.script_name}")
            else:
                logger.info(f"执行动态脚本内容")

            # 初始化运行时
            await self._initialize_runtime(request.session_id)

            # 发送到Playwright执行器智能体
            await self.runtime.publish_message(
                request,
                topic_id=TopicId(type=TopicTypes.PLAYWRIGHT_EXECUTOR.value, source="orchestrator")
            )

            logger.info(f"Playwright脚本执行工作流完成: {request.session_id}")

        except Exception as e:
            logger.error(f"会话 {request.session_id} Playwright脚本执行工作流失败: {str(e)}")
            raise
        finally:
            await self._cleanup_runtime()

    # ==================== 会话管理 ====================

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话状态信息

        返回会话信息包括:
        - status: 当前会话状态 ("running", "completed", "error")
        - started_at: 会话开始时间戳
        - runtime_id: 运行时实例标识符
        - registered_agents: 已注册智能体数量
        - agent_factory_info: 当前智能体工厂状态

        此方法不会触发任何智能体消息流。
        """
        session_info = self.active_sessions.get(session_id)
        if session_info:
            # 添加智能体工厂信息
            session_info["agent_factory_info"] = self.get_agent_factory_status()
        return session_info

    def list_active_sessions(self) -> List[str]:
        """
        列出所有活跃会话ID

        返回当前活跃会话的会话标识符列表。
        此方法不会触发任何智能体消息流。
        """
        return list(self.active_sessions.keys())

    def get_available_agents(self) -> List[Dict[str, Any]]:
        """
        获取可用智能体列表

        返回所有可创建智能体类型的详细信息:
        - agent_type: 智能体类型标识符
        - agent_class: 智能体类名
        - description: 智能体功能描述
        - platform: 目标平台 (WEB)

        此方法不会触发任何智能体消息流。
        """
        return self.agent_factory.list_available_agents()

    def get_registered_agents(self) -> List[Dict[str, Any]]:
        """
        获取已注册智能体列表

        返回当前已注册智能体实例的信息:
        - agent_id: 唯一智能体实例标识符
        - agent_type: 智能体类型标识符
        - status: 智能体状态 ("active", "idle", "busy")
        - registered_at: 注册时间戳

        此方法不会触发任何智能体消息流。
        """
        return self.agent_factory.list_registered_agents()




# ==================== 全局实例管理 ====================

def get_web_orchestrator(collector: Optional[StreamResponseCollector] = None) -> WebAgentOrchestrator:
    """
    获取Web智能体编排器实例

    工厂函数，创建新的WebAgentOrchestrator实例。
    每次调用都创建新实例，确保每个工作流的状态干净。

    Args:
        collector: 可选的StreamResponseCollector用于捕获智能体响应

    Returns:
        WebAgentOrchestrator: 准备好进行智能体工作流的新编排器实例

    注意: 此函数不会触发任何智能体消息流。
    """
    return WebAgentOrchestrator(collector)

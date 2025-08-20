"""
UI自动化测试系统 - 智能体工厂
统一创建和管理所有智能体实例，提供 AssistantAgent 和自定义智能体的创建接口
"""
from typing import Dict, Any, Callable, Optional, List, Type
from abc import ABC, abstractmethod

from autogen_core import SingleThreadedAgentRuntime, ClosureAgent, TypeSubscription
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from loguru import logger

from app.core.config import settings
from app.core.llms import (
    get_deepseek_model_client, 
    get_uitars_model_client, 
    get_qwenvl_model_client, 
    get_glm_model_client,
    get_optimal_model_for_task
)
from app.core.types import AgentTypes, TopicTypes, AGENT_NAMES, AgentPlatform
from app.core.agents.base import BaseAgent


class AgentFactory:
    """智能体工厂类，统一管理智能体的创建和注册"""

    def __init__(self):
        """初始化智能体工厂"""
        self._registered_agents: Dict[str, Dict[str, Any]] = {}
        self._agent_classes: Dict[str, Type[BaseAgent]] = {}
        self._assistant_agent_configs: Dict[str, Dict[str, Any]] = {}
        
        # 注册所有可用的智能体类
        self._register_agent_classes()
        
        logger.info("智能体工厂初始化完成")

    def _register_agent_classes(self) -> None:
        """注册所有智能体类"""
        try:
            # Web平台智能体
            # from app.agents.web.ui_image_analyzer_agent import ImageAnalyzerAgent
            from app.agents.web.page_element_analyzer_agent import PageAnalyzerAgent
            from app.agents.web.page_data_storage_agent import PageAnalysisStorageAgent
            from app.agents.web.yaml_script_generator_agent import YAMLGeneratorAgent
            from app.agents.web.yaml_script_executor_agent import YAMLExecutorAgent
            from app.agents.web.playwright_script_generator_agent import PlaywrightGeneratorAgent
            from app.agents.web.playwright_script_executor_agent import PlaywrightExecutorAgent
            from app.agents.web.test_script_storage_agent import ScriptDatabaseSaverAgent
            from app.agents.web.image_description_agent import ImageDescriptionGeneratorAgent
            from app.agents.web.test_case_parser_agent import TestCaseElementParserAgent

            # 注册智能体类
            self._agent_classes.update({
                # AgentTypes.IMAGE_ANALYZER.value: ImageAnalyzerAgent,
                AgentTypes.PAGE_ANALYZER.value: PageAnalyzerAgent,
                AgentTypes.PAGE_ANALYSIS_STORAGE.value: PageAnalysisStorageAgent,
                AgentTypes.YAML_GENERATOR.value: YAMLGeneratorAgent,
                AgentTypes.YAML_EXECUTOR.value: YAMLExecutorAgent,
                AgentTypes.PLAYWRIGHT_GENERATOR.value: PlaywrightGeneratorAgent,
                AgentTypes.PLAYWRIGHT_EXECUTOR.value: PlaywrightExecutorAgent,
                AgentTypes.SCRIPT_DATABASE_SAVER.value: ScriptDatabaseSaverAgent,
                AgentTypes.IMAGE_DESCRIPTION_GENERATOR.value: ImageDescriptionGeneratorAgent,
                AgentTypes.TEST_CASE_ELEMENT_PARSER.value: TestCaseElementParserAgent,
            })
            
            # 调试信息
            logger.info(f"已注册 {len(self._agent_classes)} 个智能体类")
            logger.debug(f"注册的智能体类型: {list(self._agent_classes.keys())}")

        except ImportError as e:
            logger.error(f"智能体类导入失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"注册智能体类时发生错误: {str(e)}")
            raise

    def create_assistant_agent(self,
                               name: str,
                               system_message: str,
                               model_client_type: str = "auto",
                               model_client_stream: bool = True,
                               task_type: str = "default",
                               **kwargs) -> AssistantAgent:
        """创建 AssistantAgent 实例 - 支持智能模型选择
        
        Args:
            name: 智能体名称
            system_message: 系统提示词
            model_client_type: 模型客户端类型 ("auto", "qwenvl", "deepseek", "glm", "uitars")
            model_client_stream: 是否使用流式响应
            task_type: 任务类型，用于自动选择最优模型
            **kwargs: 其他参数
            
        Returns:
            AssistantAgent: 创建的智能体实例
        """
        try:
            # 智能选择模型客户端
            if model_client_type == "auto":
                model_client = get_optimal_model_for_task(task_type)
                logger.info(f"🎯 智能选择模型 - 任务: {task_type}")
            elif model_client_type == "qwenvl" or model_client_type == "qwen":
                model_client = get_qwenvl_model_client()
            elif model_client_type == "deepseek":
                model_client = get_deepseek_model_client()
            elif model_client_type == "glm":
                model_client = get_glm_model_client()
            elif model_client_type == "uitars":
                model_client = get_uitars_model_client()
            else:
                logger.warning(f"未知的模型客户端类型: {model_client_type}，使用智能选择")
                model_client = get_optimal_model_for_task(task_type)
            
            # 创建 AssistantAgent
            agent = AssistantAgent(
                name=name,
                model_client=model_client,
                system_message=system_message,
                model_client_stream=model_client_stream,
                **kwargs
            )
            
            logger.info(f"创建 AssistantAgent: {name} (模型: {model_client_type})")
            return agent
            
        except Exception as e:
            logger.error(f"创建 AssistantAgent 失败: {str(e)}")
            raise

    def create_agent(self, 
                    agent_type: str,
                    **kwargs) -> BaseAgent:
        """创建自定义智能体实例
        
        Args:
            agent_type: 智能体类型 (AgentTypes 枚举值)
            **kwargs: 智能体初始化参数
            
        Returns:
            BaseAgent: 创建的智能体实例
        """
        try:
            if agent_type not in self._agent_classes:
                raise ValueError(f"未知的智能体类型: {agent_type}")
            
            agent_class = self._agent_classes[agent_type]
            
            # 根据智能体类型智能选择最优模型客户端
            if not kwargs.get('model_client_instance'):
                # 图片和页面分析任务 - 使用QWen-VL (最佳视觉理解)
                if agent_type in [AgentTypes.IMAGE_ANALYZER.value, AgentTypes.PAGE_ANALYZER.value, 
                                 AgentTypes.MULTIMODAL_ANALYZER.value]:
                    kwargs['model_client_instance'] = get_optimal_model_for_task("ui_analysis")
                    logger.info(f"🎯 {agent_type} -> 使用QWen-VL(视觉分析)")
                    
                # 代码生成任务 - 使用DeepSeek (性价比极高)
                elif agent_type in [AgentTypes.YAML_GENERATOR.value, AgentTypes.PLAYWRIGHT_GENERATOR.value, 
                                   AgentTypes.TEST_CASE_ELEMENT_PARSER.value]:
                    kwargs['model_client_instance'] = get_optimal_model_for_task("code_generation")
                    logger.info(f"💰 {agent_type} -> 使用DeepSeek(代码生成)")
                    
                # 复杂分析任务 - 使用GLM-4V (多模态能力强)
                elif agent_type in [AgentTypes.RESULT_ANALYZER.value, AgentTypes.REPORT_GENERATOR.value]:
                    kwargs['model_client_instance'] = get_optimal_model_for_task("complex_analysis")
                    logger.info(f"🧠 {agent_type} -> 使用GLM-4V(复杂分析)")
                    
                # 其他任务 - 默认使用QWen-VL
                else:
                    kwargs['model_client_instance'] = get_optimal_model_for_task("default")
                    logger.info(f"🎯 {agent_type} -> 使用QWen-VL(默认最佳)")
            
            # 创建智能体实例
            agent = agent_class(**kwargs)
            
            logger.info(f"创建智能体: {AGENT_NAMES.get(agent_type, agent_type)}")
            return agent
            
        except Exception as e:
            logger.error(f"创建智能体失败 ({agent_type}): {str(e)}")
            raise

    async def register_agent(self,
                           runtime: SingleThreadedAgentRuntime,
                           agent_type: str,
                           topic_type: str,
                           **kwargs) -> None:
        """注册单个智能体到运行时
        
        Args:
            runtime: 智能体运行时
            agent_type: 智能体类型
            topic_type: 主题类型
            **kwargs: 智能体初始化参数
        """
        try:
            logger.debug(f"尝试注册智能体: {agent_type}")
            logger.debug(f"可用的智能体类型: {list(self._agent_classes.keys())}")

            if agent_type not in self._agent_classes:
                logger.error(f"智能体类型 '{agent_type}' 不在已注册的类型中")
                logger.error(f"已注册的类型: {list(self._agent_classes.keys())}")
                raise ValueError(f"未知的智能体类型: {agent_type}")

            agent_class = self._agent_classes[agent_type]
            
            # 注册智能体
            await agent_class.register(
                runtime,
                topic_type,
                lambda: self.create_agent(agent_type, **kwargs)
            )
            
            # 记录注册信息
            self._registered_agents[agent_type] = {
                "agent_type": agent_type,
                "topic_type": topic_type,
                "agent_name": AGENT_NAMES.get(agent_type, agent_type),
                "kwargs": kwargs
            }
            
            logger.info(f"注册智能体成功: {AGENT_NAMES.get(agent_type, agent_type)}")
            
        except Exception as e:
            logger.error(f"注册智能体失败 ({agent_type}): {str(e)}")
            raise

    async def register_web_agents(self,
                                runtime: SingleThreadedAgentRuntime,
                                collector=None,
                                enable_user_feedback: bool = False) -> None:
        """注册所有Web平台智能体

        Args:
            runtime: 智能体运行时
            collector: 响应收集器
            enable_user_feedback: 是否启用用户反馈
        """
        try:
            logger.info("开始注册Web平台智能体...")
            # 注册图片分析智能体
            # await self.register_agent(
            #     runtime,
            #     AgentTypes.IMAGE_ANALYZER.value,
            #     TopicTypes.IMAGE_ANALYZER.value,
            #     enable_user_feedback=enable_user_feedback,
            #     collector=collector,
            # )

            # 注册页面分析智能体
            await self.register_agent(
                runtime,
                AgentTypes.PAGE_ANALYZER.value,
                TopicTypes.PAGE_ANALYZER.value,
                enable_user_feedback=enable_user_feedback,
                collector=collector,
            )

            # 注册分析图片生成自然语言用例智能体
            await self.register_agent(
                runtime,
                AgentTypes.IMAGE_DESCRIPTION_GENERATOR.value,
                TopicTypes.IMAGE_DESCRIPTION_GENERATOR.value,
                enable_user_feedback=enable_user_feedback,
                collector=collector,
            )

            # 注册页面分析存储智能体
            await self.register_agent(
                runtime,
                AgentTypes.PAGE_ANALYSIS_STORAGE.value,
                TopicTypes.PAGE_ANALYSIS_STORAGE.value,
                enable_user_feedback=enable_user_feedback,
                collector=collector,
            )

            # 注册YAML生成智能体
            await self.register_agent(
                runtime,
                AgentTypes.YAML_GENERATOR.value,
                TopicTypes.YAML_GENERATOR.value
            )

            # 注册YAML执行智能体
            await self.register_agent(
                runtime,
                AgentTypes.YAML_EXECUTOR.value,
                TopicTypes.YAML_EXECUTOR.value
            )

            # 注册Playwright生成智能体
            await self.register_agent(
                runtime,
                AgentTypes.PLAYWRIGHT_GENERATOR.value,
                TopicTypes.PLAYWRIGHT_GENERATOR.value
            )

            # 注册Playwright执行智能体
            await self.register_agent(
                runtime,
                AgentTypes.PLAYWRIGHT_EXECUTOR.value,
                TopicTypes.PLAYWRIGHT_EXECUTOR.value
            )

            # 注册脚本数据库保存智能体
            await self.register_agent(
                runtime,
                AgentTypes.SCRIPT_DATABASE_SAVER.value,
                TopicTypes.SCRIPT_DATABASE_SAVER.value
            )

            # 注册测试用例元素解析智能体
            await self.register_agent(
                runtime,
                AgentTypes.TEST_CASE_ELEMENT_PARSER.value,
                TopicTypes.TEST_CASE_ELEMENT_PARSER.value
            )

            logger.info(f"Web平台智能体注册完成，共注册 {len(self._registered_agents)} 个智能体")

        except Exception as e:
            logger.error(f"注册Web平台智能体失败: {str(e)}")
            raise

    async def register_generation_agents(self,
                                        runtime: SingleThreadedAgentRuntime,
                                        formats: Optional[List[str]] = None,
                                        collector=None,
                                        enable_user_feedback: bool = False) -> None:
        """仅注册“脚本生成最小集合”智能体，避免与执行器耦合导致生成失败。

        - 根据 formats 注册对应生成器（yaml / playwright）
        - 始终注册 SCRIPT_DATABASE_SAVER 以便入库
        - 不注册 PLAYWRIGHT_EXECUTOR / YAML_EXECUTOR 等执行器
        """
        try:
            formats = formats or ["playwright"]

            # YAML 生成器
            if "yaml" in formats:
                await self.register_agent(
                    runtime,
                    AgentTypes.YAML_GENERATOR.value,
                    TopicTypes.YAML_GENERATOR.value
                )

            # Playwright 生成器
            if "playwright" in formats:
                await self.register_agent(
                    runtime,
                    AgentTypes.PLAYWRIGHT_GENERATOR.value,
                    TopicTypes.PLAYWRIGHT_GENERATOR.value
                )

            # 数据库存储
            await self.register_agent(
                runtime,
                AgentTypes.SCRIPT_DATABASE_SAVER.value,
                TopicTypes.SCRIPT_DATABASE_SAVER.value
            )

            # 注册流式收集器（如传入）
            if collector:
                await self.register_stream_collector(runtime, collector)

            logger.info("最小生成智能体集合注册完成")

        except Exception as e:
            logger.error(f"注册最小生成智能体集合失败: {str(e)}")
            raise

    async def register_all_agents(self,
                                runtime: SingleThreadedAgentRuntime,
                                collector=None,
                                enable_user_feedback: bool = False) -> None:
        """注册所有智能体

        Args:
            runtime: 智能体运行时
            collector: 响应收集器
            enable_user_feedback: 是否启用用户反馈
        """
        try:
            logger.info("开始注册所有智能体...")

            # 注册Web平台智能体
            await self.register_web_agents(runtime, collector, enable_user_feedback)

            # 注册流式响应收集器
            if collector:
                await self.register_stream_collector(runtime, collector)

            logger.info(f"所有智能体注册完成，共注册 {len(self._registered_agents)} 个智能体")

        except Exception as e:
            logger.error(f"注册所有智能体失败: {str(e)}")
            raise

    def create_user_proxy_agent(self,
                               name: str = "user_proxy",
                               input_func: Optional[Callable] = None,
                               **kwargs) -> UserProxyAgent:
        """创建用户代理智能体

        Args:
            name: 智能体名称
            input_func: 用户输入函数
            **kwargs: 其他参数

        Returns:
            UserProxyAgent: 用户代理智能体实例
        """
        try:
            from autogen_agentchat.agents import UserProxyAgent

            agent = UserProxyAgent(
                name=name,
                input_func=input_func,
                **kwargs
            )

            logger.info(f"创建用户代理智能体: {name}")
            return agent

        except Exception as e:
            logger.error(f"创建用户代理智能体失败: {str(e)}")
            raise

    async def register_stream_collector(self,
                                      runtime: SingleThreadedAgentRuntime,
                                      collector) -> None:
        """注册流式响应收集器

        Args:
            runtime: 智能体运行时
            collector: 响应收集器实例
        """
        try:
            # 检查回调函数是否存在
            if collector.callback is None:
                logger.warning("流式响应收集器回调函数为空，跳过注册")
                return

            await ClosureAgent.register_closure(
                runtime,
                "stream_collector_agent",
                collector.callback,
                subscriptions=lambda: [
                    TypeSubscription(
                        topic_type=TopicTypes.STREAM_OUTPUT.value,
                        agent_type="stream_collector_agent"
                    )
                ],
            )

            logger.info("流式响应收集器注册成功")

        except Exception as e:
            logger.error(f"注册流式响应收集器失败: {str(e)}")
            raise

    def get_agent_info(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """获取智能体信息
        
        Args:
            agent_type: 智能体类型
            
        Returns:
            Dict: 智能体信息，如果不存在返回None
        """
        return self._registered_agents.get(agent_type)

    def list_available_agents(self) -> List[Dict[str, Any]]:
        """列出所有可用的智能体
        
        Returns:
            List[Dict]: 智能体信息列表
        """
        return [
            {
                "agent_type": agent_type,
                "agent_name": AGENT_NAMES.get(agent_type, agent_type),
                "agent_class": agent_class.__name__,
                "registered": agent_type in self._registered_agents
            }
            for agent_type, agent_class in self._agent_classes.items()
        ]

    def list_registered_agents(self) -> List[Dict[str, Any]]:
        """列出所有已注册的智能体
        
        Returns:
            List[Dict]: 已注册智能体信息列表
        """
        return list(self._registered_agents.values())

    def clear_registered_agents(self) -> None:
        """清空已注册的智能体记录"""
        self._registered_agents.clear()
        logger.info("已清空智能体注册记录")


# 全局工厂实例（延迟初始化）
_agent_factory = None

def get_agent_factory() -> AgentFactory:
    """获取全局智能体工厂实例（延迟初始化）"""
    global _agent_factory
    if _agent_factory is None:
        _agent_factory = AgentFactory()
    return _agent_factory

# 保持向后兼容性
agent_factory = get_agent_factory()

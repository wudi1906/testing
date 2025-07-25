"""
API自动化智能体基类
提供公共的功能和方法，减少代码重复
"""
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from autogen_core import MessageContext
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import ModelClientStreamingChunkEvent
from loguru import logger

from app.core.agents.base import BaseAgent
from app.core.agents.llms import get_model_client
from app.core.types import AgentTypes


class BaseApiAutomationAgent(BaseAgent):
    """
    API自动化智能体基类
    
    提供公共功能：
    1. 大模型调用和流式处理
    2. JSON数据提取和解析
    3. 错误处理和统计
    4. AssistantAgent管理
    """
    
    def __init__(self, agent_type=None, model_client_instance=None, agent_id=None, agent_name=None, **kwargs):
        """初始化基类"""
        # 处理参数兼容性
        if agent_type is not None:
            # 从AgentTypes获取agent_name
            from app.core.types import AGENT_NAMES
            if agent_id is None:
                agent_id = agent_type.value if hasattr(agent_type, 'value') else str(agent_type)
            if agent_name is None:
                agent_name = AGENT_NAMES.get(agent_type.value if hasattr(agent_type, 'value') else agent_type, str(agent_type))

        # 调用父类构造函数
        super().__init__(
            agent_id=agent_id,
            agent_name=agent_name,
            **kwargs
        )

        # 存储agent_type以供子类使用
        self.agent_type = agent_type

        # 初始化大模型客户端
        self.model_client = model_client_instance or get_model_client("deepseek")
        
        # AssistantAgent管理
        self.assistant_agent = None
        self._assistant_creation_pending = False
        
        # 公共统计指标
        self.common_metrics = {
            "total_requests": 0,
            "successful_operations": 0,
            "failed_operations": 0,
            "total_processing_time": 0.0,
            "avg_processing_time": 0.0
        }
    
    def _initialize_assistant_agent(self):
        """通过工厂创建AssistantAgent"""
        try:
            from app.agents.factory import agent_factory, AgentPlatform
            
            async def create_assistant():
                return await agent_factory.create_agent(
                    agent_type=self.agent_type.value,
                    platform=AgentPlatform.AUTOGEN,
                    model_client_instance=self.model_client,
                    model_client_stream=True
                )
            
            # 异步上下文处理
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    self.assistant_agent = None
                    self._assistant_creation_pending = True
                else:
                    self.assistant_agent = loop.run_until_complete(create_assistant())
                    self._assistant_creation_pending = False
            except RuntimeError:
                self.assistant_agent = None
                self._assistant_creation_pending = True
                
            logger.info("AssistantAgent初始化配置完成")
            
        except Exception as e:
            logger.error(f"初始化AssistantAgent失败: {str(e)}")
            self._create_fallback_assistant_agent()
    
    def _create_fallback_assistant_agent(self):
        """创建备用AssistantAgent"""
        self.assistant_agent = AssistantAgent(
            name=f"{self.agent_type.value}_fallback",
            model_client=self.model_client,
            system_message="你是一个专业的API自动化助手。",
            model_client_stream=True
        )
        self._assistant_creation_pending = False
    
    async def _ensure_assistant_agent(self):
        """确保AssistantAgent已创建"""
        if self.assistant_agent is None or self._assistant_creation_pending:
            try:
                from app.agents.factory import agent_factory, AgentPlatform
                
                self.assistant_agent = await agent_factory.create_agent(
                    agent_type=self.agent_type.value,
                    platform=AgentPlatform.AUTOGEN,
                    model_client_instance=self.model_client,
                    model_client_stream=True
                )
                self._assistant_creation_pending = False
                logger.info("AssistantAgent异步创建完成")
                
            except Exception as e:
                logger.error(f"异步创建AssistantAgent失败: {str(e)}")
                if self.assistant_agent is None:
                    self._create_fallback_assistant_agent()
    
    async def _run_assistant_agent(self, task: str) -> Optional[str]:
        """运行AssistantAgent获取结果"""
        try:
            await self._ensure_assistant_agent()
            
            if self.assistant_agent is None:
                logger.error("AssistantAgent未能成功创建")
                return None
            
            stream = self.assistant_agent.run_stream(task=task)
            result_content = ""
            
            async for event in stream:
                if isinstance(event, ModelClientStreamingChunkEvent):
                    # 流式输出处理
                    continue
                if isinstance(event, TaskResult):
                    messages = event.messages
                    if messages and hasattr(messages[-1], 'content'):
                        result_content = messages[-1].content
                        break
            
            return result_content
            
        except Exception as e:
            logger.error(f"运行AssistantAgent失败: {str(e)}")
            return None
    
    def _extract_json_from_content(self, content: str) -> Optional[Dict[str, Any]]:
        """从内容中提取JSON数据"""
        try:
            import re
            
            # 查找JSON代码块
            json_pattern = r'```json\s*(.*?)\s*```'
            json_matches = re.findall(json_pattern, content, re.DOTALL)
            
            if json_matches:
                return json.loads(json_matches[0])
            
            # 查找普通JSON
            json_pattern = r'\{.*\}'
            json_matches = re.findall(json_pattern, content, re.DOTALL)
            
            if json_matches:
                return json.loads(json_matches[0])
            
            return None
            
        except Exception as e:
            logger.error(f"提取JSON失败: {str(e)}")
            return None
    
    def _update_metrics(self, operation_type: str, success: bool, processing_time: float = 0.0):
        """更新统计指标"""
        self.common_metrics["total_requests"] += 1
        
        if success:
            self.common_metrics["successful_operations"] += 1
        else:
            self.common_metrics["failed_operations"] += 1
        
        if processing_time > 0:
            self.common_metrics["total_processing_time"] += processing_time
            self.common_metrics["avg_processing_time"] = (
                self.common_metrics["total_processing_time"] / 
                self.common_metrics["total_requests"]
            )
    
    def _handle_common_error(self, error: Exception, operation: str) -> Dict[str, Any]:
        """公共错误处理"""
        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "operation": operation,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.error(f"{operation}失败: {error_info}")
        return error_info
    
    def get_common_statistics(self) -> Dict[str, Any]:
        """获取公共统计信息"""
        success_rate = 0.0
        if self.common_metrics["total_requests"] > 0:
            success_rate = (
                self.common_metrics["successful_operations"] / 
                self.common_metrics["total_requests"]
            ) * 100
        
        return {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type.value,
            "common_metrics": self.common_metrics,
            "success_rate": round(success_rate, 2)
        }

    async def process_message(self, message: Any, ctx: MessageContext) -> None:
        """处理消息的默认实现 - 子类可以重写此方法"""
        # 这是一个默认实现，子类可以根据需要重写
        logger.info(f"[{self.agent_name}] 收到消息: {message}")
        # 子类应该重写此方法来处理具体的消息逻辑

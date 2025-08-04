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
from tortoise import Tortoise

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

        # 数据库连接状态（基类提供）
        self._db_initialized = False
    
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
    
    async def _run_assistant_agent(self, task: str, stream: bool = False) -> Optional[str]:
        """运行AssistantAgent获取结果"""
        try:
            await self._ensure_assistant_agent()
            
            if self.assistant_agent is None:
                logger.error("AssistantAgent未能成功创建")
                return None
            if stream:
                stream = self.assistant_agent.run_stream(task=task)
                result_content = ""
                async for event in stream:
                    if isinstance(event, ModelClientStreamingChunkEvent):
                        await self.send_response(event.content)
                        continue
                    if isinstance(event, TaskResult):
                        messages = event.messages
                        if messages and hasattr(messages[-1], 'content'):
                            result_content = messages[-1].content
                            break
            else:
                result = await self.assistant_agent.run(task=task)
                result_content = result.messages[-1].content if result.messages else ""

            return result_content
            
        except Exception as e:
            logger.error(f"运行AssistantAgent失败: {str(e)}")
            return None
    
    def _extract_json_from_content(self, content: str) -> Optional[Dict[str, Any]]:
        """从内容中提取JSON数据 - 增强版本"""
        try:
            import re

            if not content or not content.strip():
                return None

            # 第一步：尝试直接解析整个内容
            try:
                return json.loads(content.strip())
            except json.JSONDecodeError:
                pass

            # 第二步：查找JSON代码块
            json_patterns = [
                r'```json\s*(.*?)\s*```',  # 标准markdown json块
                r'```\s*(.*?)\s*```',     # 普通代码块
                r'`(.*?)`'                # 单行代码块
            ]

            for pattern in json_patterns:
                json_matches = re.findall(pattern, content, re.DOTALL)
                for match in json_matches:
                    try:
                        cleaned_match = match.strip()
                        if cleaned_match.startswith('{') and cleaned_match.endswith('}'):
                            return json.loads(cleaned_match)
                    except json.JSONDecodeError:
                        continue

            # 第三步：使用更智能的JSON提取方法
            extracted_json = self._extract_complete_json_object(content)
            if extracted_json:
                return extracted_json

            # 第四步：尝试修复常见的JSON格式问题
            cleaned_content = self._clean_json_content(content)
            if cleaned_content:
                try:
                    return json.loads(cleaned_content)
                except json.JSONDecodeError:
                    pass

            logger.warning(f"无法从内容中提取有效JSON，内容前100字符: {content[:100]}")
            return None

        except Exception as e:
            logger.error(f"提取JSON失败: {str(e)}")
            return None

    def _extract_complete_json_object(self, content: str) -> Optional[Dict[str, Any]]:
        """智能提取完整的JSON对象，支持复杂嵌套结构"""
        try:
            # 查找所有可能的JSON起始位置
            start_positions = []
            for i, char in enumerate(content):
                if char == '{':
                    start_positions.append(i)

            # 收集所有有效的JSON对象
            valid_json_objects = []

            # 按起始位置尝试提取JSON
            for start_pos in start_positions:
                json_str = self._extract_balanced_json(content, start_pos)
                if json_str:
                    try:
                        parsed_json = json.loads(json_str)
                        # 验证这是一个有意义的JSON对象（不是空对象或只有一个简单字段）
                        if isinstance(parsed_json, dict) and len(parsed_json) > 0:
                            valid_json_objects.append({
                                'json': parsed_json,
                                'size': len(json_str),
                                'keys': list(parsed_json.keys()),
                                'start_pos': start_pos
                            })
                    except json.JSONDecodeError:
                        continue

            if not valid_json_objects:
                return None

            # 优先选择包含 test_cases 键的JSON对象
            test_cases_objects = [obj for obj in valid_json_objects if 'test_cases' in obj['keys']]
            if test_cases_objects:
                # 如果有多个包含test_cases的对象，选择最大的
                best_object = max(test_cases_objects, key=lambda x: x['size'])
                logger.info(f"选择包含test_cases的JSON对象，大小: {best_object['size']}, 键: {best_object['keys']}")
                return best_object['json']

            # 如果没有包含test_cases的对象，选择最大的JSON对象
            best_object = max(valid_json_objects, key=lambda x: x['size'])
            logger.info(f"选择最大的JSON对象，大小: {best_object['size']}, 键: {best_object['keys']}")
            return best_object['json']

        except Exception as e:
            logger.error(f"智能JSON提取失败: {str(e)}")
            return None

    def _extract_balanced_json(self, content: str, start_pos: int) -> Optional[str]:
        """从指定位置提取平衡的JSON字符串"""
        try:
            if start_pos >= len(content) or content[start_pos] != '{':
                return None

            brace_count = 0
            in_string = False
            escape_next = False

            for i in range(start_pos, len(content)):
                char = content[i]

                if escape_next:
                    escape_next = False
                    continue

                if char == '\\':
                    escape_next = True
                    continue

                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue

                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            # 找到完整的JSON对象
                            json_str = content[start_pos:i+1]
                            return json_str.strip()

            return None

        except Exception as e:
            logger.error(f"提取平衡JSON失败: {str(e)}")
            return None

    def _clean_json_content(self, content: str) -> Optional[str]:
        """清理和修复JSON内容"""
        try:
            import re

            # 移除markdown标记
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)

            # 移除注释
            content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

            # 修复常见的JSON问题
            content = re.sub(r',\s*}', '}', content)  # 移除对象末尾多余逗号
            content = re.sub(r',\s*]', ']', content)  # 移除数组末尾多余逗号

            # 修复未引用的键名
            content = re.sub(r'([{,]\s*)(\w+):', r'\1"\2":', content)

            # 查找最外层的JSON对象
            start_idx = content.find('{')
            if start_idx == -1:
                return None

            brace_count = 0
            end_idx = start_idx

            for i in range(start_idx, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i
                        break

            if brace_count == 0:
                return content[start_idx:end_idx + 1].strip()

            return None

        except Exception as e:
            logger.error(f"清理JSON内容失败: {str(e)}")
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

    async def _log_to_recorder(self, session_id: str, level: str, message: str, metadata: Dict[str, Any] = None):
        """发送日志到日志记录智能体

        Args:
            session_id: 会话ID
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: 日志消息
            metadata: 额外的元数据
        """
        try:
            from .schemas import LogRecordRequest, LogLevel
            from autogen_core import TopicId
            from app.core.types import TopicTypes

            # 转换日志级别
            log_level = getattr(LogLevel, level.upper(), LogLevel.INFO)

            # 创建日志记录请求
            log_request = LogRecordRequest(
                session_id=session_id,
                source=self.agent_name,
                level=log_level,
                message=message,
                metadata=metadata or {},
                operation=getattr(self, 'current_operation', 'unknown')
            )

            # 发送到日志记录智能体
            if hasattr(self, 'runtime') and self.runtime:
                await self.runtime.publish_message(
                    log_request,
                    topic_id=TopicId(type=TopicTypes.LOG_RECORDER.value, source=self.agent_name)
                )
            else:
                logger.warning(f"运行时未初始化，无法发送日志: {message}")

        except Exception as e:
            logger.error(f"发送日志到记录器失败: {str(e)}")

    async def _log_operation_start(self, session_id: str, operation: str, details: Dict[str, Any] = None):
        """记录操作开始日志"""
        self.current_operation = operation
        await self._log_to_recorder(
            session_id,
            "INFO",
            f"开始执行操作: {operation}",
            {
                "operation": operation,
                "step": "start",
                "details": details or {}
            }
        )

    async def _log_operation_progress(self, session_id: str, operation: str, step: str, details: Dict[str, Any] = None):
        """记录操作进度日志"""
        await self._log_to_recorder(
            session_id,
            "INFO",
            f"操作进度: {operation} - {step}",
            {
                "operation": operation,
                "step": step,
                "details": details or {}
            }
        )

    async def _log_operation_complete(self, session_id: str, operation: str, result: Dict[str, Any] = None):
        """记录操作完成日志"""
        await self._log_to_recorder(
            session_id,
            "INFO",
            f"操作完成: {operation}",
            {
                "operation": operation,
                "step": "complete",
                "result": result or {}
            }
        )

    async def _log_operation_error(self, session_id: str, operation: str, error: Exception, details: Dict[str, Any] = None):
        """记录操作错误日志"""
        await self._log_to_recorder(
            session_id,
            "ERROR",
            f"操作失败: {operation} - {str(error)}",
            {
                "operation": operation,
                "step": "error",
                "error_type": type(error).__name__,
                "error_message": str(error),
                "details": details or {}
            }
        )

    async def _ensure_database_connection(self):
        """确保数据库连接已建立（基类方法）"""
        if not self._db_initialized:
            try:
                # 检查Tortoise是否已初始化
                if not Tortoise._inited:
                    logger.info(f"[{self.agent_name}] 初始化Tortoise ORM连接...")
                    from app.settings.config import settings
                    await Tortoise.init(config=settings.TORTOISE_ORM)
                    logger.info(f"[{self.agent_name}] Tortoise ORM连接初始化成功")

                self._db_initialized = True

            except Exception as e:
                logger.error(f"[{self.agent_name}] 数据库连接初始化失败: {str(e)}")
                raise

    async def process_message(self, message: Any, ctx: MessageContext) -> None:
        """处理消息的默认实现 - 子类可以重写此方法"""
        # 这是一个默认实现，子类可以根据需要重写
        logger.info(f"[{self.agent_name}] 收到消息: {message}")
        # 子类应该重写此方法来处理具体的消息逻辑

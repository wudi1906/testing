"""
接口自动化测试系统 - 统一流式响应收集器
基于AutoGen框架的标准响应收集器
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Awaitable

from autogen_core import MessageContext, ClosureContext
from loguru import logger

from ..messages import StreamMessage
from ..types import AgentPlatform


class StreamResponseCollector:
    """统一流式响应收集器，用于收集智能体产生的流式输出"""

    def __init__(self, platform: AgentPlatform = AgentPlatform.API_AUTOMATION,
                 buffer_flush_interval: float = 0.3):
        """初始化流式响应收集器

        Args:
            platform: 平台类型
            buffer_flush_interval: 缓冲区刷新间隔（秒）
        """
        self.platform = platform
        self.callback: Optional[Callable[[ClosureContext, StreamMessage, MessageContext], Awaitable[None]]] = None
        self.user_input: Optional[Callable[[str, Any], Awaitable[str]]] = None
        self.message_buffers: Dict[str, str] = {}  # 用于缓存各智能体的消息
        self.last_flush_time: Dict[str, float] = {}  # 记录最后一次刷新缓冲区的时间
        self.buffer_flush_interval: float = buffer_flush_interval  # 缓冲区刷新间隔（秒）

        # 通用结果存储
        self.results: Dict[str, Any] = {}
        self.collected_data: List[Dict[str, Any]] = []
        self.session_metadata: Dict[str, Any] = {}

        logger.info(f"{platform.value}流式响应收集器初始化完成")

    def set_callback(self, callback: Callable[[ClosureContext, StreamMessage, MessageContext], Awaitable[None]]) -> None:
        """设置回调函数

        Args:
            callback: 用于处理响应消息的异步回调函数
        """
        self.callback = callback
        logger.debug("设置流式响应回调函数")

    def set_user_input(self, user_input: Callable[[str, Any], Awaitable[str]]) -> None:
        """设置用户输入函数

        Args:
            user_input: 用于获取用户输入的异步函数
        """
        self.user_input = user_input
        logger.debug("设置用户输入函数")

    def set_session_metadata(self, metadata: Dict[str, Any]) -> None:
        """设置会话元数据

        Args:
            metadata: 会话元数据
        """
        self.session_metadata.update(metadata)
        logger.debug(f"设置会话元数据: {list(metadata.keys())}")

    def add_result(self, key: str, value: Any) -> None:
        """添加结果数据

        Args:
            key: 结果键
            value: 结果值
        """
        self.results[key] = value
        logger.debug(f"添加结果数据: {key}")

    def get_result(self, key: str, default: Any = None) -> Any:
        """获取结果数据

        Args:
            key: 结果键
            default: 默认值

        Returns:
            Any: 结果值
        """
        return self.results.get(key, default)

    def add_collected_data(self, data: Dict[str, Any]) -> None:
        """添加收集的数据

        Args:
            data: 数据字典
        """
        data_with_timestamp = {
            **data,
            "collected_at": datetime.now().isoformat(),
            "platform": self.platform.value
        }
        self.collected_data.append(data_with_timestamp)
        logger.debug(f"添加收集数据: {data.get('type', 'unknown')}")

    def get_collected_data(self, data_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取收集的数据

        Args:
            data_type: 数据类型过滤器

        Returns:
            List[Dict[str, Any]]: 收集的数据列表
        """
        if data_type:
            return [data for data in self.collected_data if data.get('type') == data_type]
        return self.collected_data.copy()

    def clear_collected_data(self) -> None:
        """清空收集的数据"""
        self.collected_data.clear()
        logger.debug("清空收集的数据")

    def get_session_summary(self) -> Dict[str, Any]:
        """获取会话摘要

        Returns:
            Dict[str, Any]: 会话摘要信息
        """
        return {
            "platform": self.platform.value,
            "session_metadata": self.session_metadata,
            "results_count": len(self.results),
            "collected_data_count": len(self.collected_data),
            "message_buffers_count": len(self.message_buffers),
            "last_activity": datetime.now().isoformat()
        }

    async def process_stream_message(self, message: StreamMessage, ctx: MessageContext) -> None:
        """处理流式消息

        Args:
            message: 流式消息
            ctx: 消息上下文
        """
        try:
            # 记录消息到收集器
            self.add_collected_data({
                "type": "stream_message",
                "agent_name": message.agent_name,
                "content": message.content,
                "message_type": message.message_type,
                "is_final": message.is_final,
                "region": message.region,
                "timestamp": message.timestamp.isoformat()
            })

            # 如果有结果数据，保存到结果中
            if message.result:
                result_key = f"{message.agent_name}_{message.timestamp.timestamp()}"
                self.add_result(result_key, message.result)

            # 调用回调函数（如果设置了）
            if self.callback:
                await self.callback(ClosureContext(), message, ctx)

            logger.debug(f"处理流式消息: {message.agent_name} - {message.content[:50]}...")

        except Exception as e:
            logger.error(f"处理流式消息失败: {str(e)}")

    def get_agent_messages(self, agent_name: str) -> List[Dict[str, Any]]:
        """获取特定智能体的消息

        Args:
            agent_name: 智能体名称

        Returns:
            List[Dict[str, Any]]: 消息列表
        """
        return [
            data for data in self.collected_data 
            if data.get('type') == 'stream_message' and data.get('agent_name') == agent_name
        ]

    def get_messages_by_type(self, message_type: str) -> List[Dict[str, Any]]:
        """根据消息类型获取消息

        Args:
            message_type: 消息类型

        Returns:
            List[Dict[str, Any]]: 消息列表
        """
        return [
            data for data in self.collected_data 
            if data.get('type') == 'stream_message' and data.get('message_type') == message_type
        ]

    def get_error_messages(self) -> List[Dict[str, Any]]:
        """获取错误消息

        Returns:
            List[Dict[str, Any]]: 错误消息列表
        """
        return self.get_messages_by_type('error')

    def get_final_messages(self) -> List[Dict[str, Any]]:
        """获取最终消息

        Returns:
            List[Dict[str, Any]]: 最终消息列表
        """
        return [
            data for data in self.collected_data 
            if data.get('type') == 'stream_message' and data.get('is_final') is True
        ]

    def cleanup(self) -> None:
        """清理收集器资源"""
        try:
            self.message_buffers.clear()
            self.last_flush_time.clear()
            self.results.clear()
            self.collected_data.clear()
            self.session_metadata.clear()
            logger.info("流式响应收集器资源清理完成")
        except Exception as e:
            logger.error(f"清理收集器资源失败: {str(e)}")

    def export_data(self, format_type: str = "json") -> Dict[str, Any]:
        """导出收集的数据

        Args:
            format_type: 导出格式

        Returns:
            Dict[str, Any]: 导出的数据
        """
        export_data = {
            "platform": self.platform.value,
            "export_time": datetime.now().isoformat(),
            "session_metadata": self.session_metadata,
            "results": self.results,
            "collected_data": self.collected_data,
            "summary": self.get_session_summary()
        }

        logger.info(f"导出数据完成，格式: {format_type}")
        return export_data

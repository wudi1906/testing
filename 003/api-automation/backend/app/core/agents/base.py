"""
智能体基类
定义所有智能体的通用接口和功能，基于AutoGen Core
"""
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from datetime import datetime

from autogen_core import RoutedAgent, MessageContext, TopicId, ClosureContext
from loguru import logger

from ..messages import StreamMessage
from .collector import StreamResponseCollector
from ..types import AgentPlatform, MessageRegion, TopicTypes


class BaseAgent(RoutedAgent, ABC):
    """统一智能体基类，提供所有智能体的共享功能"""

    def __init__(self, agent_id: str, agent_name: str, platform: AgentPlatform = AgentPlatform.API_AUTOMATION,
                 model_client_instance=None, **kwargs):
        """初始化基础智能体

        Args:
            agent_id: 智能体ID
            agent_name: 智能体名称（用于显示）
            platform: 智能体平台类型
            model_client_instance: 模型客户端实例
            **kwargs: 其他初始化参数
        """
        super().__init__(agent_id)
        self.agent_name = agent_name
        self.platform = platform
        self.model_client = model_client_instance
        self.agent_metadata = kwargs
        self.performance_metrics = {}
        self.created_at = datetime.now()

        # 智能体状态
        self.is_active = True
        self.message_count = 0
        self.error_count = 0

        logger.info(f"初始化 {agent_name} 智能体 (ID: {agent_id})")

    async def _send_message(self, content: str, message_type: str = "info", 
                          is_final: bool = False, result: Optional[Dict[str, Any]] = None,
                          region: MessageRegion = MessageRegion.PROCESS) -> None:
        """发送流式消息到收集器

        Args:
            content: 消息内容
            message_type: 消息类型
            is_final: 是否为最终消息
            result: 结果数据
            region: 消息区域
        """
        try:
            stream_message = StreamMessage(
                content=content,
                message_type=message_type,
                is_final=is_final,
                result=result,
                region=region.value,
                agent_name=self.agent_name,
                timestamp=datetime.now()
            )

            # 发布到流式响应主题
            await self.publish_message(
                stream_message,
                topic_id=TopicId(type="stream_response", source=self.id.key)
            )

            self.message_count += 1
            logger.debug(f"[{self.agent_name}] 发送消息: {content[:50]}...")

        except Exception as e:
            logger.error(f"[{self.agent_name}] 发送消息失败: {str(e)}")

    async def send_response(self, content: str, is_final: bool = False, 
                          result: Optional[Dict[str, Any]] = None, 
                          error: Optional[str] = None,
                          region: str = "process") -> None:
        """发送响应消息"""
        message_type = "error" if error else "info"
        region_enum = MessageRegion.ERROR if error else MessageRegion.PROCESS
        
        if error:
            content = f"❌ {content}"
            self.error_count += 1
        
        await self._send_message(content, message_type, is_final, result, region_enum)

    async def send_progress(self, content: str, current: int = 0, total: int = 100) -> None:
        """发送进度消息"""
        progress_content = f"⏳ {content} ({current}/{total})"
        await self._send_message(progress_content, "progress", False, 
                                {"current": current, "total": total}, MessageRegion.PROCESS)

    async def send_success(self, content: str, result: Optional[Dict[str, Any]] = None) -> None:
        """发送成功消息"""
        await self._send_message(f"✅ {content}", "success", True, result, MessageRegion.SUCCESS)

    async def send_warning(self, content: str) -> None:
        """发送警告消息"""
        await self._send_message(f"⚠️ {content}", "warning", False, None, MessageRegion.WARNING)

    async def send_error(self, content: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """发送错误消息"""
        await self._send_message(f"❌ {content}", "error", True, error_details, MessageRegion.ERROR)

    async def send_info(self, content: str) -> None:
        """发送信息消息"""
        await self._send_message(f"ℹ️ {content}", "info", False, None, MessageRegion.INFO)

    async def handle_exception(self, func_name: str, exception: Exception,
                             send_error_message: bool = True) -> None:
        """处理异常并可选发送错误消息

        Args:
            func_name: 发生异常的函数名
            exception: 异常对象
            send_error_message: 是否发送错误消息到流
        """
        error_msg = f"在{func_name}中发生错误: {str(exception)}"
        logger.error(f"[{self.agent_name}] {error_msg}")

        if send_error_message:
            await self.send_error(error_msg)

        self.error_count += 1

    def update_performance_metrics(self, operation: str, duration: float, success: bool = True) -> None:
        """更新性能指标

        Args:
            operation: 操作名称
            duration: 执行时长
            success: 是否成功
        """
        if operation not in self.performance_metrics:
            self.performance_metrics[operation] = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
                "min_duration": float('inf'),
                "max_duration": 0.0
            }

        metrics = self.performance_metrics[operation]
        metrics["total_calls"] += 1
        metrics["total_duration"] += duration

        if success:
            metrics["successful_calls"] += 1
        else:
            metrics["failed_calls"] += 1

        metrics["avg_duration"] = metrics["total_duration"] / metrics["total_calls"]
        metrics["min_duration"] = min(metrics["min_duration"], duration)
        metrics["max_duration"] = max(metrics["max_duration"], duration)

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        return {
            "agent_name": self.agent_name,
            "agent_id": self.id.key,
            "platform": self.platform.value,
            "created_at": self.created_at.isoformat(),
            "is_active": self.is_active,
            "message_count": self.message_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.message_count, 1),
            "operations": self.performance_metrics
        }

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "agent_id": self.id.key,
            "agent_name": self.agent_name,
            "status": "healthy" if self.is_active else "inactive",
            "uptime": (datetime.now() - self.created_at).total_seconds(),
            "message_count": self.message_count,
            "error_count": self.error_count,
            "last_activity": datetime.now().isoformat()
        }

    async def cleanup(self):
        """清理智能体资源"""
        try:
            self.is_active = False
            # 清理性能监控数据
            self.performance_metrics.clear()
            logger.info(f"智能体资源清理完成: {self.agent_name}")
        except Exception as e:
            logger.error(f"清理智能体资源失败: {str(e)}")

    @abstractmethod
    async def process_message(self, message: Any, ctx: MessageContext) -> None:
        """处理消息的抽象方法，子类必须实现"""
        pass

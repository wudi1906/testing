"""
运行时管理器
管理智能体运行时的创建、初始化和生命周期
"""
import asyncio
from typing import Optional, Dict, Any
from autogen_core import SingleThreadedAgentRuntime
from loguru import logger

from app.agents.factory import agent_factory
from .collector import StreamResponseCollector


class RuntimeManager:
    """运行时管理器 - 单例模式"""
    
    _instance: Optional['RuntimeManager'] = None
    _runtime: Optional[SingleThreadedAgentRuntime] = None
    _initialized: bool = False
    _response_collector: Optional[StreamResponseCollector] = None
    
    def __new__(cls) -> 'RuntimeManager':
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def get_runtime(self) -> SingleThreadedAgentRuntime:
        """获取运行时实例，如果不存在则创建并初始化"""
        if self._runtime is None or not self._initialized:
            await self._initialize_runtime()
        return self._runtime
    
    async def _initialize_runtime(self) -> None:
        """初始化运行时"""
        try:
            logger.info("🚀 初始化智能体运行时...")
            
            # 创建运行时
            self._runtime = SingleThreadedAgentRuntime()
            
            # 创建响应收集器
            self._response_collector = StreamResponseCollector()
            
            # 注册所有智能体到运行时
            await agent_factory.register_agents_to_runtime(self._runtime)
            
            # 注册响应收集器
            await agent_factory.register_stream_collector(
                runtime=self._runtime,
                collector=self._response_collector
            )
            
            # 启动运行时
            self._runtime.start()
            
            self._initialized = True
            logger.info("✅ 智能体运行时初始化完成")
            
        except Exception as e:
            logger.error(f"❌ 智能体运行时初始化失败: {str(e)}")
            self._runtime = None
            self._initialized = False
            raise
    
    def get_response_collector(self) -> Optional[StreamResponseCollector]:
        """获取响应收集器"""
        return self._response_collector
    
    async def shutdown(self) -> None:
        """关闭运行时"""
        try:
            if self._runtime is not None:
                logger.info("🔄 关闭智能体运行时...")
                await self._runtime.stop()
                self._runtime = None
                self._initialized = False
                self._response_collector = None
                logger.info("✅ 智能体运行时已关闭")
        except Exception as e:
            logger.error(f"❌ 关闭智能体运行时失败: {str(e)}")
    
    def is_initialized(self) -> bool:
        """检查运行时是否已初始化"""
        return self._initialized and self._runtime is not None
    
    def get_status(self) -> Dict[str, Any]:
        """获取运行时状态"""
        return {
            "initialized": self._initialized,
            "runtime_exists": self._runtime is not None,
            "response_collector_exists": self._response_collector is not None,
            "registered_agents": agent_factory.list_runtime_agents() if self._initialized else []
        }


# 全局运行时管理器实例
runtime_manager = RuntimeManager()

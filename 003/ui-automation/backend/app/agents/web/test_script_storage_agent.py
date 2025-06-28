"""
脚本数据库保存智能体
负责接收YAML和Playwright生成智能体的脚本信息，将其保存到数据库中
"""
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from loguru import logger
from pydantic import BaseModel, Field

from app.core.agents.base import BaseAgent
from app.core.types import TopicTypes, AgentTypes, AGENT_NAMES, MessageRegion
from app.core.messages.web import WebMultimodalAnalysisResponse
from app.services.database_script_service import database_script_service
from app.models.test_scripts import ScriptFormat, ScriptType


class ScriptSaveRequest(BaseModel):
    """脚本保存请求消息"""
    session_id: str = Field(..., description="会话ID")
    script_content: str = Field(..., description="脚本内容")
    script_format: ScriptFormat = Field(..., description="脚本格式")
    script_type: ScriptType = Field(..., description="脚本类型")
    analysis_result: WebMultimodalAnalysisResponse = Field(..., description="分析结果")
    script_name: Optional[str] = Field(None, description="脚本名称")
    script_description: Optional[str] = Field(None, description="脚本描述")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    category: Optional[str] = Field(None, description="脚本分类")
    priority: int = Field(1, ge=1, le=5, description="优先级(1-5)")
    source_agent: Optional[str] = Field(None, description="来源智能体")
    file_path: Optional[str] = Field(None, description="文件路径")

    class Config:
        """Pydantic配置"""
        arbitrary_types_allowed = True  # 允许任意类型，用于WebMultimodalAnalysisResponse


@type_subscription(topic_type=TopicTypes.SCRIPT_DATABASE_SAVER.value)
class ScriptDatabaseSaverAgent(BaseAgent):
    """脚本数据库保存智能体，负责将生成的脚本保存到数据库"""

    def __init__(self, model_client_instance=None, **kwargs):
        """初始化脚本数据库保存智能体"""
        super().__init__(
            agent_id=AgentTypes.SCRIPT_DATABASE_SAVER.value,
            agent_name=AGENT_NAMES[AgentTypes.SCRIPT_DATABASE_SAVER.value],
            model_client_instance=model_client_instance,
            **kwargs
        )
        
        logger.info(f"脚本数据库保存智能体初始化完成: {self.agent_name}")

    @message_handler
    async def handle_script_save_request(self, message: ScriptSaveRequest, ctx: MessageContext) -> None:
        """处理脚本保存请求"""
        try:
            monitor_id = self.start_performance_monitoring("script_save")
            
            await self.send_message(
                f"📝 开始保存脚本到数据库 (来源: {message.source_agent}) \n\n",
                region=MessageRegion.PROCESS
            )
            
            # 生成脚本名称（如果未提供）
            script_name = message.script_name
            if not script_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                format_name = "YAML" if message.script_format == ScriptFormat.YAML else "Playwright"
                script_name = f"{format_name}脚本_{timestamp}"
            
            # 生成脚本描述（如果未提供）
            script_description = message.script_description
            if not script_description:
                analysis = message.analysis_result.page_analysis
                script_description = f"基于{analysis.page_title}页面分析生成的{message.script_format.value}脚本"
            
            # 准备保存数据
            save_data = {
                "session_id": message.session_id,
                "name": script_name,
                "description": script_description,
                "content": message.script_content,
                "script_format": message.script_format,
                "script_type": message.script_type,
                "test_description": getattr(message.analysis_result, 'test_description', ''),
                "additional_context": getattr(message.analysis_result, 'additional_context', ''),
                "analysis_result_id": message.analysis_result.analysis_id,
                "source_url": getattr(message.analysis_result, 'source_url', None),
                "source_image_path": getattr(message.analysis_result, 'source_image_path', ''),
                "file_path": message.file_path,
            }
            
            await self.send_message(
                f"💾 正在保存脚本: {script_name}\n\n",
                region=MessageRegion.PROCESS
            )
            
            # 保存脚本到数据库
            saved_script = await database_script_service.create_script_from_analysis(**save_data)
            
            # 设置额外属性
            updates = {}
            if message.tags:
                updates["tags"] = message.tags
            if message.category:
                updates["category"] = message.category
            if message.priority != 1:
                updates["priority"] = message.priority
            
            if updates:
                saved_script = await database_script_service.update_script(saved_script.id, updates)
            
            # 记录性能指标
            metrics = self.end_performance_monitoring(monitor_id)
            
            # 构建保存结果
            save_result = {
                "script_id": saved_script.id,
                "script_name": saved_script.name,
                "script_format": saved_script.script_format.value,
                "script_type": saved_script.script_type.value,
                "created_at": self._format_datetime(saved_script.created_at),
                "tags": saved_script.tags,
                "category": saved_script.category,
                "priority": saved_script.priority,
                "file_path": saved_script.file_path,  # 使用数据库中的file_path
                "source_agent": message.source_agent,
                "metrics": metrics
            }
            
            await self.send_response(
                f"脚本已成功保存到数据库: {saved_script.name} (ID: {saved_script.id})\n\n",
                result=save_result,
                region=MessageRegion.GENERATION,
            )
            
            logger.info(f"脚本保存成功: {saved_script.id} - {saved_script.name}")
            
        except Exception as e:
            await self.handle_exception("handle_script_save_request", e)

    def _format_datetime(self, dt) -> Optional[str]:
        """格式化日期时间对象为ISO字符串

        Args:
            dt: 日期时间对象（可能是datetime、字符串或None）

        Returns:
            Optional[str]: ISO格式的日期时间字符串，如果输入为None则返回None
        """
        if dt is None:
            return None

        # 如果已经是字符串，直接返回
        if isinstance(dt, str):
            return dt

        # 如果是datetime对象，转换为ISO格式
        if hasattr(dt, 'isoformat'):
            return dt.isoformat()

        # 其他情况，转换为字符串
        return str(dt)


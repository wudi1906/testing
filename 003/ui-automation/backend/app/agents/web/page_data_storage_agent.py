"""
页面分析存储智能体
专门负责将页面分析结果保存到MySQL数据库中
"""
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from loguru import logger

from app.core.messages.web import (
    PageAnalysisStorageRequest, PageAnalysisStorageResponse,
    PageAnalysis, UIElement
)
from app.core.agents.base import BaseAgent
from app.core.types import TopicTypes, AgentTypes, AGENT_NAMES
from app.database.connection import db_manager
from app.database.models.page_analysis import PageAnalysisResult, PageElement
from app.database.repositories.page_analysis_repository import PageAnalysisRepository, PageElementRepository


@type_subscription(topic_type=TopicTypes.PAGE_ANALYSIS_STORAGE.value)
class PageAnalysisStorageAgent(BaseAgent):
    """页面分析存储智能体，负责将分析结果保存到数据库"""

    def __init__(self, **kwargs):
        """初始化页面分析存储智能体"""
        super().__init__(
            agent_id=AgentTypes.PAGE_ANALYSIS_STORAGE.value,
            agent_name=AGENT_NAMES.get(AgentTypes.PAGE_ANALYSIS_STORAGE.value, "页面分析存储智能体"),
            **kwargs
        )

        # 初始化仓库
        self.page_analysis_repo = PageAnalysisRepository()
        self.page_element_repo = PageElementRepository()

        logger.info("页面分析存储智能体初始化完成")

    @message_handler
    async def handle_message(self, message: PageAnalysisStorageRequest, ctx: MessageContext) -> None:
        """处理页面分析存储请求"""
        try:
            logger.info(f"收到页面分析存储请求，会话ID: {message.session_id}")
            
            # 开始性能监控
            monitor_id = self.start_performance_monitoring()
            
            # 保存页面分析结果到数据库
            storage_result = await self._save_page_analysis_to_database(message)
            
            # 结束性能监控
            metrics = self.end_performance_monitoring(monitor_id)
            
            # 发送响应
            response = PageAnalysisStorageResponse(
                session_id=message.session_id,
                analysis_id=message.analysis_id,
                storage_id=storage_result["storage_id"],
                status="success",
                message=f"页面分析结果已成功保存到数据库，存储了 {storage_result['elements_count']} 个页面元素",
                stored_elements_count=storage_result["elements_count"]
            )
            
            await self.send_response(
                f"✅ 页面分析结果存储完成\n"
                f"📄 页面名称: {message.page_name}\n"
                f"🔍 分析ID: {message.analysis_id}\n"
                f"💾 存储ID: {storage_result['storage_id']}\n"
                f"📊 元素数量: {storage_result['elements_count']}\n"
                f"⏱️ 处理时间: {metrics.get('duration_seconds', 0):.2f}秒",
                is_final=True,
                result={
                    "storage_result": response.model_dump(),
                    "metrics": metrics
                }
            )
            
            logger.info(f"页面分析结果存储完成，存储ID: {storage_result['storage_id']}")
            
        except Exception as e:
            await self.handle_exception("handle_message", e)

    async def _save_page_analysis_to_database(self, request: PageAnalysisStorageRequest) -> Dict[str, Any]:
        """保存页面分析结果到数据库"""
        try:
            async with db_manager.get_session() as session:
                # 准备页面分析数据
                analysis_data = {
                    "id": str(uuid.uuid4()),
                    "session_id": request.session_id,
                    "analysis_id": request.analysis_id,
                    "page_name": request.page_name,
                    "page_url": request.page_url,
                    "page_type": request.page_type,
                    "page_description": request.page_description,
                    "analysis_summary": request.analysis_result.analysis_summary,
                    "confidence_score": request.confidence_score,
                    "raw_analysis_json": request.analysis_metadata.get("raw_json", {}),
                    "parsed_ui_elements": request.analysis_metadata.get("parsed_elements", []),
                    "analysis_metadata": request.analysis_metadata,
                    "processing_time": request.analysis_metadata.get("processing_time", 0.0)
                }

                # 准备页面元素数据
                elements_data = await self._prepare_elements_data(request.analysis_result, request.analysis_metadata)

                # 使用仓库创建页面分析结果及元素
                page_analysis_result = await self.page_analysis_repo.create_with_elements(
                    session, analysis_data, elements_data
                )

                await session.commit()

                logger.info(f"页面分析结果已保存到数据库，ID: {page_analysis_result.id}")

                return {
                    "storage_id": page_analysis_result.id,
                    "elements_count": len(elements_data)
                }

        except Exception as e:
            logger.error(f"保存页面分析结果到数据库失败: {str(e)}")
            raise

    async def _prepare_elements_data(self, analysis_result: PageAnalysis, analysis_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """准备页面元素数据"""
        try:
            elements_data = []

            # 从分析元数据中获取解析后的元素
            parsed_elements = analysis_metadata.get("parsed_elements", [])

            # 如果没有解析后的元素，则从ui_elements中解析
            if not parsed_elements:
                for i, ui_element in enumerate(analysis_result.ui_elements):
                    try:
                        if isinstance(ui_element, str):
                            element_info = await self._parse_element_from_string(ui_element, i)
                        else:
                            element_info = ui_element
                        parsed_elements.append(element_info)
                    except Exception as e:
                        logger.warning(f"解析页面元素失败，跳过: {str(e)}")
                        continue

            # 转换为数据库格式
            for i, element_data in enumerate(parsed_elements):
                try:
                    if isinstance(element_data, str):
                        element_data = await self._parse_element_from_string(element_data, i)

                    # 确保element_data是字典类型
                    if not isinstance(element_data, dict):
                        logger.warning(f"元素数据格式错误，跳过: {element_data}")
                        continue

                    # 提取元素信息，支持新的JSON格式
                    element_name = element_data.get("name", element_data.get("element_name", f"元素_{i+1}"))
                    element_type = element_data.get("element_type", element_data.get("type", "unknown"))
                    element_description = element_data.get("description", "")

                    # 构建完整的元素数据
                    complete_element_data = {
                        "id": element_data.get("id", f"element_{i+1:03d}"),
                        "name": element_name,
                        "element_type": element_type,
                        "description": element_description,
                        "text_content": element_data.get("text_content", ""),
                        "position": element_data.get("position", {}),
                        "visual_features": element_data.get("visual_features", {}),
                        "functionality": element_data.get("functionality", ""),
                        "interaction_state": element_data.get("interaction_state", "unknown"),
                        "confidence_score": element_data.get("confidence_score", 0.8),
                        "is_testable": self._determine_testability(element_type, element_data.get("interaction_state", "unknown"))
                    }

                    element_record = {
                        "id": str(uuid.uuid4()),
                        "element_name": element_name,
                        "element_type": element_type,
                        "element_description": element_description,
                        "element_data": complete_element_data,  # 存储完整的元素数据
                        "confidence_score": element_data.get("confidence_score", 0.8),
                        "is_testable": complete_element_data["is_testable"]
                    }

                    elements_data.append(element_record)

                except Exception as e:
                    logger.warning(f"准备页面元素数据失败，跳过: {str(e)}")
                    continue

            logger.info(f"成功准备了 {len(elements_data)} 个页面元素数据")
            return elements_data

        except Exception as e:
            logger.error(f"准备页面元素数据失败: {str(e)}")
            return []

    def _determine_testability(self, element_type: str, interaction_state: str) -> bool:
        """确定元素是否可测试"""
        # 交互元素通常可测试
        interactive_types = {
            "button", "link", "input", "textarea", "select", "checkbox",
            "radio", "switch", "slider", "dropdown", "menu", "tab"
        }

        # 可点击状态的元素可测试
        clickable_states = {"可点击", "clickable", "enabled", "active"}

        # 静态元素通常不可测试
        static_states = {"static", "disabled", "readonly", "禁用", "只读"}

        if element_type.lower() in interactive_types:
            return interaction_state.lower() not in static_states

        if interaction_state.lower() in clickable_states:
            return True

        if interaction_state.lower() in static_states:
            return False

        # 默认情况下，非静态元素可测试
        return element_type.lower() not in {"text", "image", "label", "span", "div"}

    async def _save_page_elements(self, session, page_analysis_id: str, analysis_result: PageAnalysis) -> int:
        """保存页面元素到数据库"""
        try:
            elements_count = 0

            # 从分析结果中获取解析后的元素数据
            parsed_elements = []

            # 尝试从analysis_metadata中获取解析后的元素
            analysis_metadata = getattr(analysis_result, 'analysis_metadata', {})
            if isinstance(analysis_metadata, dict):
                parsed_elements = analysis_metadata.get("parsed_elements", [])

            # 如果没有解析后的元素，则从ui_elements中解析
            if not parsed_elements:
                for i, ui_element_str in enumerate(analysis_result.ui_elements):
                    try:
                        element_info = await self._parse_element_from_string(ui_element_str, i)
                        parsed_elements.append(element_info)
                    except Exception as e:
                        logger.warning(f"解析页面元素失败，跳过: {str(e)}")
                        continue

            # 保存解析后的元素
            for i, element_data in enumerate(parsed_elements):
                try:
                    if isinstance(element_data, str):
                        element_data = await self._parse_element_from_string(element_data, i)

                    page_element = PageElement(
                        id=str(uuid.uuid4()),
                        page_analysis_id=page_analysis_id,
                        element_name=element_data.get("name", f"元素_{i+1}"),
                        element_type=element_data.get("element_type", element_data.get("type", "unknown")),
                        element_description=element_data.get("description", ""),
                        element_data=element_data,  # 存储完整的元素数据
                        confidence_score=element_data.get("confidence_score", 0.8),
                        is_testable=element_data.get("is_testable", True)
                    )

                    session.add(page_element)
                    elements_count += 1

                except Exception as e:
                    logger.warning(f"保存页面元素失败，跳过: {str(e)}")
                    continue

            return elements_count

        except Exception as e:
            logger.error(f"保存页面元素失败: {str(e)}")
            return 0

    async def _parse_element_from_string(self, element_str: str, index: int) -> Dict[str, Any]:
        """从字符串中解析元素信息"""
        try:
            # 尝试解析JSON格式
            if element_str.strip().startswith('{'):
                try:
                    return json.loads(element_str)
                except json.JSONDecodeError:
                    pass
            
            # 如果不是JSON，则进行文本解析
            element_info = {
                "name": f"元素_{index+1}",
                "type": "unknown",
                "description": element_str[:500],
                "location": "",
                "selector": "",
                "attributes": {},
                "visual_features": {},
                "functionality": "",
                "interaction_state": "unknown",
                "confidence_score": 0.7,
                "is_testable": True,
                "test_priority": "medium"
            }
            
            # 简单的关键词匹配来推断元素类型
            element_str_lower = element_str.lower()
            if "按钮" in element_str or "button" in element_str_lower:
                element_info["type"] = "button"
                element_info["functionality"] = "点击操作"
                element_info["interaction_state"] = "clickable"
            elif "输入" in element_str or "input" in element_str_lower:
                element_info["type"] = "input"
                element_info["functionality"] = "文本输入"
                element_info["interaction_state"] = "editable"
            elif "链接" in element_str or "link" in element_str_lower:
                element_info["type"] = "link"
                element_info["functionality"] = "页面导航"
                element_info["interaction_state"] = "clickable"
            elif "图片" in element_str or "image" in element_str_lower:
                element_info["type"] = "image"
                element_info["functionality"] = "内容展示"
                element_info["interaction_state"] = "static"
            elif "文本" in element_str or "text" in element_str_lower:
                element_info["type"] = "text"
                element_info["functionality"] = "信息展示"
                element_info["interaction_state"] = "static"
            
            return element_info
            
        except Exception as e:
            logger.warning(f"解析元素信息失败: {str(e)}")
            return {
                "name": f"元素_{index+1}",
                "type": "unknown",
                "description": element_str[:500] if element_str else "",
                "confidence_score": 0.5
            }

    async def get_page_analysis_by_id(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """根据分析ID查询页面分析结果"""
        try:
            async with db_manager.get_session() as session:
                result = await self.page_analysis_repo.get_with_elements(session, analysis_id)

                if not result:
                    return None

                return {
                    "page_analysis": result["page_analysis"].to_dict(),
                    "page_elements": [element.to_dict() for element in result["page_elements"]]
                }

        except Exception as e:
            logger.error(f"查询页面分析结果失败: {str(e)}")
            return None

    async def get_page_analysis_by_name(self, page_name: str) -> List[Dict[str, Any]]:
        """根据页面名称查询页面分析结果"""
        try:
            async with db_manager.get_session() as session:
                page_analyses = await self.page_analysis_repo.search_by_page_name(session, page_name)

                results = []
                for page_analysis in page_analyses:
                    # 获取关联的页面元素
                    page_elements = await self.page_element_repo.get_by_analysis_id(session, page_analysis.id)

                    results.append({
                        "page_analysis": page_analysis.to_dict(),
                        "page_elements": [element.to_dict() for element in page_elements]
                    })

                return results

        except Exception as e:
            logger.error(f"根据页面名称查询分析结果失败: {str(e)}")
            return []

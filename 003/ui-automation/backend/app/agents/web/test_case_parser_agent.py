"""
测试用例元素解析智能体
根据用户编写的测试用例内容，智能分析并从数据库中获取相应的页面元素信息
对返回的数据进行整理分类，为脚本生成智能体提供结构化的页面元素数据
"""
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import ModelClientStreamingChunkEvent, TextMessage
from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from autogen_agentchat.agents import AssistantAgent
from autogen_core.memory import ListMemory
from loguru import logger

from app.core.messages.web import (
    TestCaseElementParseRequest, 
    TestCaseElementParseResponse,
    ParsedPageElement,
    ParsedPageInfo,
    WebMultimodalAnalysisResponse
)
from app.core.agents.base import BaseAgent
from app.core.types import TopicTypes, AgentTypes, AGENT_NAMES, MessageRegion
from app.database.repositories.page_analysis_repository import PageAnalysisRepository, PageElementRepository
from app.database.connection import db_manager


@type_subscription(topic_type=TopicTypes.TEST_CASE_ELEMENT_PARSER.value)
class TestCaseElementParserAgent(BaseAgent):
    """测试用例元素解析智能体，负责根据测试用例解析页面元素"""

    def __init__(self, model_client_instance=None, **kwargs):
        """初始化测试用例元素解析智能体"""
        super().__init__(
            agent_id=AgentTypes.TEST_CASE_ELEMENT_PARSER.value,
            agent_name=AGENT_NAMES[AgentTypes.TEST_CASE_ELEMENT_PARSER.value],
            model_client_instance=model_client_instance,
            **kwargs
        )
        self._prompt_template = self._build_prompt_template()
        self.metrics = None
        self.page_analysis_repo = PageAnalysisRepository()
        self.page_element_repo = PageElementRepository()

        logger.info(f"测试用例元素解析智能体初始化完成: {self.agent_name}")

    @classmethod
    def create_assistant_agent(cls, model_client_instance=None, **kwargs) -> AssistantAgent:
        """创建用于测试用例分析的AssistantAgent实例"""
        from app.agents.factory import agent_factory

        return agent_factory.create_assistant_agent(
            name="test_case_element_parser",
            system_message=cls._build_prompt_template_static(),
            model_client_type="deepseek",
            model_client_stream=True,
            **kwargs
        )

    @staticmethod
    def _build_prompt_template_static() -> str:
        """构建静态的测试用例分析提示模板（用于工厂方法）"""
        return """
你是测试用例元素解析专家，专门分析用户编写的测试用例内容，提取其中涉及的页面和UI元素信息。

## 核心职责

1. **测试用例分析**: 深度理解用户编写的测试用例内容
2. **页面识别**: 识别测试用例中涉及的页面名称、页面类型
3. **元素提取**: 提取测试用例中提到的UI元素、操作对象
4. **关键词匹配**: 生成用于数据库查询的关键词和条件

## 分析要求

### 页面信息提取
- 识别页面名称（如：登录页面、首页、商品详情页等）
- 推断页面类型（如：form、list、detail、dashboard等）
- 提取页面相关的URL或路径信息

### 元素信息提取
- 识别UI元素类型（如：button、input、link、dropdown等）
- 提取元素描述和功能说明
- 识别元素的交互方式（点击、输入、选择等）
- 推断元素的重要性和测试优先级

### 查询条件生成
- 生成页面名称的模糊匹配关键词
- 生成元素类型的精确匹配条件
- 生成元素描述的关键词匹配条件

## 输出格式

请以JSON格式输出分析结果：

```json
{
  "analysis_summary": "测试用例分析总结",
  "identified_pages": [
    {
      "page_name": "页面名称",
      "page_type": "页面类型",
      "keywords": ["关键词1", "关键词2"],
      "confidence": 0.9
    }
  ],
  "identified_elements": [
    {
      "element_type": "元素类型",
      "element_description": "元素描述",
      "keywords": ["关键词1", "关键词2"],
      "interaction_type": "交互类型",
      "priority": "high|medium|low",
      "confidence": 0.8
    }
  ],
  "search_strategy": {
    "page_filters": ["页面过滤条件"],
    "element_filters": ["元素过滤条件"],
    "confidence_threshold": 0.7
  }
}
```

请确保分析结果准确、全面，为后续的数据库查询和元素匹配提供可靠的依据。
"""

    def _build_prompt_template(self) -> str:
        """构建测试用例分析提示模板"""
        return self._build_prompt_template_static()

    @message_handler
    async def handle_message(self, message: TestCaseElementParseRequest, ctx: MessageContext) -> None:
        """处理测试用例元素解析请求"""
        try:
            monitor_id = self.start_performance_monitoring()
            
            await self.send_response("🔍 开始分析测试用例内容...")

            # 1. 使用LLM分析测试用例
            analysis_result = await self._analyze_test_case_content(message)
            
            await self.send_response("📊 正在查询数据库中的页面元素...")

            # 2. 根据分析结果查询数据库
            database_results = await self._query_database_elements(analysis_result, message)
            
            await self.send_response("🔧 正在整理和分类页面元素...")

            # 3. 整理和分类数据
            parsed_data = await self._organize_and_classify_data(
                analysis_result, database_results, message
            )

            self.metrics = self.end_performance_monitoring(monitor_id)

            # 4. 构建响应
            response = TestCaseElementParseResponse(
                session_id=message.session_id,
                parse_id=str(uuid.uuid4()),
                test_case_content=message.test_case_content,
                parsed_pages=parsed_data["pages"],
                element_summary=parsed_data["summary"],
                analysis_insights=parsed_data["insights"],
                recommendations=parsed_data["recommendations"],
                confidence_score=parsed_data["confidence_score"],
                processing_time=self.metrics.get("total_time", 0.0),
                status="success",
                message="测试用例元素解析完成"
            )

            # 添加数据库查询结果到响应中
            response.database_results = database_results

            # 5. 发送给脚本生成智能体
            await self._send_to_script_generators(response, message)

            await self.send_response(
                "✅ 测试用例元素解析完成",
                is_final=True,
                result={
                    "parsed_pages": len(parsed_data["pages"]),
                    "total_elements": sum(len(page.elements) for page in parsed_data["pages"]),
                    "confidence_score": parsed_data["confidence_score"],
                    "metrics": self.metrics
                }
            )

        except Exception as e:
            await self.handle_exception("handle_message", e)

    async def _analyze_test_case_content(self, message: TestCaseElementParseRequest) -> Dict[str, Any]:
        """使用LLM分析测试用例内容"""
        try:
            # 创建分析智能体
            agent = self.create_assistant_agent()
            
            # 构建分析任务
            task = f"""
请分析以下测试用例内容，提取页面和元素信息：

**测试用例内容**:
{message.test_case_content}

**测试描述**: {message.test_description or '无'}
**目标格式**: {message.target_format}
**额外上下文**: {message.additional_context or '无'}

请按照系统提示的JSON格式输出分析结果。
"""

            # 执行分析
            full_content = ""
            stream = agent.run_stream(task=task)
            async for event in stream:
                if isinstance(event, ModelClientStreamingChunkEvent):
                    await self.send_response(content=event.content, region=MessageRegion.ANALYSIS)
                    continue
                if isinstance(event, TextMessage):
                    full_content = event.content

            # 解析JSON结果
            return await self._parse_analysis_result(full_content)

        except Exception as e:
            logger.error(f"分析测试用例内容失败: {str(e)}")
            raise

    async def _parse_analysis_result(self, content: str) -> Dict[str, Any]:
        """解析LLM分析结果"""
        try:
            # 尝试提取JSON内容
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 如果没有代码块，尝试直接解析
                json_str = content.strip()

            result = json.loads(json_str)
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败，使用默认结果: {str(e)}")
            return {
                "analysis_summary": "分析失败，使用默认配置",
                "identified_pages": [],
                "identified_elements": [],
                "search_strategy": {
                    "page_filters": [],
                    "element_filters": [],
                    "confidence_threshold": 0.5
                }
            }

    async def _query_database_elements(self, analysis_result: Dict[str, Any],
                                     message: TestCaseElementParseRequest) -> Dict[str, Any]:
        """根据分析结果查询数据库中的页面元素"""
        try:
            await db_manager.initialize()

            async with db_manager.get_session() as session:
                database_results = {
                    "pages": [],
                    "elements": [],
                    "total_pages": 0,
                    "total_elements": 0,
                    "selected_page_ids": message.selected_page_ids or []
                }

                # 添加调试日志
                logger.info(f"🔍 开始查询数据库元素，用户选择的页面ID: {message.selected_page_ids}")
                await self.send_response(f"🔍 开始查询数据库元素，用户选择的页面ID: {message.selected_page_ids}")

                # 1. 优先查询用户选择的页面
                if message.selected_page_ids:
                    await self.send_response(f"🎯 查询用户选择的 {len(message.selected_page_ids)} 个页面...")
                    logger.info(f"🎯 查询用户选择的 {len(message.selected_page_ids)} 个页面: {message.selected_page_ids}")

                    for page_id in message.selected_page_ids:
                        try:
                            logger.info(f"🔍 正在查询页面ID: {page_id}")
                            page = await self.page_analysis_repo.get_by_id(session, page_id)
                            if page:
                                page_dict = page.to_dict()
                                # 获取页面元素
                                elements = await self.page_element_repo.get_by_analysis_id(
                                    session, page.id
                                )
                                page_dict["elements"] = [elem.to_dict() for elem in elements]
                                database_results["pages"].append(page_dict)

                                logger.info(f"✅ 成功加载页面: {page.page_name} ({len(elements)} 个元素)")
                                await self.send_response(f"✅ 已加载页面: {page.page_name} ({len(elements)} 个元素)")
                            else:
                                logger.warning(f"⚠️ 页面ID {page_id} 不存在")
                                await self.send_response(f"⚠️ 页面ID {page_id} 不存在")
                        except Exception as e:
                            logger.error(f"查询页面 {page_id} 失败: {str(e)}")
                            await self.send_response(f"❌ 查询页面 {page_id} 失败: {str(e)}")

                # 2. 如果用户没有选择页面，或者选择的页面都查询失败，根据页面名称查询页面
                if not message.selected_page_ids and not database_results["pages"]:
                    logger.info("🔍 用户未选择页面，开始根据页面名称查询")
                    await self.send_response("🔍 用户未选择页面，开始根据页面名称查询...")

                    # 查询页面信息
                    for page_info in analysis_result.get("identified_pages", []):
                        page_name = page_info.get("page_name", "")
                        if page_name:
                            logger.info(f"🔍 根据页面名称查询: {page_name}")
                            pages = await self.page_analysis_repo.search_by_page_name(
                                session, page_name, limit=10
                            )
                            for page in pages:
                                page_dict = page.to_dict()
                                # 获取页面元素
                                elements = await self.page_element_repo.get_by_analysis_id(
                                    session, page.id
                                )
                                page_dict["elements"] = [elem.to_dict() for elem in elements]
                                database_results["pages"].append(page_dict)
                                logger.info(f"✅ 根据名称找到页面: {page.page_name} ({len(elements)} 个元素)")

                database_results["total_pages"] = len(database_results["pages"])
                database_results["total_elements"] = sum(
                    len(page.get("elements", [])) for page in database_results["pages"]
                )

                logger.info(f"📊 数据库查询完成，总页面数: {database_results['total_pages']}, 总元素数: {database_results['total_elements']}")
                await self.send_response(f"📊 数据库查询完成，总页面数: {database_results['total_pages']}, 总元素数: {database_results['total_elements']}")

                return database_results

        except Exception as e:
            logger.error(f"查询数据库元素失败: {str(e)}")
            return {"pages": [], "elements": [], "total_pages": 0, "total_elements": 0}

    async def _organize_and_classify_data(self, analysis_result: Dict[str, Any],
                                        database_results: Dict[str, Any],
                                        message: TestCaseElementParseRequest) -> Dict[str, Any]:
        """整理和分类页面元素数据"""
        try:
            parsed_pages = []
            element_categories = {}
            total_confidence = 0.0
            element_count = 0

            for page_data in database_results.get("pages", []):
                # 构建页面信息
                parsed_page = ParsedPageInfo(
                    page_id=page_data.get("id", ""),
                    page_name=page_data.get("page_name", ""),
                    page_description=page_data.get("page_description", ""),
                    page_type=page_data.get("page_type", "unknown"),
                    page_url=page_data.get("page_url"),
                    confidence_score=float(page_data.get("confidence_score", 0.0)),
                    elements=[],
                    element_categories={}
                )

                # 处理页面元素
                page_elements = []
                page_categories = {}

                for element_data in page_data.get("elements", []):
                    element_type = element_data.get("element_type", "unknown")

                    # 构建元素信息
                    parsed_element = ParsedPageElement(
                        element_id=element_data.get("id", ""),
                        element_name=element_data.get("element_name", ""),
                        element_type=element_type,
                        element_description=element_data.get("element_description", ""),
                        selector=self._extract_selector_from_element_data(element_data),
                        position=self._extract_position_from_element_data(element_data),
                        visual_features=self._extract_visual_features_from_element_data(element_data),
                        functionality=self._extract_functionality_from_element_data(element_data),
                        interaction_state=self._extract_interaction_state_from_element_data(element_data),
                        confidence_score=float(element_data.get("confidence_score", 0.0)),
                        is_testable=element_data.get("is_testable", True),
                        test_priority=self._determine_test_priority(element_data, analysis_result)
                    )

                    page_elements.append(parsed_element)

                    # 分类统计
                    if element_type not in page_categories:
                        page_categories[element_type] = []
                    page_categories[element_type].append(parsed_element.element_id)

                    if element_type not in element_categories:
                        element_categories[element_type] = 0
                    element_categories[element_type] += 1

                    total_confidence += parsed_element.confidence_score
                    element_count += 1

                parsed_page.elements = page_elements
                parsed_page.element_categories = page_categories
                parsed_pages.append(parsed_page)

            # 计算平均置信度
            avg_confidence = total_confidence / element_count if element_count > 0 else 0.0

            # 生成分析洞察
            insights = self._generate_analysis_insights(parsed_pages, analysis_result)

            # 生成建议
            recommendations = self._generate_recommendations(parsed_pages, analysis_result, message)

            return {
                "pages": parsed_pages,
                "summary": {
                    "total_pages": len(parsed_pages),
                    "total_elements": element_count,
                    "element_categories": element_categories,
                    "average_confidence": avg_confidence
                },
                "insights": insights,
                "recommendations": recommendations,
                "confidence_score": avg_confidence
            }

        except Exception as e:
            logger.error(f"整理和分类数据失败: {str(e)}")
            return {
                "pages": [],
                "summary": {"total_pages": 0, "total_elements": 0, "element_categories": {}, "average_confidence": 0.0},
                "insights": ["数据整理失败"],
                "recommendations": ["请检查数据库连接和数据完整性"],
                "confidence_score": 0.0
            }

    def _extract_selector_from_element_data(self, element_data: Dict[str, Any]) -> Optional[str]:
        """从元素数据中提取选择器"""
        element_full_data = element_data.get("element_data", {})
        return element_full_data.get("selector") or element_full_data.get("css_selector")

    def _extract_position_from_element_data(self, element_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从元素数据中提取位置信息"""
        element_full_data = element_data.get("element_data", {})
        return element_full_data.get("position") or element_full_data.get("location")

    def _extract_visual_features_from_element_data(self, element_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从元素数据中提取视觉特征"""
        element_full_data = element_data.get("element_data", {})
        return element_full_data.get("visual_features")

    def _extract_functionality_from_element_data(self, element_data: Dict[str, Any]) -> Optional[str]:
        """从元素数据中提取功能描述"""
        element_full_data = element_data.get("element_data", {})
        return element_full_data.get("functionality")

    def _extract_interaction_state_from_element_data(self, element_data: Dict[str, Any]) -> Optional[str]:
        """从元素数据中提取交互状态"""
        element_full_data = element_data.get("element_data", {})
        return element_full_data.get("interaction_state")

    def _determine_test_priority(self, element_data: Dict[str, Any],
                               analysis_result: Dict[str, Any]) -> str:
        """确定测试优先级"""
        element_type = element_data.get("element_type", "").lower()
        confidence = float(element_data.get("confidence_score", 0.0))

        # 根据元素类型和置信度确定优先级
        if element_type in ["button", "submit", "link"] and confidence > 0.8:
            return "high"
        elif element_type in ["input", "textarea", "select"] and confidence > 0.7:
            return "high"
        elif confidence > 0.6:
            return "medium"
        else:
            return "low"

    def _generate_analysis_insights(self, parsed_pages: List[ParsedPageInfo],
                                  analysis_result: Dict[str, Any]) -> List[str]:
        """生成分析洞察"""
        insights = []

        if not parsed_pages:
            insights.append("未找到匹配的页面元素，可能需要先进行页面分析")
            return insights

        total_elements = sum(len(page.elements) for page in parsed_pages)
        high_priority_elements = sum(
            len([e for e in page.elements if e.test_priority == "high"])
            for page in parsed_pages
        )

        insights.append(f"共找到 {len(parsed_pages)} 个相关页面，包含 {total_elements} 个UI元素")
        insights.append(f"其中 {high_priority_elements} 个元素被标记为高优先级测试对象")

        # 分析元素类型分布
        element_types = {}
        for page in parsed_pages:
            for element in page.elements:
                element_types[element.element_type] = element_types.get(element.element_type, 0) + 1

        if element_types:
            most_common_type = max(element_types, key=element_types.get)
            insights.append(f"最常见的元素类型是 {most_common_type}，共 {element_types[most_common_type]} 个")

        return insights

    def _generate_recommendations(self, parsed_pages: List[ParsedPageInfo],
                                analysis_result: Dict[str, Any],
                                message: TestCaseElementParseRequest) -> List[str]:
        """生成建议"""
        recommendations = []

        if not parsed_pages:
            recommendations.append("建议先上传相关页面进行AI分析，以获得更准确的元素信息")
            return recommendations

        total_elements = sum(len(page.elements) for page in parsed_pages)
        testable_elements = sum(
            len([e for e in page.elements if e.is_testable])
            for page in parsed_pages
        )

        if testable_elements < total_elements * 0.5:
            recommendations.append("部分元素可测试性较低，建议优化页面分析或手动调整元素信息")

        if message.target_format == "yaml":
            recommendations.append("建议使用YAML格式生成MidScene.js测试脚本，适合快速原型开发")
        elif message.target_format == "playwright":
            recommendations.append("建议使用Playwright格式生成完整的TypeScript测试代码")

        avg_confidence = sum(
            sum(e.confidence_score for e in page.elements)
            for page in parsed_pages
        ) / total_elements if total_elements > 0 else 0

        if avg_confidence < 0.7:
            recommendations.append("元素识别置信度较低，建议重新分析页面或手动验证元素信息")

        return recommendations



    async def _send_to_script_generators(self, response: TestCaseElementParseResponse,
                                       message: TestCaseElementParseRequest) -> None:
        """将解析结果发送给脚本生成智能体"""
        try:
            # 构建多模态分析响应格式，以便与现有的脚本生成智能体兼容
            from app.core.messages.web import PageAnalysis, UIElement, TestAction

            # 转换为兼容格式
            ui_elements_list = []
            test_steps = []

            for page in response.parsed_pages:
                for element in page.elements:
                    # 转换为UIElement格式
                    ui_element = UIElement(
                        element_type=element.element_type,
                        description=element.element_description,
                        location=str(element.position) if element.position else None,
                        attributes=element.visual_features or {},
                        selector=element.selector,
                        confidence_score=element.confidence_score
                    )
                    ui_elements_list.append(ui_element)

                    # 根据元素类型生成测试步骤
                    if element.is_testable and element.test_priority in ["high", "medium"]:
                        action_type = self._determine_action_type(element.element_type)
                        if action_type:
                            test_action = TestAction(
                                step_number=len(test_steps) + 1,
                                action=action_type,
                                target=element.element_name or element.element_description,
                                description=f"{action_type} {element.element_description}",
                                selector=element.selector,
                                expected_result=f"成功{action_type}{element.element_description}"
                            )
                            test_steps.append(test_action)

            # 直接使用用户输入的测试用例内容

            # 准备数据库元素信息
            database_elements = None
            if hasattr(response, 'database_results') and response.database_results:
                database_elements = response.database_results

            page_analysis = PageAnalysis(
                page_title=response.parsed_pages[0].page_name if response.parsed_pages else "测试页面",
                page_type=response.parsed_pages[0].page_type if response.parsed_pages else "unknown",
                main_content=message.test_case_content,
                ui_elements=[elem.description for elem in ui_elements_list],
                test_steps=test_steps,
                analysis_summary=f"测试用例解析完成，识别到{len(response.parsed_pages)}个页面，{len(ui_elements_list)}个元素",
                confidence_score=response.confidence_score,
                database_elements=database_elements
            )

            # 构建兼容的响应消息
            from app.core.messages.web import AnalysisType
            analysis_response = WebMultimodalAnalysisResponse(
                session_id=response.session_id,
                analysis_id=response.parse_id,
                analysis_type=AnalysisType.TEXT,  # 基于文本的分析
                page_analysis=page_analysis,
                confidence_score=response.confidence_score,
                status="success",
                message="测试用例元素解析完成",
                processing_time=response.processing_time
            )

            # 根据目标格式发送给相应的生成智能体
            if message.target_format.lower() == "yaml":
                await self.publish_message(
                    analysis_response,
                    topic_id=TopicId(type=TopicTypes.YAML_GENERATOR.value, source=self.id.key)
                )
                await self.send_response("📤 已发送数据给YAML生成智能体")

            elif message.target_format.lower() == "playwright":
                await self.publish_message(
                    analysis_response,
                    topic_id=TopicId(type=TopicTypes.PLAYWRIGHT_GENERATOR.value, source=self.id.key)
                )
                await self.send_response("📤 已发送数据给Playwright生成智能体")

            else:
                # 默认发送给两个生成智能体
                await self.publish_message(
                    analysis_response,
                    topic_id=TopicId(type=TopicTypes.YAML_GENERATOR.value, source=self.id.key)
                )
                await self.publish_message(
                    analysis_response,
                    topic_id=TopicId(type=TopicTypes.PLAYWRIGHT_GENERATOR.value, source=self.id.key)
                )
                await self.send_response("📤 已发送数据给YAML和Playwright生成智能体")

        except Exception as e:
            logger.error(f"发送数据给脚本生成智能体失败: {str(e)}")
            await self.send_warning(f"发送数据给脚本生成智能体失败: {str(e)}")

    def _determine_action_type(self, element_type: str) -> Optional[str]:
        """根据元素类型确定操作类型"""
        element_type = element_type.lower()

        action_mapping = {
            "button": "click",
            "submit": "click",
            "link": "click",
            "input": "input",
            "textarea": "input",
            "select": "select",
            "dropdown": "select",
            "checkbox": "click",
            "radio": "click",
            "image": "click",
            "tab": "click"
        }

        return action_mapping.get(element_type)

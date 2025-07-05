"""
图片专门分析智能体
基于AutoGen团队协作机制，专门用于深度分析UI界面图片
支持MultiModalMessage和团队协作分析
"""
import json
import uuid
import base64
import requests
from io import BytesIO
from typing import Dict, List, Any, Optional
from datetime import datetime

from autogen_agentchat.base import TaskResult
from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from autogen_core import Image as AGImage
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent, MessageFilterAgent, MessageFilterConfig, PerSourceFilter
from autogen_agentchat.messages import MultiModalMessage, TextMessage, ModelClientStreamingChunkEvent
from autogen_agentchat.teams import RoundRobinGroupChat, GraphFlow, DiGraphBuilder
from PIL import Image
from loguru import logger

from app.core.messages.web import (
    WebMultimodalAnalysisRequest, WebMultimodalAnalysisResponse,
    PageAnalysis, UIElement, AnalysisType, PageAnalysisStorageRequest
)
from app.core.agents.base import BaseAgent
from app.core.types import TopicTypes, AgentTypes, AGENT_NAMES, MessageRegion


@type_subscription(topic_type=TopicTypes.PAGE_ANALYZER.value)
class PageAnalyzerAgent(BaseAgent):
    """图片专门分析智能体，基于AutoGen团队协作"""

    def __init__(self, model_client_instance=None, enable_user_feedback: bool = False, collector=None, **kwargs):
        """初始化图片分析智能体"""
        super().__init__(
            agent_id=AgentTypes.PAGE_ANALYZER.value,
            agent_name=AGENT_NAMES[AgentTypes.PAGE_ANALYZER.value],
            model_client_instance=model_client_instance,
            **kwargs
        )

        self.metrics = None
        self.enable_user_feedback = enable_user_feedback
        self._analysis_team = None
        self.collector = collector

        logger.info(f"图片专门分析智能体初始化完成，用户反馈: {enable_user_feedback}")

    @classmethod
    def create_ui_expert_agent(cls, **kwargs) -> AssistantAgent:
        """创建UI专家智能体"""
        from app.agents.factory import agent_factory

        return agent_factory.create_assistant_agent(
            name=AgentTypes.UI_EXPERT.value,
            system_message=cls._build_ui_expert_prompt(),
            model_client_type="uitars",
            **kwargs
        )

    @staticmethod
    def _build_ui_expert_prompt() -> str:
        """职责 (Responsibilities):
        接收用户提供的界面截图或实时界面信息。
        利用多模态大模型的能力，识别界面中的关键元素，例如按钮、输入框、文本标签、图片、列表项等。
        输出结构化的界面元素信息，包括元素类型、位置、文本内容、可能的交互方式以及推荐的定位符（如ID、类名、文本内容等，MidScene.js可能用到的）。"""
        return """你是UI元素识别专家，专门分析Web界面中的可测试交互元素，为UI自动化测试提供精确的元素信息。你的分析将用于MidScene.js自动化测试框架。

## 核心职责

### 1. 仅识别可测试的交互元素
**重点识别以下元素类型（按优先级排序）**:

**1. 按钮类元素**:
- 提交按钮、确认按钮、取消按钮
- 登录按钮、注册按钮、保存按钮
- 编辑按钮、删除按钮、添加按钮
- 搜索按钮、重置按钮、刷新按钮

**2. 输入类元素**:
- 文本输入框、密码输入框、搜索框
- 文本域（textarea）
- 数字输入框、邮箱输入框、电话输入框

**3. 选择类元素**:
- 下拉菜单（select）、多选下拉框
- 复选框（checkbox）、单选按钮（radio）
- 开关切换按钮（toggle/switch）

**4. 链接类元素**:
- 导航链接、菜单链接
- 操作链接（编辑、删除、查看详情等）
- 外部链接、下载链接

**5. 特殊交互元素**:
- 文件上传按钮
- 日期选择器、时间选择器
- 滑块、评分组件

### 忽略的元素类型：
- 纯装饰性图片、图标
- 静态文本、标题、段落
- 布局容器（div、section等）
- 纯展示性的表格、列表
- 面包屑导航、页面标题
- 版权信息、页脚内容

### 2. 元素识别标准
**必须满足以下条件之一才识别**:
- 可以点击执行操作（按钮、链接）
- 可以输入内容（输入框、文本域）
- 可以选择或切换状态（下拉菜单、复选框、单选按钮、开关）
- 可以上传文件或选择日期时间

**元素描述要求**:
- 使用MidScene.js友好的自然语言描述
- 包含位置、颜色、文字内容等关键特征
- 确保描述足够具体，能够唯一定位元素

**位置描述标准**:
- **绝对位置**: "页面左上角"、"右上角"、"中央区域"
- **相对位置**: "搜索框右侧"、"表单底部"、"导航栏中"
- **文字定位**: 优先使用按钮文字、链接文字、标签文字进行定位

### 3. 测试操作适配
**MidScene.js操作映射**:
- **aiTap**: 按钮、链接、复选框、单选按钮、开关
- **aiInput**: 文本输入框、密码框、搜索框、文本域
- **aiQuery**: 获取输入框内容、按钮状态、选择框选项
- **aiAssert**: 验证元素存在、文字内容、状态正确性

## 质量标准与要求

### 精准识别原则
- **只识别可测试元素**: 严格按照上述5类交互元素进行识别
- **避免过度识别**: 不识别纯展示性、装饰性元素
- **优先核心功能**: 登录、提交、搜索等核心业务操作优先

### 描述准确性
- **元素类型准确**: 正确区分button、input、select、link等
- **状态识别准确**: 准确识别启用/禁用、必填/可选状态
- **文本内容完整**: 提取完整的按钮文字、链接文字、标签文字

## 输出格式要求

请严格按照以下JSON格式输出，只包含可测试的交互元素：

{
  "title": "根据页面内容自动生成的页面标题",
  "description": "页面主要功能的简要描述",
  "elements": [
    {
      "id": "element_001",
      "name": "登录按钮",
      "element_type": "button",
      "description": "页面右上角的蓝色登录按钮，白色文字'登录'",
      "text_content": "登录",
      "position": {
        "area": "页面右上角",
        "relative_to": "导航栏右侧"
      },
      "visual_features": {
        "color": "蓝色背景，白色文字",
        "size": "中等尺寸",
        "shape": "圆角矩形"
      },
      "functionality": "用户登录入口",
      "interaction_state": "可点击",
      "testability": {
        "is_testable": true,
        "test_priority": "high",
        "midscene_operations": ["aiTap", "aiAssert"],
        "test_scenarios": ["点击登录", "验证按钮存在"]
      },
      "locator_suggestions": {
        "natural_language": "页面右上角的蓝色登录按钮",
        "alternative_descriptions": [
          "登录按钮",
          "蓝色的登录按钮"
        ]
      },
      "confidence_score": 0.95
    }
  ]
}

## 特别注意事项

1. **严格筛选**: 只识别可点击、可输入、可选择的交互元素
2. **避免冗余**: 不要识别装饰性图片、静态文本、布局容器
3. **优先核心功能**: 登录、提交、搜索等核心操作元素优先
4. **简化描述**: 提供足够定位信息即可，避免过度详细
5. **确保可操作**: 每个识别的元素都必须支持MidScene.js操作

请开始分析工作，只输出可测试的交互元素。

    """

    @message_handler
    async def handle_message(self, message: WebMultimodalAnalysisRequest, ctx: MessageContext) -> None:
        """处理图片分析请求"""
        try:
            monitor_id = self.start_performance_monitoring()

            # 创建分析智能体
            agent = self.create_ui_expert_agent()

            # 准备多模态消息
            multimodal_message = await self._prepare_multimodal_message(message)

            # 运行智能体分析
            analysis_results = await self._run_agent_analysis(agent, multimodal_message)

            # 构建页面分析结果
            analysis_result = await self._build_page_analysis_result(analysis_results, message)

            self.metrics = self.end_performance_monitoring(monitor_id)

            await self.send_response(
                "✅ 页面分析完成",
                is_final=True,
                result={
                    "analysis_result": analysis_result,
                    "team_collaboration": True,
                    "user_feedback_enabled": self.enable_user_feedback,
                    "metrics": self.metrics
                }
            )

            # 发送分析结果到存储智能体
            await self._send_to_storage_agent(analysis_result, message)


        except Exception as e:
            await self.handle_exception("handle_message", e)
    async def _run_agent_analysis(self, agent: AssistantAgent, multimodal_message: MultiModalMessage) -> Dict[str, Any]:
        """运行团队协作分析"""
        try:
            # 运行团队分析
            stream = agent.run_stream(task=multimodal_message)
            full_content = ""

            async for event in stream:  # type: ignore
                # 流式消息
                if isinstance(event, ModelClientStreamingChunkEvent):
                    await self.send_response(content=event.content, region=MessageRegion.ANALYSIS, source=AGENT_NAMES[event.source])
                    # full_content += event.content
                    continue

                # 最终的完整结果
                if isinstance(event, TaskResult):
                    messages = event.messages
                    # 从最后一条消息中获取完整内容
                    if messages and hasattr(messages[-1], 'content'):
                        full_content = messages[-1].content
                    continue

            # 解析智能体输出的JSON结果
            analysis_result = await self._parse_agent_output(full_content)
            return analysis_result

        except Exception as e:
            logger.error(f"团队分析执行失败: {str(e)}")
            # 返回默认结果
            return {
                "page_name": "未知页面",
                "page_description": "分析失败",
                "raw_json": {},
                "ui_elements": [],
                "parsed_elements": [],
                "confidence_score": 0.0
            }

    async def _prepare_multimodal_message(self, request: WebMultimodalAnalysisRequest) -> MultiModalMessage:
        """准备多模态消息，基于AutoGen的MultiModalMessage格式"""
        try:
            # 构建聚焦测试元素的分析指导文本内容
            text_content = f"""
请对提供的Web页面截图进行UI元素分析，只识别可测试的交互元素。

## 分析上下文信息
**用户测试需求**: {request.test_description or '通用UI自动化测试'}
**页面URL**: {request.web_url or request.target_url or '未提供'}
**附加说明**: {request.additional_context or '无特殊要求'}

## 只识别以下5类可测试元素：

### 1. 按钮类元素
- 提交、确认、取消、保存、删除、编辑按钮
- 登录、注册、搜索、重置、刷新按钮
- 添加、导出、导入、下载按钮

### 2. 输入类元素
- 文本输入框、密码框、搜索框
- 文本域（多行文本输入）
- 数字、邮箱、电话等特殊输入框

### 3. 选择类元素
- 下拉菜单、多选下拉框
- 复选框、单选按钮
- 开关切换按钮

### 4. 链接类元素
- 导航链接、菜单链接
- 操作链接（编辑、删除、查看详情）
- 外部链接、下载链接

### 5. 特殊交互元素
- 文件上传按钮
- 日期时间选择器
- 滑块、评分组件

## 严格忽略以下元素：
- 静态文本、标题、段落
- 装饰性图片、图标
- 布局容器、分割线
- 纯展示的表格、列表
- 面包屑导航、页面标题
- 版权信息、页脚内容

## 分析要求：
- 每个元素必须可以进行点击、输入或选择操作
- 提供清晰的自然语言定位描述
- 标注支持的MidScene.js操作类型
- 按重要性排序（核心业务功能优先）

请严格按照系统提示的JSON格式输出，只包含可测试的交互元素。

开始分析工作：
"""

            # 转换图片为AGImage对象
            ag_image = await self._convert_image_to_agimage(request)

            # 创建MultiModalMessage，参考官方示例格式
            multimodal_message = MultiModalMessage(
                content=[text_content, ag_image],
                source="user"
            )

            return multimodal_message

        except Exception as e:
            logger.error(f"准备多模态消息失败: {str(e)}")
            raise

    async def _convert_image_to_agimage(self, request: WebMultimodalAnalysisRequest) -> AGImage:
        """将图片内容转换为AGImage对象，参考官方示例代码"""
        try:
            pil_image = None

            if request.image_url:
                # 从URL获取图片，参考官方示例：requests.get(url).content
                response = requests.get(request.image_url)
                response.raise_for_status()
                pil_image = Image.open(BytesIO(response.content))
            elif request.image_data:
                # 处理base64数据
                if request.image_data.startswith('data:image'):
                    # 移除data URI前缀
                    base64_data = request.image_data.split(',')[1]
                else:
                    base64_data = request.image_data

                # 解码base64数据并创建PIL图片
                image_bytes = base64.b64decode(base64_data)
                pil_image = Image.open(BytesIO(image_bytes))
            else:
                raise ValueError("缺少图片数据或URL")

            # 转换为AGImage，完全按照官方示例：AGImage(pil_image)
            ag_image = AGImage(pil_image)
            logger.info(f"成功转换图片为AGImage，尺寸: {pil_image.size}")

            return ag_image

        except Exception as e:
            logger.error(f"转换图片为AGImage失败: {str(e)}")
            raise

    async def _parse_agent_output(self, content: str) -> Dict[str, Any]:
        """解析智能体输出的JSON内容"""
        try:
            # 尝试从内容中提取JSON
            json_start = content.find('{')
            json_end = content.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                logger.warning("未找到JSON格式的输出，使用文本解析")
                return await self._parse_text_output(content)

            json_str = content[json_start:json_end]
            parsed_json = json.loads(json_str)

            # 解析新的JSON格式
            page_name = "未知页面"
            page_description = ""
            ui_elements = []

            if isinstance(parsed_json, dict):
                # 新格式：{"title": "页面名称", "description": "描述", "elements": [...]}
                if "title" in parsed_json and "description" in parsed_json and "elements" in parsed_json:
                    page_name = parsed_json.get("title", "未知页面")
                    page_description = parsed_json.get("description", "")
                    ui_elements = parsed_json.get("elements", [])

                    logger.info(f"成功解析新格式JSON - 页面: {page_name}, 元素数量: {len(ui_elements)}")

                # 兼容旧格式：{"页面名称": [{"description": "..."}, {...}]}
                elif len(parsed_json) == 1:
                    first_key = list(parsed_json.keys())[0]
                    page_name = first_key
                    page_data = parsed_json[first_key]

                    if isinstance(page_data, list) and page_data:
                        # 第一个元素可能是页面描述
                        if isinstance(page_data[0], dict) and "description" in page_data[0] and len(page_data[0]) == 1:
                            page_description = page_data[0]["description"]
                            ui_elements = page_data[1:]
                        else:
                            ui_elements = page_data

                    logger.info(f"解析兼容格式JSON - 页面: {page_name}, 元素数量: {len(ui_elements)}")

                else:
                    logger.warning("未识别的JSON格式，尝试提取元素")
                    # 尝试从任何数组字段中提取元素
                    for key, value in parsed_json.items():
                        if isinstance(value, list) and value:
                            ui_elements = value
                            break

            # 计算平均置信度
            confidence_scores = []
            for element in ui_elements:
                if isinstance(element, dict) and "confidence_score" in element:
                    confidence_scores.append(element["confidence_score"])

            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.8

            return {
                "page_name": page_name,
                "page_description": page_description,
                "raw_json": parsed_json,
                "ui_elements": ui_elements,
                "parsed_elements": ui_elements,
                "confidence_score": avg_confidence
            }

        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {str(e)}，使用文本解析")
            return await self._parse_text_output(content)
        except Exception as e:
            logger.error(f"解析智能体输出失败: {str(e)}")
            return {
                "page_name": "解析失败",
                "page_description": "智能体输出解析失败",
                "raw_json": {},
                "ui_elements": [],
                "parsed_elements": [],
                "confidence_score": 0.0
            }

    async def _parse_text_output(self, content: str) -> Dict[str, Any]:
        """解析文本格式的输出"""
        try:
            lines = content.strip().split('\n')
            page_name = "文本分析页面"
            page_description = "基于文本内容的页面分析"
            ui_elements = []

            # 简单的文本解析逻辑
            for i, line in enumerate(lines):
                if line.strip():
                    ui_elements.append({
                        "id": f"element_{i+1}",
                        "name": f"元素_{i+1}",
                        "description": line.strip()[:200],
                        "element_type": "text",
                        "confidence_score": 0.7
                    })

            return {
                "page_name": page_name,
                "page_description": page_description,
                "raw_json": {"text_content": content},
                "ui_elements": ui_elements,
                "parsed_elements": ui_elements,
                "confidence_score": 0.7
            }

        except Exception as e:
            logger.error(f"文本解析失败: {str(e)}")
            return {
                "page_name": "解析失败",
                "page_description": "文本解析失败",
                "raw_json": {},
                "ui_elements": [],
                "parsed_elements": [],
                "confidence_score": 0.0
            }

    async def _build_page_analysis_result(self, analysis_results: Dict[str, Any], request: WebMultimodalAnalysisRequest) -> Dict[str, Any]:
        """构建页面分析结果"""
        try:
            from app.core.messages.web import PageAnalysis

            # 构建PageAnalysis对象
            page_analysis = PageAnalysis(
                page_title=analysis_results.get("page_name", "未知页面"),
                page_type="web_page",
                main_content=analysis_results.get("page_description", ""),
                ui_elements=[str(element) for element in analysis_results.get("ui_elements", [])],
                user_flows=["基于UI元素分析的用户流程"],
                test_scenarios=["基于页面分析的测试场景"],
                analysis_summary=f"页面'{analysis_results.get('page_name', '未知页面')}'的分析结果",
                confidence_score=analysis_results.get("confidence_score", 0.0)
            )

            return {
                "page_name": analysis_results.get("page_name", "未知页面"),
                "page_description": analysis_results.get("page_description", ""),
                "page_analysis": page_analysis,
                "raw_json": analysis_results.get("raw_json", {}),
                "parsed_elements": analysis_results.get("parsed_elements", []),
                "confidence_score": analysis_results.get("confidence_score", 0.0)
            }

        except Exception as e:
            logger.error(f"构建页面分析结果失败: {str(e)}")
            # 返回默认结果
            from app.core.messages.web import PageAnalysis
            default_analysis = PageAnalysis(
                page_title="分析失败",
                page_type="unknown",
                main_content="页面分析失败",
                analysis_summary="页面分析过程中发生错误"
            )
            return {
                "page_name": "分析失败",
                "page_description": "页面分析失败",
                "page_analysis": default_analysis,
                "raw_json": {},
                "parsed_elements": [],
                "confidence_score": 0.0
            }

    async def _send_to_storage_agent(self, analysis_result: Dict[str, Any], request: WebMultimodalAnalysisRequest) -> None:
        """发送分析结果到存储智能体"""
        try:
            from app.core.messages.web import PageAnalysisStorageRequest

            # 提取原始session_id（去除可能的后缀）
            original_session_id = request.session_id
            if "_file_" in original_session_id:
                original_session_id = original_session_id.split("_file_")[0]
            elif original_session_id.count("_") > 4:  # UUID通常有4个下划线
                # 如果有额外的下划线，可能是添加了后缀，尝试提取原始UUID
                parts = original_session_id.split("_")
                if len(parts) > 5:  # UUID有5个部分，如果超过说明有后缀
                    original_session_id = "_".join(parts[:5])

            # 构建存储请求
            storage_request = PageAnalysisStorageRequest(
                session_id=original_session_id,  # 使用原始session_id
                analysis_id=str(uuid.uuid4()),
                page_name=analysis_result.get("page_name", "未知页面"),
                page_url=request.web_url or request.target_url,
                page_type="web_page",
                page_description=analysis_result.get("page_description", ""),
                analysis_result=analysis_result["page_analysis"],
                confidence_score=analysis_result.get("confidence_score", 0.0),
                analysis_metadata={
                    "raw_json": analysis_result.get("raw_json", {}),
                    "parsed_elements": analysis_result.get("parsed_elements", []),
                    "processing_time": self.metrics.get("duration_seconds", 0.0) if self.metrics else 0.0,
                    "agent_type": "page_analyzer",
                    "analysis_timestamp": datetime.now().isoformat()
                }
            )

            # 使用消息机制发送到存储智能体
            await self.publish_message(
                storage_request,
                topic_id=TopicId(type=TopicTypes.PAGE_ANALYSIS_STORAGE.value, source=self.id.key)
            )

            logger.info(f"已发送分析结果到存储智能体，页面: {analysis_result.get('page_name', '未知页面')}")

        except Exception as e:
            logger.error(f"发送分析结果到存储智能体失败: {str(e)}")
            # 不抛出异常，避免影响主流程


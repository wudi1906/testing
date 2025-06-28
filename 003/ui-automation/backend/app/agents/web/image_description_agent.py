"""
图片描述生成智能体
专门用于分析UI界面截图并生成详细的自然语言测试用例描述
基于AutoGen框架和BaseAgent实现
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
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import MultiModalMessage, TextMessage, ModelClientStreamingChunkEvent
from PIL import Image
from loguru import logger

from app.core.messages.web import WebMultimodalAnalysisRequest
from app.core.agents.base import BaseAgent
from app.core.types import TopicTypes, AgentTypes, AGENT_NAMES, MessageRegion


@type_subscription(topic_type=TopicTypes.IMAGE_DESCRIPTION_GENERATOR.value)
class ImageDescriptionGeneratorAgent(BaseAgent):
    """图片描述生成智能体，基于AutoGen框架"""

    def __init__(self, model_client_instance=None, enable_user_feedback: bool = False, collector=None, **kwargs):
        """初始化图片描述生成智能体"""
        super().__init__(
            agent_id="image_description_generator",
            agent_name="图片描述生成智能体",
            model_client_instance=model_client_instance,
            **kwargs
        )

        self.metrics = None
        self.enable_user_feedback = enable_user_feedback
        self.collector = collector

        logger.info(f"图片描述生成智能体初始化完成，用户反馈: {enable_user_feedback}")

    @classmethod
    def create_description_agent(cls, **kwargs) -> AssistantAgent:
        """创建描述生成智能体"""
        from app.agents.factory import agent_factory

        return agent_factory.create_assistant_agent(
            name="description_generator",
            system_message=cls._build_description_prompt(),
            model_client_type="uitars",
            **kwargs
        )
    @staticmethod
    def _build_description_prompt() -> str:
        """构建描述生成提示词"""
        return """你是UI界面测试用例描述生成专家，专门分析UI界面截图并生成详细的自然语言测试用例描述。

## 核心职责

### 1. 界面概述分析
- 识别界面类型（登录页、表单页、列表页、详情页等）
- 分析主要功能和业务场景
- 描述整体布局和设计风格

### 2. 主要元素识别
- **交互元素**: 按钮、链接、输入框、下拉菜单、复选框等
- **显示元素**: 文本、图片、图标、标签、提示信息等
- **容器元素**: 表单、卡片、模态框、导航栏等
- **列表元素**: 表格、列表项、菜单项等

### 3. 测试场景生成
- 基于界面元素推测用户操作流程
- 生成正常流程测试用例
- 考虑边界情况和异常场景
- 包含数据验证和错误处理

### 4. 输出格式要求

请使用Markdown格式输出，包含以下结构：

```markdown
# 界面测试用例描述

## 界面概述
[描述界面类型和主要功能]

## 主要元素分析
- **元素1**: [位置和功能描述]
- **元素2**: [位置和功能描述]
- ...

## 测试场景
### 场景1: [场景名称]
1. [操作步骤1]
2. [操作步骤2]
3. [验证点]

### 场景2: [场景名称]
1. [操作步骤1]
2. [操作步骤2]
3. [验证点]

## 预期结果
- [预期结果1]
- [预期结果2]
```

## 质量标准
- 描述要具体详细，包含元素的位置、文本内容、颜色等特征
- 测试步骤要清晰可执行
- 考虑正常流程和异常情况
- 如果有表单，要考虑验证规则
"""

    @message_handler
    async def handle_message(self, message: WebMultimodalAnalysisRequest, ctx: MessageContext) -> None:
        """处理图片描述生成请求"""
        try:
            monitor_id = self.start_performance_monitoring()

            # 创建描述生成智能体
            agent = self.create_description_agent()

            # 准备多模态消息
            multimodal_message = await self._prepare_multimodal_message(message)

            # 运行智能体分析
            description_result = await self._run_agent_analysis(agent, multimodal_message)

            self.metrics = self.end_performance_monitoring(monitor_id)

            await self.send_response(
                "✅ 图片描述生成完成",
                is_final=True,
                result={
                    "description": description_result.get("description", ""),
                    "confidence_score": description_result.get("confidence_score", 0.8),
                    "analysis_result": description_result,
                    "metrics": self.metrics
                }
            )

        except Exception as e:
            await self.handle_exception("handle_message", e)

    async def generate_description(
        self,
        image_data: str,
        additional_context: str = "",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成图片的自然语言测试用例描述（兼容性方法）

        Args:
            image_data: Base64编码的图片数据
            additional_context: 额外上下文信息
            session_id: 会话ID

        Returns:
            包含描述和分析结果的字典
        """
        try:
            if not session_id:
                session_id = str(uuid.uuid4())

            logger.info(f"开始生成图片描述: {session_id}")

            # 创建请求消息
            from app.core.messages.web import AnalysisType
            request = WebMultimodalAnalysisRequest(
                session_id=session_id,
                analysis_type=AnalysisType.IMAGE,
                image_data=image_data,
                test_description="生成测试用例描述",
                additional_context=additional_context,
                generate_formats=[]
            )

            # 创建描述生成智能体
            agent = self.create_description_agent()

            # 准备多模态消息
            multimodal_message = await self._prepare_multimodal_message(request)

            # 运行智能体分析
            description_result = await self._run_agent_analysis(agent, multimodal_message)

            return description_result

        except Exception as e:
            logger.error(f"图片描述生成失败: {session_id}, 错误: {str(e)}")
            raise

    async def _prepare_multimodal_message(self, request: WebMultimodalAnalysisRequest) -> MultiModalMessage:
        """准备多模态消息，基于AutoGen的MultiModalMessage格式"""
        try:
            # 构建文本内容
            text_content = f"""
请分析这个UI界面，并生成详细的自然语言测试用例描述：

**分析需求**: {request.test_description or '生成测试用例描述'}
**附加说明**: {request.additional_context or '无'}

请开始分析工作。
"""

            # 转换图片为AGImage对象
            ag_image = await self._convert_image_to_agimage(request)

            # 创建MultiModalMessage
            multimodal_message = MultiModalMessage(
                content=[text_content, ag_image],
                source="user"
            )

            return multimodal_message

        except Exception as e:
            logger.error(f"准备多模态消息失败: {str(e)}")
            raise

    async def _convert_image_to_agimage(self, request: WebMultimodalAnalysisRequest) -> AGImage:
        """将图片内容转换为AGImage对象"""
        try:
            pil_image = None

            if request.image_url:
                # 从URL获取图片
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

            # 转换为AGImage
            ag_image = AGImage(pil_image)
            logger.info(f"成功转换图片为AGImage，尺寸: {pil_image.size}")

            return ag_image

        except Exception as e:
            logger.error(f"转换图片为AGImage失败: {str(e)}")
            raise
    async def _run_agent_analysis(self, agent: AssistantAgent, multimodal_message: MultiModalMessage) -> Dict[str, Any]:
        """运行智能体分析"""
        try:
            # 运行智能体分析
            stream = agent.run_stream(task=multimodal_message)
            full_content = ""

            async for event in stream:  # type: ignore
                # 流式消息
                if isinstance(event, ModelClientStreamingChunkEvent):
                    await self.send_response(content=event.content, region=MessageRegion.ANALYSIS, source="description_generator")
                    continue

                # 最终的完整结果
                if isinstance(event, TaskResult):
                    messages = event.messages
                    # 从最后一条消息中获取完整内容
                    if messages and hasattr(messages[-1], 'content'):
                        full_content = messages[-1].content

                        # 发送最终的测试用例到富文本区域
                        await self.send_response(
                            content=full_content,
                            region=MessageRegion.TESTCASE,  # 使用TESTCASE区域标识最终用例
                            is_final=True,
                            source="description_generator"
                        )
                    continue

            # 处理和优化描述
            processed_description = self._process_description(full_content)

            # 计算置信度分数
            confidence_score = self._calculate_confidence_score(processed_description)

            return {
                "description": processed_description,
                "raw_response": full_content,
                "confidence_score": confidence_score,
                "analysis_result": {
                    "timestamp": datetime.now().isoformat(),
                    "agent_type": "description_generator"
                }
            }

        except Exception as e:
            logger.error(f"智能体分析执行失败: {str(e)}")
            # 返回默认结果
            return {
                "description": "分析失败，请重试",
                "raw_response": "",
                "confidence_score": 0.0,
                "analysis_result": {
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
            }
    def _process_description(self, raw_description: str) -> str:
        """处理和优化描述内容"""
        try:
            # 基本清理
            processed = raw_description.strip()

            # 确保有标题
            if not processed.startswith('#'):
                processed = "# 界面测试用例描述\n\n" + processed

            # 添加时间戳
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            processed += f"\n\n---\n*生成时间: {timestamp}*"

            return processed

        except Exception as e:
            logger.warning(f"处理描述内容失败: {str(e)}")
            return raw_description
    def _calculate_confidence_score(self, description: str) -> float:
        """计算描述质量的置信度分数"""
        try:
            score = 0.5  # 基础分数

            # 检查内容长度
            if len(description) > 200:
                score += 0.1
            if len(description) > 500:
                score += 0.1

            # 检查结构化内容
            structure_keywords = ['##', '###', '1.', '2.', '-', '*']
            for keyword in structure_keywords:
                if keyword in description:
                    score += 0.05

            # 检查测试相关关键词
            test_keywords = [
                '测试', '验证', '点击', '输入', '选择', '提交',
                '登录', '表单', '按钮', '输入框', '链接',
                '步骤', '操作', '预期', '结果'
            ]

            for keyword in test_keywords:
                if keyword in description:
                    score += 0.02

            # 检查UI元素关键词
            ui_keywords = [
                'button', 'input', 'form', 'link', 'menu', 'nav',
                '按钮', '输入框', '表单', '链接', '菜单', '导航',
                '页面', '界面', '元素', '组件'
            ]

            for keyword in ui_keywords:
                if keyword.lower() in description.lower():
                    score += 0.03

            # 限制最大分数
            score = min(score, 0.95)

            return round(score, 2)

        except Exception as e:
            logger.warning(f"计算置信度分数失败: {str(e)}")
            return 0.8
    async def enhance_description(
        self,
        original_description: str,
        enhancement_type: str = "detail"
    ) -> str:
        """
        增强描述内容

        Args:
            original_description: 原始描述
            enhancement_type: 增强类型 (detail, structure, test_cases)

        Returns:
            增强后的描述
        """
        try:
            enhancement_prompts = {
                "detail": "请为以下测试用例描述添加更多细节，包括具体的元素位置、颜色、大小等视觉特征：",
                "structure": "请重新组织以下测试用例描述的结构，使其更加清晰和易读：",
                "test_cases": "请为以下界面描述生成更多具体的测试用例，包括边界情况和异常场景："
            }

            prompt = enhancement_prompts.get(enhancement_type, enhancement_prompts["detail"])
            full_prompt = f"{prompt}\n\n{original_description}"

            # 创建增强智能体
            agent = self.create_description_agent()

            # 创建文本消息
            text_message = TextMessage(content=full_prompt, source="user")

            # 运行智能体
            stream = agent.run_stream(task=text_message)
            enhanced_content = ""

            async for event in stream:
                if isinstance(event, TaskResult):
                    messages = event.messages
                    if messages and hasattr(messages[-1], 'content'):
                        enhanced_content = messages[-1].content
                    break

            return enhanced_content or original_description

        except Exception as e:
            logger.error(f"增强描述失败: {str(e)}")
            return original_description

"""
YAML生成智能体
负责根据多模态分析结果生成MidScene.js格式的YAML测试脚本
"""
import json
import uuid
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import ModelClientStreamingChunkEvent, TextMessage
from autogen_core import message_handler, type_subscription, MessageContext, TopicId
from autogen_agentchat.agents import AssistantAgent
from autogen_core.memory import ListMemory
from loguru import logger

from app.core.messages.web import WebMultimodalAnalysisResponse
from app.core.agents.base import BaseAgent
from app.core.types import TopicTypes, AgentTypes, AGENT_NAMES, MessageRegion


@type_subscription(topic_type=TopicTypes.YAML_GENERATOR.value)
class YAMLGeneratorAgent(BaseAgent):
    """YAML生成智能体，负责生成MidScene.js格式的测试脚本"""

    def __init__(self, model_client_instance=None, **kwargs):
        """初始化YAML生成智能体"""
        super().__init__(
            agent_id=AgentTypes.YAML_GENERATOR.value,
            agent_name=AGENT_NAMES[AgentTypes.YAML_GENERATOR.value],
            model_client_instance=model_client_instance,
            **kwargs
        )
        self._prompt_template = self._build_prompt_template()
        self.metrics = None

        logger.info(f"YAML生成智能体初始化完成: {self.agent_name}")

    @classmethod
    def create_assistant_agent(cls, model_client_instance=None, **kwargs) -> AssistantAgent:
        """创建用于YAML生成的AssistantAgent实例

        Args:
            model_client_instance: 模型客户端实例
            **kwargs: 其他参数

        Returns:
            AssistantAgent: 配置好的智能体实例
        """
        from app.agents.factory import agent_factory

        return agent_factory.create_assistant_agent(
            name="yaml_generator",
            system_message=cls._build_prompt_template(),
            model_client_type="auto",
            task_type="yaml_generation",  # 指定任务类型为YAML代码生成，自动选择DeepSeek
            model_client_stream=True,
            **kwargs
        )

    @staticmethod
    def _build_prompt_template() -> str:
        """构建YAML生成提示模板"""
        return """
你是MidScene.js YAML测试脚本生成专家，专门根据UI分析结果生成高质量的自动化测试脚本。

## MidScene.js核心概念

MidScene.js是基于AI的UI自动化测试框架，通过自然语言描述进行元素定位和操作。
- 官方文档: https://midscenejs.com/zh/api.html
- 核心优势: 无需传统选择器，使用AI理解页面内容
- 适用场景: Web应用UI自动化测试

## YAML脚本标准结构

```yaml
web:
  url: "https://example.com"  # 必填，访问的URL
  viewportWidth: 1280  # 可选，默认1280
  viewportHeight: 960  # 可选，默认960
  deviceScaleFactor: 1  # 可选，设备像素比，默认1
  userAgent: "Mozilla/5.0..."  # 可选，浏览器UA

  # 等待网络空闲策略
  waitForNetworkIdle:
    timeout: 2000  # 等待超时时间，默认2000ms
    continueOnNetworkIdleError: true  # 超时后是否继续，默认true

  # 可选配置
  output: "./output/result.json"  # aiQuery结果输出文件路径
  serve: "./public"  # 本地静态服务根目录
  cookie: "./cookies.json"  # Cookie文件路径
  acceptInsecureCerts: false  # 是否忽略HTTPS证书错误
  forceSameTabNavigation: true  # 是否限制在当前tab打开
  bridgeMode: false  # 桥接模式: false | 'newTabWithUrl' | 'currentTab'
  closeNewTabsAfterDisconnect: false  # 桥接断开时是否关闭新标签页
  aiActionContext: "页面功能描述，帮助AI理解测试上下文"

tasks:
  - name: "测试任务名称"
    continueOnError: false  # 可选，错误时是否继续执行下一个任务
    flow:
      - ai: "type 'search text' in search box, click search button"
      - sleep: 3000
      - aiAssert: "验证条件"
        errorMessage: "失败提示"
```

## 核心API格式详解（基于官方文档）

### 1. aiAction/ai - 复合操作（推荐使用）
```yaml
- aiAction: "type 'Headphones' in search box, hit Enter"
- ai: "type 'standard_user' in user name input, type 'secret_sauce' in password, click 'Login'"
- ai: "click the link 'Go to planet list'"
- aiAction: "scroll down the page for 800px"
```
**重要**: `ai` 是 `aiAction` 的简写形式，都可以描述复合操作

### 2. 即时操作API（也支持使用）
```yaml
# 点击元素
- aiTap: "页面右上角的登录按钮"
  deepThink: true
  cacheable: true

# 鼠标悬停
- aiHover: "导航菜单项"
  deepThink: true

# 文本输入
- aiInput: "test@example.com"
  locate: "用户名输入框"
  deepThink: true

# 键盘操作
- aiKeyboardPress: "Enter"
  locate: "搜索框"

# 滚动操作
- aiScroll:
    direction: "down"
    scrollType: "once"
    distance: 300
  locate: "页面主体区域"
```

### 3. aiQuery - 数据提取（支持命名）
```yaml
- aiQuery: >
    {name: string, price: number, subTitle: string}[],
    return item name, price and the subTitle on the lower right corner of each item
  name: headphones

- aiQuery: >
    {name: string, status: string}[],
    service status of github page
  name: status
```

### 4. 等待和断言
```yaml
# 等待条件满足（YAML中使用timeout，不是timeoutMs）
- aiWaitFor: "页面加载完成显示搜索结果"
  timeout: 30000  # 毫秒

# 断言验证
- aiAssert: "There are some headphone items on the page"
  errorMessage: "页面未显示耳机商品"

- aiAssert: "The price of 'Sauce Labs Fleece Jacket' is 49.99"
```

### 5. 其他操作
```yaml
# 固定等待
- sleep: 5000  # 等待5秒

# 执行JavaScript代码
- javascript: >
    document.title
  name: page-title

# 或者简单的JavaScript
- javascript: "console.log('test')"
```

## 官方示例参考

### 示例1: eBay搜索耳机
```yaml
web:
  url: https://www.ebay.com
  viewportWidth: 400
  viewportHeight: 1200
  output: ./output/ebay-headphones.json

tasks:
  - name: search headphones
    flow:
      - aiAction: type 'Headphones' in search box, hit Enter
      - sleep: 5000
      - aiAction: scroll down the page for 800px

  - name: extract headphones info
    flow:
      - aiQuery: >
          {name: string, price: number, subTitle: string}[],
          return item name, price and the subTitle on the lower right corner of each item
        name: headphones
      - aiNumber: "What is the price of the first headphone?"
      - aiBoolean: "Is the price of the headphones more than 1000?"
```

### 示例2: SauceDemo登录测试
```yaml
web:
  url: https://www.saucedemo.com/
  output: ./output/sauce-demo-items.json

tasks:
  - name: login
    flow:
      - aiAction: type 'standard_user' in user name input, type 'secret_sauce' in password, click 'Login'

  - name: extract items info
    flow:
      - aiQuery: >
          {name: string, price: number, actionBtnName: string}[],
          return item name, price and the action button name on the lower right corner of each item
        name: items
      - aiAssert: The price of 'Sauce Labs Fleece Jacket' is 49.99
```

## 重要规则和最佳实践

### ✅ 正确做法
1. **优先使用ai/aiAction**：`ai: "type 'text' in input box, click button"`
2. **即时操作API也可使用**：aiTap、aiInput、aiHover等都支持
3. **aiQuery使用多行格式**：使用 `>` 符号进行多行描述
4. **为aiQuery添加name**：便于结果识别
5. **合理使用sleep**：在操作间添加等待时间
6. **环境变量支持**：使用 `${variable-name}` 格式
7. **正确的等待API**：YAML中aiWaitFor使用 `timeout`，不是 `timeoutMs`

### ✅ 环境变量使用
```yaml
# 支持环境变量替换
web:
  url: "${BASE_URL}/login"

tasks:
  - name: "登录测试"
    flow:
      - ai: "type '${USERNAME}' in username field, type '${PASSWORD}' in password field, click login"
```

### ✅ 灵活的API选择
```yaml
# 方式1：使用复合操作（推荐）
- ai: "type 'computer' in search box, hit Enter"

# 方式2：使用即时操作API
- aiInput: "computer"
  locate: "搜索输入框"
- aiTap: "搜索按钮"

# 方式3：混合使用
- aiInput: "computer"
  locate: "搜索输入框"
- ai: "click search button and wait for results"
```

### ❌ 需要注意的差异
```yaml
# YAML格式中的等待API
- aiWaitFor: "条件描述"
  timeout: 30000  # 使用timeout，不是timeoutMs

# 断言错误信息字段
- aiAssert: "断言条件"
  errorMessage: "错误信息"  # 使用errorMessage，不是errorMsg
```

### 移动设备配置示例
```yaml
web:
  url: https://example.com
  viewportWidth: 400
  viewportHeight: 1200
  deviceScaleFactor: 2
  userAgent: "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36"
```

### 本地服务器配置示例
```yaml
web:
  serve: ./public
  url: index.html  # 相对于serve目录的路径
```

### 桥接模式配置示例
```yaml
web:
  url: https://example.com
  bridgeMode: newTabWithUrl  # 或 'currentTab'
  closeNewTabsAfterDisconnect: true
```

## 脚本质量标准

### 1. API格式正确性
- 优先使用 `ai` 或 `aiAction` 进行复合操作
- 即时操作API（aiTap、aiInput等）也完全支持
- 正确使用YAML格式的参数名（timeout而非timeoutMs）
- 正确使用aiQuery的多行格式

### 2. 操作描述准确性
- 使用自然语言描述完整操作流程
- 包含具体的输入内容和目标元素
- 描述清晰的验证条件
- 支持环境变量动态替换

### 3. 结构完整性
- 合理的任务分组和命名
- 适当的等待时间和错误处理
- 完整的验证流程
- 灵活使用不同的API组合

### 4. 高级特性支持
- 环境变量：`${VARIABLE_NAME}`
- JavaScript执行：`javascript` 动作
- 数据输出：`output` 配置和 `name` 字段
- 桥接模式：与现有浏览器会话集成

请根据UI分析结果，严格按照以上官方文档格式生成标准的MidScene.js YAML测试脚本。
优先使用 `ai` 进行复合操作，必要时可结合即时操作API。
直接输出完整的YAML格式内容，不要包装在JSON中。
"""

    @message_handler
    async def handle_message(self, message: WebMultimodalAnalysisResponse, ctx: MessageContext) -> None:
        """处理多模态分析结果消息，生成YAML测试脚本"""
        try:
            monitor_id = self.start_performance_monitoring()

            # 获取分析结果信息
            analysis_id = message.analysis_id

            # 使用工厂创建agent并执行YAML生成任务
            agent = self.create_assistant_agent(
                model_client_instance=self.model_client
            )

            from autogen_core.memory import ListMemory, MemoryContent, MemoryMimeType
            memory = ListMemory()

            # 准备生成任务
            task = self._prepare_yaml_generation_task(message)

            # 执行YAML生成
            yaml_content = ""
            stream = agent.run_stream(task=task)
            async for event in stream:  # type: ignore
                if isinstance(event, ModelClientStreamingChunkEvent):
                    await self.send_response(content=event.content, region=MessageRegion.GENERATION)
                    continue
                if isinstance(event, TextMessage):
                    yaml_content = event.model_dump_json()
                    await memory.add(MemoryContent(
                        content=yaml_content,
                        mime_type=MemoryMimeType.JSON.value
                    ))
            self.metrics = self.end_performance_monitoring(monitor_id=monitor_id)

            # 处理生成的YAML内容
            yaml_result = await self._process_generated_yaml(yaml_content, message)

            # 保存YAML文件
            file_path = await self._save_yaml_file(yaml_result.get("yaml_script", {}).get("content"), analysis_id)

            # 构建完整结果
            result = {
                "yaml_script": yaml_result.get("yaml_script"),
                "yaml_content": yaml_result.get("yaml_content", ""),
                "file_path": file_path,
                "generation_time": datetime.now().isoformat(),
                "memory_content": self.serialize_memory_content(memory),
                "metrics": self.metrics
            }

            # 发送脚本到数据库保存智能体
            await self._send_to_database_saver(yaml_result.get("yaml_content", ""), message, file_path)

            await self.send_response(
                "✅ YAML测试脚本生成完成",
                is_final=True,
                result=result
            )

        except Exception as e:
            await self.handle_exception("handle_message", e)

    async def _send_to_database_saver(self, yaml_content: str, analysis_result: WebMultimodalAnalysisResponse, file_path: str) -> None:
        """发送脚本到数据库保存智能体"""
        try:
            from app.agents.web.test_script_storage_agent import ScriptSaveRequest
            from app.models.test_scripts import ScriptFormat, ScriptType

            # 创建保存请求
            save_request = ScriptSaveRequest(
                session_id=analysis_result.analysis_id,
                script_content=yaml_content,
                script_format=ScriptFormat.YAML,
                script_type=ScriptType.IMAGE_ANALYSIS,
                analysis_result=analysis_result,
                source_agent="yaml_generator",
                file_path=file_path
            )

            # 发送到数据库保存智能体
            await self.publish_message(
                save_request,
                topic_id=TopicId(type="script_database_saver", source=self.id.key)
            )

            logger.info(f"YAML脚本已发送到数据库保存智能体: {analysis_result.analysis_id}")

        except Exception as e:
            logger.error(f"发送脚本到数据库保存智能体失败: {e}")
            # 不抛出异常，避免影响主流程


    def _prepare_yaml_generation_task(self, message: WebMultimodalAnalysisResponse) -> str:
        """准备YAML生成任务"""
        try:
            # 构建分析摘要
            analysis_summary = self._prepare_analysis_summary(message)

            # 构建生成任务
            task = f"""
基于以下UI分析结果，生成标准的MidScene.js YAML测试脚本：

{analysis_summary}

## 生成要求

1. **输出格式**: 直接输出完整的YAML格式脚本，不要包装在JSON或其他格式中
2. **元素描述**: 使用详细的视觉描述，包含位置、颜色、文本等特征
3. **操作选择**: 根据元素类型选择最合适的MidScene.js动作
4. **流程设计**: 设计完整的测试流程，包含验证步骤
5. **上下文设置**: 在web.aiActionContext中描述页面功能和测试目标

请严格按照MidScene.js YAML规范生成高质量的测试脚本。
"""
            return task

        except Exception as e:
            logger.error(f"准备YAML生成任务失败: {str(e)}")
            raise

    def _prepare_analysis_summary(self, message: WebMultimodalAnalysisResponse) -> str:
        """准备优化后的分析摘要，充分利用GraphFlow智能体的结构化输出和数据库页面元素信息"""
        try:
            page_analysis = message.page_analysis

            # 构建基础摘要
            summary = f"""
## 页面基本信息
- **标题**: {page_analysis.page_title}
- **类型**: {page_analysis.page_type}
- **主要内容**: {page_analysis.main_content}

## GraphFlow分析结果
### UI元素:
{page_analysis.ui_elements}
### 交互流程:
{page_analysis.user_flows}
### 测试场景:
{page_analysis.test_scenarios}
"""

            # 如果有数据库页面元素信息，添加简化的元素指导
            if page_analysis.database_elements:
                summary += self._add_database_elements_info_yaml(page_analysis.database_elements)

            summary += f"""
## MidScene.js YAML设计指导

基于以上分析结果、数据库页面元素信息，请重点关注：

1. **精确元素定位**:
   - 优先使用数据库中提供的元素描述和选择器信息
   - 结合元素的位置、视觉特征进行YAML action设计
   - 对于高置信度元素，直接使用其描述进行操作

2. **YAML结构优化**:
   - 根据元素类型选择最合适的action类型
   - 对于button类型元素，使用tap action
   - 对于input类型元素，使用input action
   - 对于验证操作，使用assert action

3. **测试优先级**:
   - 优先测试数据库中标记为高优先级的元素
   - 确保可测试性强的元素都被包含在测试步骤中
   - 为低置信度元素添加额外的等待时间

4. **选择器策略**:
   - 当数据库提供了选择器时，在YAML中同时提供AI描述和选择器
   - 使用AI描述作为主要定位方式，选择器作为备选方案
   - 确保生成的YAML具有良好的可维护性
"""
            return summary

        except Exception as e:
            logger.error(f"准备分析摘要失败: {str(e)}")
            return "分析摘要生成失败"

    def _add_database_elements_info_yaml(self, database_elements: Dict[str, Any]) -> str:
        """添加数据库页面元素信息（YAML版本）"""
        try:
            info = "\n## 页面元素信息\n\n"

            # 处理页面信息
            pages = database_elements.get("pages", [])
            elements = database_elements.get("elements", [])

            if pages:
                # 按页面组织元素信息
                for page in pages:
                    page_name = page.get("page_name", "未知页面")
                    page_desc = page.get("page_description", "")
                    page_url = page.get("page_url", "")

                    info += f"### 页面名称：{page_name}\n"
                    if page_desc:
                        info += f"页面描述：{page_desc}\n"
                    if page_url:
                        info += f"页面URL：{page_url}\n"

                    info += "页面元素：\n"

                    # 获取该页面的元素
                    page_elements = page.get("elements", [])
                    if page_elements:
                        for element in page_elements:
                            element_name = element.get("element_name", "未命名")
                            element_desc = element.get("element_description", "")
                            elem_type = element.get("element_type", "unknown")
                            selector = element.get("selector", "")
                            position = element.get("position", "")
                            is_testable = element.get("is_testable", False)

                            info += f"- **{element_name}** ({elem_type})\n"
                            info += f"  描述：{element_desc}\n"
                            if selector:
                                info += f"  选择器：{selector}\n"
                            if position:
                                info += f"  位置：{position}\n"
                            info += f"  可测试：{'是' if is_testable else '否'}\n"
                            info += "\n"
                    else:
                        info += "  暂无元素信息\n\n"

                    info += "\n"

            elif elements:
                # 如果没有页面分组，直接列出所有元素
                info += "### 页面名称：未分组页面\n"
                info += "页面元素：\n"

                for element in elements:
                    element_name = element.get("element_name", "未命名")
                    element_desc = element.get("element_description", "")
                    elem_type = element.get("element_type", "unknown")
                    selector = element.get("selector", "")
                    position = element.get("position", "")
                    is_testable = element.get("is_testable", False)

                    info += f"- **{element_name}** ({elem_type})\n"
                    info += f"  描述：{element_desc}\n"
                    if selector:
                        info += f"  选择器：{selector}\n"
                    if position:
                        info += f"  位置：{position}\n"
                    info += f"  可测试：{'是' if is_testable else '否'}\n"
                    info += "\n"

            info += "请根据以上页面元素信息生成准确的MidScene.js YAML测试脚本。\n\n"

            return info

        except Exception as e:
            logger.error(f"添加数据库元素信息失败: {str(e)}")
            return "\n## 页面元素信息获取失败\n\n"



    def _build_enhanced_ui_elements_summary(self, ui_elements) -> str:
        """构建增强的UI元素摘要，充分利用优化后的结构化数据"""
        try:
            if not ui_elements:
                return "### 🔍 UI元素分析\n暂无识别到的UI元素"

            # 按元素类型分类
            elements_by_type = {}
            high_confidence_elements = []

            for element in ui_elements[:15]:  # 增加处理数量
                element_type = getattr(element, 'element_type', 'unknown')
                confidence = getattr(element, 'confidence_score', 0.0)

                if element_type not in elements_by_type:
                    elements_by_type[element_type] = []
                elements_by_type[element_type].append(element)

                if confidence >= 0.8:
                    high_confidence_elements.append(element)

            summary = "### 🔍 UI元素分析\n\n"

            # 高置信度元素优先展示
            if high_confidence_elements:
                summary += "#### 🎯 高置信度元素 (推荐优先使用)\n"
                for i, element in enumerate(high_confidence_elements[:8], 1):
                    summary += self._format_ui_element_detail(element, i)
                summary += "\n"

            # 按类型分组展示
            type_names = {
                'button': '🔘 按钮元素',
                'input': '📝 输入元素',
                'link': '🔗 链接元素',
                'text': '📄 文本元素',
                'image': '🖼️ 图片元素',
                'form': '📋 表单元素',
                'unknown': '❓ 其他元素'
            }

            for element_type, elements in elements_by_type.items():
                if len(elements) > 0:
                    type_name = type_names.get(element_type, f'📦 {element_type}元素')
                    summary += f"#### {type_name} ({len(elements)}个)\n"
                    for i, element in enumerate(elements[:5], 1):  # 每类最多5个
                        summary += self._format_ui_element_brief(element, i)
                    summary += "\n"

            return summary

        except Exception as e:
            logger.error(f"构建UI元素摘要失败: {str(e)}")
            return "### 🔍 UI元素分析\n构建摘要失败"

    def _format_ui_element_detail(self, element, index: int) -> str:
        """格式化UI元素的详细信息"""
        try:
            name = getattr(element, 'name', f'元素{index}')
            element_type = getattr(element, 'element_type', 'unknown')
            description = getattr(element, 'description', '无描述')
            confidence = getattr(element, 'confidence_score', 0.0)

            # 尝试解析位置信息
            position_info = ""
            if hasattr(element, 'position') and element.position:
                if isinstance(element.position, dict):
                    area = element.position.get('area', '')
                    relative_to = element.position.get('relative_to', '')
                    if area or relative_to:
                        position_info = f" | 位置: {area} {relative_to}".strip()

            return f"{index}. **{name}** ({element_type}) - 置信度: {confidence:.2f}\n   📍 {description}{position_info}\n\n"

        except Exception as e:
            logger.debug(f"格式化UI元素详情失败: {str(e)}")
            return f"{index}. 元素信息解析失败\n\n"

    def _format_ui_element_brief(self, element, index: int) -> str:
        """格式化UI元素的简要信息"""
        try:
            name = getattr(element, 'name', f'元素{index}')
            description = getattr(element, 'description', '无描述')
            confidence = getattr(element, 'confidence_score', 0.0)

            # 截断过长的描述
            if len(description) > 80:
                description = description[:80] + "..."

            return f"   {index}. {name} (置信度: {confidence:.2f}) - {description}\n"

        except Exception as e:
            logger.debug(f"格式化UI元素简要信息失败: {str(e)}")
            return f"   {index}. 元素信息解析失败\n"

    def _build_enhanced_user_flows_summary(self, user_flows) -> str:
        """构建增强的用户交互流程摘要，支持结构化流程数据"""
        try:
            if not user_flows:
                return "### 🔄 交互流程分析\n暂无识别到的交互流程"

            summary = "### 🔄 交互流程分析\n\n"

            # 尝试解析结构化的流程数据
            structured_flows = []
            simple_flows = []

            for flow in user_flows[:10]:  # 增加处理数量
                if isinstance(flow, dict):
                    structured_flows.append(flow)
                else:
                    simple_flows.append(str(flow))

            # 处理结构化流程
            if structured_flows:
                summary += "#### 🎯 主要交互流程\n\n"
                for i, flow_data in enumerate(structured_flows[:5], 1):
                    summary += self._format_structured_flow(flow_data, i)
                summary += "\n"

            # 处理简单流程
            if simple_flows:
                summary += "#### 📝 基础操作流程\n\n"
                for i, flow in enumerate(simple_flows[:8], 1):
                    # 清理和格式化流程描述
                    clean_flow = flow.strip()
                    if len(clean_flow) > 100:
                        clean_flow = clean_flow[:100] + "..."
                    summary += f"{i}. {clean_flow}\n"
                summary += "\n"

            # 添加流程统计信息
            total_flows = len(structured_flows) + len(simple_flows)
            summary += f"**流程统计**: 共识别 {total_flows} 个交互流程，其中 {len(structured_flows)} 个结构化流程\n\n"

            return summary

        except Exception as e:
            logger.error(f"构建交互流程摘要失败: {str(e)}")
            return "### 🔄 交互流程分析\n构建摘要失败"

    def _format_structured_flow(self, flow_data: dict, index: int) -> str:
        """格式化结构化的交互流程"""
        try:
            flow_name = flow_data.get('flow_name', f'流程{index}')
            description = flow_data.get('description', '无描述')
            steps = flow_data.get('steps', [])
            success_criteria = flow_data.get('success_criteria', '')

            formatted = f"**{index}. {flow_name}**\n"
            formatted += f"   📋 描述: {description}\n"

            if steps:
                formatted += f"   🔢 步骤 ({len(steps)}个):\n"
                for step_idx, step in enumerate(steps[:5], 1):  # 最多显示5个步骤
                    if isinstance(step, dict):
                        action = step.get('action', '未知操作')
                        target = step.get('target_element', '未知元素')
                        formatted += f"      {step_idx}. {action} → {target}\n"
                    else:
                        formatted += f"      {step_idx}. {str(step)}\n"

            if success_criteria:
                formatted += f"   ✅ 成功标准: {success_criteria}\n"

            formatted += "\n"
            return formatted

        except Exception as e:
            logger.debug(f"格式化结构化流程失败: {str(e)}")
            return f"**{index}. 流程信息解析失败**\n\n"

    def _build_enhanced_test_scenarios_summary(self, test_scenarios) -> str:
        """构建增强的测试场景摘要，充分利用MidScene.js专家的输出"""
        try:
            if not test_scenarios:
                return "### 🧪 测试场景设计\n暂无设计的测试场景"

            summary = "### 🧪 测试场景设计\n\n"

            # 分析场景类型和复杂度
            scenario_stats = {
                'total': len(test_scenarios),
                'high_priority': 0,
                'medium_priority': 0,
                'low_priority': 0,
                'with_midscene_actions': 0
            }

            for i, scenario in enumerate(test_scenarios[:8], 1):  # 增加处理数量
                if isinstance(scenario, dict):
                    summary += self._format_structured_scenario(scenario, i)

                    # 统计优先级
                    priority = scenario.get('priority', 'medium')
                    if priority == 'high':
                        scenario_stats['high_priority'] += 1
                    elif priority == 'low':
                        scenario_stats['low_priority'] += 1
                    else:
                        scenario_stats['medium_priority'] += 1

                    # 检查是否包含MidScene.js动作
                    steps = scenario.get('steps', [])
                    if any('ai' in str(step).lower() for step in steps):
                        scenario_stats['with_midscene_actions'] += 1

                else:
                    summary += f"**{i}. 基础测试场景**\n"
                    scenario_str = str(scenario)
                    if len(scenario_str) > 150:
                        scenario_str = scenario_str[:150] + "..."
                    summary += f"   📝 {scenario_str}\n\n"

            # 添加场景统计和建议
            summary += "#### 📊 场景分析统计\n\n"
            summary += f"- **总场景数**: {scenario_stats['total']}\n"
            summary += f"- **优先级分布**: 高({scenario_stats['high_priority']}) | 中({scenario_stats['medium_priority']}) | 低({scenario_stats['low_priority']})\n"
            summary += f"- **MidScene.js就绪**: {scenario_stats['with_midscene_actions']}/{scenario_stats['total']} 个场景包含AI动作\n\n"

            # 提供优化建议
            if scenario_stats['with_midscene_actions'] < scenario_stats['total']:
                summary += "💡 **优化建议**: 部分场景可进一步优化为MidScene.js格式的AI动作\n\n"

            return summary

        except Exception as e:
            logger.error(f"构建测试场景摘要失败: {str(e)}")
            return "### 🧪 测试场景设计\n构建摘要失败"

    def _format_structured_scenario(self, scenario: dict, index: int) -> str:
        """格式化结构化的测试场景"""
        try:
            name = scenario.get('name', f'测试场景{index}')
            steps = scenario.get('steps', [])
            priority = scenario.get('priority', 'medium')
            duration = scenario.get('estimated_duration', '未知')

            # 优先级图标
            priority_icons = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }
            priority_icon = priority_icons.get(priority, '⚪')

            formatted = f"**{index}. {name}** {priority_icon} ({priority}优先级)\n"
            formatted += f"   ⏱️ 预估时长: {duration}\n"

            if steps:
                formatted += f"   📋 测试步骤 ({len(steps)}个):\n"
                for step_idx, step in enumerate(steps[:6], 1):  # 最多显示6个步骤
                    step_str = str(step).strip()
                    if len(step_str) > 80:
                        step_str = step_str[:80] + "..."

                    # 检查是否为MidScene.js动作
                    if any(action in step_str.lower() for action in ['aitap', 'aiinput', 'aiassert', 'aiquery']):
                        formatted += f"      {step_idx}. 🤖 {step_str}\n"
                    else:
                        formatted += f"      {step_idx}. 📝 {step_str}\n"

            formatted += "\n"
            return formatted

        except Exception as e:
            logger.debug(f"格式化测试场景失败: {str(e)}")
            return f"**{index}. 场景信息解析失败**\n\n"

    def _build_quality_assessment_summary(self, message: WebMultimodalAnalysisResponse) -> str:
        """构建质量评估摘要，展示GraphFlow质量控制的结果"""
        try:
            summary = "### 📊 质量评估报告\n\n"

            # 基础质量指标
            confidence = message.confidence_score
            processing_time = getattr(message, 'processing_time', 0.0)
            team_enabled = getattr(message, 'team_collaboration_enabled', False)
            user_feedback = getattr(message, 'user_feedback_provided', False)

            # 置信度评级
            if confidence >= 0.9:
                confidence_level = "🟢 优秀"
            elif confidence >= 0.8:
                confidence_level = "🟡 良好"
            elif confidence >= 0.7:
                confidence_level = "🟠 一般"
            else:
                confidence_level = "🔴 需改进"

            summary += f"#### 🎯 分析质量指标\n\n"
            summary += f"- **整体置信度**: {confidence:.2f} ({confidence_level})\n"
            summary += f"- **处理时长**: {processing_time:.2f}秒\n"
            summary += f"- **团队协作**: {'✅ 已启用' if team_enabled else '❌ 未启用'}\n"
            summary += f"- **用户反馈**: {'✅ 已收集' if user_feedback else '⏸️ 未收集'}\n\n"

            # 数据完整性评估
            page_analysis = message.page_analysis
            ui_count = len(page_analysis.ui_elements) if page_analysis.ui_elements else 0
            flow_count = len(page_analysis.user_flows) if page_analysis.user_flows else 0
            scenario_count = len(page_analysis.test_scenarios) if page_analysis.test_scenarios else 0

            summary += f"#### 📈 数据完整性评估\n\n"
            summary += f"- **UI元素**: {ui_count} 个 {'✅' if ui_count >= 5 else '⚠️' if ui_count >= 2 else '❌'}\n"
            summary += f"- **交互流程**: {flow_count} 个 {'✅' if flow_count >= 3 else '⚠️' if flow_count >= 1 else '❌'}\n"
            summary += f"- **测试场景**: {scenario_count} 个 {'✅' if scenario_count >= 2 else '⚠️' if scenario_count >= 1 else '❌'}\n\n"

            # GraphFlow工作流状态
            if team_enabled:
                summary += f"#### 🔄 GraphFlow工作流状态\n\n"
                summary += f"- **并行分析**: UI_Expert + Interaction_Analyst ✅\n"
                summary += f"- **质量控制**: Quality_Reviewer 审查通过 ✅\n"
                summary += f"- **消息过滤**: MidScene_Expert 接收高质量输入 ✅\n"
                summary += f"- **协作效率**: 优化的多智能体协作 ✅\n\n"

            return summary

        except Exception as e:
            logger.error(f"构建质量评估摘要失败: {str(e)}")
            return "### 📊 质量评估报告\n构建摘要失败\n\n"

    async def _process_generated_yaml(self, yaml_content: str, message: WebMultimodalAnalysisResponse) -> Dict[str, Any]:
        """处理生成的YAML内容"""
        try:
            # 清理YAML内容，移除可能的markdown标记
            cleaned_yaml = self._clean_yaml_content(yaml_content)

            # 验证YAML格式
            try:
                yaml_data = yaml.safe_load(cleaned_yaml)
                if not yaml_data:
                    raise ValueError("YAML内容为空")

                # 验证基本结构
                validated_data = self._validate_yaml_structure(yaml_data, message)

                # 计算复杂度和时长
                complexity_score = self._calculate_complexity_score(validated_data)
                estimated_duration = self._estimate_execution_duration(validated_data)

                return {
                    "yaml_script": validated_data,
                    "yaml_content": yaml.dump(validated_data, default_flow_style=False, allow_unicode=True, sort_keys=False),
                    "estimated_duration": estimated_duration,
                    "complexity_score": complexity_score
                }

            except yaml.YAMLError as e:
                logger.warning(f"YAML解析失败，尝试修复: {str(e)}")
                # 尝试修复常见的YAML格式问题
                fixed_yaml = self._fix_yaml_format(cleaned_yaml)
                yaml_data = yaml.safe_load(fixed_yaml)

                validated_data = self._validate_yaml_structure(yaml_data, message)
                complexity_score = self._calculate_complexity_score(validated_data)
                estimated_duration = self._estimate_execution_duration(validated_data)

                return {
                    "yaml_script": validated_data,
                    "yaml_content": yaml.dump(validated_data, default_flow_style=False, allow_unicode=True, sort_keys=False),
                    "estimated_duration": estimated_duration,
                    "complexity_score": complexity_score
                }

        except Exception as e:
            logger.error(f"处理生成的YAML失败: {str(e)}")
            return await self._generate_default_yaml(message)

    def _clean_yaml_content(self, content: str) -> str:
        """清理YAML内容，移除markdown标记和多余字符"""
        try:
            # 移除markdown代码块标记
            content = content.replace('```yaml', '').replace('```', '')

            # 移除可能的JSON包装
            if content.strip().startswith('{') and content.strip().endswith('}'):
                try:
                    json_data = json.loads(content)
                    if 'yaml_script' in json_data:
                        return yaml.dump(json_data['yaml_script'], default_flow_style=False, allow_unicode=True)
                except:
                    pass

            # 清理多余的空行和空格
            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                if line.strip():  # 保留非空行
                    cleaned_lines.append(line.rstrip())

            return '\n'.join(cleaned_lines)

        except Exception as e:
            logger.warning(f"清理YAML内容失败: {str(e)}")
            return content

    def _fix_yaml_format(self, content: str) -> str:
        """修复常见的YAML格式问题"""
        try:
            # 修复缩进问题
            lines = content.split('\n')
            fixed_lines = []

            for line in lines:
                # 确保正确的缩进（使用2个空格）
                if line.strip():
                    indent_level = len(line) - len(line.lstrip())
                    if indent_level % 2 != 0:  # 奇数缩进，调整为偶数
                        line = ' ' + line
                    fixed_lines.append(line)
                else:
                    fixed_lines.append('')

            return '\n'.join(fixed_lines)

        except Exception as e:
            logger.warning(f"修复YAML格式失败: {str(e)}")
            return content

    def _validate_yaml_structure(self, data: Dict[str, Any], message: WebMultimodalAnalysisResponse) -> Dict[str, Any]:
        """验证和补充YAML结构"""
        try:
            # 确保基本结构存在
            if not isinstance(data, dict):
                raise ValueError("YAML根节点必须是字典")

            # 验证web配置
            if "web" not in data:
                data["web"] = {}

            web_config = data["web"]
            web_config.setdefault("url", "https://example.com")
            web_config.setdefault("viewportWidth", 1280)
            web_config.setdefault("viewportHeight", 960)
            web_config.setdefault("waitForNetworkIdle", {
                "timeout": 2000,
                "continueOnNetworkIdleError": True
            })

            # 设置aiActionContext
            page_analysis = message.page_analysis
            if "aiActionContext" not in web_config:
                web_config["aiActionContext"] = f"这是一个{page_analysis.page_type}页面，标题为{page_analysis.page_title}"

            # 验证tasks
            if "tasks" not in data:
                data["tasks"] = []

            if not data["tasks"]:
                # 如果没有任务，创建默认任务
                data["tasks"] = [{
                    "name": f"{page_analysis.page_title}测试",
                    "continueOnError": False,
                    "flow": [
                        {"aiTap": "页面中的主要按钮", "deepThink": True},
                        {"aiAssert": "操作执行成功", "errorMsg": "操作验证失败"}
                    ]
                }]

            # 验证每个任务
            for i, task in enumerate(data["tasks"]):
                if not isinstance(task, dict):
                    continue

                task.setdefault("name", f"测试任务{i+1}")
                task.setdefault("continueOnError", False)
                task.setdefault("flow", [])

                # 确保flow不为空
                if not task["flow"]:
                    task["flow"] = [
                        {"aiTap": "页面中的主要元素", "deepThink": True},
                        {"aiAssert": "操作完成", "errorMsg": "验证失败"}
                    ]

            return data

        except Exception as e:
            logger.error(f"验证YAML结构失败: {str(e)}")
            # 返回最小可用结构
            return {
                "web": {
                    "url": "https://example.com",
                    "viewportWidth": 1280,
                    "viewportHeight": 960,
                    "waitForNetworkIdle": {"timeout": 2000, "continueOnNetworkIdleError": True},
                    "aiActionContext": "基础测试页面"
                },
                "tasks": [{
                    "name": "基础测试",
                    "continueOnError": False,
                    "flow": [
                        {"aiTap": "页面中的主要按钮", "deepThink": True},
                        {"aiAssert": "操作执行成功", "errorMsg": "操作验证失败"}
                    ]
                }]
            }

    def _calculate_complexity_score(self, yaml_data: Dict[str, Any]) -> float:
        """计算脚本复杂度评分"""
        try:
            score = 1.0

            tasks = yaml_data.get("tasks", [])
            if not tasks:
                return score

            total_actions = 0
            complex_actions = 0

            for task in tasks:
                flow = task.get("flow", [])
                total_actions += len(flow)

                for action in flow:
                    if isinstance(action, dict):
                        # 复杂动作类型加分
                        if any(key in action for key in ["aiQuery", "aiWaitFor", "aiHover"]):
                            complex_actions += 1
                        # 有参数的动作加分
                        if len(action) > 1:
                            complex_actions += 0.5

            # 基础分数 + 动作数量分数 + 复杂度分数
            score = 1.0 + (total_actions * 0.3) + (complex_actions * 0.5)

            # 限制在1-5分之间
            return min(max(score, 1.0), 5.0)

        except Exception as e:
            logger.warning(f"计算复杂度评分失败: {str(e)}")
            return 2.5

    def _estimate_execution_duration(self, yaml_data: Dict[str, Any]) -> str:
        """估算执行时长"""
        try:
            tasks = yaml_data.get("tasks", [])
            if not tasks:
                return "10秒"

            total_seconds = 0

            for task in tasks:
                flow = task.get("flow", [])
                for action in flow:
                    if isinstance(action, dict):
                        # 根据动作类型估算时间
                        if "aiTap" in action:
                            total_seconds += 2
                        elif "aiInput" in action:
                            total_seconds += 3
                        elif "aiQuery" in action:
                            total_seconds += 4
                        elif "aiAssert" in action:
                            total_seconds += 2
                        elif "aiWaitFor" in action:
                            total_seconds += 5
                        elif "sleep" in action:
                            sleep_time = action.get("sleep", 1000)
                            total_seconds += sleep_time / 1000
                        else:
                            total_seconds += 2

            # 添加基础页面加载时间
            total_seconds += 5

            if total_seconds < 60:
                return f"{int(total_seconds)}秒"
            else:
                minutes = int(total_seconds // 60)
                seconds = int(total_seconds % 60)
                return f"{minutes}分{seconds}秒"

        except Exception as e:
            logger.warning(f"估算执行时长失败: {str(e)}")
            return "30秒"

    async def _generate_default_yaml(self, message: WebMultimodalAnalysisResponse) -> Dict[str, Any]:
        """生成默认YAML脚本"""
        try:
            page_analysis = message.page_analysis

            # 构建默认任务流程
            default_flow = []

            # 基于UI元素生成操作
            if page_analysis.ui_elements:
                for element in page_analysis.ui_elements[:5]:  # 限制数量
                    if hasattr(element, 'element_type'):
                        if element.element_type == "button":
                            default_flow.append({
                                "aiTap": f"{getattr(element, 'description', '按钮元素')}",
                                "deepThink": True
                            })
                        elif element.element_type == "input":
                            default_flow.append({
                                "aiInput": "测试内容",
                                "locate": f"{getattr(element, 'description', '输入框元素')}"
                            })

            # 添加验证步骤
            if default_flow:
                default_flow.append({
                    "aiAssert": "页面显示预期内容",
                    "errorMsg": "验证失败"
                })

            # 如果没有元素，添加基本操作
            if not default_flow:
                default_flow = [
                    {"aiTap": "页面中的主要按钮", "deepThink": True},
                    {"aiAssert": "操作执行成功", "errorMsg": "操作验证失败"}
                ]

            default_yaml = {
                "web": {
                    "url": "https://example.com",
                    "viewportWidth": 1280,
                    "viewportHeight": 960,
                    "waitForNetworkIdle": {
                        "timeout": 2000,
                        "continueOnNetworkIdleError": True
                    },
                    "aiActionContext": f"这是一个{page_analysis.page_type}页面，标题为{page_analysis.page_title}"
                },
                "tasks": [
                    {
                        "name": f"{page_analysis.page_title}测试",
                        "continueOnError": False,
                        "flow": default_flow
                    }
                ]
            }

            # 计算复杂度和时长
            complexity_score = self._calculate_complexity_score(default_yaml)
            estimated_duration = self._estimate_execution_duration(default_yaml)

            yaml_content_str = yaml.dump(default_yaml, default_flow_style=False, allow_unicode=True, sort_keys=False)

            return {
                "yaml_script": default_yaml,
                "yaml_content": yaml_content_str,
                "estimated_duration": estimated_duration,
                "complexity_score": complexity_score
            }

        except Exception as e:
            logger.error(f"生成默认YAML失败: {str(e)}")
            return {
                "yaml_script": {},
                "yaml_content": "# 默认YAML生成失败",
                "estimated_duration": "未知",
                "complexity_score": 1.0
            }

    async def _save_yaml_file(self, yaml_content: str, analysis_id: str) -> str:
        """保存YAML文件到工作空间和数据库存储目录"""
        try:
            from app.core.config import settings

            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_{analysis_id}_{timestamp}.yaml"

            # 1. 保存到PLAYWRIGHT工作空间（用于执行）
            workspace_dir = Path(settings.MIDSCENE_SCRIPT_PATH)
            workspace_dir.mkdir(parents=True, exist_ok=True)

            # 创建yaml目录
            yaml_workspace_dir = workspace_dir / "yaml"
            yaml_workspace_dir.mkdir(exist_ok=True)

            # 保存到工作空间
            workspace_file_path = yaml_workspace_dir / filename
            with open(workspace_file_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
            logger.info(f"YAML脚本已保存到工作空间: {workspace_file_path}")

            # 2. 保存到数据库存储目录（用于管理）
            storage_dir = Path(settings.YAML_OUTPUT_DIR)
            storage_dir.mkdir(parents=True, exist_ok=True)

            # 保存到存储目录
            storage_file_path = storage_dir / filename
            with open(storage_file_path, "w", encoding="utf-8") as f:
                f.write(yaml_content)
            logger.info(f"YAML脚本已保存到存储目录: {storage_file_path}")

            # 返回数据库中记录的路径
            return str(storage_file_path)

        except Exception as e:
            logger.error(f"保存YAML文件失败: {str(e)}")
            return ""

    def serialize_memory_content(self, memory: ListMemory) -> List[Dict[str, Any]]:
        """将ListMemory序列化为可传输的格式

        Args:
            memory: 内存对象

        Returns:
            List[Dict[str, Any]]: 序列化的内存内容
        """
        memory_content = []
        for content in memory.content:
            memory_content.append({
                "content": content.content,
                "mime_type": content.mime_type,
                "metadata": content.metadata
            })
        return memory_content

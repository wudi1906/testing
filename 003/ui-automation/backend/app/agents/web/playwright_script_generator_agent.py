"""
Playwright代码生成智能体
负责根据多模态分析结果生成MidScene.js + Playwright测试代码
"""
import json
import os
import uuid
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


@type_subscription(topic_type=TopicTypes.PLAYWRIGHT_GENERATOR.value)
class PlaywrightGeneratorAgent(BaseAgent):
    """Playwright代码生成智能体，负责生成MidScene.js + Playwright测试代码"""

    def __init__(self, model_client_instance=None, **kwargs):
        """初始化Playwright代码生成智能体"""
        super().__init__(
            agent_id=AgentTypes.PLAYWRIGHT_GENERATOR.value,
            agent_name=AGENT_NAMES[AgentTypes.PLAYWRIGHT_GENERATOR.value],
            model_client_instance=model_client_instance,
            **kwargs
        )
        self._prompt_template = self._build_prompt_template()
        self.metrics = None

        logger.info(f"Playwright代码生成智能体初始化完成: {self.agent_name}")

    @classmethod
    def create_assistant_agent(cls, model_client_instance=None, **kwargs) -> AssistantAgent:
        """创建用于Playwright代码生成的AssistantAgent实例

        Args:
            model_client_instance: 模型客户端实例
            **kwargs: 其他参数

        Returns:
            AssistantAgent: 配置好的智能体实例
        """
        from app.agents.factory import agent_factory

        return agent_factory.create_assistant_agent(
            name="playwright_generator",
            system_message=cls._build_prompt_template_static(),
            model_client_type="deepseek",
            model_client_stream=True,
            **kwargs
        )

    @staticmethod
    def _build_prompt_template_static() -> str:
        """构建静态的Playwright代码生成提示模板（用于工厂方法）"""
        return """
你是MidScene.js + Playwright测试代码生成专家，专门根据页面分析结果和用户测试需求生成高质量的可直接运行的自动化测试代码。

## 核心任务理解

### 输入信息分析
1. **页面分析结果**: 包含页面的UI元素、用户流程、测试场景等结构化信息
2. **用户测试需求**: main_content字段包含用户用自然语言描述的具体测试步骤和期望
3. **测试上下文**: 页面类型、置信度、分析总结等辅助信息

### 代码生成目标
- 将用户的自然语言测试需求转换为可执行的MidScene.js + Playwright代码
- 充分利用页面分析结果中的UI元素信息进行精确定位
- 确保生成的代码能够完整覆盖用户描述的测试场景

## MidScene.js + Playwright 集成规范（基于官方文档）

### 核心概念
MidScene.js是基于AI的UI自动化测试框架，与Playwright完美集成：
- 官方文档: https://midscenejs.com/zh/integrate-with-playwright.html
- 核心优势: 无需传统选择器，使用AI理解页面内容
- 适用场景: Web应用端到端测试

### 标准fixture.ts（官方推荐）
```typescript
import { test as base } from "@playwright/test";
import type { PlayWrightAiFixtureType } from "@midscene/web/playwright";
import { PlaywrightAiFixture } from "@midscene/web/playwright";
import 'dotenv/config';

export const test = base.extend<PlayWrightAiFixtureType>(PlaywrightAiFixture({
  waitForNetworkIdleTimeout: 20000, // 可选，交互过程中等待网络空闲的超时时间
}));
```

### MidScene.js API（基于官方示例）

#### 1. 基础AI操作
```typescript
// ai/aiAction - 通用AI交互（不优先使用）
await ai('type "Headphones" in search box, hit Enter');
await aiAction('click the blue login button in top right corner');

// aiTap - 点击操作
await aiTap('搜索按钮');

// aiInput - 输入操作
await aiInput('Headphones', '搜索框');

// aiHover - 悬停操作
await aiHover('导航菜单');

// aiKeyboardPress - 键盘操作
await aiKeyboardPress('Enter');

// aiScroll - 滚动操作
await aiScroll({ direction: 'down', scrollType: 'untilBottom' }, '搜索结果列表');
```

#### 2. 查询操作
```typescript
// aiQuery - 结构化数据查询（注意格式）
const items = await aiQuery<Array<{itemTitle: string, price: number}>>(
  '{itemTitle: string, price: Number}[], find item in list and corresponding price'
);

// 特定类型查询
const price = await aiNumber('What is the price of the first headphone?');
const isExpensive = await aiBoolean('Is the price of the headphones more than 1000?');
const name = await aiString('What is the name of the first headphone?');
const location = await aiLocate('What is the location of the first headphone?');
```

#### 3. 验证和等待
```typescript
// aiWaitFor - 等待条件
await aiWaitFor('there is at least one headphone item on page');
await aiWaitFor('搜索结果列表已加载', { timeoutMs: 5000 });

// aiAssert - 断言验证
await aiAssert('There is a category filter on the left');
await aiAssert('页面顶部显示用户头像和用户名');
```

### 官方示例代码模板（基于ebay-search.spec.ts）
```typescript
import { expect } from "@playwright/test";
import { test } from "./fixture";

test.beforeEach(async ({ page }) => {
  page.setViewportSize({ width: 1280, height: 768 });
  await page.goto("https://www.ebay.com");
  await page.waitForLoadState("networkidle");
});

test("search headphone on ebay", async ({
  ai,
  aiQuery,
  aiAssert,
  aiWaitFor,
  aiNumber,
  aiBoolean,
  aiString,
  aiLocate,
}) => {
  // 👀 使用ai进行复合操作
  await ai('type "Headphones" in search box, hit Enter');

  // 👀 等待加载完成
  await aiWaitFor("there is at least one headphone item on page");

  // 👀 查询商品信息（注意格式）
  const items = await aiQuery<Array<{itemTitle: string, price: number}>>(
    "{itemTitle: string, price: Number}[], find item in list and corresponding price"
  );

  // 👀 特定类型查询
  const isMoreThan1000 = await aiBoolean("Is the price of the headphones more than 1000?");
  const price = await aiNumber("What is the price of the first headphone?");
  const name = await aiString("What is the name of the first headphone?");
  const location = await aiLocate("What is the location of the first headphone?");

  // 👀 验证结果
  console.log("headphones in stock", items);
  expect(items?.length).toBeGreaterThan(0);

  // 👀 AI断言
  await aiAssert("There is a category filter on the left");
});
```

## MidScene.js 最佳实践（基于官方指南）

### 1. 提示词优化
- ✅ 详细描述: "找到搜索框（搜索框的上方应该有区域切换按钮），输入'耳机'，敲回车"
- ❌ 简单描述: "搜'耳机'"
- ✅ 具体断言: "界面左侧有类目筛选功能"
- ❌ 模糊断言: "有筛选功能"

### 2. API使用策略
- **ai操作优先**: 用于复合操作，如 `ai('type "text" in input, click button')`
- **即时操作补充**: aiTap、aiInput等用于精确控制
- **查询格式标准**: aiQuery使用 `{field: type}[]` 格式

### 3. 数据查询格式
```typescript
// 正确格式（基于官方示例）
const items = await aiQuery<Array<{itemTitle: string, price: number}>>(
  "{itemTitle: string, price: Number}[], find item in list and corresponding price"
);

// 错误格式
const items = await aiQuery("获取商品列表");
```

### 4. 等待和验证
- 使用自然语言描述等待条件
- 断言使用具体的视觉描述
- 结合console.log输出调试信息

## 代码生成要求

### 1. **用户需求理解与转换**
- **需求分析**: 仔细分析main_content中用户的测试需求描述
- **步骤映射**: 将用户描述的每个测试步骤映射为对应的MidScene.js操作
- **场景完整性**: 确保生成的代码覆盖用户描述的完整测试场景
- **期望验证**: 将用户的预期结果转换为相应的断言和验证

### 2. **输出格式要求**
- 直接输出完整的TypeScript测试文件
- 不要包装在JSON或其他格式中
- 确保代码可以直接运行
- 包含必要的注释说明用户需求对应关系

### 3. **代码结构设计**
- 包含完整的import语句
- 使用test.beforeEach设置页面和视口
- 测试函数包含所有必要的AI操作参数
- 测试用例名称应反映用户的测试意图

### 4. **MidScene.js操作策略**
- **复合操作优先**: 对于用户描述的连续动作，使用ai()进行组合操作
- **精确操作补充**: 对于特定的单一操作，使用aiTap、aiInput等方法
- **智能等待**: 根据用户流程添加适当的aiWaitFor操作
- **数据验证**: 为用户期望的结果添加aiQuery和aiAssert验证

### 5. **视觉描述优化**
- **用户语言转换**: 将用户的自然语言描述转换为MidScene.js的视觉描述
- **元素特征结合**: 结合页面分析中的UI元素信息进行精确描述
- **上下文信息**: 包含位置、颜色、文本等特征，提供足够的上下文
- **避免技术术语**: 使用用户友好的描述而非技术选择器

### 6. **测试可靠性保证**
- 添加适当的console.log用于调试和跟踪
- 使用expect进行标准断言验证
- 考虑异常情况和错误处理
- 确保测试在不同环境下的稳定性

### 7. **特别注意事项**
- **忠实用户意图**: 严格按照用户描述的测试步骤和期望进行代码生成
- **保持测试逻辑**: 不要添加用户未要求的额外测试步骤
- **实用性优先**: 生成实际可执行且有意义的测试代码

请根据页面分析结果和用户测试需求，严格按照官方示例格式生成可直接运行的MidScene.js + Playwright测试代码。
"""

    def _build_prompt_template(self) -> str:
        """构建Playwright代码生成提示模板"""
        return self._build_prompt_template_static()

    @message_handler
    async def handle_message(self, message: WebMultimodalAnalysisResponse, ctx: MessageContext) -> None:
        """处理多模态分析结果消息，生成Playwright测试代码"""
        try:
            monitor_id = self.start_performance_monitoring()

            # 获取分析结果信息
            analysis_id = message.analysis_id

            # 使用工厂创建agent并执行Playwright代码生成任务
            agent = self.create_assistant_agent(
                model_client_instance=self.model_client
            )

            # 准备生成任务
            task = self._prepare_playwright_generation_task(message)

            # 执行Playwright代码生成
            playwright_content = ""
            stream = agent.run_stream(task=task)
            async for event in stream:  # type: ignore
                if isinstance(event, ModelClientStreamingChunkEvent):
                    await self.send_response(content=event.content, region=MessageRegion.GENERATION)
                    continue
                if isinstance(event, TextMessage):
                    playwright_content = event.model_dump_json()

            self.metrics = self.end_performance_monitoring(monitor_id=monitor_id)

            # 处理生成的Playwright代码内容
            playwright_result = await self._process_generated_playwright(playwright_content, message)

            # 保存Playwright文件
            file_paths = await self._save_playwright_files(playwright_result.get("test_code", {}), analysis_id)

            # 构建完整结果
            result = {
                "test_code": playwright_result.get("test_code"),
                "playwright_content": playwright_result.get("playwright_content", ""),
                "file_paths": file_paths,
                "generation_time": datetime.now().isoformat(),
                "metrics": self.metrics
            }

            # 发送脚本到数据库保存智能体
            await self._send_to_database_saver(
                playwright_result.get("test_code").get("test_content"),
                playwright_result.get("playwright_content", ""),
                message,
                file_paths.get("test_file", "")
            )

            await self.send_response(
                "✅ Playwright测试代码生成完成",
                is_final=True,
                result=result
            )

        except Exception as e:
            await self.handle_exception("handle_message", e)

    async def _send_to_database_saver(self, playwright_content: str, script_description: str, analysis_result: WebMultimodalAnalysisResponse, file_path: str) -> None:
        """发送脚本到数据库保存智能体"""
        try:
            from app.agents.web.test_script_storage_agent import ScriptSaveRequest
            from app.models.test_scripts import ScriptFormat, ScriptType
            script_name = os.path.basename(file_path)
            # 创建保存请求
            save_request = ScriptSaveRequest(
                session_id=analysis_result.analysis_id,
                script_name=script_name,
                script_content=playwright_content,
                script_format=ScriptFormat.PLAYWRIGHT,
                script_type=ScriptType.IMAGE_ANALYSIS,
                analysis_result=analysis_result,
                source_agent="playwright_generator",
                file_path=file_path,
                script_description=script_description
            )

            # 发送到数据库保存智能体
            await self.publish_message(
                save_request,
                topic_id=TopicId(type="script_database_saver", source=self.id.key)
            )

            logger.info(f"Playwright脚本已发送到数据库保存智能体: {analysis_result.analysis_id}")

        except Exception as e:
            logger.error(f"发送脚本到数据库保存智能体失败: {e}")
            # 不抛出异常，避免影响主流程

    def _prepare_playwright_generation_task(self, message: WebMultimodalAnalysisResponse) -> str:
        """准备Playwright代码生成任务"""
        try:
            # 构建分析摘要
            analysis_summary = self._prepare_analysis_summary(message)

            # 构建生成任务
            task = f"""
基于以下页面分析结果和用户测试需求，生成标准的MidScene.js + Playwright测试代码：

{analysis_summary}

## 代码生成要求

### 1. 输出格式要求
- **直接输出**: 完整的TypeScript代码，不要包装在JSON或其他格式中
- **文件结构**: 生成完整的.spec.ts测试文件
- **导入语句**: 包含所有必要的import语句

### 2. 测试用例设计要求
- **测试名称**: 基于用户测试需求生成有意义的测试用例名称
- **页面设置**: 使用test.beforeEach设置页面和视口
- **测试步骤**: 严格按照用户描述的测试步骤进行代码组织

### 3. MidScene.js API使用要求
- **优先使用ai()**: 对于复合操作，如"在搜索框输入关键词并点击搜索"
- **精确操作**: 对于单一操作，使用aiTap、aiInput等具体方法
- **视觉描述**: 使用详细的视觉描述而非技术选择器，包含：
  - 元素的位置信息（如"页面顶部"、"左侧导航"、"右上角"）
  - 视觉特征（如"蓝色按钮"、"搜索图标"、"下拉菜单"）
  - 文本内容（如"登录按钮"、"用户名输入框"）

### 4. 数据查询和验证要求
- **类型安全**: 为aiQuery提供准确的TypeScript类型定义
- **数据格式**: 使用标准的JSON Schema格式，如 `{{field: type}}[]`
- **验证断言**: 结合expect断言和aiAssert AI验证
- **等待机制**: 使用aiWaitFor确保页面状态正确

### 5. 代码质量要求
- **错误处理**: 添加适当的等待和重试机制
- **调试信息**: 包含console.log输出关键信息
- **注释说明**: 为复杂操作添加中文注释
- **测试可靠性**: 确保测试在不同环境下的稳定性

### 6. 特别注意事项
- **用户需求优先**: 严格按照main_content中的用户测试需求进行代码生成
- **流程完整性**: 确保测试覆盖用户描述的所有关键步骤
- **实际可执行**: 生成的代码应该能够直接运行，无需额外修改

请严格按照以上要求和MidScene.js + Playwright集成规范生成高质量、可直接运行的测试代码。
"""
            return task

        except Exception as e:
            logger.error(f"准备Playwright生成任务失败: {str(e)}")
            raise

    def _prepare_analysis_summary(self, message: WebMultimodalAnalysisResponse) -> str:
        """准备优化后的分析摘要，充分利用页面分析智能体的结构化输出"""
        try:
            page_analysis = message.page_analysis

            # 格式化UI元素列表
            ui_elements_text = ""
            if page_analysis.ui_elements:
                ui_elements_text = "\n".join([f"  - {element}" for element in page_analysis.ui_elements])
            else:
                ui_elements_text = "  - 暂无识别的UI元素"

            # 格式化用户流程
            user_flows_text = ""
            if page_analysis.user_flows:
                user_flows_text = "\n".join([f"  {i+1}. {flow}" for i, flow in enumerate(page_analysis.user_flows)])
            else:
                user_flows_text = "  1. 暂无识别的用户流程"

            # 格式化测试场景
            test_scenarios_text = ""
            if page_analysis.test_scenarios:
                test_scenarios_text = "\n".join([f"  - {scenario}" for scenario in page_analysis.test_scenarios])
            else:
                test_scenarios_text = "  - 暂无识别的测试场景"

            # 格式化测试步骤
            test_steps_text = ""
            if page_analysis.test_steps:
                test_steps_text = "\n".join([
                    f"  {step.step_number}. {step.action} - {step.target}: {step.description}"
                    for step in page_analysis.test_steps
                ])
            else:
                test_steps_text = "  1. 暂无具体测试步骤"

            # 构建完整的增强摘要
            summary = f"""
## 页面基本信息
- **页面标题**: {page_analysis.page_title or '未识别'}
- **页面类型**: {page_analysis.page_type}
- **置信度分数**: {page_analysis.confidence_score:.2f}
- **用户测试需求**: {page_analysis.main_content}

## 页面分析结果

### 识别的UI元素:
{ui_elements_text}

### 用户交互流程:
{user_flows_text}

### 测试场景:
{test_scenarios_text}

### 分析总结:
{page_analysis.analysis_summary}

## MidScene.js + Playwright代码生成指导

基于以上页面分析结果和用户测试需求，请重点关注：

1. **用户需求理解**:
   - 主要内容描述了用户的具体测试需求和步骤
   - 需要将用户的自然语言描述转换为MidScene.js的AI操作

2. **UI元素精确定位**:
   - 利用识别的UI元素进行精确的视觉描述
   - 结合元素的功能和位置特征进行MidScene.js操作设计

3. **流程化测试设计**:
   - 参考用户流程和测试步骤的序列进行代码组织
   - 确保每个步骤都有对应的MidScene.js操作和验证

4. **MidScene.js最佳实践**:
   - 优先使用ai()进行复合操作
   - 使用详细的视觉描述而非技术选择器
   - 为数据查询提供准确的TypeScript类型定义

5. **测试完整性**:
   - 包含适当的等待和验证操作
   - 添加必要的断言确保测试可靠性
   - 考虑异常情况的处理
"""
            return summary

        except Exception as e:
            logger.error(f"准备分析摘要失败: {str(e)}")
            return "分析摘要生成失败"

    async def _process_generated_playwright(self, playwright_content: str, message: WebMultimodalAnalysisResponse) -> Dict[str, Any]:
        """处理生成的Playwright代码内容"""
        try:
            # 解析TextMessage内容
            if playwright_content:
                try:
                    text_message_data = json.loads(playwright_content)
                    actual_content = text_message_data.get("content", playwright_content)
                except json.JSONDecodeError:
                    actual_content = playwright_content
            else:
                actual_content = ""

            # 提取TypeScript代码块
            import re
            code_blocks = re.findall(r'```(?:typescript|ts)\n(.*?)\n```', actual_content, re.DOTALL)

            test_code = {}
            if code_blocks:
                # 第一个代码块通常是主测试文件
                test_code["test_content"] = code_blocks[0]

                # 如果有多个代码块，可能包含fixture等
                if len(code_blocks) > 1:
                    test_code["fixture_content"] = code_blocks[1]
            else:
                # 如果没有代码块，直接使用内容
                test_code["test_content"] = actual_content

            # 补充默认内容
            if "fixture_content" not in test_code:
                test_code["fixture_content"] = self._get_default_fixture()
            if "config_content" not in test_code:
                test_code["config_content"] = self._get_default_config()
            if "package_json" not in test_code:
                test_code["package_json"] = self._get_default_package_json()

            return {
                "test_code": test_code,
                "playwright_content": actual_content,
                "generation_time": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"处理生成的Playwright代码失败: {str(e)}")
            return {
                "test_code": {
                    "test_content": playwright_content,
                    "fixture_content": self._get_default_fixture(),
                    "config_content": self._get_default_config(),
                    "package_json": self._get_default_package_json()
                },
                "playwright_content": playwright_content,
                "generation_time": datetime.now().isoformat()
            }

    async def _save_playwright_files(self, test_code: Dict[str, str], analysis_id: str) -> Dict[str, str]:
        """保存生成的Playwright文件"""
        try:
            from app.core.config import settings
            # 创建输出目录
            output_dir = Path(settings.MIDSCENE_SCRIPT_PATH)
            output_dir.mkdir(parents=True, exist_ok=True)

            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # project_name = f"test_{analysis_id}_{timestamp}"
            project_dir = output_dir    # / project_name
            project_dir.mkdir(exist_ok=True)

            # 创建e2e目录
            e2e_dir = project_dir / "e2e"
            e2e_dir.mkdir(exist_ok=True)

            file_paths = {}

            # 保存测试文件
            if test_code.get("test_content"):
                test_file = e2e_dir / f"test_{timestamp}.spec.ts"
                with open(test_file, "w", encoding="utf-8") as f:
                    f.write(test_code["test_content"])
                file_paths["test_file"] = str(test_file)

            # ------------- 以下内容已经生成，暂时不需要，所以注释掉 -----------

            # # 保存fixture文件
            # if test_code.get("fixture_content"):
            #     fixture_file = e2e_dir / "fixture.ts"
            #     with open(fixture_file, "w", encoding="utf-8") as f:
            #         f.write(test_code["fixture_content"])
            #     file_paths["fixture_file"] = str(fixture_file)
            #
            # # 保存配置文件
            # if test_code.get("config_content"):
            #     config_file = project_dir / "playwright.config.ts"
            #     with open(config_file, "w", encoding="utf-8") as f:
            #         f.write(test_code["config_content"])
            #     file_paths["config_file"] = str(config_file)
            #
            # # 保存package.json
            # if test_code.get("package_json"):
            #     package_file = project_dir / "package.json"
            #     with open(package_file, "w", encoding="utf-8") as f:
            #         f.write(test_code["package_json"])
            #     file_paths["package_file"] = str(package_file)

            # ------------- 以上内容已经生成，暂时不需要，所以注释掉 -----------

            logger.info(f"Playwright项目文件已保存到: {project_dir}")
            return file_paths

        except Exception as e:
            logger.error(f"保存生成文件失败: {str(e)}")
            return {}

    def _get_default_fixture(self) -> str:
        """获取默认的fixture内容"""
        return """import { test as base } from '@playwright/test';
import type { PlayWrightAiFixtureType } from '@midscene/web/playwright';
import { PlaywrightAiFixture } from '@midscene/web/playwright';

export const test = base.extend<PlayWrightAiFixtureType>(PlaywrightAiFixture({
  waitForNetworkIdleTimeout: 2000,
}));

export { expect } from '@playwright/test';
"""

    def _get_default_config(self) -> str:
        """获取默认的配置内容"""
        return """import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 90 * 1000,
  use: {
    headless: false,
    viewport: { width: 1280, height: 960 },
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  reporter: [
    ['list'],
    ['@midscene/web/playwright-report', { type: 'merged' }]
  ],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
"""

    def _get_default_package_json(self) -> str:
        """获取默认的package.json内容"""
        return """{
  "name": "midscene-playwright-test",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "test:debug": "playwright test --debug"
  },
  "devDependencies": {
    "@playwright/test": "^1.40.0",
    "@midscene/web": "latest",
    "typescript": "^5.0.0"
  }
}
"""

    def _generate_readme(self, project_name: str) -> str:
        """生成README文件"""
        try:
            readme_content = f"""# {project_name}

## 项目描述
这是一个基于MidScene.js + Playwright的自动化测试项目，使用AI驱动的UI自动化测试。

## 安装和运行

### 1. 安装依赖
```bash
npm install
```

### 2. 配置AI模型
设置环境变量（根据你使用的AI模型）：
```bash
# OpenAI
export OPENAI_API_KEY="your-api-key"

# 或其他模型配置
```

### 3. 运行测试
```bash
# 无头模式运行
npx playwright test

# 有头模式运行
npx playwright test --headed

# 调试模式运行
npx playwright test --debug
```

### 4. 查看测试报告
测试完成后，会在控制台输出报告文件路径，通过浏览器打开即可查看详细报告。

## 项目结构
```
{project_name}/
├── package.json          # 项目依赖配置
├── playwright.config.ts  # Playwright配置
├── e2e/
│   ├── fixture.ts        # MidScene.js fixture
│   └── test.spec.ts      # 测试用例
└── README.md            # 项目说明
```

## 技术栈
- **Playwright**: 浏览器自动化框架
- **MidScene.js**: AI驱动的UI自动化测试工具
- **TypeScript**: 类型安全的JavaScript

## 注意事项
1. 确保目标网站可访问
2. 根据实际情况调整元素描述
3. 测试前请检查网络连接和AI模型配置
4. 建议在稳定的环境中运行测试

## 生成信息
- **生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **官方文档**: https://midscenejs.com/zh/integrate-with-playwright.html
"""

            return readme_content

        except Exception as e:
            logger.error(f"生成README失败: {str(e)}")
            return f"# {project_name}\n\n自动生成的Playwright测试项目"

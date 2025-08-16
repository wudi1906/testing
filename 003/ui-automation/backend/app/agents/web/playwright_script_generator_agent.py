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
            model_client_type="auto",
            task_type="playwright_generation",  # 指定任务类型为Playwright代码生成，自动选择DeepSeek
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

## MidScene.js + Playwright 集成规范（基于官方文档v2024）

### 核心概念
MidScene.js是基于AI的UI自动化测试框架，与Playwright完美集成：
- 官方文档: https://midscenejs.com/zh/integrate-with-playwright.html
- 核心优势: 无需传统选择器，使用AI理解页面内容和自然语言描述
- 适用场景: Web应用端到端测试，支持复杂UI交互

### 标准fixture.ts（官方推荐）
```typescript
import { test as base } from "@playwright/test";
import type { PlayWrightAiFixtureType } from "@midscene/web/playwright";
import { PlaywrightAiFixture } from "@midscene/web/playwright";
import 'dotenv/config';

export const test = base.extend<PlayWrightAiFixtureType>(PlaywrightAiFixture({
  waitForNetworkIdleTimeout: 2000, // 交互过程中等待网络空闲的超时时间
}));
```

### MidScene.js API 完整指南（基于官方最新文档）

#### 1. 交互方法 - 自动规划 vs 即时操作

**自动规划（Auto Planning）**：
- `ai()` / `aiAction()` - AI自动规划操作步骤并执行，适合复合操作
- 更智能，但可能较慢，效果依赖AI模型质量

**即时操作（Instant Action）**：
- `aiTap()`, `aiInput()`, `aiHover()`, `aiKeyboardPress()`, `aiScroll()`, `aiRightClick()`
- 直接执行指定操作，AI只负责元素定位，更快更可靠
- 当完全确定操作类型时推荐使用

#### 2. 基础交互操作
```typescript
// ai/aiAction - 自动规划复合操作
await ai('type "Headphones" in search box, hit Enter');
await aiAction('click the blue login button in top right corner');

// aiTap - 点击操作（即时操作，推荐优先使用）
await aiTap('搜索按钮');
await aiTap('页面顶部的登录按钮', { deepThink: true }); // 使用深度思考精确定位

// aiInput - 输入操作（即时操作，推荐优先使用）
await aiInput('Headphones', '搜索框');
await aiInput('', '用户名输入框'); // 空字符串清空输入框

// aiHover - 悬停操作（仅Web可用）
await aiHover('导航菜单');

// aiKeyboardPress - 键盘操作
await aiKeyboardPress('Enter', '搜索框');
await aiKeyboardPress('Tab'); // 不指定元素时在当前焦点元素操作

// aiScroll - 滚动操作
await aiScroll({ direction: 'down', scrollType: 'once', distance: 100 }, '表单区域');
await aiScroll({ direction: 'down', scrollType: 'untilBottom' }, '搜索结果列表');

// aiRightClick - 右键点击（仅Web可用）
await aiRightClick('页面顶部的文件名称');
```

#### 3. 数据提取方法
```typescript
// aiAsk - 自由问答（特别好用，可结合业务场景生成真实数据）
const isLoggedIn = await aiAsk('登录成功了吗？成功返回true，失败返回false');
const businessData = await aiAsk('根据当前页面的业务场景，生成3个真实的用户测试数据');
const testScenarios = await aiAsk('基于当前电商页面，推荐5个核心的测试场景');
const userPersona = await aiAsk('为当前应用生成一个典型用户画像，包括姓名、年龄、职业等信息');

// aiQuery - 结构化数据查询（核心方法）
const items = await aiQuery<Array<{itemTitle: string, price: number}>>(
  '{itemTitle: string, price: Number}[], find item in list and corresponding price'
);

// 便捷查询方法
const price = await aiNumber('What is the price of the first headphone?');
const isExpensive = await aiBoolean('Is the price of the headphones more than 1000?');
const name = await aiString('What is the name of the first headphone?');

// aiLocate - 元素定位信息
const location = await aiLocate('页面顶部的登录按钮');
```

#### 4. 验证和等待
```typescript
// aiWaitFor - 等待条件（支持自定义超时和检查间隔）
await aiWaitFor('there is at least one headphone item on page');
await aiWaitFor('搜索结果列表已加载', { timeoutMs: 30000, checkIntervalMs: 5000 });

// aiAssert - 断言验证
await aiAssert('There is a category filter on the left');
await aiAssert('页面顶部显示用户头像和用户名');
```

#### 5. 高级功能选项
```typescript
// deepThink - 深度思考功能（精确定位小元素或难区分元素）, 适用于复杂UI,一般不推荐
await aiTap('页面顶部的登录按钮', { deepThink: true });
await aiHover('导航菜单', { deepThink: true });

// xpath - 结合传统选择器（可选）
await aiTap('登录按钮', { xpath: '//button[@id="login"]' });

// domIncluded - 提取不可见属性
const data = await aiQuery('用户信息', { domIncluded: true });
const linkUrl = await aiString('忘记密码链接地址', { domIncluded: true });

// cacheable - 缓存控制
await aiTap('搜索按钮', { cacheable: false }); // 不缓存此操作
```

### 官方示例代码模板（基于最新文档）
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
  aiTap,
  aiInput,
  aiQuery,
  aiAsk,
  aiAssert,
  aiWaitFor,
  aiNumber,
  aiBoolean,
  aiString,
  aiLocate,
}) => {
  // 🌟 使用aiAsk生成测试数据和策略
  const testStrategy = await aiAsk(`
    分析当前eBay页面，推荐最有效的商品搜索测试策略，
    包括搜索关键词建议和验证要点
  `);
  console.log("AI推荐的测试策略:", testStrategy);

  // 👀 推荐：使用即时操作进行精确控制
  await aiInput('Headphones', '搜索框');
  await aiTap('搜索按钮');

  // 👀 或者使用自动规划进行复合操作
  // await ai('type "Headphones" in search box, hit Enter');

  // 👀 等待加载完成
  await aiWaitFor("there is at least one headphone item on page");

  // 🌟 使用aiAsk进行业务场景分析
  const pageAnalysis = await aiAsk(`
    分析当前搜索结果页面的布局和功能，
    识别用户可能关注的关键信息和操作
  `);
  console.log("页面分析结果:", pageAnalysis);

  // 👀 查询商品信息（注意TypeScript类型和格式）
  const items = await aiQuery<Array<{itemTitle: string, price: number}>>(
    "{itemTitle: string, price: Number}[], find item in list and corresponding price"
  );

  // 🌟 使用aiAsk生成测试数据验证
  const dataValidation = await aiAsk(`
    基于查询到的商品数据，评估数据质量和完整性，
    并提出可能的测试验证点
  `);
  console.log("数据验证建议:", dataValidation);

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

## MidScene.js 最佳实践（基于官方最新指南）

### 1. API选择策略
- **即时操作优先**: 当明确知道操作类型时，优先使用 `aiTap()`, `aiInput()` 等
- **自动规划补充**: 对于复合操作或不确定具体步骤时，使用 `ai()` / `aiAction()`
- **深度思考**: 对于小元素或难以区分的元素，启用 `deepThink: true`

### 2. 元素描述优化
- ✅ 详细描述: "页面顶部右侧的蓝色登录按钮"
- ❌ 简单描述: "登录按钮"
- ✅ 位置信息: "左侧导航栏中的设置选项"
- ✅ 视觉特征: "带有搜索图标的输入框"
- ✅ 上下文信息: "用户信息卡片中的编辑按钮"

### 3. 数据查询格式规范
```typescript
// ✅ 正确格式 - 使用JSON Schema格式
const items = await aiQuery<Array<{itemTitle: string, price: number}>>(
  "{itemTitle: string, price: Number}[], find item in list and corresponding price"
);

// ✅ 复杂数据结构
const userData = await aiQuery({
  name: '用户姓名，string',
  profile: '用户资料，{age: number, location: string}',
  posts: '用户发布的帖子，{title: string, date: string}[]'
});

// ❌ 错误格式 - 模糊描述
const items = await aiQuery("获取商品列表");
```

### 4. aiAsk 业务场景应用策略（特别推荐）
`aiAsk` 是一个特别好用的方法，可以结合业务场景与大模型对话生成真实数据：

```typescript
// 🌟 生成测试数据
const testUsers = await aiAsk(`
  基于当前页面的业务场景，生成3个真实的用户测试数据，
  包括用户名、邮箱、手机号等信息，要求数据真实可用
`);

// 🌟 业务场景分析
const businessAnalysis = await aiAsk(`
  分析当前页面的业务流程，识别关键的用户操作路径，
  并推荐最重要的5个测试场景
`);

// 🌟 动态内容理解
const pageContext = await aiAsk(`
  描述当前页面的主要功能和用户目标，
  以及可能存在的异常情况和边界条件
`);

// 🌟 测试策略建议
const testStrategy = await aiAsk(`
  基于当前页面的复杂度和业务重要性，
  推荐合适的测试策略和优先级
`);

// 🌟 数据验证规则
const validationRules = await aiAsk(`
  根据页面上的表单字段，生成相应的数据验证规则，
  包括必填项、格式要求、长度限制等
`);
```

**aiAsk 最佳实践**：
- 提供详细的上下文描述，让AI更好理解业务场景
- 要求具体的输出格式，如"生成JSON格式的数据"
- 结合页面内容进行智能分析和建议
- 用于动态生成测试数据，避免硬编码
- 获取业务逻辑相关的测试建议

### 5. 等待和验证策略
- **智能等待**: 使用自然语言描述等待条件，而非固定时间
- **分层验证**: 结合 `aiAssert()` 和传统 `expect()` 断言
- **调试输出**: 添加 `console.log()` 输出关键信息便于调试

## 代码生成要求（基于官方最新规范）

### 1. **用户需求理解与API映射**
- **需求分析**: 深入分析main_content中用户的测试需求描述
- **操作分类**: 区分单一操作（使用即时操作API）和复合操作（使用自动规划API）
- **API选择策略**:
  - 明确的点击操作 → `aiTap()`
  - 明确的输入操作 → `aiInput()`
  - 复合操作序列 → `ai()` / `aiAction()`
  - 数据提取需求 → `aiQuery()`, `aiString()`, `aiNumber()`, `aiBoolean()`
  - 验证需求 → `aiAssert()` + `expect()`
  - 等待需求 → `aiWaitFor()`

### 2. **输出格式要求**
- 直接输出完整的TypeScript测试文件，不包装在JSON中
- 包含正确的import语句和fixture引用
- 确保代码可以直接运行，无需额外修改
- 添加清晰的中文注释说明用户需求对应关系

### 3. **代码结构设计**
```typescript
// 标准结构模板
import { expect } from "@playwright/test";
import { test } from "./fixture";

test.beforeEach(async ({ page }) => {
  page.setViewportSize({ width: 1280, height: 768 });
  await page.goto("目标URL");
  await page.waitForLoadState("networkidle");
});

test("测试用例名称", async ({
  ai, aiTap, aiInput, aiQuery, aiAssert, aiWaitFor,
  aiNumber, aiBoolean, aiString, aiLocate, aiHover, aiScroll
}) => {
  // 测试步骤实现
});
```

### 4. **MidScene.js操作策略优化**
- **即时操作优先**: 当用户明确描述具体操作时，优先使用对应的即时操作API
- **自动规划补充**: 对于复杂的多步骤操作，使用 `ai()` 进行自然语言描述
- **深度思考应用**: 对于可能难以定位的元素，添加 `{ deepThink: true }` 选项
- **智能等待**: 在关键操作后添加 `aiWaitFor()` 确保页面状态正确
- **分层验证**: 结合AI断言和传统断言提高测试可靠性
- **aiAsk业务增强**: 积极使用 `aiAsk()` 生成测试数据、分析业务场景、获取测试建议

### 5. **元素描述优化策略**
- **详细位置描述**: "页面顶部右侧的蓝色登录按钮"
- **视觉特征描述**: "带有搜索图标的输入框"
- **功能性描述**: "用户信息卡片中的编辑按钮"
- **上下文描述**: "导航栏下方的搜索结果列表"
- **避免技术术语**: 使用自然语言而非CSS选择器或XPath

### 6. **数据查询和验证规范**
```typescript
// 🌟 aiAsk业务场景应用（特别推荐）
const testData = await aiAsk(`
  基于当前页面的表单字段，生成3组真实的测试数据，
  包括正常数据、边界数据和异常数据，格式为JSON 字符串
`);

const captcha = await aiAsk(`
  在界面上，有个验证码图片，告诉我上面的内容
`);

const businessInsights = await aiAsk(`
  分析当前页面的业务流程，识别关键的测试点，
  并推荐优先级最高的5个测试场景
`);

const validationRules = await aiAsk(`
  根据页面上的输入字段，生成相应的验证规则，
  包括数据类型、长度限制、格式要求等
`);

// ✅ 正确的数据查询格式
const items = await aiQuery<Array<{title: string, price: number}>>(
  "{title: string, price: Number}[], 商品列表中的标题和价格"
);

// ✅ 复杂数据结构查询
const pageData = await aiQuery({
  userInfo: '用户信息，{name: string, avatar: string}',
  menuItems: '菜单项列表，string[]',
  statistics: '统计数据，{views: number, likes: number}'
});

// ✅ 结合aiAsk的智能验证
const validationAdvice = await aiAsk(`
  基于查询到的数据：${JSON.stringify(items)}，
  评估数据质量并提出验证建议
`);

// ✅ 分层验证策略
await aiAssert('页面顶部显示用户头像和用户名');
expect(items.length).toBeGreaterThan(0);
console.log('查询到的商品数量:', items.length);
console.log('AI验证建议:', validationAdvice);
```

### 7. **测试可靠性和调试**
- **调试输出**: 添加 `console.log()` 输出关键信息和中间结果
- **错误处理**: 使用 `try-catch` 处理可能的异常情况
- **超时配置**: 为 `aiWaitFor()` 设置合理的超时时间
- **状态验证**: 在关键步骤后验证页面状态

### 8. **特别注意事项**
- **忠实用户意图**: 严格按照用户描述的测试步骤进行代码生成
- **API使用准确性**: 根据操作类型选择最合适的MidScene.js API
- **性能优化**: 优先使用即时操作API提高执行效率
- **可维护性**: 生成清晰、易读、易维护的测试代码
- **🌟 aiAsk优先使用**: 积极使用 `aiAsk()` 方法结合业务场景生成真实测试数据、获取测试建议、分析页面功能

### 9. **aiAsk方法应用场景（重点推荐）**
在生成测试代码时，特别注意以下aiAsk的应用场景：

1. **测试数据生成**: 根据页面表单生成真实的测试数据
2. **业务场景分析**: 分析页面功能和用户流程
3. **测试策略建议**: 获取针对性的测试建议和优先级
4. **数据验证规则**: 生成字段验证规则和边界条件
5. **异常场景识别**: 识别可能的异常情况和错误处理
6. **用户体验评估**: 从用户角度评估页面可用性

请根据页面分析结果和用户测试需求，严格按照MidScene.js官方API规范生成高质量的测试代码。
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
基于以下用户测试需求，生成标准的MidScene.js + Playwright测试代码：

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
- **复合操作优先使用ai()**: 对于复合操作，如"在搜索框输入关键词并点击搜索"
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
        """准备优化后的分析摘要，充分利用页面分析智能体的结构化输出和数据库页面元素信息"""
        try:
            page_analysis = message.page_analysis

            # 构建基础摘要
            summary = f"""
## 用户测试需求
{page_analysis.main_content}
"""

            # 如果有数据库页面元素信息，添加简化的元素指导
            if page_analysis.database_elements:
                summary += self._add_database_elements_info(page_analysis.database_elements)

            summary += f"""
## MidScene.js + Playwright代码生成指导

基于以上用户需求、精确分析并确定用户需求中涉及的页面元素，请重点关注：

1. **精确元素定位**:
   - 优先使用数据库中提供的元素描述和选择器信息
   - 结合元素的位置、视觉特征和功能进行MidScene.js操作设计
   - 对于高置信度元素，直接使用其描述进行操作

2. **智能操作选择**:
   - 根据元素类型选择最合适的MidScene.js API
   - 对于button类型元素，优先使用aiTap()
   - 对于input类型元素，优先使用aiInput()
   - 对于复合操作，例如一句话对应多个操作，使用ai()进行自然语言描述

3. **测试优先级**:
   - 优先测试数据库中标记为高优先级的元素
   - 对于可测试性强的元素，确保包含相应的测试步骤
   - 为低置信度元素添加额外的等待和错误处理

4. **选择器策略**:
   - 当数据库提供了选择器时，可以结合传统选择器和AI描述
   - 使用AI描述作为主要定位方式，选择器作为备选方案
   - 确保生成的代码具有良好的可维护性

5. **测试完整性**:
   - 包含适当的等待和验证操作
   - 添加必要的断言确保测试可靠性
   - 考虑异常情况的处理
   - 为每个关键操作添加验证步骤
"""
            return summary

        except Exception as e:
            logger.error(f"准备分析摘要失败: {str(e)}")
            return "分析摘要生成失败"

    def _add_database_elements_info(self, database_elements: Dict[str, Any]) -> str:
        """添加数据库页面元素信息"""
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

            return info

        except Exception as e:
            logger.error(f"添加数据库元素信息失败: {str(e)}")
            return "\n## 页面元素信息获取失败\n\n"



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
        """保存生成的Playwright文件到工作空间和数据库存储目录"""
        try:
            from app.core.config import settings
            file_paths = {}

            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 1. 保存到PLAYWRIGHT工作空间（用于执行）
            workspace_dir = Path(settings.MIDSCENE_SCRIPT_PATH)
            workspace_dir.mkdir(parents=True, exist_ok=True)

            # 创建e2e目录
            e2e_dir = workspace_dir / "e2e"
            e2e_dir.mkdir(exist_ok=True)

            # 保存测试文件到工作空间
            if test_code.get("test_content"):
                workspace_test_file = e2e_dir / f"test_{timestamp}.spec.ts"
                with open(workspace_test_file, "w", encoding="utf-8") as f:
                    f.write(test_code["test_content"])
                file_paths["workspace_test_file"] = str(workspace_test_file)
                logger.info(f"Playwright脚本已保存到工作空间: {workspace_test_file}")

            # 2. 保存到数据库存储目录（用于管理）
            storage_dir = Path(settings.PLAYWRIGHT_OUTPUT_DIR)
            storage_dir.mkdir(parents=True, exist_ok=True)

            # 保存测试文件到存储目录
            if test_code.get("test_content"):
                storage_test_file = storage_dir / f"test_{timestamp}.spec.ts"
                with open(storage_test_file, "w", encoding="utf-8") as f:
                    f.write(test_code["test_content"])
                file_paths["test_file"] = str(storage_test_file)  # 数据库中记录的路径
                logger.info(f"Playwright脚本已保存到存储目录: {storage_test_file}")

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

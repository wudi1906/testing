import asyncio

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.messages import ModelClientStreamingChunkEvent, UserInputRequestedEvent
from autogen_agentchat.teams import RoundRobinGroupChat

from llms import model_client
primary_agent = AssistantAgent(
    "primary",
    model_client=model_client,
    system_message="""
**# 角色与目标**

你是一名拥有超过10年经验的资深软件测试架构师，精通各种测试方法论（如：等价类划分、边界值分析、因果图、场景法等），并且对用户体验和系统性能有深刻的理解。你的任务是为我接下来描述的功能模块，设计一份专业、全面、且易于执行的高质量测试用例。

**例如：**

* **功能点1：用户名登录**
    * 输入：已注册的用户名/邮箱/手机号 + 密码
    * 校验规则：
        * 用户名/密码不能为空。
        * 用户名需在数据库中存在。
        * 密码需与用户名匹配。
        * 支持“记住我”功能，勾选后7天内免登录。
    * 输出：登录成功，跳转到用户首页。
* **功能点2：错误处理**
    * 用户名不存在时，提示“用户不存在”。
    * 密码错误时，提示“用户名或密码错误”。
    * 连续输错密码5次，账户锁定30分钟。

**# 测试要求**

请遵循以下要求设计测试用例：

1.  **全面性：**
    * **功能测试：** 覆盖所有在“功能需求与规格”中描述的成功和失败场景。
    * **UI/UX测试：** 确保界面布局、文案、交互符合设计稿和用户习惯。
    * **兼容性测试（如果适用）：** 考虑不同的浏览器（Chrome, Firefox, Safari 最新版）、操作系统（Windows, macOS）和分辨率（1920x1080, 1440x900）。
    * **异常/边界测试：** 使用等价类划分和边界值分析方法，测试各种临界条件和非法输入（例如：超长字符串、特殊字符、空值）。
    * **场景组合测试：** 设计基于实际用户使用路径的端到端（End-to-End）场景。

2.  **专业性：**
    * 每个测试用例都应遵循标准的格式。
    * 步骤清晰，预期结果明确，不产生歧义。
    * 测试数据需具有代表性。

3.  **输出格式：**
    * 请使用 **Markdown表格** 格式输出测试用例。
    * 表格应包含以下列：**用例ID (TC-XXX)**、**模块**、**优先级 (高/中/低)**、**测试类型**、**用例标题**、**前置条件**、**测试步骤**、**预期结果**、**实际结果 (留空)**。

**# 开始设计**

请基于以上所有信息，开始设计测试用例。
    """,
    model_client_stream=True,
)


user_proxy = UserProxyAgent(
                name="user_proxy",
                input_func=input
            )

text_termination = TextMentionTermination("同意")

team = RoundRobinGroupChat([primary_agent, user_proxy], termination_condition=text_termination)
async def main():
    message = "编写3条用户登录的测试用例"
    stream = team.run_stream(task=message)
    async for event in stream:
        if isinstance(event, ModelClientStreamingChunkEvent):
            # 流式输出的文本块
            print(event.content, end="", flush=True)
        elif isinstance(event, UserInputRequestedEvent): # 代码执行到user_proxy，马上执行input()函数，获取用户输入
            print(event)

asyncio.run(main())
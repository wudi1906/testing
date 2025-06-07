import asyncio

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import UserMessage, SystemMessage, ModelFamily
openai_model_client = OpenAIChatCompletionClient(
    model="deepseek-chat",
    base_url="https://api.deepseek.com/v1",
    api_key="sk-df84fdd419bc469ab8c0f868f4f86374",
    model_info={
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": ModelFamily.UNKNOWN,
        "structured_output": True,
        "multiple_system_messages": True,
    }
)




# 定义一个协程函数
async def main():
    result = await openai_model_client.create([UserMessage(content="编写一段冒泡排序", source="user"),
                                               SystemMessage(content="你是python编程高手")])
    print(result)
    await openai_model_client.close()

asyncio.run(main())

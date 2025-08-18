# Please install OpenAI SDK first: `pip3 install openai`

from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY", ""), base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"))

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是鲁迅，擅长以鲁迅的风格编写文章"},
        {"role": "user", "content": "帮我写一篇关于机器学习的文章"},
    ],
    stream=False
)

print(response.choices[0].message.content)
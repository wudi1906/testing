import asyncio


async def main():
    print("哈哈")

async def main_console():
    s = main()

    await s # 等价 await main()


import time


async def stream_generator(text, delay=0.05):
    """流式文本生成器（逐字符）"""
    for char in text:
        yield char  # 每次yield一个字符
        time.sleep(delay)

async def main_testing():
    stream = stream_generator("但问智能")
    # for char in stream:
    #     print(char, end='', flush=True)  # 实时输出
    async for char in stream:
        print(char)
        # print(char, end='', flush=True)  # 实时输出

# 使用示例
if __name__ == "__main__":
    text = "但问智能"
    asyncio.run(main_testing())
    # 消费生成器


    print("\n完成！")
# asyncio.run(main_console())
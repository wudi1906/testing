import { test } from "./fixture";
import {expect} from "@playwright/test";

test.beforeEach(async ({ page }) => {
  page.setViewportSize({ width: 1280, height: 768 });
  await page.goto("http://bbs.huice.com");
  await page.waitForLoadState("networkidle");
});



test("登录功能", async ({
    ai,
    aiInput,
    aiAssert,
    aiTap,
    aiAsk
}) => {
        await aiInput("admin", "在用户名后面的输入框")
        await aiInput("admin", "在密码后面的输入框")
        await aiTap("登录")
        const result =await aiAsk("登录成功了吗？")
        console.log(result)

        // await aiAssert("在界面右上角会显示 `退出` 字样")

  // await ai("在用户名后面输入:admin，密码后面输入:admin，然后点击登录 按钮");
});


test("注册功能", async ({
    ai,
    aiInput,
    aiAssert,
    aiTap,
    aiAsk
}) => {
    await aiTap("立即注册")
    // await ai("分别在界面上输入合法的 用户名、密码、确认密码、邮箱")
    const data = await aiAsk("请给我生成如下合法的数据：用户名、密码、确认密码、邮箱，数据以英文逗号分割")
    await aiInput(data.split(",")[0], "在用户名后面的输入框")
    await aiInput(data.split(",")[1], "在密码后面的输入框")
    await aiInput(data.split(",")[2], "在确认密码后面的输入框")
    await aiInput(data.split(",")[3], "在邮箱后面的输入框")

    const code = await aiAsk("在界面上，有个验证码图片，告诉我上面的内容")
    await aiInput(code, "在验证码后面的输入框")
    await aiTap("提交")
    await aiAssert("界面有 感谢 字样")
    const success =  await aiAsk("注册成功了吗？如果成功回复 yes，失败回复 no")
    expect(success).toBe("yes")

    // await aiInput("admin", "在用户名后面的输入框")
    // await aiInput("admin123", "在密码后面的输入框")
    // await aiTap("登录")
    // const result =await aiAsk("登录成功了吗？")
    // console.log(result)

    // await aiAssert("在界面右上角会显示 `退出` 字样")

  // await ai("在用户名后面输入:admin，密码后面输入:admin，然后点击登录 按钮");
});


test("测试生成文件", async ({

    aiInput,
    aiAssert,
    aiTap,
    aiAsk,
}) => {
    const result =  await aiAsk("帮我生成一段js脚本功能如下：生成一个文件，文件名是:test.txt，文件内容是:hello world")
    console.log(result)
});


test("发帖测试", async ({
    ai,
    aiInput,
    aiAssert,
    aiTap,
    aiAsk,
    aiScroll
}) => {
    await aiInput("admin", "在用户名后面的输入框")
    await aiInput("admin", "在密码后面的输入框")
    await aiTap("登录")

    await aiTap("Locust链接")
    await aiTap("发帖")
    await ai("随机输入不超过80个字符的帖子主题和内容，内容长度超过30个字")

    // 如果不需要滚动，可以增加 page.setViewportSize({ width: 1280, height: 768 });中的 height
     await aiScroll(
    {
      direction: 'down',
      scrollType: 'untilBottom',
    },
  );
    await aiTap("左下角的发表帖子")
    await aiAssert("页面有新帖子出现")
});

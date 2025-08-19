import { expect } from "@playwright/test";
import { test } from "./fixture";

test.describe("问卷填写测试", () => {
  test.beforeEach(async ({ page }) => {
    page.setViewportSize({ width: 1280, height: 768 });
    await page.goto("https://www.wjx.cn/vm/w4e8hc9.aspx");
    await page.waitForLoadState("networkidle");
  });

  test("完整填写问卷并提交", async ({
    ai,
    aiTap,
    aiInput,
    aiWaitFor,
    aiAssert,
    aiScroll,
  }) => {
    // 检查是否有开始按钮
    try {
      await aiTap('"开始作答"或"开始填写"或"进入答题"按钮', { timeout: 5000 });
      await aiWaitFor("问卷题目区域加载完成");
    } catch (error) {
      console.log("未找到开始按钮，直接进入问卷");
    }

    // 1. 您的性别：选择"男"
    await aiTap('性别选择中的"男"选项');
    await aiTap('"下一题"或"继续"按钮');
    await aiWaitFor("下一页题目加载完成");

    // 2. 过去3个月是否网购：选择"是"
    await aiTap('网购问题中的"是"选项');
    await aiTap('"下一题"或"继续"按钮');
    await aiWaitFor("下一页题目加载完成");

    // 3. 主要原因【多选】：勾选"时尚有趣"、"实体店难以买到"
    await aiTap('多选题中的"时尚有趣"选项');
    await aiTap('多选题中的"实体店难以买到"选项');
    await aiTap('"下一题"或"继续"按钮');
    await aiWaitFor("下一页题目加载完成");

    // 4. 主要购买【多选】：勾选"电子产品"、"书籍"
    await aiScroll({ direction: 'down', distance: 200 }, '多选题区域');
    await aiTap('多选题中的"电子产品"选项');
    await aiTap('多选题中的"书籍"选项');
    await aiTap('"下一题"或"继续"按钮');
    await aiWaitFor("下一页题目加载完成");

    // 5. 网购频率：选择"每周１次"
    await aiTap('频率选择中的"每周１次"选项');
    await aiTap('"下一题"或"继续"按钮');
    await aiWaitFor("下一页题目加载完成");

    // 6. 月均花费：选择"３０１－５００元"
    await aiTap('花费选择中的"３０１－５００元"选项');
    await aiTap('"下一题"或"继续"按钮');
    await aiWaitFor("下一页题目加载完成");

    // 7. 喜欢的促销【多选】：勾选"打折"、"赠送优惠券"
    await aiScroll({ direction: 'down', distance: 200 }, '多选题区域');
    await aiTap('多选题中的"打折"选项');
    await aiTap('多选题中的"赠送优惠券"选项');
    await aiTap('"下一题"或"继续"按钮');
    await aiWaitFor("下一页题目加载完成");

    // 8. 对网络支付态度：选择"比较放心"
    await aiTap('支付态度中的"比较放心"选项');
    await aiTap('"下一题"或"继续"按钮');
    await aiWaitFor("下一页题目加载完成");

    // 9. 最长送达可接受：选择"４－５天"
    await aiTap('送达时间中的"４－５天"选项');
    await aiTap('"下一题"或"继续"按钮');
    await aiWaitFor("下一页题目加载完成");

    // 10. 最担心因素：选择"图片和实物有差距"
    await aiTap('担心因素中的"图片和实物有差距"选项');
    await aiTap('"下一题"或"继续"按钮');
    await aiWaitFor("下一页题目加载完成");

    // 11. 总体满意度：选择"比较满意"
    await aiTap('满意度中的"比较满意"选项');
    await aiTap('"下一题"或"继续"按钮');
    await aiWaitFor("下一页题目加载完成");

    // 12. 意见建议（≤50字）：输入"题目清晰，建议增加隐私提示与进度显示，移动端更友好。"
    await aiInput(
      "题目清晰，建议增加隐私提示与进度显示，移动端更友好。",
      "意见建议输入框"
    );
    await aiTap('"下一题"或"继续"按钮');
    await aiWaitFor("下一页题目加载完成");

    // 13. 网购最担心的是什么：选择"被盗刷账户"
    await aiTap('最担心问题中的"被盗刷账户"选项');
    await aiScroll({ direction: 'down', scrollType: 'untilBottom' }, '问卷页面');
    
    // 提交问卷
    await aiTap('页面底部的"提交"按钮');
    await aiWaitFor('"提交成功"或"感谢参与"提示出现', { timeoutMs: 30000 });

    // 验证提交成功
    await aiAssert("问卷提交成功提示已显示");
    const isSuccess = await aiAsk('当前页面是否显示"提交成功"或"感谢参与"字样？');
    expect(isSuccess.toLowerCase()).toContain('true');
  });
});
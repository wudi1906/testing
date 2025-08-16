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
    aiScroll
  }) => {
    // 检查并点击开始作答按钮（如果有）
    try {
      await aiTap('开始作答按钮', { timeout: 5000 });
      await aiWaitFor('问卷题目已加载');
    } catch (e) {
      console.log('没有找到开始作答按钮，直接进入问卷');
    }

    // 1. 您的性别：选择"男"
    await aiTap('性别选择中的"男"选项');
    await aiTap('下一题按钮');
    await aiWaitFor('第二题已加载');

    // 2. 过去3个月是否网购：选择"是"
    await aiTap('网购选择中的"是"选项');
    await aiTap('下一题按钮');
    await aiWaitFor('第三题已加载');

    // 3. 主要原因【多选】：勾选"时尚有趣"、"实体店难以买到"
    await aiTap('多选题中的"时尚有趣"选项');
    await aiTap('多选题中的"实体店难以买到"选项');
    await aiTap('下一题按钮');
    await aiWaitFor('第四题已加载');

    // 4. 主要购买【多选】：勾选"电子产品"、"书籍"
    await aiScroll({ direction: 'down', distance: 200 }, '多选题区域');
    await aiTap('多选题中的"电子产品"选项');
    await aiTap('多选题中的"书籍"选项');
    await aiTap('下一题按钮');
    await aiWaitFor('第五题已加载');

    // 5. 网购频率：选择"每周１次"
    await aiTap('频率选择中的"每周１次"选项');
    await aiTap('下一题按钮');
    await aiWaitFor('第六题已加载');

    // 6. 月均花费：选择"３０１－５００元"
    await aiTap('花费选择中的"３０１－５００元"选项');
    await aiTap('下一题按钮');
    await aiWaitFor('第七题已加载');

    // 7. 喜欢的促销【多选】：勾选"打折"、"赠送优惠券"
    await aiScroll({ direction: 'down', distance: 200 }, '多选题区域');
    await aiTap('促销多选题中的"打折"选项');
    await aiTap('促销多选题中的"赠送优惠券"选项');
    await aiTap('下一题按钮');
    await aiWaitFor('第八题已加载');

    // 8. 对网络支付态度：选择"比较放心"
    await aiTap('支付态度选择中的"比较放心"选项');
    await aiTap('下一题按钮');
    await aiWaitFor('第九题已加载');

    // 9. 最长送达可接受：选择"４－５天"
    await aiTap('送达时间选择中的"４－５天"选项');
    await aiTap('下一题按钮');
    await aiWaitFor('第十题已加载');

    // 10. 最担心因素：选择"图片和实物有差距"
    await aiTap('担心因素选择中的"图片和实物有差距"选项');
    await aiTap('下一题按钮');
    await aiWaitFor('第十一题已加载');

    // 11. 总体满意度：选择"比较满意"
    await aiTap('满意度选择中的"比较满意"选项');
    await aiTap('下一题按钮');
    await aiWaitFor('第十二题已加载');

    // 12. 意见建议（≤50字）：输入建议
    await aiInput(
      '题目清晰，建议增加隐私提示与进度显示，移动端更友好。',
      '意见建议输入框'
    );
    await aiTap('下一题按钮');
    await aiWaitFor('第十三题已加载');

    // 13. 网购最担心的是什么：选择"被盗刷账户"
    await aiTap('最担心问题选择中的"被盗刷账户"选项');

    // 提交问卷
    await aiScroll({ direction: 'down', scrollType: 'untilBottom' });
    await aiTap('页面底部的"提交"按钮');
    
    // 验证提交结果
    await aiWaitFor('"提交成功"或"感谢参与"提示出现', { timeout: 30000 });
    await aiAssert('页面显示问卷提交成功的提示信息');

    console.log('问卷填写测试完成');
  });
});
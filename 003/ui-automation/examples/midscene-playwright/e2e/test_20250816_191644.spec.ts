import { expect } from "@playwright/test";
import { test } from "./fixture";

test.beforeEach(async ({ page }) => {
  page.setViewportSize({ width: 1280, height: 768 });
  await page.goto("https://www.wjx.cn/vm/w4e8hc9.aspx");
  await page.waitForLoadState("networkidle");
});

test("问卷填写测试：网购行为调查", async ({
  ai,
  aiTap,
  aiInput,
  aiAssert,
  aiWaitFor,
  aiScroll
}) => {
  // 1. 检查并点击开始作答按钮（如果有）
  try {
    await aiTap('开始作答按钮', { timeoutMs: 5000 });
    await aiWaitFor('问卷题目已加载', { timeoutMs: 10000 });
  } catch {
    console.log('未找到开始作答按钮，直接进入问卷');
  }

  // 2. 性别选择
  await aiTap('性别选择中的"男"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('"过去3个月是否网购"问题已显示');

  // 3. 过去3个月是否网购
  await aiTap('"是"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('"主要原因"多选题已显示');

  // 4. 主要原因多选题
  await aiTap('"时尚有趣"选项');
  await aiTap('"实体店难以买到"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('"主要购买"多选题已显示');

  // 5. 主要购买多选题
  await aiScroll({ direction: 'down', distance: 200 }, '选项区域');
  await aiTap('"电子产品"选项');
  await aiTap('"书籍"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('"网购频率"问题已显示');

  // 6. 网购频率
  await aiTap('"每周１次"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('"月均花费"问题已显示');

  // 7. 月均花费
  await aiTap('"３０１－５００元"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('"喜欢的促销"多选题已显示');

  // 8. 喜欢的促销多选题
  await aiScroll({ direction: 'down', distance: 200 }, '选项区域');
  await aiTap('"打折"选项');
  await aiTap('"赠送优惠券"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('"对网络支付态度"问题已显示');

  // 9. 对网络支付态度
  await aiTap('"比较放心"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('"最长送达可接受"问题已显示');

  // 10. 最长送达可接受
  await aiTap('"４－５天"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('"最担心因素"问题已显示');

  // 11. 最担心因素
  await aiTap('"图片和实物有差距"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('"总体满意度"问题已显示');

  // 12. 总体满意度
  await aiTap('"比较满意"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('"意见建议"输入框已显示');

  // 13. 意见建议
  await aiInput('题目清晰，建议增加隐私提示与进度显示，移动端更友好。', '意见建议输入框');
  await aiTap('下一题按钮');
  await aiWaitFor('"网购最担心的是什么"问题已显示');

  // 14. 网购最担心的是什么
  await aiTap('"被盗刷账户"选项');
  
  // 提交问卷
  await aiScroll({ direction: 'down', scrollType: 'untilBottom' });
  await aiTap('提交按钮');
  
  // 验证提交结果
  await aiWaitFor('"提交成功"或"感谢参与"提示出现', { timeoutMs: 30000 });
  await aiAssert('页面显示提交成功或感谢参与的提示信息');
  
  console.log('问卷提交测试完成');
});
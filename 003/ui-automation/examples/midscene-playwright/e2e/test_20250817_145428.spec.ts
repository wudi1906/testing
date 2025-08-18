import { expect } from "@playwright/test";
import { test } from "./fixture";

test.beforeEach(async ({ page }) => {
  page.setViewportSize({ width: 1280, height: 768 });
  await page.goto("https://www.wjx.cn/vm/w4e8hc9.aspx");
  await page.waitForLoadState("networkidle");
});

test("完整填写问卷并提交", async ({
  ai,
  aiTap,
  aiInput,
  aiAssert,
  aiWaitFor,
  aiScroll
}) => {
  // 检查并点击开始作答按钮（如果有）
  try {
    await aiTap('开始作答按钮', { timeoutMs: 3000 });
    await aiWaitFor('问卷题目已加载');
  } catch {
    console.log('未找到开始作答按钮，直接进入问卷');
  }

  // 1. 您的性别：选择"男"
  await aiTap('性别选择中的"男"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('题目已切换');

  // 2. 过去3个月是否网购：选择"是"
  await aiTap('网购选择中的"是"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('题目已切换');

  // 3. 主要原因【多选】：勾选"时尚有趣"、"实体店难以买到"
  await aiTap('多选题中的"时尚有趣"选项');
  await aiTap('多选题中的"实体店难以买到"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('题目已切换');

  // 4. 主要购买【多选】：勾选"电子产品"、"书籍"
  await aiTap('多选题中的"电子产品"选项');
  await aiTap('多选题中的"书籍"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('题目已切换');

  // 5. 网购频率：选择"每周１次"
  await aiTap('频率选择中的"每周１次"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('题目已切换');

  // 6. 月均花费：选择"３０１－５００元"
  await aiTap('花费选择中的"３０１－５００元"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('题目已切换');

  // 7. 喜欢的促销【多选】：勾选"打折"、"赠送优惠券"
  await aiTap('多选题中的"打折"选项');
  await aiTap('多选题中的"赠送优惠券"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('题目已切换');

  // 8. 对网络支付态度：选择"比较放心"
  await aiTap('态度选择中的"比较放心"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('题目已切换');

  // 9. 最长送达可接受：选择"４－５天"
  await aiTap('送达时间选择中的"４－５天"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('题目已切换');

  // 10. 最担心因素：选择"图片和实物有差距"
  await aiTap('担心因素选择中的"图片和实物有差距"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('题目已切换');

  // 11. 总体满意度：选择"比较满意"
  await aiTap('满意度选择中的"比较满意"选项');
  await aiTap('下一题按钮');
  await aiWaitFor('题目已切换');

  // 12. 意见建议（≤50字）：输入指定内容
  await aiInput('题目清晰，建议增加隐私提示与进度显示，移动端更友好。', '意见建议输入框');
  await aiTap('下一题按钮');
  await aiWaitFor('题目已切换');

  // 13. 网购最担心的是什么：选择"被盗刷账户"
  await aiTap('最担心选择中的"被盗刷账户"选项');
  
  // 滚动到底部并提交
  await aiScroll({ direction: 'down', scrollType: 'untilBottom' });
  await aiTap('页面底部的"提交"按钮');
  
  // 验证提交结果
  await aiWaitFor('"提交成功"或"感谢参与"提示出现', { timeoutMs: 15000 });
  await aiAssert('页面显示提交成功的提示信息');
  
  console.log('问卷提交测试完成');
});
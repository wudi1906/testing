import { expect } from "@playwright/test";
import { test } from "./fixture";

test.beforeEach(async ({ page }) => {
  page.setViewportSize({ width: 1280, height: 768 });
  await page.goto("https://www.wjx.cn/vm/w4e8hc9.aspx");
  await page.waitForLoadState("networkidle");
});

test("问卷填写测试 - 网购行为调研", async ({
  ai,
  aiTap,
  aiInput,
  aiAssert,
  aiWaitFor,
  aiScroll
}) => {
  // 1. 检查并点击开始作答按钮（如果有）
  await aiWaitFor('页面加载完成');
  try {
    await aiTap('"开始作答"或"开始填写"按钮');
    await aiWaitFor('问卷题目区域出现');
  } catch (e) {
    // 若不存在开始按钮，直接进入问卷
  }

  // 2. 性别选择
  await aiTap('性别选择中的"男"选项');
  await aiWaitFor('下一题按钮可点击');

  // 3. 过去3个月是否网购
  await aiTap('"是"选项，关于过去3个月是否网购的问题');
  await aiWaitFor('下一题按钮可点击');

  // 4. 网购主要原因（多选题）
  await aiScroll({ direction: 'down', distance: 200 }, '多选题区域');
  await aiTap('"时尚有趣"选项');
  await aiTap('"实体店难以买到"选项');
  await aiWaitFor('下一题按钮可点击');

  // 5. 主要购买商品（多选题）
  await aiScroll({ direction: 'down', distance: 200 }, '多选题区域');
  await aiTap('"电子产品"选项');
  await aiTap('"书籍"选项');
  await aiWaitFor('下一题按钮可点击');

  // 6. 网购频率
  await aiScroll({ direction: 'down', distance: 200 }, '单选题区域');
  await aiTap('"每周１次"选项');
  await aiWaitFor('下一题按钮可点击');

  // 7. 月均花费
  await aiScroll({ direction: 'down', distance: 200 }, '单选题区域');
  await aiTap('"３０１－５００元"选项');
  await aiWaitFor('下一题按钮可点击');

  // 8. 喜欢的促销方式（多选题）
  await aiScroll({ direction: 'down', distance: 200 }, '多选题区域');
  await aiTap('"打折"选项');
  await aiTap('"赠送优惠券"选项');
  await aiWaitFor('下一题按钮可点击');

  // 9. 对网络支付态度
  await aiScroll({ direction: 'down', distance: 200 }, '单选题区域');
  await aiTap('"比较放心"选项');
  await aiWaitFor('下一题按钮可点击');

  // 10. 最长送达可接受时间
  await aiScroll({ direction: 'down', distance: 200 }, '单选题区域');
  await aiTap('"４－５天"选项');
  await aiWaitFor('下一题按钮可点击');

  // 11. 最担心因素
  await aiScroll({ direction: 'down', distance: 200 }, '单选题区域');
  await aiTap('"图片和实物有差距"选项');
  await aiWaitFor('下一题按钮可点击');

  // 12. 总体满意度
  await aiScroll({ direction: 'down', distance: 200 }, '单选题区域');
  await aiTap('"比较满意"选项');
  await aiWaitFor('下一题按钮可点击');

  // 13. 意见建议
  await aiScroll({ direction: 'down', distance: 200 }, '文本输入区域');
  await aiInput(
    '题目清晰，建议增加隐私提示与进度显示，移动端更友好。',
    '意见建议输入框'
  );
  await aiWaitFor('下一题按钮可点击');

  // 14. 网购最担心的问题
  await aiScroll({ direction: 'down', distance: 200 }, '单选题区域');
  await aiTap('"被盗刷账户"选项');
  await aiWaitFor('提交按钮可点击');

  // 15. 提交问卷
  await aiScroll({ direction: 'down', scrollType: 'untilBottom' });
  await aiTap('"提交"按钮');
  
  // 16. 验证提交结果
  await aiWaitFor('"提交成功"或"感谢参与"提示出现', { timeoutMs: 30000 });
  await aiAssert('页面显示问卷提交成功的提示信息');

  // 17. 输出测试完成信息
  console.log('问卷填写测试顺利完成');
});
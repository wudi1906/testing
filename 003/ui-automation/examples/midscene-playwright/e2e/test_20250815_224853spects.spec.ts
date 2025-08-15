import { expect } from "@playwright/test";
import { test } from "./fixture";

test.beforeEach(async ({ page }) => {
  page.setViewportSize({ width: 1280, height: 768 });
  await page.goto("https://www.wjx.cn/vm/w4e8hc9.aspx");
  await page.waitForLoadState("networkidle");
});

test("问卷填写测试 - 网购行为调查", async ({
  ai,
  aiTap,
  aiInput,
  aiWaitFor,
  aiAssert,
  aiScroll,
  aiAsk
}) => {
  // 检查并点击开始作答按钮（如果有）
  await aiWaitFor('页面加载完成');
  const startButton = await aiAsk('当前页面是否有"开始作答"、"开始填写"或"进入答题"按钮？');
  if (startButton.includes('有')) {
    await aiTap('开始作答/开始填写/进入答题按钮');
    await aiWaitFor('问卷题目区域出现', { timeoutMs: 10000 });
  }

  // 1. 您的性别：选择"男"
  await aiTap('性别选择中的"男"选项');
  await aiWaitFor('下一题按钮可点击');

  // 2. 过去3个月是否网购：选择"是"
  await aiTap('"过去3个月是否网购"问题中的"是"选项');
  await aiWaitFor('下一题按钮可点击');

  // 3. 主要原因【多选】：勾选"时尚有趣"、"实体店难以买到"
  await aiScroll({ direction: 'down', distance: 200 });
  await aiTap('"主要原因"多选题中的"时尚有趣"选项');
  await aiTap('"主要原因"多选题中的"实体店难以买到"选项');
  await aiWaitFor('下一题按钮可点击');

  // 4. 主要购买【多选】：勾选"电子产品"、"书籍"
  await aiScroll({ direction: 'down', distance: 200 });
  await aiTap('"主要购买"多选题中的"电子产品"选项');
  await aiTap('"主要购买"多选题中的"书籍"选项');
  await aiWaitFor('下一题按钮可点击');

  // 5. 网购频率：选择"每周１次"
  await aiTap('"网购频率"问题中的"每周１次"选项');
  await aiWaitFor('下一题按钮可点击');

  // 6. 月均花费：选择"３０１－５００元"
  await aiTap('"月均花费"问题中的"３０１－５００元"选项');
  await aiWaitFor('下一题按钮可点击');

  // 7. 喜欢的促销【多选】：勾选"打折"、"赠送优惠券"
  await aiScroll({ direction: 'down', distance: 200 });
  await aiTap('"喜欢的促销"多选题中的"打折"选项');
  await aiTap('"喜欢的促销"多选题中的"赠送优惠券"选项');
  await aiWaitFor('下一题按钮可点击');

  // 8. 对网络支付态度：选择"比较放心"
  await aiTap('"对网络支付态度"问题中的"比较放心"选项');
  await aiWaitFor('下一题按钮可点击');

  // 9. 最长送达可接受：选择"４－５天"
  await aiTap('"最长送达可接受"问题中的"４－５天"选项');
  await aiWaitFor('下一题按钮可点击');

  // 10. 最担心因素：选择"图片和实物有差距"
  await aiTap('"最担心因素"问题中的"图片和实物有差距"选项');
  await aiWaitFor('下一题按钮可点击');

  // 11. 总体满意度：选择"比较满意"
  await aiTap('"总体满意度"问题中的"比较满意"选项');
  await aiWaitFor('下一题按钮可点击');

  // 12. 意见建议（≤50字）：输入"题目清晰，建议增加隐私提示与进度显示，移动端更友好。"
  await aiInput('题目清晰，建议增加隐私提示与进度显示，移动端更友好。', '意见建议输入框');
  await aiWaitFor('下一题按钮可点击');

  // 13. 网购最担心的是什么：选择"被盗刷账户"
  await aiTap('"网购最担心的是什么"问题中的"被盗刷账户"选项');
  await aiWaitFor('提交按钮可点击');

  // 提交问卷
  await aiScroll({ direction: 'down', scrollType: 'untilBottom' });
  await aiTap('页面底部的"提交"按钮');
  
  // 验证提交结果
  await aiWaitFor('"提交成功"或"感谢参与"提示出现', { timeoutMs: 15000 });
  await aiAssert('页面显示问卷提交成功的提示信息');

  // 获取提交结果分析
  const submissionResult = await aiAsk('分析当前页面显示的提交结果，确认是否成功提交');
  console.log('问卷提交结果分析:', submissionResult);
});
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
  aiQuery,
  aiAsk
}) => {
  // 检查是否需要点击开始作答按钮
  await aiWaitFor("页面加载完成，检查是否有开始作答按钮");
  const hasStartButton = await aiAsk('页面上是否有"开始作答"、"开始填写"或"进入答题"按钮？有则返回true，无则返回false');
  
  if (hasStartButton === 'true') {
    console.log("检测到开始作答按钮，点击进入");
    await aiTap('开始作答按钮');
    await page.waitForLoadState("networkidle");
  }

  // 1. 您的性别：选择"男"
  console.log("选择性别：男");
  await aiTap('性别选择中的"男"选项');
  await aiWaitFor("性别选择完成，等待下一题加载");
  await page.waitForLoadState("networkidle");

  // 2. 过去3个月是否网购：选择"是"
  console.log("选择过去3个月是否网购：是");
  await aiTap('网购选择中的"是"选项');
  await aiWaitFor("网购选择完成，等待下一题加载");
  await page.waitForLoadState("networkidle");

  // 3. 主要原因【多选】：勾选"时尚有趣"、"实体店难以买到"
  console.log("多选题：勾选主要原因 - 时尚有趣、实体店难以买到");
  await aiScroll({ direction: 'down', scrollType: 'once', distance: 200 }, '多选题区域');
  await aiTap('"时尚有趣"选项');
  await aiTap('"实体店难以买到"选项');
  await aiWaitFor("多选题选择完成，等待下一题按钮可用");
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 4. 主要购买【多选】：勾选"电子产品"、"书籍"
  console.log("多选题：勾选主要购买物品 - 电子产品、书籍");
  await aiScroll({ direction: 'down', scrollType: 'once', distance: 200 }, '购买物品多选题区域');
  await aiTap('"电子产品"选项');
  await aiTap('"书籍"选项');
  await aiWaitFor("多选题选择完成，等待下一题按钮可用");
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 5. 网购频率：选择"每周１次"
  console.log("选择网购频率：每周１次");
  await aiTap('网购频率中的"每周１次"选项');
  await aiWaitFor("频率选择完成，等待下一题加载");
  await page.waitForLoadState("networkidle");

  // 6. 月均花费：选择"３０１－５００元"
  console.log("选择月均花费：３０１－５００元");
  await aiTap('月均花费中的"３０１－５００元"选项');
  await aiWaitFor("花费选择完成，等待下一题加载");
  await page.waitForLoadState("networkidle");

  // 7. 喜欢的促销【多选】：勾选"打折"、"赠送优惠券"
  console.log("多选题：勾选喜欢的促销方式 - 打折、赠送优惠券");
  await aiScroll({ direction: 'down', scrollType: 'once', distance: 200 }, '促销方式多选题区域');
  await aiTap('"打折"选项');
  await aiTap('"赠送优惠券"选项');
  await aiWaitFor("多选题选择完成，等待下一题按钮可用");
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 8. 对网络支付态度：选择"比较放心"
  console.log("选择网络支付态度：比较放心");
  await aiTap('支付态度中的"比较放心"选项');
  await aiWaitFor("支付态度选择完成，等待下一题加载");
  await page.waitForLoadState("networkidle");

  // 9. 最长送达可接受：选择"４－５天"
  console.log("选择最长送达可接受时间：４－５天");
  await aiTap('送达时间中的"４－５天"选项');
  await aiWaitFor("送达时间选择完成，等待下一题加载");
  await page.waitForLoadState("networkidle");

  // 10. 最担心因素：选择"图片和实物有差距"
  console.log("选择最担心因素：图片和实物有差距");
  await aiTap('担心因素中的"图片和实物有差距"选项');
  await aiWaitFor("担心因素选择完成，等待下一题加载");
  await page.waitForLoadState("networkidle");

  // 11. 总体满意度：选择"比较满意"
  console.log("选择总体满意度：比较满意");
  await aiTap('满意度中的"比较满意"选项');
  await aiWaitFor("满意度选择完成，等待下一题加载");
  await page.waitForLoadState("networkidle");

  // 12. 意见建议（≤50字）：输入指定文本
  console.log("填写意见建议");
  await aiInput('题目清晰，建议增加隐私提示与进度显示，移动端更友好。', '意见建议输入框');
  await aiWaitFor("意见建议输入完成，等待下一题按钮可用");
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 13. 网购最担心的是什么：选择"被盗刷账户"
  console.log("选择网购最担心的问题：被盗刷账户");
  await aiTap('最担心问题中的"被盗刷账户"选项');
  await aiWaitFor("最后选择题完成，等待提交按钮可用");
  await page.waitForLoadState("networkidle");

  // 提交问卷
  console.log("滚动到底部并提交问卷");
  await aiScroll({ direction: 'down', scrollType: 'untilBottom' }, '问卷页面');
  await aiWaitFor('提交按钮可见且可点击');
  await aiTap('提交按钮');
  
  // 等待提交结果
  console.log("等待提交结果页面加载");
  await aiWaitFor('"提交成功"或"感谢参与"等结果提示出现', { timeoutMs: 30000, checkIntervalMs: 2000 });
  await page.waitForLoadState("networkidle");
  
  // 验证提交结果
  const submissionResult = await aiAsk('当前页面是否显示提交成功或感谢参与的信息？');
  console.log("提交结果验证:", submissionResult);
  
  await aiAssert('页面显示问卷提交成功的提示信息');
  console.log("问卷填写测试完成！");
});
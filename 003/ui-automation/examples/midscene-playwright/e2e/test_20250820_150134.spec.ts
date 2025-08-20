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
  aiWaitFor,
  aiAssert,
  aiScroll,
  aiQuery,
  aiAsk
}) => {
  console.log("开始问卷填写测试...");

  // 检查是否需要点击开始作答按钮
  try {
    await aiWaitFor('页面加载完成，检查是否有"开始作答"、"开始填写"或"进入答题"按钮', { timeoutMs: 5000 });
    const hasStartButton = await aiAsk('页面上是否有"开始作答"、"开始填写"或"进入答题"按钮？有的话返回true，没有返回false');
    
    if (hasStartButton.toLowerCase().includes('true')) {
      console.log("检测到开始作答按钮，点击进入...");
      await aiTap('开始作答按钮');
      await page.waitForLoadState("networkidle");
    }
  } catch (error) {
    console.log("未检测到开始作答按钮，直接进入问卷填写");
  }

  // 等待问卷表单加载完成
  await aiWaitFor('问卷题目加载完成，可以看到第一个问题', { timeoutMs: 10000 });

  // 1. 您的性别：选择"男"
  console.log("正在填写第1题：性别选择");
  await aiTap('性别选择中的"男"选项');
  await aiWaitFor('"下一题"或"继续"按钮出现', { timeoutMs: 5000 });
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 2. 过去3个月是否网购：选择"是"
  console.log("正在填写第2题：网购情况");
  await aiTap('过去3个月是否网购选择中的"是"选项');
  await aiWaitFor('"下一题"或"继续"按钮出现', { timeoutMs: 5000 });
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 3. 主要原因【多选】：勾选"时尚有趣"、"实体店难以买到"
  console.log("正在填写第3题：网购主要原因");
  await aiTap('网购主要原因中的"时尚有趣"复选框');
  await aiTap('网购主要原因中的"实体店难以买到"复选框');
  await aiWaitFor('"下一题"或"继续"按钮出现', { timeoutMs: 5000 });
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 4. 主要购买【多选】：勾选"电子产品"、"书籍"
  console.log("正在填写第4题：主要购买品类");
  await aiTap('主要购买品类中的"电子产品"复选框');
  await aiTap('主要购买品类中的"书籍"复选框');
  await aiWaitFor('"下一题"或"继续"按钮出现', { timeoutMs: 5000 });
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 5. 网购频率：选择"每周１次"
  console.log("正在填写第5题：网购频率");
  await aiTap('网购频率选择中的"每周１次"选项');
  await aiWaitFor('"下一题"或"继续"按钮出现', { timeoutMs: 5000 });
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 6. 月均花费：选择"３０１－５００元"
  console.log("正在填写第6题：月均花费");
  await aiTap('月均花费选择中的"３０１－５００元"选项');
  await aiWaitFor('"下一题"或"继续"按钮出现', { timeoutMs: 5000 });
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 7. 喜欢的促销【多选】：勾选"打折"、"赠送优惠券"
  console.log("正在填写第7题：喜欢的促销方式");
  await aiTap('喜欢的促销方式中的"打折"复选框');
  await aiTap('喜欢的促销方式中的"赠送优惠券"复选框');
  await aiWaitFor('"下一题"或"继续"按钮出现', { timeoutMs: 5000 });
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 8. 对网络支付态度：选择"比较放心"
  console.log("正在填写第8题：网络支付态度");
  await aiTap('网络支付态度选择中的"比较放心"选项');
  await aiWaitFor('"下一题"或"继续"按钮出现', { timeoutMs: 5000 });
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 9. 最长送达可接受：选择"４－５天"
  console.log("正在填写第9题：最长送达时间");
  await aiTap('最长送达时间选择中的"４－５天"选项');
  await aiWaitFor('"下一题"或"继续"按钮出现', { timeoutMs: 5000 });
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 10. 最担心因素：选择"图片和实物有差距"
  console.log("正在填写第10题：最担心因素");
  await aiTap('最担心因素选择中的"图片和实物有差距"选项');
  await aiWaitFor('"下一题"或"继续"按钮出现', { timeoutMs: 5000 });
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 11. 总体满意度：选择"比较满意"
  console.log("正在填写第11题：总体满意度");
  await aiTap('总体满意度选择中的"比较满意"选项');
  await aiWaitFor('"下一题"或"继续"按钮出现', { timeoutMs: 5000 });
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 12. 意见建议（≤50字）：输入指定文本
  console.log("正在填写第12题：意见建议");
  await aiInput('题目清晰，建议增加隐私提示与进度显示，移动端更友好。', '意见建议输入框');
  await aiWaitFor('"下一题"或"继续"按钮出现', { timeoutMs: 5000 });
  await aiTap('下一题按钮');
  await page.waitForLoadState("networkidle");

  // 13. 网购最担心的是什么：选择"被盗刷账户"
  console.log("正在填写第13题：网购最担心的问题");
  await aiTap('网购最担心问题选择中的"被盗刷账户"选项');
  await aiWaitFor('"提交"按钮出现', { timeoutMs: 5000 });

  // 滚动到底部并点击提交
  console.log("滚动到页面底部准备提交...");
  await aiScroll({ direction: 'down', scrollType: 'untilBottom' }, '问卷页面');
  await aiTap('页面底部的提交按钮');

  // 等待提交结果
  console.log("等待提交结果...");
  await aiWaitFor('提交成功页面加载，出现"提交成功"、"感谢参与"或类似提示', { timeoutMs: 15000 });

  // 验证提交结果
  const submissionResult = await aiAsk('当前页面是否显示提交成功或感谢参与的提示？');
  console.log("提交结果验证:", submissionResult);

  await aiAssert('页面显示提交成功或感谢参与的提示信息');
  
  console.log("问卷填写测试完成！");
});
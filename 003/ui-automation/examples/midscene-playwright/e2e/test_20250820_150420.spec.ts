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
  // 🌟 使用aiAsk分析问卷页面结构
  const pageAnalysis = await aiAsk(`
    分析当前问卷页面的布局和功能，
    识别开始按钮、题目区域、提交按钮等关键元素，
    并推荐填写策略
  `);
  console.log("页面分析结果:", pageAnalysis);

  // 检查并点击开始作答按钮（如果有）
  try {
    await aiWaitFor('页面加载完成，检查是否有"开始作答"、"开始填写"或"进入答题"按钮', { timeoutMs: 5000 });
    await aiTap('开始作答按钮');
    await aiWaitFor('题目区域出现', { timeoutMs: 10000 });
  } catch (error) {
    console.log('未找到开始按钮，直接进入答题环节');
  }

  // 1. 您的性别：选择"男"
  await aiTap('性别选择中的"男"选项');
  await aiTap('下一题或继续按钮');
  await aiWaitFor('第二题出现', { timeoutMs: 5000 });

  // 2. 过去3个月是否网购：选择"是"
  await aiTap('网购选择中的"是"选项');
  await aiTap('下一题或继续按钮');
  await aiWaitFor('第三题出现', { timeoutMs: 5000 });

  // 3. 主要原因【多选】：勾选"时尚有趣"、"实体店难以买到"
  await aiTap('多选题中的"时尚有趣"选项');
  await aiTap('多选题中的"实体店难以买到"选项');
  await aiTap('下一题或继续按钮');
  await aiWaitFor('第四题出现', { timeoutMs: 5000 });

  // 4. 主要购买【多选】：勾选"电子产品"、"书籍"
  await aiScroll({ direction: 'down', scrollType: 'once', distance: 200 }, '多选题区域');
  await aiTap('多选题中的"电子产品"选项');
  await aiTap('多选题中的"书籍"选项');
  await aiTap('下一题或继续按钮');
  await aiWaitFor('第五题出现', { timeoutMs: 5000 });

  // 5. 网购频率：选择"每周１次"
  await aiTap('频率选择中的"每周１次"选项');
  await aiTap('下一题或继续按钮');
  await aiWaitFor('第六题出现', { timeoutMs: 5000 });

  // 6. 月均花费：选择"３０１－５００元"
  await aiTap('花费选择中的"３０１－５００元"选项');
  await aiTap('下一题或继续按钮');
  await aiWaitFor('第七题出现', { timeoutMs: 5000 });

  // 7. 喜欢的促销【多选】：勾选"打折"、"赠送优惠券"
  await aiTap('促销选择中的"打折"选项');
  await aiTap('促销选择中的"赠送优惠券"选项');
  await aiTap('下一题或继续按钮');
  await aiWaitFor('第八题出现', { timeoutMs: 5000 });

  // 8. 对网络支付态度：选择"比较放心"
  await aiTap('支付态度选择中的"比较放心"选项');
  await aiTap('下一题或继续按钮');
  await aiWaitFor('第九题出现', { timeoutMs: 5000 });

  // 9. 最长送达可接受：选择"４－５天"
  await aiTap('送达时间选择中的"４－５天"选项');
  await aiTap('下一题或继续按钮');
  await aiWaitFor('第十题出现', { timeoutMs: 5000 });

  // 10. 最担心因素：选择"图片和实物有差距"
  await aiTap('担心因素选择中的"图片和实物有差距"选项');
  await aiTap('下一题或继续按钮');
  await aiWaitFor('第十一题出现', { timeoutMs: 5000 });

  // 11. 总体满意度：选择"比较满意"
  await aiTap('满意度选择中的"比较满意"选项');
  await aiTap('下一题或继续按钮');
  await aiWaitFor('第十二题出现', { timeoutMs: 5000 });

  // 12. 意见建议（≤50字）：输入指定内容
  await aiInput('题目清晰，建议增加隐私提示与进度显示，移动端更友好。', '意见建议输入框');
  await aiTap('下一题或继续按钮');
  await aiWaitFor('第十三题出现', { timeoutMs: 5000 });

  // 13. 网购最担心的是什么：选择"被盗刷账户"
  await aiTap('担心问题选择中的"被盗刷账户"选项');

  // 🌟 使用aiAsk验证填写完整性
  const completionCheck = await aiAsk(`
    检查当前问卷是否已完整填写所有题目，
    确认所有必填项都已作答，没有遗漏
  `);
  console.log("填写完整性检查:", completionCheck);

  // 滚动到底部并提交
  await aiScroll({ direction: 'down', scrollType: 'untilBottom' }, '问卷页面');
  await aiWaitFor('提交按钮出现在视野中', { timeoutMs: 5000 });
  await aiTap('页面底部的提交按钮');

  // 等待提交结果
  await aiWaitFor('提交成功或感谢参与的提示出现', { timeoutMs: 15000 });
  
  // 验证提交结果
  await aiAssert('页面显示"提交成功"或"感谢参与"的提示信息');
  
  // 🌟 使用aiQuery获取提交结果信息
  const resultInfo = await aiQuery<{status: string, message: string}>(`
    {status: string, message: string}, 获取提交结果的状态和信息
  `);
  console.log("提交结果:", resultInfo);

  // 最终验证
  expect(resultInfo?.status).toMatch(/成功|完成|感谢/i);
  console.log("问卷填写测试完成！");
});
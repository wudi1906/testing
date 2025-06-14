import { expect } from "@playwright/test";
import { test } from "./fixture";

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 768 });
  await page.goto("https://www.saucedemo.com");
  await page.waitForLoadState("networkidle");
});

test("标准用户登录成功流程", async ({
  ai,
  aiInput,
  aiTap,
  aiAssert,
  aiWaitFor
}) => {
  // 步骤1: 输入标准用户名
  await aiInput("standard_user", "页面中央偏上的白色矩形输入框，灰色边框，placeholder为'Username'");
  await aiAssert("输入框显示'standard_user'");

  // 步骤2: 输入密码
  await aiInput("secret_sauce", "Username输入框下方的白色矩形输入框，灰色边框，placeholder为'Password'");
  await aiAssert("密码输入框内容长度等于8个字符");

  // 步骤3: 点击登录按钮
  await aiTap("密码输入框下方的绿色矩形按钮，黑色文字'Login'，高度约40像素");
  await aiWaitFor("页面跳转至商品列表页");
  await aiAssert("当前URL包含'/inventory.html'");
  await aiAssert("页面标题为'Swag Labs'");
});

test("锁定用户登录失败验证", async ({
  ai,
  aiInput,
  aiTap,
  aiAssert
}) => {
  // 步骤1: 输入锁定用户名
  await aiInput("locked_out_user", "页面中央的Username输入框，白色背景，灰色1px边框，圆角半径约3px");
  await aiAssert("输入框显示'locked_out_user'");

  // 步骤2: 输入密码
  await aiInput("secret_sauce", "Password输入框，视觉特征与Username输入框相同，位于其正下方");
  await aiAssert("密码输入框非空");

  // 步骤3: 点击登录按钮并验证错误
  await aiTap("页面中央唯一的绿色按钮，hover状态颜色可能略微变深");
  await aiAssert("页面出现红色错误提示框，内容包含'locked out'");
});

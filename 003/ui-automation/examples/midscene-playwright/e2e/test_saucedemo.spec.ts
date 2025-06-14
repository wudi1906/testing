import { expect } from "@playwright/test";
import { test } from "./fixture";

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 768 });
  await page.goto("https://www.saucedemo.com");
  await page.waitForLoadState("networkidle");
});

test("标准用户登录成功流程", async ({
  ai,
}) => {
 await ai("输入正确的用户名和密码，然后点击登录，登录后将前3条商品加入购物车，验证右上角购物车中显示的数量是否是3");
});

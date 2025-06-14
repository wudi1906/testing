import { expect } from "@playwright/test";
import { test } from "./fixture";

test.beforeEach(async ({ page }) => {
  page.setViewportSize({ width: 1280, height: 768 });
  await page.goto("https://www.ebay.com");
  await page.waitForLoadState("networkidle");
});

test("search computer on eBay and verify left navigation", async ({
  ai,
  aiInput,
  aiTap,
  aiWaitFor,
  aiAssert,
  aiQuery
}) => {
  // Step 1: Input search term in the search box
  await aiInput('computer', 
    '页面顶部中央的白色矩形搜索框，内含灰色提示文字"Search for anything"，位于eBay logo右侧约100像素处，右侧紧邻"All Categories"下拉菜单');

  // Step 2: Click the search button
  await aiTap('搜索框右侧的蓝色"Search"按钮，圆角矩形设计，白色文字，位于"All Categories"下拉菜单右侧');

  // Step 3: Wait for results page to load
  await aiWaitFor('页面跳转至搜索结果页面，URL包含"computer"关键词');

  // Step 4: Verify left navigation appears
  await aiWaitFor('页面左侧约1/5宽度的垂直导航栏区域，白色背景，通常包含多个分类选项');

  // Step 5: Verify computer-related categories exist
  await aiAssert('左侧导航区域至少包含一个与计算机相关的分类（如"Computers/Tablets & Networking"）');

});

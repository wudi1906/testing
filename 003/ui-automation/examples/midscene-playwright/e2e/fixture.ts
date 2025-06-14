import { test as base } from '@playwright/test';
import type { PlayWrightAiFixtureType } from '@midscene/web/playwright';
import { PlaywrightAiFixture } from '@midscene/web/playwright';
// 实现对环境变量的读取
import 'dotenv/config';
export const test = base.extend<PlayWrightAiFixtureType>(PlaywrightAiFixture({
  waitForNetworkIdleTimeout: 200000,
}));

export { expect } from '@playwright/test';

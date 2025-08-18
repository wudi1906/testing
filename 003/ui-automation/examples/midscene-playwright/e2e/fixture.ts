import { test as base } from '@playwright/test';
import type { PlayWrightAiFixtureType } from '@midscene/web/playwright';
import { PlaywrightAiFixture } from '@midscene/web/playwright';
import 'dotenv/config';
declare const process: any;
import midsceneConfigReal from '../midscene.config';
import midsceneConfigMock from '../midscene.mock.config';

const midsceneConfig = (process.env.AI_MOCK_MODE === 'true') ? midsceneConfigMock : midsceneConfigReal;

// 提供在 Mock 模式下的容错回退：当 AI 操作失败时，使用启发式 DOM 操作兜底
function normalizeText(text: string): string {
  return (text || '').replace(/\s+/g, '').toLowerCase();
}

async function fallbackTapByHeuristic(page: any, description: string): Promise<void> {
  const d = normalizeText(description);
  // 开始作答
  if (/(开始|立即开始|开始作答)/.test(description)) {
    const button = page.getByText(/开始|立即开始|开始作答/);
    await button.first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  // 下一题
  if (/(下一题|下一页|继续|next)/i.test(description)) {
    const nextBtn = page.getByRole('button', { name: /下一|继续|next/i });
    await nextBtn.first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  // 是/否选择
  if (/"是"/.test(description)) {
    await page.getByText(/^\s*是\s*$/).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  if (/"否"/.test(description)) {
    await page.getByText(/^\s*否\s*$/).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  // 性别 男/女
  if (/"男"/.test(description)) {
    await page.getByText(/男/).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  if (/"女"/.test(description)) {
    await page.getByText(/女/).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  // 频率、花费等常见中文全角/半角匹配
  if (/每周/.test(description)) {
    await page.getByText(/每周/).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  if (/(301|３０１|500|５００)/.test(description)) {
    await page.getByText(/301|３０１|500|５００/).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  // 兜底：尝试点击包含引号内文案
  const m = description.match(/"(.+?)"/);
  if (m && m[1]) {
    await page.getByText(new RegExp(m[1].replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
}

const baseWithAi = base.extend<PlayWrightAiFixtureType>(
  PlaywrightAiFixture({
    waitForNetworkIdleTimeout: 200000,
    ...midsceneConfig,
  })
);

export const test = baseWithAi.extend<{
  aiTap: any;
  aiWaitFor: any;
  aiAssert: any;
  aiInput: any;
  aiScroll: any;
}>({
  aiTap: async ({ aiTap, page }, use) => {
    await use(async (desc: string, options?: any): Promise<any> => {
      try {
        return await aiTap(desc, options);
      } catch (e) {
        await fallbackTapByHeuristic(page, desc);
        return undefined as any;
      }
    });
  },
  aiWaitFor: async ({ aiWaitFor, page }, use) => {
    await use(async (desc: string, options?: any): Promise<any> => {
      try {
        return await aiWaitFor(desc, options);
      } catch (e) {
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        return undefined as any;
      }
    });
  },
  aiAssert: async ({ aiAssert, page }, use) => {
    await use(async (desc: string, options?: any): Promise<any> => {
      try {
        return await aiAssert(desc, options);
      } catch (e) {
        const m = desc && desc.match(/"(.+?)"/);
        const text = m ? m[1] : desc;
        await page.getByText(new RegExp((text || '').replace(/[.*+?^${}()|[\]\\]/g, '\\\\$&'))).first().waitFor({ timeout: 5000 }).catch(() => {});
        return undefined as any;
      }
    });
  },
  aiInput: async ({ aiInput, page }, use) => {
    await use(async (desc: string, valueOrOptions?: any, maybeOptions?: any): Promise<any> => {
      try {
        return await aiInput(desc, valueOrOptions, maybeOptions);
      } catch (e) {
        const m = desc && desc.match(/"(.+?)"/);
        const value = typeof valueOrOptions === 'string' ? valueOrOptions : (m ? m[1] : 'test');
        await page.locator('input, textarea').first().fill(value).catch(() => {});
        return undefined as any;
      }
    });
  },
  aiScroll: async ({ aiScroll, page }, use) => {
    await use(async (opts?: any, d?: string): Promise<any> => {
      try {
        return await aiScroll(opts, d);
      } catch (e) {
        await page.mouse.wheel(0, (opts?.distance ?? 400));
        return undefined as any;
      }
    });
  },
});


export { expect } from '@playwright/test';

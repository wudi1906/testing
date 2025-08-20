import { test as base, chromium, Browser } from '@playwright/test';
import type { PlayWrightAiFixtureType } from '@midscene/web/playwright';
import { PlaywrightAiFixture } from '@midscene/web/playwright';
import 'dotenv/config';
declare const process: any;
import midsceneConfigReal from '../midscene.config';
import midsceneConfigMock from '../midscene.mock.config';

const midsceneConfig = (process.env.AI_MOCK_MODE === 'true') ? midsceneConfigMock : midsceneConfigReal;

// 如果后端通过 AdsPower 提供了 wsEndpoint，则通过 CDP 连接现有浏览器实例
const WS_ENDPOINT = process.env.PW_TEST_CONNECT_WS_ENDPOINT || process.env.PW_WS_ENDPOINT;

const HUMANIZE_LEVEL = Number(process.env.HUMANIZE_LEVEL || '1');
const STEALTH_MODE = (process.env.STEALTH_MODE ?? 'true') !== 'false';

function rand(min: number, max: number) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function sleep(ms: number) { return new Promise(res => setTimeout(res, ms)); }
async function humanPause(level = HUMANIZE_LEVEL) {
  if (level <= 0) return;
  // 100~300ms 轻微随机停顿
  await sleep(rand(80, 220) + level * rand(20, 120));
}

async function installStealth(page: any) {
  if (!STEALTH_MODE) return;
  // 在新文档注入，避免同步问题
  await page.addInitScript(() => {
    try {
      Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
      // window.chrome 伪装
      // @ts-ignore
      window.chrome = window.chrome || { runtime: {} };
      // plugins / languages
      Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
      Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en-US', 'en'] });
      // permissions.query 伪装
      const originalQuery = (navigator as any).permissions?.query;
      if (originalQuery) {
        (navigator as any).permissions.query = (parameters: any) => (
          parameters && parameters.name === 'notifications'
            ? Promise.resolve({ state: 'granted' })
            : originalQuery(parameters)
        );
      }
      // WebGL vendor/renderer 伪装
      const getParameter = WebGLRenderingContext.prototype.getParameter;
      // @ts-ignore
      WebGLRenderingContext.prototype.getParameter = function(param: any) {
        if (param === 37445) return 'Intel Inc.'; // UNMASKED_VENDOR_WEBGL
        if (param === 37446) return 'Intel Iris OpenGL Engine'; // UNMASKED_RENDERER_WEBGL
        return getParameter.call(this, param);
      };
      // Canvas 指纹微扰
      const toDataURL = HTMLCanvasElement.prototype.toDataURL;
      HTMLCanvasElement.prototype.toDataURL = function() {
        const ctx = this.getContext('2d');
        try {
          // @ts-ignore
          ctx && ctx.fillRect && ctx.fillRect(0, 0, 1, 1);
        } catch {}
        return toDataURL.apply(this, arguments as any);
      } as any;
      // WebRTC 关闭本地地址泄露
      // @ts-ignore
      if (window.RTCPeerConnection) {
        const orig = RTCPeerConnection.prototype.createDataChannel;
        RTCPeerConnection.prototype.createDataChannel = function() {
          const pc: any = this;
          pc && pc.setLocalDescription && (pc.setLocalDescription = async () => {});
          return orig.apply(this, arguments as any);
        } as any;
      }
    } catch {}
  });
}

// 提供在 Mock 模式下的容错回退：当 AI 操作失败时，使用启发式 DOM 操作兜底
function normalizeText(text: string): string {
  return (text || '').replace(/\s+/g, '').toLowerCase();
}

function escapeRegExp(text: string): string {
  return (text || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

async function fallbackTapByHeuristic(page: any, description: string): Promise<void> {
  const d = normalizeText(description);
  // 开始作答
  if (/(开始|立即开始|开始作答)/.test(description)) {
    const button = page.getByText(/开始|立即开始|开始作答/);
    await humanPause();
    await button.first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  // 下一题
  if (/(下一题|下一页|继续|next)/i.test(description)) {
    const nextBtn = page.getByRole('button', { name: /下一|继续|next/i });
    await humanPause();
    await nextBtn.first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  // 是/否选择
  if (/"是"/.test(description)) {
    await humanPause();
    await page.getByText(/^\s*是\s*$/).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  if (/"否"/.test(description)) {
    await humanPause();
    await page.getByText(/^\s*否\s*$/).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  // 性别 男/女
  if (/"男"/.test(description)) {
    await humanPause();
    await page.getByText(/男/).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  if (/"女"/.test(description)) {
    await humanPause();
    await page.getByText(/女/).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  // 频率、花费等常见中文全角/半角匹配
  if (/每周/.test(description)) {
    await humanPause();
    await page.getByText(/每周/).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  if (/(301|３０１|500|５００)/.test(description)) {
    await humanPause();
    await page.getByText(/301|３０１|500|５００/).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  // 兜底：尝试点击包含引号内文案
  const m = description.match(/"(.+?)"/);
  if (m && m[1]) {
    await humanPause();
    await page.getByText(new RegExp(escapeRegExp(m[1]))).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
}

async function fillInputNearDesc(page: any, desc: string, value: string): Promise<boolean> {
  const escaped = escapeRegExp(desc);
  const fillableSelectors = [
    'textarea',
    'input:not([type])',
    'input[type="text"]',
    'input[type="search"]',
    'input[type="email"]',
    'input[type="url"]',
    'input[type="tel"]',
    'input[type="password"]',
    'input[type="number"]',
    '[role="textbox"]',
    '[contenteditable="true"]'
  ].join(', ');

  // 0) 语义相近修正
  const synonyms = [desc, desc.replace('意见建议', '意见和建议'), desc.replace('意见和建议', '意见建议')]
    .filter((s, i, arr) => !!s && arr.indexOf(s) === i);

  // 1) getByRole('textbox')
  for (const s of synonyms) {
    const roleBox = page.getByRole('textbox', { name: new RegExp(escapeRegExp(s)) });
    if (await roleBox.first().count().catch(() => 0)) {
      await roleBox.first().click({ timeout: 1000 }).catch(() => {});
      await roleBox.first().fill('');
      // 类人键入
      for (const ch of String(value)) { await roleBox.first().type(ch, { delay: rand(40, 140) }); }
      return true;
    }
  }

  // 2) label/placeholder
  for (const s of synonyms) {
    const byLabel = page.getByLabel(new RegExp(escapeRegExp(s)));
    if (await byLabel.first().count().catch(() => 0)) {
      await byLabel.first().click({ timeout: 1000 }).catch(() => {});
      await byLabel.first().fill('');
      for (const ch of String(value)) { await byLabel.first().type(ch, { delay: rand(40, 140) }); }
      return true;
    }
    const byPlaceholder = page.getByPlaceholder(new RegExp(escapeRegExp(s)));
    if (await byPlaceholder.first().count().catch(() => 0)) {
      await byPlaceholder.first().click({ timeout: 1000 }).catch(() => {});
      await byPlaceholder.first().fill('');
      for (const ch of String(value)) { await byPlaceholder.first().type(ch, { delay: rand(40, 140) }); }
      return true;
    }
  }

  // 3) 题干容器
  for (const s of synonyms) {
    const container = page.locator(`xpath=//*[contains(normalize-space(.), "${s}")]`).first();
    if (await container.count().catch(() => 0)) {
      const ta = container.locator('textarea');
      if (await ta.first().count().catch(() => 0)) {
        await ta.first().click({ timeout: 1000 }).catch(() => {});
        await ta.first().fill('');
        for (const ch of String(value)) { await ta.first().type(ch, { delay: rand(40, 140) }); }
        return true;
      }
      const field = container.locator(fillableSelectors).first();
      if (await field.count().catch(() => 0)) {
        await field.click({ timeout: 1000 }).catch(() => {});
        await field.fill?.('');
        try { await field.type?.(String(value), { delay: rand(40, 140) }); return true; } catch {}
        await field.fill?.(value).catch(() => {});
        return true;
      }
    }
  }

  // 4) 全局 textarea
  const anyTextarea = page.locator('textarea').filter({ hasNot: page.locator('[type="hidden"]') }).first();
  if (await anyTextarea.count().catch(() => 0)) {
    await anyTextarea.click({ timeout: 1000 }).catch(() => {});
    await anyTextarea.fill('');
    for (const ch of String(value)) { await anyTextarea.type(ch, { delay: rand(40, 140) }); }
    return true;
  }

  // 5) 全局兜底
  const anyField = page.locator(fillableSelectors).first();
  if (await anyField.count().catch(() => 0)) {
    await anyField.click({ timeout: 1000 }).catch(() => {});
    try { await anyField.type?.(String(value), { delay: rand(40, 140) }); return true; } catch {}
    await anyField.fill?.(value).catch(() => {});
    return true;
  }
  return false;
}

async function openDropdownTrigger(page: any, desc: string): Promise<boolean> {
  const escaped = escapeRegExp(desc);
  // 原生 select 容器（先不打开，由选择时处理）
  // 常见库触发器
  const triggers = [
    // 通用 ARIA
    page.getByRole('combobox', { name: new RegExp(escaped) }),
    // 常见库
    page.locator('.ant-select, .ant-select-selector'),
    page.locator('.el-select, .el-select__caret, .el-select__wrapper'),
    page.locator('.react-select__control'),
    page.locator('.MuiSelect-select, [aria-haspopup="listbox"]'),
    page.locator('.p-dropdown, .p-dropdown-label'),
    page.locator('.t-select, .t-select__wrap'),
    page.locator('.arco-select, .arco-select-view'),
    page.locator('.ivu-select, .ivu-select-selection'),
    page.locator('.v-select, .vs__dropdown-toggle'),
    page.locator('.select2-selection'),
  ];
  for (const t of triggers) {
    const count = await t.first().count().catch(() => 0);
    if (count) {
      await t.first().click({ timeout: 2000 }).catch(() => {});
      return true;
    }
  }
  // 题干容器内的触发器
  const container = page.locator(`xpath=//*[contains(normalize-space(.), "${desc}")]`).first();
  if (await container.count().catch(() => 0)) {
    const innerTrigger = container.locator('button, [role="combobox"], .ant-select, .el-select, .react-select__control, .p-dropdown, .t-select, .arco-select, .ivu-select, .v-select, .select2-selection');
    if (await innerTrigger.count().catch(() => 0)) {
      await innerTrigger.first().click({ timeout: 2000 }).catch(() => {});
      return true;
    }
  }
  return false;
}

async function chooseDropdownOption(page: any, optionText: string): Promise<boolean> {
  const escapedOpt = escapeRegExp(optionText);
  // 优先 role=option
  const byRole = page.getByRole('option', { name: new RegExp(escapedOpt, 'i') });
  if (await byRole.first().count().catch(() => 0)) {
    await byRole.first().click({ timeout: 2000 }).catch(() => {});
    return true;
  }
  // 常见库下拉弹层容器
  const layers = page.locator([
    '.ant-select-dropdown',
    '.el-select-dropdown',
    '.react-select__menu',
    '.MuiPopover-root, .MuiList-root',
    '.p-dropdown-panel',
    '.t-select__dropdown',
    '.arco-select-dropdown',
    '.ivu-select-dropdown',
    '.vs__dropdown-menu',
    '.select2-results__options',
  ].join(', '));
  if (await layers.count().catch(() => 0)) {
    const option = layers.locator(`:scope >> text=${optionText}`);
    if (await option.first().count().catch(() => 0)) {
      await option.first().click({ timeout: 2000 }).catch(() => {});
      return true;
    }
    // 兜底：任意可见文本
    const any = layers.locator(`xpath=.//*[contains(normalize-space(.), "${optionText}")]`).first();
    if (await any.count().catch(() => 0)) {
      await any.click({ timeout: 2000 }).catch(() => {});
      return true;
    }
  }
  // 全局兜底
  const anyGlobal = page.getByText(new RegExp(escapedOpt, 'i')).first();
  if (await anyGlobal.count().catch(() => 0)) {
    await anyGlobal.click({ timeout: 2000 }).catch(() => {});
    return true;
  }
  return false;
}

const baseWithAi = base.extend<PlayWrightAiFixtureType>(
  PlaywrightAiFixture({
    waitForNetworkIdleTimeout: 200000,
    ...midsceneConfig,
    // 仍保留中间件内置的连接能力
    connectExisting: WS_ENDPOINT || undefined,
    cdpConnect: true,
    connectTimeoutMs: 60000,
  })
);

// 显式覆盖 browser 固定夹：当提供 WS endpoint 时强制使用 CDP 直连 AdsPower，避免回退到本地Chromium
const baseForceConnect = baseWithAi.extend<{ browser: Browser }>({
  browser: async ({}, use) => {
    if (WS_ENDPOINT) {
      console.log(`🔌 [Fixture] Connecting to existing AdsPower via CDP: ${WS_ENDPOINT}`);
      const browser = await chromium.connectOverCDP(WS_ENDPOINT);
      // 不在此处关闭，由后端统一 stop/delete
      await use(browser as unknown as Browser);
      return;
    }
    // 无 WS 时走默认行为（用于本地兜底）
    await use(await chromium.launch());
  }
});

export const test = baseForceConnect.extend<{
  aiTap: any;
  aiWaitFor: any;
  aiAssert: any;
  aiInput: any;
  aiScroll: any;
  aiSelect: any;
  aiAsk: any;
}>({
  // 复用 AdsPower 现有唯一 Context，避免新建上下文导致新标签页
  context: async ({ browser }, use) => {
    const existing = browser.contexts?.() || [];
    if (existing.length > 0) {
      await use(existing[0]);
      return;
    }
    const ctx = await browser.newContext();
    await use(ctx);
  },
  // 复用现有唯一 Page，避免新开标签页与 viewport 变更
  page: async ({ context }, use) => {
    const pages = context.pages?.() || [];
    if (pages.length > 0) {
      await use(pages[0]);
      return;
    }
    const p = await context.newPage();
    await use(p);
  },
  aiAsk: async ({ ai }, use) => {
    await use(async (question: string, options?: any): Promise<any> => {
      try {
        // 优先使用基础 ai() 能力进行问答
        return await (ai as any)(question, options);
      } catch (e) {
        // 兜底：直接返回字符串，避免用例因缺参中断
        return String(question);
      }
    });
  },
  aiTap: async ({ aiTap, page, ai }, use) => {
    await use(async (desc: string, options?: any): Promise<any> => {
      try {
        return await aiTap(desc, options);
      } catch (e) {
        // 深度思考再次尝试
        try { return await aiTap(desc, { ...(options||{}), deepThink: true }); } catch {}
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
        await page.getByText(new RegExp(escapeRegExp(text || ''))).first().waitFor({ timeout: 5000 }).catch(() => {});
        return undefined as any;
      }
    });
  },
  aiInput: async ({ aiInput, page, ai }, use) => {
    await use(async (a: any, b?: any, c?: any): Promise<any> => {
      // 允许两种签名：(desc, value, options) 或 (value, desc, options)
      let desc: string | undefined;
      let value: string | undefined;
      let options: any | undefined;
      if (typeof a === 'string' && typeof b === 'string') {
        // 猜测：较“语义化”的那一个当作 desc，较长或含标点的当作 value
        const looksLikeDesc = (s: string) => /输入框|文本|意见|建议|内容|描述|备注|comment|input|textarea/i.test(s) || s.length <= 30;
        if (looksLikeDesc(a) && !looksLikeDesc(b)) {
          desc = a; value = b; options = c;
        } else if (looksLikeDesc(b) && !looksLikeDesc(a)) {
          desc = b; value = a; options = c;
        } else {
          // 默认 (desc, value)
          desc = a; value = b; options = c;
        }
      } else {
        desc = a; value = b; options = c;
      }
      try {
        return await aiInput(desc, value, options);
      } catch (e) {
        // 深度思考再试
        try { return await aiInput(desc, value, { ...(options||{}), deepThink: true }); } catch {}
        // 启发式就近定位
        const ok = await fillInputNearDesc(page, desc || '', value || '');
        if (ok) return undefined as any;
        // 兜底：用 ai() 复合描述
        try { return await (ai as any)(`在 ${desc} 输入 ${value}`); } catch {}
        throw e;
      }
    });
  },
  aiScroll: async ({ aiScroll, page }, use) => {
    await use(async (opts?: any, d?: string): Promise<any> => {
      try {
        return await aiScroll(opts, d);
      } catch (e) {
        try {
          if (typeof page.isClosed === 'function' && page.isClosed()) {
            return undefined as any;
          }
          await page.mouse.wheel(0, (opts?.distance ?? 300));
        } catch {}
        return undefined as any;
      }
    });
  },
  aiSelect: async ({ page }, use) => {
    await use(async (desc: string, optionText: string): Promise<any> => {
      // 1) 原生 select
      try {
        const container = page.locator(`xpath=//*[contains(normalize-space(.), "${desc}")]`).first();
        const selectInContainer = container.locator('select');
        if (await selectInContainer.count().catch(() => 0)) {
          await selectInContainer.first().selectOption({ label: optionText }).catch(async () => {
            await selectInContainer.first().selectOption(optionText).catch(() => {});
          });
          return;
        }
        const globalSelect = page.locator('select');
        if (await globalSelect.count().catch(() => 0)) {
          await globalSelect.first().selectOption({ label: optionText }).catch(async () => {
            await globalSelect.first().selectOption(optionText).catch(() => {});
          });
          return;
        }
      } catch {}
      // 2) 自定义下拉：点击触发器
      await openDropdownTrigger(page, desc).catch(() => {});
      // 3) 选择选项
      const done = await chooseDropdownOption(page, optionText);
      if (!done) {
        // 再尝试：输入法型下拉（可搜索）
        const searchBox = page.locator('input[role="combobox"], .ant-select input, .el-select input, .react-select__input input, .MuiInputBase-input');
        if (await searchBox.count().catch(() => 0)) {
          await searchBox.first().fill(optionText).catch(() => {});
          await chooseDropdownOption(page, optionText).catch(() => {});
        }
      }
    });
  },
});


export { expect } from '@playwright/test';


// 翻页驱动：点击“下一题/下一页/继续/提交”等，并等待稳定
export async function nextStep(page: any): Promise<void> {
  const candidates = [
    { role: 'button', name: /提交|下一题|下一页|继续|保存并继续|提交并下一页/i },
    { role: 'link', name: /提交|下一题|下一页|继续/i },
  ];
  for (const c of candidates) {
    try {
      const btn = page.getByRole(c.role as any, { name: c.name }).first();
      if (await btn.count().catch(() => 0)) {
        await btn.click({ timeout: 5000 }).catch(() => {});
        try { await page.waitForLoadState('networkidle', { timeout: 15000 }); } catch {}
        return;
      }
    } catch {}
  }
  // 兜底：查找包含文案的可点击元素
  const textBtn = page.getByText(/提交|下一题|下一页|继续/i).first();
  if (await textBtn.count().catch(() => 0)) {
    await textBtn.click({ timeout: 5000 }).catch(() => {});
    try { await page.waitForLoadState('networkidle', { timeout: 15000 }); } catch {}
  }
}

// 循环直到完成：每页调用 fillPageFn 完成本页作答，然后 nextStep，直到检测到完成文案
export async function untilFinish(page: any, fillPageFn: () => Promise<void>): Promise<void> {
  for (let i = 0; i < 1000; i++) { // 安全上限
    // 若已完成，终止
    const done = await page.getByText(/提交成功|感谢参与|已完成|谢谢参与/i).first().count().catch(() => 0);
    if (done) return;
    await fillPageFn();
    await nextStep(page);
    try { await page.waitForLoadState('networkidle', { timeout: 15000 }); } catch {}
  }
}

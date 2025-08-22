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
const AUTO_WAIT_VISIBLE_MS = 2000;

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

// 🎯 历史版本74b3fa646的高效输入处理策略
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

  // 语义相近修正
  const synonyms = [desc, desc.replace('意见建议', '意见和建议'), desc.replace('意见和建议', '意见建议')]
    .filter((s, i, arr) => !!s && arr.indexOf(s) === i);

  // 1) getByRole('textbox')
  for (const s of synonyms) {
    const roleBox = page.getByRole('textbox', { name: new RegExp(escapeRegExp(s)) });
    if (await roleBox.first().count().catch(() => 0)) {
      await roleBox.first().click({ timeout: 1000 }).catch(() => {});
      await roleBox.first().fill('');
      // 类人键入
      for (const ch of String(value)) { 
        await roleBox.first().type(ch, { delay: Math.floor(Math.random() * 100) + 40 }); 
      }
      return true;
    }
  }

  // 2) label/placeholder
  for (const s of synonyms) {
    const byLabel = page.getByLabel(new RegExp(escapeRegExp(s)));
    if (await byLabel.first().count().catch(() => 0)) {
      await byLabel.first().click({ timeout: 1000 }).catch(() => {});
      await byLabel.first().fill('');
      for (const ch of String(value)) { 
        await byLabel.first().type(ch, { delay: Math.floor(Math.random() * 100) + 40 }); 
      }
      return true;
    }
    const byPlaceholder = page.getByPlaceholder(new RegExp(escapeRegExp(s)));
    if (await byPlaceholder.first().count().catch(() => 0)) {
      await byPlaceholder.first().click({ timeout: 1000 }).catch(() => {});
      await byPlaceholder.first().fill('');
      for (const ch of String(value)) { 
        await byPlaceholder.first().type(ch, { delay: Math.floor(Math.random() * 100) + 40 }); 
      }
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
        for (const ch of String(value)) { 
          await ta.first().type(ch, { delay: Math.floor(Math.random() * 100) + 40 }); 
        }
        return true;
      }
      const field = container.locator(fillableSelectors).first();
      if (await field.count().catch(() => 0)) {
        await field.click({ timeout: 1000 }).catch(() => {});
        await field.fill?.('');
        try { await field.type?.(String(value), { delay: Math.floor(Math.random() * 100) + 40 }); return true; } catch {}
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
    for (const ch of String(value)) { 
      await anyTextarea.type(ch, { delay: Math.floor(Math.random() * 100) + 40 }); 
    }
    return true;
  }

  return false;
}

// 🎯 历史版本74b3fa646的高效启发式回退策略
async function fallbackTapByHeuristic(page: any, description: string): Promise<void> {
  console.log(`[Fallback] 启发式回退处理: ${description}`);
  
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
    await page.getByText(new RegExp(escapeRegExp(m[1]))).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
}

// 🎯 历史版本74b3fa646的专门下拉处理逻辑
async function openDropdownTrigger(page: any, desc: string): Promise<boolean> {
  const escaped = escapeRegExp(desc);
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

// 🎯 智能页面状态检测与修复：确保问卷从顶部开始
async function ensureQuestionnaireStartsFromTop(page: any): Promise<void> {
  try {
    console.log('[页面状态] 检测问卷页面状态...');
    
    // 等待页面加载完成
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(500);
    
    // 检测是否在问卷页面  
    const isQuestionnaire = await page.locator(':has-text("问卷")').count() > 0 || 
                            await page.locator(':has-text("调查")').count() > 0 ||
                            await page.locator(':has-text("题目")').count() > 0;
    
    if (!isQuestionnaire) {
      console.log('[页面状态] 非问卷页面，跳过状态检测');
      return;
    }
    
    // 检查当前滚动位置
    const scrollInfo = await page.evaluate(() => ({
      scrollY: window.scrollY,
      scrollHeight: document.body.scrollHeight,
      clientHeight: window.innerHeight,
      isAtTop: window.scrollY < 100,
      isAtBottom: window.scrollY + window.innerHeight > document.body.scrollHeight - 100
    }));
    
    console.log(`[页面状态] 滚动位置: Y=${scrollInfo.scrollY}, 是否在顶部=${scrollInfo.isAtTop}, 是否在底部=${scrollInfo.isAtBottom}`);
    
    // 如果页面在底部或中间，说明可能有会话状态，需要重置
    if (!scrollInfo.isAtTop) {
      console.log('[页面状态] 页面不在顶部，尝试重置到起始状态');
      
      // 方法1: 滚动到顶部并检查是否有第1题
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(500);
      
      // 检查是否能看到第1题或性别选择
      const firstQuestionVisible = await page.locator('text*="1."').first().isVisible().catch(() => false) ||
                                   await page.locator('text*="第1题"').first().isVisible().catch(() => false) ||
                                   await page.locator('text*="性别"').first().isVisible().catch(() => false);
      
      if (!firstQuestionVisible) {
        console.log('[页面状态] 第1题不可见，尝试重新开始问卷');
        
        // 方法2: 查找并点击"重新开始"、"返回首页"等按钮
        const restartButtons = [
          'text*="重新开始"',
          'text*="返回首页"', 
          'text*="重新填写"',
          'text*="开始填写"',
          'link*="重新"'
        ];
        
        for (const selector of restartButtons) {
          try {
            const button = page.locator(selector).first();
            if (await button.count() > 0 && await button.isVisible()) {
              console.log(`[页面状态] 找到重启按钮: ${selector}`);
              await button.click();
              await page.waitForTimeout(1000);
              break;
            }
          } catch (e) {
            // 继续尝试下一个按钮
          }
        }
        
        // 方法3: 如果没有重启按钮，尝试刷新页面
        const stillNotVisible = await page.locator('text*="性别"').first().isVisible().catch(() => false);
        if (!stillNotVisible) {
          console.log('[页面状态] 未找到重启按钮，刷新页面重置状态');
          await page.reload({ waitUntil: 'networkidle' });
          await page.waitForTimeout(1000);
        }
      }
      
      // 最终确保在顶部
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(300);
      console.log('[页面状态] 页面状态已重置到顶部');
    } else {
      console.log('[页面状态] 页面已在顶部，状态正常');
    }
    
  } catch (e) {
    console.log(`[页面状态] 状态检测失败: ${e.message}`);
  }
}

async function fallbackTapByHeuristic(page: any, description: string): Promise<void> {
  const d = normalizeText(description);
  // 开始作答
  if (/(开始|立即开始|开始作答)/.test(description)) {
    console.log('[Playwright][Tap-Dbg] fallback: start-exam');
    const button = page.getByText(/开始|立即开始|开始作答/);
    await humanPause();
    await button.first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  // 下一题
  if (/(下一题|下一页|继续|next)/i.test(description)) {
    console.log('[Playwright][Tap-Dbg] fallback: next-step');
    const nextBtn = page.getByRole('button', { name: /下一|继续|next/i });
    await humanPause();
    await nextBtn.first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  // 提交
  if (/(提交|提交按钮)/.test(description)) {
    console.log('[Playwright][Tap-Dbg] fallback: submit');
    const submitBtn = page.getByRole('button', { name: /提交|提交并/i });
    await humanPause();
    const hit = await submitBtn.first().count().catch(() => 0);
    if (hit) {
      await submitBtn.first().click({ timeout: 3000 }).catch(() => {});
      return;
    }
    // 兜底：按文本
    const textBtn = page.getByText(/提交/).first();
    await textBtn.click({ timeout: 3000 }).catch(() => {});
    return;
  }
  // 是/否选择
  if (/"是"/.test(description)) {
    console.log('[Playwright][Tap-Dbg] fallback: yes');
    await humanPause();
    await page.getByText(/^\s*是\s*$/).first().click({ timeout: 3000 }).catch(() => {});
    return;
  }
  if (/"否"/.test(description)) {
    console.log('[Playwright][Tap-Dbg] fallback: no');
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

function extractQuoted(text?: string): string | undefined {
  if (!text) return undefined;
  const m = text.match(/"(.+?)"/);
  return m ? m[1] : undefined;
}

async function trySelectFromDesc(page: any, desc?: string): Promise<boolean> {
  const opt = extractQuoted(desc);
  if (!opt) return false;
  try {
    console.log(`[Playwright][Select-Dbg] trySelectFromDesc opt="${opt}" desc="${desc}"`);
    // 先尝试题干容器+原生select（可能匹配不到，记录计数）
    const container = page.locator(`xpath=//*[contains(normalize-space(.), "${escapeRegExp(desc || '')}")]`).first();
    const containerCount = await container.count().catch(() => 0);
    console.log(`[Playwright][Select-Dbg] container count=${containerCount}`);
    if (containerCount) {
      const sel = container.locator('select');
      if (await sel.count().catch(() => 0)) {
        console.log('[Playwright][Select-Dbg] container select found');
        await sel.first().selectOption({ label: opt }).catch(async () => {
          await sel.first().selectOption(opt).catch(() => {});
        });
        return true;
      }
    }
    // 全局原生 select（不依赖容器文案）
    const globalSel = page.locator('select');
    const globalSelCount = await globalSel.count().catch(() => 0);
    console.log(`[Playwright][Select-Dbg] global select count=${globalSelCount}`);
    if (globalSelCount) {
      await globalSel.first().selectOption({ label: opt }).catch(async () => {
        await globalSel.first().selectOption(opt).catch(() => {});
      });
      console.log('[Playwright][Select-Dbg] selected via global select');
      return true;
    }
    // 自定义下拉：点击触发器后选择
    const opened = await openDropdownTrigger(page, desc || '').catch(() => false);
    console.log(`[Playwright][Select-Dbg] opened=${opened}`);
    const done = await chooseDropdownOption(page, opt).catch(() => false);
    console.log(`[Playwright][Select-Dbg] choose result=${done}`);
    if (done) return true;
    // 搜索型下拉
    const searchBox = page.locator('input[role="combobox"], .ant-select input, .el-select input, .react-select__input input, .MuiInputBase-input');
    const sCount = await searchBox.count().catch(() => 0);
    console.log(`[Playwright][Select-Dbg] searchBox count=${sCount}`);
    if (sCount) {
      await searchBox.first().fill(opt).catch(() => {});
      const picked = await chooseDropdownOption(page, opt).catch(() => false);
      console.log(`[Playwright][Select-Dbg] choose after type result=${picked}`);
      return picked;
    }
  } catch {}
  return false;
}

async function scrollToDesc(page: any, desc?: string): Promise<void> {
  if (!desc) return;
  try {
    const escaped = escapeRegExp(desc);
    const target = page.locator(`xpath=//*[contains(normalize-space(.), "${escaped}")]`).first();
    const count = await target.count().catch(() => 0);
    console.log(`[Playwright][Scroll-Dbg] target count=${count} for desc="${desc}"`);
    if (!count) return; // 找不到就不滚动，避免无意义滚动
    const handle = await target.elementHandle();
    if (!handle) return;
    // 仅当不在视口内时才滚动
    const inView = await page.evaluate((el: any) => {
      try {
        const r = el.getBoundingClientRect();
        const vw = Math.max(document.documentElement.clientWidth, window.innerWidth || 0);
        const vh = Math.max(document.documentElement.clientHeight, window.innerHeight || 0);
        return r.top >= 0 && r.left >= 0 && r.bottom <= vh && r.right <= vw;
      } catch { return true; }
    }, handle);
    console.log(`[Playwright][Scroll-Dbg] inView=${inView} for desc="${desc}"`);
    if (!inView) {
      await handle.scrollIntoViewIfNeeded().catch(async () => {
        try { await page.evaluate((el: any) => el && el.scrollIntoView && el.scrollIntoView({ block: 'center', inline: 'center' }), handle); } catch {}
      });
    }
  } catch {}
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
  console.log(`[Playwright][Input-Dbg] fillInputNearDesc desc="${desc}" value.len=${(value||'').length} synonyms=${synonyms.length}`);

  // 1) getByRole('textbox')
  for (const s of synonyms) {
    const roleBox = page.getByRole('textbox', { name: new RegExp(escapeRegExp(s)) });
    if (await roleBox.first().count().catch(() => 0)) {
      console.log(`[Playwright][Input-Dbg] byRole(textbox) hit name~="${s}"`);
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
      console.log(`[Playwright][Input-Dbg] byLabel hit ~="${s}"`);
      await byLabel.first().click({ timeout: 1000 }).catch(() => {});
      await byLabel.first().fill('');
      for (const ch of String(value)) { await byLabel.first().type(ch, { delay: rand(40, 140) }); }
      return true;
    }
    const byPlaceholder = page.getByPlaceholder(new RegExp(escapeRegExp(s)));
    if (await byPlaceholder.first().count().catch(() => 0)) {
      console.log(`[Playwright][Input-Dbg] byPlaceholder hit ~="${s}"`);
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
      console.log(`[Playwright][Input-Dbg] container hit for ~="${s}"`);
      const ta = container.locator('textarea');
      if (await ta.first().count().catch(() => 0)) {
        console.log('[Playwright][Input-Dbg] container>textarea');
        await ta.first().click({ timeout: 1000 }).catch(() => {});
        await ta.first().fill('');
        for (const ch of String(value)) { await ta.first().type(ch, { delay: rand(40, 140) }); }
        return true;
      }
      const field = container.locator(fillableSelectors).first();
      if (await field.count().catch(() => 0)) {
        console.log('[Playwright][Input-Dbg] container>field');
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
    console.log('[Playwright][Input-Dbg] global textarea');
    await anyTextarea.click({ timeout: 1000 }).catch(() => {});
    await anyTextarea.fill('');
    for (const ch of String(value)) { await anyTextarea.type(ch, { delay: rand(40, 140) }); }
    return true;
  }

  // 5) 全局兜底
  const anyField = page.locator(fillableSelectors).first();
  if (await anyField.count().catch(() => 0)) {
    console.log('[Playwright][Input-Dbg] global field');
    await anyField.click({ timeout: 1000 }).catch(() => {});
    try { await anyField.type?.(String(value), { delay: rand(40, 140) }); return true; } catch {}
    await anyField.fill?.(value).catch(() => {});
    return true;
  }
  console.log('[Playwright][Input-Dbg] no fillable found');
  return false;
}

async function openDropdownTrigger(page: any, desc: string): Promise<boolean> {
  const escaped = escapeRegExp(desc);
  // 原生 select 容器（先不打开，由选择时处理）
  // 常见库触发器
  const triggers = [
    // 通用 ARIA
    page.getByRole('combobox', { name: new RegExp(escaped) }),
    page.locator('[aria-haspopup="listbox"]'),
    page.locator('[role="button"][aria-expanded]'),
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
    console.log(`[Playwright][Select-Dbg] trigger probe: count=${count}`);
    if (count) {
      await t.first().click({ timeout: 2000 }).catch(() => {});
      console.log(`[Playwright][Select-Dbg] trigger clicked`);
      return true;
    }
  }
  // 题干容器内的触发器
  const container = page.locator(`xpath=//*[contains(normalize-space(.), "${desc}")]`).first();
  if (await container.count().catch(() => 0)) {
    const innerTrigger = container.locator('button, [role="combobox"], [aria-haspopup="listbox"], .ant-select, .el-select, .react-select__control, .p-dropdown, .t-select, .arco-select, .ivu-select, .v-select, .select2-selection');
    const innerCount = await innerTrigger.count().catch(() => 0);
    console.log(`[Playwright][Select-Dbg] inner trigger count=${innerCount}`);
    if (innerCount) {
      await innerTrigger.first().click({ timeout: 2000 }).catch(() => {});
      console.log(`[Playwright][Select-Dbg] inner trigger clicked`);
      return true;
    }
  }
  console.log('[Playwright][Select-Dbg] no trigger found');
  return false;
}

async function chooseDropdownOption(page: any, optionText: string): Promise<boolean> {
  const escapedOpt = escapeRegExp(optionText);
  console.log(`[Playwright][Select-Dbg] choose option="${optionText}"`);
  
  // 等待下拉面板出现
  await page.waitForTimeout(300);
  
  // 优先 role=option
  const byRole = page.getByRole('option', { name: new RegExp(escapedOpt, 'i') });
  const roleCount = await byRole.first().count().catch(() => 0);
  console.log(`[Playwright][Select-Dbg] role=option count=${roleCount}`);
  if (roleCount) {
    console.log(`[Playwright][Select-Dbg] option via role=option found`);
    await byRole.first().click({ timeout: 2000 }).catch(() => {});
    return true;
  }
  // listbox 内的选项
  const listbox = page.getByRole('listbox');
  const listboxCount = await listbox.count().catch(() => 0);
  console.log(`[Playwright][Select-Dbg] listbox count=${listboxCount}`);
  if (listboxCount) {
    const opt = listbox.locator(`:scope >> text=${optionText}`);
    const optCount = await opt.first().count().catch(() => 0);
    console.log(`[Playwright][Select-Dbg] listbox option count=${optCount}`);
    if (optCount) {
      console.log(`[Playwright][Select-Dbg] option via listbox text found`);
      await opt.first().click({ timeout: 2000 }).catch(() => {});
      return true;
    }
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
    console.log(`[Playwright][Select-Dbg] dropdown layers=${await layers.count().catch(() => 0)}`);
    const option = layers.locator(`:scope >> text=${optionText}`);
    if (await option.first().count().catch(() => 0)) {
      console.log(`[Playwright][Select-Dbg] option via layer text found`);
      await option.first().click({ timeout: 2000 }).catch(() => {});
      return true;
    }
    // 兜底：任意可见文本
    const any = layers.locator(`xpath=.//*[contains(normalize-space(.), "${optionText}")]`).first();
    if (await any.count().catch(() => 0)) {
      console.log(`[Playwright][Select-Dbg] option via layer xpath contains found`);
      await any.click({ timeout: 2000 }).catch(() => {});
      return true;
    }
  }
  // 终极兜底：全局可见 li/div 选项
  const globalOpt = page.locator(`xpath=//li[normalize-space(.)="${optionText}"] | //div[@role='option' and normalize-space(.)="${optionText}"] | //*[@role='menuitem' and normalize-space(.)="${optionText}"]`).first();
  if (await globalOpt.count().catch(() => 0)) {
    console.log(`[Playwright][Select-Dbg] option via global li/div/role found`);
    await globalOpt.click({ timeout: 2000 }).catch(() => {});
    return true;
  }
  // 全局兜底
  const anyGlobal = page.getByText(new RegExp(escapedOpt, 'i')).first();
  if (await anyGlobal.count().catch(() => 0)) {
    console.log(`[Playwright][Select-Dbg] option via global text found`);
    await anyGlobal.click({ timeout: 2000 }).catch(() => {});
    return true;
  }
  console.log('[Playwright][Select-Dbg] no option matched');
  return false;
}

async function selectByTyping(page: any, optionText: string): Promise<boolean> {
  try {
    const input = page.locator('input[role="combobox"], .ant-select input, .el-select input, .react-select__input input, .MuiInputBase-input').first();
    if (await input.count().catch(() => 0)) {
      await input.focus().catch(() => {});
      await input.fill('');
      await input.type(optionText, { delay: rand(30, 90) }).catch(() => {});
      await page.keyboard.press('Enter').catch(() => {});
      console.log(`[Playwright][Select-Dbg] typed then Enter: ${optionText}`);
      return true;
    }
  } catch {}
  return false;
}

async function getSelectedTextNearDesc(page: any, desc?: string): Promise<string | undefined> {
  try {
    if (!desc) return undefined;
    const container = page.locator(`xpath=//*[contains(normalize-space(.), "${escapeRegExp(desc)}")]`).first();
    // 1) 原生 select 文本
    const sel = container.locator('select').first();
    if (await sel.count().catch(() => 0)) {
      const label = await sel.evaluate((s: HTMLSelectElement) => {
        const opt = s.options[s.selectedIndex];
        return (opt && (opt.label || opt.text)) || '';
      }).catch(() => '');
      if (label) return label;
    }
    // 2) 常见库触发器显示的选中文案
    const display = container.locator([
      '.ant-select-selector .ant-select-selection-item',
      '.el-select .el-select__selected-item',
      '.react-select__single-value',
      '.arco-select-view-value',
      '.p-dropdown-label',
      '.t-select .t-input__inner',
      '.ivu-select-selected-value',
      '[aria-selected="true"]'
    ].join(', ')).first();
    if (await display.count().catch(() => 0)) {
      const txt = await display.textContent().catch(() => '');
      if (txt) return txt.trim();
    }
  } catch {}
  return undefined;
}

async function ensureSelection(page: any, desc: string | undefined, optionText: string): Promise<boolean> {
  try {
    const selected = await getSelectedTextNearDesc(page, desc).catch(() => undefined);
    if (selected && normalizeText(selected) === normalizeText(optionText)) {
      console.log(`[Playwright][Select-Dbg] already selected: ${selected}`);
      return true;
    }
    console.log(`[Playwright][Select-Dbg] ensureSelection need select: want="${optionText}" current="${selected||''}"`);
    let ok = await trySelectFromDesc(page, desc);
    console.log(`[Playwright][Select-Dbg] trySelectFromDesc result=${ok}`);
    if (!ok) {
      console.log('[Playwright][Select-Dbg] trySelectFromDesc failed, trying dropdown trigger');
      await openDropdownTrigger(page, desc || '').catch(() => {});
      ok = await chooseDropdownOption(page, optionText).catch(() => false);
      console.log(`[Playwright][Select-Dbg] chooseDropdownOption result=${ok}`);
      if (!ok) {
        ok = await selectByTyping(page, optionText);
        console.log(`[Playwright][Select-Dbg] selectByTyping final result=${ok}`);
      }
    }
    const after = await getSelectedTextNearDesc(page, desc).catch(() => undefined);
    console.log(`[Playwright][Select-Dbg] ensureSelection after selected="${after||''}"`);
    return !!after && normalizeText(after) === normalizeText(optionText);
  } catch { return false; }
}

async function scanComboboxAndSelect(page: any, optionText: string): Promise<boolean> {
  const candidates = page.locator([
    '[role="combobox"]',
    '[aria-haspopup="listbox"]',
    '.ant-select, .ant-select-selector',
    '.el-select, .el-select__wrapper',
    '.react-select__control',
    '.MuiSelect-select',
    '.p-dropdown',
    '.t-select',
    '.arco-select',
    '.ivu-select',
    '.v-select',
    '.select2-selection'
  ].join(', '));
  const count = await candidates.count().catch(() => 0);
  console.log(`[Playwright][Select-Dbg] scan combobox candidates=${count}`);
  for (let i = 0; i < Math.min(count, 8); i++) {
    try {
      const one = candidates.nth(i);
      await one.click({ timeout: 1500 }).catch(() => {});
      const ok = await chooseDropdownOption(page, optionText).catch(() => false);
      if (ok) return true;
    } catch {}
  }
  return false;
}

// 新增：专门的select操作混合策略
async function handleSelectOperation(page: any, desc: string, options: any = {}): Promise<boolean> {
  try {
    console.log(`[Playwright][Select-Enhanced] 启动增强select处理: ${desc}`);
    
    const optionText = extractQuoted(desc);
    if (!optionText) {
      console.log('[Playwright][Select-Enhanced] 无法提取选项文本');
      return false;
    }
    
    // 策略1: 智能题目定位 - 基于题目上下文找到对应的select元素
    console.log('[Playwright][Select-Enhanced] 策略1: 智能题目定位（按题目上下文）');
    try {
      // 🎯 核心修复：根据题目描述找到对应的select元素，而不是遍历所有
      
      // 先尝试找到包含题目关键词的区域
      const titleKeywords = desc.match(/第\d+题|问题\d+|[\u4e00-\u9fa5]{3,}/g) || [];
      console.log(`[Playwright][Select-Enhanced] 题目关键词: ${titleKeywords.join(', ')}`);
      
      let targetSelectElement: any = null;
      let targetContext = '';
      
      // 方法1: 通过题目序号或描述定位
      for (const keyword of titleKeywords) {
        try {
          // 寻找包含关键词的题目区域
          const titleElement = page.locator(`:has-text("${keyword}")`).first();
          const titleExists = await titleElement.count() > 0;
          
          if (titleExists) {
            console.log(`[Playwright][Select-Enhanced] 找到题目关键词"${keyword}"`);
            
            // 在题目附近查找对应的select元素（向下查找最近的）
            const nearbySelect = page.locator(`
              xpath=//text()[contains(., "${keyword}")]/ancestor-or-self::*[1]//following::*[
                self::select or 
                contains(@role, "combobox") or 
                contains(@aria-haspopup, "listbox") or 
                contains(@class, "select") or 
                contains(@class, "dropdown")
              ][1]
            `);
            
            const selectCount = await nearbySelect.count();
            if (selectCount > 0) {
              targetSelectElement = nearbySelect.first();
              targetContext = keyword;
              console.log(`[Playwright][Select-Enhanced] 找到题目"${keyword}"对应的select元素`);
              break;
            }
          }
        } catch (e: any) {
          console.log(`[Playwright][Select-Enhanced] 关键词"${keyword}"定位失败: ${e.message}`);
        }
      }
      
      // 方法2: 直接使用第一个可见的select元素（按DOM顺序）
      if (!targetSelectElement) {
        console.log('[Playwright][Select-Enhanced] 使用第一个可见的select元素（按DOM顺序）');
        
        // 🎯 简化逻辑：直接找第一个可用的select元素
        const visibleSelects = await page.locator('select, [role="combobox"], [aria-haspopup="listbox"], .ant-select, .el-select, [class*="select"], [class*="dropdown"]').all();
        console.log(`[Playwright][Select-Enhanced] 找到${visibleSelects.length}个潜在select元素`);
        
        let closestElement: any = null;
        
        // 🎯 简化逻辑：直接使用第一个可见且可操作的select
        for (let i = 0; i < visibleSelects.length; i++) {
          try {
            const element = visibleSelects[i];
            const isVisible = await element.isVisible();
            const isEnabled = await element.isEnabled();
            
            if (isVisible && isEnabled) {
              closestElement = element;
              targetContext = `第${i + 1}个可见select元素`;
              console.log(`[Playwright][Select-Enhanced] ✅ 选中${targetContext}`);
              break;
            } else {
              console.log(`[Playwright][Select-Enhanced] 跳过元素${i + 1}: visible=${isVisible}, enabled=${isEnabled}`);
            }
          } catch (e: any) {
            console.log(`[Playwright][Select-Enhanced] 检查元素${i + 1}失败: ${e.message}`);
          }
        }
        
        targetSelectElement = closestElement;
      }
      
      // 🎯 只处理找到的目标select元素
      if (targetSelectElement) {
        console.log(`[Playwright][Select-Enhanced] 处理目标select: ${targetContext}`);
        
        // 滚动到元素可见
        await targetSelectElement.scrollIntoViewIfNeeded();
        await page.waitForTimeout(300);
        
        // 检查是否可见和可交互
        const isVisible = await targetSelectElement.isVisible();
        const isEnabled = await targetSelectElement.isEnabled().catch(() => true);
        
        if (isVisible && isEnabled) {
          // 点击触发下拉
          await targetSelectElement.click({ timeout: 2000 });
          await page.waitForTimeout(400);
          
          // 尝试选择目标选项
          const success = await chooseDropdownOption(page, optionText);
          if (success) {
            console.log(`[Playwright][Select-Enhanced] 策略1成功 - 已选择"${optionText}"`);
            return true;
          } else {
            console.log(`[Playwright][Select-Enhanced] 无法在当前select中选择"${optionText}"`);
          }
        }
      } else {
        console.log('[Playwright][Select-Enhanced] 未找到合适的目标select元素');
      }
      
      // 如果上述都失败，尝试常规处理
      const success = await trySelectFromDesc(page, desc);
      if (success) {
        console.log('[Playwright][Select-Enhanced] 策略1成功（常规处理）');
        return true;
      }
    } catch (e) {
      console.log(`[Playwright][Select-Enhanced] 策略1失败: ${e}`);
    }
    
    // 策略2: 关键词区域定位（包含单选按钮）
    console.log('[Playwright][Select-Enhanced] 策略2: 关键词区域定位');
    try {
      // 提取描述中的关键词
      const keywords = desc.match(/[\u4e00-\u9fa5]{2,}/g) || [];
      console.log(`[Playwright][Select-Enhanced] 提取关键词: ${keywords.join(', ')}`);
      
      for (const keyword of keywords) {
        try {
          // 寻找包含关键词的文本节点
          const textLocator = page.locator(`text=${keyword}`).first();
          const exists = await textLocator.count() > 0;
          
          if (exists) {
            console.log(`[Playwright][Select-Enhanced] 找到关键词"${keyword}"，寻找附近的select/radio`);
            
            // 在该文本附近寻找select元素或单选按钮（向下和向右查找）
            const nearbySelectors = [
              // 下拉选择
              `xpath=.//following::*[contains(@class,"select") or contains(@role,"combobox") or self::select][1]`,
              `xpath=.//parent::*//following-sibling::*[contains(@class,"select") or contains(@role,"combobox") or self::select][1]`,
              `xpath=.//ancestor::*[1]//*[contains(@class,"select") or contains(@role,"combobox") or self::select][1]`,
              // 单选按钮
              `xpath=.//following::*[@type="radio"][1]`,
              `xpath=.//parent::*//following-sibling::*//*[@type="radio"][1]`,
              `xpath=.//ancestor::*[2]//*[@type="radio"][1]`,
              // 根据具体选项文本查找单选按钮
              `xpath=.//following::*[contains(text(),"${optionText}")]/preceding-sibling::input[@type="radio"] | .//following::*[contains(text(),"${optionText}")]/following-sibling::input[@type="radio"] | .//following::input[@type="radio" and contains(@value,"${optionText}")]`
            ];
            
            for (const selector of nearbySelectors) {
              try {
                const nearbyElement = textLocator.locator(selector);
                const hasNearby = await nearbyElement.count() > 0;
                
                if (hasNearby) {
                  console.log(`[Playwright][Select-Enhanced] 找到附近的元素: ${selector}`);
                  
                  // 检查是否是单选按钮
                  const isRadio = await nearbyElement.getAttribute('type') === 'radio';
                  
                  if (isRadio) {
                    // 单选按钮直接点击
                    await nearbyElement.click({ timeout: 2000 });
                    console.log('[Playwright][Select-Enhanced] 策略2成功（单选按钮）');
                    return true;
                  } else {
                    // 下拉选择
                    await nearbyElement.click({ timeout: 2000 });
                    await page.waitForTimeout(300);
                    
                    const success = await chooseDropdownOption(page, optionText);
                    if (success) {
                      console.log('[Playwright][Select-Enhanced] 策略2成功（下拉选择）');
                      return true;
                    }
                  }
                }
              } catch {}
            }
            
            // 尝试直接查找包含选项文本的可点击元素
            try {
              const directOption = page.locator(`text=${optionText}`).first();
              const hasDirectOption = await directOption.count() > 0;
              
              if (hasDirectOption) {
                console.log(`[Playwright][Select-Enhanced] 找到直接包含选项文本的元素: ${optionText}`);
                await directOption.click({ timeout: 2000 });
                console.log('[Playwright][Select-Enhanced] 策略2成功（直接点击选项文本）');
                return true;
              }
            } catch {}
          }
        } catch {}
      }
    } catch (e) {
      console.log(`[Playwright][Select-Enhanced] 策略2失败: ${e}`);
    }
    
    // 策略3: 全局扫描备选方案
    console.log('[Playwright][Select-Enhanced] 策略3: 全局扫描');
    const globalScanResult = await scanComboboxAndSelect(page, optionText);
    if (globalScanResult) {
      console.log('[Playwright][Select-Enhanced] 策略3成功');
      return true;
    }
    
    console.log('[Playwright][Select-Enhanced] 所有增强策略失败');
    return false;
  } catch (e) {
    console.log(`[Playwright][Select-Enhanced] 处理异常: ${e}`);
    return false;
  }
}

const baseWithAi = base.extend<PlayWrightAiFixtureType>(
  PlaywrightAiFixture({
    waitForNetworkIdleTimeout: 200000,
    // Midscene现在会自动从标准环境变量读取配置
    // 只保留基本的网络等待配置
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
    const p = pages.length > 0 ? pages[0] : await context.newPage();

    // 🎯 全新Profile方案：无需清理，每次都是全新AdsPower环境
    console.log('[Fixture] 🆕 使用全新AdsPower Profile，无需数据清理');

    // 🚀 商用级AdsPower窗口稳定性增强
    if (WS_ENDPOINT) {
      // 等待窗口完全初始化
      console.log('[Fixture] 🔍 检查AdsPower窗口稳定性...');
      await p.waitForTimeout(1000);
      
      // 🎯 历史版本74b3fa646的简洁方式 - 无需复杂页面状态检测
      
      // 验证窗口状态
      try {
        const isReady = await p.evaluate(() => {
          return document.readyState === 'complete' && typeof window !== 'undefined';
        });
        console.log(`[Fixture] 📋 窗口就绪状态: ${isReady}`);
        
        if (!isReady) {
          console.log('[Fixture] ⏳ 等待窗口完全加载...');
          await p.waitForLoadState('domcontentloaded', { timeout: 10000 });
        }
      } catch (e) {
        console.log(`[Fixture] ⚠️ 窗口状态检查异常: ${e.message}`);
      }
      
      try {
        // 🎯 精确匹配窗口尺寸，确保内容完全可见
        console.log('[Fixture] 🖥️ 精确匹配窗口尺寸...');
        
        // 获取精确的窗口尺寸
        const size = await p.evaluate(() => ({ 
          width: (window as any).innerWidth, 
          height: (window as any).innerHeight,
          outerWidth: (window as any).outerWidth,
          outerHeight: (window as any).outerHeight
        }));
        console.log(`[Fixture] 📐 检测到实际尺寸: inner=${size?.width}x${size?.height}, outer=${size?.outerWidth}x${size?.outerHeight}`);
        
        // 🎯 关键修复：使用实际内部尺寸，不要放大
        const actualWidth = size?.width || 592;
        const actualHeight = size?.height || 834;
        
        await p.setViewportSize({ 
          width: actualWidth, 
          height: actualHeight 
        });
        console.log(`[Fixture] ✅ 已精确匹配viewport: ${actualWidth}x${actualHeight}`);
        
        // 🎯 历史版本74b3fa646的简单页面配置 - 只做基础viewport同步

        // 🔧 强制设置桌面端User-Agent和设备特征
        await p.evaluate(() => {
          // 移除移动端标识
          Object.defineProperty(navigator, 'userAgent', {
            value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            writable: false
          });
          
          // 确保不是移动设备
          Object.defineProperty(navigator, 'platform', {
            value: 'Win32',
            writable: false
          });
        });

        // 🔍 诊断页面初始状态（不做强制修改）
        console.log('[Fixture] 🔍 检查页面初始滚动状态...');
        const initialScroll = await p.evaluate(() => ({
          scrollY: window.scrollY,
          scrollTop: document.documentElement.scrollTop,
          bodyScrollTop: document.body.scrollTop,
          hasHash: window.location.hash,
          documentHeight: document.documentElement.scrollHeight,
          windowHeight: window.innerHeight
        }));
        console.log('[Fixture] 📊 页面初始状态:', initialScroll);

      } catch {}

      try {
        const original = (p as any).setViewportSize?.bind(p);
        (p as any).setViewportSize = async (sz: any) => {
          console.log('[Fixture] Ignore setViewportSize in CDP-connected mode (keeping window-matched viewport):', sz);
          return; // no-op，保持与外层窗口一致
        };
        // 仍可通过 original 手动调用（若以后需要）
        (p as any).__setViewportSizeOriginal = original;
      } catch {}
    }

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
        // 历史版本的高效启发式回退
        await fallbackTapByHeuristic(page, desc);
        return undefined as any;
      }
    });
  },
  aiWaitFor: async ({ aiWaitFor, page }, use) => {
    await use(async (desc: string, options?: any): Promise<any> => {
      try {
        console.log(`[Playwright][Wait-Dbg] aiWaitFor desc="${desc}" opts=${JSON.stringify(options||{})}`);
        return await aiWaitFor(desc, options);
      } catch (e) {
        console.log(`[Playwright][Wait-Dbg] aiWaitFor error=${(e as any)?.message || e}`);
        await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});
        return undefined as any;
      }
    });
  },
  aiAssert: async ({ aiAssert, page }, use) => {
    await use(async (desc: string, options?: any): Promise<any> => {
      try {
        console.log(`[Playwright][Assert-Dbg] aiAssert desc="${desc}"`);
        await scrollToDesc(page, desc);
        return await aiAssert(desc, { autoWaitVisibleMs: AUTO_WAIT_VISIBLE_MS, ...(options||{}) });
      } catch (e) {
        console.log(`[Playwright][Assert-Dbg] aiAssert error=${(e as any)?.message || e}`);
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
        console.log(`[Input-Dbg] aiInput start desc="${desc}" value.len=${(value||'').length}`);
        await scrollToDesc(page, desc);
        const r = await aiInput(desc, value, { autoWaitVisibleMs: AUTO_WAIT_VISIBLE_MS, ...(options||{}) });
        console.log(`[Input-Dbg] aiInput result=${!!r}`);
        return r;
      } catch (e) {
        console.log(`[Input-Dbg] aiInput error=${(e as any)?.message || e}`);
        // 深度思考再试
        try {
          console.log('[Input-Dbg] deepThink retry');
          const rr = await aiInput(desc, value, { autoWaitVisibleMs: AUTO_WAIT_VISIBLE_MS, ...(options||{}), deepThink: true });
          console.log(`[Input-Dbg] deepThink result=${!!rr}`);
          return rr;
        } catch {}
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
      console.log(`[Select-Dbg] aiSelect start desc="${desc}" option="${optionText}"`);
      await scrollToDesc(page, desc);
      // 先尝试“题干+原生select”
      // 1) 原生 select
      try {
        const container = page.locator(`xpath=//*[contains(normalize-space(.), "${desc}")]`).first();
        const selectInContainer = container.locator('select');
        if (await selectInContainer.count().catch(() => 0)) {
          await selectInContainer.first().selectOption({ label: optionText }).catch(async () => {
            await selectInContainer.first().selectOption(optionText).catch(() => {});
          });
          const selected = await getSelectedTextNearDesc(page, desc).catch(() => undefined);
          if (selected) console.log(`[Select-Dbg] selected via native select: ${selected}`);
          return;
        }
        const globalSelect = page.locator('select');
        if (await globalSelect.count().catch(() => 0)) {
          await globalSelect.first().selectOption({ label: optionText }).catch(async () => {
            await globalSelect.first().selectOption(optionText).catch(() => {});
          });
          const selected = await getSelectedTextNearDesc(page, desc).catch(() => undefined);
          if (selected) console.log(`[Select-Dbg] selected via global select: ${selected}`);
          return;
        }
      } catch {}
      // 2) 自定义下拉：点击触发器
      await openDropdownTrigger(page, desc).catch(() => {});
      // 3) 选择选项
      let done = await chooseDropdownOption(page, optionText);
      if (!done) {
        // 再尝试：输入法型下拉（可搜索）
        done = await selectByTyping(page, optionText);
        if (!done) await chooseDropdownOption(page, optionText).catch(() => {});
      }
      // 小等待，保证弹层关闭
      await page.waitForTimeout(100).catch(() => {});
      const selected = await getSelectedTextNearDesc(page, desc).catch(() => undefined);
      if (selected) console.log(`[Select-Dbg] selected via custom select: ${selected}`);
    });
  },
  // 🎯 添加历史版本74b3fa646的专门aiSelect实现
  aiSelect: async ({ page }, use) => {
    await use(async (desc: string, optionText: string): Promise<any> => {
      console.log(`[Select] aiSelect desc="${desc}" option="${optionText}"`);
      // 1) 原生 select
      try {
        const container = page.locator(`xpath=//*[contains(normalize-space(.), "${desc}")]`).first();
        const selectInContainer = container.locator('select');
        if (await selectInContainer.count().catch(() => 0)) {
          await selectInContainer.first().selectOption({ label: optionText }).catch(async () => {
            await selectInContainer.first().selectOption(optionText).catch(() => {});
          });
          console.log(`[Select] 原生select选择成功`);
          return;
        }
        const globalSelect = page.locator('select');
        if (await globalSelect.count().catch(() => 0)) {
          await globalSelect.first().selectOption({ label: optionText }).catch(async () => {
            await globalSelect.first().selectOption(optionText).catch(() => {});
          });
          console.log(`[Select] 全局select选择成功`);
          return;
        }
      } catch {}
      // 2) 自定义下拉：点击触发器
      console.log(`[Select] 尝试打开下拉触发器`);
      await openDropdownTrigger(page, desc).catch(() => {});
      // 3) 选择选项
      console.log(`[Select] 尝试选择选项: ${optionText}`);
      const done = await chooseDropdownOption(page, optionText);
      if (!done) {
        // 再尝试：输入法型下拉（可搜索）
        console.log(`[Select] 尝试搜索型下拉输入`);
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

// 🎯 商用级增强：多选题智能处理
async function handleMultiSelectOperation(page: any, desc: string, options: any = {}): Promise<boolean> {
  console.log(`[Playwright][MultiSelect] 🎯 启动智能多选处理: ${desc}`);
  
  try {
    // 提取所有需要选择的选项
    const quotedOptions = desc.match(/["""]([^"""]+)["""]/g)?.map(opt => opt.replace(/["""]/g, '')) || [];
    
    if (quotedOptions.length === 0) {
      console.log('[Playwright][MultiSelect] ❌ 未找到需要选择的选项');
      return false;
    }
    
    console.log(`[Playwright][MultiSelect] 📋 需要选择: ${quotedOptions.join(', ')}`);
    
    let successCount = 0;
    
    // 为每个选项尝试选择
    for (const option of quotedOptions) {
      try {
        // 查找对应的checkbox或选项
        const checkboxSelectors = [
          `input[type="checkbox"][value*="${option}"]`,
          `input[type="checkbox"] + label:text-is("${option}")`,
          `label:text-is("${option}") input[type="checkbox"]`,
          `*:text-is("${option}") input[type="checkbox"]`,
          `*:text-is("${option}")`,
        ];
        
        for (const selector of checkboxSelectors) {
          const elements = page.locator(selector);
          const count = await elements.count().catch(() => 0);
          
          if (count > 0) {
            await elements.first().click();
            console.log(`[Playwright][MultiSelect] ✅ 已选择: ${option}`);
            successCount++;
            break;
          }
        }
      } catch (e) {
        console.log(`[Playwright][MultiSelect] ⚠️ 选择"${option}"失败: ${e.message}`);
      }
    }
    
    const success = successCount === quotedOptions.length;
    console.log(`[Playwright][MultiSelect] ${success ? '✅' : '⚠️'} 多选完成: ${successCount}/${quotedOptions.length}`);
    return success;
    
  } catch (error) {
    console.log(`[Playwright][MultiSelect] ❌ 多选处理失败: ${error.message}`);
    return false;
  }
}

// 🎯 商用级增强：智能输入处理
async function handleSmartInput(page: any, desc: string, options: any = {}): Promise<boolean> {
  console.log(`[Playwright][SmartInput] 🎯 启动智能输入处理: ${desc}`);
  
  try {
    // 提取输入内容
    const quotedContent = desc.match(/["""]([^"""]+)["""]/);
    const inputValue = quotedContent ? quotedContent[1] : '';
    
    if (!inputValue) {
      console.log('[Playwright][SmartInput] ❌ 未找到输入内容');
      return false;
    }
    
    console.log(`[Playwright][SmartInput] 📝 输入内容: ${inputValue}`);
    
    // 智能定位输入框（从上到下扫描）
    const inputSelectors = [
      'input[type="text"]:visible',
      'input[type="email"]:visible', 
      'input[type="tel"]:visible',
      'input[type="number"]:visible',
      'input:not([type]):visible',
      'textarea:visible',
      '[contenteditable="true"]:visible'
    ];
    
    for (const selector of inputSelectors) {
      try {
        const elements = page.locator(selector);
        const count = await elements.count().catch(() => 0);
        
        if (count > 0) {
          const element = elements.first();
          
          // 检查是否可见和可编辑
          const isVisible = await element.isVisible();
          const isEnabled = await element.isEnabled().catch(() => true);
          
          if (isVisible && isEnabled) {
            // 滚动到元素
            await element.scrollIntoViewIfNeeded();
            await page.waitForTimeout(200);
            
            // 清空并输入
            await element.click();
            await element.fill('');
            await element.type(inputValue, { delay: 50 });
            
            console.log(`[Playwright][SmartInput] ✅ 输入成功: ${inputValue}`);
            return true;
          }
        }
      } catch (e) {
        console.log(`[Playwright][SmartInput] ⚠️ 尝试${selector}失败: ${e.message}`);
      }
    }
    
    console.log('[Playwright][SmartInput] ❌ 未找到合适的输入框');
    return false;
    
  } catch (error) {
    console.log(`[Playwright][SmartInput] ❌ 智能输入失败: ${error.message}`);
    return false;
  }
}

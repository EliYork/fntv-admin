import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { join } from 'node:path'
import { createRequire } from 'node:module'
const require = createRequire(import.meta.url)
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright')
const browser = await chromium.launch({ channel: 'msedge', headless: true })
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } })
  await page.clock.install()
  const errors = []
  const calls = []
  page.on('pageerror', (error) => errors.push(error.message))
  const movie = { guid: 'movie-1', title: '测试电影', media_type: 'Movie', play_count: 3, runtime: '90 分钟' }
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url()); if (!url.pathname.startsWith('/api/')) return route.continue(); calls.push(url.pathname + url.search)
    const n = Number(url.searchParams.get('page') || 1)
    const size = Number(url.searchParams.get('page_size') || 20)
    let data = {}
    if (url.pathname.endsWith('/auth/me')) data = { id: 1, username: 'admin', is_admin: true, auth_mode: 'local_no_auth' }
    else if (url.pathname.endsWith('/database-status')) data = { fntv: { availability: 'available', snapshot_enabled: false }, admin: { ok: true } }
    else if (url.pathname === '/api/users') data = { items: Array.from({ length: size }, (_, i) => ({ guid: `u-${i + (n - 1) * size}`, username: `测试用户${i + (n - 1) * size}`, play_count: 1, watch_duration: '1 小时' })), page: n, page_size: size, pages: 6, total: 120 }
    else if (url.pathname === '/api/history') data = { items: [{ id: 'record', user_guid: url.searchParams.get('user_guid') || 'u-1', username: '用户甲', display_title: '观看记录', played_at: '2026-09-23 12:00:00' }], total: 1, pages: 1, page: 1, page_size: size }
    else if (url.pathname === '/api/media') data = { items: [movie], total: 1, pages: 1, page: 1, page_size: 20 }
    else if (url.pathname === '/api/media/movie-1') data = movie
    else if (url.pathname.endsWith('/top-users')) data = [{ user_guid: 'u-1', username: '用户甲', play_count: 4 }]
    else if (url.pathname.endsWith('/top-media')) data = [{ item_guid: movie.guid, title: movie.title, play_count: 3 }]
    else if (url.pathname.endsWith('/overview')) data = { database_ok: true, total_users: 12, active_users_7d: 5, today_plays: 18, total_play_records: 1286 }
    else if (url.pathname.endsWith('/play-trend')) data = Array.from({ length: 365 }, (_, i) => ({ date: new Date(Date.UTC(2025, 8, 24 + i)).toISOString().slice(0, 10), play_count: i % 7 * 3 }))
    else if (url.pathname.endsWith('/hourly-distribution')) data = Array.from({ length: 24 }, (_, hour) => ({ hour, play_count: hour > 16 ? (hour - 15) * 7 : hour % 4 * 2 }))
    else if (url.pathname.startsWith('/api/reports/')) data = []
    await route.fulfill({ json: { success: true, data, message: 'ok' } })
  })
  await page.goto(process.env.FRONTEND_URL || 'http://localhost:18127')
  if (process.env.SCREENSHOT_DIR) {
    await mkdir(process.env.SCREENSHOT_DIR, { recursive: true })
    await page.getByRole('link', { name: '用户甲' }).waitFor()
    for (const theme of ['light', 'dark']) {
      if (theme === 'dark') await page.getByRole('button', { name: '切换到深色主题' }).click()
      await page.screenshot({ path: join(process.env.SCREENSHOT_DIR, `dashboard-${theme}.png`) })
    }
    await page.setViewportSize({ width: 390, height: 844 })
    await page.screenshot({ path: join(process.env.SCREENSHOT_DIR, 'dashboard-mobile.png') })
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'mobile document must not overflow')
    await page.setViewportSize({ width: 1280, height: 720 })
    await page.getByRole('button', { name: '切换到浅色主题' }).click()
  }
  await page.getByRole('link', { name: '用户甲' }).click()
  await page.waitForURL('**/history?user=u-1')
  await page.getByText('观看记录', { exact: true }).waitFor()
  assert.ok(calls.some((url) => url.startsWith('/api/history?') && url.includes('user_guid=u-1')))
  await page.goBack()
  await page.getByRole('link', { name: '测试电影' }).click()
  await page.getByText('90 分钟', { exact: true }).last().waitFor()
  assert.equal(await page.locator('.series-drawer').isVisible(), true)
  await page.locator('.series-drawer .el-drawer__close-btn').click()
  await page.waitForURL('**/media')
  async function navigate(name) {
    await page.getByRole('button', { name: '打开功能与设置' }).click()
    const drawer = page.locator('#features-drawer')
    await drawer.waitFor({ state: 'visible' })
    assert.ok(await drawer.evaluate((el) => el.classList.contains('ltr')), 'features drawer must open from left')
    await drawer.getByRole('button', { name, exact: false }).click()
  }
  await navigate('用户管理')
  await page.getByPlaceholder('搜索用户名').fill('测试')
  await page.getByRole('button', { name: '搜索', exact: true }).click()
  await page.getByRole('button', { name: '播放次数，点击排序', exact: true }).click()
  await page.locator('.el-pager li').filter({ hasText: /^2$/ }).click()
  await page.getByRole('button', { name: '测试用户20', exact: true }).waitFor()
  if (process.env.SCREENSHOT_DIR) {
    await page.getByRole('button', { name: '测试用户20', exact: true }).click()
    await page.getByText('显示别名', { exact: true }).waitFor()
    await page.waitForTimeout(400)
    await page.screenshot({ path: join(process.env.SCREENSHOT_DIR, 'user-details.png') })
    await page.locator('.el-drawer:visible .el-drawer__close-btn').click()
  }
  await page.locator('.main-view').evaluate((el) => { el.scrollTop = 300 })
  const before = await page.locator('.main-view').evaluate((el) => el.scrollTop)
  assert.ok(before > 0)
  await navigate('媒体库')
  await navigate('用户管理')
  assert.equal(await page.getByPlaceholder('搜索用户名').inputValue(), '测试')
  assert.equal(await page.locator('.el-pager li.is-active').innerText(), '2')
  assert.ok(await page.getByRole('button', { name: '播放次数，当前降序，点击切换为升序', exact: true }).count())
  const after = await page.locator('.main-view').evaluate((el) => el.scrollTop)
  assert.ok(Math.abs(before - after) < 2, `scroll must be restored (${before} => ${after})`)
  const historyCount = calls.filter((url) => url.startsWith('/api/history?')).length
  const reportCount = calls.filter((url) => url.startsWith('/api/reports/')).length
  const userCount = calls.filter((url) => url.startsWith('/api/users?')).length
  const refreshed = page.waitForResponse((response) => response.url().includes('/api/users?'))
  await page.clock.fastForward(61_000)
  await refreshed
  assert.equal(calls.filter((url) => url.startsWith('/api/history?')).length, historyCount, 'inactive history must not poll')
  assert.equal(calls.filter((url) => url.startsWith('/api/reports/')).length, reportCount, 'inactive dashboard must not poll')
  assert.ok(calls.filter((url) => url.startsWith('/api/users?')).length > userCount, 'active users page keeps refreshing')
  assert.deepEqual(errors, [])
  console.log('browser: rank links, media drawer, left feature menu, retained filters/sort/page/scroll passed')
} finally { await browser.close() }

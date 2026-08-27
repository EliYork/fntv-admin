import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { join } from 'node:path'

const root = process.cwd()
const require = createRequire(import.meta.url)
const ts = require(join(root, 'frontend', 'node_modules', 'typescript'))

function loadTypeScriptModule(relativePath) {
  const source = readFileSync(join(root, relativePath), 'utf8')
  const output = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 }
  }).outputText
  const module = { exports: {} }
  new Function('exports', 'module', output)(module.exports, module)
  return module.exports
}

const { buildDateMonthLabels } = loadTypeScriptModule('frontend/src/utils/heatmapCalendar.ts')
const { shouldRefreshWhenVisible, VISIBILITY_REFRESH_STALE_MS } = loadTypeScriptModule('frontend/src/utils/visibilityRefresh.ts')
const dashboard = readFileSync(join(root, 'frontend', 'src', 'views', 'Dashboard.vue'), 'utf8')
const heatmap = readFileSync(join(root, 'frontend', 'src', 'components', 'PlaybackHeatmap.vue'), 'utf8')
const layout = readFileSync(join(root, 'frontend', 'src', 'layouts', 'AdminLayout.vue'), 'utf8')
const history = readFileSync(join(root, 'frontend', 'src', 'components', 'HistoryFeed.vue'), 'utf8')

const dates = []
for (let cursor = new Date(2025, 7, 27); cursor <= new Date(2026, 1, 2); cursor.setDate(cursor.getDate() + 1)) {
  dates.push(`${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, '0')}-${String(cursor.getDate()).padStart(2, '0')}`)
}
const byDate = new Set(dates)
const start = new Date(2025, 7, 25)
const weeks = []
for (let cursor = new Date(start); cursor <= new Date(2026, 1, 2); cursor.setDate(cursor.getDate() + 7)) {
  const cells = []
  for (let day = 0; day < 7; day += 1) {
    const value = new Date(cursor)
    value.setDate(value.getDate() + day)
    cells.push({ date: `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}` })
  }
  weeks.push({ cells })
}
const labels = buildDateMonthLabels(weeks, dates.map((date) => ({ date, play_count: byDate.has(date) ? 1 : 0 })))
assert.equal(labels[0].text, '2025年9月', 'partial August must not render an isolated month label')
assert.equal(labels.find((label) => label.key === '2026-01')?.text, '2026年1月', 'year transitions must include the new year')
assert.ok(labels.slice(1).some((label) => label.text === '10月'), 'later labels should remain compact')

const now = 100_000
assert.equal(shouldRefreshWhenVisible('hidden', 0, 0, now), false, 'hidden pages must not refresh')
assert.equal(shouldRefreshWhenVisible('visible', now - VISIBILITY_REFRESH_STALE_MS + 1, 0, now), false, 'fresh data must not refresh')
assert.equal(shouldRefreshWhenVisible('visible', now - VISIBILITY_REFRESH_STALE_MS, 0, now), true, 'stale visible data must refresh')
assert.equal(shouldRefreshWhenVisible('visible', 0, now - 1_000, now), false, 'a recent failed attempt must still throttle retries')

assert.match(layout, /visibilitychange/, 'visibility changes should drive automatic page refresh')
assert.match(layout, /router\.replace/, 'automatic refresh should notify only the current route')
const visibleRefresh = layout.slice(layout.indexOf('async function refreshVisiblePage'), layout.indexOf('function handleVisibilityChange'))
assert.doesNotMatch(visibleRefresh, /refreshSnapshot/, 'visibility refresh must not force a snapshot rebuild')
assert.match(history, /item\.record_key \|\| item\.id/, 'history rows should deduplicate by the backend row identity')
assert.match(dashboard, /\.hourly-chart::after/, 'the hourly chart should use one shared baseline')
assert.doesNotMatch(dashboard, /\.hour-bar-zone[^}]*border-bottom/, 'hour bars must not have separate bases')
assert.match(heatmap, /grid-template-columns: 16px minmax\(0, 1fr\); gap: 6px/, 'weekday labels should sit closer to the heatmap grid')

console.log('dashboard refresh and visual smoke passed')

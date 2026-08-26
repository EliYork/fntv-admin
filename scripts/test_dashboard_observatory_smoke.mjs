import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()
const dashboard = readFileSync(join(root, 'frontend', 'src', 'views', 'Dashboard.vue'), 'utf8')
const history = readFileSync(join(root, 'frontend', 'src', 'components', 'HistoryFeed.vue'), 'utf8')
const layout = readFileSync(join(root, 'frontend', 'src', 'layouts', 'AdminLayout.vue'), 'utf8')
const heatmap = readFileSync(join(root, 'frontend', 'src', 'components', 'PlaybackHeatmap.vue'), 'utf8')

assert.match(layout, /飞牛影视/, 'top toolbar should carry the product name')
assert.doesNotMatch(layout, /desktop-aside|admin-aside/, 'desktop layout should not keep a permanent sidebar')
assert.match(dashboard, /<HistoryFeed ref="historyFeed"/, 'dashboard should include the continuous history feed')
assert.match(dashboard, /grid-template-columns: repeat\(24/, 'hourly distribution should use a 24-column horizontal chart')
assert.doesNotMatch(dashboard, /收藏记录|下载记录|媒体类型分布|分辨率分布|最近观看/, 'low-frequency and duplicate sections should stay off the dashboard')
assert.doesNotMatch(heatmap, /颜色越深|heatmap-legend|>少<|>多</, 'heatmap should not include an explanatory color legend')

assert.match(history, /const pageSize = ref\(50\)/, 'history should initially load 50 rows')
assert.match(history, /items\.value = requestedPage === 1 \? uniqueItems : \[\.\.\.items\.value, \.\.\.uniqueItems\]/, 'later pages should append instead of replace')
assert.match(history, /const knownKeys = new Set/, 'history append should deduplicate records')
assert.match(history, /data\.page >= data\.pages/, 'history should stop at the final API page')
assert.match(history, /@change="changePageSize"/, 'changing batch size should reset the feed')
assert.match(history, /IntersectionObserver/, 'history should support automatic continuous loading')
assert.match(history, />加载更多</, 'history should retain an explicit load-more fallback')

console.log('dashboard observatory smoke passed')

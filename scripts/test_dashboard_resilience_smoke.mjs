import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()
const dashboard = readFileSync(join(root, 'frontend', 'src', 'views', 'Dashboard.vue'), 'utf8')
const history = readFileSync(join(root, 'frontend', 'src', 'components', 'HistoryFeed.vue'), 'utf8')
const layout = readFileSync(join(root, 'frontend', 'src', 'layouts', 'AdminLayout.vue'), 'utf8')
const cache = readFileSync(join(root, 'frontend', 'src', 'utils', 'successfulDataCache.ts'), 'utf8')
const time = readFileSync(join(root, 'frontend', 'src', 'utils', 'applicationTime.ts'), 'utf8')
const client = readFileSync(join(root, 'frontend', 'src', 'api', 'client.ts'), 'utf8')

assert.match(cache, /SUCCESSFUL_DATA_CACHE_VERSION = 1/, 'dashboard cache must be explicitly versioned')
assert.match(cache, /JSON\.parse/, 'dashboard cache must parse JSON defensively')
assert.match(cache, /localStorage\.removeItem/, 'invalid cache entries must be ignored and removed')
assert.match(dashboard, /Promise\.allSettled/, 'dashboard modules must commit independently')
assert.match(dashboard, /status === 'fulfilled'/, 'only fulfilled module requests may replace displayed data')
assert.doesNotMatch(dashboard, /Request failed|AxiosError|sectionErrors/, 'dashboard must not expose technical request errors')
assert.match(layout, /数据更新于/, 'top bar must show the successful data timestamp')
assert.match(layout, /部分数据可能来自上次成功更新/, 'mixed-age data must have a quiet tooltip')
assert.match(history, /resetAndLoad\(true\)/, 'ordinary history refresh must preserve committed rows')
assert.match(history, /data\.error/, 'HTTP 200 business failures must not replace committed history')
assert.match(history, /retry the same nextPage/, 'failed infinite loading must not advance the page cursor')
assert.doesNotMatch(history, /new Date\(value\)/, 'history must not parse ambiguous wall-clock strings with Date')
assert.match(time, /WALL_CLOCK_RE/, 'frontend time parsing must recognize explicit API wall-clock values')
assert.ok(client.indexOf('status && status >= 500') < client.indexOf("typeof message === 'string'"), 'HTTP 500 must be sanitized before backend details are considered')

console.log('dashboard resilience smoke passed')

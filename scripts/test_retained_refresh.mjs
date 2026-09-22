import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { resolve, dirname } from 'node:path'
const require = createRequire(import.meta.url)
const root = process.cwd()
const ts = require(resolve('frontend/node_modules/typescript'))
const vue = require(resolve('frontend/node_modules/vue'))
const compiler = require(resolve('frontend/node_modules/@vue/compiler-sfc'))
let mounts = [], unmounts = [], activations = [], deactivations = [], timers = [], hidden = false
const route = vue.reactive({ path: "/media", query: {} })
const router = { replace: async (target) => { Object.assign(route, target) } }
const api = {}
const fakeVue = { ...vue, onMounted: (fn) => mounts.push(fn), onUnmounted: (fn) => unmounts.push(fn), onActivated: (fn) => activations.push(fn), onDeactivated: (fn) => deactivations.push(fn) }
const document = { get visibilityState() { return hidden ? 'hidden' : 'visible' }, querySelector: () => null }
function load(path) {
  const absolute = resolve(root, path)
  let source = readFileSync(absolute, 'utf8')
  if (path.endsWith('.vue')) source = compiler.compileScript(compiler.parse(source).descriptor, { id: 'test' }).content
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  const module = { exports: {} }
  const localRequire = (name) => {
    if (name === 'vue') return fakeVue
    if (name === 'vue-router') return { useRoute: () => route, useRouter: () => router, RouterLink: {} }
    if (name === 'element-plus') return { ElMessage: { success() {} } }
    if (name.startsWith('@element-plus')) return {}
    if (name.endsWith('/api/modules')) return api
    if (name.endsWith('/utils/routeRefresh')) return { useRouteRefresh() {} }
    if (name.endsWith('.vue')) return {}
    if (name.startsWith('.')) return load(resolve(dirname(absolute), name + '.ts'))
    throw new Error(name)
  }
  new Function('require', 'module', 'exports', 'document', 'setTimeout', 'clearTimeout', 'window', js)(localRequire, module, module.exports, document, (fn) => { timers.push(fn); return fn }, (fn) => { timers = timers.filter((item) => item !== fn) }, { dispatchEvent() {} })
  return module.exports
}
function setup(path, props = {}, emit = () => {}) { return load(path).default.setup(props, { expose() {}, emit }) }
function deferred() { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no }); return { promise, resolve, reject } }
const page = (id) => ({ items: [{ guid: id }], page: 1, page_size: 20, total: 1, pages: 1 })
const { useRetainedPage } = load('frontend/src/utils/retainedPage.ts')
let requests = []
const retained = useRetainedPage(() => { const d = deferred(); requests.push(d); return d.promise })
const old = retained.loadData(), fresh = retained.loadData()
requests[1].resolve(page('new')); await fresh
requests[0].resolve(page('old')); await old
assert.equal(retained.pageData.value.items[0].guid, 'new', 'late results must not overwrite the newest request')
let next = retained.loadData(); requests[2].reject(new Error('offline')); await next
assert.equal(retained.pageData.value.items[0].guid, 'new')
assert.match(retained.errorMessage.value, /上次结果/)
next = retained.loadData(); requests[3].resolve({ ...page('bad'), error: 'unavailable' }); await next
assert.equal(retained.pageData.value.items[0].guid, 'new', 'HTTP 200 business errors preserve data')
next = retained.loadData(); requests[4].resolve({ ...page('empty'), items: [], total: 0 }); await next
assert.equal(retained.pageData.value.items.length, 0, 'a genuine successful empty result replaces old rows')
next = retained.loadData(); unmounts.forEach((fn) => fn()); requests[5].resolve(page('unmounted')); await next
assert.equal(retained.pageData.value.items.length, 0)

mounts = []; unmounts = []; timers = []
const { useAutoRefresh } = load('frontend/src/utils/autoRefresh.ts')
let polls = 0, busy = false
useAutoRefresh(async () => { polls += 1 }, () => busy)
mounts.forEach((fn) => fn())
await timers.shift()(); assert.equal(polls, 1)
hidden = true; await timers.shift()(); assert.equal(polls, 1)
hidden = false; busy = true; await timers.shift()(); assert.equal(polls, 1)
busy = false; await timers.shift()(); assert.equal(polls, 2)
unmounts.forEach((fn) => fn()); assert.equal(timers.length, 0, 'poll stops when leaving page')

mounts = []; unmounts = []; requests = []
api.fetchMediaChildren = () => { const d = deferred(); requests.push(d); return d.promise }
api.fetchMedia = async (params) => { assert.equal(params.show_hidden, true); return page('restored') }
const media = setup('frontend/src/views/MediaLibrary.vue')
media.showHidden.value = true; await media.loadData(); assert.equal(media.pageData.value.items[0].guid, 'restored')
const first = media.openSeries({ guid: 'first', title: 'First', media_type: 'Series' })
const second = media.openSeries({ guid: 'second', title: 'Second', media_type: 'Series' })
requests[1].resolve([{ guid: 'second-season' }]); await second
requests[0].resolve([{ guid: 'first-season' }]); await first
assert.equal(media.seriesChildren.value[0].guid, 'second-season')
const season = { guid: 'season', title: 'Season' }
let expanding = media.toggleSeason(season); requests[2].reject(new Error('offline')); await expanding
assert.equal(media.seasonErrors.value.season, true)
assert.equal(media.episodesBySeason.value.season, undefined, 'failure must not become cached empty data')
await media.toggleSeason(season)
expanding = media.toggleSeason(season); requests[3].resolve([{ guid: 'episode' }]); await expanding
assert.equal(media.episodesBySeason.value.season[0].guid, 'episode', 'reopening retries failed seasons')

let saved
api.updateUserProfile = async (guid, profile) => { saved = { guid, ...profile } }
const details = setup('frontend/src/components/UserDetailsDrawer.vue', { user: { guid: 'u', username: 'User' } })
details.displayName.value = 'Alias'; details.note.value = '<b>plain text</b>'
await details.save(); assert.deepEqual(saved, { guid: 'u', display_name: 'Alias', note: '<b>plain text</b>' })

mounts = []; unmounts = []
const row = (id) => ({ id, record_key: id })
let failing = false, historyCalls = []
api.fetchHistory = async (params) => {
  historyCalls.push(params.page)
  if (failing) throw new Error('offline')
  return { items: [row(String(params.page))], page: params.page, page_size: 1, total: 3, pages: 3 }
}
const history = setup('frontend/src/components/HistoryFeed.vue')
history.pageSize.value = 1
await history.resetAndLoad(); await history.loadNextPage()
assert.equal(history.items.value.length, 2)
failing = true; await history.resetAndLoad(true); assert.equal(history.items.value.length, 2)
failing = false; historyCalls = []; await history.resetAndLoad(true)
assert.deepEqual(historyCalls, [1, 2]); assert.equal(history.items.value.length, 2, 'refresh must preserve the loaded extent')
console.log('retained refresh, request races, hierarchy retries, hidden filter, profile save and history recovery passed')

api.fetchDashboardOverview = async () => ({ database_ok: true, total_users: 1 })
api.fetchReportOverview = async () => ({ total_users: 1 })
api.fetchReportPlayTrend = async () => []
api.fetchReportTopMedia = async () => []
api.fetchReportTopUsers = async () => []
requests = []
api.fetchReportHourlyDistribution = () => { const d = deferred(); requests.push(d); return d.promise }
const dashboard = setup('frontend/src/views/Dashboard.vue')
let report = dashboard.loadHourly()
requests[0].resolve([{ hour: 1, play_count: 10 }]); await report
assert.equal(dashboard.displayedPeriods.value.hourly, '30')
dashboard.hourlyRange.value = '7'
report = dashboard.loadHourly()
assert.equal(dashboard.hourlyItems.value[0].play_count, 10, 'switching periods retains existing chart while loading')
requests[1].reject(new Error('offline')); await report
assert.equal(dashboard.hourlyItems.value[0].play_count, 10)
assert.equal(dashboard.displayedPeriods.value.hourly, '30', 'retained period is explicitly identified')
const fullRefresh = dashboard.loadData()
report = dashboard.loadHourly()
requests[3].resolve([{ hour: 1, play_count: 20 }]); await report
requests[2].resolve([{ hour: 1, play_count: 5 }]); await fullRefresh
assert.equal(dashboard.hourlyItems.value[0].play_count, 20, 'older page refresh cannot replace a newer chart request')
assert.equal(dashboard.displayedPeriods.value.hourly, '7')
console.log('dashboard stale charts and overlapping refresh tests passed')

activations = []; deactivations = []; mounts = []; unmounts = []; timers = []
let activationPolls = 0
useAutoRefresh(async () => { activationPolls += 1 }, () => false)
mounts.forEach((fn) => fn()); activations.forEach((fn) => fn())
assert.equal(timers.length, 1, 'initial activation must not duplicate the mounted timer')
deactivations.forEach((fn) => fn()); assert.equal(timers.length, 0)
activations.forEach((fn) => fn()); await timers.shift()()
assert.equal(activationPolls, 1, 'cached page restarts polling after returning')
unmounts.forEach((fn) => fn())
api.fetchMediaDetail = async (guid) => ({ guid, title: 'Movie', media_type: 'Movie', runtime: '90 分钟' })
await media.openLinkedMedia('movie-guid')
assert.equal(media.selectedSeries.value.guid, 'movie-guid')
assert.equal(media.seriesDrawerVisible.value, true)
assert.equal(media.seriesChildren.value.length, 0, 'movie details do not request series children')
const filteredProps = vue.reactive({ filterUser: 'user-one' })
const filteredHistory = setup('frontend/src/components/HistoryFeed.vue', filteredProps)
assert.equal(filteredHistory.userGuid.value, 'user-one')
filteredProps.filterUser = 'user-two'; await vue.nextTick()
assert.equal(filteredHistory.userGuid.value, 'user-two')
console.log('cached view polling, media deep links and history user filters passed')

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()
const layout = readFileSync(join(root, 'frontend', 'src', 'layouts', 'AdminLayout.vue'), 'utf8')
const start = layout.indexOf('async function refreshCurrentPage()')
const end = layout.indexOf('async function navigateTo', start)
const refresh = layout.slice(start, end)

assert.ok(start >= 0 && end > start, 'top refresh workflow should exist')
assert.match(refresh, /currentStatus\?\.fntv\.snapshot_enabled/, 'snapshot refresh should be conditional')
const snapshotCall = refresh.indexOf('await refreshSnapshot()')
const statusCall = refresh.lastIndexOf('await refreshDatabaseStatus()')
const pageCall = refresh.indexOf('router.replace')
assert.ok(snapshotCall >= 0 && snapshotCall < statusCall, 'snapshot should refresh before final database status')
assert.ok(statusCall < pageCall, 'database status should refresh before current page data')
assert.match(refresh, /快照刷新失败，已使用源库/, 'snapshot failure should use a concise fallback message')
assert.match(refresh, /refresh_in_progress/, 'busy snapshot refresh should not start another task')

console.log('top refresh smoke passed')

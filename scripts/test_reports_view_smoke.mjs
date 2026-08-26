import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()
const reportsView = join(root, 'frontend', 'src', 'views', 'Reports.vue')
const router = readFileSync(join(root, 'frontend', 'src', 'router', 'index.ts'), 'utf8')
const layout = readFileSync(join(root, 'frontend', 'src', 'layouts', 'AdminLayout.vue'), 'utf8')
const modules = readFileSync(join(root, 'frontend', 'src', 'api', 'modules.ts'), 'utf8')

assert.equal(existsSync(reportsView), false, 'standalone Reports.vue should be removed')
assert.match(router, /\{ path: 'reports', redirect: '\/dashboard' \}/, 'legacy /reports route should redirect to dashboard')
assert.doesNotMatch(layout, /path: '\/reports'/, 'function drawer should not expose a reports entry')
assert.match(modules, /fetchReportOverview/, 'dashboard report API client must remain available')

console.log('reports compatibility smoke passed')

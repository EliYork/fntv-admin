import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import vm from 'node:vm'

const root = process.cwd()
const require = createRequire(import.meta.url)
const ts = require(join(root, 'frontend', 'node_modules', 'typescript'))

function loadTsModule(relativePath) {
  const filename = join(root, relativePath)
  const source = readFileSync(filename, 'utf8')
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
    },
  }).outputText
  const module = { exports: {} }
  const sandbox = {
    exports: module.exports,
    module,
    require,
    console,
    setTimeout,
    clearTimeout,
  }
  vm.runInNewContext(output, sandbox, { filename })
  return module.exports
}

const authSession = loadTsModule('frontend/src/api/authSession.ts')
const authGuard = loadTsModule('frontend/src/router/authGuard.ts')
const clientSource = readFileSync(join(root, 'frontend', 'src', 'api', 'client.ts'), 'utf8')

assert.equal(
  authSession.getUnauthorizedAction({ status: 401, url: '/reports/overview' }),
  'recheck',
  'business 401 should recheck /auth/me before expiring the session',
)
assert.equal(
  authSession.getUnauthorizedAction({ status: 401, url: '/auth/me' }),
  'expire',
  '/auth/me 401 should expire the session',
)
assert.equal(
  authSession.getUnauthorizedAction({ status: 403, url: '/reports/overview' }),
  'ignore',
  '403 must not clear the token or redirect to login',
)
assert.equal(
  authSession.getUnauthorizedAction({ status: 500, url: '/reports/overview' }),
  'ignore',
  '500 must not be treated as a login failure',
)
assert.equal(
  authSession.getUnauthorizedAction({ status: undefined, url: '/reports/overview' }),
  'ignore',
  'network errors must not clear the token',
)
assert.equal(authSession.shouldClearTokenForStatus(401), true)
assert.equal(authSession.shouldClearTokenForStatus(403), false)
assert.equal(authSession.shouldClearTokenForStatus(undefined), false)

let finishGuard
let guardResolved = false
const pendingGuard = authGuard.resolveAuthNavigation(
  { name: 'reports', fullPath: '/reports', meta: {} },
  {
    isAuthenticated: false,
    accessDeniedMessage: '',
    ensureReady: () =>
      new Promise((resolve) => {
        finishGuard = () => resolve(true)
      }),
  },
)
pendingGuard.then(() => {
  guardResolved = true
})
await Promise.resolve()
assert.equal(guardResolved, false, 'route guard must wait for auth initialization')
finishGuard()
assert.equal(await pendingGuard, true)

assert.equal(
  JSON.stringify(
    await authGuard.resolveAuthNavigation(
      { name: 'users', fullPath: '/users?page=2', meta: {} },
      {
        isAuthenticated: false,
        accessDeniedMessage: '',
        ensureReady: async () => false,
      },
    ),
  ),
  JSON.stringify({ path: '/login', query: { redirect: '/users?page=2' } }),
)

assert.match(clientSource, /suppressGlobalError\?: boolean/, 'reports should be able to suppress global error toasts')
assert.match(clientSource, /showErrorToast/, 'client should deduplicate global error toasts')
assert.match(clientSource, /action === 'recheck'[\s\S]*stillValid[\s\S]*return Promise\.reject\(error\)/, 'business 401 should reject locally after /auth/me succeeds')
assert.doesNotMatch(clientSource, /action === 'recheck'[\s\S]*ElMessage\.error\(message\)[\s\S]*return Promise\.reject\(error\)/, 'business 401 recheck success must not show a login-style toast')

console.log('frontend auth flow smoke passed')

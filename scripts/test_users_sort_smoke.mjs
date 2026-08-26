import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()
const users = readFileSync(join(root, 'frontend', 'src', 'views', 'Users.vue'), 'utf8')
const adapter = readFileSync(join(root, 'backend', 'app', 'services', 'fntv_schema_adapter.py'), 'utf8')

assert.doesNotMatch(users, /sortable="custom"/, 'Element Plus dual-arrow custom sorter should be removed')
assert.match(users, /username: 'asc'/, 'username should default to ascending')
for (const key of ['play_count', 'watch_duration', 'last_play_at', 'last_login_at']) {
  assert.match(users, new RegExp(`${key}: 'desc'`), `${key} should default to descending`)
}
assert.match(users, /sortBy\.value === key \? \(sortOrder\.value === 'asc' \? 'desc' : 'asc'\)/, 'same title should toggle direction')
assert.match(adapter, /ORDER BY \{expression\} \{direction\}/, 'sorting must remain in backend SQL before pagination')

console.log('users sort smoke passed')

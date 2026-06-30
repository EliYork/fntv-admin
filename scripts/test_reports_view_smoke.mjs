import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()
const source = readFileSync(join(root, 'frontend', 'src', 'views', 'Reports.vue'), 'utf8')

assert.match(source, /function hasListItems<T>\(state: ListState<T>\): boolean/, 'reports lists should use an explicit non-empty helper')
assert.match(source, /function showListEmpty<T>\(state: ListState<T>\): boolean/, 'reports lists should use an explicit empty-state helper')
assert.match(source, /Array\.isArray\(items\)/, 'report list loaders must reject non-array API payloads')
assert.match(source, /class="report-content-stack"/, 'media and resolution panels should render through a concrete content container')
assert.match(source, /v-if="hasListItems\(topMedia\)"/, 'top media table should use the explicit list helper')
assert.match(source, /v-else-if="showListEmpty\(topMedia\)"/, 'top media panel should show an empty state after successful empty loads')
assert.match(source, /v-if="hasListItems\(resolutions\)"/, 'resolution rows should use the explicit list helper')
assert.match(source, /v-else-if="showListEmpty\(resolutions\)"/, 'resolution panel should show an empty state after successful empty loads')

console.log('reports view smoke passed')

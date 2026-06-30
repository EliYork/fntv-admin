import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()
const themeSource = readFileSync(join(root, 'frontend', 'src', 'stores', 'theme.ts'), 'utf8')

assert.match(themeSource, /function\s+syncThemeDom/, 'theme store should centralize DOM theme synchronization')
assert.match(themeSource, /document\.documentElement\.classList\.remove\('dark'\)/, 'light mode must explicitly remove html.dark')
assert.match(themeSource, /document\.body\.classList\.remove\('dark'\)/, 'light mode must clear stale body.dark')
assert.match(themeSource, /dataset\.theme\s*=\s*resolved/, 'data-theme must match the resolved theme')
assert.match(themeSource, /dataset\.themeMode\s*=\s*mode/, 'data-theme-mode must match the selected theme mode')

console.log('theme source smoke passed')

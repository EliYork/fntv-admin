import { defineStore } from 'pinia'

export type ThemeMode = 'system' | 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'

const STORAGE_KEY = 'fntv_theme'

function normalizeThemeMode(value: unknown): ThemeMode {
  return value === 'light' || value === 'dark' || value === 'system' ? value : 'light'
}

function getSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined') return 'light'
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function getStoredThemeMode(): ThemeMode {
  if (typeof localStorage === 'undefined') return 'light'
  return normalizeThemeMode(localStorage.getItem(STORAGE_KEY))
}

export function applyThemeMode(mode: ThemeMode): ResolvedTheme {
  const resolved = mode === 'system' ? getSystemTheme() : mode
  if (typeof document !== 'undefined') {
    document.documentElement.dataset.theme = resolved
    document.documentElement.dataset.themeMode = mode
    document.documentElement.classList.toggle('dark', resolved === 'dark')
  }
  return resolved
}

export function applyStoredTheme(): void {
  applyThemeMode(getStoredThemeMode())
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    mode: getStoredThemeMode() as ThemeMode,
    resolved: applyThemeMode(getStoredThemeMode()) as ResolvedTheme,
    listenerAttached: false
  }),
  actions: {
    init() {
      this.resolved = applyThemeMode(this.mode)
      if (this.listenerAttached || typeof window === 'undefined') return
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (this.mode === 'system') {
          this.resolved = applyThemeMode(this.mode)
        }
      })
      this.listenerAttached = true
    },
    setMode(mode: ThemeMode) {
      this.mode = normalizeThemeMode(mode)
      localStorage.setItem(STORAGE_KEY, this.mode)
      this.resolved = applyThemeMode(this.mode)
    },
    reload() {
      this.mode = getStoredThemeMode()
      this.resolved = applyThemeMode(this.mode)
    }
  }
})

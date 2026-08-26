export const SUCCESSFUL_DATA_CACHE_VERSION = 1

interface CacheEnvelope<T> {
  version: number
  updatedAt: number
  data: T
}

export function readSuccessfulData<T>(key: string): CacheEnvelope<T> | null {
  if (typeof localStorage === 'undefined') return null
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<CacheEnvelope<T>>
    if (parsed.version !== SUCCESSFUL_DATA_CACHE_VERSION || typeof parsed.updatedAt !== 'number' || !('data' in parsed)) {
      localStorage.removeItem(key)
      return null
    }
    return parsed as CacheEnvelope<T>
  } catch {
    try { localStorage.removeItem(key) } catch { /* storage may be unavailable */ }
    return null
  }
}

export function writeSuccessfulData<T>(key: string, data: T, updatedAt: number): void {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(key, JSON.stringify({ version: SUCCESSFUL_DATA_CACHE_VERSION, updatedAt, data }))
  } catch {
    // Private mode and storage quotas must never break live dashboard updates.
  }
}

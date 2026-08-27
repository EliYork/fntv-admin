export const VISIBILITY_REFRESH_STALE_MS = 60_000

export function shouldRefreshWhenVisible(
  visibilityState: DocumentVisibilityState,
  updatedAt: number | null | undefined,
  lastAttemptAt: number,
  now = Date.now(),
  staleAfterMs = VISIBILITY_REFRESH_STALE_MS
): boolean {
  if (visibilityState !== 'visible') return false
  const freshestKnownAt = Math.max(updatedAt || 0, lastAttemptAt || 0)
  return freshestKnownAt <= 0 || now - freshestKnownAt >= staleAfterMs
}

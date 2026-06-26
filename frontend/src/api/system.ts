import { getApi } from './client'

export interface DatabaseStatus {
  fntv: {
    ok: boolean
    exists: boolean
    readonly: boolean
    path: string
    error?: string
  }
  admin: {
    ok: boolean
    exists: boolean
    path: string
  }
}

export function fetchHealth() {
  return getApi<{ name: string; env: string; status: string }>('/system/health')
}

export function fetchDatabaseStatus() {
  return getApi<DatabaseStatus>('/system/database-status')
}


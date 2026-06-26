import { getApi, postApi } from './client'

export interface FntvCapabilities {
  [key: string]: boolean
  can_read_users: boolean
  can_read_items: boolean
  can_read_play_history: boolean
  can_join_user_names: boolean
  can_join_item_titles: boolean
  can_calculate_progress: boolean
}

export interface CoreCandidates {
  user_table: string | null
  item_table: string | null
  play_table: string | null
}

export interface RequiredTablesStatus {
  user: boolean
  item: boolean
  item_user_play: boolean
}

export interface DatabaseStatus {
  fntv: {
    ok: boolean
    source_path_container: string
    source_exists: boolean
    source_readable: boolean
    source_readonly_configured: boolean
    source_direct_ok: boolean | null
    active_database: string
    fallback_to_source: boolean
    degraded?: boolean
    active_db_path?: string | null
    availability?: 'available' | 'degraded' | 'unavailable'
    warnings?: Array<{ code: string | null; type: string | null; message: string | null }>
    snapshot_path_container: string
    snapshot_exists: boolean
    snapshot_dir_exists: boolean
    snapshot_dir_writable: boolean
    snapshot_tmp_path: string
    snapshot_last_refresh_at: number | null
    snapshot_ok: boolean
    snapshot_error: string | null
    snapshot_error_type: string | null
    snapshot_error_message: string | null
    error?: string | null
    error_type?: string | null
    error_message?: string | null
    detected_table_count?: number
    detected_tables?: string[]
    detected_columns_by_table?: Record<string, string[]>
    core_candidates?: CoreCandidates
    required_tables_status?: RequiredTablesStatus
    capabilities?: FntvCapabilities
    write_probe_failed?: boolean
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

export function refreshSnapshot() {
  return postApi<{ ok: boolean; snapshot_path?: string; error?: string }>('/system/refresh-snapshot')
}

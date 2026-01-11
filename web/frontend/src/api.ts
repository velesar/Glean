// API client functions

import type {
  PipelineStats,
  Tool,
  ToolDetail,
  ToolsFilter,
  ToolsResponse,
  ToolUpdate,
  BulkStatusUpdate,
  BulkStatusResponse,
  BulkDeleteResponse,
  ExportFilters,
  Claim,
  Job,
  User,
  AuthToken,
  SetupStatus,
  AllSettings,
  ScoutType,
  ScoutTypeInfo
} from './types'

const API_BASE = '/api'
const TOKEN_KEY = 'glean_token'

// Token management
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

// API error class
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      ...headers,
      ...options?.headers,
    },
  })

  if (!response.ok) {
    if (response.status === 401) {
      clearToken()
      window.location.href = '/login'
    }
    throw new ApiError(response.status, `API Error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

async function fetchWithAuth(url: string, options?: RequestInit): Promise<Response> {
  const token = getToken()
  const headers: Record<string, string> = {}

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  return fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      ...headers,
      ...options?.headers,
    },
  })
}

// Auth
export async function getSetupStatus(): Promise<SetupStatus> {
  const response = await fetch(`${API_BASE}/auth/setup-status`)
  return response.json()
}

export async function login(username: string, password: string): Promise<AuthToken> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }))
    throw new ApiError(response.status, error.detail || 'Login failed')
  }

  const data = await response.json()
  setToken(data.access_token)
  return data
}

export async function register(
  username: string,
  email: string,
  password: string
): Promise<User> {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Registration failed' }))
    throw new ApiError(response.status, error.detail || 'Registration failed')
  }

  return response.json()
}

export async function getCurrentUser(): Promise<User> {
  return fetchJson<User>('/auth/me')
}

export async function logout(): Promise<void> {
  try {
    await fetchJson('/auth/logout', { method: 'POST' })
  } finally {
    clearToken()
  }
}

// Stats
export async function getStats(): Promise<PipelineStats> {
  return fetchJson<PipelineStats>('/stats')
}

// Tools
export async function getTools(filters?: ToolsFilter): Promise<ToolsResponse> {
  const params = new URLSearchParams()
  if (filters) {
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, String(value))
      }
    })
  }
  const queryString = params.toString()
  return fetchJson<ToolsResponse>(`/tools${queryString ? `?${queryString}` : ''}`)
}

export async function getTool(id: number): Promise<ToolDetail> {
  return fetchJson<ToolDetail>(`/tools/${id}`)
}

export async function updateTool(id: number, update: ToolUpdate): Promise<{ success: boolean; tool: Tool }> {
  return fetchJson<{ success: boolean; tool: Tool }>(`/tools/${id}`, {
    method: 'PUT',
    body: JSON.stringify(update),
  })
}

export async function deleteTool(id: number): Promise<{ success: boolean }> {
  return fetchJson<{ success: boolean }>(`/tools/${id}`, {
    method: 'DELETE',
  })
}

export async function updateToolStatus(
  id: number,
  status: 'approved' | 'rejected',
  reason?: string
): Promise<{ success: boolean }> {
  return fetchJson<{ success: boolean }>(`/tools/${id}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status, rejection_reason: reason }),
  })
}

export async function bulkUpdateStatus(update: BulkStatusUpdate): Promise<BulkStatusResponse> {
  return fetchJson<BulkStatusResponse>('/tools/bulk/status', {
    method: 'PUT',
    body: JSON.stringify(update),
  })
}

export async function bulkDeleteTools(toolIds: number[]): Promise<BulkDeleteResponse> {
  return fetchJson<BulkDeleteResponse>(`/tools/bulk?${toolIds.map(id => `tool_ids=${id}`).join('&')}`, {
    method: 'DELETE',
  })
}

export async function getToolClaims(id: number): Promise<{ claims: Claim[] }> {
  return fetchJson<{ claims: Claim[] }>(`/tools/${id}/claims`)
}

// Export functions
export function getExportUrl(
  type: 'tools' | 'claims' | 'all',
  format: 'json' | 'csv',
  filters?: ExportFilters
): string {
  const params = new URLSearchParams()
  if (filters) {
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, String(value))
      }
    })
  }
  const queryString = params.toString()
  const endpoint = type === 'all' ? '/export/all/json' : `/export/${type}/${format}`
  return `${API_BASE}${endpoint}${queryString ? `?${queryString}` : ''}`
}

export async function downloadExport(
  type: 'tools' | 'claims' | 'all',
  format: 'json' | 'csv',
  filters?: ExportFilters
): Promise<void> {
  const token = getToken()
  const url = getExportUrl(type, format, filters)

  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  if (!response.ok) {
    throw new ApiError(response.status, 'Export failed')
  }

  const blob = await response.blob()
  const contentDisposition = response.headers.get('Content-Disposition')
  const filename = contentDisposition
    ?.match(/filename=([^;]+)/)?.[1]
    ?.replace(/"/g, '') || `glean_export.${format}`

  // Download the file
  const downloadUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = downloadUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(downloadUrl)
}

// Jobs
export async function getJobs(): Promise<{ jobs: Job[] }> {
  return fetchJson<{ jobs: Job[] }>('/jobs')
}

export async function getScoutTypes(): Promise<{ scout_types: ScoutTypeInfo[] }> {
  return fetchJson<{ scout_types: ScoutTypeInfo[] }>('/jobs/scout-types')
}

export interface ScoutJobOptions {
  scout_type: ScoutType
  demo?: boolean
  limit?: number
  subreddits?: string[]
  queries?: string[]
  days_back?: number
  min_votes?: number
  results_per_query?: number
  feeds?: string[]
  max_age_days?: number
}

export interface AnalyzeJobOptions {
  mock?: boolean
  limit?: number
}

export interface CurateJobOptions {
  min_score?: number
  auto_merge?: boolean
}

export async function startScoutJob(
  options: ScoutJobOptions
): Promise<{ job_id: string; status: string; scout_type: ScoutType }> {
  return fetchJson<{ job_id: string; status: string; scout_type: ScoutType }>('/jobs/scout', {
    method: 'POST',
    body: JSON.stringify(options),
  })
}

export async function startAnalyzeJob(
  options?: AnalyzeJobOptions
): Promise<{ job_id: string; status: string }> {
  return fetchJson<{ job_id: string; status: string }>('/jobs/analyze', {
    method: 'POST',
    body: JSON.stringify(options || {}),
  })
}

export async function startCurateJob(
  options?: CurateJobOptions
): Promise<{ job_id: string; status: string }> {
  return fetchJson<{ job_id: string; status: string }>('/jobs/curate', {
    method: 'POST',
    body: JSON.stringify(options || {}),
  })
}

export async function startUpdateJob(): Promise<{ job_id: string; status: string }> {
  return fetchJson<{ job_id: string; status: string }>('/jobs/update', {
    method: 'POST',
    body: JSON.stringify({}),
  })
}

// Legacy function for backwards compatibility
export async function startJob(
  type: 'scout' | 'analyze' | 'curate' | 'update',
  options?: { demo?: boolean; scout_type?: ScoutType }
): Promise<{ job_id: string; status: string }> {
  if (type === 'scout') {
    return startScoutJob({ scout_type: options?.scout_type || 'reddit', demo: options?.demo })
  } else if (type === 'analyze') {
    return startAnalyzeJob({ mock: options?.demo })
  } else if (type === 'curate') {
    return startCurateJob()
  } else {
    return startUpdateJob()
  }
}

export async function cancelJob(id: string): Promise<void> {
  await fetchJson<void>(`/jobs/${id}`, { method: 'DELETE' })
}

// Reports
export async function getWeeklyReport(): Promise<string> {
  const response = await fetchWithAuth('/reports/weekly/raw')
  return response.text()
}

export async function getChangelog(): Promise<string> {
  const response = await fetchWithAuth('/reports/changelog/raw')
  return response.text()
}

export async function getToolsIndex(): Promise<string> {
  const response = await fetchWithAuth('/reports/index/raw')
  return response.text()
}

// Settings
export async function getSettings(): Promise<AllSettings> {
  return fetchJson<AllSettings>('/settings')
}

export async function updateSetting(
  category: string,
  key: string,
  value: string,
  isSecret: boolean = false
): Promise<{ success: boolean }> {
  return fetchJson<{ success: boolean }>(`/settings/${category}/${key}`, {
    method: 'PUT',
    body: JSON.stringify({ value, is_secret: isSecret }),
  })
}

export async function deleteSetting(
  category: string,
  key: string
): Promise<{ success: boolean }> {
  return fetchJson<{ success: boolean }>(`/settings/${category}/${key}`, {
    method: 'DELETE',
  })
}

export async function testSetting(
  category: string,
  key: string
): Promise<{ success: boolean; message: string }> {
  return fetchJson<{ success: boolean; message: string }>(
    `/settings/test/${category}/${key}`,
    { method: 'POST' }
  )
}

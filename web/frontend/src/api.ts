// API client functions

import type { PipelineStats, Tool, Claim, Job, User, AuthToken, SetupStatus } from './types'

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
export async function getTools(status?: string): Promise<{ tools: Tool[]; total: number }> {
  const params = status ? `?status=${status}` : ''
  return fetchJson<{ tools: Tool[]; total: number }>(`/tools${params}`)
}

export async function getTool(id: number): Promise<Tool> {
  return fetchJson<Tool>(`/tools/${id}`)
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

export async function getToolClaims(id: number): Promise<{ claims: Claim[] }> {
  return fetchJson<{ claims: Claim[] }>(`/tools/${id}/claims`)
}

// Jobs
export async function getJobs(): Promise<{ jobs: Job[] }> {
  return fetchJson<{ jobs: Job[] }>('/jobs')
}

export async function startJob(
  type: 'scout' | 'analyze' | 'curate' | 'update',
  options?: { demo?: boolean; source?: string }
): Promise<{ job_id: string; status: string }> {
  return fetchJson<{ job_id: string; status: string }>(`/jobs/${type}`, {
    method: 'POST',
    body: JSON.stringify(options || {}),
  })
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

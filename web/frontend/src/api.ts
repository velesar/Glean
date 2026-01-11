// API client functions

import type { PipelineStats, Tool, Claim, Job } from './types'

const API_BASE = '/api'

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`)
  }
  return response.json()
}

// Stats
export async function getStats(): Promise<PipelineStats> {
  return fetchJson<PipelineStats>('/stats')
}

// Tools
export async function getTools(status?: string): Promise<Tool[]> {
  const params = status ? `?status=${status}` : ''
  return fetchJson<Tool[]>(`/tools${params}`)
}

export async function getTool(id: number): Promise<Tool> {
  return fetchJson<Tool>(`/tools/${id}`)
}

export async function updateToolStatus(
  id: number,
  status: 'approved' | 'rejected',
  reason?: string
): Promise<Tool> {
  return fetchJson<Tool>(`/tools/${id}/status`, {
    method: 'PUT',
    body: JSON.stringify({ status, rejection_reason: reason }),
  })
}

export async function getToolClaims(id: number): Promise<Claim[]> {
  return fetchJson<Claim[]>(`/tools/${id}/claims`)
}

// Jobs
export async function getJobs(): Promise<Job[]> {
  return fetchJson<Job[]>('/jobs')
}

export async function startJob(
  type: 'scout' | 'analyze' | 'curate' | 'update',
  options?: { demo?: boolean; source?: string }
): Promise<Job> {
  return fetchJson<Job>(`/jobs/${type}`, {
    method: 'POST',
    body: JSON.stringify(options || {}),
  })
}

export async function cancelJob(id: string): Promise<void> {
  await fetchJson<void>(`/jobs/${id}`, { method: 'DELETE' })
}

// Reports
export async function getWeeklyReport(): Promise<string> {
  const response = await fetch(`${API_BASE}/reports/weekly`)
  return response.text()
}

export async function getChangelog(): Promise<string> {
  const response = await fetch(`${API_BASE}/reports/changelog`)
  return response.text()
}

export async function getToolsIndex(): Promise<string> {
  const response = await fetch(`${API_BASE}/reports/index`)
  return response.text()
}

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../api'
import type { Job, ScoutType } from '../types'

// Polling intervals
const ACTIVE_POLL_INTERVAL = 3000 // 3s when jobs are running
const IDLE_POLL_INTERVAL = 30000 // 30s when no active jobs

// Helper to check if any jobs are active
function hasActiveJobs(jobs: Job[] | undefined): boolean {
  if (!jobs) return false
  return jobs.some((job) => job.status === 'running' || job.status === 'pending')
}

export function useStats(hasActiveJobsFlag?: boolean) {
  return useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
    // Poll more frequently when jobs are active, otherwise slower
    refetchInterval: hasActiveJobsFlag ? ACTIVE_POLL_INTERVAL : IDLE_POLL_INTERVAL,
  })
}

export function useTools(status?: string) {
  return useQuery({
    queryKey: ['tools', status],
    queryFn: () => api.getTools(status ? { status } : undefined),
  })
}

export function useTool(id: number) {
  return useQuery({
    queryKey: ['tool', id],
    queryFn: () => api.getTool(id),
    enabled: !!id,
  })
}

export function useToolClaims(id: number) {
  return useQuery({
    queryKey: ['tool', id, 'claims'],
    queryFn: () => api.getToolClaims(id),
    enabled: !!id,
  })
}

export function useGroupedClaims(id: number) {
  return useQuery({
    queryKey: ['tool', id, 'claims', 'grouped'],
    queryFn: () => api.getGroupedClaims(id),
    enabled: !!id,
  })
}

export function useUpdateToolStatus() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      status,
      reason,
    }: {
      id: number
      status: 'approved' | 'rejected'
      reason?: string
    }) => api.updateToolStatus(id, status, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tools'] })
      queryClient.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

export function useJobs() {
  return useQuery({
    queryKey: ['jobs'],
    queryFn: api.getJobs,
    // Dynamic polling: fast when jobs are active, slow when idle
    refetchInterval: (query) => {
      const jobs = query.state.data?.jobs
      return hasActiveJobs(jobs) ? ACTIVE_POLL_INTERVAL : IDLE_POLL_INTERVAL
    },
  })
}

export function useScoutTypes() {
  return useQuery({
    queryKey: ['scout-types'],
    queryFn: api.getScoutTypes,
    staleTime: 60000, // Cache for 1 minute
  })
}

export function useStartScoutJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (options: api.ScoutJobOptions) => api.startScoutJob(options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}

export function useStartAnalyzeJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (options?: api.AnalyzeJobOptions) => api.startAnalyzeJob(options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}

export function useStartCurateJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (options?: api.CurateJobOptions) => api.startCurateJob(options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}

export function useStartUpdateJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.startUpdateJob(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}

// Legacy hook for backwards compatibility
export function useStartJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      type,
      options,
    }: {
      type: 'scout' | 'analyze' | 'curate' | 'update'
      options?: { demo?: boolean; scout_type?: ScoutType }
    }) => api.startJob(type, options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}

export function useCancelJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.cancelJob(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}

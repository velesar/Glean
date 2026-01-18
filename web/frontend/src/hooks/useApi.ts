import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../api'
import type { ScoutType } from '../types'

export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: api.getStats,
    refetchInterval: 10000,
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
    refetchInterval: 5000, // 5 seconds - balance between responsiveness and stability
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

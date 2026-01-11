import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import * as api from '../api'

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
    queryFn: () => api.getTools(status),
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
    refetchInterval: 5000,
  })
}

export function useStartJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      type,
      options,
    }: {
      type: 'scout' | 'analyze' | 'curate' | 'update'
      options?: { demo?: boolean; source?: string }
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

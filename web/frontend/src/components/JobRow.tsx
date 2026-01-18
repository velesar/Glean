import { useState } from 'react'
import type { Job, LogEntry } from '../types'

interface JobRowProps {
  job: Job
  showExpand?: boolean
  // Controlled expansion props - when provided, parent manages state
  isExpanded?: boolean
  onToggleExpand?: () => void
}

function LogLevelIcon({ level }: { level: LogEntry['level'] }) {
  switch (level) {
    case 'success':
      return (
        <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      )
    case 'error':
      return (
        <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      )
    case 'warning':
      return (
        <svg className="w-4 h-4 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      )
    default:
      return (
        <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
  }
}

function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString()
}

export function JobRow({
  job,
  showExpand = true,
  isExpanded: controlledExpanded,
  onToggleExpand,
}: JobRowProps) {
  // Support both controlled (parent manages state) and uncontrolled (internal state) modes
  const [internalExpanded, setInternalExpanded] = useState(false)
  const isControlled = controlledExpanded !== undefined
  const isExpanded = isControlled ? controlledExpanded : internalExpanded
  const handleToggle = isControlled ? onToggleExpand : () => setInternalExpanded(!internalExpanded)

  const hasLogs = job.logs && job.logs.length > 0

  const statusColor = {
    completed: 'bg-green-500',
    failed: 'bg-red-500',
    running: 'bg-blue-500',
    pending: 'bg-gray-400',
    cancelled: 'bg-gray-400',
  }[job.status]

  return (
    <div className="border-b border-gray-100 last:border-b-0">
      <div
        className={`p-4 flex items-center justify-between ${hasLogs && showExpand ? 'cursor-pointer hover:bg-gray-50' : ''}`}
        onClick={() => hasLogs && showExpand && handleToggle?.()}
      >
        <div className="flex items-center gap-3">
          {hasLogs && showExpand && (
            <svg
              className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          )}
          <span className={`w-2 h-2 rounded-full ${statusColor}`} />
          <span className="font-medium text-gray-900 capitalize">{job.type}</span>
          {job.scout_type && job.scout_type !== 'all' && (
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
              {job.scout_type}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          {job.status === 'running' && (
            <div className="flex items-center gap-2">
              <div className="w-24 bg-gray-200 rounded-full h-1.5">
                <div
                  className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${job.progress}%` }}
                />
              </div>
              <span className="text-xs text-blue-600">{job.progress}%</span>
            </div>
          )}
          {job.message && (
            <span className="text-sm text-gray-500 max-w-xs truncate">{job.message}</span>
          )}
          <span className="text-sm text-gray-400">
            {job.completed_at
              ? formatTime(job.completed_at)
              : job.started_at
                ? formatTime(job.started_at)
                : ''}
          </span>
        </div>
      </div>

      {isExpanded && hasLogs && (
        <div className="px-4 pb-4">
          <div className="bg-gray-900 rounded-lg p-3 text-sm font-mono overflow-x-auto max-h-64 overflow-y-auto">
            {job.logs.map((log, index) => (
              <div key={index} className="flex items-start gap-2 py-1">
                <span className="text-gray-500 text-xs whitespace-nowrap">
                  {formatTime(log.timestamp)}
                </span>
                <LogLevelIcon level={log.level} />
                <span
                  className={`${
                    log.level === 'error'
                      ? 'text-red-400'
                      : log.level === 'warning'
                        ? 'text-yellow-400'
                        : log.level === 'success'
                          ? 'text-green-400'
                          : 'text-gray-300'
                  }`}
                >
                  {log.message}
                </span>
              </div>
            ))}
          </div>

          {job.result && (
            <div className="mt-3 bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500 mb-2 font-medium">Result</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(job.result).map(([key, value]) => (
                  <div key={key} className="text-sm">
                    <span className="text-gray-500">{key.replace(/_/g, ' ')}: </span>
                    <span className="font-medium text-gray-900">{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {job.error && (
            <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3">
              <div className="text-xs text-red-500 mb-1 font-medium">Error</div>
              <div className="text-sm text-red-700">{job.error}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

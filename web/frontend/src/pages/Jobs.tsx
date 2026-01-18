import { useState } from 'react'
import {
  useJobs,
  useScoutTypes,
  useStartScoutJob,
  useStartAnalyzeJob,
  useStartCurateJob,
  useStartUpdateJob,
  useCancelJob,
} from '../hooks/useApi'
import type { ScoutType, Job } from '../types'

// Default demo mode from environment variable (defaults to true for local dev)
const DEFAULT_DEMO_MODE = import.meta.env.VITE_DEMO_MODE_DEFAULT !== 'false'

// Scout type icons (using simple text/emoji representations)
const SCOUT_ICONS: Record<string, string> = {
  reddit: '📱',
  twitter: '🐦',
  producthunt: '🚀',
  web: '🔍',
  rss: '📡',
  all: '🌐',
  globe: '🌐',
  search: '🔍',
}

function ScoutCard({
  id,
  name,
  description,
  icon,
  requires_api,
  onRun,
  isPending,
}: {
  id: ScoutType
  name: string
  description: string
  icon: string
  requires_api: boolean
  onRun: (scoutType: ScoutType, demo: boolean) => void
  isPending: boolean
}) {
  const [demoMode, setDemoMode] = useState(DEFAULT_DEMO_MODE)

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{SCOUT_ICONS[icon] || SCOUT_ICONS[id] || '📋'}</span>
          <div>
            <h3 className="font-semibold text-gray-900">{name}</h3>
            <p className="text-sm text-gray-500">{description}</p>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between mt-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={demoMode}
            onChange={(e) => setDemoMode(e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-gray-600">Demo mode</span>
          {requires_api && !demoMode && (
            <span className="text-xs text-amber-600">(requires API key)</span>
          )}
        </label>

        <button
          onClick={() => onRun(id, demoMode)}
          disabled={isPending}
          className="px-3 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          Run
        </button>
      </div>
    </div>
  )
}

function JobCard({ job, onCancel }: { job: Job; onCancel: () => void }) {
  const statusColors: Record<string, string> = {
    pending: 'bg-gray-100 text-gray-700',
    running: 'bg-blue-100 text-blue-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    cancelled: 'bg-gray-100 text-gray-500',
  }

  const statusDots: Record<string, string> = {
    pending: 'bg-gray-400',
    running: 'bg-blue-500 animate-pulse',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
    cancelled: 'bg-gray-400',
  }

  const jobLabel =
    job.type === 'scout' && job.scout_type
      ? `Scout: ${job.scout_type}`
      : job.type.charAt(0).toUpperCase() + job.type.slice(1)

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <span className={`w-2 h-2 rounded-full ${statusDots[job.status]}`} />
          <span className="font-medium text-gray-900">{jobLabel}</span>
          <span
            className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[job.status]}`}
          >
            {job.status}
          </span>
        </div>
        <div className="flex items-center gap-3">
          {job.status === 'running' && (
            <>
              <span className="text-sm text-blue-600 font-medium">{job.progress}%</span>
              <button
                onClick={onCancel}
                className="px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded transition-colors"
              >
                Cancel
              </button>
            </>
          )}
          <span className="text-xs text-gray-400">
            {job.started_at && new Date(job.started_at).toLocaleTimeString()}
          </span>
        </div>
      </div>

      {job.status === 'running' && (
        <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
          <div
            className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${job.progress}%` }}
          />
        </div>
      )}

      {job.message && (
        <p className={`text-sm mt-2 ${job.status === 'failed' ? 'text-red-600' : 'text-gray-500'}`}>
          {job.message}
        </p>
      )}

      {job.error && job.status === 'failed' && (
        <p className="text-sm text-red-600 mt-1 font-mono bg-red-50 p-2 rounded">{job.error}</p>
      )}

      {job.result && job.status === 'completed' && (
        <div className="text-sm text-gray-500 mt-2 flex gap-4">
          {Object.entries(job.result).map(([key, value]) => (
            <span key={key}>
              <span className="text-gray-400">{key.replace('_', ' ')}:</span>{' '}
              <span className="font-medium text-gray-700">{String(value)}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export function Jobs() {
  const { data: jobsData, isLoading: jobsLoading } = useJobs()
  const { data: scoutTypesData, isLoading: scoutTypesLoading } = useScoutTypes()

  const startScoutJob = useStartScoutJob()
  const startAnalyzeJob = useStartAnalyzeJob()
  const startCurateJob = useStartCurateJob()
  const startUpdateJob = useStartUpdateJob()
  const cancelJob = useCancelJob()

  const jobs = jobsData?.jobs || []
  const scoutTypes = scoutTypesData?.scout_types || []

  const runningJobs = jobs.filter((j) => j.status === 'running' || j.status === 'pending')
  const recentJobs = jobs.filter((j) => j.status !== 'running' && j.status !== 'pending')

  const handleRunScout = (scoutType: ScoutType, demo: boolean) => {
    startScoutJob.mutate({ scout_type: scoutType, demo })
  }

  const isAnyJobPending =
    startScoutJob.isPending ||
    startAnalyzeJob.isPending ||
    startCurateJob.isPending ||
    startUpdateJob.isPending

  if (jobsLoading || scoutTypesLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
      </div>

      {/* Scout Sources */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Scout Sources</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {scoutTypes.map((scout) => (
            <ScoutCard
              key={scout.id}
              {...scout}
              onRun={handleRunScout}
              isPending={isAnyJobPending}
            />
          ))}
        </div>
      </section>

      {/* Pipeline Actions */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Pipeline Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">🔬</span>
              <div>
                <h3 className="font-semibold text-gray-900">Analyze</h3>
                <p className="text-sm text-gray-500">Extract tools and claims from discoveries</p>
              </div>
            </div>
            <div className="flex items-center justify-between mt-4">
              <span className="text-xs text-gray-400">Uses Claude API (or mock mode)</span>
              <button
                onClick={() => startAnalyzeJob.mutate({ mock: true, limit: 10 })}
                disabled={isAnyJobPending}
                className="px-3 py-1.5 bg-purple-600 text-white text-sm font-medium rounded-md hover:bg-purple-700 disabled:opacity-50 transition-colors"
              >
                Run
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">📊</span>
              <div>
                <h3 className="font-semibold text-gray-900">Curate</h3>
                <p className="text-sm text-gray-500">Score and rank tools for review</p>
              </div>
            </div>
            <div className="flex items-center justify-between mt-4">
              <span className="text-xs text-gray-400">Moves tools to review queue</span>
              <button
                onClick={() => startCurateJob.mutate({})}
                disabled={isAnyJobPending}
                className="px-3 py-1.5 bg-yellow-600 text-white text-sm font-medium rounded-md hover:bg-yellow-700 disabled:opacity-50 transition-colors"
              >
                Run
              </button>
            </div>
          </div>

          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">🔄</span>
              <div>
                <h3 className="font-semibold text-gray-900">Update Check</h3>
                <p className="text-sm text-gray-500">Check approved tools for changes</p>
              </div>
            </div>
            <div className="flex items-center justify-between mt-4">
              <span className="text-xs text-gray-400">Detects pricing/feature changes</span>
              <button
                onClick={() => startUpdateJob.mutate()}
                disabled={isAnyJobPending}
                className="px-3 py-1.5 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                Run
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Active Jobs */}
      {runningJobs.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Active Jobs ({runningJobs.length})
          </h2>
          <div className="space-y-3">
            {runningJobs.map((job) => (
              <JobCard key={job.id} job={job} onCancel={() => cancelJob.mutate(job.id)} />
            ))}
          </div>
        </section>
      )}

      {/* Recent Jobs */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Recent Jobs ({recentJobs.length})
        </h2>
        {recentJobs.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-500">
            No jobs yet. Run a scout to get started!
          </div>
        ) : (
          <div className="space-y-3">
            {recentJobs.slice(0, 10).map((job) => (
              <JobCard key={job.id} job={job} onCancel={() => cancelJob.mutate(job.id)} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

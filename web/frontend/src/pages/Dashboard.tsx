import { useMemo, useState, useCallback } from 'react'
import { useStats, useJobs, useStartJob } from '../hooks/useApi'
import { StatCard } from '../components/StatCard'
import { JobRow } from '../components/JobRow'

export function Dashboard() {
  const { data: jobsData } = useJobs()
  const startJob = useStartJob()

  // Track expanded job IDs to persist state across refetches
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set())

  const toggleExpanded = useCallback((jobId: string) => {
    setExpandedJobs((prev) => {
      const next = new Set(prev)
      if (next.has(jobId)) {
        next.delete(jobId)
      } else {
        next.add(jobId)
      }
      return next
    })
  }, [])

  // Memoize job lists to prevent unnecessary re-renders
  const jobs = useMemo(() => jobsData?.jobs || [], [jobsData?.jobs])

  // Check if any jobs are active (running or pending)
  const hasActiveJobs = useMemo(
    () => jobs.some((j) => j.status === 'running' || j.status === 'pending'),
    [jobs]
  )

  // Stats polling is coordinated with job activity
  const { data: stats, isLoading: statsLoading } = useStats(hasActiveJobs)

  const runningJobs = useMemo(
    () => jobs.filter((j) => j.status === 'running' || j.status === 'pending'),
    [jobs]
  )

  const recentJobs = useMemo(
    () => jobs.filter((j) => j.status !== 'running' && j.status !== 'pending').slice(0, 5),
    [jobs]
  )

  const handleRunScout = () => {
    startJob.mutate({ type: 'scout' })
  }

  const handleRunAnalyze = () => {
    startJob.mutate({ type: 'analyze' })
  }

  const handleRunCurate = () => {
    startJob.mutate({ type: 'curate' })
  }

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <div className="flex gap-2">
          <button
            onClick={handleRunScout}
            disabled={startJob.isPending}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Run Scout
          </button>
          <button
            onClick={handleRunAnalyze}
            disabled={startJob.isPending}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Run Analyzer
          </button>
          <button
            onClick={handleRunCurate}
            disabled={startJob.isPending}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Run Curator
          </button>
        </div>
      </div>

      {/* Pipeline Stats */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Pipeline Status
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard label="Inbox" value={stats?.inbox || 0} color="gray" />
          <StatCard
            label="Analyzing"
            value={stats?.analyzing || 0}
            color="blue"
          />
          <StatCard label="Review" value={stats?.review || 0} color="yellow" />
          <StatCard
            label="Approved"
            value={stats?.approved || 0}
            color="green"
          />
          <StatCard label="Rejected" value={stats?.rejected || 0} color="red" />
        </div>
      </section>

      {/* Active Jobs */}
      {runningJobs.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Active Jobs
          </h2>
          <div className="space-y-3">
            {runningJobs.map((job) => (
              <div
                key={job.id}
                className="bg-white rounded-lg border border-gray-200 p-4"
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="font-medium text-gray-900 capitalize">
                    {job.type}
                  </span>
                  <span className="text-sm text-blue-600">{job.progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${job.progress}%` }}
                  />
                </div>
                {job.message && (
                  <p className="text-sm text-gray-500 mt-2">{job.message}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Recent Jobs */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Recent Jobs
        </h2>
        {recentJobs.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-4 text-gray-500 text-center">
            No recent jobs
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200">
            {recentJobs.map((job) => (
              <JobRow
                key={job.id}
                job={job}
                isExpanded={expandedJobs.has(job.id)}
                onToggleExpand={() => toggleExpanded(job.id)}
              />
            ))}
          </div>
        )}
      </section>

      {/* Quick Stats */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Quick Stats
        </h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-900">
              {stats?.total_claims || 0}
            </div>
            <div className="text-sm text-gray-500">Total Claims</div>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="text-2xl font-bold text-gray-900">
              {stats?.recent_discoveries || 0}
            </div>
            <div className="text-sm text-gray-500">Recent Discoveries</div>
          </div>
        </div>
      </section>
    </div>
  )
}

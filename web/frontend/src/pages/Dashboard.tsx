import { useStats, useJobs, useStartJob } from '../hooks/useApi'
import { StatCard } from '../components/StatCard'

export function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useStats()
  const { data: jobsData } = useJobs()
  const startJob = useStartJob()

  const jobs = jobsData?.jobs || []
  const runningJobs = jobs.filter((j) => j.status === 'running')
  const recentJobs = jobs.filter((j) => j.status !== 'running').slice(0, 5)

  const handleRunScout = () => {
    startJob.mutate({ type: 'scout', options: { demo: true } })
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

      {/* Running Jobs */}
      {runningJobs.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Running Jobs
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
          <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
            {recentJobs.map((job) => (
              <div
                key={job.id}
                className="p-4 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      job.status === 'completed'
                        ? 'bg-green-500'
                        : job.status === 'failed'
                          ? 'bg-red-500'
                          : 'bg-gray-400'
                    }`}
                  />
                  <span className="font-medium text-gray-900 capitalize">
                    {job.type}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  {job.message && (
                    <span className="text-sm text-gray-500">{job.message}</span>
                  )}
                  <span className="text-sm text-gray-400">
                    {job.completed_at
                      ? new Date(job.completed_at).toLocaleTimeString()
                      : ''}
                  </span>
                </div>
              </div>
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

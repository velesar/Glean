import { useJobs, useStartJob, useCancelJob } from '../hooks/useApi'

export function Jobs() {
  const { data: jobsData, isLoading } = useJobs()
  const startJob = useStartJob()
  const cancelJob = useCancelJob()

  const jobs = jobsData?.jobs || []
  const runningJobs = jobs.filter((j) => j.status === 'running')
  const completedJobs = jobs.filter((j) => j.status === 'completed')
  const failedJobs = jobs.filter((j) => j.status === 'failed')

  const handleStartJob = (type: 'scout' | 'analyze' | 'curate' | 'update') => {
    const options = type === 'scout' ? { demo: true } : undefined
    startJob.mutate({ type, options })
  }

  if (isLoading) {
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

      {/* Start Job Buttons */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Start New Job</h2>
        <div className="flex gap-3 flex-wrap">
          <button
            onClick={() => handleStartJob('scout')}
            disabled={startJob.isPending}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Scout (Demo)
          </button>
          <button
            onClick={() => handleStartJob('analyze')}
            disabled={startJob.isPending}
            className="px-4 py-2 bg-purple-600 text-white text-sm font-medium rounded-md hover:bg-purple-700 disabled:opacity-50 transition-colors"
          >
            Analyze
          </button>
          <button
            onClick={() => handleStartJob('curate')}
            disabled={startJob.isPending}
            className="px-4 py-2 bg-yellow-600 text-white text-sm font-medium rounded-md hover:bg-yellow-700 disabled:opacity-50 transition-colors"
          >
            Curate
          </button>
          <button
            onClick={() => handleStartJob('update')}
            disabled={startJob.isPending}
            className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            Update Check
          </button>
        </div>
      </section>

      {/* Running Jobs */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Running Jobs ({runningJobs.length})
        </h2>
        {runningJobs.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-4 text-gray-500 text-center">
            No jobs currently running
          </div>
        ) : (
          <div className="space-y-3">
            {runningJobs.map((job) => (
              <div
                key={job.id}
                className="bg-white rounded-lg border border-gray-200 p-4"
              >
                <div className="flex justify-between items-center mb-2">
                  <div>
                    <span className="font-medium text-gray-900 capitalize">
                      {job.type}
                    </span>
                    <span className="text-sm text-gray-500 ml-2">
                      Started: {new Date(job.started_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-blue-600 font-medium">
                      {job.progress}%
                    </span>
                    <button
                      onClick={() => cancelJob.mutate(job.id)}
                      className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
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
        )}
      </section>

      {/* Completed Jobs */}
      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Completed Jobs ({completedJobs.length})
        </h2>
        {completedJobs.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-4 text-gray-500 text-center">
            No completed jobs
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
            {completedJobs.slice(0, 10).map((job) => (
              <div key={job.id} className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="w-2 h-2 rounded-full bg-green-500" />
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
                      ? new Date(job.completed_at).toLocaleString()
                      : ''}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Failed Jobs */}
      {failedJobs.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Failed Jobs ({failedJobs.length})
          </h2>
          <div className="bg-white rounded-lg border border-red-200 divide-y divide-red-100">
            {failedJobs.map((job) => (
              <div key={job.id} className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="w-2 h-2 rounded-full bg-red-500" />
                  <span className="font-medium text-gray-900 capitalize">
                    {job.type}
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-red-600">{job.message}</span>
                  <span className="text-sm text-gray-400">
                    {job.completed_at
                      ? new Date(job.completed_at).toLocaleString()
                      : ''}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

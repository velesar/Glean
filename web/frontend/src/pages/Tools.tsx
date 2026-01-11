import { useState } from 'react'
import { useTools } from '../hooks/useApi'
import { ToolCard } from '../components/ToolCard'

type StatusFilter = 'all' | 'inbox' | 'analyzing' | 'review' | 'approved' | 'rejected'

export function Tools() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const { data: tools, isLoading } = useTools(
    statusFilter === 'all' ? undefined : statusFilter
  )

  const filters: { value: StatusFilter; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'inbox', label: 'Inbox' },
    { value: 'analyzing', label: 'Analyzing' },
    { value: 'review', label: 'Review' },
    { value: 'approved', label: 'Approved' },
    { value: 'rejected', label: 'Rejected' },
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Tools</h1>
        <span className="text-sm text-gray-500">{tools?.length || 0} tools</span>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {filters.map((filter) => (
          <button
            key={filter.value}
            onClick={() => setStatusFilter(filter.value)}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              statusFilter === filter.value
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {/* Tools Grid */}
      {!tools || tools.length === 0 ? (
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
          <p className="text-gray-500">
            No tools found{statusFilter !== 'all' ? ` with status "${statusFilter}"` : ''}.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {tools.map((tool) => (
            <ToolCard key={tool.id} tool={tool} />
          ))}
        </div>
      )}
    </div>
  )
}

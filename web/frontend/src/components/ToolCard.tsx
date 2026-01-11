import type { Tool } from '../types'

interface ToolCardProps {
  tool: Tool
  onApprove?: () => void
  onReject?: () => void
  onSkip?: () => void
  showActions?: boolean
}

const statusColors = {
  inbox: 'bg-gray-100 text-gray-700',
  analyzing: 'bg-blue-100 text-blue-700',
  review: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
}

export function ToolCard({
  tool,
  onApprove,
  onReject,
  onSkip,
  showActions = false,
}: ToolCardProps) {
  const scorePercent = tool.relevance_score
    ? Math.round(tool.relevance_score * 100)
    : null

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4">
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{tool.name}</h3>
          {tool.url && (
            <a
              href={tool.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline"
            >
              {tool.url}
            </a>
          )}
        </div>
        <div className="flex items-center gap-2">
          {scorePercent !== null && (
            <span className="text-sm font-medium text-gray-600">
              Score: {scorePercent}%
            </span>
          )}
          <span
            className={`px-2 py-1 text-xs font-medium rounded ${statusColors[tool.status]}`}
          >
            {tool.status}
          </span>
        </div>
      </div>

      {tool.description && (
        <p className="text-gray-600 text-sm mt-2">{tool.description}</p>
      )}

      {tool.category && (
        <div className="mt-2">
          <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
            {tool.category}
          </span>
        </div>
      )}

      {showActions && (
        <div className="flex gap-2 mt-4 pt-4 border-t border-gray-100">
          <button
            onClick={onApprove}
            className="flex-1 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 transition-colors"
          >
            Approve
          </button>
          <button
            onClick={onReject}
            className="flex-1 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 transition-colors"
          >
            Reject
          </button>
          <button
            onClick={onSkip}
            className="px-4 py-2 bg-gray-100 text-gray-700 text-sm font-medium rounded-md hover:bg-gray-200 transition-colors"
          >
            Skip
          </button>
        </div>
      )}
    </div>
  )
}

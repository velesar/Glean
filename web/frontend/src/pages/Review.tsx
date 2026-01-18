import { useState } from 'react'
import { useTools, useUpdateToolStatus, useGroupedClaims } from '../hooks/useApi'
import { ReviewToolCard } from '../components/ReviewToolCard'
import type { Tool } from '../types'

export function Review() {
  const { data, isLoading } = useTools('review')
  const updateStatus = useUpdateToolStatus()
  const [currentIndex, setCurrentIndex] = useState(0)
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [showRejectModal, setShowRejectModal] = useState(false)

  const tools = data?.tools || []
  const currentTool = tools[currentIndex]

  // Fetch grouped claims for current tool
  const { data: groupedClaims, isLoading: isLoadingClaims } = useGroupedClaims(
    currentTool?.id || 0
  )

  const handleApprove = (tool: Tool) => {
    updateStatus.mutate(
      { id: tool.id, status: 'approved' },
      {
        onSuccess: () => {
          moveToNext()
        },
      }
    )
  }

  const handleReject = (tool: Tool) => {
    setSelectedTool(tool)
    setShowRejectModal(true)
  }

  const confirmReject = () => {
    if (selectedTool) {
      updateStatus.mutate(
        { id: selectedTool.id, status: 'rejected', reason: rejectReason },
        {
          onSuccess: () => {
            setShowRejectModal(false)
            setRejectReason('')
            setSelectedTool(null)
            moveToNext()
          },
        }
      )
    }
  }

  const moveToNext = () => {
    if (currentIndex < tools.length - 1) {
      setCurrentIndex(currentIndex + 1)
    }
  }

  const handleSkip = () => {
    moveToNext()
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (tools.length === 0) {
    return (
      <div className="text-center py-12">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Review Queue</h1>
        <div className="bg-white rounded-lg border border-gray-200 p-8">
          <p className="text-gray-500">
            No tools pending review. Run the pipeline to discover new tools.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Review Queue</h1>
        <span className="text-sm text-gray-500">
          {currentIndex + 1} of {tools.length}
        </span>
      </div>

      {/* Current Tool Card with Claims */}
      {currentTool && (
        <ReviewToolCard
          tool={currentTool}
          groupedClaims={groupedClaims}
          isLoadingClaims={isLoadingClaims}
          onApprove={() => handleApprove(currentTool)}
          onReject={() => handleReject(currentTool)}
          onSkip={handleSkip}
        />
      )}

      {/* All Queue Items */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-4 py-3 border-b border-gray-100">
          <h3 className="font-semibold text-gray-900">All Items in Queue</h3>
        </div>
        <div className="divide-y divide-gray-100 max-h-64 overflow-y-auto">
          {tools.map((tool, index) => (
            <button
              key={tool.id}
              onClick={() => setCurrentIndex(index)}
              className={`w-full px-4 py-3 text-left hover:bg-gray-50 transition-colors ${
                index === currentIndex ? 'bg-blue-50' : ''
              }`}
            >
              <div className="flex justify-between items-center">
                <span className="font-medium text-gray-900">{tool.name}</span>
                <span className="text-sm text-gray-500">
                  {tool.relevance_score
                    ? `${Math.round(tool.relevance_score * 100)}%`
                    : '-'}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Reject Tool
            </h3>
            <p className="text-gray-600 mb-4">
              Rejecting: <strong>{selectedTool?.name}</strong>
            </p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="Reason for rejection (optional)"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
              rows={3}
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => {
                  setShowRejectModal(false)
                  setRejectReason('')
                }}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmReject}
                disabled={updateStatus.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                Reject
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

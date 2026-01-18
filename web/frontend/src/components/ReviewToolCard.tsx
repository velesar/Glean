import type { Tool, GroupedClaimsResponse } from '../types'
import { CollapsibleSection } from './CollapsibleSection'
import { ClaimList } from './ClaimList'
import { AudienceDisplay } from './AudienceDisplay'

interface ReviewToolCardProps {
  tool: Tool
  groupedClaims?: GroupedClaimsResponse
  isLoadingClaims?: boolean
  onApprove?: () => void
  onReject?: () => void
  onSkip?: () => void
}

const statusColors = {
  inbox: 'bg-gray-100 text-gray-700',
  analyzing: 'bg-blue-100 text-blue-700',
  review: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
}

export function ReviewToolCard({
  tool,
  groupedClaims,
  isLoadingClaims,
  onApprove,
  onReject,
  onSkip,
}: ReviewToolCardProps) {
  const scorePercent = tool.relevance_score
    ? Math.round(tool.relevance_score * 100)
    : null

  const features = groupedClaims?.features || []
  const useCases = groupedClaims?.use_cases || []
  const pricing = groupedClaims?.pricing || []
  const audience = groupedClaims?.audience || []
  const integrations = groupedClaims?.integrations || []
  const limitations = groupedClaims?.limitations || []
  const comparisons = groupedClaims?.comparisons || []

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-100">
        <div className="flex justify-between items-start">
          <div className="flex-1">
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
            {tool.category && (
              <div className="mt-2">
                <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
                  {tool.category}
                </span>
              </div>
            )}
          </div>
          <div className="flex flex-col items-end gap-2">
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
            {/* Action buttons */}
            <div className="flex gap-2">
              <button
                onClick={onApprove}
                className="px-3 py-1.5 bg-green-600 text-white text-sm font-medium rounded hover:bg-green-700 transition-colors"
              >
                Approve
              </button>
              <button
                onClick={onSkip}
                className="px-3 py-1.5 bg-gray-100 text-gray-700 text-sm font-medium rounded hover:bg-gray-200 transition-colors"
              >
                Skip
              </button>
              <button
                onClick={onReject}
                className="px-3 py-1.5 bg-red-600 text-white text-sm font-medium rounded hover:bg-red-700 transition-colors"
              >
                Reject
              </button>
            </div>
          </div>
        </div>

        {/* Description */}
        {tool.description && (
          <p className="text-gray-600 text-sm mt-3">{tool.description}</p>
        )}
      </div>

      {/* Claims sections */}
      {isLoadingClaims ? (
        <div className="p-4 text-center text-gray-500">
          Loading claims...
        </div>
      ) : (
        <div className="divide-y divide-gray-100">
          {/* What It Does (Features) - always expanded */}
          <CollapsibleSection
            title="What It Does"
            count={features.length}
            defaultExpanded={true}
          >
            <ClaimList
              claims={features}
              emptyMessage="No features extracted yet"
            />
          </CollapsibleSection>

          {/* Use Cases - always expanded */}
          <CollapsibleSection
            title="Use Cases"
            count={useCases.length}
            defaultExpanded={true}
          >
            <ClaimList
              claims={useCases}
              emptyMessage="No use cases identified"
            />
          </CollapsibleSection>

          {/* Pricing - always expanded */}
          <CollapsibleSection
            title="Pricing"
            count={pricing.length}
            defaultExpanded={true}
          >
            <ClaimList
              claims={pricing}
              emptyMessage="No pricing information"
            />
          </CollapsibleSection>

          {/* Target Audience - always expanded */}
          <CollapsibleSection
            title="Target Audience"
            count={audience.length}
            defaultExpanded={true}
          >
            <AudienceDisplay claims={audience} />
          </CollapsibleSection>

          {/* Integrations - collapsed by default */}
          <CollapsibleSection
            title="Integrations"
            count={integrations.length}
            defaultExpanded={false}
          >
            <ClaimList
              claims={integrations}
              emptyMessage="No integrations mentioned"
            />
          </CollapsibleSection>

          {/* Limitations - collapsed by default */}
          <CollapsibleSection
            title="Limitations"
            count={limitations.length}
            defaultExpanded={false}
          >
            <ClaimList
              claims={limitations}
              emptyMessage="No limitations identified"
            />
          </CollapsibleSection>

          {/* Comparisons - collapsed by default */}
          <CollapsibleSection
            title="Comparisons"
            count={comparisons.length}
            defaultExpanded={false}
          >
            <ClaimList
              claims={comparisons}
              emptyMessage="No comparisons found"
            />
          </CollapsibleSection>
        </div>
      )}
    </div>
  )
}

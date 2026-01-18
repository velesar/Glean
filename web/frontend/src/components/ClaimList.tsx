import type { GroupedClaim } from '../types'

interface ClaimListProps {
  claims: GroupedClaim[]
  emptyMessage?: string
}

function ConfidenceIndicator({ confidence }: { confidence: number }) {
  const percent = Math.round(confidence * 100)
  const color = confidence >= 0.7
    ? 'text-green-600'
    : confidence >= 0.4
      ? 'text-yellow-600'
      : 'text-gray-400'

  return (
    <span className={`text-xs ${color}`} title={`Confidence: ${percent}%`}>
      ({percent}%)
    </span>
  )
}

export function ClaimList({ claims, emptyMessage = 'No claims found' }: ClaimListProps) {
  if (claims.length === 0) {
    return <p className="text-sm text-gray-500 italic">{emptyMessage}</p>
  }

  return (
    <ul className="space-y-2">
      {claims.map((claim) => (
        <li key={claim.id} className="flex items-start gap-2 text-sm">
          <span className="text-gray-400 mt-0.5">&bull;</span>
          <span className="text-gray-700 flex-1">{claim.content}</span>
          <ConfidenceIndicator confidence={claim.confidence} />
        </li>
      ))}
    </ul>
  )
}

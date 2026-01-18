import { useState, type ReactNode } from 'react'

interface CollapsibleSectionProps {
  title: string
  count?: number
  defaultExpanded?: boolean
  children: ReactNode
}

export function CollapsibleSection({
  title,
  count,
  defaultExpanded = true,
  children,
}: CollapsibleSectionProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  return (
    <div className="border-b border-gray-100 last:border-b-0">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-gray-400 text-sm">
            {isExpanded ? '\u25BC' : '\u25B6'}
          </span>
          <span className="font-medium text-gray-900">{title}</span>
          {count !== undefined && count > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded-full">
              {count}
            </span>
          )}
        </div>
      </button>
      {isExpanded && (
        <div className="px-4 pb-4">
          {children}
        </div>
      )}
    </div>
  )
}

import type { GroupedClaim, AudienceData, BusinessType, DigitalFocus, CompanySize } from '../types'

interface AudienceDisplayProps {
  claims: GroupedClaim[]
}

// Labels for display
const businessTypeLabels: Record<BusinessType, string> = {
  service: 'Service Companies',
  product: 'Product Companies',
  hybrid: 'Hybrid',
}

const digitalFocusLabels: Record<DigitalFocus, string> = {
  digital: 'Digital-First',
  non_digital: 'Traditional',
  hybrid: 'Hybrid',
}

const companySizeLabels: Record<CompanySize, string> = {
  smb: 'SMB',
  mid_market: 'Mid-Market',
  enterprise: 'Enterprise',
}

// Badge color schemes
const badgeColors = {
  business_type: 'bg-purple-100 text-purple-700',
  digital_focus: 'bg-blue-100 text-blue-700',
  company_size: 'bg-green-100 text-green-700',
  industries: 'bg-orange-100 text-orange-700',
}

function Badge({ children, colorClass }: { children: string; colorClass: string }) {
  return (
    <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded ${colorClass}`}>
      {children}
    </span>
  )
}

function AudienceRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <span className="text-sm text-gray-500 w-28 flex-shrink-0">{label}:</span>
      <div className="flex flex-wrap gap-1.5">{children}</div>
    </div>
  )
}

export function AudienceDisplay({ claims }: AudienceDisplayProps) {
  // Aggregate audience data from all claims
  const aggregated: AudienceData = claims.reduce((acc, claim) => {
    const data = claim.parsed_content
    if (!data) return acc

    // Merge business_type (take first non-null)
    if (data.business_type && !acc.business_type) {
      acc.business_type = data.business_type
    }

    // Merge digital_focus (take first non-null)
    if (data.digital_focus && !acc.digital_focus) {
      acc.digital_focus = data.digital_focus
    }

    // Merge company_size arrays (unique values)
    if (data.company_size) {
      acc.company_size = [...new Set([...(acc.company_size || []), ...data.company_size])] as CompanySize[]
    }

    // Merge industries arrays (unique values)
    if (data.industries) {
      acc.industries = [...new Set([...(acc.industries || []), ...data.industries])]
    }

    return acc
  }, {} as AudienceData)

  const hasData = aggregated.business_type ||
    aggregated.digital_focus ||
    (aggregated.company_size && aggregated.company_size.length > 0) ||
    (aggregated.industries && aggregated.industries.length > 0)

  if (!hasData) {
    return <p className="text-sm text-gray-500 italic">No audience data available</p>
  }

  return (
    <div className="space-y-3">
      {aggregated.business_type && (
        <AudienceRow label="Business Type">
          <Badge colorClass={badgeColors.business_type}>
            {businessTypeLabels[aggregated.business_type]}
          </Badge>
        </AudienceRow>
      )}

      {aggregated.digital_focus && (
        <AudienceRow label="Digital Focus">
          <Badge colorClass={badgeColors.digital_focus}>
            {digitalFocusLabels[aggregated.digital_focus]}
          </Badge>
        </AudienceRow>
      )}

      {aggregated.company_size && aggregated.company_size.length > 0 && (
        <AudienceRow label="Company Size">
          {aggregated.company_size.map((size) => (
            <Badge key={size} colorClass={badgeColors.company_size}>
              {companySizeLabels[size]}
            </Badge>
          ))}
        </AudienceRow>
      )}

      {aggregated.industries && aggregated.industries.length > 0 && (
        <AudienceRow label="Industries">
          {aggregated.industries.map((industry) => (
            <Badge key={industry} colorClass={badgeColors.industries}>
              {formatIndustry(industry)}
            </Badge>
          ))}
        </AudienceRow>
      )}
    </div>
  )
}

// Format industry slugs for display
function formatIndustry(slug: string): string {
  return slug
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

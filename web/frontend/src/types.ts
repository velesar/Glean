// API Types

export interface User {
  id: number
  username: string
  email: string
  is_active: boolean
  is_admin: boolean
  created_at: string
  last_login: string | null
}

export interface AuthToken {
  access_token: string
  token_type: string
}

export interface SetupStatus {
  needs_setup: boolean
  user_count: number
}

export interface PipelineStats {
  inbox: number
  analyzing: number
  review: number
  approved: number
  rejected: number
  total_claims: number
  recent_discoveries: number
}

export interface Tool {
  id: number
  name: string
  url: string | null
  description: string | null
  category: string | null
  status: 'inbox' | 'analyzing' | 'review' | 'approved' | 'rejected'
  relevance_score: number | null
  first_seen: string
  last_updated: string
  reviewed_at: string | null
  rejection_reason: string | null
}

export interface Claim {
  id: number
  tool_id: number
  content: string
  claim_type: string | null
  confidence: number | null
  source_url: string | null
  extracted_at: string
}

// Audience taxonomy types
export type BusinessType = 'service' | 'product' | 'hybrid'
export type DigitalFocus = 'digital' | 'non_digital' | 'hybrid'
export type CompanySize = 'smb' | 'mid_market' | 'enterprise'

export interface AudienceData {
  business_type?: BusinessType
  digital_focus?: DigitalFocus
  company_size?: CompanySize[]
  industries?: string[]
}

export interface GroupedClaim {
  id: number
  claim_type: string | null
  content: string
  confidence: number
  source_name: string
  parsed_content?: AudienceData | null
}

export interface GroupedClaimsResponse {
  features: GroupedClaim[]
  pricing: GroupedClaim[]
  use_cases: GroupedClaim[]
  audience: GroupedClaim[]
  integrations: GroupedClaim[]
  limitations: GroupedClaim[]
  comparisons: GroupedClaim[]
}

export type ScoutType = 'reddit' | 'twitter' | 'producthunt' | 'web' | 'rss' | 'all'

export interface ScoutTypeInfo {
  id: ScoutType
  name: string
  description: string
  icon: string
  requires_api: boolean
}

export interface LogEntry {
  timestamp: string
  level: 'info' | 'warning' | 'error' | 'success'
  message: string
}

export interface Job {
  id: string
  type: 'scout' | 'analyze' | 'curate' | 'update'
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  message: string | null
  result: Record<string, unknown> | null
  started_at: string
  completed_at: string | null
  error: string | null
  scout_type: ScoutType | null
  logs: LogEntry[]
}

export interface ActivityItem {
  id: string
  type: string
  message: string
  timestamp: string
}

export interface SettingMeta {
  label: string
  description: string
  placeholder?: string
  default?: string
  options?: string[]
}

export interface SettingValue extends SettingMeta {
  value: string | null
  is_set: boolean
  is_secret: boolean
}

export interface SettingsCategory {
  [key: string]: SettingValue
}

export interface AllSettings {
  api_keys: SettingsCategory
  scouts: SettingsCategory
  analyzers: SettingsCategory
}

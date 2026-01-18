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
  reviewed_at: string | null
  rejection_reason: string | null
  created_at: string
  updated_at: string
}

export interface ToolDetail extends Tool {
  claims: Claim[]
  changelog: ChangelogEntry[]
  discoveries: Discovery[]
}

export interface ChangelogEntry {
  id: number
  tool_id: number
  change_type: string
  description: string
  source_url: string | null
  detected_at: string
}

export interface Discovery {
  id: number
  source_id: number
  source_url: string
  raw_text: string
  metadata: Record<string, unknown> | null
  processed: number
  tool_id: number | null
  discovered_at: string
}

export interface ToolsFilter {
  status?: string
  category?: string
  search?: string
  min_score?: number
  max_score?: number
  created_after?: string
  created_before?: string
  sort_by?: string
  sort_order?: 'asc' | 'desc'
  limit?: number
  offset?: number
}

export interface ToolsResponse {
  tools: Tool[]
  total: number
  limit: number
  offset: number
  filters: ToolsFilter
}

export interface ToolUpdate {
  name?: string
  url?: string
  description?: string
  category?: string
  relevance_score?: number
}

export interface BulkStatusUpdate {
  tool_ids: number[]
  status: string
  rejection_reason?: string
}

export interface BulkStatusResponse {
  success: boolean
  status: string
  updated: number[]
  updated_count: number
  not_found: number[]
}

export interface BulkDeleteResponse {
  success: boolean
  deleted: number[]
  deleted_count: number
  not_found: number[]
}

export interface ExportFilters {
  status?: string
  category?: string
  min_score?: number
  max_score?: number
  include_claims?: boolean
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

// Service-grouped API settings types
export interface ServiceField {
  key: string
  label: string
  placeholder: string
  required: boolean
  is_set: boolean
  value: string | null
}

export interface ServiceProvider {
  id: string
  name: string
  fields: ServiceField[]
  is_configured: boolean
}

export interface ServiceGroup {
  id: string
  name: string
  description: string
  is_configured: boolean
  fields?: ServiceField[]
  has_provider_choice?: boolean
  providers?: ServiceProvider[]
  selected_provider?: string
}

export interface ServicesResponse {
  services: ServiceGroup[]
}

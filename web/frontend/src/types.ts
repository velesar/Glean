// API Types

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

export interface Job {
  id: string
  type: 'scout' | 'analyze' | 'curate' | 'update'
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: number
  message: string | null
  started_at: string
  completed_at: string | null
}

export interface ActivityItem {
  id: string
  type: string
  message: string
  timestamp: string
}

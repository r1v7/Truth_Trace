export type Role = 'investigator' | 'supervisor' | 'admin'
export type CaseStatus = 'open' | 'under_review' | 'closed' | 'archived'
export type FindingType = 'match' | 'possible_conflict' | 'missing' | 'unclear'
export type FindingField = 'time' | 'location' | 'person' | 'action' | 'negation' | 'other'
export type ReviewDecision = 'accepted' | 'rejected' | 'needs_more_info'

export interface User {
  id: number
  email: string
  full_name: string
  role: Role
  is_active: boolean
}

export interface Case {
  id: number
  reference: string
  title: string
  description: string | null
  status: CaseStatus
  created_by_id: number
  created_at: string
}

export interface Interview {
  id: number
  case_id: number
  subject_name: string
  session_label: string
  interviewed_on: string | null
  notes: string | null
  conducted_by_id: number
}

export interface Claim {
  id: number
  ordinal: number
  text: string
  start_offset: number
  end_offset: number
}

export interface Statement {
  id: number
  interview_id: number
  language: string
  body: string
  claims: Claim[]
}

export interface ClaimRef {
  id: number
  text: string
  statement_id: number
  start_offset: number
  end_offset: number
}

export interface Finding {
  id: number
  finding_type: FindingType
  field: FindingField
  /** Internal engine score. Not calibrated - never present it as a confidence percentage. */
  score: number
  explanation: string
  details: Record<string, unknown>
  claim_a: ClaimRef | null
  claim_b: ClaimRef | null
  latest_decision: ReviewDecision | null
}

export interface AnalysisRun {
  id: number
  case_id: number
  interview_a_id: number
  interview_b_id: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  analyzer_backend: string
  analyzer_version: string
  error: string | null
  created_at: string
  findings?: Finding[]
}

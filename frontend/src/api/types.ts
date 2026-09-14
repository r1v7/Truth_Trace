export type Role = 'investigator' | 'supervisor' | 'admin'
export type CaseStatus = 'open' | 'under_review' | 'closed' | 'archived'
export type FindingType = 'match' | 'possible_conflict' | 'missing' | 'unclear'
export type FindingField = 'time' | 'location' | 'person' | 'action' | 'negation' | 'other'
export type ReviewDecision = 'accepted' | 'rejected' | 'needs_more_info'
export type RunKind = 'interview_pair' | 'evidence'
export type EvidenceKind = 'call_log' | 'message_log' | 'transcript' | 'document' | 'other'
export type IntegrityStatus = 'verified' | 'altered' | 'missing_file'
export type ReportStatus = 'draft' | 'submitted' | 'approved' | 'returned'

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

export interface Evidence {
  id: number
  case_id: number
  kind: EvidenceKind
  original_filename: string
  content_type: string
  size_bytes: number
  sha256: string
  description: string | null
  uploaded_by_id: number
  created_at: string
}

export interface Integrity {
  evidence_id: number
  status: IntegrityStatus
  recorded_sha256: string
  computed_sha256: string | null
  checked_at: string
  note: string
}

export interface AnalysisRun {
  id: number
  case_id: number
  kind: RunKind
  interview_a_id: number
  interview_b_id: number | null
  evidence_id: number | null
  status: 'pending' | 'running' | 'completed' | 'failed'
  analyzer_backend: string
  analyzer_version: string
  error: string | null
  created_at: string
  findings?: Finding[]
}

export interface ReportItem {
  finding_id: number
  position: number
  note: string | null
}

export interface Report {
  id: number
  case_id: number
  version: number
  title: string
  summary: string | null
  status: ReportStatus
  /** Digest of the frozen content, set at submission. */
  content_sha256: string | null
  prepared_by_id: number
  submitted_at: string | null
  decided_by_id: number | null
  decided_at: string | null
  decision_note: string | null
  created_at: string
  items: ReportItem[]
}

export interface AuditEntry {
  id: number
  created_at: string
  actor_id: number | null
  actor_name: string | null
  action: string
  entity_type: string
  entity_id: string | null
  case_id: number | null
  case_reference: string | null
  ip_address: string | null
  payload: Record<string, unknown>
}

export interface AuditPage {
  total: number
  offset: number
  limit: number
  entries: AuditEntry[]
}

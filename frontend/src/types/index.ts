export interface Profile {
  id?: string
  full_name?: string
  email?: string
  phone?: string
  location?: string
  preferred_locations?: string[]
  education?: Record<string, unknown>[]
  experience?: Record<string, unknown>[]
  skills?: string[]
  desired_roles?: string[]
  min_salary?: number
  preferred_salary?: number
  remote_preference?: string
  experience_level?: string
  notice_period?: string
  preferred_industries?: string[]
  search_keywords?: string[]
  search_exclusions?: string[]
}

export interface Resume {
  id: string
  profile_id?: string
  title: string
  original_filename: string
  file_type: string
  is_default?: boolean
  parsed_sections?: Record<string, unknown>
  created_at?: string
}

export interface Job {
  id: string
  title?: string
  company?: string
  location?: string
  remote?: boolean
  salary_min?: number
  salary_max?: number
  description?: string
  url?: string
  source?: string
  match_score?: number
  match_evidence?: string[]
  status?: string
  is_saved?: boolean
  is_duplicate?: boolean
  created_at?: string
  scraped_at?: string
}

export interface Application {
  id: string
  job_id?: string
  resume_id?: string
  company?: string
  job_title?: string
  job_url?: string
  source?: string
  match_score?: number
  status?: string
  cover_letter?: string
  notes?: string
  follow_up_date?: string
  created_at?: string
  updated_at?: string
}

export interface AutoApplySettings {
  id: string
  enabled: boolean
  emergency_stop: boolean
  mode: string
  min_match_score: number
  max_per_day: number
  preferred_titles?: string[]
  preferred_locations?: string[]
  min_salary?: number
  remote_only: boolean
  experience_level?: string
  sources?: string[]
  default_resume_id?: string
  generate_cover_letter: boolean
  auto_submit_enabled: boolean
  created_at?: string
  updated_at?: string
}

export interface AutoApplyAttempt {
  id: string
  application_id?: string
  job_id: string
  resume_id?: string
  cover_letter_id?: string
  status: string
  step?: string
  error?: string
  started_at?: string
  finished_at?: string
}

export interface ApprovalRecord {
  id: string
  attempt_id: string
  application_id?: string
  decision: string
  reviewer?: string
  notes?: string
  decided_at?: string
}

export interface QueuedApproval {
  approval_id: string
  application_id: string
  job_title: string
  company: string
  match_score?: number
  cover_letter?: string
  form_answers?: Record<string, unknown>
  job_url?: string
  source?: string
  created_at?: string
}

export interface AutoApplyStats {
  enabled: boolean
  emergency_stop: boolean
  mode: string
  min_match_score: number
  max_per_day: number
  pending_approvals: number
  active_attempts: number
  auto_submit_enabled: boolean
}

export interface DashboardSummary {
  total_jobs: number
  matching_jobs: number
  prepared: number
  submitted: number
  interviews: number
  offers: number
  rejected: number
  response_rate: number
  applications: number
  recent_applications: number
  upcoming_follow_ups: number
}

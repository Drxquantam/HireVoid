export type ApplicationStatus =
  | 'applied'
  | 'in_progress'
  | 'interview'
  | 'offer'
  | 'rejected'
  | 'unknown'

export interface Application {
  id: number
  company: string
  role: string
  status: ApplicationStatus
  source_message_id: string
  thread_id: string | null
  sender: string | null
  sender_domain: string | null
  email_subject: string | null
  email_snippet: string | null
  applied_date: string | null
  deadline: string | null
  created_at: string | null
  updated_at: string | null
}

export type GroupedApplications = Record<ApplicationStatus, Application[]>

export interface Stats {
  total: number
  by_status: Record<ApplicationStatus, number>
}

export interface SyncResult {
  success: boolean
  fetched: number
  skipped: number
  new: number
  updated: number
}

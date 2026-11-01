// Response types mirroring the Django REST serializers (see /api/docs/).

export type Role = 'STUDENT' | 'MENTOR' | 'ADMIN'
export type ApprovalStatus = 'PENDING' | 'APPROVED' | 'REJECTED'
export type Pathway = 'JOB' | 'HIGHER_STUDIES' | 'VENTURE' | 'UNSURE'
export type RequestStatus = 'SUBMITTED' | 'UNDER_REVIEW' | 'WAITING' | 'MATCHED' | 'WITHDRAWN' | 'CLOSED'
export type Stage =
  | 'SUBMITTED' | 'UNDER_REVIEW' | 'WAITING' | 'AVAILABILITY_CHECK_SENT' | 'MENTOR_CONFIRMED'
  | 'AWAITING_IIC_APPROVAL' | 'MATCHED' | 'ACTIVE' | 'WITHDRAWN' | 'CLOSED'
export type Priority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT'
export type CalendarState = 'CONNECTED' | 'DISCONNECTED' | 'REAUTH_REQUIRED'
export type MeetingStatus = 'SCHEDULED' | 'HELD' | 'CANCELLED' | 'NO_SHOW'
export type MeetingFormat = 'VIDEO' | 'PHONE' | 'IN_PERSON'
export type FeedbackKind = 'GENERAL' | 'PROGRESS' | 'CHANGE_MENTOR' | 'CLOSING'
export type OutcomeKind = 'INTERVIEW' | 'INTERNSHIP' | 'JOB' | 'HIGHER_STUDIES' | 'VENTURE' | 'OTHER'
export type ClosureType = 'COMPLETED' | 'REASSIGNED' | 'STUDENT_WITHDREW' | 'MENTOR_UNAVAILABLE' | 'OTHER'

export interface Paginated<T> { count: number; next: string | null; previous: string | null; results: T[] }
export interface Person { id: number; name: string }

export interface StudentProfile {
  iitm_roll_number: string; level: 'DIPLOMA' | 'DEGREE'; courses: string[]; cgpa: string | null
  approval_status: ApprovalStatus; rejection_reason: string
}

export interface MentorProfile {
  id: number; user: number; name: string; email?: string; alumni_roll_number: string; graduation_year: number | null
  domain: string; specialty: string; current_role: string; company: string; career_path: string; experience_years: number
  is_verified: boolean; is_available: boolean; bio: string; skills: string[]; linkedin_url: string
  is_discoverable: boolean; verified_at: string | null; has_active_mentee: boolean
}

export interface CalendarStatus { configured: boolean; status: CalendarState; google_email: string; connected_at: string | null }

export interface Me {
  id: number; email: string; first_name: string; last_name: string; role: Role
  student_profile: StudentProfile | null; mentor_profile: MentorProfile | null
  is_iic: boolean; effective_role: Role | null; display_name: string; calendar: CalendarStatus | null
}

export interface DirectoryMentor {
  id: number; name: string; current_role: string; company: string; domain: string; specialty: string; career_path: string
  experience_years: number; skills: string[]; bio: string; linkedin_url: string; graduation_year: number | null
  availability: { is_available: boolean; has_capacity: boolean; accepting_requests: boolean; label: string }
}
export interface MentorFacets { domains: string[]; specialties: string[]; career_paths: string[]; skills: string[] }

export interface PriorityInfo {
  assessment_id: number; effective: Priority; suggested: Priority; explanation: string; confidence: number | null
  overridden: boolean; override_reason: string; assessed_at: string
}

export interface HistoryEntry {
  id: number; event: string; from_status: string; to_status: string; label: string; actor_role: string; note: string; created_at: string
}

export interface MentoringRequest {
  id: number; student: number; pathway: Pathway; domain: string; background: string; problem_statement: string
  status: RequestStatus; submitted_at: string; updated_at: string; preferred_mentor: number | null
  preferred_mentor_summary: (Person & { current_role: string; company: string }) | null
  stage: Stage; stage_label: string; next_action: string; last_status_at: string
  assigned_mentor: Person | null; mentorship_id: number | null; priority: PriorityInfo | null
  student_summary: (Person & { email: string; approval_status: ApprovalStatus | null; level: string | null }) | null
}
export interface RequestDetail extends MentoringRequest { timeline: HistoryEntry[]; availability_checks: AvailabilityCheck[] | null }

export interface AvailabilityCheck {
  id: number; request: number; mentor: number; status: 'PENDING' | 'CONFIRMED' | 'DECLINED' | 'EXPIRED' | 'USED'
  sent_at: string; expires_at: string; responded_at: string | null; reason: string; is_expired: boolean
  request_summary: { id: number; pathway: Pathway; domain: string; problem_statement: string }
  mentor_summary: (Person & { domain: string; is_student_preference: boolean }) | null
}

export interface CalendarEvent {
  provider: string; html_link: string; meet_link: string; sync_status: 'SYNCED' | 'FAILED' | 'CANCELLED'
  last_synced_at: string | null; last_error: string
}
export interface Meeting {
  id: number; mentorship: number; session_date: string; duration_minutes: number; status: MeetingStatus; logged_by: number
  mentor_confirmed: boolean; created_at: string; start_at: string | null; end_at: string | null; timezone: string
  title: string; meeting_format: MeetingFormat; calendar_event: CalendarEvent | null; calendar_synced?: boolean
}

export interface Mentorship {
  id: number; request: number; student: number; mentor: number; status: 'ACTIVE' | 'CLOSED'; started_at: string
  closed_at: string | null; student_contact: string | null; mentor_contact: string | null
  student_name: string | null; mentor_name: string | null
  mentor_profile: { current_role: string; company: string; domain: string; specialty: string; linkedin_url: string } | null
  request_summary: { id: number; domain: string; pathway: Pathway; status: RequestStatus }
  closure_type: ClosureType | ''; closing_reason: string
  progress: { goals_total: number; goals_completed: number; meetings_held: number; meetings_total: number
    last_meeting_date: string | null; next_meeting: Meeting | null; outcomes: number }
  open_alerts: string[] | null
}
export interface TimelineItem { type: 'status' | 'meeting' | 'goal' | 'outcome'; at: string; title: string; detail: string; event: string }
export interface MentorshipDetail extends Mentorship { timeline: TimelineItem[]; approved_at: string }

export interface Goal { id: number; mentorship: number; slot: number; title: string; target_date: string; completed: boolean; completed_at: string | null }
export interface Feedback { id: number; mentorship: number; author: number; kind: FeedbackKind; text: string; created_at: string }
export interface Outcome { id: number; mentorship: number; kind: OutcomeKind; achieved_on: string; note: string; created_at: string }
export interface Notification { id: number; title: string; message: string; is_read: boolean; created_at: string }

export interface Task { key: string; label: string; link: string; count: number | null; tone: 'info' | 'primary' | 'warning' }
export interface NextStep { title: string; detail: string; link: string }
interface NotificationsBlock { unread: number; latest: Notification[] }

export interface StudentDashboard {
  role: 'STUDENT'; display_name: string; approval_status: ApprovalStatus | null; rejection_reason: string
  current_request: MentoringRequest | null; recent_requests: MentoringRequest[]; mentorship: Mentorship | null
  upcoming_meeting: Meeting | null; goals: { completed: number; total: number }; recent_activity: HistoryEntry[]
  notifications: NotificationsBlock; tasks: Task[]; next_steps: NextStep[]
}
export interface MentorDashboard {
  role: 'MENTOR'; display_name: string
  availability: { is_available: boolean; is_verified: boolean; has_active_mentee: boolean }
  pending_checks: AvailabilityCheck[]; mentorship: Mentorship | null; upcoming_meetings: Meeting[]
  unconfirmed_meetings: Meeting[]; feedback: { due: boolean; last_submitted_at: string | null; next_due_at: string } | null
  calendar: CalendarStatus; recent_activity: HistoryEntry[]; notifications: NotificationsBlock; tasks: Task[]
}
export interface AdminDashboard {
  role: 'ADMIN'; display_name: string; tasks: Task[]
  counts: Record<'students_pending' | 'mentors_unverified' | 'requests_awaiting_review' | 'checks_pending' |
    'matches_awaiting_approval' | 'active_mentorships' | 'inactivity_alerts' | 'feedback_alerts' | 'outcomes', number>
  review_queue: MentoringRequest[]; approval_queue: AvailabilityCheck[]
  domain_demand: { domain: string; count: number }[]
  participation: { students_approved: number; students_with_requests: number; mentors_verified: number; mentors_active: number }
  notifications: NotificationsBlock
}
export type Dashboard = StudentDashboard | MentorDashboard | AdminDashboard

export type ReviewChecklistItem = 'iitm_email' | 'roll_number' | 'level' | 'courses' | 'cgpa'

export interface MentorImportResult {
  dry_run: boolean
  created: { row: number; email: string; id: number | null }[]
  errors: { row: number; email: string; errors: Record<string, string[]> }[]
}
export interface DailyChecksResult { expired_checks: number; inactivity_alerts: number; feedback_alerts: number; priorities_refreshed: number }

export interface PendingStudent extends StudentProfile {
  id: number; user_id: number; email: string; name: string; submitted_at: string; approved_at: string | null
}

export interface Suggestion {
  mentor_id: number; name: string; domain: string; specialty: string; experience_years: number
  is_student_preference: boolean; score: number; final_score: number; ai_bonus: number; reasons: string[]
}
export interface SuggestionResult {
  request_id: number; candidates: Suggestion[]; ai_explanation_used: boolean; approval_required: boolean
  student_preference_mentor_id: number | null
}

export interface MonthPoint { month: string; count: number }
export interface Insights {
  requests: number; waiting: number; active_pairs: number; meetings_held: number; outcomes: number; alerts_open: number
  domain_demand: { domain: string; count: number }[]; students_pending: number; mentors_unverified: number
  mentors_verified: number; checks_pending: number; matches_awaiting_approval: number; mentorships_closed: number
  requests_by_status: { status: RequestStatus; count: number }[]; pathway_demand: { pathway: Pathway; count: number }[]
  outcomes_by_kind: { kind: OutcomeKind; count: number }[]; closure_types: { closure_type: ClosureType | ''; count: number }[]
  monthly_requests: MonthPoint[]; monthly_mentorships: MonthPoint[]; monthly_meetings: MonthPoint[]
}

export interface AlertRow {
  id: number; mentorship_id: number; kind: 'INACTIVITY' | 'FEEDBACK_DUE'; kind_label: string; period_start: string
  created_at: string; resolved_at: string | null; student_name: string; mentor_name: string
}
export interface AuditEvent {
  id: number; actor_id: number | null; actor_email: string | null; actor_role: string; action: string
  entity_type: string; entity_id: number; at: string; details: Record<string, unknown>
}
export interface KnowledgeArticle { id: number; title: string; content: string; audience: 'ALL' | Role; is_published: boolean; updated_at: string }
export interface ChatReply { answer: string; sources: { id: number; title: string }[]; local_ai_used: boolean; message_stored: boolean }

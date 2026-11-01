import { keepPreviousData, useMutation, useQuery, useQueryClient, type QueryKey } from '@tanstack/react-query'
import { del, get, patch, post } from './api'
import type * as T from './types'

type Params = Record<string, string | number | boolean | undefined | null>

function clean(params: Params = {}) {
  return Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ''))
}

/** Mutation that invalidates the given query-key prefixes on success. */
export function useAction<TVars, TResult = unknown>(fn: (vars: TVars) => Promise<TResult>, invalidate: QueryKey[]) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: async () => { await Promise.all(invalidate.map((queryKey) => qc.invalidateQueries({ queryKey }))) },
  })
}

// ---- auth & profile ---------------------------------------------------------
export const useMe = (enabled = true) => useQuery({ queryKey: ['me'], queryFn: () => get<T.Me>('/auth/me/'), enabled, retry: false, staleTime: 60_000 })
export const useDashboard = () => useQuery({ queryKey: ['dashboard'], queryFn: () => get<T.Dashboard>('/dashboard/') })
export const useStudentProfile = () => useQuery({ queryKey: ['student-profile'], queryFn: () => get<T.StudentProfile>('/students/me/') })
export const useMentorProfile = () => useQuery({ queryKey: ['mentor-profile'], queryFn: () => get<T.MentorProfile>('/mentor/profile/') })

// ---- discovery --------------------------------------------------------------
export const useMentorDirectory = (params: Params) => useQuery({
  queryKey: ['mentors', clean(params)], placeholderData: keepPreviousData,
  queryFn: () => get<T.Paginated<T.DirectoryMentor>>('/mentors/', { params: clean(params) }),
})
export const useMentorFacets = () => useQuery({ queryKey: ['mentor-facets'], queryFn: () => get<T.MentorFacets>('/mentors/facets/'), staleTime: 300_000 })

// ---- requests ---------------------------------------------------------------
export const useRequests = (params: Params = {}) => useQuery({
  queryKey: ['requests', clean(params)], placeholderData: keepPreviousData,
  queryFn: () => get<T.Paginated<T.MentoringRequest>>('/requests/', { params: { page_size: 50, ...clean(params) } }),
})
export const useRequest = (id?: number) => useQuery({ queryKey: ['requests', 'detail', id], enabled: !!id, queryFn: () => get<T.RequestDetail>(`/requests/${id}/`) })
export const useSuggestions = (id?: number, enabled = true) => useQuery({
  queryKey: ['suggestions', id], enabled: !!id && enabled, staleTime: 60_000,
  queryFn: () => get<T.SuggestionResult>(`/admin/requests/${id}/suggestions/`),
})

const REQUEST_KEYS: QueryKey[] = [['requests'], ['dashboard'], ['availability'], ['mentorships'], ['notifications']]

export function useRequestActions() {
  return {
    create: useAction((body: Partial<T.MentoringRequest> & { preferred_mentor?: number | null }) => post<T.MentoringRequest>('/requests/', body), REQUEST_KEYS),
    withdraw: useAction((id: number) => post(`/requests/${id}/withdraw/`), REQUEST_KEYS),
    transition: useAction(({ id, to_status, note }: { id: number; to_status: string; note?: string }) => post(`/admin/requests/${id}/transition/`, { to_status, note }), REQUEST_KEYS),
    sendCheck: useAction(({ id, mentor_id }: { id: number; mentor_id: number }) => post(`/admin/requests/${id}/availability/`, { mentor_id }), [...REQUEST_KEYS, ['suggestions']]),
    assess: useAction((id: number) => post(`/admin/requests/${id}/assess/`), [['requests'], ['dashboard']]),
    override: useAction(({ id, priority, reason }: { id: number; priority: string; reason: string }) => patch(`/admin/requests/${id}/priority/`, { priority, reason }), [['requests'], ['dashboard']]),
  }
}

// ---- availability -----------------------------------------------------------
export const useAvailability = (params: Params = {}) => useQuery({
  queryKey: ['availability', clean(params)],
  queryFn: () => get<T.Paginated<T.AvailabilityCheck>>('/availability/', { params: { page_size: 50, ...clean(params) } }),
})
export function useAvailabilityActions() {
  return {
    respond: useAction(({ id, decision, reason }: { id: number; decision: 'CONFIRMED' | 'DECLINED'; reason?: string }) => post(`/availability/${id}/respond/`, { decision, reason }), REQUEST_KEYS),
    approve: useAction((checkId: number) => post<T.Mentorship>(`/admin/availability/${checkId}/approve/`), REQUEST_KEYS),
  }
}

// ---- mentorships & workspace ----------------------------------------------
export const useMentorships = (params: Params = {}) => useQuery({
  queryKey: ['mentorships', clean(params)],
  queryFn: () => get<T.Paginated<T.Mentorship>>('/mentorships/', { params: { page_size: 50, ...clean(params) } }),
})
export const useMentorship = (id?: number | null) => useQuery({ queryKey: ['mentorships', 'detail', id], enabled: !!id, queryFn: () => get<T.MentorshipDetail>(`/mentorships/${id}/`) })
export const useGoals = (id?: number | null) => useQuery({ queryKey: ['mentorships', id, 'goals'], enabled: !!id, queryFn: () => get<T.Goal[]>(`/mentorships/${id}/goals/`) })
export const usePairMeetings = (id?: number | null) => useQuery({ queryKey: ['mentorships', id, 'meetings'], enabled: !!id, queryFn: () => get<T.Meeting[]>(`/mentorships/${id}/meetings/`) })
export const useFeedback = (id?: number | null) => useQuery({ queryKey: ['mentorships', id, 'feedback'], enabled: !!id, queryFn: () => get<T.Feedback[]>(`/mentorships/${id}/feedback/`) })
export const useOutcomes = (id?: number | null) => useQuery({ queryKey: ['mentorships', id, 'outcomes'], enabled: !!id, queryFn: () => get<T.Outcome[]>(`/mentorships/${id}/outcomes/`) })

const PAIR_KEYS: QueryKey[] = [['mentorships'], ['dashboard'], ['meetings'], ['notifications']]

export interface ScheduleInput { date: string; start_time: string; end_time: string; timezone: string; title: string; meeting_format: T.MeetingFormat; add_google_meet: boolean }

export function useWorkspaceActions(pairId?: number | null) {
  return {
    addGoal: useAction((body: { slot: number; title: string; target_date: string }) => post(`/mentorships/${pairId}/goals/`, body), PAIR_KEYS),
    toggleGoal: useAction(({ id, completed }: { id: number; completed: boolean }) => patch(`/goals/${id}/complete/`, { completed }), PAIR_KEYS),
    logMeeting: useAction((body: { session_date: string; duration_minutes: number; status: string; meeting_format: T.MeetingFormat }) => post(`/mentorships/${pairId}/meetings/`, body), PAIR_KEYS),
    confirmMeeting: useAction((id: number) => post(`/meetings/${id}/confirm/`), PAIR_KEYS),
    schedule: useAction((body: ScheduleInput) => post<T.Meeting>(`/mentorships/${pairId}/meetings/schedule/`, body), PAIR_KEYS),
    reschedule: useAction(({ id, ...body }: ScheduleInput & { id: number }) => post<T.Meeting>(`/meetings/${id}/reschedule/`, body), PAIR_KEYS),
    cancel: useAction((id: number) => post<T.Meeting>(`/meetings/${id}/cancel/`), PAIR_KEYS),
    record: useAction(({ id, status }: { id: number; status: 'HELD' | 'NO_SHOW' }) => post<T.Meeting>(`/meetings/${id}/record/`, { status }), PAIR_KEYS),
    feedback: useAction((body: { kind: T.FeedbackKind; text: string }) => post(`/mentorships/${pairId}/feedback/`, body), PAIR_KEYS),
    outcome: useAction((body: { kind: T.OutcomeKind; achieved_on: string; note: string }) => post(`/mentorships/${pairId}/outcomes/`, body), PAIR_KEYS),
  }
}

export const useMyMeetings = (params: Params = {}) => useQuery({
  queryKey: ['meetings', clean(params)],
  queryFn: () => get<T.Paginated<T.Meeting>>('/meetings/', { params: { page_size: 50, ...clean(params) } }),
})

// ---- calendar -----------------------------------------------------------------
export const useCalendarStatus = () => useQuery({ queryKey: ['calendar'], queryFn: () => get<T.CalendarStatus>('/calendar/status/') })
export function useCalendarActions() {
  return {
    connect: useMutation({ mutationFn: () => post<{ authorization_url: string }>('/calendar/connect/') }),
    disconnect: useAction(() => post<T.CalendarStatus>('/calendar/disconnect/'), [['calendar'], ['me'], ['dashboard']]),
  }
}

// ---- notifications ----------------------------------------------------------
export const useNotifications = (params: Params = {}) => useQuery({
  queryKey: ['notifications', clean(params)], refetchInterval: 60_000,
  queryFn: () => get<T.Paginated<T.Notification>>('/notifications/', { params: { page_size: 30, ...clean(params) } }),
})
export function useNotificationActions() {
  return {
    read: useAction((id: number) => post(`/notifications/${id}/read/`), [['notifications'], ['dashboard']]),
    readAll: useAction(() => post('/notifications/read-all/'), [['notifications'], ['dashboard']]),
  }
}

// ---- profile updates ----------------------------------------------------------
export function useProfileActions() {
  return {
    updateMe: useAction((body: { first_name: string; last_name: string }) => patch<T.Me>('/auth/me/', body), [['me']]),
    updateStudent: useAction((body: Partial<T.StudentProfile>) => patch('/students/me/', body), [['student-profile'], ['me'], ['dashboard']]),
    updateMentor: useAction((body: Partial<T.MentorProfile>) => patch('/mentor/profile/', body), [['mentor-profile'], ['me']]),
    availability: useAction((is_available: boolean) => patch('/mentor/availability/', { is_available }), [['mentor-profile'], ['me'], ['dashboard']]),
  }
}

// ---- IIC administration -----------------------------------------------------
export const useStudents = (params: Params) => useQuery({
  queryKey: ['admin-students', clean(params)], placeholderData: keepPreviousData,
  queryFn: () => get<T.Paginated<T.PendingStudent>>('/admin/students/', { params: { page_size: 50, ...clean(params) } }),
})
export const useAdminMentors = (params: Params) => useQuery({
  queryKey: ['admin-mentors', clean(params)], placeholderData: keepPreviousData,
  queryFn: () => get<T.Paginated<T.MentorProfile>>('/admin/mentors/', { params: { page_size: 50, ...clean(params) } }),
})
const ADMIN_KEYS: QueryKey[] = [['admin-students'], ['admin-mentors'], ['dashboard'], ['mentors'], ['insights']]
export function useAdminActions() {
  return {
    reviewStudent: useAction(({ userId, ...body }: { userId: number; decision: 'APPROVED' | 'REJECTED'; reason?: string; checklist?: Record<T.ReviewChecklistItem, boolean> }) => post(`/admin/students/${userId}/review/`, body), ADMIN_KEYS),
    createMentor: useAction((body: Record<string, unknown>) => post('/admin/mentors/', body), ADMIN_KEYS),
    importMentors: useAction((body: { mentors: Record<string, unknown>[]; dry_run: boolean }) => post<T.MentorImportResult>('/admin/mentors/import/', body), ADMIN_KEYS),
    runDailyChecks: useAction(() => post<T.DailyChecksResult>('/admin/daily-checks/'), [['alerts'], ['dashboard'], ['insights'], ['requests'], ['availability'], ['notifications']]),
    verifyMentor: useAction(({ userId, discoverable }: { userId: number; discoverable: boolean }) => post(`/admin/mentors/${userId}/verify/`, { discoverable }), ADMIN_KEYS),
    updateMentor: useAction(({ userId, ...body }: { userId: number } & Partial<T.MentorProfile>) => patch(`/admin/mentors/${userId}/`, body), ADMIN_KEYS),
    inviteMentor: useAction((userId: number) => post(`/admin/mentors/${userId}/invite/`), []),
    close: useAction(({ id, reason, closure_type }: { id: number; reason: string; closure_type: string }) => post(`/admin/mentorships/${id}/close/`, { reason, closure_type }), [...REQUEST_KEYS, ['alerts']]),
    reassign: useAction(({ id, reason }: { id: number; reason: string }) => post(`/admin/mentorships/${id}/reassign/`, { reason }), [...REQUEST_KEYS, ['alerts']]),
    resolveAlert: useAction((id: number) => post(`/admin/alerts/${id}/resolve/`), [['alerts'], ['dashboard'], ['insights']]),
  }
}
export const useInsights = () => useQuery({ queryKey: ['insights'], queryFn: () => get<T.Insights>('/admin/insights/') })
export const useAlerts = (includeResolved = false) => useQuery({
  queryKey: ['alerts', includeResolved], queryFn: () => get<T.AlertRow[]>('/admin/alerts/', { params: includeResolved ? { include_resolved: true } : {} }),
})
export const useAudit = (params: Params) => useQuery({
  queryKey: ['audit', clean(params)], placeholderData: keepPreviousData,
  queryFn: () => get<T.Paginated<T.AuditEvent>>('/admin/audit/', { params: { page_size: 50, page: 1, ...clean(params) } }),
})

// ---- AI ---------------------------------------------------------------------------
export const useKnowledgeAdmin = () => useQuery({ queryKey: ['knowledge'], queryFn: () => get<T.Paginated<T.KnowledgeArticle>>('/admin/knowledge/', { params: { page_size: 100 } }) })
export function useKnowledgeActions() {
  return {
    save: useAction(({ id, ...body }: Partial<T.KnowledgeArticle>) => (id ? patch(`/admin/knowledge/${id}/`, body) : post('/admin/knowledge/', body)), [['knowledge']]),
    remove: useAction((id: number) => del(`/admin/knowledge/${id}/`), [['knowledge']]),
  }
}
export const useChat = () => useMutation({ mutationFn: (message: string) => post<T.ChatReply>('/ai/chat/', { message }) })

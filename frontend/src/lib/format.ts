import type { MeetingFormat, OutcomeKind, Pathway, Priority, Stage } from './types'

export type Tone = 'neutral' | 'info' | 'primary' | 'success' | 'warning' | 'error' | 'ghost'

// Labels for the derived request stages returned by the backend (`stage`).
export const STAGE: Record<Stage, { label: string; tone: Tone }> = {
  SUBMITTED: { label: 'Submitted', tone: 'neutral' },
  UNDER_REVIEW: { label: 'Under review', tone: 'info' },
  WAITING: { label: 'Waiting', tone: 'warning' },
  AVAILABILITY_CHECK_SENT: { label: 'Availability check sent', tone: 'info' },
  MENTOR_CONFIRMED: { label: 'Mentor confirmed', tone: 'primary' },
  AWAITING_IIC_APPROVAL: { label: 'Awaiting IIC approval', tone: 'primary' },
  MATCHED: { label: 'Matched', tone: 'success' },
  ACTIVE: { label: 'Active', tone: 'success' },
  WITHDRAWN: { label: 'Withdrawn', tone: 'ghost' },
  CLOSED: { label: 'Closed', tone: 'neutral' },
}

export const PRIORITY: Record<Priority, { label: string; tone: Tone }> = {
  LOW: { label: 'Low', tone: 'neutral' },
  MEDIUM: { label: 'Medium', tone: 'info' },
  HIGH: { label: 'High', tone: 'warning' },
  URGENT: { label: 'Urgent', tone: 'error' },
}

export const PATHWAY: Record<Pathway, string> = { JOB: 'Job', HIGHER_STUDIES: 'Higher studies', VENTURE: 'Venture', UNSURE: 'Unsure' }
export const MEETING_FORMAT: Record<MeetingFormat, string> = { VIDEO: 'Video call', PHONE: 'Phone call', IN_PERSON: 'In person' }
export const OUTCOME: Record<OutcomeKind, string> = {
  INTERVIEW: 'Interview cleared', INTERNSHIP: 'Internship secured', JOB: 'Job offer',
  HIGHER_STUDIES: 'Admission', VENTURE: 'Venture milestone', OTHER: 'Other',
}
export const CLOSURE: Record<string, string> = {
  COMPLETED: 'Completed', REASSIGNED: 'Reassigned', STUDENT_WITHDREW: 'Student withdrew', MENTOR_UNAVAILABLE: 'Mentor unavailable', OTHER: 'Other',
}

const dateFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
const dateTimeFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })

export function formatDate(value?: string | null) {
  return value ? dateFmt.format(new Date(value)) : '—'
}
export function formatDateTime(value?: string | null) {
  return value ? dateTimeFmt.format(new Date(value)) : '—'
}
export function timeAgo(value?: string | null) {
  if (!value) return '—'
  const seconds = (new Date(value).getTime() - Date.now()) / 1000
  const steps: [Intl.RelativeTimeFormatUnit, number][] = [['year', 31536000], ['month', 2592000], ['week', 604800], ['day', 86400], ['hour', 3600], ['minute', 60]]
  for (const [unit, size] of steps) if (Math.abs(seconds) >= size) return rtf.format(Math.round(seconds / size), unit)
  return 'just now'
}
export function truncate(text: string, length = 160) {
  return text.length > length ? `${text.slice(0, length).trimEnd()}…` : text
}
export function humanize(code: string) {
  return code.replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase())
}
export function todayISO() {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}
export const browserTimeZone = () => Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Kolkata'

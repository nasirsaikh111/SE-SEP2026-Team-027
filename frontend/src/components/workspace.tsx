import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { CalendarCheck2, CalendarPlus, Check, ExternalLink, Link2, Mail, PenLine, Plus, Trophy, Video } from 'lucide-react'
import { fieldErrors } from '../lib/api'
import { CLOSURE, MEETING_FORMAT, OUTCOME, PATHWAY, browserTimeZone, formatDate, formatDateTime, todayISO } from '../lib/format'
import { useFeedback, useGoals, useOutcomes, useWorkspaceActions, type ScheduleInput } from '../lib/queries'
import type { CalendarState, FeedbackKind, Meeting, MeetingFormat, Mentorship, OutcomeKind } from '../lib/types'
import { Badge, EmptyState, ErrorAlert, Field, Loading, Modal } from './ui'

export function CalendarBadge({ status }: { status: CalendarState }) {
  const map = { CONNECTED: ['success', 'Google Calendar connected'], DISCONNECTED: ['neutral', 'Calendar not connected'], REAUTH_REQUIRED: ['warning', 'Reconnect Google Calendar'] } as const
  const [tone, label] = map[status]
  return <Badge tone={tone}>{label}</Badge>
}

/** The relationship, on the ink "river" surface. Contact details exist only after IIC approval. */
export function MentorshipCard({ pair, viewer }: { pair: Mentorship; viewer: 'STUDENT' | 'MENTOR' | 'ADMIN' }) {
  const counterpart = viewer === 'MENTOR' ? pair.student_name : pair.mentor_name
  const contact = viewer === 'MENTOR' ? pair.student_contact : pair.mentor_contact
  const p = pair.progress
  return (
    <section className="bg-neutral text-neutral-content rounded-hero relative overflow-hidden p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-neutral-content/60 text-sm">{viewer === 'MENTOR' ? 'Your mentee' : 'Your mentor'}</p>
          <h2 className="font-display text-title mt-0.5 font-semibold text-white">{counterpart}</h2>
          {viewer !== 'MENTOR' && pair.mentor_profile && (
            <p className="text-neutral-content/80">{pair.mentor_profile.current_role}{pair.mentor_profile.company && `, ${pair.mentor_profile.company}`}</p>
          )}
          <p className="text-neutral-content/60 mt-1 text-sm">{pair.request_summary.domain}, {PATHWAY[pair.request_summary.pathway].toLowerCase()} pathway</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${pair.status === 'ACTIVE' ? 'bg-[#4fb3a2] text-[#062019]' : 'bg-white/15 text-white'}`}>
          {pair.status === 'ACTIVE' ? 'Active' : pair.closure_type ? CLOSURE[pair.closure_type] : 'Closed'}
        </span>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {contact && <a href={`mailto:${contact}`} className="btn btn-sm border-0 bg-white/10 text-white hover:bg-white/20"><Mail size={15} />{contact}</a>}
        {viewer !== 'MENTOR' && pair.mentor_profile?.linkedin_url && (
          <a href={pair.mentor_profile.linkedin_url} target="_blank" rel="noopener noreferrer" className="btn btn-sm border-0 bg-white/10 text-white hover:bg-white/20"><Link2 size={15} />LinkedIn profile</a>
        )}
      </div>
      <dl className="mt-6 grid grid-cols-3 gap-4 border-t border-white/10 pt-4">
        <div><dt className="text-neutral-content/60 text-xs">Goals done</dt><dd className="font-display text-2xl font-semibold text-white tabular-nums">{p.goals_completed}<span className="text-neutral-content/40 text-base">/{p.goals_total}</span></dd></div>
        <div><dt className="text-neutral-content/60 text-xs">Meetings held</dt><dd className="font-display text-2xl font-semibold text-white tabular-nums">{p.meetings_held}</dd></div>
        <div><dt className="text-neutral-content/60 text-xs">Approved</dt><dd className="font-display text-lg font-semibold text-white">{formatDate(pair.started_at)}</dd></div>
      </dl>
    </section>
  )
}

export function MeetingLinks({ meeting }: { meeting: Meeting }) {
  const ev = meeting.calendar_event
  if (!ev || ev.sync_status === 'CANCELLED') return null
  return (
    <span className="inline-flex flex-wrap gap-1.5">
      {ev.meet_link && meeting.status === 'SCHEDULED' && (
        <a href={ev.meet_link} target="_blank" rel="noopener noreferrer" className="btn btn-primary btn-xs"><Video size={13} />Join Meet</a>
      )}
      {ev.html_link && <a href={ev.html_link} target="_blank" rel="noopener noreferrer" className="btn btn-ghost btn-xs"><ExternalLink size={13} />Calendar event</a>}
      {ev.sync_status === 'FAILED' && <Badge tone="warning">Not synced to Google</Badge>}
    </span>
  )
}

export function UpcomingMeeting({ meeting }: { meeting: Meeting | null | undefined }) {
  if (!meeting) return <p className="text-base-content/60 text-sm">Nothing scheduled yet.</p>
  const start = meeting.start_at ? new Date(meeting.start_at) : null
  return (
    <div className="flex items-center gap-4">
      {start && (
        <div className="bg-primary/10 text-primary flex w-14 shrink-0 flex-col items-center rounded-xl py-1.5">
          <span className="text-xs font-medium">{start.toLocaleDateString('en-IN', { month: 'short' })}</span>
          <span className="font-display text-2xl leading-none font-semibold">{start.getDate()}</span>
        </div>
      )}
      <div className="min-w-0 flex-1">
        <div className="font-semibold">{meeting.title || 'Mentoring session'}</div>
        <div className="text-base-content/60 text-sm">{start ? start.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : formatDate(meeting.session_date)}, {meeting.duration_minutes} min, {MEETING_FORMAT[meeting.meeting_format].toLowerCase()}</div>
        <div className="mt-1.5"><MeetingLinks meeting={meeting} /></div>
      </div>
    </div>
  )
}

const STATUS_TONE = { SCHEDULED: 'info', HELD: 'success', CANCELLED: 'ghost', NO_SHOW: 'warning' } as const
const STATUS_LABEL = { SCHEDULED: 'Scheduled', HELD: 'Held', CANCELLED: 'Cancelled', NO_SHOW: 'No show' } as const

export function MeetingsTable({ meetings, pairId, role, onReschedule }: { meetings: Meeting[]; pairId: number; role: 'STUDENT' | 'MENTOR' | 'ADMIN'; onReschedule?: (m: Meeting) => void }) {
  const actions = useWorkspaceActions(pairId)
  const [error, setError] = useState<unknown>(null)
  const [cancelling, setCancelling] = useState<Meeting | null>(null)
  const run = (p: Promise<unknown>) => p.then(() => setError(null)).catch(setError)
  if (!meetings.length) return <EmptyState title="No meetings yet" description="Sangam keeps dates, durations and formats only. What you discuss stays between you." />
  const now = Date.now()
  return (
    <div className="flex flex-col gap-2">
      <ErrorAlert error={error} />
      <ul className="rows">
        {meetings.map((m) => {
          const started = !m.start_at || new Date(m.start_at).getTime() <= now
          return (
            <li key={m.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3">
              <div className="min-w-44 flex-1">
                <div className="font-medium">{m.start_at ? formatDateTime(m.start_at) : formatDate(m.session_date)}</div>
                <div className="text-base-content/60 text-sm">{m.title ? `${m.title}, ` : ''}{m.duration_minutes} min, {MEETING_FORMAT[m.meeting_format].toLowerCase()}</div>
              </div>
              <span className="flex gap-1.5">
                <Badge tone={STATUS_TONE[m.status]}>{STATUS_LABEL[m.status]}</Badge>
                {m.status === 'HELD' && !m.mentor_confirmed && <Badge tone="warning">Awaiting mentor confirmation</Badge>}
              </span>
              <span className="flex flex-wrap justify-end gap-1.5">
                <MeetingLinks meeting={m} />
                {role === 'MENTOR' && m.status === 'HELD' && !m.mentor_confirmed && (
                  <button className="btn btn-primary btn-xs" disabled={actions.confirmMeeting.isPending} onClick={() => run(actions.confirmMeeting.mutateAsync(m.id))}><Check size={13} />Confirm</button>
                )}
                {role !== 'ADMIN' && m.status === 'SCHEDULED' && started && (
                  <>
                    <button className="btn btn-xs" onClick={() => run(actions.record.mutateAsync({ id: m.id, status: 'HELD' }))}>It happened</button>
                    <button className="btn btn-ghost btn-xs" onClick={() => run(actions.record.mutateAsync({ id: m.id, status: 'NO_SHOW' }))}>No show</button>
                  </>
                )}
                {role === 'MENTOR' && m.status === 'SCHEDULED' && !started && (
                  <>
                    <button className="btn btn-xs" onClick={() => onReschedule?.(m)}>Reschedule</button>
                    <button className="btn btn-ghost btn-xs text-error" onClick={() => setCancelling(m)}>Cancel</button>
                  </>
                )}
              </span>
            </li>
          )
        })}
      </ul>
      <Modal open={!!cancelling} onClose={() => setCancelling(null)} title="Cancel this meeting?" size="sm"
        subtitle={cancelling ? formatDateTime(cancelling.start_at) : undefined}
        actions={<><button className="btn btn-ghost btn-sm" onClick={() => setCancelling(null)}>Keep meeting</button>
          <button className="btn btn-error btn-sm" disabled={actions.cancel.isPending} onClick={async () => { if (cancelling) { await run(actions.cancel.mutateAsync(cancelling.id)); setCancelling(null) } }}>Cancel meeting</button></>}>
        <p className="text-sm">Your mentee is notified, and the Google Calendar event is cancelled for everyone invited.</p>
      </Modal>
    </div>
  )
}

export function LogMeetingModal({ pairId, open, onClose, role }: { pairId: number; open: boolean; onClose: () => void; role: 'STUDENT' | 'MENTOR' }) {
  const { logMeeting } = useWorkspaceActions(pairId)
  const { register, handleSubmit, reset } = useForm<{ session_date: string; duration_minutes: number; status: string; meeting_format: MeetingFormat }>({
    defaultValues: { session_date: todayISO(), duration_minutes: 45, status: 'HELD', meeting_format: 'VIDEO' },
  })
  const close = () => { reset(); logMeeting.reset(); onClose() }
  const onSubmit = handleSubmit(async (v) => { await logMeeting.mutateAsync({ ...v, duration_minutes: Number(v.duration_minutes) }); close() })
  return (
    <Modal open={open} onClose={close} title="Log a past meeting" size="sm"
      subtitle={role === 'STUDENT' ? 'Your mentor confirms meetings you log.' : 'Meetings you log are confirmed automatically.'}>
      <form onSubmit={onSubmit} className="grid grid-cols-2 gap-3">
        <Field label="Date"><input type="date" max={todayISO()} className="input w-full" {...register('session_date', { required: true })} /></Field>
        <Field label="Minutes"><input type="number" min={1} max={720} className="input w-full" {...register('duration_minutes', { required: true })} /></Field>
        <Field label="Format"><select className="select w-full" {...register('meeting_format')}>{Object.entries(MEETING_FORMAT).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
        <Field label="What happened"><select className="select w-full" {...register('status')}><option value="HELD">Held</option><option value="NO_SHOW">No show</option><option value="CANCELLED">Cancelled</option></select></Field>
        {logMeeting.isError && <div className="col-span-2"><ErrorAlert error={logMeeting.error} /></div>}
        <div className="col-span-2 mt-1 flex justify-end gap-2"><button type="button" className="btn btn-ghost" onClick={close}>Cancel</button><button className="btn btn-primary" disabled={logMeeting.isPending}>Log meeting</button></div>
      </form>
    </Modal>
  )
}

export function ScheduleMeetingModal({ pairId, open, onClose, meeting }: { pairId: number; open: boolean; onClose: () => void; meeting?: Meeting | null }) {
  const actions = useWorkspaceActions(pairId)
  const [result, setResult] = useState<Meeting | null>(null)
  const start = meeting?.start_at ? new Date(meeting.start_at) : null
  const time = (d: Date | null, fallback: string) => d ? d.toTimeString().slice(0, 5) : fallback
  const { register, handleSubmit, watch, setError, formState: { errors } } = useForm<ScheduleInput>({
    values: {
      date: start ? start.toLocaleDateString('en-CA') : todayISO(), start_time: time(start, '18:30'),
      end_time: time(meeting?.end_at ? new Date(meeting.end_at) : null, '19:15'), timezone: meeting?.timezone || browserTimeZone(),
      title: meeting?.title ?? '', meeting_format: meeting?.meeting_format ?? 'VIDEO', add_google_meet: true,
    },
  })
  const mutation = meeting ? actions.reschedule : actions.schedule
  const onSubmit = handleSubmit(async (values) => {
    try {
      setResult(meeting ? await actions.reschedule.mutateAsync({ id: meeting.id, ...values }) : await actions.schedule.mutateAsync(values))
    } catch (err) {
      for (const [field, message] of Object.entries(fieldErrors(err))) setError(field as keyof ScheduleInput, { message })
    }
  })
  const close = () => { setResult(null); mutation.reset(); onClose() }
  return (
    <Modal open={open} onClose={close} title={result ? (meeting ? 'Meeting moved' : 'Meeting scheduled') : meeting ? 'Reschedule meeting' : 'Schedule a meeting'}
      subtitle={!result && 'Your mentee gets a notification and, when your Google Calendar is connected, an invitation.'}>
      {result ? (
        <div className="flex flex-col gap-4">
          <div className="bg-success/10 flex items-center gap-3 rounded-xl p-4">
            <CalendarCheck2 size={22} className="text-success shrink-0" />
            <div><div className="font-semibold">{formatDateTime(result.start_at)}</div><div className="text-base-content/65 text-sm">{result.duration_minutes} min, {MEETING_FORMAT[result.meeting_format].toLowerCase()}</div></div>
          </div>
          {result.calendar_synced ? <p className="text-sm">The Google Calendar event is {meeting ? 'updated' : 'created'} and your mentee is invited.</p>
            : <p className="text-sm">Saved in Sangam only. Connect Google Calendar from Calendar &amp; Meetings to send calendar invitations.</p>}
          <MeetingLinks meeting={result} />
          <div className="flex justify-end"><button className="btn btn-primary" onClick={close}>Done</button></div>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="grid grid-cols-2 gap-3">
          <div className="col-span-2"><Field label="Event title" error={errors.title?.message}><input className="input w-full" placeholder="Mentoring session" {...register('title')} /></Field></div>
          <Field label="Date" error={errors.date?.message}><input type="date" min={todayISO()} className="input w-full" {...register('date', { required: true })} /></Field>
          <Field label="Time zone" error={errors.timezone?.message}><input className="input w-full" {...register('timezone', { required: true })} /></Field>
          <Field label="Starts" error={errors.start_time?.message}><input type="time" className="input w-full" {...register('start_time', { required: true })} /></Field>
          <Field label="Ends" error={errors.end_time?.message}><input type="time" className="input w-full" {...register('end_time', { required: true })} /></Field>
          <Field label="Format"><select className="select w-full" {...register('meeting_format')}>{Object.entries(MEETING_FORMAT).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
          {!meeting && (
            <label className="mt-7 flex cursor-pointer items-center gap-2 text-sm">
              <input type="checkbox" className="toggle toggle-primary toggle-sm" disabled={watch('meeting_format') !== 'VIDEO'} {...register('add_google_meet')} />Add a Google Meet link
            </label>
          )}
          {mutation.isError && Object.keys(fieldErrors(mutation.error)).length === 0 && <div className="col-span-2"><ErrorAlert error={mutation.error} /></div>}
          <div className="col-span-2 mt-1 flex justify-end gap-2">
            <button type="button" className="btn btn-ghost" onClick={close}>Cancel</button>
            <button className="btn btn-primary" disabled={mutation.isPending}><CalendarPlus size={16} />{meeting ? 'Move meeting' : 'Schedule meeting'}</button>
          </div>
        </form>
      )}
    </Modal>
  )
}

export function GoalsPanel({ pairId, editable }: { pairId: number; editable: boolean }) {
  const goals = useGoals(pairId)
  const actions = useWorkspaceActions(pairId)
  const [adding, setAdding] = useState(false)
  const { register, handleSubmit, reset } = useForm<{ title: string; target_date: string }>()
  if (goals.isPending) return <Loading />
  if (goals.isError) return <ErrorAlert error={goals.error} />
  const freeSlot = [1, 2, 3].find((s) => !goals.data.some((g) => g.slot === s))
  const close = () => { reset(); actions.addGoal.reset(); setAdding(false) }
  const onSubmit = handleSubmit(async (v) => { if (freeSlot) { await actions.addGoal.mutateAsync({ ...v, slot: freeSlot }); close() } })
  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-1.5" aria-hidden>
        {[1, 2, 3].map((slot) => {
          const g = goals.data.find((x) => x.slot === slot)
          return <span key={slot} className={`h-1.5 flex-1 rounded-full ${g?.completed ? 'bg-primary' : g ? 'bg-primary/30' : 'bg-base-300'}`} />
        })}
      </div>
      {goals.data.length === 0 && <p className="text-base-content/60 text-sm">No shared goals yet. Agree up to three, each with a target date.</p>}
      <ul className="flex flex-col gap-2">
        {goals.data.map((g) => (
          <li key={g.id}>
            <label className={`flex cursor-pointer items-center gap-3 rounded-xl border p-3 transition-colors ${g.completed ? 'bg-primary/8 border-transparent' : 'border-base-300 hover:border-primary/40'}`}>
              <input type="checkbox" className="checkbox checkbox-primary checkbox-sm" checked={g.completed} disabled={!editable || actions.toggleGoal.isPending}
                onChange={(e) => actions.toggleGoal.mutate({ id: g.id, completed: e.target.checked })} aria-label={`Mark "${g.title}" ${g.completed ? 'incomplete' : 'complete'}`} />
              <span className={`flex-1 ${g.completed ? 'text-base-content/55 line-through' : 'font-medium'}`}>{g.title}</span>
              <span className="text-base-content/50 text-xs whitespace-nowrap">by {formatDate(g.target_date)}</span>
            </label>
          </li>
        ))}
      </ul>
      {editable && freeSlot && <button className="btn btn-ghost btn-sm self-start" onClick={() => setAdding(true)}><Plus size={15} />Add a goal</button>}
      <ErrorAlert error={actions.toggleGoal.error} />
      <Modal open={adding} onClose={close} title="Add a shared goal" size="sm" subtitle={`${3 - goals.data.length} of 3 goal slots left.`}>
        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          <Field label="Goal"><input className="input w-full" maxLength={250} placeholder="Finish two portfolio projects" {...register('title', { required: true })} /></Field>
          <Field label="Target date"><input type="date" min={todayISO()} className="input w-full" {...register('target_date', { required: true })} /></Field>
          <ErrorAlert error={actions.addGoal.error} />
          <div className="flex justify-end gap-2"><button type="button" className="btn btn-ghost" onClick={close}>Cancel</button><button className="btn btn-primary" disabled={actions.addGoal.isPending}>Add goal</button></div>
        </form>
      </Modal>
    </div>
  )
}

const FEEDBACK_LABEL: Record<FeedbackKind, string> = { GENERAL: 'General feedback', PROGRESS: 'Fortnightly progress update', CHANGE_MENTOR: 'Ask for a different mentor', CLOSING: 'Closing feedback' }

export function FeedbackModal({ pairId, kinds, open, onClose }: { pairId: number; kinds: FeedbackKind[]; open: boolean; onClose: () => void }) {
  const { feedback } = useWorkspaceActions(pairId)
  const { register, handleSubmit, reset, watch } = useForm<{ kind: FeedbackKind; text: string }>({ defaultValues: { kind: kinds[0], text: '' } })
  const close = () => { reset({ kind: kinds[0], text: '' }); feedback.reset(); onClose() }
  const onSubmit = handleSubmit(async (v) => { await feedback.mutateAsync(v); close() })
  return (
    <Modal open={open} onClose={close} title="Write to IIC" subtitle="Only IIC staff read this. It is not shared with your mentorship partner.">
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <Field label="About"><select className="select w-full" {...register('kind')}>{kinds.map((k) => <option key={k} value={k}>{FEEDBACK_LABEL[k]}</option>)}</select></Field>
        <Field label="Your feedback" hint={`${watch('text')?.length ?? 0} of 4000 characters. Summarise progress and blockers; leave out private conversation.`}>
          <textarea className="textarea w-full" rows={6} maxLength={4000} {...register('text', { required: true })} />
        </Field>
        <ErrorAlert error={feedback.error} />
        <div className="flex justify-end gap-2"><button type="button" className="btn btn-ghost" onClick={close}>Cancel</button><button className="btn btn-primary" disabled={feedback.isPending}>Send to IIC</button></div>
      </form>
    </Modal>
  )
}

export function FeedbackPanel({ pairId, kinds, active }: { pairId: number; kinds: FeedbackKind[]; active: boolean }) {
  const list = useFeedback(pairId)
  const [writing, setWriting] = useState(false)
  return (
    <div className="flex flex-col gap-3">
      {active && <button className="btn btn-primary btn-sm self-start" onClick={() => setWriting(true)}><PenLine size={15} />Write to IIC</button>}
      {list.isPending ? <Loading /> : list.isError ? <ErrorAlert error={list.error} /> : list.data.length === 0 ? <p className="text-base-content/60 text-sm">You have not written to IIC yet.</p> : (
        <ul className="rows">
          {list.data.map((f) => (
            <li key={f.id} className="py-3">
              <div className="mb-1 flex items-center justify-between gap-2"><span className="text-sm font-semibold">{FEEDBACK_LABEL[f.kind]}</span><span className="text-base-content/50 text-xs">{formatDateTime(f.created_at)}</span></div>
              <p className="text-base-content/80 text-sm whitespace-pre-line">{f.text}</p>
            </li>
          ))}
        </ul>
      )}
      <FeedbackModal pairId={pairId} kinds={kinds} open={writing} onClose={() => setWriting(false)} />
    </div>
  )
}

export function OutcomesPanel({ pairId, canRecord }: { pairId: number; canRecord: boolean }) {
  const list = useOutcomes(pairId)
  const { outcome } = useWorkspaceActions(pairId)
  const [recording, setRecording] = useState(false)
  const { register, handleSubmit, reset } = useForm<{ kind: OutcomeKind; achieved_on: string; note: string }>({ defaultValues: { kind: 'INTERVIEW', achieved_on: todayISO(), note: '' } })
  const close = () => { reset(); outcome.reset(); setRecording(false) }
  const onSubmit = handleSubmit(async (v) => { await outcome.mutateAsync(v); close() })
  return (
    <div className="flex flex-col gap-3">
      {list.isPending ? <Loading /> : list.isError ? <ErrorAlert error={list.error} /> : list.data.length === 0 ? (
        <p className="text-base-content/60 text-sm">{canRecord ? 'Record interviews, internships, offers or admissions as they happen.' : 'No outcomes recorded yet.'}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {list.data.map((o) => (
            <li key={o.id} className="bg-accent/10 flex items-center gap-3 rounded-xl p-3">
              <Trophy size={18} className="text-accent shrink-0" />
              <div className="min-w-0 flex-1"><div className="font-semibold">{OUTCOME[o.kind]}</div>{o.note && <div className="text-base-content/65 text-sm">{o.note}</div>}</div>
              <span className="text-base-content/55 text-xs">{formatDate(o.achieved_on)}</span>
            </li>
          ))}
        </ul>
      )}
      {canRecord && <button className="btn btn-ghost btn-sm self-start" onClick={() => setRecording(true)}><Plus size={15} />Record an outcome</button>}
      <Modal open={recording} onClose={close} title="Record an outcome" size="sm">
        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          <Field label="Outcome"><select className="select w-full" {...register('kind')}>{Object.entries(OUTCOME).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
          <Field label="Achieved on"><input type="date" max={todayISO()} className="input w-full" {...register('achieved_on', { required: true })} /></Field>
          <Field label="Note (optional)" hint="For example, the company or programme."><input maxLength={500} className="input w-full" {...register('note')} /></Field>
          <ErrorAlert error={outcome.error} />
          <div className="flex justify-end gap-2"><button type="button" className="btn btn-ghost" onClick={close}>Cancel</button><button className="btn btn-primary" disabled={outcome.isPending}>Record outcome</button></div>
        </form>
      </Modal>
    </div>
  )
}

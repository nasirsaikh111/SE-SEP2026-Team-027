import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { CalendarPlus, CalendarX2, Clock, EyeOff, Link2Off, PenLine, RefreshCw } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { errorMessage } from '../../lib/api'
import { PATHWAY, formatDate, formatDateTime, timeAgo, truncate } from '../../lib/format'
import {
  useAvailability, useAvailabilityActions, useCalendarActions, useCalendarStatus, useDashboard, useMentorship,
  useMentorships, useMyMeetings, usePairMeetings, useProfileActions,
} from '../../lib/queries'
import type { AvailabilityCheck, Meeting, MentorDashboard, Mentorship } from '../../lib/types'
import { Badge, Card, EmptyState, ErrorAlert, Field, Loading, Modal, PageHeader, Tabs, TaskList, Timeline } from '../../components/ui'
import { CalendarBadge, FeedbackModal, FeedbackPanel, GoalsPanel, LogMeetingModal, MeetingsTable, MentorshipCard, OutcomesPanel, ScheduleMeetingModal, UpcomingMeeting } from '../../components/workspace'

function daysLeft(iso: string) {
  return Math.max(0, Math.ceil((new Date(iso).getTime() - Date.now()) / 86400000))
}

// ---------------------------------------------------------------- availability
/** Read an anonymised need and answer IIC. Student identity is shared only after IIC approval. */
export function AvailabilityReviewModal({ check, onClose }: { check: AvailabilityCheck | null; onClose: () => void }) {
  const { respond } = useAvailabilityActions()
  const [declining, setDeclining] = useState(false)
  const [reason, setReason] = useState('')
  const close = () => { setDeclining(false); setReason(''); respond.reset(); onClose() }
  const answer = async (decision: 'CONFIRMED' | 'DECLINED') => {
    if (!check) return
    await respond.mutateAsync({ id: check.id, decision, reason })
    close()
  }
  return (
    <Modal open={!!check} onClose={close} size="lg" title={check ? `Can you mentor someone in ${check.request_summary.domain}?` : ''}
      subtitle={check && `${PATHWAY[check.request_summary.pathway]} pathway. Please answer within ${daysLeft(check.expires_at)} day${daysLeft(check.expires_at) === 1 ? '' : 's'}.`}
      actions={check && (declining ? (
        <><button className="btn btn-ghost btn-sm" onClick={() => setDeclining(false)}>Back</button>
          <button className="btn btn-error btn-sm" disabled={respond.isPending} onClick={() => answer('DECLINED')}>Decline</button></>
      ) : (
        <><button className="btn btn-ghost btn-sm" onClick={() => setDeclining(true)}>I can't take this on</button>
          <button className="btn btn-primary btn-sm" disabled={respond.isPending} onClick={() => answer('CONFIRMED')}>Yes, I'm available</button></>
      ))}>
      {check && (
        <>
          <blockquote className="border-primary bg-base-200 rounded-r-xl border-l-4 px-4 py-3 whitespace-pre-line">{check.request_summary.problem_statement}</blockquote>
          <p className="text-base-content/60 flex items-center gap-2 text-sm"><EyeOff size={15} />The student's name and contact details are shared after IIC approves the pairing.</p>
          {declining && (
            <Field label="Reason for IIC (optional)" hint="Helps IIC find someone better suited.">
              <textarea className="textarea w-full" rows={3} maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
            </Field>
          )}
          <p className="text-sm">{declining ? 'IIC will offer the request to another mentor.' : 'Confirming does not start the mentorship yet. IIC gives the final approval, then you can contact your mentee.'}</p>
          <ErrorAlert error={respond.error} />
        </>
      )}
    </Modal>
  )
}

const CHECK_STATUS: Record<string, [string, 'success' | 'primary' | 'neutral' | 'ghost']> = {
  USED: ['Approved by IIC', 'success'], CONFIRMED: ['Waiting for IIC approval', 'primary'], DECLINED: ['Declined', 'neutral'], EXPIRED: ['Expired', 'ghost'],
}

export function AvailabilityRequestsPage() {
  const checks = useAvailability()
  const [reviewing, setReviewing] = useState<AvailabilityCheck | null>(null)
  const rows = checks.data?.results ?? []
  const pending = rows.filter((c) => c.status === 'PENDING' && !c.is_expired)
  const past = rows.filter((c) => !pending.includes(c))
  return (
    <>
      <PageHeader title="Availability requests" subtitle="IIC asks whether you can mentor a specific need. You see the need, not the student, until IIC approves." />
      {checks.isPending ? <Loading /> : checks.isError ? <ErrorAlert error={checks.error} /> : (
        <div className="flex flex-col gap-8">
          {pending.length === 0 ? <EmptyState title="Nothing to answer right now" description="We'll notify you when IIC thinks you're a good fit for a student." /> : (
            <ul className="grid gap-4 md:grid-cols-2">
              {pending.map((c) => (
                <li key={c.id}>
                  <button onClick={() => setReviewing(c)} className="panel hover:border-primary/50 flex h-full w-full flex-col gap-3 p-5 text-left transition-colors">
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-display text-lg font-semibold">{c.request_summary.domain}</span>
                      <span className="bg-accent/20 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold"><Clock size={12} />{daysLeft(c.expires_at)} days left</span>
                    </div>
                    <p className="text-base-content/70 text-sm">{truncate(c.request_summary.problem_statement, 180)}</p>
                    <span className="text-primary mt-auto text-sm font-semibold">Review and respond</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {past.length > 0 && (
            <Card title="Earlier requests">
              <ul className="rows">
                {past.map((c) => {
                  const [label, tone] = CHECK_STATUS[c.status] ?? (c.is_expired ? CHECK_STATUS.EXPIRED : ['Pending', 'neutral'])
                  return (
                    <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                      <span><span className="font-medium">{c.request_summary.domain}</span><span className="text-base-content/55 ml-2 text-sm">asked {formatDate(c.sent_at)}</span></span>
                      <Badge tone={tone}>{label}</Badge>
                    </li>
                  )
                })}
              </ul>
            </Card>
          )}
        </div>
      )}
      <AvailabilityReviewModal check={reviewing} onClose={() => setReviewing(null)} />
    </>
  )
}

// ------------------------------------------------------------------- workspace
function useActivePair() {
  const list = useMentorships({ status: 'ACTIVE' })
  return { list, pair: list.data?.results[0] as Mentorship | undefined }
}

export function AvailabilityToggle({ compact = false }: { compact?: boolean }) {
  const { me } = useAuth()
  const { availability } = useProfileActions()
  const profile = me?.mentor_profile
  if (!profile) return null
  return (
    <label className={`flex cursor-pointer items-center gap-3 ${compact ? '' : 'justify-between'}`}>
      <span className="text-sm">{!profile.is_verified ? 'Available after IIC verifies you' : profile.is_available ? 'Open to new mentees' : 'Not taking new mentees'}</span>
      <input type="checkbox" className="toggle toggle-primary" checked={profile.is_available} disabled={!profile.is_verified || availability.isPending}
        onChange={(e) => availability.mutate(e.target.checked)} aria-label="Open to new mentees" />
    </label>
  )
}

type WorkspaceTab = 'overview' | 'meetings' | 'goals' | 'progress' | 'history'

export function MentorWorkspacePage() {
  const { list, pair } = useActivePair()
  const dashboard = useDashboard()
  const detail = useMentorship(pair?.id)
  const meetings = usePairMeetings(pair?.id)
  const [params, setParams] = useSearchParams()
  const tab = (params.get('tab') as WorkspaceTab) || 'overview'
  const [modal, setModal] = useState<{ kind: 'schedule' | 'log' | 'feedback' | null; meeting?: Meeting | null }>({ kind: null })
  if (list.isPending) return <Loading />
  if (list.isError) return <ErrorAlert error={list.error} />
  if (!pair) {
    return (
      <>
        <PageHeader title="Mentorship workspace" />
        <div className="panel mb-6 max-w-md p-5"><AvailabilityToggle /></div>
        <EmptyState title="No active mentee" description="Your workspace opens when IIC approves a pairing you confirmed." action={<Link to="/mentor/availability" className="btn btn-sm">Availability requests</Link>} />
      </>
    )
  }
  const d = dashboard.data?.role === 'MENTOR' ? (dashboard.data as MentorDashboard) : null
  const unconfirmed = meetings.data?.filter((m) => m.status === 'HELD' && !m.mentor_confirmed).length ?? 0
  const close = () => setModal({ kind: null })
  return (
    <>
      <PageHeader title="Mentorship workspace" actions={<>
        <button className="btn" onClick={() => setModal({ kind: 'log' })}>Log a past meeting</button>
        <button className="btn btn-primary" onClick={() => setModal({ kind: 'schedule' })}><CalendarPlus size={17} />Schedule meeting</button>
      </>} />
      <div className="mb-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <MentorshipCard pair={pair} viewer="MENTOR" />
        <div className="flex flex-col gap-4">
          <div className="panel p-5"><AvailabilityToggle /></div>
          <div className="panel flex flex-col gap-2 p-5"><h2 className="font-semibold">Next meeting</h2><UpcomingMeeting meeting={pair.progress.next_meeting} /></div>
          {d && d.tasks.length > 0 && <div className="panel flex flex-col gap-2 p-5"><h2 className="font-semibold">Waiting on you</h2><TaskList tasks={d.tasks} /></div>}
        </div>
      </div>
      <Tabs<WorkspaceTab> value={tab} onChange={(t) => setParams(t === 'overview' ? {} : { tab: t })} tabs={[
        { key: 'overview', label: 'Overview' }, { key: 'meetings', label: 'Meetings', count: unconfirmed || undefined },
        { key: 'goals', label: 'Goals' }, { key: 'progress', label: 'Progress' }, { key: 'history', label: 'History' },
      ]} />
      {tab === 'overview' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Recent milestones">
            {detail.isPending ? <Loading /> : detail.isError ? <ErrorAlert error={detail.error} /> :
              <Timeline items={detail.data.timeline.slice(0, 5).map((t, i) => ({ key: i, title: t.title, detail: t.detail, at: t.at }))} />}
          </Card>
          <Card title="Shared goals"><GoalsPanel pairId={pair.id} editable /></Card>
        </div>
      )}
      {tab === 'meetings' && (
        <Card title="Meeting history">
          {meetings.isPending ? <Loading /> : meetings.isError ? <ErrorAlert error={meetings.error} /> :
            <MeetingsTable meetings={meetings.data} pairId={pair.id} role="MENTOR" onReschedule={(m) => setModal({ kind: 'schedule', meeting: m })} />}
        </Card>
      )}
      {tab === 'goals' && <Card title="Shared goals"><GoalsPanel pairId={pair.id} editable /></Card>}
      {tab === 'progress' && (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Progress updates to IIC"><FeedbackPanel pairId={pair.id} kinds={['PROGRESS', 'GENERAL', 'CLOSING']} active /></Card>
          <Card title="Outcomes"><p className="text-base-content/60 text-sm">Your mentee records outcomes. To suggest ending the mentorship, send IIC closing feedback.</p><OutcomesPanel pairId={pair.id} canRecord={false} /></Card>
        </div>
      )}
      {tab === 'history' && (
        <Card title="Everything so far">
          {detail.isPending ? <Loading /> : detail.isError ? <ErrorAlert error={detail.error} /> :
            <Timeline items={detail.data.timeline.map((t, i) => ({ key: i, title: t.title, detail: t.detail, at: t.at, tone: t.type === 'goal' || t.type === 'outcome' ? 'success' : undefined }))} />}
        </Card>
      )}
      <ScheduleMeetingModal pairId={pair.id} open={modal.kind === 'schedule'} meeting={modal.meeting} onClose={close} />
      <LogMeetingModal pairId={pair.id} open={modal.kind === 'log'} onClose={close} role="MENTOR" />
    </>
  )
}

// -------------------------------------------------------------------- calendar
export function CalendarMeetingsPage() {
  const status = useCalendarStatus()
  const { connect, disconnect } = useCalendarActions()
  const { pair } = useActivePair()
  const meetings = useMyMeetings()
  const [params, setParams] = useSearchParams()
  const [scheduling, setScheduling] = useState<{ open: boolean; meeting?: Meeting | null }>({ open: false })
  const [confirmDisconnect, setConfirmDisconnect] = useState(false)
  const result = params.get('calendar')

  useEffect(() => { if (result) status.refetch() }, [result]) // eslint-disable-line react-hooks/exhaustive-deps

  const startConnect = async () => {
    const { authorization_url } = await connect.mutateAsync()
    window.location.assign(authorization_url)
  }
  const s = status.data
  const mine = (meetings.data?.results ?? []).filter((m) => !pair || m.mentorship === pair.id)
  return (
    <>
      <PageHeader title="Calendar & meetings" actions={pair && <button className="btn btn-primary" onClick={() => setScheduling({ open: true })}><CalendarPlus size={17} />Schedule meeting</button>} />
      {result && (
        <div role="status" className={`mb-5 flex items-center justify-between gap-2 rounded-2xl px-4 py-3 text-sm ${result === 'connected' ? 'bg-success/12' : 'bg-accent/15'}`}>
          {result === 'connected' ? 'Google Calendar is connected. New meetings will appear in your calendar.' : result === 'denied' ? 'Google Calendar access was not granted, so nothing changed.' : 'Google Calendar could not be connected. Try again.'}
          <button className="btn btn-ghost btn-xs" onClick={() => setParams({})}>Dismiss</button>
        </div>
      )}
      <div className="grid gap-6 lg:grid-cols-[22rem_minmax(0,1fr)]">
        <section className="bg-neutral text-neutral-content rounded-hero flex flex-col gap-4 p-6">
          <h2 className="font-display text-xl font-semibold text-white">Google Calendar</h2>
          {status.isPending ? <Loading /> : status.isError ? <ErrorAlert error={status.error} /> : s && (
            <>
              <CalendarBadge status={s.status} />
              {s.google_email && <p className="text-neutral-content/80 text-sm">Connected as {s.google_email} since {formatDate(s.connected_at)}.</p>}
              {!s.configured ? <p className="text-neutral-content/70 text-sm">Calendar sync isn't switched on for Sangam yet. Meetings you schedule are still saved and shown to your mentee.</p> : (
                <div className="flex flex-wrap gap-2">
                  {s.status !== 'CONNECTED' && <button className="btn btn-sm border-0 bg-[#4fb3a2] text-[#062019] hover:bg-[#62c3b2]" disabled={connect.isPending} onClick={startConnect}>
                    {s.status === 'REAUTH_REQUIRED' ? <><RefreshCw size={15} />Reconnect</> : 'Connect Google Calendar'}</button>}
                  {s.status !== 'DISCONNECTED' && <button className="btn btn-sm border-0 bg-white/10 text-white hover:bg-white/20" onClick={() => setConfirmDisconnect(true)}><Link2Off size={15} />Disconnect</button>}
                </div>
              )}
              {connect.isError && <p className="text-sm text-[#ef7f74]">{errorMessage(connect.error)}</p>}
              <p className="text-neutral-content/55 mt-auto text-xs">Sangam only creates events for your mentoring sessions, with a Meet link, and invites your mentee. It never reads your other events.</p>
            </>
          )}
        </section>
        <Card title="Your meetings">
          {!pair && <p className="text-base-content/60 text-sm">You can schedule meetings while you have an active mentee.</p>}
          {meetings.isPending ? <Loading /> : meetings.isError ? <ErrorAlert error={meetings.error} /> : mine.length === 0 ? (
            <EmptyState icon={<CalendarX2 size={26} />} title="No meetings yet" description="Schedule the first session to get started." />
          ) : pair ? (
            <MeetingsTable meetings={mine} pairId={pair.id} role="MENTOR" onReschedule={(m) => setScheduling({ open: true, meeting: m })} />
          ) : (
            <ul className="rows">{mine.map((m) => <li key={m.id} className="py-3 text-sm">{formatDateTime(m.start_at ?? m.session_date)}<span className="text-base-content/55 ml-2">{m.status.toLowerCase()}</span></li>)}</ul>
          )}
        </Card>
      </div>
      {pair && <ScheduleMeetingModal pairId={pair.id} open={scheduling.open} meeting={scheduling.meeting} onClose={() => setScheduling({ open: false })} />}
      <Modal open={confirmDisconnect} onClose={() => setConfirmDisconnect(false)} size="sm" title="Disconnect Google Calendar?"
        actions={<><button className="btn btn-ghost btn-sm" onClick={() => setConfirmDisconnect(false)}>Keep connected</button>
          <button className="btn btn-error btn-sm" disabled={disconnect.isPending} onClick={async () => { await disconnect.mutateAsync(); setConfirmDisconnect(false) }}>Disconnect</button></>}>
        <p className="text-sm">Sangam deletes its access to your calendar. Existing events stay in Google Calendar, but changes you make in Sangam will no longer sync.</p>
      </Modal>
    </>
  )
}

// -------------------------------------------------------------------- feedback
export function FeedbackProgressPage() {
  const { list, pair } = useActivePair()
  const dashboard = useDashboard()
  const [writing, setWriting] = useState(false)
  if (list.isPending) return <Loading />
  if (list.isError) return <ErrorAlert error={list.error} />
  if (!pair) return <><PageHeader title="Feedback & progress" /><EmptyState title="No active mentee" description="Fortnightly progress updates start once a mentorship is active." /></>
  const fb = dashboard.data?.role === 'MENTOR' ? (dashboard.data as MentorDashboard).feedback : null
  return (
    <>
      <PageHeader title="Feedback & progress" subtitle="Every two weeks, send IIC a short written update on how your mentee is doing."
        actions={<button className="btn btn-primary" onClick={() => setWriting(true)}><PenLine size={17} />Write an update</button>} />
      {fb && (
        <div className={`mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl px-5 py-4 ${fb.due ? 'bg-accent/18' : 'bg-success/10'}`}>
          <div>
            <p className="font-semibold">{fb.due ? 'Your fortnightly update is due' : `Next update due ${formatDate(fb.next_due_at)}`}</p>
            <p className="text-base-content/65 text-sm">Last sent {fb.last_submitted_at ? timeAgo(fb.last_submitted_at) : 'never'}.</p>
          </div>
          {fb.due && <button className="btn btn-sm" onClick={() => setWriting(true)}>Write it now</button>}
        </div>
      )}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_24rem]">
        <Card title="What you've sent"><FeedbackPanel pairId={pair.id} kinds={['PROGRESS', 'GENERAL', 'CLOSING']} active={false} /></Card>
        <div className="flex flex-col gap-6">
          <Card title="Goal progress"><GoalsPanel pairId={pair.id} editable /></Card>
          <Card title="Outcomes"><OutcomesPanel pairId={pair.id} canRecord={false} /></Card>
        </div>
      </div>
      <FeedbackModal pairId={pair.id} kinds={['PROGRESS', 'GENERAL', 'CLOSING']} open={writing} onClose={() => setWriting(false)} />
    </>
  )
}

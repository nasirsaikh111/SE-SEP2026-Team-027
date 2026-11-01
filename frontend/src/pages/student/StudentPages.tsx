import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { CalendarPlus, Plus } from 'lucide-react'
import { PATHWAY, formatDate, timeAgo, truncate } from '../../lib/format'
import { useMentorship, useMentorships, usePairMeetings, useRequests } from '../../lib/queries'
import type { Mentorship } from '../../lib/types'
import { Card, EmptyState, ErrorAlert, Loading, PageHeader, StageBadge, Timeline } from '../../components/ui'
import { FeedbackPanel, GoalsPanel, LogMeetingModal, MeetingsTable, MentorshipCard, OutcomesPanel, UpcomingMeeting } from '../../components/workspace'
import { Confluence } from '../../components/Confluence'
import { RequestDetailModal, RequestFormModal, useOpenRequest } from './requestModals'

// ------------------------------------------------------------------ my requests
export function MyRequestsPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const requests = useRequests()
  const { open } = useOpenRequest()
  const [creating, setCreating] = useState(false)
  const selected = id ? Number(id) : null
  const rows = requests.data?.results ?? []
  const current = rows.find((r) => ['SUBMITTED', 'UNDER_REVIEW', 'WAITING'].includes(r.status))
  const past = rows.filter((r) => r !== current)
  return (
    <>
      <PageHeader title="My requests" subtitle="You can have one request with IIC at a time. Open any request to follow its progress."
        actions={<button className="btn btn-primary" disabled={!!open} onClick={() => setCreating(true)} title={open ? 'You already have an open request or an active mentorship' : undefined}><Plus size={17} />New request</button>} />
      {requests.isPending ? <Loading /> : requests.isError ? <ErrorAlert error={requests.error} /> : rows.length === 0 ? (
        <EmptyState title="You haven't asked for a mentor yet" description="Browse verified alumni and name someone you'd like, or describe your goal and let IIC suggest a match."
          action={<div className="flex gap-2"><Link to="/discover" className="btn btn-primary btn-sm">Discover mentors</Link><button className="btn btn-sm" onClick={() => setCreating(true)}>Describe my goal</button></div>} />
      ) : (
        <div className="flex flex-col gap-8">
          {current && (
            <button onClick={() => navigate(`/requests/${current.id}`)} className="bg-neutral text-neutral-content rounded-hero p-6 text-left transition-transform hover:-translate-y-0.5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="max-w-xl">
                  <p className="text-neutral-content/60 text-sm">With IIC now, sent {formatDate(current.submitted_at)}</p>
                  <h2 className="font-display text-title mt-1 font-semibold text-white">{current.domain}</h2>
                  <p className="text-neutral-content/75 mt-1 text-sm">{truncate(current.problem_statement, 150)}</p>
                </div>
                <span className="rounded-full bg-white/12 px-3 py-1 text-xs font-semibold text-white">{current.stage_label}</span>
              </div>
              <div className="mt-4"><Confluence stage={current.stage} tone="dark" waiting={current.stage === 'WAITING'} /></div>
              <p className="text-neutral-content/70 mt-1 text-sm">{current.next_action}</p>
            </button>
          )}
          {past.length > 0 && (
            <section>
              <h2 className="mb-3 text-lg font-semibold">{current ? 'Earlier requests' : 'Your requests'}</h2>
              <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {past.map((r) => (
                  <li key={r.id}>
                    <button onClick={() => navigate(`/requests/${r.id}`)} className="panel hover:border-primary/50 flex h-full w-full flex-col gap-2 p-5 text-left transition-colors">
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-display text-lg font-semibold">{r.domain}</span>
                        <StageBadge stage={r.stage} />
                      </div>
                      <p className="text-base-content/65 text-sm">{truncate(r.problem_statement, 110)}</p>
                      <div className="text-base-content/55 mt-auto flex flex-wrap gap-x-4 pt-2 text-xs">
                        <span>{PATHWAY[r.pathway]}</span>
                        <span>Sent {formatDate(r.submitted_at)}</span>
                        <span>Updated {timeAgo(r.last_status_at)}</span>
                        {r.assigned_mentor && <span className="text-primary font-medium">Mentor: {r.assigned_mentor.name}</span>}
                        {!r.assigned_mentor && r.preferred_mentor_summary && <span>Preferred: {r.preferred_mentor_summary.name}</span>}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
      <RequestFormModal open={creating} onClose={() => setCreating(false)} />
      <RequestDetailModal requestId={selected} onClose={() => navigate('/requests')} />
    </>
  )
}

// ----------------------------------------------------------------- my mentorship
export function useCurrentPair() {
  const list = useMentorships()
  const pairs = list.data?.results ?? []
  const pair: Mentorship | undefined = pairs.find((p) => p.status === 'ACTIVE') ?? pairs[0]
  return { list, pair }
}

function NoMentorship() {
  return <EmptyState title="No mentor yet" description="Your mentor appears here once IIC approves the pairing." action={<Link to="/requests" className="btn btn-sm">See my requests</Link>} />
}

export function MyMentorshipPage() {
  const { list, pair } = useCurrentPair()
  const detail = useMentorship(pair?.id)
  if (list.isPending) return <Loading />
  if (list.isError) return <ErrorAlert error={list.error} />
  return (
    <>
      <PageHeader title="My mentorship" />
      {!pair ? <NoMentorship /> : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
          <div className="flex flex-col gap-6">
            <MentorshipCard pair={pair} viewer="STUDENT" />
            {pair.closure_type === 'REASSIGNED' && <div className="bg-accent/15 rounded-2xl px-4 py-3 text-sm">IIC closed this pairing and is arranging a new mentor for you. Your request is back in the matching queue.</div>}
            <Card title="Next meeting" actions={<Link to="/meetings-goals" className="link link-hover text-sm">All meetings</Link>}><UpcomingMeeting meeting={pair.progress.next_meeting} /></Card>
            <Card title="Feedback to IIC">
              <p className="text-base-content/65 text-sm">Tell IIC how it's going, ask for a different mentor, or share closing feedback. Your mentor does not see this.</p>
              <FeedbackPanel pairId={pair.id} kinds={['GENERAL', 'CHANGE_MENTOR', 'CLOSING']} active={pair.status === 'ACTIVE'} closed={pair.status === 'CLOSED'} />
              {pair.status === 'CLOSED' && <p className="text-base-content/65 mt-3 text-sm">Got an interview, offer or admission? <Link to="/meetings-goals" className="link link-primary">Record the outcome</Link> so IIC can see what the programme achieved.</p>}
            </Card>
          </div>
          <Card title="Milestones">
            {detail.isPending ? <Loading /> : detail.isError ? <ErrorAlert error={detail.error} /> :
              <Timeline items={detail.data.timeline.map((t, i) => ({ key: `${t.type}-${i}`, title: t.title, detail: t.detail, at: t.at, tone: t.type === 'goal' || t.type === 'outcome' ? 'success' : undefined }))} />}
          </Card>
        </div>
      )}
    </>
  )
}

export function MeetingsGoalsPage() {
  const { list, pair } = useCurrentPair()
  const meetings = usePairMeetings(pair?.id)
  const [logging, setLogging] = useState(false)
  if (list.isPending) return <Loading />
  if (list.isError) return <ErrorAlert error={list.error} />
  if (!pair) return <><PageHeader title="Meetings & goals" /><NoMentorship /></>
  const active = pair.status === 'ACTIVE'
  return (
    <>
      <PageHeader title="Meetings & goals" subtitle="Sangam records when you met and for how long, never what you discussed."
        actions={active && <button className="btn btn-primary" onClick={() => setLogging(true)}><CalendarPlus size={17} />Log a meeting</button>} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Shared goals"><GoalsPanel pairId={pair.id} editable={active} /></Card>
        <Card title="Outcomes"><OutcomesPanel pairId={pair.id} canRecord /></Card>
        <Card title="Meetings" className="lg:col-span-2">
          {meetings.isPending ? <Loading /> : meetings.isError ? <ErrorAlert error={meetings.error} /> : <MeetingsTable meetings={meetings.data} pairId={pair.id} role="STUDENT" />}
        </Card>
      </div>
      <LogMeetingModal pairId={pair.id} open={logging} onClose={() => setLogging(false)} role="STUDENT" />
    </>
  )
}

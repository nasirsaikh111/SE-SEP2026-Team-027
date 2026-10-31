import { useState } from 'react'
import { Link } from 'react-router'
import { Clock } from 'lucide-react'
import { formatDate, timeAgo, truncate } from '../../lib/format'
import type { AvailabilityCheck, MentorDashboard } from '../../lib/types'
import { Card, TaskList, Timeline } from '../../components/ui'
import { CalendarBadge, MentorshipCard, UpcomingMeeting } from '../../components/workspace'
import { AvailabilityReviewModal, AvailabilityToggle } from '../mentor/MentorPages'
import { greeting } from '../Dashboard'

export default function MentorHome({ d }: { d: MentorDashboard }) {
  const [reviewing, setReviewing] = useState<AvailabilityCheck | null>(null)
  const name = d.display_name.split(' ')[0]
  const asks = d.pending_checks.length
  return (
    <>
      <section className="bg-neutral text-neutral-content rounded-hero mb-8 flex flex-wrap items-end justify-between gap-6 px-6 py-7 sm:px-9">
        <div className="max-w-xl">
          <p className="text-neutral-content/60">{greeting()}, {name}</p>
          <h1 className="font-display text-title sm:text-display mt-1 font-semibold text-white">
            {asks ? `IIC would like to know if you can mentor ${asks === 1 ? 'a student' : `${asks} students`}.` : d.mentorship ? `${d.mentorship.student_name} is your mentee.` : 'No one is waiting on you right now.'}
          </h1>
        </div>
        <div className="flex flex-col gap-3 rounded-2xl bg-white/8 p-4 [&_span]:text-white">
          <AvailabilityToggle compact />
          <CalendarBadge status={d.calendar.status} />
        </div>
      </section>

      {asks > 0 && (
        <section className="mb-8">
          <h2 className="mb-3 text-lg font-semibold">Asked by IIC</h2>
          <ul className="grid gap-4 md:grid-cols-2">
            {d.pending_checks.map((c) => (
              <li key={c.id}>
                <button onClick={() => setReviewing(c)} className="panel border-accent/50 hover:border-accent flex h-full w-full flex-col gap-2 p-5 text-left transition-colors">
                  <span className="flex items-start justify-between gap-2"><span className="font-display text-lg font-semibold">{c.request_summary.domain}</span>
                    <span className="bg-accent/20 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold"><Clock size={12} />by {formatDate(c.expires_at)}</span></span>
                  <span className="text-base-content/70 text-sm">{truncate(c.request_summary.problem_statement, 160)}</span>
                  <span className="text-primary mt-auto text-sm font-semibold">Review and respond</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex flex-col gap-6">
          {d.mentorship ? <MentorshipCard pair={d.mentorship} viewer="MENTOR" /> : (
            <Card title="Mentee"><p className="text-base-content/60 text-sm">When you confirm an availability check and IIC approves, your mentee appears here with their contact details.</p></Card>
          )}
          <div className="grid gap-6 sm:grid-cols-2">
            <Card title="Coming up" actions={<Link to="/mentor/calendar" className="link link-hover text-sm">Calendar</Link>}>
              {d.upcoming_meetings.length ? <div className="flex flex-col gap-4">{d.upcoming_meetings.map((m) => <UpcomingMeeting key={m.id} meeting={m} />)}</div> : <p className="text-base-content/60 text-sm">No meetings scheduled.</p>}
            </Card>
            <Card title="Progress update for IIC">
              {d.feedback ? (
                <>
                  <p className={`font-display text-xl font-semibold ${d.feedback.due ? 'text-accent' : ''}`}>{d.feedback.due ? 'Due now' : `Due ${formatDate(d.feedback.next_due_at)}`}</p>
                  <p className="text-base-content/60 text-sm">Last sent {d.feedback.last_submitted_at ? timeAgo(d.feedback.last_submitted_at) : 'never'}.</p>
                  <Link to="/mentor/feedback" className="btn btn-sm self-start">Write an update</Link>
                </>
              ) : <p className="text-base-content/60 text-sm">Starts once you have an active mentee.</p>}
            </Card>
          </div>
        </div>
        <div className="flex flex-col gap-6">
          <Card title="Your move"><TaskList tasks={d.tasks} /></Card>
          <Card title="Recent activity"><Timeline items={d.recent_activity.map((h) => ({ key: h.id, title: h.label, detail: h.note, at: h.created_at }))} /></Card>
        </div>
      </div>
      <AvailabilityReviewModal check={reviewing} onClose={() => setReviewing(null)} />
    </>
  )
}

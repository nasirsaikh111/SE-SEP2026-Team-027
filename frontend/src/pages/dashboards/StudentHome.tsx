import { Link, useNavigate } from 'react-router'
import { Compass, Lightbulb } from 'lucide-react'
import { PATHWAY, formatDate } from '../../lib/format'
import type { StudentDashboard } from '../../lib/types'
import { Card, StageBadge, TaskList, Timeline } from '../../components/ui'
import { UpcomingMeeting } from '../../components/workspace'
import { Confluence } from '../../components/Confluence'
import { greeting } from '../Dashboard'

function Hero({ d }: { d: StudentDashboard }) {
  const navigate = useNavigate()
  const name = d.display_name.split(' ')[0]
  const req = d.current_request
  const pair = d.mentorship

  let line: string
  let body = null
  if (d.approval_status === 'PENDING') line = 'IIC is verifying your registration. You can ask for a mentor once that’s done.'
  else if (d.approval_status === 'REJECTED') line = 'IIC could not approve your registration yet. Update your profile and it goes back for review.'
  else if (pair) {
    line = `You’re mentored by ${pair.mentor_name}${pair.mentor_profile?.company ? ` from ${pair.mentor_profile.company}` : ''}.`
    body = <Confluence stage="ACTIVE" tone="dark" />
  } else if (req) {
    line = req.next_action
    body = <Confluence stage={req.stage} tone="dark" waiting={req.stage === 'WAITING'} />
  } else line = 'Find an alumnus who has walked the path you’re on, and ask IIC to pair you.'

  return (
    <section className="bg-neutral text-neutral-content rounded-hero relative mb-8 overflow-hidden px-6 pt-7 pb-5 sm:px-9">
      <p className="text-neutral-content/60">{greeting()}, {name}</p>
      <h1 className="font-display text-title sm:text-display mt-1 max-w-2xl font-semibold text-white">{line}</h1>
      {body && <div className="mt-6 max-w-3xl">{body}</div>}
      <div className="mt-5 flex flex-wrap gap-2">
        {pair && <Link to="/mentorship" className="btn border-0 bg-[#4fb3a2] text-[#062019] hover:bg-[#62c3b2]">Open my mentorship</Link>}
        {!pair && req && <button onClick={() => navigate(`/requests/${req.id}`)} className="btn border-0 bg-[#4fb3a2] text-[#062019] hover:bg-[#62c3b2]">Follow my request</button>}
        {!pair && !req && d.approval_status === 'APPROVED' && <Link to="/discover" className="btn border-0 bg-[#f0b54a] text-[#2a1c02] hover:bg-[#f5c46a]"><Compass size={17} />Discover mentors</Link>}
        {d.approval_status !== 'APPROVED' && <Link to="/profile" className="btn border-0 bg-white/12 text-white hover:bg-white/20">View my profile</Link>}
      </div>
    </section>
  )
}

export default function StudentHome({ d }: { d: StudentDashboard }) {
  const navigate = useNavigate()
  return (
    <>
      <Hero d={d} />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex flex-col gap-6">
          <div className="grid gap-6 sm:grid-cols-2">
            <Card title="Next meeting"><UpcomingMeeting meeting={d.upcoming_meeting} /></Card>
            <Card title="Shared goals" actions={d.mentorship && <Link to="/meetings-goals" className="link link-hover text-sm">Open</Link>}>
              {d.goals.total ? (
                <div className="flex items-end gap-4">
                  <span className="font-display text-display font-semibold tabular-nums">{d.goals.completed}<span className="text-base-content/35 text-title">/{d.goals.total}</span></span>
                  <span className="text-base-content/65 pb-1.5 text-sm">{d.goals.total - d.goals.completed === 0 ? 'All done.' : `${d.goals.total - d.goals.completed} still to go`}</span>
                </div>
              ) : <p className="text-base-content/60 text-sm">{d.mentorship ? 'Agree up to three goals with your mentor.' : 'Goals start once you have a mentor.'}</p>}
            </Card>
          </div>
          <Card title="Recent requests" actions={<Link to="/requests" className="link link-hover text-sm">All requests</Link>}>
            {d.recent_requests.length ? (
              <ul className="rows">
                {d.recent_requests.map((r) => (
                  <li key={r.id}>
                    <button onClick={() => navigate(`/requests/${r.id}`)} className="row-link -mx-2 flex w-[calc(100%+1rem)] items-center justify-between gap-2 px-2 py-2.5 text-left">
                      <span><span className="font-medium">{r.domain}</span><span className="text-base-content/55 ml-2 text-sm">{PATHWAY[r.pathway].toLowerCase()}, {formatDate(r.submitted_at)}</span></span>
                      <StageBadge stage={r.stage} />
                    </button>
                  </li>
                ))}
              </ul>
            ) : <p className="text-base-content/60 text-sm">You haven’t sent a request yet.</p>}
          </Card>
          <Card title="What changed recently">
            <Timeline items={d.recent_activity.map((h) => ({ key: h.id, title: h.label, detail: h.note, at: h.created_at }))} />
          </Card>
        </div>
        <div className="flex flex-col gap-6">
          <Card title="Your move"><TaskList tasks={d.tasks} /></Card>
          {d.next_steps.length > 0 && (
            <Card title={<span className="inline-flex items-center gap-2"><Lightbulb size={17} className="text-accent" />Suggested next steps</span>}>
              <ul className="flex flex-col gap-1">
                {d.next_steps.map((s) => (
                  <li key={s.title}><Link to={s.link} className="row-link -mx-2 block px-2 py-2"><span className="block font-medium">{s.title}</span><span className="text-base-content/60 block text-sm">{s.detail}</span></Link></li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
    </>
  )
}

import { useState } from 'react'
import { Link } from 'react-router'
import { timeAgo, truncate } from '../../lib/format'
import type { AdminDashboard, AvailabilityCheck } from '../../lib/types'
import { Card, PriorityBadge, RowButton, Stat, TaskList } from '../../components/ui'
import { CategoryBars } from '../../components/charts'
import { RequestReviewModal } from '../admin/AdminReview'
import { ApprovePairingModal } from '../admin/AdminOperations'
import { greeting } from '../Dashboard'

export default function AdminHome({ d }: { d: AdminDashboard }) {
  const [reviewing, setReviewing] = useState<number | null>(null)
  const [approving, setApproving] = useState<AvailabilityCheck | null>(null)
  const c = d.counts
  const waiting = c.students_pending + c.requests_awaiting_review + c.matches_awaiting_approval + c.mentors_unverified
  return (
    <>
      <section className="mb-6">
        <p className="text-base-content/60">{greeting()}, {d.display_name.split(' ')[0]}</p>
        <h1 className="font-display text-title sm:text-display mt-1 max-w-3xl font-semibold">
          {waiting ? `${waiting} ${waiting === 1 ? 'decision is' : 'decisions are'} waiting for IIC.` : 'Every queue is clear.'}
        </h1>
      </section>

      <div className="panel mb-8 grid grid-cols-2 gap-1 p-3 md:grid-cols-3 xl:grid-cols-6">
        <Stat label="Students to approve" value={c.students_pending} to="/admin/students" attention={c.students_pending > 0} />
        <Stat label="Mentors to verify" value={c.mentors_unverified} to="/admin/mentors?verified=false" attention={c.mentors_unverified > 0} />
        <Stat label="Requests to review" value={c.requests_awaiting_review} to="/admin/requests?queue=review" attention={c.requests_awaiting_review > 0} />
        <Stat label="Waiting for mentors" value={c.checks_pending} to="/admin/matching?tab=pending" />
        <Stat label="Pairings to approve" value={c.matches_awaiting_approval} to="/admin/matching?tab=confirmed" attention={c.matches_awaiting_approval > 0} />
        <Stat label="Active mentorships" value={c.active_mentorships} to="/admin/mentorships"
          hint={c.inactivity_alerts ? `${c.inactivity_alerts} need a nudge` : `${c.outcomes} outcomes so far`} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex flex-col gap-6">
          <Card title="Requests to review" actions={<Link to="/admin/requests" className="link link-hover text-sm">All requests</Link>}>
            {d.review_queue.length ? (
              <ul className="rows">
                {d.review_queue.map((r) => (
                  <li key={r.id}>
                    <RowButton onClick={() => setReviewing(r.id)}>
                      <span className="min-w-0 flex-1"><span className="block font-medium">{r.student_summary?.name} <span className="text-base-content/50 font-normal">in {r.domain}</span></span>
                        <span className="text-base-content/60 block truncate text-sm">{truncate(r.problem_statement, 100)}</span></span>
                      <span className="flex flex-col items-end gap-1">{r.priority && <PriorityBadge priority={r.priority.effective} />}<span className="text-base-content/50 text-xs">{timeAgo(r.submitted_at)}</span></span>
                    </RowButton>
                  </li>
                ))}
              </ul>
            ) : <p className="text-base-content/60 text-sm">No requests are waiting for a first look.</p>}
          </Card>
          <Card title="What students are asking for" actions={<Link to="/admin/reports" className="link link-hover text-sm">Reports</Link>}>
            <CategoryBars data={d.domain_demand.map((x) => ({ name: x.domain, value: x.count }))} label="Requests" />
          </Card>
        </div>
        <div className="flex flex-col gap-6">
          <Card title="Ready to approve">
            {d.approval_queue.length ? (
              <ul className="rows">
                {d.approval_queue.map((a) => (
                  <li key={a.id}>
                    <RowButton onClick={() => setApproving(a)}>
                      <span className="min-w-0 flex-1"><span className="block font-medium">{a.mentor_summary?.name}</span><span className="text-base-content/55 block text-sm">said yes to request #{a.request}</span></span>
                      <span className="btn btn-primary btn-xs">Review</span>
                    </RowButton>
                  </li>
                ))}
              </ul>
            ) : <p className="text-base-content/60 text-sm">No mentor has confirmed a pairing yet.</p>}
          </Card>
          <Card title="Your move"><TaskList tasks={d.tasks} emptyText="Nothing is waiting." /></Card>
          <Card title="Participation">
            <dl className="grid grid-cols-2 gap-3">
              {[['Approved students', d.participation.students_approved], ['Students who asked', d.participation.students_with_requests], ['Verified mentors', d.participation.mentors_verified], ['Mentoring now', d.participation.mentors_active]].map(([k, v]) => (
                <div key={k}><dd className="font-display text-2xl font-semibold tabular-nums">{v}</dd><dt className="text-base-content/60 text-xs">{k}</dt></div>
              ))}
            </dl>
          </Card>
        </div>
      </div>
      <RequestReviewModal requestId={reviewing} onClose={() => setReviewing(null)} />
      <ApprovePairingModal check={approving} onClose={() => setApproving(null)} />
    </>
  )
}

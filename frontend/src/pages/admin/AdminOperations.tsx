import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useSearchParams } from 'react-router'
import { CheckCircle2, Download, Plus, RefreshCw } from 'lucide-react'
import { downloadFile, errorMessage } from '../../lib/api'
import { CLOSURE, OUTCOME, PATHWAY, formatDate, formatDateTime, humanize, timeAgo } from '../../lib/format'
import {
  useAdminActions, useAlerts, useAudit, useAvailability, useAvailabilityActions, useFeedback, useInsights, useKnowledgeActions,
  useKnowledgeAdmin, useMentorship, useMentorships,
} from '../../lib/queries'
import type { AlertRow, AuditEvent, AvailabilityCheck, KnowledgeArticle, Mentorship } from '../../lib/types'
import { Badge, Card, EmptyState, ErrorAlert, Field, Loading, Modal, PageHeader, Pager, RowButton, Stat, Tabs, Timeline } from '../../components/ui'
import { CategoryBars, DataTable, MonthlyActivity } from '../../components/charts'

// --------------------------------------------------------------------- matching
/** Final IIC approval: creates the mentorship and reveals contact details to both people. */
export function ApprovePairingModal({ check, onClose, onApproved }: { check: AvailabilityCheck | null; onClose: () => void; onApproved?: (pairId: number) => void }) {
  const { approve } = useAvailabilityActions()
  const close = () => { approve.reset(); onClose() }
  return (
    <Modal open={!!check} onClose={close} title="Approve this pairing?" subtitle={check && `Request #${check.request}, ${check.request_summary.domain}`}
      actions={<><button className="btn btn-ghost btn-sm" onClick={close}>Not yet</button>
        <button className="btn btn-primary btn-sm" disabled={approve.isPending} onClick={async () => { if (check) { const pair = await approve.mutateAsync(check.id); onApproved?.(pair.id); close() } }}>Approve pairing</button></>}>
      {check && (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="bg-base-200 rounded-xl p-3"><p className="text-base-content/60 text-xs">Mentor</p><p className="font-semibold">{check.mentor_summary?.name}</p><p className="text-base-content/60 text-sm">{check.mentor_summary?.domain}</p></div>
            <div className="bg-base-200 rounded-xl p-3"><p className="text-base-content/60 text-xs">Mentor confirmed</p><p className="font-semibold">{formatDate(check.responded_at)}</p><p className="text-base-content/60 text-sm">Offer valid until {formatDate(check.expires_at)}</p></div>
          </div>
          <blockquote className="border-primary bg-base-200 rounded-r-xl border-l-4 px-4 py-3 text-sm whitespace-pre-line">{check.request_summary.problem_statement}</blockquote>
          {check.mentor_summary?.is_student_preference && <p className="text-sm">This is the mentor the student asked for.</p>}
          <p className="text-base-content/65 text-sm">Both people are notified and can see each other's email straight away.</p>
          <ErrorAlert error={approve.error} />
        </>
      )}
    </Modal>
  )
}

type MatchTab = 'confirmed' | 'pending' | 'history'

export function MatchingPage() {
  const [params, setParams] = useSearchParams()
  const tab = (params.get('tab') as MatchTab) || 'confirmed'
  const status = { confirmed: 'CONFIRMED', pending: 'PENDING', history: 'DECLINED,EXPIRED,USED' }[tab]
  const checks = useAvailability({ status })
  const [approving, setApproving] = useState<AvailabilityCheck | null>(null)
  const [approved, setApproved] = useState<number | null>(null)
  const rows = (checks.data?.results ?? []).filter((c) => tab === 'history' || !c.is_expired)
  return (
    <>
      <PageHeader title="Matching & approvals" subtitle="A mentorship starts only when you approve a pairing the mentor has confirmed." />
      <Tabs<MatchTab> value={tab} onChange={(k) => setParams({ tab: k })} tabs={[{ key: 'confirmed', label: 'Ready to approve' }, { key: 'pending', label: 'Waiting for mentors' }, { key: 'history', label: 'History' }]} />
      {approved && <div role="status" className="bg-success/12 mb-4 flex items-center gap-2 rounded-2xl px-4 py-3 text-sm"><CheckCircle2 size={18} className="text-success" />Mentorship #{approved} has started.<Link className="link ml-auto" to="/admin/mentorships">View mentorships</Link></div>}
      <Card>
        {checks.isPending ? <Loading /> : checks.isError ? <ErrorAlert error={checks.error} /> : rows.length === 0 ? (
          <EmptyState title={tab === 'confirmed' ? 'No pairings to approve' : tab === 'pending' ? 'No mentors are being asked right now' : 'No history yet'} />
        ) : (
          <ul className="rows">
            {rows.map((c) => (
              <li key={c.id}>
                <RowButton onClick={() => tab === 'confirmed' ? setApproving(c) : undefined} className={tab === 'confirmed' ? '' : 'cursor-default hover:bg-transparent'}>
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium">{c.mentor_summary?.name}<span className="text-base-content/50 font-normal"> for request #{c.request}</span></span>
                    <span className="text-base-content/60 block text-sm">{c.request_summary.domain}, {PATHWAY[c.request_summary.pathway].toLowerCase()}{c.mentor_summary?.is_student_preference && ', the student\'s choice'}</span>
                  </span>
                  {tab === 'confirmed' && <span className="btn btn-primary btn-sm">Review</span>}
                  {tab === 'pending' && <span className="text-base-content/55 text-sm">asked {timeAgo(c.sent_at)}, due {formatDate(c.expires_at)}</span>}
                  {tab === 'history' && <Badge tone={c.status === 'USED' ? 'success' : 'neutral'}>{c.status === 'USED' ? 'Approved' : c.status.toLowerCase()}</Badge>}
                </RowButton>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <ApprovePairingModal check={approving} onClose={() => setApproving(null)} onApproved={setApproved} />
    </>
  )
}

// ---------------------------------------------------------- active mentorships
function MentorshipSheet({ pair, onClose }: { pair: Mentorship | null; onClose: () => void }) {
  const detail = useMentorship(pair?.id)
  const feedback = useFeedback(pair?.id)
  const { close, reassign } = useAdminActions()
  const [mode, setMode] = useState<'close' | 'reassign' | null>(null)
  const [reason, setReason] = useState('')
  const [closureType, setClosureType] = useState('COMPLETED')
  const action = mode === 'close' ? close : reassign
  const finish = () => { setMode(null); setReason(''); action.reset() }
  return (
    <Modal variant="sheet" wide open={!!pair} onClose={onClose} title={pair ? `${pair.student_name} with ${pair.mentor_name}` : ''}
      subtitle={pair && `${pair.request_summary.domain}. Started ${formatDate(pair.started_at)}.`}>
      {pair && (
        <>
          <div className="flex flex-wrap gap-2">
            <Badge tone={pair.status === 'ACTIVE' ? 'success' : 'neutral'}>{pair.status === 'ACTIVE' ? 'Active' : 'Closed'}</Badge>
            {pair.closure_type && <Badge>{CLOSURE[pair.closure_type]}</Badge>}
            {pair.open_alerts?.map((a) => <Badge key={a} tone="warning">{a === 'INACTIVITY' ? 'No meeting in 14 days' : 'Progress update overdue'}</Badge>)}
          </div>
          <dl className="grid grid-cols-3 gap-3">
            {[['Goals done', `${pair.progress.goals_completed}/${pair.progress.goals_total}`], ['Meetings held', pair.progress.meetings_held], ['Last met', formatDate(pair.progress.last_meeting_date)]].map(([k, v]) => (
              <div key={k} className="bg-base-200 rounded-xl p-3"><dt className="text-base-content/60 text-xs">{k}</dt><dd className="font-display text-lg font-semibold">{v}</dd></div>
            ))}
          </dl>
          <section>
            <h4 className="mb-2 font-semibold">Written feedback</h4>
            {feedback.isPending ? <Loading /> : feedback.isError ? <ErrorAlert error={feedback.error} /> : feedback.data.length === 0 ? <p className="text-base-content/60 text-sm">Nobody has written to IIC about this mentorship yet.</p> : (
              <ul className="rows">{feedback.data.map((f) => (
                <li key={f.id} className="py-3"><div className="text-base-content/55 mb-1 text-xs">{humanize(f.kind)} from the {f.author === pair.mentor ? 'mentor' : 'student'}, {formatDateTime(f.created_at)}</div><p className="text-sm whitespace-pre-line">{f.text}</p></li>
              ))}</ul>
            )}
          </section>
          <section>
            <h4 className="mb-3 font-semibold">Milestones</h4>
            {detail.isPending ? <Loading /> : detail.isError ? <ErrorAlert error={detail.error} /> : <Timeline items={detail.data.timeline.slice(0, 12).map((t, i) => ({ key: i, title: t.title, detail: t.detail, at: t.at }))} />}
          </section>
          {pair.status === 'ACTIVE' && (
            <div className="border-base-300 flex flex-wrap gap-2 border-t pt-4">
              <button className="btn btn-sm" onClick={() => setMode('reassign')}>Find a new mentor</button>
              <button className="btn btn-sm text-error ml-auto" onClick={() => setMode('close')}>End mentorship</button>
            </div>
          )}
          <Modal open={!!mode} onClose={finish} size="sm" title={mode === 'close' ? 'End this mentorship?' : 'Find a new mentor?'}
            subtitle={mode === 'close' ? 'The linked request closes too.' : 'This pairing closes and the request returns to your matching queue.'}
            actions={<><button className="btn btn-ghost btn-sm" onClick={finish}>Cancel</button>
              <button className={`btn btn-sm ${mode === 'close' ? 'btn-error' : 'btn-primary'}`} disabled={!reason.trim() || action.isPending}
                onClick={async () => { if (mode === 'close') await close.mutateAsync({ id: pair.id, reason, closure_type: closureType }); else await reassign.mutateAsync({ id: pair.id, reason }); finish(); onClose() }}>
                {mode === 'close' ? 'End mentorship' : 'Reopen for matching'}</button></>}>
            {mode === 'close' && (
              <Field label="How did it end?"><select className="select w-full" value={closureType} onChange={(e) => setClosureType(e.target.value)}>
                {Object.entries(CLOSURE).filter(([k]) => k !== 'REASSIGNED').map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></Field>
            )}
            <Field label="Reason (required)"><textarea className="textarea w-full" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
            <ErrorAlert error={action.error} />
          </Modal>
        </>
      )}
    </Modal>
  )
}

export function ActiveMentorshipsPage() {
  const [status, setStatus] = useState<'ACTIVE' | 'CLOSED'>('ACTIVE')
  const pairs = useMentorships({ status })
  const [selected, setSelected] = useState<Mentorship | null>(null)
  return (
    <>
      <PageHeader title="Mentorships" subtitle="Open one to read written feedback, end it, or find the student a new mentor." />
      <Tabs value={status} onChange={setStatus} tabs={[{ key: 'ACTIVE', label: 'Active' }, { key: 'CLOSED', label: 'Ended' }]} />
      <Card>
        {pairs.isPending ? <Loading /> : pairs.isError ? <ErrorAlert error={pairs.error} /> : pairs.data.results.length === 0 ? <EmptyState title={status === 'ACTIVE' ? 'No active mentorships' : 'None have ended yet'} /> : (
          <ul className="rows">
            {pairs.data.results.map((p) => (
              <li key={p.id}>
                <RowButton onClick={() => setSelected(p)}>
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium">{p.student_name} <span className="text-base-content/50 font-normal">with</span> {p.mentor_name}</span>
                    <span className="text-base-content/60 block text-sm">{p.request_summary.domain}, since {formatDate(p.started_at)}. {p.progress.meetings_held} meetings, {p.progress.goals_completed} of {p.progress.goals_total} goals.</span>
                  </span>
                  {p.open_alerts?.length ? <Badge tone="warning">Needs attention</Badge> : status === 'CLOSED' && p.closure_type ? <Badge>{CLOSURE[p.closure_type]}</Badge> : <Badge tone="success">On track</Badge>}
                </RowButton>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <MentorshipSheet pair={selected} onClose={() => setSelected(null)} />
    </>
  )
}

// ------------------------------------------------------------------- monitoring
export function MonitoringPage() {
  const [includeResolved, setIncludeResolved] = useState(false)
  const alerts = useAlerts(includeResolved)
  const { resolveAlert, runDailyChecks } = useAdminActions()
  const [resolving, setResolving] = useState<AlertRow | null>(null)
  const ran = runDailyChecks.data
  return (
    <>
      <PageHeader title="Monitoring & alerts" subtitle="Raised every day for mentorships with no meeting in 14 days or an overdue progress update. Unanswered 7-day availability checks expire at the same time."
        actions={<>
          <label className="bg-base-100 border-base-300 flex cursor-pointer items-center gap-2 rounded-full border px-4 py-2 text-sm"><input type="checkbox" className="toggle toggle-sm" checked={includeResolved} onChange={(e) => setIncludeResolved(e.target.checked)} />Show resolved</label>
          <button className="btn btn-sm" disabled={runDailyChecks.isPending} onClick={() => runDailyChecks.mutate()}>{runDailyChecks.isPending ? <span className="loading loading-spinner loading-xs" /> : <RefreshCw size={15} />}Run checks now</button>
        </>} />
      {ran && <div role="status" className="bg-base-200 mb-4 rounded-2xl px-4 py-3 text-sm">Checks complete: {ran.expired_checks} availability checks expired, {ran.inactivity_alerts} new inactivity alerts, {ran.feedback_alerts} new feedback reminders.</div>}
      <ErrorAlert error={runDailyChecks.error} />
      <Card>
        {alerts.isPending ? <Loading /> : alerts.isError ? <ErrorAlert error={alerts.error} /> : alerts.data.length === 0 ? <EmptyState title="Everything's on track" description="No mentorship needs a nudge right now." /> : (
          <ul className="rows">
            {alerts.data.map((a) => (
              <li key={a.id} className="flex flex-wrap items-center gap-3 py-3">
                <span className={`size-2.5 shrink-0 rounded-full ${a.resolved_at ? 'bg-base-300' : 'bg-accent'}`} aria-hidden />
                <span className="min-w-0 flex-1"><span className="block font-medium">{a.kind_label}</span><span className="text-base-content/60 block text-sm">{a.student_name} with {a.mentor_name}, raised {timeAgo(a.created_at)}</span></span>
                {a.resolved_at ? <span className="text-base-content/55 text-sm">Resolved {formatDate(a.resolved_at)}</span> : <button className="btn btn-sm" onClick={() => setResolving(a)}>Resolve</button>}
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Modal open={!!resolving} onClose={() => setResolving(null)} size="sm" title="Mark this alert resolved?" subtitle={resolving && `${resolving.student_name} with ${resolving.mentor_name}`}
        actions={<><button className="btn btn-ghost btn-sm" onClick={() => setResolving(null)}>Cancel</button>
          <button className="btn btn-primary btn-sm" disabled={resolveAlert.isPending} onClick={async () => { if (resolving) { await resolveAlert.mutateAsync(resolving.id); setResolving(null) } }}>Mark resolved</button></>}>
        <p className="text-sm">Use this once you have followed up with the pair. Alerts also clear automatically when a meeting is confirmed or the mentor sends a progress update.</p>
      </Modal>
    </>
  )
}

// ---------------------------------------------------------------------- reports
const EXPORTS = [{ type: 'pairs', label: 'Mentorships' }, { type: 'requests', label: 'Requests' }, { type: 'meetings', label: 'Meetings' }, { type: 'outcomes', label: 'Outcomes' }]

export function ReportsPage() {
  const insights = useInsights()
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState('')
  const exportCsv = (type: string) => downloadFile(`/admin/export/?type=${type}`, `sangam_${type}.csv`).then(() => setExportError('')).catch((e) => setExportError(errorMessage(e)))
  return (
    <>
      <PageHeader title="Reports & analytics" actions={<button className="btn" onClick={() => setExporting(true)}><Download size={17} />Export data</button>} />
      {insights.isPending ? <Loading /> : insights.isError ? <ErrorAlert error={insights.error} /> : (() => {
        const d = insights.data
        return (
          <div className="flex flex-col gap-6">
            <div className="panel grid grid-cols-2 gap-2 p-3 md:grid-cols-3 xl:grid-cols-6">
              <Stat label="Requests" value={d.requests} /><Stat label="Active mentorships" value={d.active_pairs} />
              <Stat label="Ended mentorships" value={d.mentorships_closed} /><Stat label="Meetings held" value={d.meetings_held} />
              <Stat label="Outcomes recorded" value={d.outcomes} /><Stat label="Open alerts" value={d.alerts_open} to="/admin/monitoring" attention={d.alerts_open > 0} />
            </div>
            <Card title="The last six months">
              <MonthlyActivity requests={d.monthly_requests} mentorships={d.monthly_mentorships} meetings={d.monthly_meetings} />
              <DataTable columns={[{ key: 'month', label: 'Month' }, { key: 'r', label: 'Requests' }, { key: 'm', label: 'Mentorships' }, { key: 'x', label: 'Meetings' }]}
                rows={d.monthly_requests.map((r, i) => ({ month: r.month, r: r.count, m: d.monthly_mentorships[i]?.count ?? 0, x: d.monthly_meetings[i]?.count ?? 0 }))} />
            </Card>
            <div className="grid gap-6 lg:grid-cols-2">
              <Card title="What students ask for"><CategoryBars data={d.domain_demand.map((x) => ({ name: x.domain, value: x.count }))} label="Requests" /></Card>
              <Card title="Career pathways"><CategoryBars data={d.pathway_demand.map((x) => ({ name: PATHWAY[x.pathway], value: x.count }))} label="Requests" /></Card>
              <Card title="Where requests stand"><CategoryBars data={d.requests_by_status.map((x) => ({ name: humanize(x.status), value: x.count }))} label="Requests" /></Card>
              <Card title="Outcomes achieved"><CategoryBars data={d.outcomes_by_kind.map((x) => ({ name: OUTCOME[x.kind], value: x.count }))} label="Outcomes" /></Card>
            </div>
          </div>
        )
      })()}
      <Modal open={exporting} onClose={() => setExporting(false)} size="sm" title="Export data as CSV" subtitle="Files contain IDs and dates only: no names, contact details, problem statements or feedback text.">
        <ul className="rows">
          {EXPORTS.map((e) => (
            <li key={e.type} className="flex items-center justify-between py-2.5"><span className="font-medium">{e.label}</span><button className="btn btn-sm" onClick={() => exportCsv(e.type)}><Download size={15} />Download</button></li>
          ))}
        </ul>
        {exportError && <p className="text-error text-sm">{exportError}</p>}
      </Modal>
    </>
  )
}

// -------------------------------------------------------------------- audit log
export function AuditLogPage() {
  const [page, setPage] = useState(1)
  const [action, setAction] = useState('')
  const [viewing, setViewing] = useState<AuditEvent | null>(null)
  const audit = useAudit({ page, action })
  return (
    <>
      <PageHeader title="Audit log" subtitle="Every approval and status change, newest first. Records are permanent and hold no conversation content."
        actions={<input className="input w-64" placeholder="Filter by action, e.g. MATCH_APPROVED" value={action} onChange={(e) => { setAction(e.target.value.toUpperCase()); setPage(1) }} aria-label="Filter by action" />} />
      <Card>
        {audit.isPending ? <Loading /> : audit.isError ? <ErrorAlert error={audit.error} /> : audit.data.results.length === 0 ? <EmptyState title="No events match" /> : (
          <>
            <ul className="rows">
              {audit.data.results.map((e) => (
                <li key={e.id}>
                  <RowButton onClick={() => setViewing(e)}>
                    <span className="text-base-content/55 w-32 shrink-0 text-sm">{formatDateTime(e.at)}</span>
                    <span className="min-w-0 flex-1"><span className="block font-medium">{humanize(e.action)}</span><span className="text-base-content/60 block truncate text-sm">{e.actor_email ?? 'System'}, on {humanize(e.entity_type).toLowerCase()} #{e.entity_id}</span></span>
                  </RowButton>
                </li>
              ))}
            </ul>
            <Pager page={page} count={audit.data.count} onChange={setPage} />
          </>
        )}
      </Card>
      <Modal open={!!viewing} onClose={() => setViewing(null)} title={viewing ? humanize(viewing.action) : ''} subtitle={viewing && formatDateTime(viewing.at)}>
        {viewing && (
          <dl className="grid grid-cols-[8rem_1fr] gap-y-2 text-sm">
            <dt className="text-base-content/60">Who</dt><dd>{viewing.actor_email ?? 'System'} ({viewing.actor_role.toLowerCase()})</dd>
            <dt className="text-base-content/60">Record</dt><dd>{viewing.entity_type} #{viewing.entity_id}</dd>
            <dt className="text-base-content/60">Event code</dt><dd><code>{viewing.action}</code></dd>
            <dt className="text-base-content/60">Details</dt><dd>{Object.keys(viewing.details).length ? <pre className="bg-base-200 overflow-x-auto rounded-lg p-2 text-xs">{JSON.stringify(viewing.details, null, 2)}</pre> : 'None'}</dd>
          </dl>
        )}
      </Modal>
    </>
  )
}

// ------------------------------------------------------------- knowledge base
function ArticleModal({ article, open, onClose }: { article: Partial<KnowledgeArticle> | null; open: boolean; onClose: () => void }) {
  const { save, remove } = useKnowledgeActions()
  const [confirmDelete, setConfirmDelete] = useState(false)
  const { register, handleSubmit } = useForm<Partial<KnowledgeArticle>>({ values: article ?? { title: '', content: '', audience: 'ALL', is_published: false } })
  const close = () => { save.reset(); setConfirmDelete(false); onClose() }
  const onSubmit = handleSubmit(async (v) => { await save.mutateAsync({ ...v, id: article?.id }); close() })
  return (
    <Modal open={open} onClose={close} size="lg" title={article?.id ? 'Edit article' : 'New article'} subtitle="The assistant answers only from published articles.">
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <Field label="Title"><input className="input w-full" maxLength={180} {...register('title', { required: true })} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Who can see it"><select className="select w-full" {...register('audience')}><option value="ALL">Everyone</option><option value="STUDENT">Students</option><option value="MENTOR">Mentors</option><option value="ADMIN">IIC staff</option></select></Field>
          <label className="mt-7 flex cursor-pointer items-center gap-2 text-sm"><input type="checkbox" className="toggle toggle-primary toggle-sm" {...register('is_published')} />Published</label>
        </div>
        <Field label="Guidance" hint="Approved, non-confidential policy only. Never paste student or mentor conversations."><textarea className="textarea w-full" rows={9} {...register('content', { required: true })} /></Field>
        <ErrorAlert error={save.error ?? remove.error} />
        <div className="flex flex-wrap items-center gap-2">
          {article?.id && (confirmDelete
            ? <><span className="text-sm">Delete for good?</span><button type="button" className="btn btn-error btn-sm" onClick={async () => { await remove.mutateAsync(article.id!); close() }}>Delete</button></>
            : <button type="button" className="btn btn-ghost btn-sm text-error" onClick={() => setConfirmDelete(true)}>Delete article</button>)}
          <span className="flex-1" />
          <button type="button" className="btn btn-ghost" onClick={close}>Cancel</button>
          <button className="btn btn-primary" disabled={save.isPending}>Save article</button>
        </div>
      </form>
    </Modal>
  )
}

export function KnowledgePage() {
  const articles = useKnowledgeAdmin()
  const [editing, setEditing] = useState<{ open: boolean; article: Partial<KnowledgeArticle> | null }>({ open: false, article: null })
  return (
    <>
      <PageHeader title="Assistant knowledge" subtitle="What the Ask Sangam assistant can draw on. Chat messages themselves are never stored."
        actions={<button className="btn btn-primary" onClick={() => setEditing({ open: true, article: null })}><Plus size={17} />New article</button>} />
      <Card>
        {articles.isPending ? <Loading /> : articles.isError ? <ErrorAlert error={articles.error} /> : articles.data.results.length === 0 ? <EmptyState title="No articles yet" description="Write the first piece of guidance students and mentors can ask about." /> : (
          <ul className="rows">
            {articles.data.results.map((a) => (
              <li key={a.id}>
                <RowButton onClick={() => setEditing({ open: true, article: a })}>
                  <span className="min-w-0 flex-1"><span className="block font-medium">{a.title}</span><span className="text-base-content/60 block truncate text-sm">{a.content}</span></span>
                  <span className="text-base-content/50 hidden text-xs sm:inline">{a.audience === 'ALL' ? 'Everyone' : humanize(a.audience)}, {timeAgo(a.updated_at)}</span>
                  <Badge tone={a.is_published ? 'success' : 'ghost'}>{a.is_published ? 'Published' : 'Draft'}</Badge>
                </RowButton>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <ArticleModal open={editing.open} article={editing.article} onClose={() => setEditing({ open: false, article: null })} />
    </>
  )
}

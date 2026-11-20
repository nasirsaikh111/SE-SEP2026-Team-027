import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { Mail, Search, Send, ShieldCheck, Sparkles, UserPlus } from 'lucide-react'
import { errorMessage, fieldErrors } from '../../lib/api'
import { PATHWAY, PRIORITY, formatDate, formatDateTime, timeAgo, truncate } from '../../lib/format'
import { useAdminActions, useAdminMentors, useRequest, useRequestActions, useRequests, useStudents, useSuggestions } from '../../lib/queries'
import type { MentorProfile, PendingStudent, Priority, RequestDetail } from '../../lib/types'
import { Badge, Card, EmptyState, ErrorAlert, Field, Loading, Modal, PageHeader, Pager, PriorityBadge, RowButton, StageBadge, Tabs, Timeline } from '../../components/ui'
import { Confluence } from '../../components/Confluence'

function SearchBox({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <label className="bg-base-100 border-base-300 focus-within:border-primary mb-4 flex h-10 w-full items-center gap-2 rounded-full border px-4 sm:w-72">
      <Search size={16} className="opacity-50" />
      <input type="search" className="w-full bg-transparent text-sm outline-none" placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)} aria-label={placeholder} />
    </label>
  )
}

// ------------------------------------------------------------ student approvals
type StudentTab = 'PENDING' | 'APPROVED' | 'REJECTED' | 'ALL'

function StudentReviewModal({ student, onClose }: { student: PendingStudent | null; onClose: () => void }) {
  const { reviewStudent } = useAdminActions()
  const [mode, setMode] = useState<'view' | 'reject'>('view')
  const [reason, setReason] = useState('')
  const [verified, setVerified] = useState(false)
  const close = () => { setMode('view'); setReason(''); setVerified(false); reviewStudent.reset(); onClose() }
  const decide = async (decision: 'APPROVED' | 'REJECTED') => {
    if (!student) return
    await reviewStudent.mutateAsync({ userId: student.user_id, decision, reason, academic_verified: verified })
    close()
  }
  const pending = student?.approval_status !== 'APPROVED'
  return (
    <Modal open={!!student} onClose={close} title={student?.name || student?.email || ''} subtitle={student && `${student.email}, registered ${formatDate(student.submitted_at)}`}
      actions={student && pending && (mode === 'reject' ? (
        <><button className="btn btn-ghost btn-sm" onClick={() => setMode('view')}>Back</button>
          <button className="btn btn-error btn-sm" disabled={!reason.trim() || reviewStudent.isPending} onClick={() => decide('REJECTED')}>Reject registration</button></>
      ) : (
        <>{student.approval_status === 'PENDING' && <button className="btn btn-ghost btn-sm" onClick={() => setMode('reject')}>Reject</button>}
          <button className="btn btn-primary btn-sm" disabled={!verified || reviewStudent.isPending} onClick={() => decide('APPROVED')}>Approve student</button></>
      ))}>
      {student && (
        <>
          <dl className="grid grid-cols-2 gap-3">
            {[['Roll number', student.iitm_roll_number], ['Level', student.level === 'DEGREE' ? 'Degree' : 'Diploma'], ['CGPA', student.cgpa ?? 'Not given'], ['Status', student.approval_status.toLowerCase()]].map(([k, v]) => (
              <div key={k} className="bg-base-200 rounded-xl p-3"><dt className="text-base-content/60 text-xs">{k}</dt><dd className="font-medium">{v}</dd></div>
            ))}
            <div className="bg-base-200 col-span-2 rounded-xl p-3"><dt className="text-base-content/60 text-xs">Courses completed</dt><dd className="font-medium">{student.courses.join(', ')}</dd></div>
          </dl>
          {pending && (mode === 'reject' ? (
            <Field label="Reason the student will see"><textarea className="textarea w-full" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
          ) : (
            <label className="bg-primary/8 flex cursor-pointer items-start gap-3 rounded-xl p-3 text-sm">
              <input type="checkbox" className="checkbox checkbox-primary checkbox-sm mt-0.5" checked={verified} onChange={(e) => setVerified(e.target.checked)} />
              I checked the roll number, level, courses and CGPA against IITM's records.
            </label>
          ))}
          {!pending && <p className="text-base-content/65 text-sm">Approved {formatDate(student.approved_at)}. Approved academic records are locked.</p>}
          <ErrorAlert error={reviewStudent.error} />
        </>
      )}
    </Modal>
  )
}

export function StudentApprovalsPage() {
  const [tab, setTab] = useState<StudentTab>('PENDING')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [reviewing, setReviewing] = useState<PendingStudent | null>(null)
  const students = useStudents({ status: tab, search, page })
  return (
    <>
      <PageHeader title="Student approvals" subtitle="Students can ask for a mentor once you verify their academic details." />
      <div className="flex flex-wrap items-start justify-between gap-2">
        <Tabs<StudentTab> value={tab} onChange={(t) => { setTab(t); setPage(1) }} tabs={[{ key: 'PENDING', label: 'Waiting for you' }, { key: 'APPROVED', label: 'Approved' }, { key: 'REJECTED', label: 'Rejected' }, { key: 'ALL', label: 'Everyone' }]} />
        <SearchBox value={search} onChange={(v) => { setSearch(v); setPage(1) }} placeholder="Name, email or roll number" />
      </div>
      <Card>
        {students.isPending ? <Loading /> : students.isError ? <ErrorAlert error={students.error} /> : students.data.results.length === 0 ? (
          <EmptyState title={tab === 'PENDING' ? 'No registrations waiting' : 'Nobody here'} description={tab === 'PENDING' ? 'New student registrations will appear here.' : undefined} />
        ) : (
          <>
            <ul className="rows">
              {students.data.results.map((s) => (
                <li key={s.id}>
                  <RowButton onClick={() => setReviewing(s)}>
                    <span className="bg-base-200 font-display grid size-10 shrink-0 place-items-center rounded-xl font-semibold">{(s.name || s.email).slice(0, 1).toUpperCase()}</span>
                    <span className="min-w-0 flex-1"><span className="block font-medium">{s.name || s.email}</span><span className="text-base-content/60 block truncate text-sm">{s.iitm_roll_number}, {s.level.toLowerCase()}, CGPA {s.cgpa ?? 'not given'}</span></span>
                    <span className="text-base-content/50 hidden text-sm sm:inline">{timeAgo(s.submitted_at)}</span>
                    <Badge tone={s.approval_status === 'APPROVED' ? 'success' : s.approval_status === 'REJECTED' ? 'error' : 'warning'}>{s.approval_status === 'PENDING' ? 'Review' : s.approval_status.toLowerCase()}</Badge>
                  </RowButton>
                </li>
              ))}
            </ul>
            <Pager page={page} count={students.data.count} onChange={setPage} />
          </>
        )}
      </Card>
      <StudentReviewModal student={reviewing} onClose={() => setReviewing(null)} />
    </>
  )
}

// ------------------------------------------------------------- mentor repository
interface MentorForm {
  email: string; first_name: string; last_name: string; alumni_roll_number: string; graduation_year: number; domain: string
  specialty: string; current_role: string; company: string; career_path: string; experience_years: number; skills: string; linkedin_url: string; bio: string
}

function MentorFormModal({ mentor, open, onClose }: { mentor: MentorProfile | null; open: boolean; onClose: () => void }) {
  const { createMentor, updateMentor } = useAdminActions()
  const [errors, setErrors] = useState<Record<string, string>>({})
  const { register, handleSubmit } = useForm<MentorForm>({
    values: mentor ? { ...mentor, email: mentor.email ?? '', first_name: '', last_name: '', graduation_year: mentor.graduation_year ?? 2022, skills: mentor.skills.join(', ') } as MentorForm
      : { email: '', first_name: '', last_name: '', alumni_roll_number: '', graduation_year: 2022, domain: '', specialty: '', current_role: '', company: '', career_path: '', experience_years: 0, skills: '', linkedin_url: '', bio: '' },
  })
  const action = mentor ? updateMentor : createMentor
  const close = () => { setErrors({}); action.reset(); onClose() }
  const onSubmit = handleSubmit(async (v) => {
    setErrors({})
    const body = { ...v, skills: v.skills.split(',').map((s) => s.trim()).filter(Boolean), graduation_year: Number(v.graduation_year), experience_years: Number(v.experience_years) }
    try {
      if (mentor) {
        const { email, first_name, last_name, ...profile } = body
        await updateMentor.mutateAsync({ userId: mentor.user, ...profile })
      } else await createMentor.mutateAsync(body)
      close()
    } catch (err) { setErrors(fieldErrors(err)) }
  })
  const input = (name: keyof MentorForm, label: string, props: Record<string, unknown> = {}) => (
    <Field label={label} error={errors[name]}><input className="input w-full" {...props} {...register(name)} /></Field>
  )
  return (
    <Modal open={open} onClose={close} size="lg" title={mentor ? `Edit ${mentor.name}` : 'Add an alumni mentor'}
      subtitle={!mentor && 'They stay unverified until you check their alumni record. Send an invitation so they can set a password.'}>
      <form onSubmit={onSubmit} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {!mentor && <>{input('first_name', 'First name')}{input('last_name', 'Last name')}<div className="sm:col-span-2">{input('email', 'Email', { type: 'email' })}</div></>}
        {input('alumni_roll_number', 'Alumni roll number')}{input('graduation_year', 'Graduation year', { type: 'number' })}
        {input('current_role', 'Current role')}{input('company', 'Company')}
        {input('domain', 'Domain')}{input('specialty', 'Specialty')}
        {input('career_path', 'Career pathway')}{input('experience_years', 'Years of experience', { type: 'number', min: 0 })}
        <div className="sm:col-span-2">{input('skills', 'Skills, separated by commas')}</div>
        <div className="sm:col-span-2">{input('linkedin_url', 'LinkedIn URL (optional)', { placeholder: 'https://www.linkedin.com/in/…' })}</div>
        <div className="sm:col-span-2"><Field label="Professional summary" error={errors.bio}><textarea className="textarea w-full" rows={2} maxLength={500} {...register('bio')} /></Field></div>
        {action.isError && !Object.keys(errors).length && <div className="sm:col-span-2"><ErrorAlert error={action.error} /></div>}
        <div className="flex justify-end gap-2 sm:col-span-2"><button type="button" className="btn btn-ghost" onClick={close}>Cancel</button><button className="btn btn-primary" disabled={action.isPending}>{mentor ? 'Save changes' : 'Add mentor'}</button></div>
      </form>
    </Modal>
  )
}

function MentorSheet({ mentor, onClose, onEdit }: { mentor: MentorProfile | null; onClose: () => void; onEdit: (m: MentorProfile) => void }) {
  const { verifyMentor, updateMentor, inviteMentor } = useAdminActions()
  const [notice, setNotice] = useState('')
  const [publish, setPublish] = useState(true)
  const run = (p: Promise<unknown>, done: string) => p.then(() => setNotice(done)).catch((e) => setNotice(errorMessage(e)))
  const close = () => { setNotice(''); onClose() }
  const m = mentor
  return (
    <Modal variant="sheet" open={!!m} onClose={close} title={m?.name || m?.email || ''} subtitle={m && `${m.current_role}${m.company ? ` at ${m.company}` : ''}`}>
      {m && (
        <>
          <div className="flex flex-wrap gap-1.5">
            {m.is_verified ? <Badge tone="success">Verified</Badge> : <Badge tone="warning">Not verified</Badge>}
            {m.is_discoverable ? <Badge tone="primary">In the student directory</Badge> : <Badge tone="ghost">Hidden from students</Badge>}
            {m.has_active_mentee ? <Badge tone="info">Mentoring now</Badge> : !m.is_available && <Badge tone="ghost">Not taking mentees</Badge>}
          </div>
          {notice && <div className="bg-base-200 rounded-xl px-3 py-2 text-sm">{notice}</div>}
          <section className="bg-base-200 rounded-2xl p-4">
            <h4 className="font-semibold">Alumni record</h4>
            <p className="text-base-content/70 text-sm">Roll number {m.alumni_roll_number || 'missing'}, graduated {m.graduation_year ?? 'year missing'}. {m.verified_at && `Verified ${formatDate(m.verified_at)}.`}</p>
            {!m.is_verified && (
              <div className="mt-3 flex flex-col gap-3">
                <label className="flex cursor-pointer items-center gap-2 text-sm"><input type="checkbox" className="toggle toggle-primary toggle-sm" checked={publish} onChange={(e) => setPublish(e.target.checked)} />Show in Discover Mentors after verifying</label>
                <button className="btn btn-primary btn-sm self-start" disabled={verifyMentor.isPending} onClick={() => run(verifyMentor.mutateAsync({ userId: m.user, discoverable: publish }), 'Verified. The mentor has been notified.')}><ShieldCheck size={15} />I checked the record; verify</button>
              </div>
            )}
          </section>
          <dl className="grid grid-cols-2 gap-3 text-sm">
            {[['Email', m.email], ['Domain', m.domain], ['Specialty', m.specialty], ['Career pathway', m.career_path || '—'], ['Experience', `${m.experience_years} years`], ['Skills', m.skills.join(', ') || '—']].map(([k, v]) => (
              <div key={k}><dt className="text-base-content/55 text-xs">{k}</dt><dd className="font-medium break-words">{v}</dd></div>
            ))}
          </dl>
          {m.bio && <p className="text-base-content/75 text-sm">{m.bio}</p>}
          <div className="border-base-300 mt-auto flex flex-wrap gap-2 border-t pt-4">
            {m.is_verified && <button className="btn btn-sm" disabled={updateMentor.isPending} onClick={() => run(updateMentor.mutateAsync({ userId: m.user, is_discoverable: !m.is_discoverable }), m.is_discoverable ? 'Hidden from the directory.' : 'Now shown in the directory.')}>{m.is_discoverable ? 'Hide from directory' : 'Show in directory'}</button>}
            <button className="btn btn-sm" disabled={inviteMentor.isPending} onClick={() => run(inviteMentor.mutateAsync(m.user), `Invitation sent to ${m.email}.`)}><Mail size={15} />Send invitation</button>
            <button className="btn btn-ghost btn-sm" onClick={() => onEdit(m)}>Edit details</button>
          </div>
        </>
      )}
    </Modal>
  )
}

export function MentorRepositoryPage() {
  const [params, setParams] = useSearchParams()
  const verified = params.get('verified') ?? ''
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [editing, setEditing] = useState<{ open: boolean; mentor: MentorProfile | null }>({ open: false, mentor: null })
  const mentors = useAdminMentors({ verified, search, page })
  const selected = mentors.data?.results.find((m) => m.id === selectedId) ?? null
  return (
    <>
      <PageHeader title="Mentor repository" subtitle="Verify alumni against IIC records and choose who students can find in Discover Mentors."
        actions={<button className="btn btn-primary" onClick={() => setEditing({ open: true, mentor: null })}><UserPlus size={17} />Add mentor</button>} />
      <div className="flex flex-wrap items-start justify-between gap-2">
        <Tabs value={verified || 'all'} onChange={(k) => { setPage(1); setParams(k === 'all' ? {} : { verified: k }) }} tabs={[{ key: 'all', label: 'Everyone' }, { key: 'false', label: 'To verify' }, { key: 'true', label: 'Verified' }]} />
        <SearchBox value={search} onChange={(v) => { setSearch(v); setPage(1) }} placeholder="Name, company or specialty" />
      </div>
      <Card>
        {mentors.isPending ? <Loading /> : mentors.isError ? <ErrorAlert error={mentors.error} /> : mentors.data.results.length === 0 ? <EmptyState title="No mentors here" /> : (
          <>
            <ul className="rows">
              {mentors.data.results.map((m) => (
                <li key={m.id}>
                  <RowButton onClick={() => setSelectedId(m.id)}>
                    <span className="bg-neutral text-neutral-content font-display grid size-10 shrink-0 place-items-center rounded-xl font-semibold">{(m.name || m.email || '?').slice(0, 1).toUpperCase()}</span>
                    <span className="min-w-0 flex-1"><span className="block font-medium">{m.name || m.email}</span><span className="text-base-content/60 block truncate text-sm">{m.current_role}{m.company && ` at ${m.company}`}, {m.domain}</span></span>
                    <span className="flex flex-wrap justify-end gap-1">
                      {!m.is_verified ? <Badge tone="warning">Verify</Badge> : m.is_discoverable ? <Badge tone="primary">In directory</Badge> : <Badge tone="ghost">Hidden</Badge>}
                      {m.has_active_mentee && <Badge tone="info">Mentoring</Badge>}
                    </span>
                  </RowButton>
                </li>
              ))}
            </ul>
            <Pager page={page} count={mentors.data.count} onChange={setPage} />
          </>
        )}
      </Card>
      <MentorSheet mentor={selected} onClose={() => setSelectedId(null)} onEdit={(m) => setEditing({ open: true, mentor: m })} />
      <MentorFormModal open={editing.open} mentor={editing.mentor} onClose={() => setEditing({ open: false, mentor: null })} />
    </>
  )
}

// ------------------------------------------------------------------ request review
function PrioritySection({ r }: { r: RequestDetail }) {
  const { assess, override } = useRequestActions()
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState<Priority | ''>('')
  const [reason, setReason] = useState('')
  const p = r.priority
  if (!['SUBMITTED', 'UNDER_REVIEW', 'WAITING'].includes(r.status)) return null
  return (
    <section className="bg-base-200 rounded-2xl p-4">
      <div className="flex items-center justify-between gap-2">
        <h4 className="inline-flex items-center gap-1.5 font-semibold"><Sparkles size={16} className="text-primary" />Suggested priority</h4>
        <button className="btn btn-ghost btn-xs" disabled={assess.isPending} onClick={() => assess.mutate(r.id)}>Re-assess</button>
      </div>
      {p ? (
        <div className="mt-2 flex flex-col gap-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <PriorityBadge priority={p.effective} />
            {p.overridden && <span className="text-base-content/60 text-xs">Your override. The suggestion was {PRIORITY[p.suggested].label.toLowerCase()}.</span>}
            {p.confidence != null && !p.overridden && <span className="text-base-content/60 text-xs">{Math.round(p.confidence * 100)}% confidence</span>}
          </div>
          <p>{p.explanation}.</p>
          {p.overridden && p.override_reason && <p className="text-base-content/60 text-xs">Reason: {p.override_reason}</p>}
          <p className="text-base-content/50 text-xs">Based only on stated deadlines, waiting time and workflow state. It never changes the request's status.</p>
          <button className="btn btn-xs self-start" onClick={() => { setValue(p.overridden ? p.effective : ''); setEditing(true) }}>Change priority</button>
        </div>
      ) : <p className="text-base-content/60 mt-1 text-sm">Not assessed yet.</p>}
      <Modal open={editing} onClose={() => setEditing(false)} size="sm" title="Change priority"
        actions={<><button className="btn btn-ghost btn-sm" onClick={() => setEditing(false)}>Cancel</button>
          <button className="btn btn-primary btn-sm" disabled={override.isPending || (!!value && !reason.trim())}
            onClick={async () => { await override.mutateAsync({ id: r.id, priority: value, reason }); setEditing(false); setReason('') }}>{value ? 'Set priority' : 'Use the suggestion'}</button></>}>
        <div className="flex flex-wrap gap-2">
          {(['', 'URGENT', 'HIGH', 'MEDIUM', 'LOW'] as const).map((k) => (
            <button key={k || 'auto'} type="button" onClick={() => setValue(k)} className={`btn btn-sm rounded-full ${value === k ? 'btn-neutral' : 'btn-outline border-base-300'}`}>{k ? PRIORITY[k].label : 'Suggested'}</button>
          ))}
        </div>
        {value && <Field label="Why? (required)"><input className="input w-full" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Offer deadline confirmed by the student" /></Field>}
        <ErrorAlert error={override.error} />
      </Modal>
    </section>
  )
}

function SuggestionsSection({ r }: { r: RequestDetail }) {
  const live = r.availability_checks?.find((c) => ['PENDING', 'CONFIRMED'].includes(c.status) && !c.is_expired)
  const open = ['SUBMITTED', 'UNDER_REVIEW', 'WAITING'].includes(r.status)
  const suggestions = useSuggestions(r.id, open && !live)
  const { sendCheck } = useRequestActions()
  if (!open) return null
  if (live) {
    return (
      <section className="border-primary/30 rounded-2xl border p-4">
        <h4 className="font-semibold">{live.status === 'PENDING' ? `Waiting for ${live.mentor_summary?.name}` : `${live.mentor_summary?.name} is available`}</h4>
        <p className="text-base-content/65 text-sm">{live.status === 'PENDING' ? `They have until ${formatDate(live.expires_at)} to answer.` : 'Approve the pairing to start the mentorship.'}</p>
        {live.status === 'CONFIRMED' && <Link to="/admin/matching?tab=confirmed" className="btn btn-primary btn-sm mt-3">Go to final approval</Link>}
      </section>
    )
  }
  return (
    <section>
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <h4 className="font-semibold">Suggested mentors</h4>
        {suggestions.data && <span className="text-base-content/50 text-xs">{suggestions.data.ai_explanation_used ? 'Rules with local AI notes. Advisory only.' : 'Ranked by domain, skills and experience. Advisory only.'}</span>}
      </div>
      {suggestions.isPending ? <Loading /> : suggestions.isError ? <ErrorAlert error={suggestions.error} /> : suggestions.data.candidates.length === 0 ? (
        <p className="text-base-content/60 text-sm">No verified mentors are free right now. Mark the request as waiting and check back.</p>
      ) : (
        <ul className="rows">
          {suggestions.data.candidates.map((c) => (
            <li key={c.mentor_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2 font-medium">{c.name}{c.is_student_preference && <Badge tone="warning">Student's choice</Badge>}</div>
                <div className="text-base-content/60 text-sm">{c.domain}; {c.specialty}; {c.experience_years} yrs</div>
                <div className="text-base-content/50 text-xs">{c.reasons.join('; ')}</div>
              </div>
              <span className="font-display text-base-content/50 text-sm tabular-nums">{c.final_score}</span>
              <button className="btn btn-sm" disabled={sendCheck.isPending} onClick={() => sendCheck.mutate({ id: r.id, mentor_id: c.mentor_id })}><Send size={14} />Ask if available</button>
            </li>
          ))}
        </ul>
      )}
      <ErrorAlert error={sendCheck.error} />
    </section>
  )
}

/** Full IIC review of one request, opened as a wide sheet. */
export function RequestReviewModal({ requestId, onClose }: { requestId: number | null; onClose: () => void }) {
  const query = useRequest(requestId ?? undefined)
  const { transition } = useRequestActions()
  const [closing, setClosing] = useState(false)
  const [note, setNote] = useState('')
  const r = query.data
  const open = r && ['SUBMITTED', 'UNDER_REVIEW', 'WAITING'].includes(r.status)
  return (
    <Modal variant="sheet" wide open={requestId != null} onClose={onClose} title={r ? `${r.student_summary?.name}: ${r.domain}` : 'Request'}
      subtitle={r && `${r.student_summary?.email}. ${PATHWAY[r.pathway]} pathway, sent ${formatDateTime(r.submitted_at)}.`}>
      {query.isPending ? <Loading /> : query.isError ? <ErrorAlert error={query.error} /> : r && (
        <>
          <div className="flex flex-wrap items-center gap-2"><StageBadge stage={r.stage} /><span className="text-base-content/70 text-sm">{r.next_action}</span></div>
          <Confluence stage={r.stage} waiting={r.stage === 'WAITING'} />
          <section>
            <h4 className="mb-1 font-semibold">The student's need</h4>
            <p className="whitespace-pre-line">{r.problem_statement}</p>
            {r.background && <p className="text-base-content/60 mt-2 text-sm whitespace-pre-line">{r.background}</p>}
            {r.preferred_mentor_summary && <p className="bg-accent/15 mt-3 rounded-xl px-3 py-2 text-sm">The student would like <strong>{r.preferred_mentor_summary.name}</strong> ({r.preferred_mentor_summary.current_role}). This is a preference, not a pairing.</p>}
          </section>
          <PrioritySection r={r} />
          <SuggestionsSection r={r} />
          {r.availability_checks && r.availability_checks.length > 0 && (
            <section>
              <h4 className="mb-2 font-semibold">Mentors asked so far</h4>
              <ul className="rows text-sm">
                {r.availability_checks.map((c) => (
                  <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                    <span><span className="font-medium">{c.mentor_summary?.name}</span><span className="text-base-content/55 ml-2">asked {formatDate(c.sent_at)}</span>{c.reason && <span className="text-base-content/55 block text-xs">“{c.reason}”</span>}</span>
                    <Badge tone={c.status === 'USED' || c.status === 'CONFIRMED' ? 'success' : c.status === 'PENDING' && !c.is_expired ? 'info' : 'neutral'}>{c.is_expired && c.status === 'PENDING' ? 'Expired' : c.status === 'USED' ? 'Approved' : c.status.toLowerCase()}</Badge>
                  </li>
                ))}
              </ul>
            </section>
          )}
          <section>
            <h4 className="mb-3 font-semibold">History</h4>
            <Timeline items={[...r.timeline].reverse().map((t) => ({ key: t.id, title: t.label, detail: [t.note, t.actor_role && `By ${t.actor_role.toLowerCase()}.`].filter(Boolean).join(' '), at: t.created_at }))} />
          </section>
          {open && (
            <div className="border-base-300 flex flex-wrap gap-2 border-t pt-4">
              {r.status === 'SUBMITTED' && <button className="btn btn-sm" disabled={transition.isPending} onClick={() => transition.mutate({ id: r.id, to_status: 'UNDER_REVIEW' })}>Start review</button>}
              {r.status !== 'WAITING' && r.stage !== 'AVAILABILITY_CHECK_SENT' && <button className="btn btn-sm" disabled={transition.isPending} onClick={() => transition.mutate({ id: r.id, to_status: 'WAITING' })}>No mentor free yet</button>}
              <button className="btn btn-ghost btn-sm text-error ml-auto" onClick={() => setClosing(true)}>Close request</button>
            </div>
          )}
          <ErrorAlert error={transition.error} />
          <Modal open={closing} onClose={() => setClosing(false)} size="sm" title="Close this request?"
            actions={<><button className="btn btn-ghost btn-sm" onClick={() => setClosing(false)}>Keep open</button>
              <button className="btn btn-error btn-sm" disabled={!note.trim() || transition.isPending} onClick={async () => { await transition.mutateAsync({ id: r.id, to_status: 'CLOSED', note }); setClosing(false) }}>Close request</button></>}>
            <Field label="Reason (sent to the student)"><textarea className="textarea w-full" rows={3} maxLength={300} value={note} onChange={(e) => setNote(e.target.value)} /></Field>
          </Modal>
        </>
      )}
    </Modal>
  )
}

type QueueTab = 'review' | 'open' | 'matched' | 'closed' | 'all'
const QUEUE: Record<QueueTab, string> = { review: 'SUBMITTED,UNDER_REVIEW,WAITING', open: 'SUBMITTED,UNDER_REVIEW,WAITING', matched: 'MATCHED', closed: 'WITHDRAWN,CLOSED', all: '' }
const RANK: Record<Priority, number> = { URGENT: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }

export function RequestsQueuePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const tab = (params.get('queue') as QueueTab) || 'review'
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const requests = useRequests({ status: QUEUE[tab], search, page })
  let rows = requests.data?.results ?? []
  if (tab === 'review') rows = rows.filter((r) => ['SUBMITTED', 'UNDER_REVIEW', 'WAITING'].includes(r.stage))
  if (tab === 'review' || tab === 'open') rows = [...rows].sort((a, b) => (RANK[a.priority?.effective ?? 'LOW'] - RANK[b.priority?.effective ?? 'LOW']) || a.submitted_at.localeCompare(b.submitted_at))
  const openRequest = (rid: number) => navigate({ pathname: `/admin/requests/${rid}`, search: params.toString() })
  return (
    <>
      <PageHeader title="Mentorship requests" subtitle="Sorted by suggested priority. A pairing always needs a mentor's yes and your final approval." />
      <div className="flex flex-wrap items-start justify-between gap-2">
        <Tabs<QueueTab> value={tab} onChange={(k) => { setPage(1); setParams({ queue: k }) }} tabs={[
          { key: 'review', label: 'Needs review' }, { key: 'open', label: 'All open' }, { key: 'matched', label: 'Matched' }, { key: 'closed', label: 'Withdrawn or closed' }, { key: 'all', label: 'Everything' }]} />
        <SearchBox value={search} onChange={(v) => { setSearch(v); setPage(1) }} placeholder="Domain or student" />
      </div>
      <Card>
        {requests.isPending ? <Loading /> : requests.isError ? <ErrorAlert error={requests.error} /> : rows.length === 0 ? <EmptyState title="Nothing in this queue" description={tab === 'review' ? 'Every open request has a mentor check in progress.' : undefined} /> : (
          <>
            <ul className="rows">
              {rows.map((r) => (
                <li key={r.id}>
                  <RowButton onClick={() => openRequest(r.id)}>
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-2"><span className="font-medium">{r.student_summary?.name}</span><span className="text-base-content/50 text-sm">{r.domain}</span></span>
                      <span className="text-base-content/60 block truncate text-sm">{truncate(r.problem_statement, 120)}</span>
                    </span>
                    <span className="hidden flex-col items-end gap-1 sm:flex">
                      {r.priority && <PriorityBadge priority={r.priority.effective} />}
                      <span className="text-base-content/50 text-xs">{timeAgo(r.submitted_at)}</span>
                    </span>
                    <StageBadge stage={r.stage} />
                  </RowButton>
                </li>
              ))}
            </ul>
            <Pager page={page} count={requests.data.count} onChange={setPage} />
          </>
        )}
      </Card>
      <RequestReviewModal requestId={id ? Number(id) : null} onClose={() => navigate({ pathname: '/admin/requests', search: params.toString() })} />
    </>
  )
}

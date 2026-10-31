import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router'
import { fieldErrors } from '../../lib/api'
import { PATHWAY, STAGE, formatDate, formatDateTime } from '../../lib/format'
import { useRequest, useRequestActions, useRequests } from '../../lib/queries'
import type { DirectoryMentor, MentoringRequest, Pathway } from '../../lib/types'
import { ErrorAlert, Field, Loading, Modal, StageBadge, Timeline } from '../../components/ui'
import { Confluence } from '../../components/Confluence'

const OPEN = ['SUBMITTED', 'UNDER_REVIEW', 'WAITING']

/** The student's open request or active mentorship (only one is allowed at a time). */
export function useOpenRequest() {
  const requests = useRequests()
  const open = requests.data?.results.find((r) => OPEN.includes(r.status) || r.stage === 'ACTIVE')
  return { open, loading: requests.isPending }
}

interface RequestForm { pathway: Pathway; domain: string; background: string; problem_statement: string }

/** New mentoring request. A preferred mentor is advisory: IIC still checks availability and approves the pairing. */
export function RequestFormModal({ open, onClose, mentor }: { open: boolean; onClose: () => void; mentor?: DirectoryMentor | null }) {
  const { create } = useRequestActions()
  const navigate = useNavigate()
  const [errors, setErrors] = useState<Record<string, string>>({})
  const { register, handleSubmit, watch, reset } = useForm<RequestForm>({ values: { pathway: 'JOB', domain: mentor?.domain ?? '', background: '', problem_statement: '' } })
  const length = watch('problem_statement')?.trim().length ?? 0
  const close = () => { reset(); setErrors({}); create.reset(); onClose() }

  const onSubmit = handleSubmit(async (values) => {
    setErrors({})
    try {
      const created = await create.mutateAsync({ ...values, preferred_mentor: mentor?.id ?? null })
      close()
      navigate(`/requests/${created.id}`)
    } catch (err) {
      setErrors(fieldErrors(err))
    }
  })

  return (
    <Modal open={open} onClose={close} size="lg" title={mentor ? `Ask for ${mentor.name.split(' ')[0]} as your mentor` : 'Request a mentor'}
      subtitle="IIC reads every request, checks a mentor's availability, and approves the final pairing.">
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        {mentor && (
          <div className="bg-primary/8 rounded-xl p-3 text-sm">
            <span className="font-semibold">{mentor.name}</span> will be noted as your preference. If they are unavailable, IIC suggests someone else for the same need.
          </div>
        )}
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Career pathway" error={errors.pathway}>
            <select className="select w-full" {...register('pathway')}>{Object.entries(PATHWAY).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
          </Field>
          <Field label="Domain" error={errors.domain}><input className="input w-full" maxLength={150} placeholder="Data science, product, research…" {...register('domain', { required: true })} /></Field>
        </div>
        <Field label="What should IIC know about you?" error={errors.background} hint="Courses, projects or work experience that relate to your question.">
          <textarea className="textarea w-full" rows={2} {...register('background')} />
        </Field>
        <Field label="What do you want help with?" error={errors.problem_statement}
          hint={length < 80 ? `${80 - length} more characters needed. Say what you want to achieve and by when.` : 'Leave out phone numbers and personal email; they are removed before mentors see this.'}>
          <textarea className="textarea w-full" rows={5} {...register('problem_statement', { required: true })} />
        </Field>
        <progress className={`progress h-1 ${length >= 80 ? 'progress-primary' : 'progress-accent'}`} value={Math.min(length, 80)} max={80} aria-hidden />
        {create.isError && !Object.keys(errors).length && <ErrorAlert error={create.error} />}
        {errors.preferred_mentor && <p className="text-error text-sm">{errors.preferred_mentor}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn btn-ghost" onClick={close}>Cancel</button>
          <button className="btn btn-primary" disabled={create.isPending || length < 80}>{create.isPending && <span className="loading loading-spinner loading-xs" />}Send request to IIC</button>
        </div>
      </form>
    </Modal>
  )
}

export function WithdrawButton({ request, onDone }: { request: MentoringRequest; onDone?: () => void }) {
  const { withdraw } = useRequestActions()
  const [confirming, setConfirming] = useState(false)
  if (!OPEN.includes(request.status)) return null
  return (
    <>
      <button className="btn btn-ghost btn-sm text-error" onClick={() => setConfirming(true)}>Withdraw</button>
      <Modal open={confirming} onClose={() => setConfirming(false)} size="sm" title="Withdraw this request?"
        actions={<><button className="btn btn-ghost btn-sm" onClick={() => setConfirming(false)}>Keep request</button>
          <button className="btn btn-error btn-sm" disabled={withdraw.isPending} onClick={async () => { await withdraw.mutateAsync(request.id); setConfirming(false); onDone?.() }}>Withdraw request</button></>}>
        <p className="text-sm">IIC stops looking for a mentor, and any pending availability check is cancelled. You can submit a new request afterwards.</p>
        <ErrorAlert error={withdraw.error} />
      </Modal>
    </>
  )
}

export function RequestDetailModal({ requestId, onClose }: { requestId: number | null; onClose: () => void }) {
  const query = useRequest(requestId ?? undefined)
  const r = query.data
  return (
    <Modal variant="sheet" wide open={requestId != null} onClose={onClose}
      title={r ? r.domain : 'Request'} subtitle={r ? `${PATHWAY[r.pathway]} pathway, sent ${formatDate(r.submitted_at)}` : undefined}>
      {query.isPending ? <Loading /> : query.isError ? <ErrorAlert error={query.error} /> : r && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <StageBadge stage={r.stage} />
            {r.next_action && <span className="text-base-content/70 text-sm">{r.next_action}</span>}
          </div>
          <div className="bg-neutral rounded-2xl px-4 pt-4 pb-2"><Confluence stage={r.stage} tone="dark" waiting={r.stage === 'WAITING'} /></div>
          <section>
            <h4 className="mb-1 font-semibold">What you asked for</h4>
            <p className="text-base-content/80 whitespace-pre-line">{r.problem_statement}</p>
            {r.background && <p className="text-base-content/60 mt-2 text-sm whitespace-pre-line">{r.background}</p>}
          </section>
          <dl className="grid gap-3 sm:grid-cols-2">
            <div className="bg-base-200 rounded-xl p-3">
              <dt className="text-base-content/60 text-xs">Preferred mentor</dt>
              <dd className="font-medium">{r.preferred_mentor_summary ? `${r.preferred_mentor_summary.name}, ${r.preferred_mentor_summary.current_role}` : 'No preference'}</dd>
            </div>
            <div className="bg-base-200 rounded-xl p-3">
              <dt className="text-base-content/60 text-xs">Assigned mentor</dt>
              <dd className="font-medium">{r.assigned_mentor ? <Link className="link" to="/mentorship">{r.assigned_mentor.name}</Link> : 'Shown once IIC approves'}</dd>
            </div>
          </dl>
          <section>
            <h4 className="mb-3 font-semibold">History</h4>
            <Timeline items={[...r.timeline].reverse().map((t) => ({
              key: t.id, title: t.label, detail: t.note, at: t.created_at,
              tone: STAGE[t.to_status as keyof typeof STAGE]?.tone === 'success' ? 'success' : t.to_status === 'WAITING' ? 'warning' : undefined,
            }))} />
          </section>
          <div className="border-base-300 flex justify-between gap-2 border-t pt-3">
            <span className="text-base-content/50 self-center text-xs">Last update {formatDateTime(r.last_status_at)}</span>
            <WithdrawButton request={r} onDone={onClose} />
          </div>
        </>
      )}
    </Modal>
  )
}

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'
import { Link2, Pencil } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { fieldErrors } from '../lib/api'
import { formatDate } from '../lib/format'
import { useMentorProfile, useProfileActions, useStudentProfile } from '../lib/queries'
import type { MentorProfile, StudentProfile } from '../lib/types'
import { Badge, Card, EmptyState, ErrorAlert, Field, Loading, Modal, PageHeader } from '../components/ui'
import { AssistantPanel, NotificationsList } from '../components/panels'

export function AssistantPage() {
  return (
    <>
      <PageHeader title="Ask Sangam" subtitle="Quick answers about how mentoring works here. You can also open the assistant from the top bar on any page." />
      <div className="panel max-w-3xl p-6"><AssistantPanel /></div>
    </>
  )
}

export function NotificationsPage() {
  return (
    <>
      <PageHeader title="Notifications" />
      <div className="panel max-w-3xl px-6 py-3"><NotificationsList /></div>
    </>
  )
}

// ---------------------------------------------------------------------- profile
function NameModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { me } = useAuth()
  const { updateMe } = useProfileActions()
  const { register, handleSubmit } = useForm({ values: { first_name: me?.first_name ?? '', last_name: me?.last_name ?? '' } })
  return (
    <Modal open={open} onClose={onClose} size="sm" title="Your name">
      <form onSubmit={handleSubmit(async (v) => { await updateMe.mutateAsync(v); onClose() })} className="flex flex-col gap-3">
        <Field label="First name"><input className="input w-full" {...register('first_name')} /></Field>
        <Field label="Last name"><input className="input w-full" {...register('last_name')} /></Field>
        <ErrorAlert error={updateMe.error} />
        <div className="flex justify-end gap-2"><button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={updateMe.isPending}>Save name</button></div>
      </form>
    </Modal>
  )
}

function StudentProfileSection() {
  const profile = useStudentProfile()
  const { updateStudent } = useProfileActions()
  const [editing, setEditing] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const { register, handleSubmit } = useForm<{ iitm_roll_number: string; level: StudentProfile['level']; courses: string; cgpa: string }>({
    values: profile.data ? { ...profile.data, courses: profile.data.courses.join(', '), cgpa: profile.data.cgpa ?? '' } : undefined,
  })
  if (profile.isPending) return <Loading />
  if (profile.isError) return <ErrorAlert error={profile.error} />
  const p = profile.data
  const locked = p.approval_status === 'APPROVED'
  const onSubmit = handleSubmit(async (v) => {
    setErrors({})
    try { await updateStudent.mutateAsync({ ...v, courses: v.courses.split(',').map((c) => c.trim()).filter(Boolean), cgpa: v.cgpa || null }); setEditing(false) }
    catch (err) { setErrors(fieldErrors(err)) }
  })
  return (
    <Card title="Academic details" actions={locked ? <Badge tone="success">Approved by IIC</Badge> : <button className="btn btn-sm" onClick={() => setEditing(true)}><Pencil size={14} />Edit</button>}>
      {p.approval_status === 'REJECTED' && <div className="bg-accent/15 rounded-xl px-3 py-2 text-sm">IIC's note: {p.rejection_reason || 'Please check your details.'} Saving sends your profile back for review.</div>}
      {p.approval_status === 'PENDING' && <div className="bg-info/10 rounded-xl px-3 py-2 text-sm">IIC is checking these details against IITM records.</div>}
      <dl className="grid grid-cols-2 gap-3">
        {[['Roll number', p.iitm_roll_number], ['Level', p.level === 'DEGREE' ? 'Degree' : 'Diploma'], ['CGPA', p.cgpa ?? 'Not given'], ['Courses', p.courses.join(', ')]].map(([k, v]) => (
          <div key={k}><dt className="text-base-content/55 text-xs">{k}</dt><dd className="font-medium">{v}</dd></div>
        ))}
      </dl>
      {locked && <p className="text-base-content/55 text-xs">Approved records are locked. Ask IIC if something needs correcting.</p>}
      <Modal open={editing} onClose={() => setEditing(false)} title="Edit academic details" subtitle="Saving sends your profile to IIC for review.">
        <form onSubmit={onSubmit} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Roll number" error={errors.iitm_roll_number}><input className="input w-full" {...register('iitm_roll_number')} /></Field>
          <Field label="Level" error={errors.level}><select className="select w-full" {...register('level')}><option value="DEGREE">Degree</option><option value="DIPLOMA">Diploma</option></select></Field>
          <Field label="Courses completed" error={errors.courses} hint="Separate with commas."><input className="input w-full" {...register('courses')} /></Field>
          <Field label="CGPA" error={errors.cgpa}><input type="number" step="0.01" min="0" max="10" className="input w-full" {...register('cgpa')} /></Field>
          {updateStudent.isError && !Object.keys(errors).length && <div className="sm:col-span-2"><ErrorAlert error={updateStudent.error} /></div>}
          <div className="flex justify-end gap-2 sm:col-span-2"><button type="button" className="btn btn-ghost" onClick={() => setEditing(false)}>Cancel</button><button className="btn btn-primary" disabled={updateStudent.isPending}>Save and send for review</button></div>
        </form>
      </Modal>
    </Card>
  )
}

function MentorProfileSection() {
  const profile = useMentorProfile()
  const { updateMentor } = useProfileActions()
  const [editing, setEditing] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const { register, handleSubmit } = useForm<Omit<MentorProfile, 'skills'> & { skills: string }>({
    values: profile.data ? { ...profile.data, skills: profile.data.skills.join(', ') } : undefined,
  })
  if (profile.isPending) return <Loading />
  if (profile.isError) return <ErrorAlert error={profile.error} />
  const p = profile.data
  const onSubmit = handleSubmit(async (v) => {
    setErrors({})
    try {
      await updateMentor.mutateAsync({ domain: v.domain, specialty: v.specialty, current_role: v.current_role, company: v.company, career_path: v.career_path,
        experience_years: Number(v.experience_years), bio: v.bio, linkedin_url: v.linkedin_url, skills: v.skills.split(',').map((s) => s.trim()).filter(Boolean) })
      setEditing(false)
    } catch (err) { setErrors(fieldErrors(err)) }
  })
  const text = (name: 'domain' | 'specialty' | 'current_role' | 'company' | 'career_path' | 'linkedin_url' | 'skills', label: string, hint?: string) => (
    <Field label={label} error={errors[name]} hint={hint}><input className="input w-full" {...register(name)} /></Field>
  )
  return (
    <Card title="How students see you" actions={<button className="btn btn-sm" onClick={() => setEditing(true)}><Pencil size={14} />Edit</button>}>
      <div className="flex flex-wrap gap-1.5">
        <Badge tone={p.is_verified ? 'success' : 'warning'}>{p.is_verified ? 'Verified by IIC' : 'Waiting for IIC verification'}</Badge>
        <Badge tone={p.is_discoverable ? 'primary' : 'ghost'}>{p.is_discoverable ? 'Listed in Discover Mentors' : 'Not listed for students'}</Badge>
      </div>
      <div>
        <p className="font-display text-xl font-semibold">{p.current_role}{p.company && ` at ${p.company}`}</p>
        <p className="text-base-content/65">{p.domain}; {p.specialty}. {p.experience_years} years of experience.</p>
      </div>
      {p.bio && <p className="text-base-content/80">{p.bio}</p>}
      {p.skills.length > 0 && <div className="flex flex-wrap gap-1.5">{p.skills.map((s) => <span key={s} className="bg-base-200 rounded-full px-3 py-1 text-sm">{s}</span>)}</div>}
      {p.linkedin_url && <a href={p.linkedin_url} target="_blank" rel="noopener noreferrer" className="link link-hover inline-flex items-center gap-1.5 text-sm"><Link2 size={15} />LinkedIn profile</a>}
      <p className="text-base-content/55 text-xs">Alumni record {p.alumni_roll_number || '—'}, class of {p.graduation_year ?? '—'}{p.verified_at && `, verified ${formatDate(p.verified_at)}`}. Students never see your email before IIC approves a pairing.</p>
      <Link to="/mentor/calendar" className="link link-hover text-sm">Google Calendar connection</Link>
      <Modal open={editing} onClose={() => setEditing(false)} size="lg" title="Edit your professional profile" subtitle="Verification and directory listing are managed by IIC.">
        <form onSubmit={onSubmit} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {text('current_role', 'Current role')}{text('company', 'Company')}
          {text('domain', 'Domain')}{text('specialty', 'Specialty')}
          {text('career_path', 'Career pathway', 'For example: job, higher studies, venture.')}
          <Field label="Years of experience" error={errors.experience_years}><input type="number" min={0} max={80} className="input w-full" {...register('experience_years')} /></Field>
          <div className="sm:col-span-2">{text('skills', 'Skills', 'Separate with commas. Up to 15.')}</div>
          <div className="sm:col-span-2">{text('linkedin_url', 'LinkedIn profile URL (optional)', 'Shown in the directory and to your mentee.')}</div>
          <div className="sm:col-span-2"><Field label="Professional summary" error={errors.bio}><textarea className="textarea w-full" rows={3} maxLength={500} {...register('bio')} /></Field></div>
          {updateMentor.isError && !Object.keys(errors).length && <div className="sm:col-span-2"><ErrorAlert error={updateMentor.error} /></div>}
          <div className="flex justify-end gap-2 sm:col-span-2"><button type="button" className="btn btn-ghost" onClick={() => setEditing(false)}>Cancel</button><button className="btn btn-primary" disabled={updateMentor.isPending}>Save profile</button></div>
        </form>
      </Modal>
    </Card>
  )
}

export function ProfilePage() {
  const { me, role } = useAuth()
  const [editingName, setEditingName] = useState(false)
  return (
    <>
      <section className="mb-8 flex flex-wrap items-center gap-5">
        <span className="bg-neutral text-neutral-content font-display grid size-20 place-items-center rounded-3xl text-3xl font-semibold">{me?.display_name.slice(0, 1).toUpperCase()}</span>
        <div>
          <h1 className="text-title sm:text-display font-semibold">{me?.display_name}</h1>
          <p className="text-base-content/65">{me?.email}</p>
        </div>
        <button className="btn btn-sm ml-auto" onClick={() => setEditingName(true)}><Pencil size={14} />Edit name</button>
      </section>
      <div className="flex max-w-3xl flex-col gap-6">
        {role === 'STUDENT' && <StudentProfileSection />}
        {role === 'MENTOR' && <MentorProfileSection />}
        {role === 'ADMIN' && <Card title="IIC administrator"><p className="text-base-content/70 text-sm">Your access comes from IIC staff permissions on the server. Records without a screen here are in Django admin at <code>/admin/</code>.</p></Card>}
      </div>
      <NameModal open={editingName} onClose={() => setEditingName(false)} />
    </>
  )
}

export function NotFoundPage() {
  return <EmptyState title="This page doesn't exist" description="It may have moved, or it isn't part of your role." action={<Link to="/dashboard" className="btn btn-primary btn-sm">Back to dashboard</Link>} />
}

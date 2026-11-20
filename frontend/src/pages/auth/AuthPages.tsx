import { useState, type ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router'
import { CheckCircle2 } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { errorMessage, fieldErrors, post } from '../../lib/api'
import { Brand } from '../../layout/AppShell'
import { Field } from '../../components/ui'
import { Confluence } from '../../components/Confluence'

/** Split screen: the confluence on the river side, the form on the paper side. */
function AuthFrame({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
      <aside className="bg-neutral text-neutral-content relative hidden flex-col justify-between overflow-hidden p-12 lg:flex">
        <Brand light />
        <div className="max-w-lg">
          <h2 className="font-display text-[2.75rem] leading-[1.05] font-semibold tracking-tight text-white">Where your question meets someone who has lived the answer.</h2>
          <p className="text-neutral-content/70 mt-4 text-lg">IITM BS students and verified alumni, brought together by IIC.</p>
          <div className="mt-10"><Confluence stage="AWAITING_IIC_APPROVAL" tone="dark" /></div>
        </div>
        <p className="text-neutral-content/45 text-sm">Every pairing is reviewed and approved by IIC. Conversations are never recorded.</p>
      </aside>
      <main className="flex items-center justify-center px-5 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden"><Brand /></div>
          <h1 className="text-title font-semibold">{title}</h1>
          <p className="text-base-content/65 mt-1 mb-6">{subtitle}</p>
          {children}
        </div>
      </main>
    </div>
  )
}

function FormError({ message }: { message: string }) {
  return message ? <div role="alert" className="bg-error/10 text-error rounded-xl px-3 py-2 text-sm">{message}</div> : null
}

export function LoginPage() {
  const { me, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState('')
  const { register, handleSubmit, formState: { isSubmitting } } = useForm<{ email: string; password: string }>()
  if (me) return <Navigate to="/dashboard" replace />
  const from = (location.state as { from?: string } | null)?.from ?? '/dashboard'
  const onSubmit = handleSubmit(async ({ email, password }) => {
    setError('')
    try {
      await login(email.trim(), password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(errorMessage(err, 'Sign-in failed.'))
    }
  })
  return (
    <AuthFrame title="Sign in" subtitle="Students, alumni mentors and IIC staff all sign in here.">
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <FormError message={error} />
        <Field label="Email"><input type="email" autoComplete="email" className="input input-lg w-full" {...register('email', { required: true })} /></Field>
        <Field label="Password"><input type="password" autoComplete="current-password" className="input input-lg w-full" {...register('password', { required: true })} /></Field>
        <button className="btn btn-primary btn-lg mt-2" disabled={isSubmitting}>{isSubmitting && <span className="loading loading-spinner loading-sm" />}Sign in</button>
      </form>
      <p className="text-base-content/65 mt-6 text-sm">New IITM student? <Link to="/register" className="link link-primary font-medium">Create an account</Link></p>
    </AuthFrame>
  )
}

interface RegisterForm {
  email: string; password: string; first_name: string; last_name: string; iitm_roll_number: string
  level: 'DIPLOMA' | 'DEGREE'; courses: string; cgpa: string
}

export function RegisterPage() {
  const [done, setDone] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [error, setError] = useState('')
  const { register, handleSubmit, formState: { isSubmitting } } = useForm<RegisterForm>({ defaultValues: { level: 'DEGREE' } })
  const onSubmit = handleSubmit(async (values) => {
    setErrors({}); setError('')
    try {
      await post('/auth/register/', { ...values, courses: values.courses.split(',').map((c) => c.trim()).filter(Boolean), cgpa: values.cgpa ? values.cgpa : null })
      setDone(true)
    } catch (err) {
      const fields = fieldErrors(err)
      setErrors(fields)
      if (!Object.keys(fields).length) setError(errorMessage(err))
    }
  })
  if (done) {
    return (
      <AuthFrame title="You're registered" subtitle="IIC will check your academic details against IITM records. We'll email you when you can ask for a mentor.">
        <div className="bg-success/10 mb-6 flex items-center gap-3 rounded-xl p-4 text-sm"><CheckCircle2 size={20} className="text-success" />Registration received</div>
        <Link to="/login" className="btn btn-primary btn-lg w-full">Go to sign in</Link>
      </AuthFrame>
    )
  }
  return (
    <AuthFrame title="Create your account" subtitle="Use your IITM email. IIC approves every student before matching.">
      <form onSubmit={onSubmit} className="flex flex-col gap-3" noValidate>
        <FormError message={error} />
        <div className="grid grid-cols-2 gap-3">
          <Field label="First name" error={errors.first_name}><input className="input w-full" {...register('first_name')} /></Field>
          <Field label="Last name" error={errors.last_name}><input className="input w-full" {...register('last_name')} /></Field>
        </div>
        <Field label="IITM email" error={errors.email}><input type="email" autoComplete="email" className="input w-full" placeholder="you@ds.study.iitm.ac.in" {...register('email')} /></Field>
        <Field label="Password" error={errors.password} hint="At least 8 characters, not a common password."><input type="password" autoComplete="new-password" className="input w-full" {...register('password')} /></Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Roll number" error={errors.iitm_roll_number}><input className="input w-full" {...register('iitm_roll_number')} /></Field>
          <Field label="Level" error={errors.level}><select className="select w-full" {...register('level')}><option value="DEGREE">Degree</option><option value="DIPLOMA">Diploma</option></select></Field>
        </div>
        <Field label="Courses completed" error={errors.courses} hint="Separate with commas, e.g. Python, MLF"><input className="input w-full" {...register('courses')} /></Field>
        <Field label="CGPA" error={errors.cgpa}><input type="number" step="0.01" min="0" max="10" className="input w-full" {...register('cgpa')} /></Field>
        <button className="btn btn-primary btn-lg mt-2" disabled={isSubmitting}>{isSubmitting && <span className="loading loading-spinner loading-sm" />}Create account</button>
      </form>
      <p className="text-base-content/65 mt-6 text-sm">Already registered? <Link to="/login" className="link link-primary font-medium">Sign in</Link></p>
    </AuthFrame>
  )
}

export function MentorActivatePage() {
  const [params] = useSearchParams()
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const { register, handleSubmit, watch, formState: { isSubmitting } } = useForm<{ password: string; confirm: string }>()
  const mismatch = !!watch('confirm') && watch('password') !== watch('confirm')
  const onSubmit = handleSubmit(async ({ password }) => {
    setError('')
    try {
      await post('/auth/mentor/activate/', { uid: params.get('uid'), token: params.get('token'), password })
      setDone(true)
    } catch (err) {
      setError(errorMessage(err))
    }
  })
  if (done) {
    return (
      <AuthFrame title="Your account is ready" subtitle="Sign in to see availability requests from IIC.">
        <Link to="/login" className="btn btn-primary btn-lg w-full">Sign in</Link>
      </AuthFrame>
    )
  }
  return (
    <AuthFrame title="Welcome, mentor" subtitle="Set a password to activate the account IIC created for you.">
      <form onSubmit={onSubmit} className="flex flex-col gap-4" noValidate>
        <FormError message={error} />
        <Field label="New password"><input type="password" autoComplete="new-password" className="input input-lg w-full" {...register('password', { required: true })} /></Field>
        <Field label="Confirm password" error={mismatch ? 'The passwords don’t match.' : undefined}><input type="password" autoComplete="new-password" className="input input-lg w-full" {...register('confirm', { required: true })} /></Field>
        <button className="btn btn-primary btn-lg mt-2" disabled={isSubmitting || mismatch}>Activate account</button>
      </form>
    </AuthFrame>
  )
}

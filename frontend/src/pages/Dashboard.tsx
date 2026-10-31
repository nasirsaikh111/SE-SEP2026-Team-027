import { lazy } from 'react'
import { useDashboard } from '../lib/queries'
import type { AdminDashboard, MentorDashboard, StudentDashboard } from '../lib/types'
import { ErrorAlert, Loading } from '../components/ui'

const StudentHome = lazy(() => import('./dashboards/StudentHome'))
const MentorHome = lazy(() => import('./dashboards/MentorHome'))
const AdminHome = lazy(() => import('./dashboards/AdminHome'))

export function greeting() {
  const h = new Date().getHours()
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
}

/** The landing page after sign-in: a greeting followed by the role's live work. */
export default function DashboardPage() {
  const query = useDashboard()
  if (query.isPending) return <Loading />
  if (query.isError) return <ErrorAlert error={query.error} />
  const d = query.data
  if (d.role === 'STUDENT') return <StudentHome d={d as StudentDashboard} />
  if (d.role === 'MENTOR') return <MentorHome d={d as MentorDashboard} />
  if (d.role === 'ADMIN') return <AdminHome d={d as AdminDashboard} />
  return <ErrorAlert error={new Error('No role')} title="Your account has no Sangam role yet. Contact IIC." />
}

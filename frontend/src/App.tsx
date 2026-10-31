import { lazy, Suspense, type ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router'
import { RequireAuth, RequireRole } from './auth/AuthContext'
import { AppShell } from './layout/AppShell'
import { Loading } from './components/ui'
import { LoginPage, MentorActivatePage, RegisterPage } from './pages/auth/AuthPages'
import DashboardPage from './pages/Dashboard'
import { AssistantPage, NotFoundPage, NotificationsPage, ProfilePage } from './pages/SharedPages'
import type { Role } from './lib/types'

const DiscoverMentorsPage = lazy(() => import('./pages/student/DiscoverMentors'))
const student = () => import('./pages/student/StudentPages')
const MyRequestsPage = lazy(() => student().then((m) => ({ default: m.MyRequestsPage })))
const MyMentorshipPage = lazy(() => student().then((m) => ({ default: m.MyMentorshipPage })))
const MeetingsGoalsPage = lazy(() => student().then((m) => ({ default: m.MeetingsGoalsPage })))
const mentor = () => import('./pages/mentor/MentorPages')
const AvailabilityRequestsPage = lazy(() => mentor().then((m) => ({ default: m.AvailabilityRequestsPage })))
const MentorWorkspacePage = lazy(() => mentor().then((m) => ({ default: m.MentorWorkspacePage })))
const CalendarMeetingsPage = lazy(() => mentor().then((m) => ({ default: m.CalendarMeetingsPage })))
const FeedbackProgressPage = lazy(() => mentor().then((m) => ({ default: m.FeedbackProgressPage })))
const review = () => import('./pages/admin/AdminReview')
const ops = () => import('./pages/admin/AdminOperations')
const StudentApprovalsPage = lazy(() => review().then((m) => ({ default: m.StudentApprovalsPage })))
const MentorRepositoryPage = lazy(() => review().then((m) => ({ default: m.MentorRepositoryPage })))
const RequestsQueuePage = lazy(() => review().then((m) => ({ default: m.RequestsQueuePage })))
const MatchingPage = lazy(() => ops().then((m) => ({ default: m.MatchingPage })))
const ActiveMentorshipsPage = lazy(() => ops().then((m) => ({ default: m.ActiveMentorshipsPage })))
const MonitoringPage = lazy(() => ops().then((m) => ({ default: m.MonitoringPage })))
const ReportsPage = lazy(() => ops().then((m) => ({ default: m.ReportsPage })))
const AuditLogPage = lazy(() => ops().then((m) => ({ default: m.AuditLogPage })))
const KnowledgePage = lazy(() => ops().then((m) => ({ default: m.KnowledgePage })))

const only = (roles: Role[], page: ReactNode) => <RequireRole roles={roles}>{page}</RequireRole>

export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/mentor/activate" element={<MentorActivatePage />} />
        <Route element={<RequireAuth><AppShell /></RequireAuth>}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/notifications" element={<NotificationsPage />} />
          <Route path="/profile" element={<ProfilePage />} />

          <Route path="/discover" element={only(['STUDENT'], <DiscoverMentorsPage />)} />
          <Route path="/requests" element={only(['STUDENT'], <MyRequestsPage />)} />
          <Route path="/requests/:id" element={only(['STUDENT'], <MyRequestsPage />)} />
          <Route path="/mentorship" element={only(['STUDENT'], <MyMentorshipPage />)} />
          <Route path="/meetings-goals" element={only(['STUDENT'], <MeetingsGoalsPage />)} />

          <Route path="/mentor/availability" element={only(['MENTOR'], <AvailabilityRequestsPage />)} />
          <Route path="/mentor/workspace" element={only(['MENTOR'], <MentorWorkspacePage />)} />
          <Route path="/mentor/calendar" element={only(['MENTOR'], <CalendarMeetingsPage />)} />
          <Route path="/mentor/feedback" element={only(['MENTOR'], <FeedbackProgressPage />)} />

          <Route path="/admin/students" element={only(['ADMIN'], <StudentApprovalsPage />)} />
          <Route path="/admin/mentors" element={only(['ADMIN'], <MentorRepositoryPage />)} />
          <Route path="/admin/requests" element={only(['ADMIN'], <RequestsQueuePage />)} />
          <Route path="/admin/requests/:id" element={only(['ADMIN'], <RequestsQueuePage />)} />
          <Route path="/admin/matching" element={only(['ADMIN'], <MatchingPage />)} />
          <Route path="/admin/mentorships" element={only(['ADMIN'], <ActiveMentorshipsPage />)} />
          <Route path="/admin/monitoring" element={only(['ADMIN'], <MonitoringPage />)} />
          <Route path="/admin/reports" element={only(['ADMIN'], <ReportsPage />)} />
          <Route path="/admin/audit" element={only(['ADMIN'], <AuditLogPage />)} />
          <Route path="/admin/knowledge" element={only(['ADMIN'], <KnowledgePage />)} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}

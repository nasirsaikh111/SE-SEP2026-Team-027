import {
  Activity, BarChart3, BellRing, BookOpenText, Bot, CalendarClock, CalendarDays, ClipboardCheck, ClipboardList,
  Compass, FileClock, GitMerge, HandHelping, Inbox, LayoutDashboard, MessageSquareText, UserCheck, UserRound, Users, Workflow,
  type LucideIcon,
} from 'lucide-react'
import type { Role } from '../lib/types'

export interface NavItem { to: string; label: string; icon: LucideIcon }

export const NAV: Record<Role, NavItem[]> = {
  STUDENT: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/discover', label: 'Discover Mentors', icon: Compass },
    { to: '/requests', label: 'My Requests', icon: ClipboardList },
    { to: '/mentorship', label: 'My Mentorship', icon: HandHelping },
    { to: '/meetings-goals', label: 'Meetings & Goals', icon: CalendarDays },
    { to: '/assistant', label: 'AI Assistant', icon: Bot },
    { to: '/notifications', label: 'Notifications', icon: BellRing },
    { to: '/profile', label: 'My Profile', icon: UserRound },
  ],
  MENTOR: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/mentor/availability', label: 'Availability Requests', icon: Inbox },
    { to: '/mentor/workspace', label: 'Mentorship Workspace', icon: Workflow },
    { to: '/mentor/calendar', label: 'Calendar & Meetings', icon: CalendarClock },
    { to: '/mentor/feedback', label: 'Feedback & Progress', icon: MessageSquareText },
    { to: '/assistant', label: 'AI Assistant', icon: Bot },
    { to: '/profile', label: 'My Profile', icon: UserRound },
  ],
  ADMIN: [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/admin/students', label: 'Student Approvals', icon: UserCheck },
    { to: '/admin/mentors', label: 'Mentor Repository', icon: Users },
    { to: '/admin/requests', label: 'Mentorship Requests', icon: ClipboardList },
    { to: '/admin/matching', label: 'Matching & Approvals', icon: GitMerge },
    { to: '/admin/mentorships', label: 'Active Mentorships', icon: ClipboardCheck },
    { to: '/admin/monitoring', label: 'Monitoring & Alerts', icon: Activity },
    { to: '/admin/reports', label: 'Reports & Analytics', icon: BarChart3 },
    { to: '/admin/audit', label: 'Audit Log', icon: FileClock },
    { to: '/admin/knowledge', label: 'AI Knowledge Management', icon: BookOpenText },
  ],
}

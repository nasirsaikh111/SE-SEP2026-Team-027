import { createRouter, createWebHistory } from 'vue-router';

// Auth views
import WelcomeView from '../views/auth/WelcomeView.vue';
import LoginView from '../views/auth/LoginView.vue';
import RegisterView from '../views/auth/RegisterView.vue';

// Student views
import StudentDashboardView from '../views/student/StudentDashboardView.vue';
import DiscoverMentorsView from '../views/student/DiscoverMentorsView.vue';
import MyRequestsView from '../views/student/MyRequestsView.vue';
import StudentWorkspaceView from '../views/student/StudentWorkspaceView.vue';

// Mentor views
import MentorDashboardView from '../views/mentor/MentorDashboardView.vue';
import MentorWorkspaceView from '../views/mentor/MentorWorkspaceView.vue';
import MentorProfileSetupView from '../views/mentor/MentorProfileSetupView.vue';

// Admin views
import AdminInsightsView from '../views/admin/AdminInsightsView.vue';
import VerifyMentorsView from '../views/admin/VerifyMentorsView.vue';
import FlagsAuditView from '../views/admin/FlagsAuditView.vue';
import AuditLogView from '../views/admin/AuditLogView.vue';

const routes = [
  { path: '/', name: 'welcome', component: WelcomeView },
  { path: '/login', name: 'login', component: LoginView },
  { path: '/register', name: 'register', component: RegisterView },

  // Student Flow
  { path: '/student/dashboard', name: 'student-dashboard', component: StudentDashboardView },
  { path: '/student/discover', name: 'student-discover', component: DiscoverMentorsView },
  { path: '/student/requests', name: 'student-requests', component: MyRequestsView },
  { path: '/student/workspace', name: 'student-workspace', component: StudentWorkspaceView },

  // Mentor Flow
  { path: '/mentor/dashboard', name: 'mentor-dashboard', component: MentorDashboardView },
  { path: '/mentor/workspace', name: 'mentor-workspace', component: MentorWorkspaceView },
  { path: '/mentor/profile', name: 'mentor-profile', component: MentorProfileSetupView },

  // Admin Flow
  { path: '/admin/insights', name: 'admin-insights', component: AdminInsightsView },
  { path: '/admin/verify', name: 'admin-verify', component: VerifyMentorsView },
  { path: '/admin/flags', name: 'admin-flags', component: FlagsAuditView },
  { path: '/admin/audit', name: 'admin-audit', component: AuditLogView },

  // Catch-all fallback
  { path: '/:pathMatch(.*)*', redirect: '/' }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 };
  }
});

export default router;

import { createRouter, createWebHistory } from 'vue-router';

// Auth views
import WelcomeView from '../views/auth/WelcomeView.vue';
import LoginView from '../views/auth/LoginView.vue';
import RegisterView from '../views/auth/RegisterView.vue';

// Student views
import StudentDashboardView from '../views/student/StudentDashboardView.vue';

const routes = [
  { path: '/', name: 'welcome', component: WelcomeView },
  { path: '/login', name: 'login', component: LoginView },
  { path: '/register', name: 'register', component: RegisterView },

  // Student Dashboard (Step 2)
  { path: '/student/dashboard', name: 'student-dashboard', component: StudentDashboardView },

  // Fallback for Step 2
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

import { defineStore } from 'pinia';
import { Sangam, setToken, getToken } from '../api/client';

// Backend roles -> frontend roles
const ROLE_MAP = { ADMIN: 'admin', MENTOR: 'mentor', STUDENT: 'student' };

export const useAuthStore = defineStore('auth', {
  state: () => ({
    currentUser: {
      id: 'student-1',
      name: 'Hemant Dhayal',
      email: 'hemant@study.iitm.ac.in',
      rollNo: '21f100027',
      role: 'student' // 'student' | 'mentor' | 'admin'
    },
    // true once signed in against the real Django API (JWT); false = demo mode with mock data
    isLive: false,
    availableRoles: [
      { id: 'student', label: 'Student (Mentee)', defaultPath: '/student/dashboard' },
      { id: 'mentor', label: 'Mentor (Alumni)', defaultPath: '/mentor/dashboard' },
      { id: 'admin', label: 'IIC Placement Admin', defaultPath: '/admin/insights' }
    ]
  }),
  getters: {
    currentRole: (state) => state.currentUser.role,
    isStudent: (state) => state.currentUser.role === 'student',
    isMentor: (state) => state.currentUser.role === 'mentor',
    isAdmin: (state) => state.currentUser.role === 'admin'
  },
  actions: {
    switchRole(roleId) {
      this.currentUser.role = roleId;
      if (roleId === 'student') {
        this.currentUser.name = 'Hemant Dhayal (Student)';
        this.currentUser.email = 'hemant@study.iitm.ac.in';
        this.currentUser.id = 'student-1';
      } else if (roleId === 'mentor') {
        this.currentUser.name = 'Arjun K. (Mentor)';
        this.currentUser.email = 'arjun.k@alumni.iitm.ac.in';
        this.currentUser.id = 'mentor-1';
      } else if (roleId === 'admin') {
        this.currentUser.name = 'IIC Admin (Placement Cell)';
        this.currentUser.email = 'iic-head@iitm.ac.in';
        this.currentUser.id = 'admin-1';
      }
    },
    // Demo-mode login kept for the milestone walkthrough (no backend needed)
    login(email, role) {
      this.switchRole(role || 'student');
      this.currentUser.email = email;
    },
    // Real login: get a JWT, then read the user's role from /auth/me/
    async loginLive(email, password) {
      const tokens = await Sangam.login(email, password);
      setToken(tokens.access);
      await this.loadMe();
      return this.currentUser.role;
    },
    async loadMe() {
      const me = await Sangam.me();
      const role = ROLE_MAP[me.role] || 'student';
      this.currentUser = {
        id: me.id, email: me.email, rollNo: me.student_profile?.iitm_roll_number || '',
        name: [me.first_name, me.last_name].filter(Boolean).join(' ') || me.email, role,
      };
      this.isLive = true;
    },
    // Restore a session after a page reload if a token is still stored
    async restore() {
      if (!getToken()) return;
      try { await this.loadMe(); } catch { setToken(null); this.isLive = false; }
    },
    logout() {
      setToken(null);
      this.isLive = false;
      this.switchRole('student');
    }
  }
});

import { defineStore } from 'pinia';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    currentUser: {
      id: 'student-1',
      name: 'Hemant Dhayal',
      email: 'hemant@ds.study.iitm.ac.in',
      rollNo: '21f100001',
      level: 'Degree',
      cgpa: '8.45',
      role: 'student' // 'student' | 'mentor' | 'admin'
    },
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
        this.currentUser.name = 'Hemant Dhayal';
        this.currentUser.email = 'hemant@ds.study.iitm.ac.in';
        this.currentUser.rollNo = '21f100001';
        this.currentUser.id = 'student-1';
        this.currentUser.level = 'Degree';
        this.currentUser.cgpa = '8.45';
      } else if (roleId === 'mentor') {
        this.currentUser.name = 'Arjun Kumar';
        this.currentUser.email = 'arjun.k@alumni.example.org';
        this.currentUser.rollNo = '21f1001234';
        this.currentUser.id = 'mentor-1';
      } else if (roleId === 'admin') {
        this.currentUser.name = 'IIC Admin';
        this.currentUser.email = 'iic.admin@iitm.ac.in';
        this.currentUser.id = 'admin-1';
      }
    },
    login(email, role) {
      // Auto-detect role by email domain/prefix if not explicitly specified
      let detectedRole = role;
      if (email.includes('admin')) {
        detectedRole = 'admin';
      } else if (email.includes('alumni') || email.includes('mentor')) {
        detectedRole = 'mentor';
      } else {
        detectedRole = 'student';
      }
      this.switchRole(detectedRole);
      this.currentUser.email = email;
    },
    logout() {
      this.switchRole('student');
    }
  }
});

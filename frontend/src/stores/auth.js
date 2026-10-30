import { defineStore } from 'pinia';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    currentUser: {
      id: 'student-1',
      name: 'Hemant Dhayal',
      email: 'hemant@study.iitm.ac.in',
      rollNo: '21f100027',
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
    login(email, role) {
      this.switchRole(role || 'student');
      this.currentUser.email = email;
    },
    logout() {
      this.switchRole('student');
    }
  }
});

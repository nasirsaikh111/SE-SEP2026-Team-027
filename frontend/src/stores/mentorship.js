import { defineStore } from 'pinia';
import { initialMentors, initialRequests, initialWorkspace, initialFlags, initialAuditLogs } from '../mock/data';

export const useMentorshipStore = defineStore('mentorship', {
  state: () => ({
    mentors: [...initialMentors],
    requests: [...initialRequests],
    workspace: { ...initialWorkspace },
    flags: [...initialFlags],
    auditLogs: [...initialAuditLogs],
    selectedMentorForRequest: null
  }),
  getters: {
    verifiedMentors: (state) => state.mentors.filter(m => m.verified),
    pendingVerificationMentors: (state) => state.mentors.filter(m => !m.verified),
    myStudentRequests: (state) => state.requests.filter(r => r.studentId === 'student-1'),
    activePendingRequestsCount: (state) => state.requests.filter(r => r.studentId === 'student-1' && r.status === 'PENDING').length,
    incomingMentorRequests: (state) => state.requests.filter(r => r.mentorId === 'mentor-1' && r.status === 'PENDING'),
    activeMentorshipsCount: (state) => state.requests.filter(r => r.status === 'ACCEPTED').length,
    completedGoalsCount: (state) => state.workspace.goals.filter(g => g.completed).length,
    totalGoalsCount: (state) => state.workspace.goals.length
  },
  actions: {
    submitRequest({ mentorId, domain, pathway, urgency, question }) {
      if (this.activePendingRequestsCount >= 3) {
        throw new Error("You already have 3 pending requests. Please withdraw one or wait for a response.");
      }
      if (!question || question.trim().length < 80) {
        throw new Error("Question must be at least 80 characters long to provide clear context to the mentor.");
      }

      const mentor = this.mentors.find(m => m.id === mentorId);
      const newRequest = {
        id: `req-${Date.now()}`,
        studentId: 'student-1',
        studentName: 'Hemant Dhayal',
        studentRoll: '21f100027',
        mentorId: mentorId,
        mentorName: mentor ? mentor.name : 'Selected Mentor',
        domain,
        pathway,
        urgency: urgency || 'Medium',
        question: question.trim(),
        status: 'PENDING',
        submittedAt: new Date().toISOString().split('T')[0],
        declineReason: null,
        expiryDaysLeft: 7
      };

      this.requests.unshift(newRequest);
      this.addAuditLog('student (Hemant)', `Submitted request to ${newRequest.mentorName}`, `Domain: ${domain}`);
      return newRequest;
    },

    withdrawRequest(requestId) {
      const idx = this.requests.findIndex(r => r.id === requestId);
      if (idx !== -1) {
        const req = this.requests[idx];
        this.requests.splice(idx, 1);
        this.addAuditLog('student (Hemant)', `Withdrew request to ${req.mentorName}`);
      }
    },

    acceptRequest(requestId) {
      const req = this.requests.find(r => r.id === requestId);
      if (req) {
        req.status = 'ACCEPTED';
        this.addAuditLog('mentor (Arjun K.)', `Accepted request #${requestId}`, `Mentee: ${req.studentName}`);
      }
    },

    declineRequest(requestId, reason) {
      const req = this.requests.find(r => r.id === requestId);
      if (req) {
        req.status = 'DECLINED';
        req.declineReason = reason || 'At capacity';
        this.addAuditLog('mentor (Arjun K.)', `Declined request #${requestId}`, `Reason: ${req.declineReason}`);
      }
    },

    toggleGoal(goalId) {
      const goal = this.workspace.goals.find(g => g.id === goalId);
      if (goal) {
        goal.completed = !goal.completed;
      }
    },

    addGoal(title, targetDate) {
      const newGoal = {
        id: `g-${Date.now()}`,
        title,
        targetDate: targetDate || '2026-11-20',
        completed: false
      };
      this.workspace.goals.push(newGoal);
      this.addAuditLog('mentor/student', `Added new goal: ${title}`);
    },

    logSession({ date, duration, status }) {
      const newSession = {
        id: `sess-${Date.now()}`,
        date: date || 'Today',
        duration: duration || '45 mins',
        status: status || 'DONE'
      };
      this.workspace.sessions.unshift(newSession);
      this.addAuditLog('mentor (Arjun K.)', `Logged mentoring session`, `Status: ${status}, Duration: ${duration}`);
    },

    submitSessionRating({ rating, helpfulTags, comment }) {
      this.addAuditLog('student (Hemant)', `Submitted session feedback`, `Rating: ${rating}/5 stars`);
    },

    verifyMentor(mentorId) {
      const mentor = this.mentors.find(m => m.id === mentorId);
      if (mentor) {
        mentor.verified = true;
        this.addAuditLog('admin', `Verified mentor ${mentor.name} (#${mentor.id})`, `Roll: ${mentor.rollNo}`);
      }
    },

    rejectMentor(mentorId) {
      const idx = this.mentors.findIndex(m => m.id === mentorId);
      if (idx !== -1) {
        const m = this.mentors[idx];
        this.mentors.splice(idx, 1);
        this.addAuditLog('admin', `Rejected unverified mentor profile ${m.name}`);
      }
    },

    resolveFlag(flagId, action) {
      const flag = this.flags.find(f => f.id === flagId);
      if (flag) {
        flag.status = 'RESOLVED';
        this.addAuditLog('admin', `Resolved flag #${flagId}`, `Action: ${action}`);
      }
    },

    addAuditLog(actor, action, details = '') {
      this.auditLogs.unshift({
        id: `log-${Date.now()}`,
        date: 'Just now',
        actor,
        action,
        details
      });
    }
  }
});

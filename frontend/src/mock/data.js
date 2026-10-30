export const initialMentors = [
  {
    id: "mentor-1",
    name: "Arjun K.",
    role: "Senior Data Scientist",
    company: "Fractal Analytics",
    domain: "Data & ML",
    pathway: "Industry",
    gradYear: 2024,
    rollNo: "21f1001234",
    headline: "Foundation → Analyst → Data Scientist at Fractal",
    expertise: ["Data Science", "Machine Learning", "SQL", "Mock Interviews"],
    rating: 4.8,
    reviewsCount: 11,
    capacity: 3,
    activeMentees: 1,
    verified: true,
    paused: false,
    officeHours: ["Tue 6:30 PM", "Thu 6:30 PM"],
    matchScore: 92,
    matchReason: "Direct match on Data & ML, Industry pathway, and shared IITM coursework"
  },
  {
    id: "mentor-2",
    name: "Neha S.",
    role: "Analytics Lead",
    company: "Swiggy",
    domain: "Analytics",
    pathway: "Industry",
    gradYear: 2023,
    rollNo: "20f1002345",
    headline: "Analytics & Product Strategy | Ex-Mu Sigma",
    expertise: ["Product Analytics", "SQL", "Business Insights", "Tableau"],
    rating: 4.7,
    reviewsCount: 8,
    capacity: 2,
    activeMentees: 2,
    verified: true,
    paused: false,
    officeHours: ["Wed 7:00 PM"],
    matchScore: 86,
    matchReason: "Strong fit for Business & Analytics pathway"
  },
  {
    id: "mentor-3",
    name: "Priya N.",
    role: "Software Development Engineer",
    company: "Amazon",
    domain: "Software",
    pathway: "Industry",
    gradYear: 2024,
    rollNo: "21f1003456",
    headline: "SDE @ Amazon | Distributed Systems & DSA",
    expertise: ["Data Structures", "System Design", "Backend Java", "Interview Prep"],
    rating: 4.9,
    reviewsCount: 14,
    capacity: 3,
    activeMentees: 1,
    verified: true,
    paused: false,
    officeHours: ["Sat 11:00 AM", "Sun 4:00 PM"],
    matchScore: 88,
    matchReason: "Specialist in SDE interviews and resume screening"
  },
  {
    id: "mentor-4",
    name: "Rohan S.",
    role: "MS Student & Researcher",
    company: "TU Munich",
    domain: "Higher Studies",
    pathway: "Higher Studies",
    gradYear: 2024,
    rollNo: "21f1004567",
    headline: "Pursuing Masters in CS in Germany | European Admissions",
    expertise: ["SOP Writing", "GRE/IELTS", "Research Proposals", "Scholarships"],
    rating: 4.6,
    reviewsCount: 5,
    capacity: 3,
    activeMentees: 2,
    verified: true,
    paused: false,
    officeHours: ["Fri 8:00 PM"],
    matchScore: 61,
    matchReason: "Matches your interest in international Masters applications"
  },
  {
    id: "mentor-5",
    name: "Sana D.",
    role: "ML Researcher",
    company: "IISc Bangalore",
    domain: "Data & ML",
    pathway: "Higher Studies",
    gradYear: 2023,
    rollNo: "20f1005678",
    headline: "Computer Vision & LLMs researcher",
    expertise: ["Deep Learning", "PyTorch", "Research Papers"],
    rating: 4.8,
    reviewsCount: 6,
    capacity: 1,
    activeMentees: 1,
    verified: true,
    paused: true,
    officeHours: ["Mon 6:00 PM"],
    matchScore: 64,
    matchReason: "Research track match, but currently at full capacity"
  },
  {
    id: "mentor-6",
    name: "Kavya R.",
    role: "SDE",
    company: "Microsoft",
    domain: "Software",
    pathway: "Industry",
    gradYear: 2025,
    rollNo: "21f1009876",
    headline: "Incoming SDE @ Microsoft | Campus placement guide",
    expertise: ["Software", "Interviews", "DSA", "LeetCode"],
    rating: 5.0,
    reviewsCount: 2,
    capacity: 2,
    activeMentees: 0,
    verified: false,
    paused: false,
    officeHours: ["Sat 5:00 PM"],
    matchScore: 90,
    matchReason: "Recently graduated alumni with fresh placement experience"
  }
];

export const initialRequests = [
  {
    id: "req-101",
    studentId: "student-1",
    studentName: "Hemant Dhayal",
    studentRoll: "21f100027",
    mentorId: "mentor-1",
    mentorName: "Arjun K.",
    domain: "Data & ML",
    pathway: "Industry",
    urgency: "High",
    question: "Should I prioritize taking an entry-level data analyst internship right now, or finish all Diploma ML courses and build 2 full-stack ML capstone projects first?",
    status: "ACCEPTED", // PENDING, UNDER_REVIEW, ACCEPTED, DECLINED, EXPIRED
    submittedAt: "2026-10-22",
    declineReason: null,
    expiryDaysLeft: null
  },
  {
    id: "req-102",
    studentId: "student-1",
    studentName: "Hemant Dhayal",
    studentRoll: "21f100027",
    mentorId: "mentor-3",
    mentorName: "Priya N.",
    domain: "Software",
    pathway: "Industry",
    urgency: "Medium",
    question: "How do big tech firms structure the system design round for freshers, and what project architectures should I highlight in my resume?",
    status: "PENDING",
    submittedAt: "2026-10-25",
    declineReason: null,
    expiryDaysLeft: 5
  },
  {
    id: "req-103",
    studentId: "student-2",
    studentName: "Priya S.",
    studentRoll: "22f1001111",
    mentorId: "mentor-1",
    mentorName: "Arjun K.",
    domain: "Data & ML",
    pathway: "Industry",
    urgency: "High",
    question: "Analyst role now or finish degree? I am confused between accepting a non-tech business analyst offer or preparing for pure data science roles.",
    status: "PENDING",
    submittedAt: "2026-10-26",
    declineReason: null,
    expiryDaysLeft: 4
  },
  {
    id: "req-104",
    studentId: "student-3",
    studentName: "Rahul M.",
    studentRoll: "21f1002222",
    mentorId: "mentor-1",
    mentorName: "Arjun K.",
    domain: "Software",
    pathway: "Industry",
    urgency: "Low",
    question: "Could you please give general guidance on how to become a backend engineer and what technologies are popular in the market?",
    status: "DECLINED",
    submittedAt: "2026-10-18",
    declineReason: "At capacity & request was too broad; please specify concrete target companies.",
    expiryDaysLeft: null
  }
];

export const initialWorkspace = {
  mentorshipId: "pair-1",
  mentorId: "mentor-1",
  mentorName: "Arjun K.",
  studentId: "student-1",
  studentName: "Hemant Dhayal",
  nextSession: {
    date: "Thu, 31 Oct 2026",
    time: "6:30 PM IST",
    link: "https://meet.google.com/sangam-test-session"
  },
  goals: [
    { id: "g-1", title: "Pick target role & analyze Job Descriptions", targetDate: "2026-10-15", completed: true },
    { id: "g-2", title: "Audit existing GitHub portfolio projects", targetDate: "2026-10-22", completed: true },
    { id: "g-3", title: "Conduct company-specific mock technical interview", targetDate: "2026-11-05", completed: false },
    { id: "g-4", title: "Resume screening and final referral prep", targetDate: "2026-11-12", completed: false }
  ],
  sessions: [
    {
      id: "sess-1",
      date: "Thu, 17 Oct 2026",
      duration: "45 mins",
      status: "DONE", // DONE, NO_SHOW, CANCELLED
      notes: "Held initial career alignment call. Agreed on Data Science track."
    },
    {
      id: "sess-2",
      date: "Thu, 24 Oct 2026",
      duration: "60 mins",
      status: "DONE",
      notes: "Reviewed project architecture and SQL query optimization strategies."
    }
  ],
  sharedNotes: "Focus on indexing, query optimization, and explaining project business impact clearly during technical rounds.",
  privateNotes: "Mentee has solid fundamentals in SQL. Needs confidence when answering open-ended system design questions."
};

export const initialFlags = [
  {
    id: "flag-1",
    reporterName: "Meera I.",
    reporterRole: "Student",
    targetName: "Unverified User",
    targetType: "Message #81",
    reason: "Asked for payment outside the platform",
    reportedAt: "2 hours ago",
    context: "User asked: 'I charge ₹1500 for a 30-minute resume review session. GPay me here.'",
    status: "OPEN"
  },
  {
    id: "flag-2",
    reporterName: "Rohan S.",
    reporterRole: "Student",
    targetName: "Profile #12",
    targetType: "Mentor Profile",
    reason: "Fake company listed",
    reportedAt: "Yesterday",
    context: "Claimed to be Director of AI at Google but profile links to an unrelated student account.",
    status: "OPEN"
  }
];

export const initialAuditLogs = [
  { id: "log-1", date: "29 Oct 2026, 11:30 AM", actor: "admin", action: "Mentor #41 (Kavya R.) registered", details: "Status set to PENDING verification" },
  { id: "log-2", date: "28 Oct 2026, 04:15 PM", actor: "arjun.k", action: "Req #101 accepted", details: "Pairing created with student Hemant Dhayal" },
  { id: "log-3", date: "27 Oct 2026, 02:40 PM", actor: "arjun.k", action: "Req #104 declined", details: "Reason: At capacity" },
  { id: "log-4", date: "26 Oct 2026, 12:00 AM", actor: "system", action: "Req #89 auto-expired", details: "7 days elapsed without mentor response" }
];

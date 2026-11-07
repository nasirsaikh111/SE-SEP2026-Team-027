# Sangam: Student Mentoring & Career Support Platform
**IITM BS Degree Program — Software Engineering Course (Sep 2026 Term)**  
**Team 027 · Option 2: Student Mentoring and Career Support Platform**  

---

## 👥 Team Members & Roles

| Member Name | Student ID | Primary Roles in Project |
| :--- | :--- | :--- |
| **Hemant Dhayal** | `23f2001646` | **Team Leader**, Frontend Developer, Tester |
| **Rituparna Bhaumik** | `24f1002607` | Product Manager, Code Reviewer |
| **Debshata Choudhury** | `23f2005432` | Scrum Master, Backend Developer, AI/ML Integration |
| **Payal Agrawal** | `22f3000954` | Tester, Frontend Developer |
| **Nasir** | `24f1002474` | Tester, Backend Developer |

---

## 🌐 Live Production Deployment

- **Live URL:** [https://frontend-orpin-iota-73.vercel.app](https://frontend-orpin-iota-73.vercel.app)
- **Backend API:** Django REST Framework deployed on Render

---

## 🔑 Demo Login Credentials

You can use the convenient **"Quick Login Demo"** buttons on the sign-in page, or enter these credentials:

| Role | Email Address | Password |
| :--- | :--- | :--- |
| **Student (Degree)** | `hemant@ds.study.iitm.ac.in` | `SangamDemo!2026` |
| **Student (Diploma)** | `kiran.verma@ds.study.iitm.ac.in` | `SangamDemo!2026` |
| **Alumni Mentor (Data Science)** | `arjun.k@alumni.example.org` | `SangamDemo!2026` |
| **Alumni Mentor (Software Eng)** | `priya.nair@alumni.example.org` | `SangamDemo!2026` |
| **IIC Placement Admin** | `iic.admin@iitm.ac.in` | `SangamDemo!2026` |

---

## 🚀 Installation & Run Instructions

### Prerequisites
Make sure you have Node.js and npm installed:
- **Node.js**: `v18.0.0` or higher (Recommended: Node 20 LTS or Node 22+)
- **npm**: `v9.0.0` or higher

Check your installed versions:
```bash
node -v
npm -v
```

### 1. Extract the ZIP & Navigate to Directory
```bash
cd frontend
```

### 2. Install Dependencies
Install all required packages from `package.json`:
```bash
npm install
```

### 3. Run Development Server
Start the local Vite development server:
```bash
npm run dev
```

After running the command, open your browser and navigate to:
👉 **[http://localhost:5173](http://localhost:5173)**

---

## 📦 Production Build & Preview

To compile and minify the frontend for production:
```bash
npm run build
```
This generates the optimized static bundle in the `dist/` directory.

To locally preview the production build:
```bash
npm run preview
```
Default preview port: **`http://localhost:4173`**

---

## 🎨 Dual Theme Switcher (White & Royal Blue vs. IITM Teal)

Sangam includes a built-in theme toggle located in the navigation bar (`AppNavbar.vue`):
- 🔵 **White & Royal Blue Theme:** Modern, crisp corporate theme utilizing Tailwind `sangam` palette (50–900).
- 🌲 **IITM Teal & Slate Theme:** Official IIT Madras brand aesthetic.
- The user's preference is automatically saved to `localStorage` and persists across sessions and page refreshes.

---

## 🧭 Persona Testing Guide

Use the **"View as" role switcher** in the top navigation bar or log in with the test accounts to explore each stakeholder's perspective:

### 1. Student (Mentee) Persona
- **Dashboard (`/student/dashboard`)**:
  - View current active mentorship card (e.g. Hemant + Arjun Kumar).
  - Track shared goals progress (e.g., 2/4 completed).
  - View upcoming scheduled Google Meet sessions.
  - Interactive **Pathway Compass** with structured need capture.
- **Mentor Discovery (`/student/discover`)**:
  - Search and filter 8+ verified alumni by domain (Data & ML, SDE, Product), career path, and company.
  - View match compatibility score and profile details.
  - Submit request (enforcing a maximum of 3 active requests and 80+ character question validation).
- **My Requests (`/student/requests`)**:
  - Track lifecycle status: `SUBMITTED`, `UNDER_REVIEW`, `WAITING`, `MATCHED`.
- **Mentorship Workspace (`/student/workspace`)**:
  - Check off shared goals in real-time.
  - Log session feedback and 5-star ratings.
  - Record tangible career outcomes (job offer, interview cleared, MS admission).

### 2. Alumni Mentor Persona
- **Mentor Dashboard (`/mentor/dashboard`)**:
  - Review incoming student requests with background and problem statements.
  - Accept or decline with mandatory reason selection.
  - Toggle volunteer availability and cap intake (1–3 mentees/term).
- **Mentee Workspace (`/mentor/workspace`)**:
  - Access active mentee roster.
  - Shared notes (visible to student) vs. Private notes (locked to mentor).
  - Log completed session hours without storing private conversational text (preserving privacy).

### 3. IIC Placement Admin Persona
- **Admin Dashboard (`/admin/insights`)**:
  - Key platform KPIs: active mentorships, verification backlog, and request funnel metrics.
  - Export program telemetry report as CSV.
- **Student Approval Queue (`/admin/student-approvals`)**:
  - Review degree/diploma students, roll numbers, and CGPA before approving for matching.
- **Mentor Repository (`/admin/mentor-repository`)**:
  - Verify alumni roll numbers and approve profiles for Discover Mentors.
- **Safety & Audit Logs (`/admin/audit`)**:
  - Complete immutable audit trail of matches, approvals, and status changes.
- **Assistant Knowledge Base (`/admin/knowledge`)**:
  - View published matching policies and pathway guides.

---

## 📁 Project Directory Structure

```text
frontend/
├── index.html              # HTML entrypoint
├── package.json            # Dependencies and scripts (Vue 3, Pinia, Tailwind)
├── vite.config.js          # Vite configuration
├── tailwind.config.js      # Custom theme colors (sangam 50–900 palette)
├── postcss.config.js       # PostCSS plugins
├── public/                 # Static assets and icons
│   ├── favicon.svg
│   └── icons.svg
└── src/
    ├── main.js             # Vue application initialization
    ├── App.vue             # Root component with theme wrapper
    ├── style.css           # Global Tailwind directives & theme variables
    ├── router/             # Vue Router route definitions
    │   └── index.js
    ├── stores/             # Pinia state stores
    │   ├── auth.js         # Authentication & role management
    │   ├── mentoring.js    # Requests, matches, and workspace state
    │   ├── admin.js        # Admin queues, verifications, and audit logs
    │   └── theme.js        # Dynamic theme switcher state
    ├── mock/               # Complete realistic demo dataset
    │   └── data.js         # 8 Mentors, 6 Students, Sessions, Goals, Articles
    ├── components/         # Reusable UI components
    │   ├── common/         # AppNavbar, ThemeToggle, NotificationBell
    │   ├── student/        # ActiveMentorshipCard, PathwayCompass
    │   ├── mentor/         # MenteeList, RequestCard
    │   └── admin/          # FunnelChart, MetricCard
    └── views/              # View pages by role
        ├── auth/           # LoginView, RegisterView
        ├── student/        # StudentDashboard, DiscoverView, WorkspaceView
        ├── mentor/         # MentorDashboard, MentorWorkspaceView
        └── admin/          # AdminInsightsView, ApprovalsView, AuditView
```

---

## 🛠️ Tech Stack

- **Framework**: [Vue 3](https://vuejs.org/) (Composition API `<script setup>`)
- **State Management**: [Pinia](https://pinia.vuejs.org/)
- **Build Tool**: [Vite](https://vitejs.dev/)
- **Styling**: [Tailwind CSS v3](https://tailwindcss.com/)
- **Routing**: [Vue Router 4](https://router.vuejs.org/)
- **Icons**: [Lucide Vue Next](https://lucide.dev/)
- **Target Deployment**: Vercel

# Sangam: Student Mentoring & Career Support Platform
**IITM BS Degree Program — Software Engineering Course (Sep 2026 Term)**  
**Team 027** · Option 2: Student Mentoring and Career Support Platform  
**Frontend Lead:** Hemant

---

## 📌 Milestone 2 Deliverable Overview

This repository contains the complete frontend prototype for **Sangam**, implementing all wireframes and user stories from the Milestone 1 requirements specification:
- **Zero conversation logging** to preserve mentor-mentee conversational privacy.
- **Role-based navigation** supporting all three stakeholders: **Students (Mentees)**, **Alumni Mentors**, and **IIC Administrators**.
- **Interactive mock stores (Pinia)** providing full state persistence across page redirects (submitting requests, accepting/declining requests, logging session hours, marking shared goals, verifying alumni roll numbers, and audit trail).

---

## 🚀 Quick Start Guide

### Prerequisites
- **Node.js**: v18.0.0 or higher (Tested on Node v20/v24)
- **npm**: v9.0.0 or higher

### Installation & Run

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Launch the development server:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:5173](http://localhost:5173) in your web browser.

---

## 🧭 How to Test & Evaluate (For Peer Reviewers)

Use the **"View as" role switcher** in the top navigation bar to test each user persona seamlessly:

### 1. Student (Mentee) Persona
- **Dashboard (`/student/dashboard`)**: View active mentorship progress (Arjun K., 2/4 goals completed), upcoming call schedule, and the **Pathway Compass**.
- **Record a Need**: In Pathway Compass, try entering a question. A minimum of 80 characters is enforced to avoid vague requests (Story 1.1).
- **Discover Mentors (`/student/discover`)**: Filter verified alumni by domain (Data & ML, Software, Analytics), pathway, and open slot availability.
- **Submit Request**: Click "Send Request" on any open mentor card. Notice the 3-request limit and 7-day auto-expiry warning.
- **My Requests (`/student/requests`)**: Track status pills (`ACCEPTED`, `PENDING`, `DECLINED`), withdrawal actions, and countdowns.
- **Mentorship Workspace (`/student/workspace`)**:
  - Toggle shared goal checkboxes (updates progress in real-time).
  - Add a new milestone goal.
  - Review logged sessions and click **"Rate Session"** (1–5 stars + helpful tags modal).
  - Record tangible career outcomes (e.g., cleared interview round) per Story 5.2.

### 2. Mentor (Alumni) Persona
- **Mentor Dashboard (`/mentor/dashboard`)**:
  - Toggle **"Pause Requests"** to cap incoming requests.
  - Review incoming student requests with stated questions.
  - Test the **"Accept"** button or click **"Decline..."** (prompts mandatory reason dropdown).
- **Mentee Workspace (`/mentor/workspace`)**:
  - View mentee roster (includes the **"Nudge"** button for mentees inactive > 21 days).
  - Dual notes system: Shared notes (visible to mentee) vs. Private notes (locked to mentor).
  - Click **"Log Mentoring Session"**: logs date, duration, and status without conversation discussion fields (ensuring privacy).
- **Profile Setup (`/mentor/profile`)**: Adjust volunteer capacity (1–3 mentees/term) and manage office hours slots.

### 3. IIC Placement Admin Persona
- **Program Insights (`/admin/insights`)**: Aggregated metrics, 4-stage funnel (Sent → Accepted → Session → Done), domain demand distribution, and one-click **"Export Program CSV"** (Story 5.4).
- **Verification Queue (`/admin/verify`)**: Cross-checks alumni roll numbers and graduation years against the institute records. Test **"Verify & Publish"** to immediately make the alumni profile discoverable to students.
- **Safety & Flags (`/admin/flags`)**: Review reported message incidents and test the "Warn & Resolve" or "Suspend User" workflows.
- **Audit Log (`/admin/audit`)**: Inspect the immutable chronological trail of state changes and filter by actor.

---

## 🛠️ Tech Stack & Architecture

- **Framework**: Vue 3 (Composition API `<script setup>`)
- **Build Tool**: Vite
- **Styling**: Tailwind CSS (Utility-first styling matching wireframe boxes and flows)
- **Routing**: Vue Router 4 (HTML5 history mode)
- **State Management**: Pinia (Reactive mock store ready for Firebase Auth and Firestore integration in Milestones 3 & 4)
- **Icons**: Lucide Icons

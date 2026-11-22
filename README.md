# SE-SEP2026-Team-027 · Sangam Platform

**Option 2: Student Mentoring and Career Support Platform**  
**IITM BS Degree Program — Software Engineering Course (Sep 2026 Term)**

## Demo Branch: `finaldemo`

This branch contains the fully aligned, complete setup connecting the React 19 Frontend with the Django REST Backend (SQLite + Ollama local AI integration).

### Quick Start: 1-Click Local Run

You can launch all services (Ollama, Django REST API, and Vite React Frontend) with a single command:

```bash
chmod +x run_local.sh
./run_local.sh
```

- **Frontend App:** [http://127.0.0.1:5173](http://127.0.0.1:5173)
- **Django REST API:** [http://127.0.0.1:8000/api/v1/](http://127.0.0.1:8000/api/v1/)
- **Swagger / OpenAPI Docs:** [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)

---

### Demo Accounts & 1-Click Sign-In

The login page at [http://127.0.0.1:5173/login](http://127.0.0.1:5173/login) includes **Demo Quick Access** buttons for instant 1-click sign-in:

| Role | Pre-seeded Email | Password | Primary Workflow Tested |
|---|---|---|---|
| **Student (Hemant)** | `hemant@ds.study.iitm.ac.in` | `SangamDemo!2026` | Discover Mentors, Submit & Track Requests, Meetings & Goals, Ask Sangam AI |
| **IIC Staff (Admin)** | `iic.admin@iitm.ac.in` | `SangamDemo!2026` | Student Approvals, Mentor Verification, Review Queue, Semantic Matching, Reports & Audit Log |
| **Alumni Mentor (Arjun)** | `arjun.k@alumni.example.org` | `SangamDemo!2026` | Respond to Availability Checks, Mentee Workspace, Google Calendar & Meetings, Feedback |

---

### Building the Project

#### Build Frontend
```bash
cd frontend
npm install
npm run build
```
This runs TypeScript checking (`tsc -b`) and bundles production assets into `dist/`.

#### Backend Verification
```bash
cd backend
source .venv/bin/activate
python manage.py check
python manage.py test apps.accounts apps.mentoring
```

---

### Live Deployment Links (Vercel)

- **Production Frontend:** [https://frontend-orpin-iota-73.vercel.app](https://frontend-orpin-iota-73.vercel.app)
- **Production Backend API:** [https://team-027-backend.vercel.app/api/v1/](https://team-027-backend.vercel.app/api/v1/)
- **API Documentation (Swagger):** [https://team-027-backend.vercel.app/api/v1/docs/](https://team-027-backend.vercel.app/api/v1/docs/)

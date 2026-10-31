# SE-SEP2026-Team-027 · Sangam

**Student Mentoring and Career Support Platform**, IITM BS Degree Programme, Software Engineering (Sep 2026 term).

Students request mentoring; IIC administrators approve students, verify alumni mentors, confirm mentor availability
and approve every pairing; mentors and students then track meetings, goals, written feedback and outcomes.

| Part | Stack | Location |
|---|---|---|
| Backend (only business backend) | Django 6.1, Django REST Framework, SimpleJWT, PostgreSQL (Supabase) / SQLite | [`backend/`](./backend) |
| Frontend | React 19, Vite, TypeScript, Tailwind CSS 4, DaisyUI 5, TanStack Query, Recharts, Lucide | [`frontend/`](./frontend) |
| Documentation | Gap analysis, API reference, integration contract, RBAC matrix, deployment, change summary | [`docs/`](./docs), also served at `/project-report/` |

## Quick start
```bash
# backend
cd backend && python -m venv .venv && .venv/Scripts/activate && pip install -r requirements.txt
cp .env.example .env            # set DJANGO_DEBUG=true and DJANGO_SECRET_KEY
python manage.py migrate && python manage.py seed_sangam_demo && python manage.py runserver

# frontend (new terminal)
cd frontend && npm install && cp .env.example .env && npm run dev
```
Open http://localhost:5173. Demo accounts printed by `seed_sangam_demo` share the password `SangamDemo!2026`.
API docs: http://127.0.0.1:8000/api/docs/. Project report: http://127.0.0.1:8000/project-report/.

Tests: `cd backend && python manage.py test`. Build: `cd frontend && npm run build`.

The earlier Vue 3 prototype is preserved at Git tag `vue-prototype-m2`.

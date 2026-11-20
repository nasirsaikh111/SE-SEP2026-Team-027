# 5. Migration and deployment

## 5.1 Before anything else: rotate credentials
The Supabase password and Django `SECRET_KEY` were committed in `backend/config/settings.py` (removed in this change,
but still in Git history). Before deploying:
1. Reset the database password in Supabase (Project settings → Database).
2. Generate a new secret key: `python -c "import secrets; print(secrets.token_urlsafe(50))"`.
3. Put both in `backend/.env` (local) or the hosting platform's environment, never in code.

## 5.2 Local development
```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/activate            # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env              # set DJANGO_DEBUG=true and DJANGO_SECRET_KEY; leave DATABASE_URL unset for SQLite
python manage.py migrate
python manage.py seed_sangam_demo # optional, DEBUG only: demo IIC/mentor/student accounts
python manage.py runserver

# Frontend (second terminal)
cd frontend
npm install
cp .env.example .env              # VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
npm run dev                       # http://localhost:5173
```
Your existing `backend/.env` only has `DATABASE_URL`. Add `DJANGO_DEBUG=true` and `DJANGO_SECRET_KEY=...` for local use.
If Django reports that `DATABASE_URL` is not a valid URL, remove any `[brackets]` around the password, or switch to the
`POSTGRES_*` variables shown in `.env.example`.

## 5.3 Migrating the shared Supabase database (additive)
New migrations: `accounts.0002_mentor_professional_details`, `mentoring.0002_scheduling_history_calendar`,
`mentoring.0003_backfill_status_history` (data only, idempotent) and `assistant_ai.0002_airequestassessment`.
They only add columns, tables and choices. No column is dropped, renamed or narrowed.
```bash
cd backend
python manage.py showmigrations accounts mentoring assistant_ai   # confirm 0001 is applied everywhere
python manage.py migrate --plan                                   # review
pg_dump "$DATABASE_URL" > sangam_backup_$(date +%F).sql           # backup (or a Supabase backup)
python manage.py migrate
python manage.py check --deploy
```
Existing verified mentors start with `is_discoverable=false`, so nobody is published to the directory without an IIC
decision. Publish them from **Mentor Repository** (Publish), or in bulk:
`python manage.py shell -c "from apps.accounts.models import MentorProfile as M; M.objects.filter(is_verified=True).update(is_discoverable=True)"`.

## 5.4 Production backend
Required environment: `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL` (or `POSTGRES_*`),
`SANGAM_FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, email settings. Leave `DJANGO_DEBUG` unset.
```bash
pip install -r requirements.txt gunicorn
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 3
```
Schedule the daily job, which expires 7-day checks, raises inactivity and feedback alerts, and refreshes priorities:
```bash
python manage.py check_sangam_alerts      # e.g. cron: 0 2 * * *
```
In production the API schema and Swagger UI require a staff session (`/admin/` login).

## 5.5 Google Calendar (optional)
1. In Google Cloud, enable the **Google Calendar API** and create an OAuth client of type *Web application*.
2. Add the authorised redirect URI `https://<backend-host>/api/v1/calendar/oauth/callback/`.
3. Set `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI`, and ideally a dedicated
   `SANGAM_TOKEN_ENCRYPTION_KEY` (Fernet key). If this key changes, mentors must reconnect.
4. The scopes requested are `openid email https://www.googleapis.com/auth/calendar.events` (events only; other events are never read).
5. While the app is in Google "testing" mode, add mentor accounts as test users.

Without these variables, scheduling still works inside Sangam and the UI reports that the calendar is not configured.

## 5.6 Frontend (Vercel)
- Root directory `frontend`, build `npm run build`, output `dist`.
- Environment: `VITE_API_BASE_URL=https://team-027-pre-prod.vercel.app/api/v1` (also the built-in default in `src/lib/api.ts`).
- `frontend/vercel.json` rewrites all paths to `index.html` for client-side routing.

## 5.6a Backend on Vercel (team-027-pre-prod.vercel.app)
Set these in the backend project's Environment Variables, then redeploy:

| Variable | Value |
|---|---|
| `SANGAM_FRONTEND_URL` | The React frontend URL, e.g. `https://<frontend>.vercel.app` (used in mentor invitation links) |
| `CORS_ALLOWED_ORIGINS` | `https://<frontend>.vercel.app,http://localhost:5173` |
| `CORS_ALLOWED_ORIGIN_REGEXES` | Optional, for preview URLs, e.g. `^https://<frontend>(-[a-z0-9-]+)?\.vercel\.app$` |
| `CSRF_TRUSTED_ORIGINS` | `https://<frontend>.vercel.app` |
| `CRON_SECRET` | A long random string (`python -c "import secrets;print(secrets.token_urlsafe(32))"`) |

Vercel has no long-running server, so `check_sangam_alerts` cannot run from system cron. `backend/vercel.json` schedules
`GET /api/v1/cron/daily/` at 20:30 UTC (02:00 IST); Vercel sends `Authorization: Bearer $CRON_SECRET` automatically.
The job is idempotent. IIC can also run it any time from **Monitoring & alerts → Run checks now**
(`POST /api/v1/admin/daily-checks/`), and the mentor availability inbox expires overdue 7-day checks on every load.
This assumes the Vercel project's Root Directory is `backend`; otherwise move the `crons` entry to the root `vercel.json`.

## 5.7 Verification commands
```bash
cd backend && python manage.py test                     # 43 tests
python manage.py spectacular --validate --file schema.yml
cd ../frontend && npm run build                         # type-check + production build
```

## 5.8 Restoring the Vue prototype
The Vue 3 prototype is preserved at tag `vue-prototype-m2` (commit `f4bd4bf`):
`git checkout vue-prototype-m2 -- frontend` (or `git worktree add ../sangam-vue vue-prototype-m2`).
The tag is local until you push it: `git push origin vue-prototype-m2`.

# 3. Frontend–backend integration contract

## 3.1 Principles
1. **Django is the only business backend.** The React app calls `/api/v1/` through a single Axios client
   (`frontend/src/lib/api.ts`). It does not access Supabase or any database directly, and holds no mock stores.
2. **The backend is the security boundary.** React route guards (`RequireRole`) and the role-based sidebar are UX only;
   every endpoint applies its own permission and object-ownership checks.
3. **Role comes from `GET /auth/me/` → `effective_role`.** There is no role switcher and no client-side role selection.
4. **Server state lives in TanStack Query** (`frontend/src/lib/queries.ts`). Every mutation invalidates the affected
   query keys (`requests`, `dashboard`, `availability`, `mentorships`, `meetings`, `notifications`, …).

## 3.2 Authentication flow
| Step | Call | Frontend behaviour |
|---|---|---|
| Sign in | `POST /auth/token/` `{email, password}` | Store `access` and `refresh`, then fetch `/auth/me/` |
| Every request | `Authorization: Bearer <access>` | Added by the request interceptor |
| 401 response | `POST /auth/token/refresh/` `{refresh}` | Single-flight refresh, then the original request is retried once |
| Refresh fails | — | Tokens cleared; `sangam:session-expired` event; user returned to `/login` |
| Sign out | — | Tokens and query cache cleared |

Tokens are kept in `localStorage`, guarded by try/catch. Access tokens last 30 minutes and refresh tokens 1 day
(`JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS`). Moving to httpOnly cookies would require a cookie-based SimpleJWT setup and CSRF handling.

## 3.3 Environment
| Variable | Where | Example |
|---|---|---|
| `VITE_API_BASE_URL` | `frontend/.env` / Vercel | `https://api.example.org/api/v1` |
| `SANGAM_FRONTEND_URL` | backend | `https://sangam-step2.vercel.app` (activation links, OAuth redirect target) |
| `CORS_ALLOWED_ORIGINS` | backend | must include the frontend origin |

## 3.4 Errors, loading and pagination
- `errorMessage(err)` shows `detail`; `fieldErrors(err)` maps field errors to form inputs.
- 400/401/403/404 are not retried; other failures retry twice.
- Every screen renders explicit loading (`Loading`), error (`ErrorAlert`) and empty (`EmptyState`) states.
- List hooks always send `page_size`, so they receive the paginated envelope.

## 3.5 Request status mapping
The UI never invents a status. It shows the backend-derived `stage`:

| `stage` | Derived from | Label shown |
|---|---|---|
| SUBMITTED | `status=SUBMITTED`, no live check | Submitted |
| UNDER_REVIEW | `status=UNDER_REVIEW`, no live check | Under review |
| WAITING | `status=WAITING` (after a decline or expiry, or set by IIC) | Waiting |
| AVAILABILITY_CHECK_SENT | open request with an unexpired PENDING check | Availability check sent |
| AWAITING_IIC_APPROVAL | open request with an unexpired CONFIRMED check | Awaiting IIC approval |
| ACTIVE | `status=MATCHED` and the mentorship is ACTIVE | Active |
| MATCHED | `status=MATCHED`, mentorship no longer active | Matched |
| WITHDRAWN / CLOSED | persisted status | Withdrawn / Closed |

`MENTOR_CONFIRMED` appears as a timeline event. The resulting stage is `AWAITING_IIC_APPROVAL`, because the mentor's
confirmation and the wait for IIC are the same backend state.

## 3.6 Screen ↔ endpoint map
| Screen (route) | Role | Reads | Writes |
|---|---|---|---|
| Sign in `/login`, Register `/register`, Activate `/mentor/activate` | Public | — | `auth/token`, `auth/register`, `auth/mentor/activate` |
| Dashboard `/dashboard` | All | `dashboard/` | mentor availability toggle |
| Discover Mentors `/discover` | Student | `mentors/`, `mentors/facets/`, `requests/` | `POST requests/` (with `preferred_mentor`) |
| My Requests `/requests`, `/requests/:id` | Student | `requests/`, `requests/{id}/` | `requests/{id}/withdraw/`, `POST requests/` |
| My Mentorship `/mentorship` | Student | `mentorships/`, `mentorships/{id}/`, `…/feedback/` | `…/feedback/` |
| Meetings & Goals `/meetings-goals` | Student | `…/goals/`, `…/meetings/`, `…/outcomes/` | goals, goal complete, meetings log/record, outcomes |
| Availability Requests `/mentor/availability` | Mentor | `availability/` | `availability/{id}/respond/` |
| Mentorship Workspace `/mentor/workspace` | Mentor | `mentorships/?status=ACTIVE`, `mentorships/{id}/`, meetings, goals, feedback, outcomes, `dashboard/` | schedule/reschedule/cancel/record/confirm meetings, goals, feedback, availability |
| Calendar & Meetings `/mentor/calendar` | Mentor | `calendar/status/`, `meetings/` | `calendar/connect|disconnect/`, meeting scheduling |
| Feedback & Progress `/mentor/feedback` | Mentor | feedback, goals, outcomes, `dashboard/` | `…/feedback/` (PROGRESS) |
| Student Approvals `/admin/students` | IIC | `admin/students/` | `admin/students/{id}/review/` |
| Mentor Repository `/admin/mentors` | IIC | `admin/mentors/` | create, `PATCH admin/mentors/{id}/`, verify, invite |
| Mentorship Requests `/admin/requests`, `/admin/requests/:id` | IIC | `requests/`, `requests/{id}/`, suggestions | availability check, transition, assess, priority override |
| Matching & Approvals `/admin/matching` | IIC | `availability/?status=` | `admin/availability/{id}/approve/` |
| Active Mentorships `/admin/mentorships` | IIC | `mentorships/`, `mentorships/{id}/`, feedback | close, reassign |
| Monitoring & Alerts `/admin/monitoring` | IIC | `admin/alerts/` | `admin/alerts/{id}/resolve/` |
| Reports & Analytics `/admin/reports` | IIC | `admin/insights/` | `admin/export/?type=` (download) |
| Audit Log `/admin/audit` | IIC | `admin/audit/` | — |
| AI Knowledge Management `/admin/knowledge` | IIC | `admin/knowledge/` | CRUD |
| AI Assistant `/assistant` | All | — | `ai/chat/` (not stored) |
| Notifications `/notifications` + bell | All | `notifications/` | read, read-all |
| My Profile `/profile` | All | `auth/me/`, `students/me/` or `mentor/profile/` | the same endpoints (PATCH) |

## 3.7 Privacy rules the UI relies on
- Before IIC approval a mentor sees only the redacted need: no student name, email or roll number.
- Students never see a mentor's email before approval; the directory has no contact fields.
- Feedback lists return only the caller's own entries (IIC sees all). Text is written; there are no ratings.
- Meeting records hold date, time, duration, format and calendar links, never discussion notes.
- Chat messages are not stored (`message_stored: false`).

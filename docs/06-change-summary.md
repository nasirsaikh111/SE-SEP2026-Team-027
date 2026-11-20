# 6. Change summary and deviations from Milestone 2

Branch `feature/react-rbac-integration` (from `main` @ `f4bd4bf`). Uncommitted at the time of writing.

## 6.1 Deviations requiring stakeholder approval

> **Discover Mentors and mentor preference are a change from the Milestone 2 rule** ("students cannot choose a mentor;
> IIC matches"). This iteration adds a curated directory and an optional *preferred mentor* on a request.
> Safeguards keep the original intent: only IIC-verified profiles that IIC has explicitly published are listed;
> no contact details are shown; a preference creates no availability check or mentorship; IIC suggestions flag the
> preference but do not score it higher; IIC still confirms availability and gives final approval.
> **The IIC stakeholder should sign off on this change before release.** To withdraw the feature, unpublish every mentor
> (Mentor Repository) and remove the Discover item from `frontend/src/layout/nav.ts`. The API and data model need no change.

Other changes that extend Milestone 2 and should be noted to stakeholders:

| Change | Why | Safeguard |
|---|---|---|
| Advisory AI priority on requests (replaces student-selected urgency) | Brief §6 | Uses only stated deadlines, waiting time and workflow state; IIC override with reason; never changes status; hidden from students |
| Google Calendar integration and scheduled meetings (`SCHEDULED` status, start/end/time zone/format) | Brief §9 | Events contain no discussion content; tokens encrypted; mentor opts in |
| Mentor reassignment and closure types | Brief §3/§7 | IIC-only, audited, the reason is required |
| Mentor LinkedIn, skills, summary in the directory | Brief §5 | LinkedIn must be an https linkedin.com URL; email and phone are never exposed |

## 6.2 Prototype features intentionally not carried over from Vue
"View as" role switcher, global footer, star ratings and "rate session", mentor private notes and shared free-text notes,
3 concurrent requests per student, student-selected urgency, the separate welcome page, mock match scores and reviews,
"flags and suspension" (no backend model; out of Milestone 2 scope). Each either conflicted with Milestone 2's privacy
rules (no ratings, no conversation content, one open request) or with this brief.

## 6.3 Files changed

### Backend (Django)
| File | Change |
|---|---|
| `config/settings.py` | Environment-based secrets, database, CORS, email, JWT lifetimes, throttles, error handler, pagination, OpenAPI tags and enums, Google OAuth and test settings |
| `config/urls.py`, `config/report.py`, `templates/sangam/project_report.html` | Working `/project-report/` (docs plus live endpoint index) |
| `apps/__init__.py` | Makes `apps` a package so `manage.py test` discovers tests |
| `apps/accounts/models.py` + `migrations/0002_mentor_professional_details.py` | Mentor `bio`, `skills`, `linkedin_url`, `is_discoverable`, `verified_by`, `verified_at` |
| `apps/accounts/serializers.py` | `MeSerializer` (`effective_role`, `is_iic`, mentor profile, calendar), directory, mentor self/admin update serializers |
| `apps/accounts/views_api.py`, `urls.py` | Throttled auth; directory, facets, mentor profile, admin mentor PATCH; filters and pagination on admin lists |
| `apps/accounts/permissions.py` | `IsMentor`, `IsApprovedStudentOrIIC`, `approved_student()` |
| `apps/accounts/exceptions.py`, `pagination.py` | Standard error body; opt-in pagination helper |
| `apps/accounts/admin.py` | Mentor professional fields, verification audit fields |
| `apps/mentoring/models.py` + `migrations/0002_scheduling_history_calendar.py`, `0003_backfill_status_history.py` | `preferred_mentor`, closure fields, meeting scheduling fields, `ActivityStatusHistory`, `GoogleCalendarConnection`, `MeetingCalendarEvent` |
| `apps/mentoring/workflow.py` | Derived request stages and next actions |
| `apps/mentoring/services.py` | History on every transition, request creation/withdrawal/transition, reassignment, closure types, expiry fix, alert resolution |
| `apps/mentoring/serializers.py` | Stage, timeline, priority, redacted availability summaries, pair progress, scheduling serializers |
| `apps/mentoring/views_api.py`, `urls.py` | Request detail, transitions, priority, mentorship detail and timeline, reassign, my meetings, read-all, alert resolve, export types, OpenAPI annotations |
| `apps/mentoring/views_calendar.py`, `google_calendar.py` | OAuth connect/callback/disconnect, schedule/reschedule/cancel/record with Google Calendar sync |
| `apps/mentoring/views_dashboard.py` | Role dashboards with linked tasks |
| `apps/mentoring/admin.py` | Admin for new models; requests read-only outside the workflow; tokens hidden |
| `apps/mentoring/management/commands/check_sangam_alerts.py` | Uses the shared expiry service; refreshes priorities |
| `apps/mentoring/management/commands/seed_sangam_demo.py` | Demo data for local development (refuses when DEBUG is off) |
| `apps/assistant_ai/models.py` + `migrations/0002_airequestassessment.py` | `AIRequestAssessment` |
| `apps/assistant_ai/services.py` | Priority rules; suggestions use skills and pathway and flag preference |
| `apps/assistant_ai/views.py`, `urls.py`, `admin.py` | Knowledge management ViewSet; schema annotations |
| `apps/accounts/tests.py`, `apps/mentoring/test_workflow.py`, `test_calendar.py`, `factories.py` | 38 new tests (43 total) |
| `requirements.txt`, `.env.example` | Pinned dependencies; documented configuration |

### Frontend (React, replaces Vue)
| Path | Purpose |
|---|---|
| `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, `vercel.json`, `.env.example`, `public/favicon.svg` | React 19, Vite 8, TypeScript, Tailwind 4, DaisyUI 5; SPA rewrites |
| `src/index.css` | Light and dark DaisyUI themes; chart colour tokens for each theme |
| `src/lib/api.ts`, `queries.ts`, `types.ts`, `format.ts` | Axios client with JWT refresh; TanStack Query hooks; typed API models; labels |
| `src/auth/AuthContext.tsx` | Session, `/auth/me/` role, route guards |
| `src/layout/AppShell.tsx`, `nav.ts` | Top bar, collapsible role sidebar, mobile drawer, theme toggle, notification bell |
| `src/components/ui.tsx`, `workspace.tsx`, `charts.tsx` | Shared DaisyUI primitives; goals, meetings, scheduling, feedback and outcome panels; Recharts charts |
| `src/pages/**` | All screens listed in the integration contract |
| Removed | `src/**/*.vue`, Pinia stores, `mock/data.js`, `router/`, Vue/Vite scaffold assets, `tailwind.config.js`, `postcss.config.js` |

### Documentation
`docs/01`–`06` (rendered at `/project-report/`), root `README.md`, `frontend/README.md`.

## 6.4 Verification performed
- `python manage.py test`: 43 tests pass (SQLite).
- `python manage.py spectacular --validate`: 74 operations, 0 errors, 0 warnings.
- `python manage.py makemigrations --check`: no missing migrations; all migrations applied to a fresh SQLite database.
- `npm run build`: type-check and production build pass.
- Browser checks (headless Chrome against the running stack and seeded data): every screen for each role at desktop,
  mobile (390 px) and in dark mode, with no console errors, no failed API calls and no horizontal overflow; a full workflow
  through the UI (approval → request with preference → availability check → mentor confirmation → IIC approval →
  scheduling → goals → progress feedback → withdrawal → audit and reports).
- **Not verified:** migrations against the live Supabase database (not accessed), and real Google OAuth (requires
  client credentials; covered by tests with the Google API mocked).

## 6.5 Frontend redesign (second pass)
The first React UI was replaced with a distinct visual identity built around the meaning of *Sangam* (confluence):
- **Palette and type:** ink river blue, jade for actions, marigold for "needs your action"; Bricolage Grotesque display with Figtree body.
- **Confluence ribbon** (`components/Confluence.tsx`): the request workflow drawn as the student's and mentor's streams meeting at IIC approval. It is driven by the backend `stage` and used on the student dashboard, request details, the IIC review sheet and sign-in.
- **Modal-first interaction:** details open as right-hand sheets (request, mentor profile, IIC request review, mentor record, mentorship management, notifications, assistant), and actions open as centred modals (request form, approvals, scheduling, goals, feedback, outcomes, priority changes, closures, profile edits). `/requests/:id` and `/admin/requests/:id` deep-link to the list with the sheet open.
- Data layer unchanged: same API client, queries and routes.

# 2. REST API reference

Base URL `/api/v1/`. Interactive documentation: `/api/docs/` (Swagger UI), `/api/redoc/`; schema at `/api/schema/`
(public when `DJANGO_DEBUG=true`, staff session otherwise). Every operation below appears in the schema with its
request and response shapes. **New** marks endpoints added in this iteration; **Extended** marks existing endpoints
that gained fields or filters without breaking their earlier contract.

Roles: **Public** (no token) · **Any** (any signed-in user) · **Student** (IIC-approved student unless stated) ·
**Mentor** · **IIC** (`role=ADMIN` + `is_staff`, or superuser). Ownership checks are listed in the RBAC matrix.

## 2.1 Endpoint index

| Method | Path | Role | Status | Frontend screen |
|---|---|---|---|---|
| POST | `/auth/token/` | Public | throttled | Sign in |
| POST | `/auth/token/refresh/` | Public | throttled | API client (automatic) |
| POST | `/auth/register/` | Public | throttled | Student registration |
| POST | `/auth/mentor/activate/` | Public | throttled | Mentor activation |
| GET, PATCH | `/auth/me/` | Any | Extended | App shell, My Profile |
| GET, PATCH | `/students/me/` | Student (any approval state) | — | My Profile |
| GET | `/dashboard/` | Any | **New** | Dashboard (all roles) |
| GET | `/mentors/` | Student, IIC | **New** | Discover Mentors |
| GET | `/mentors/facets/` | Student, IIC | **New** | Discover Mentors filters |
| GET | `/mentors/{user_id}/` | Student, IIC | **New** | Discover Mentors |
| GET, PATCH | `/mentor/profile/` | Mentor | **New** | My Profile (mentor) |
| PATCH | `/mentor/availability/` | Verified mentor | — | Mentor dashboard, Workspace |
| GET, POST | `/requests/` | GET: Any (own) / IIC (all) · POST: Student | Extended | My Requests, Discover, IIC Requests |
| GET | `/requests/{id}/` | Owner student, IIC | **New** | Request details, IIC request review |
| POST | `/requests/{id}/withdraw/` | Owner student | — | My Requests |
| GET | `/admin/requests/{id}/suggestions/` | IIC | Extended | IIC request review |
| POST | `/admin/requests/{id}/availability/` | IIC | — | IIC request review |
| POST | `/admin/requests/{id}/transition/` | IIC | **New** | IIC request review |
| POST | `/admin/requests/{id}/assess/` | IIC | **New** | IIC request review |
| PATCH | `/admin/requests/{id}/priority/` | IIC | **New** | IIC request review |
| GET | `/availability/` | Mentor (own), IIC (all) | Extended | Availability Requests, Matching |
| GET | `/availability/{id}/` | Addressed mentor, IIC | — | Availability Requests |
| POST | `/availability/{id}/respond/` | Addressed verified mentor | — | Availability Requests |
| POST | `/admin/availability/{id}/approve/` | IIC | — | Matching & Approvals |
| GET | `/mentorships/` | Participants (own), IIC | Extended | My Mentorship, Workspace, Active Mentorships |
| GET | `/mentorships/{id}/` | Participants, IIC | **New** | My Mentorship, Workspace history |
| POST | `/admin/mentorships/{id}/close/` | IIC | Extended | Active Mentorships |
| POST | `/admin/mentorships/{id}/reassign/` | IIC | **New** | Active Mentorships |
| GET, POST | `/mentorships/{id}/goals/` | Participants (POST active only), IIC (GET) | — | Meetings & Goals, Workspace |
| PATCH | `/goals/{id}/complete/` | Participants | — | Meetings & Goals, Workspace |
| GET, POST | `/mentorships/{id}/meetings/` | Participants, IIC (GET) | Extended | Meetings & Goals, Workspace |
| POST | `/meetings/{id}/confirm/` | Mentor of the pair | — | Workspace › Meetings |
| GET | `/meetings/` | Participants (own), IIC | **New** | Calendar & Meetings |
| POST | `/mentorships/{id}/meetings/schedule/` | Mentor of an active pair | **New** | Workspace, Calendar & Meetings |
| POST | `/meetings/{id}/reschedule/` | Mentor of the pair | **New** | Workspace, Calendar & Meetings |
| POST | `/meetings/{id}/cancel/` | Mentor of the pair | **New** | Workspace, Calendar & Meetings |
| POST | `/meetings/{id}/record/` | Participants | **New** | Meetings tables |
| GET, POST | `/mentorships/{id}/feedback/` | Participants (own entries), IIC (all) | Extended | My Mentorship, Feedback & Progress, Active Mentorships |
| GET, POST | `/mentorships/{id}/outcomes/` | GET: participants, IIC · POST: student | — | Meetings & Goals |
| GET | `/calendar/status/` | Mentor | **New** | Calendar & Meetings |
| POST | `/calendar/connect/` | Mentor | **New** | Calendar & Meetings |
| GET | `/calendar/oauth/callback/` | Public (Google redirect) | **New** | — (redirects to `/mentor/calendar`) |
| POST | `/calendar/disconnect/` | Mentor | **New** | Calendar & Meetings |
| GET | `/notifications/` | Any | Extended | Notifications, top bar |
| POST | `/notifications/{id}/read/` | Recipient | — | Notifications |
| POST | `/notifications/read-all/` | Any | **New** | Notifications |
| GET | `/admin/students/` | IIC | Extended | Student Approvals |
| POST | `/admin/students/{user_id}/review/` | IIC | — | Student Approvals |
| GET, POST | `/admin/mentors/` | IIC | Extended | Mentor Repository |
| PATCH | `/admin/mentors/{user_id}/` | IIC | **New** | Mentor Repository |
| POST | `/admin/mentors/{user_id}/verify/` | IIC | Extended | Mentor Repository |
| POST | `/admin/mentors/{user_id}/invite/` | IIC | — | Mentor Repository |
| GET | `/admin/insights/` | IIC | Extended | Dashboard, Reports & Analytics |
| GET | `/admin/alerts/` | IIC | Extended | Monitoring & Alerts |
| POST | `/admin/alerts/{id}/resolve/` | IIC | **New** | Monitoring & Alerts |
| GET | `/admin/audit/` | IIC | Extended | Audit Log |
| GET | `/admin/export/?type=` | IIC | Extended | Reports & Analytics |
| POST | `/ai/chat/` | Any (10/min) | — | AI Assistant |
| GET | `/ai/knowledge/` | Any | — | AI Assistant |
| GET, POST, PUT, PATCH, DELETE | `/admin/knowledge/[{id}/]` | IIC | **New** | AI Knowledge Management |

## 2.2 Conventions

- **Auth:** `Authorization: Bearer <access>`. The access token lasts 30 min and the refresh token 1 day (configurable).
- **Errors:** every error body has `detail` (message), `code` and `status_code`. Field errors remain at top level
  (`{"email": ["…"]}`) and are repeated under `errors`.
- **Pagination:** endpoints marked Extended that previously returned a plain list still do so. Add `?page=` or
  `?page_size=` (max 200) to receive `{count, next, previous, results}`. `/mentors/` and `/admin/knowledge/` always paginate.
- **Ids:** `admin/students/{id}`, `admin/mentors/{id}` and `mentors/{id}` take the **user** id.

## 2.3 Samples for new and extended endpoints

### GET `/auth/me/` (Extended)
```json
{"id": 7, "email": "arjun.k@alumni.example.org", "first_name": "Arjun", "last_name": "Kumar", "role": "MENTOR",
 "student_profile": null, "mentor_profile": {"id": 2, "user": 7, "domain": "Data & ML", "is_verified": true, "is_discoverable": true, "...": "..."},
 "is_iic": false, "effective_role": "MENTOR", "display_name": "Arjun Kumar",
 "calendar": {"configured": true, "status": "CONNECTED", "google_email": "arjun@gmail.com", "connected_at": "2026-10-31T10:02:00+05:30"}}
```
`effective_role` is `ADMIN` only for real IIC staff, and `null` for an `ADMIN` role without staff rights.

### GET `/dashboard/` (New), student example
```json
{"role": "STUDENT", "display_name": "Hemant Demo", "approval_status": "APPROVED",
 "current_request": null, "mentorship": {"id": 1, "mentor_name": "Arjun Kumar", "mentor_contact": "arjun.k@…", "progress": {"goals_total": 2, "goals_completed": 1, "next_meeting": {"...": "..."}}},
 "upcoming_meeting": {"id": 4, "start_at": "2026-11-03T18:30:00+05:30", "calendar_event": {"meet_link": "https://meet.google.com/…"}},
 "goals": {"completed": 1, "total": 2}, "recent_activity": [{"event": "MATCH_APPROVED", "label": "Active", "created_at": "…"}],
 "tasks": [{"key": "add_goals", "label": "Agree shared goals with your mentor", "link": "/meetings-goals", "count": 1, "tone": "info"}],
 "next_steps": [{"title": "Record outcomes", "detail": "…", "link": "/meetings-goals"}], "notifications": {"unread": 2, "latest": []}}
```
Mentor dashboards add `availability`, `pending_checks`, `unconfirmed_meetings`, `feedback` (due / next due) and `calendar`.
IIC dashboards add `counts`, `review_queue` (sorted by priority), `approval_queue`, `domain_demand` and `participation`.

### GET `/mentors/?domain=data&skill=python&min_experience=3&available=true&page=1` (New)
Filters: `search`, `domain`, `specialty`, `career_path`, `skill`, `min_experience`, `max_experience`, `available`.
```json
{"count": 1, "next": null, "previous": null, "results": [{"id": 7, "name": "Arjun Kumar", "current_role": "Senior Data Scientist",
 "company": "Fractal Analytics", "domain": "Data & ML", "specialty": "Machine learning engineering", "career_path": "Job",
 "experience_years": 6, "skills": ["Python", "SQL"], "bio": "", "linkedin_url": "https://www.linkedin.com/in/…", "graduation_year": 2022,
 "availability": {"is_available": true, "has_capacity": true, "accepting_requests": true, "label": "Available"}}]}
```
There is never an email, phone or roll number. `GET /mentors/facets/` returns `{"domains": [], "specialties": [], "career_paths": [], "skills": []}`.

### GET, PATCH `/mentor/profile/` (New)
Request: `{"skills": ["SQL", "Tableau"], "linkedin_url": "https://www.linkedin.com/in/neha", "bio": "Analytics lead"}`.
Response: the full mentor profile. `is_verified` and `is_discoverable` are read-only here (IIC-controlled). Non-LinkedIn URLs are rejected with 400.

### POST `/requests/` (Extended)
```json
{"pathway": "JOB", "domain": "Software", "background": "Diploma in programming",
 "problem_statement": "≥ 80 characters describing the need …", "preferred_mentor": 9}
```
Response 201 (student view):
```json
{"id": 3, "status": "SUBMITTED", "stage": "SUBMITTED", "stage_label": "Submitted",
 "next_action": "No action needed. IIC will review your request.", "preferred_mentor": 9,
 "preferred_mentor_summary": {"id": 9, "name": "Priya Nair", "current_role": "SDE", "company": "Amazon"},
 "assigned_mentor": null, "mentorship_id": null, "priority": null, "student_summary": null, "last_status_at": "…"}
```
Returns 400 for a second open request, an existing active mentorship, a statement under 80 characters, or a preferred mentor not in the directory.
IIC callers also receive `priority` and `student_summary`. GET supports `status=` (comma list), `stage=`, `search=` for IIC.

### GET `/requests/{id}/` (New)
Adds `timeline` (`[{event, from_status, to_status, label, actor_role, note, created_at}]`) and, for IIC only, `availability_checks`.

### POST `/admin/requests/{id}/transition/` (New)
`{"to_status": "UNDER_REVIEW" | "WAITING" | "CLOSED", "note": "required for CLOSED"}` → the updated request. Invalid transitions return 400.

### POST `/admin/requests/{id}/assess/` and PATCH `/admin/requests/{id}/priority/` (New)
```json
{"assessment_id": 5, "effective": "URGENT", "suggested": "HIGH", "explanation": "Deadline mentioned within 4 day(s)",
 "confidence": 0.85, "overridden": true, "override_reason": "Offer expiring", "assessed_at": "…"}
```
The override request is `{"priority": "URGENT", "reason": "Offer expiring"}`; `{"priority": ""}` clears it. A reason is required when setting an override.

### GET `/admin/requests/{id}/suggestions/` (Extended)
Adds `student_preference_mentor_id`; each candidate has `name` and `is_student_preference`. A preferred mentor is always listed if eligible, but is never scored higher.

### GET `/availability/?status=CONFIRMED` (Extended)
Each check now includes `request_summary` (domain, pathway and a redacted problem statement, with no student identity), `is_expired`, and (IIC only) `mentor_summary`.

### GET `/mentorships/{id}/` (New)
The pair (`student_name`, `mentor_name`, contacts, `mentor_profile.linkedin_url`, `progress`, `closure_type`) plus
`timeline`: `[{type: "status"|"meeting"|"goal"|"outcome", at, title, detail, event}]` and `approved_at`.

### POST `/admin/mentorships/{id}/close/` (Extended) and `/reassign/` (New)
Close: `{"reason": "Goals achieved", "closure_type": "COMPLETED"}` → `{"id": 1, "status": "CLOSED", "closure_type": "COMPLETED"}`.
Reassign: `{"reason": "Student requested a change"}` → the linked request, now `status: "WAITING"`, ready for a new availability check.

### POST `/mentorships/{id}/meetings/schedule/` (New); POST `/meetings/{id}/reschedule/` takes the same body
```json
{"date": "2026-11-03", "start_time": "18:30", "end_time": "19:15", "timezone": "Asia/Kolkata",
 "title": "Portfolio review", "meeting_format": "VIDEO", "add_google_meet": true}
```
Response 201:
```json
{"id": 4, "status": "SCHEDULED", "start_at": "2026-11-03T18:30:00+05:30", "end_at": "…", "duration_minutes": 45,
 "calendar_event": {"provider": "GOOGLE", "html_link": "https://calendar.google.com/…", "meet_link": "https://meet.google.com/…",
 "sync_status": "SYNCED", "last_synced_at": "…", "last_error": ""}, "calendar_synced": true}
```
If the mentor has not connected Google Calendar, the meeting is still saved, with `calendar_event: null` and `calendar_synced: false`.
`/cancel/` takes no body. `/record/` takes `{"status": "HELD" | "NO_SHOW"}` once the start time has passed.

### Calendar (New)
`GET /calendar/status/` → `{"configured": true, "status": "CONNECTED" | "DISCONNECTED" | "REAUTH_REQUIRED", "google_email": "", "connected_at": null}`.
`POST /calendar/connect/` → `{"authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?..."}`, or 503 with `code: calendar_not_configured`.
Google then redirects to `/calendar/oauth/callback/`, which redirects to `<frontend>/mentor/calendar?calendar=connected|denied|error`.

### GET `/admin/insights/` (Extended)
The original keys are unchanged. New keys: `students_pending`, `mentors_unverified`, `mentors_verified`, `checks_pending`,
`matches_awaiting_approval`, `mentorships_closed`, `requests_by_status`, `pathway_demand`, `outcomes_by_kind`, `closure_types`,
`monthly_requests`, `monthly_mentorships`, `monthly_meetings` (each `[{month: "2026-10", count: 3}]`, the last six months ending with the current one).

### Alerts, audit, export (Extended / New)
- `GET /admin/alerts/?include_resolved=true` adds `kind_label`, `created_at`, `resolved_at`, `student_name`, `mentor_name`. `POST /admin/alerts/{id}/resolve/` → `{"id": 3, "resolved_at": "…"}`.
- `GET /admin/audit/?action=MATCH_APPROVED&page=1` adds `actor_email`, `actor_role` and `details` to the original fields.
- `GET /admin/export/?type=pairs|requests|meetings|outcomes` returns CSV with IDs and metadata only; `pairs` is the default (original behaviour).

### Notifications (Extended / New)
`GET /notifications/?unread=true&page=1`; `POST /notifications/read-all/` → `{"updated": 4}`.

### Knowledge management (New)
`POST /admin/knowledge/` `{"title": "How matching works", "content": "…", "audience": "ALL", "is_published": true}` → 201 with the article.
Standard list/retrieve/update/partial_update/destroy. Writes are recorded in the audit log.

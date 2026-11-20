# 4. Role and permission matrix

IIC = `role=ADMIN` **and** `is_staff`, or a superuser (`apps.accounts.permissions.iic`). An `ADMIN` role without staff rights
has no IIC access. "Approved student" = `role=STUDENT` with `approval_status=APPROVED`.

Legend: ✔ allowed · **own** limited to the caller's records · — denied (403/404).

| Capability | Student | Mentor | IIC | Enforced in |
|---|---|---|---|---|
| Register, sign in, view/edit own name | ✔ | ✔ | ✔ | `RegisterView`, `me` |
| Edit academic profile (until approved) | own | — | — | `student_profile` |
| Approve/reject student registrations | — | — | ✔ | `IsIIC` |
| Browse Discover Mentors directory | approved | — | ✔ | `IsApprovedStudentOrIIC` |
| Edit own professional profile | — | own (not verification or publication) | ✔ (any mentor) | `IsMentor`, `MentorSelfUpdateSerializer` / `IsIIC` |
| Verify mentor, publish to directory, invite | — | — | ✔ | `IsIIC` |
| Toggle own availability | — | verified, own | — | `IsVerifiedMentor` |
| Submit a mentoring request (one open at a time) | approved | — | — | `require_student`, `create_request`, DB constraint |
| Name a preferred mentor | approved (published mentors only) | — | — | `RequestSerializer.validate_preferred_mentor` |
| View request list and details | own | — | ✔ all | `requests`, `request_detail` |
| See AI priority and student summary on requests | — | — | ✔ | `RequestSerializer` (`iic()` check) |
| Withdraw a request | own, open | — | — | `withdraw_request` |
| Mentor suggestions, availability checks, transitions, priority override | — | — | ✔ | `require_iic` |
| View availability checks | — | own (addressed to them) | ✔ all | `availability_inbox`, `availability_detail` |
| Confirm/decline availability | — | own, verified, unexpired | — | `respond_availability` |
| Final approval of a pairing | — | — | ✔ (confirmed, unexpired check only) | `approve_match` |
| View mentorships | own | own | ✔ all | `pair_for_user` |
| See counterpart contact details | after approval | after approval | ✔ | `PairSerializer._can_see` (only mentorships exist post-approval) |
| Add/complete shared goals (max 3) | own active | own active | read | `goals`, `goal_complete` |
| Log past meetings | own active (unconfirmed) | own active (confirmed) | read | `meetings` |
| Confirm a student-logged meeting | — | own | — | `confirm_meeting` |
| Schedule, reschedule or cancel meetings | — | own active | — | `views_calendar._meeting_for_mentor` |
| Record a scheduled meeting as held or no-show | own | own | — | `record_meeting` |
| Submit written feedback | own (GENERAL, CHANGE_MENTOR, CLOSING) | own (PROGRESS, GENERAL, CLOSING) | — | `feedback`, `FEEDBACK_AUTHORS` |
| Read feedback | own entries | own entries | ✔ all | `feedback` |
| Record outcomes | own | — | read | `outcomes` |
| Close or reassign a mentorship | — | — | ✔ | `require_iic` |
| Connect Google Calendar | — | ✔ | — | `require_mentor` |
| Dashboard | student view | mentor view | IIC view | `views_dashboard.dashboard` |
| Insights, alerts, audit log, CSV exports | — | — | ✔ | `require_iic` |
| Manage AI knowledge base | — | — | ✔ | `KnowledgeAdminViewSet` (`IsIIC`) |
| Use AI assistant | ✔ | ✔ | ✔ | `chat` (10/min, not stored) |
| Notifications | own | own | own | `notifications` (recipient filter) |
| Django admin `/admin/` | — | — | staff | Django admin; workflow models are read-only there |

## Frontend navigation (derived from `effective_role`)
- **Student:** Dashboard · Discover Mentors · My Requests · My Mentorship · Meetings & Goals · AI Assistant · Notifications · My Profile
- **Mentor:** Dashboard · Availability Requests · Mentorship Workspace · Calendar & Meetings · Feedback & Progress · AI Assistant · My Profile
- **IIC:** Dashboard · Student Approvals · Mentor Repository · Mentorship Requests · Matching & Approvals · Active Mentorships · Monitoring & Alerts · Reports & Analytics · Audit Log · AI Knowledge Management

Opening a route outside your role redirects to the dashboard. The API would refuse the calls regardless.

## Test coverage of this matrix
`apps/accounts/tests.py` and `apps/mentoring/test_workflow.py` cover: a fake ADMIN without staff rights, directory access by
pending students and mentors, mentors trying to self-verify, another student or mentor reading a request or check,
students calling IIC endpoints, mentors approving matches, wrong-role feedback kinds, mentors recording outcomes,
outsiders reading goals, and non-IIC audit access. `test_calendar.py` covers students attempting to schedule or connect a calendar.

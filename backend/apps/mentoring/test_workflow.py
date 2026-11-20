from datetime import timedelta
from django.utils import timezone
from apps.accounts.models import User
from apps.assistant_ai.models import AIRequestAssessment, KnowledgeArticle
from .factories import SangamAPITestCase, make_mentor, make_student, PROBLEM
from .models import AvailabilityCheck, Mentorship, MentoringRequest, Alert, ActivityStatusHistory, Meeting


class ApprovalWorkflowTests(SangamAPITestCase):
    def test_preferred_mentor_never_creates_or_confirms_a_mentorship(self):
        req = self.submit_request(preferred_mentor=self.mentor.pk)
        self.assertEqual(req['stage'], 'SUBMITTED')
        self.assertEqual(req['preferred_mentor_summary']['id'], self.mentor.pk)
        self.assertIsNone(req['assigned_mentor'])
        self.assertFalse(AvailabilityCheck.objects.exists())
        self.assertFalse(Mentorship.objects.exists())
        suggestions = self.as_user(self.iic).get(f'/api/v1/admin/requests/{req["id"]}/suggestions/')
        self.assertEqual(suggestions.data['student_preference_mentor_id'], self.mentor.pk)
        self.assertTrue(suggestions.data['candidates'][0]['is_student_preference'])
        self.assertTrue(suggestions.data['approval_required'])

    def test_preferred_mentor_must_be_published(self):
        hidden = make_mentor('hidden@example.org', discoverable=False, alumni_roll_number='AL2')
        r = self.as_user(self.student).post('/api/v1/requests/', {**self.request_data, 'preferred_mentor': hidden.pk}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('preferred_mentor', r.data)

    def test_stages_timeline_and_contact_visibility(self):
        req_id = self.submit_request()['id']
        c = self.as_user(self.iic)
        check = c.post(f'/api/v1/admin/requests/{req_id}/availability/', {'mentor_id': self.mentor.pk}, format='json').data
        detail = self.as_user(self.student).get(f'/api/v1/requests/{req_id}/').data
        self.assertEqual(detail['stage'], 'AVAILABILITY_CHECK_SENT')
        self.assertIsNone(detail['assigned_mentor'])
        self.assertIsNone(detail['availability_checks'])  # IIC-only
        self.assertNotIn(self.mentor.email, str(detail))
        self.as_user(self.mentor).post(f'/api/v1/availability/{check["id"]}/respond/', {'decision': 'CONFIRMED'}, format='json')
        self.assertEqual(self.as_user(self.student).get(f'/api/v1/requests/{req_id}/').data['stage'], 'AWAITING_IIC_APPROVAL')
        # Mentor sees the anonymised need, never the student identity, before approval.
        inbox = self.as_user(self.mentor).get('/api/v1/availability/').data[0]
        self.assertNotIn(self.student.email, str(inbox))
        self.assertIsNone(inbox['mentor_summary'])
        pair = self.as_user(self.iic).post(f'/api/v1/admin/availability/{check["id"]}/approve/').data
        detail = self.as_user(self.student).get(f'/api/v1/requests/{req_id}/').data
        self.assertEqual(detail['stage'], 'ACTIVE')
        self.assertEqual(detail['assigned_mentor']['id'], self.mentor.pk)
        events = [t['event'] for t in detail['timeline']]
        self.assertEqual(events, ['REQUEST_SUBMITTED', 'AVAILABILITY_CHECK_SENT', 'MENTOR_CONFIRMED', 'MATCH_APPROVED'])
        mentorship = self.as_user(self.mentor).get(f'/api/v1/mentorships/{pair["id"]}/').data
        self.assertEqual(mentorship['student_contact'], self.student.email)
        self.assertTrue(mentorship['timeline'])

    def test_object_level_permissions(self):
        req_id = self.submit_request()['id']
        other = make_student('other@study.iitm.ac.in', roll='21f9')
        self.assertEqual(self.as_user(other).get(f'/api/v1/requests/{req_id}/').status_code, 403)
        self.assertEqual(self.as_user(other).post(f'/api/v1/requests/{req_id}/withdraw/').status_code, 404)
        self.assertEqual(self.as_user(self.mentor).get(f'/api/v1/requests/{req_id}/').status_code, 403)
        self.assertEqual(self.as_user(self.student).post(f'/api/v1/admin/requests/{req_id}/availability/', {'mentor_id': self.mentor.pk}, format='json').status_code, 403)
        check = self.as_user(self.iic).post(f'/api/v1/admin/requests/{req_id}/availability/', {'mentor_id': self.mentor.pk}, format='json').data
        intruder = make_mentor('intruder@example.org', alumni_roll_number='AL5')
        self.assertEqual(self.as_user(intruder).get(f'/api/v1/availability/{check["id"]}/').status_code, 403)
        self.assertEqual(self.as_user(intruder).post(f'/api/v1/availability/{check["id"]}/respond/', {'decision': 'CONFIRMED'}, format='json').status_code, 403)
        self.assertEqual(self.as_user(intruder).get('/api/v1/availability/').data, [])
        self.assertEqual(self.as_user(self.mentor).post(f'/api/v1/admin/availability/{check["id"]}/approve/').status_code, 403)
        self.assertEqual(self.as_user(self.student).get('/api/v1/requests/').data[0]['priority'], None)

    def test_expired_check_is_persisted_when_mentor_responds_late(self):
        req_id = self.submit_request()['id']
        check_id = self.as_user(self.iic).post(f'/api/v1/admin/requests/{req_id}/availability/', {'mentor_id': self.mentor.pk}, format='json').data['id']
        AvailabilityCheck.objects.filter(pk=check_id).update(expires_at=timezone.now() - timedelta(minutes=1))
        r = self.as_user(self.mentor).post(f'/api/v1/availability/{check_id}/respond/', {'decision': 'CONFIRMED'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(AvailabilityCheck.objects.get(pk=check_id).status, 'EXPIRED')
        self.assertEqual(MentoringRequest.objects.get(pk=req_id).status, 'WAITING')

    def test_one_active_mentee_per_mentor(self):
        self.activate_pair()
        second = make_student('second@study.iitm.ac.in', roll='21f3')
        r = self.as_user(second).post('/api/v1/requests/', self.request_data, format='json')
        busy = self.as_user(self.iic).post(f'/api/v1/admin/requests/{r.data["id"]}/availability/', {'mentor_id': self.mentor.pk}, format='json')
        self.assertEqual(busy.status_code, 400)

    def test_withdraw_and_iic_close_with_reason(self):
        req_id = self.submit_request()['id']
        self.assertEqual(self.as_user(self.student).post(f'/api/v1/requests/{req_id}/withdraw/').data['status'], 'WITHDRAWN')
        req2 = self.submit_request()['id']
        c = self.as_user(self.iic)
        self.assertEqual(c.post(f'/api/v1/admin/requests/{req2}/transition/', {'to_status': 'CLOSED'}, format='json').status_code, 400)
        self.assertEqual(c.post(f'/api/v1/admin/requests/{req2}/transition/', {'to_status': 'UNDER_REVIEW'}, format='json').data['stage'], 'UNDER_REVIEW')
        closed = c.post(f'/api/v1/admin/requests/{req2}/transition/', {'to_status': 'CLOSED', 'note': 'Outside programme scope'}, format='json')
        self.assertEqual(closed.data['status'], 'CLOSED')

    def test_reassignment_reopens_request_for_a_new_mentor(self):
        pair_id = self.activate_pair()
        r = self.as_user(self.iic).post(f'/api/v1/admin/mentorships/{pair_id}/reassign/', {'reason': 'Student asked for a change'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['status'], 'WAITING')
        old = Mentorship.objects.get(pk=pair_id)
        self.assertEqual((old.status, old.closure_type), ('CLOSED', 'REASSIGNED'))
        new_mentor = make_mentor('second-mentor@example.org', alumni_roll_number='AL6')
        new_pair = self.activate_pair(request_id=r.data['id'], mentor=new_mentor)
        self.assertEqual(Mentorship.objects.get(pk=new_pair).mentor, new_mentor)
        self.assertEqual(self.as_user(self.iic).post(f'/api/v1/admin/mentorships/{new_pair}/close/', {'reason': ''}, format='json').status_code, 400)
        closed = self.as_user(self.iic).post(f'/api/v1/admin/mentorships/{new_pair}/close/', {'reason': 'Goals achieved'}, format='json')
        self.assertEqual(closed.data['closure_type'], 'COMPLETED')


class PriorityTests(SangamAPITestCase):
    def test_deadline_drives_advisory_priority_and_override_persists(self):
        soon = (timezone.localdate() + timedelta(days=4)).isoformat()
        req = self.submit_request(problem_statement=PROBLEM + f' My interview is on {soon}.')
        self.assertIsNone(req['priority'])  # students never see triage priority
        listing = self.as_user(self.iic).get('/api/v1/requests/').data[0]
        self.assertEqual(listing['priority']['suggested'], 'HIGH')
        self.assertEqual(listing['priority']['confidence'], 0.85)
        self.assertEqual(listing['status'], 'SUBMITTED')  # priority never changes workflow status
        factors = AIRequestAssessment.objects.get(request_id=req['id']).factors
        self.assertEqual(set(factors), {'days_to_deadline', 'deadline_explicit', 'deadline_keyword', 'waiting_days',
                                        'unsuccessful_checks', 'status', 'score'})
        c = self.as_user(self.iic)
        self.assertEqual(c.patch(f'/api/v1/admin/requests/{req["id"]}/priority/', {'priority': 'LOW'}, format='json').status_code, 400)
        over = c.patch(f'/api/v1/admin/requests/{req["id"]}/priority/', {'priority': 'URGENT', 'reason': 'Offer expiring'}, format='json')
        self.assertEqual(over.data['effective'], 'URGENT')
        again = c.post(f'/api/v1/admin/requests/{req["id"]}/assess/').data
        self.assertEqual((again['effective'], again['overridden']), ('URGENT', True))
        self.assertEqual(self.as_user(self.student).post(f'/api/v1/admin/requests/{req["id"]}/assess/').status_code, 403)

    def test_no_signals_is_low(self):
        req = self.submit_request()
        self.assertEqual(self.as_user(self.iic).get(f'/api/v1/requests/{req["id"]}/').data['priority']['suggested'], 'LOW')


class WorkspaceTests(SangamAPITestCase):
    def setUp(self):
        super().setUp()
        self.pair_id = self.activate_pair()

    def test_feedback_roles_privacy_and_alert_resolution(self):
        pair = Mentorship.objects.get(pk=self.pair_id)
        alert = Alert.objects.create(mentorship=pair, kind='FEEDBACK_DUE', period_start=timezone.localdate())
        url = f'/api/v1/mentorships/{self.pair_id}/feedback/'
        self.assertEqual(self.as_user(self.student).post(url, {'kind': 'PROGRESS', 'text': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.as_user(self.mentor).post(url, {'kind': 'PROGRESS', 'text': 'Portfolio review done.'}, format='json').status_code, 201)
        self.assertIsNotNone(Alert.objects.get(pk=alert.pk).resolved_at)
        self.as_user(self.student).post(url, {'kind': 'GENERAL', 'text': 'Helpful sessions.'}, format='json')
        self.assertEqual(len(self.as_user(self.mentor).get(url).data), 1)
        self.assertEqual(len(self.as_user(self.iic).get(url).data), 2)

    def test_meeting_log_rules(self):
        url = f'/api/v1/mentorships/{self.pair_id}/meetings/'
        future = (timezone.localdate() + timedelta(days=2)).isoformat()
        c = self.as_user(self.student)
        self.assertEqual(c.post(url, {'session_date': future, 'duration_minutes': 30}, format='json').status_code, 400)
        self.assertEqual(c.post(url, {'session_date': str(timezone.localdate()), 'duration_minutes': 30, 'status': 'SCHEDULED'}, format='json').status_code, 400)
        logged = c.post(url, {'session_date': str(timezone.localdate()), 'duration_minutes': 30}, format='json')
        self.assertFalse(logged.data['mentor_confirmed'])
        dash = self.as_user(self.mentor).get('/api/v1/dashboard/').data
        self.assertEqual(len(dash['unconfirmed_meetings']), 1)
        self.assertEqual(self.as_user(self.student).post(f'/api/v1/meetings/{logged.data["id"]}/confirm/').status_code, 403)
        self.assertTrue(self.as_user(self.mentor).post(f'/api/v1/meetings/{logged.data["id"]}/confirm/').data['mentor_confirmed'])

    def test_goals_limit_and_outcomes_by_student(self):
        url = f'/api/v1/mentorships/{self.pair_id}/goals/'
        for slot in (1, 2, 3):
            self.assertEqual(self.as_user(self.student).post(url, {'slot': slot, 'title': f'Goal {slot}', 'target_date': '2027-01-01'}, format='json').status_code, 201)
        self.assertEqual(self.as_user(self.mentor).post(url, {'slot': 1, 'title': 'Extra', 'target_date': '2027-01-01'}, format='json').status_code, 400)
        out = f'/api/v1/mentorships/{self.pair_id}/outcomes/'
        self.assertEqual(self.as_user(self.mentor).post(out, {'kind': 'JOB', 'achieved_on': '2026-10-01'}, format='json').status_code, 403)
        self.assertEqual(self.as_user(self.student).post(out, {'kind': 'JOB', 'achieved_on': '2026-10-01'}, format='json').status_code, 201)
        outsider = make_student('outsider@study.iitm.ac.in', roll='21f8')
        self.assertEqual(self.as_user(outsider).get(url).status_code, 403)


class DashboardAndReportTests(SangamAPITestCase):
    def test_role_dashboards(self):
        self.submit_request()
        self.assertEqual(self.as_user(self.student).get('/api/v1/dashboard/').data['role'], 'STUDENT')
        self.assertEqual(self.as_user(self.mentor).get('/api/v1/dashboard/').data['role'], 'MENTOR')
        admin = self.as_user(self.iic).get('/api/v1/dashboard/').data
        self.assertEqual(admin['role'], 'ADMIN')
        self.assertEqual(admin['counts']['requests_awaiting_review'], 1)
        self.assertTrue(all(t['link'].startswith('/admin/') for t in admin['tasks']))

    def test_insights_exports_audit_and_notifications(self):
        self.activate_pair()
        c = self.as_user(self.iic)
        insights = c.get('/api/v1/admin/insights/').data
        for key in ('requests', 'waiting', 'active_pairs', 'meetings_held', 'outcomes', 'alerts_open', 'domain_demand', 'monthly_requests'):
            self.assertIn(key, insights)
        for kind in ('pairs', 'requests', 'outcomes', 'meetings'):
            r = c.get(f'/api/v1/admin/export/?type={kind}')
            self.assertEqual(r.status_code, 200)
            self.assertNotIn(self.student.email, r.content.decode())
        self.assertEqual(c.get('/api/v1/admin/export/?type=users').status_code, 400)
        audit = c.get('/api/v1/admin/audit/?page=1').data
        self.assertIn('results', audit)
        self.assertIn('MATCH_APPROVED', [row['action'] for row in audit['results']])
        self.assertEqual(self.as_user(self.student).get('/api/v1/admin/audit/').status_code, 403)
        s = self.as_user(self.student)
        self.assertGreater(len(s.get('/api/v1/notifications/?unread=true').data), 0)
        s.post('/api/v1/notifications/read-all/')
        self.assertEqual(len(s.get('/api/v1/notifications/?unread=true').data), 0)

    def test_history_is_append_only_and_has_no_personal_text(self):
        req_id = self.submit_request()['id']
        for row in ActivityStatusHistory.objects.filter(request_id=req_id):
            self.assertNotIn(PROBLEM[:30], row.note)
            self.assertNotIn(self.student.email, row.note)


class KnowledgeAdminTests(SangamAPITestCase):
    def test_iic_manages_knowledge_and_chatbot_uses_published_only(self):
        payload = {'title': 'Requesting a mentor', 'content': 'Submit a pathway, domain and a specific question of 80+ characters.',
                   'audience': 'ALL', 'is_published': False}
        self.assertEqual(self.as_user(self.student).post('/api/v1/admin/knowledge/', payload, format='json').status_code, 403)
        created = self.as_user(self.iic).post('/api/v1/admin/knowledge/', payload, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(self.as_user(self.student).get('/api/v1/ai/knowledge/').data, [])
        self.as_user(self.iic).patch(f'/api/v1/admin/knowledge/{created.data["id"]}/', {'is_published': True}, format='json')
        self.assertEqual(len(self.as_user(self.student).get('/api/v1/ai/knowledge/').data), 1)
        chat = self.as_user(self.student).post('/api/v1/ai/chat/', {'message': 'How do I request a mentor?'}, format='json')
        self.assertFalse(chat.data['message_stored'])
        self.assertEqual(chat.data['sources'][0]['id'], created.data['id'])
        self.assertEqual(self.as_user(self.iic).delete(f'/api/v1/admin/knowledge/{created.data["id"]}/').status_code, 204)
        self.assertFalse(KnowledgeArticle.objects.exists())


class MonthlySeriesTests(SangamAPITestCase):
    def test_series_ends_with_current_month(self):
        self.submit_request()
        series = self.as_user(self.iic).get('/api/v1/admin/insights/').data['monthly_requests']
        self.assertEqual(len(series), 6)
        self.assertEqual(series[-1]['month'], timezone.localdate().strftime('%Y-%m'))
        self.assertEqual(series[-1]['count'], 1)

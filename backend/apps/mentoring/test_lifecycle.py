"""The 12-step mentoring lifecycle: intake, registration checklist, scheduler, closing feedback."""
from datetime import timedelta
from django.test import override_settings
from django.utils import timezone
from apps.accounts.models import User, StudentProfile
from .factories import SangamAPITestCase, make_student
from .models import Alert, AuditLog, AvailabilityCheck, Mentorship, MentoringRequest, Notification

MENTOR_ROW = {'first_name': 'Meera', 'last_name': 'Iyer', 'alumni_roll_number': 'AL9', 'graduation_year': 2021,
              'domain': 'Data & ML', 'specialty': 'NLP', 'current_role': 'ML engineer', 'experience_years': 4}
CHECKLIST = {'iitm_email': True, 'roll_number': True, 'level': True, 'courses': True, 'cgpa': True}


class MentorIntakeTests(SangamAPITestCase):
    """Step 1: IIC builds the repository from the alumni call."""
    def test_bulk_import_dry_run_then_partial_create(self):
        rows = [{**MENTOR_ROW, 'email': 'meera@example.org'}, {**MENTOR_ROW, 'email': 'MEERA@example.org'},
                {**MENTOR_ROW, 'email': 'not-an-email'}, {**MENTOR_ROW, 'email': 'ravi@example.org', 'skills': ['Python']}]
        url = '/api/v1/admin/mentors/import/'
        self.assertEqual(self.as_user(self.student).post(url, {'mentors': rows}, format='json').status_code, 403)
        dry = self.as_user(self.iic).post(url, {'mentors': rows, 'dry_run': True}, format='json')
        self.assertEqual(dry.status_code, 200, dry.data)
        self.assertEqual([c['row'] for c in dry.data['created']], [1, 4])
        self.assertEqual([e['row'] for e in dry.data['errors']], [2, 3])
        self.assertFalse(User.objects.filter(email='meera@example.org').exists())
        real = self.as_user(self.iic).post(url, {'mentors': rows}, format='json')
        self.assertEqual(real.status_code, 201, real.data)
        self.assertEqual(len(real.data['created']), 2)
        m = User.objects.get(email='meera@example.org')
        self.assertFalse(m.has_usable_password())
        self.assertFalse(m.mentor_profile.is_verified)  # verification remains a separate IIC step
        self.assertTrue(AuditLog.objects.filter(action='MENTORS_IMPORTED').exists())


class RegistrationChecklistTests(SangamAPITestCase):
    """Steps 2-3: IITM email registration and checklist-based IIC approval."""
    def test_roll_number_is_derived_from_iitm_email(self):
        self.client.force_authenticate(user=None)
        payload = {'email': '23F2001234@ds.study.iitm.ac.in', 'password': 'Str0ng!Passw0rd', 'first_name': 'A',
                   'last_name': 'B', 'level': 'DIPLOMA', 'courses': ['Python']}
        self.assertEqual(self.client.post('/api/v1/auth/register/', payload, format='json').status_code, 201)
        self.assertEqual(StudentProfile.objects.get(user__email='23f2001234@ds.study.iitm.ac.in').iitm_roll_number, '23f2001234')
        other = self.client.post('/api/v1/auth/register/', {**payload, 'email': 'asha.rao@study.iitm.ac.in'}, format='json')
        self.assertEqual(other.status_code, 400)
        self.assertIn('iitm_roll_number', other.data)

    def test_approval_requires_every_checklist_item(self):
        pending = make_student('pending@study.iitm.ac.in', approved=False, roll='22f1000002')
        url = f'/api/v1/admin/students/{pending.pk}/review/'
        partial = self.as_user(self.iic).post(url, {'decision': 'APPROVED', 'checklist': {**CHECKLIST, 'cgpa': False}}, format='json')
        self.assertEqual(partial.status_code, 400)
        self.assertIn('checklist', partial.data)
        ok = self.as_user(self.iic).post(url, {'decision': 'APPROVED', 'checklist': CHECKLIST}, format='json')
        self.assertEqual(ok.status_code, 200, ok.data)
        self.assertEqual(ok.data['approval_status'], 'APPROVED')
        self.assertEqual(AuditLog.objects.get(action='STUDENT_REVIEW').details['checklist'], CHECKLIST)


class SchedulerTests(SangamAPITestCase):
    """Steps 7 and 11: the 7-day expiry and 14-day monitoring run without a server cron."""
    @override_settings(CRON_SECRET='s3cret')
    def test_cron_endpoint_requires_secret_and_runs_checks(self):
        req_id = self.submit_request()['id']
        check = self.as_user(self.iic).post(f'/api/v1/admin/requests/{req_id}/availability/', {'mentor_id': self.mentor.pk}, format='json').data
        AvailabilityCheck.objects.filter(pk=check['id']).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get('/api/v1/cron/daily/').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/cron/daily/', HTTP_AUTHORIZATION='Bearer wrong').status_code, 403)
        ok = self.client.get('/api/v1/cron/daily/', HTTP_AUTHORIZATION='Bearer s3cret')
        self.assertEqual(ok.status_code, 200, ok.data)
        self.assertEqual(ok.data['expired_checks'], 1)
        self.assertEqual(MentoringRequest.objects.get(pk=req_id).status, 'WAITING')
        self.assertTrue(Notification.objects.filter(recipient=self.iic, title='Availability check expired').exists())

    def test_cron_endpoint_disabled_without_secret(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get('/api/v1/cron/daily/', HTTP_AUTHORIZATION='Bearer ').status_code, 403)

    def test_iic_runs_checks_on_demand_and_alerts_are_idempotent(self):
        pair_id = self.activate_pair()
        Mentorship.objects.filter(pk=pair_id).update(started_at=timezone.now() - timedelta(days=20))
        self.assertEqual(self.as_user(self.mentor).post('/api/v1/admin/daily-checks/').status_code, 403)
        first = self.as_user(self.iic).post('/api/v1/admin/daily-checks/').data
        self.assertEqual((first['inactivity_alerts'], first['feedback_alerts']), (1, 1))
        second = self.as_user(self.iic).post('/api/v1/admin/daily-checks/').data
        self.assertEqual((second['inactivity_alerts'], second['feedback_alerts']), (0, 0))
        self.assertEqual(Alert.objects.filter(mentorship_id=pair_id, resolved_at__isnull=True).count(), 2)

    def test_mentor_inbox_expires_overdue_checks(self):
        req_id = self.submit_request()['id']
        check = self.as_user(self.iic).post(f'/api/v1/admin/requests/{req_id}/availability/', {'mentor_id': self.mentor.pk}, format='json').data
        AvailabilityCheck.objects.filter(pk=check['id']).update(expires_at=timezone.now() - timedelta(minutes=1))
        inbox = self.as_user(self.mentor).get('/api/v1/availability/').data
        self.assertEqual(inbox[0]['status'], 'EXPIRED')

    def test_decline_notifies_iic(self):
        req_id = self.submit_request()['id']
        check = self.as_user(self.iic).post(f'/api/v1/admin/requests/{req_id}/availability/', {'mentor_id': self.mentor.pk}, format='json').data
        self.as_user(self.mentor).post(f'/api/v1/availability/{check["id"]}/respond/', {'decision': 'DECLINED'}, format='json')
        self.assertTrue(Notification.objects.filter(recipient=self.iic, title='Mentor declined availability').exists())


class ClosingTests(SangamAPITestCase):
    """Step 12: closing feedback and outcomes after IIC ends the mentorship; mentor returns to the pool."""
    def test_closing_feedback_and_outcomes_after_close(self):
        pair_id = self.activate_pair()
        self.as_user(self.iic).post(f'/api/v1/admin/mentorships/{pair_id}/close/', {'reason': 'Goals achieved'}, format='json')
        url = f'/api/v1/mentorships/{pair_id}/feedback/'
        self.assertEqual(self.as_user(self.student).post(url, {'kind': 'GENERAL', 'text': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.as_user(self.student).post(url, {'kind': 'CLOSING', 'text': 'Got an internship.'}, format='json').status_code, 201)
        self.assertEqual(self.as_user(self.student).post(url, {'kind': 'CLOSING', 'text': 'Again'}, format='json').status_code, 400)
        self.assertEqual(self.as_user(self.mentor).post(url, {'kind': 'CLOSING', 'text': 'Great mentee.'}, format='json').status_code, 201)
        outcome = self.as_user(self.student).post(f'/api/v1/mentorships/{pair_id}/outcomes/',
                                                  {'kind': 'INTERNSHIP', 'achieved_on': str(timezone.localdate()), 'note': ''}, format='json')
        self.assertEqual(outcome.status_code, 201, outcome.data)
        self.assertTrue(Notification.objects.filter(recipient=self.mentor, message__contains='back in the mentor pool').exists())
        # The mentor is free for the next match.
        other = make_student('next@study.iitm.ac.in', roll='22f1000003')
        r = self.as_user(other).post('/api/v1/requests/', self.request_data, format='json').data
        check = self.as_user(self.iic).post(f'/api/v1/admin/requests/{r["id"]}/availability/', {'mentor_id': self.mentor.pk}, format='json')
        self.assertEqual(check.status_code, 201, check.data)

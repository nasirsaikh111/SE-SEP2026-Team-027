"""HTTP contract tests for accounts; run from this folder with python -m pytest.

Uses Django's isolated test database and in-memory email, with no live services.
"""
from urllib.parse import parse_qs, urlparse

from django.core import mail
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.accounts.models import MentorProfile, StudentProfile, User
from apps.mentoring.models import AuditLog, Notification


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class AccountsAPITests(APITestCase):
    password = 'Orchid!River4729'

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user('admin@iitm.ac.in', cls.password, role='ADMIN', is_staff=True)
        cls.student = User.objects.create_user('student@iitm.ac.in', cls.password, role='STUDENT')
        cls.profile = StudentProfile.objects.create(
            user=cls.student, iitm_roll_number='23F100001', level='DEGREE',
            courses=['Software Engineering'], cgpa='8.50')
        cls.mentor = User.objects.create_user('mentor@example.com', role='MENTOR', first_name='Alumni')
        cls.mentor_profile = MentorProfile.objects.create(
            user=cls.mentor, alumni_roll_number='19F100001', graduation_year=2023,
            domain='Software', specialty='Backend', current_role='Engineer',
            skills=['Python'], is_verified=True)

    def request(self, method, path, data=None, user=None):
        self.client.force_authenticate(user=user)
        return getattr(self.client, method)('/api/v1/' + path, data=data, format='json')

    def registration(self, **changes):
        return dict(email='new@ds.study.iitm.ac.in', password=self.password,
                    first_name='Test', last_name='Student', iitm_roll_number='23F100002',
                    level='DEGREE', courses=['Software Engineering'], cgpa='8.00', **changes)

    def invitation(self):
        response = self.request('post', f'admin/mentors/{self.mentor.pk}/invite/', {}, self.admin)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('token', response.data)
        self.assertEqual(mail.outbox[-1].to, [self.mentor.email])
        link = mail.outbox[-1].body.split('Activate your account: ', 1)[1].strip()
        return {key: values[0] for key, values in parse_qs(urlparse(link).query).items()}

    def test_registration_creates_pending_student_and_hashes_password(self):
        response = self.request('post', 'auth/register/', self.registration())
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(pk=response.data['id'])
        self.assertEqual(user.role, 'STUDENT')
        self.assertEqual(user.student_profile.approval_status, 'PENDING')
        self.assertTrue(user.check_password(self.password))
        self.assertNotIn('password', response.data)

    def test_registration_rejects_invalid_inputs_without_creating_users(self):
        for field, value in [('email', 'outsider@example.com'), ('level', 'DIPLOMA'),
                             ('courses', []), ('cgpa', '10.01'), ('password', '12345678')]:
            with self.subTest(field=field):
                payload = self.registration()
                payload[field] = value
                count = User.objects.count()
                response = self.request('post', 'auth/register/', payload)
                self.assertEqual(response.status_code, 400, response.data)
                self.assertIn(field, response.data)
                self.assertEqual(User.objects.count(), count)

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        payload = self.registration()
        payload['email'] = self.student.email.upper()
        self.assertEqual(self.request('post', 'auth/register/', payload).status_code, 400)

    def test_jwt_login_authenticated_me_and_refresh(self):
        response = self.request('post', 'auth/token/', {'email': self.student.email, 'password': self.password})
        self.assertEqual(response.status_code, 200, response.data)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + response.data['access'])
        me = self.client.get('/api/v1/auth/me/')
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data['id'], self.student.pk)
        self.assertNotIn('password', me.data)
        self.client.credentials()
        refresh = self.request('post', 'auth/token/refresh/', {'refresh': response.data['refresh']})
        self.assertEqual(refresh.status_code, 200)
        self.assertIn('access', refresh.data)

    def test_login_rejects_wrong_password(self):
        response = self.request('post', 'auth/token/', {'email': self.student.email, 'password': 'wrong'})
        self.assertEqual(response.status_code, 401)

    def test_protected_routes_reject_anonymous_requests(self):
        routes = [('get', 'auth/me/'), ('get', 'students/me/'), ('get', 'admin/students/'),
                  ('post', f'admin/students/{self.student.pk}/review/'), ('get', 'admin/mentors/'),
                  ('post', f'admin/mentors/{self.mentor.pk}/verify/'), ('patch', 'mentor/availability/'),
                  ('post', f'admin/mentors/{self.mentor.pk}/invite/'), ('post', 'admin/mentors/import/'),
                  ('patch', f'admin/mentors/{self.mentor.pk}/'), ('get', 'mentor/profile/'),
                  ('get', 'mentors/'), ('get', 'mentors/facets/'), ('get', f'mentors/{self.mentor.pk}/')]
        for method, path in routes:
            with self.subTest(path=path):
                self.assertEqual(self.request(method, path, {}).status_code, 403)

    def test_admin_routes_reject_student(self):
        for method, path in [('get', 'admin/students/'), ('post', f'admin/students/{self.student.pk}/review/'),
                             ('post', 'admin/mentors/'), ('post', f'admin/mentors/{self.mentor.pk}/verify/'),
                             ('post', f'admin/mentors/{self.mentor.pk}/invite/'),
                             ('patch', f'admin/mentors/{self.mentor.pk}/'), ('post', 'admin/mentors/import/')]:
            with self.subTest(path=path):
                self.assertEqual(self.request(method, path, {}, self.student).status_code, 403)

    def test_student_reads_and_edits_own_profile(self):
        self.assertEqual(self.request('get', 'students/me/', user=self.student).status_code, 200)
        response = self.request('patch', 'students/me/', {'courses': ['Databases']}, self.student)
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.courses, ['Databases'])

    def test_approved_student_records_are_locked(self):
        self.profile.approval_status = 'APPROVED'
        self.profile.save()
        response = self.request('patch', 'students/me/', {'cgpa': '9.00'}, self.student)
        self.assertEqual(response.status_code, 403)
        self.profile.refresh_from_db()
        self.assertEqual(str(self.profile.cgpa), '8.50')

    def test_rejected_student_edit_resets_review(self):
        self.profile.approval_status = 'REJECTED'
        self.profile.rejection_reason = 'Incomplete records'
        self.profile.save()
        response = self.request('patch', 'students/me/', {'courses': ['Databases']}, self.student)
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.approval_status, 'PENDING')
        self.assertEqual(self.profile.rejection_reason, '')
        self.assertIsNone(self.profile.approved_by)

    def test_nonstudent_cannot_access_student_profile(self):
        self.assertEqual(self.request('get', 'students/me/', user=self.mentor).status_code, 403)

    def test_admin_student_list_search_and_status_filter(self):
        response = self.request('get', 'admin/students/?search=23F100001', user=self.admin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['user_id'], self.student.pk)
        response = self.request('get', 'admin/students/?status=APPROVED', user=self.admin)
        self.assertEqual(response.data['count'], 0)

    def test_student_approval_persists_audit_and_notification(self):
        response = self.request('post', f'admin/students/{self.student.pk}/review/',
                                {'decision': 'APPROVED', 'academic_verified': True}, self.admin)
        self.assertEqual(response.status_code, 200, response.data)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.approval_status, 'APPROVED')
        self.assertEqual(self.profile.approved_by, self.admin)
        self.assertIsNotNone(self.profile.approved_at)
        self.assertTrue(AuditLog.objects.filter(action='STUDENT_REVIEW', actor=self.admin).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.student).exists())

    def test_student_review_rejects_missing_verification_or_reason(self):
        for payload in [{'decision': 'APPROVED'}, {'decision': 'REJECTED'}, {'decision': 'INVALID'}]:
            with self.subTest(payload=payload):
                response = self.request('post', f'admin/students/{self.student.pk}/review/', payload, self.admin)
                self.assertEqual(response.status_code, 400)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.approval_status, 'PENDING')
        self.assertFalse(AuditLog.objects.exists())

    def test_approval_rejects_incomplete_academic_records(self):
        self.profile.cgpa = None
        self.profile.save()
        response = self.request('post', f'admin/students/{self.student.pk}/review/',
                                {'decision': 'APPROVED', 'academic_verified': True}, self.admin)
        self.assertEqual(response.status_code, 400)

    def test_student_rejection_records_reason(self):
        response = self.request('post', f'admin/students/{self.student.pk}/review/',
                                {'decision': 'REJECTED', 'reason': 'Records do not match'}, self.admin)
        self.assertEqual(response.status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.approval_status, 'REJECTED')
        self.assertEqual(self.profile.rejection_reason, 'Records do not match')

    def test_admin_creates_unverified_mentor_with_unusable_password(self):
        payload = dict(email='newmentor@example.com', first_name='New', last_name='Mentor',
                       alumni_roll_number='19F100002', graduation_year=2023, domain='Software',
                       specialty='Backend', current_role='Engineer', experience_years=3)
        response = self.request('post', 'admin/mentors/', payload, self.admin)
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(pk=response.data['id'])
        self.assertEqual(user.role, 'MENTOR')
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.mentor_profile.is_verified)
        self.assertTrue(AuditLog.objects.filter(action='MENTOR_ADDED').exists())
        self.assertEqual(self.request('post', 'admin/mentors/', payload, self.admin).status_code, 400)

    def test_admin_mentor_list_filters(self):
        response = self.request('get', 'admin/mentors/?verified=true&search=Backend', user=self.admin)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(self.request('get', 'admin/mentors/?verified=false', user=self.admin).data['count'], 0)

    def test_mentor_verification_requires_alumni_records(self):
        self.mentor_profile.is_verified = False
        self.mentor_profile.graduation_year = None
        self.mentor_profile.save()
        path = f'admin/mentors/{self.mentor.pk}/verify/'
        self.assertEqual(self.request('post', path, {}, self.admin).status_code, 400)
        self.mentor_profile.graduation_year = 2023
        self.mentor_profile.save()
        self.assertEqual(self.request('post', path, {}, self.admin).status_code, 200)
        self.mentor_profile.refresh_from_db()
        self.assertTrue(self.mentor_profile.is_verified)
        self.assertTrue(AuditLog.objects.filter(action='MENTOR_VERIFIED').exists())

    def test_activation_weak_password_returns_validation_error_not_server_error(self):
        payload = dict(self.invitation(), password='123')
        self.client.raise_request_exception = False
        response = self.request('post', 'auth/mentor/activate/', payload)
        self.assertEqual(response.status_code, 400, 'Weak passwords must return HTTP 400, not an unhandled server error')
        self.mentor.refresh_from_db()
        self.assertFalse(self.mentor.has_usable_password())

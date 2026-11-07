from apps.accounts.models import User, MentorProfile
from apps.mentoring.factories import SangamAPITestCase, make_mentor, make_student, PASSWORD


class AuthAndRoleTests(SangamAPITestCase):
    def test_registration_requires_iitm_email_and_starts_pending(self):
        payload = {'email': 'someone@gmail.com', 'password': 'Str0ng!Passw0rd', 'first_name': 'A', 'last_name': 'B',
                   'iitm_roll_number': '22f1', 'level': 'DEGREE', 'courses': ['Python']}
        self.client.force_authenticate(user=None)
        bad = self.client.post('/api/v1/auth/register/', payload, format='json')
        self.assertEqual(bad.status_code, 400)
        self.assertIn('email', bad.data)          # original field-error contract preserved
        self.assertIn('detail', bad.data)         # standardized message
        self.assertEqual(bad.data['code'], 'invalid')
        ok = self.client.post('/api/v1/auth/register/', {**payload, 'email': 'new@ds.study.iitm.ac.in'}, format='json')
        self.assertEqual(ok.status_code, 201, ok.data)
        self.assertEqual(ok.data['approval_status'], 'PENDING')

    def test_token_login_and_me_effective_role(self):
        token = self.client.post('/api/v1/auth/token/', {'email': self.student.email, 'password': PASSWORD}, format='json')
        self.assertEqual(token.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.data["access"]}')
        me = self.client.get('/api/v1/auth/me/')
        self.assertEqual(me.data['effective_role'], 'STUDENT')
        self.assertFalse(me.data['is_iic'])
        self.assertEqual(me.data['student_profile']['approval_status'], 'APPROVED')

    def test_admin_role_without_staff_flag_is_not_iic(self):
        fake = User.objects.create_user(email='fake@example.org', password=PASSWORD, role='ADMIN')
        me = self.as_user(fake).get('/api/v1/auth/me/')
        self.assertIsNone(me.data['effective_role'])
        self.assertEqual(self.client.get('/api/v1/admin/students/').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/admin/insights/').status_code, 403)

    def test_mentor_me_includes_profile_and_calendar_status(self):
        me = self.as_user(self.mentor).get('/api/v1/auth/me/')
        self.assertEqual(me.data['effective_role'], 'MENTOR')
        self.assertEqual(me.data['mentor_profile']['domain'], 'Data & ML')
        self.assertEqual(me.data['calendar']['status'], 'DISCONNECTED')


class MentorDirectoryTests(SangamAPITestCase):
    def setUp(self):
        super().setUp()
        make_mentor('hidden@example.org', verified=True, discoverable=False, alumni_roll_number='AL2')
        make_mentor('unverified@example.org', verified=False, alumni_roll_number='AL3')
        make_mentor('sde@example.org', domain='Software', specialty='Backend systems', experience_years=8,
                    skills=['Java', 'System design'], alumni_roll_number='AL4', first_name='Priya')

    def test_only_verified_published_profiles_without_private_fields(self):
        response = self.as_user(self.student).get('/api/v1/mentors/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        card = response.data['results'][0]
        for private in ('email', 'alumni_roll_number', 'phone'):
            self.assertNotIn(private, card)
        self.assertNotIn('@', str(response.data))

    def test_filters(self):
        c = self.as_user(self.student)
        self.assertEqual(c.get('/api/v1/mentors/?domain=software').data['count'], 1)
        self.assertEqual(c.get('/api/v1/mentors/?min_experience=5').data['count'], 1)
        self.assertEqual(c.get('/api/v1/mentors/?skill=java').data['count'], 1)
        self.assertEqual(c.get('/api/v1/mentors/?search=priya').data['count'], 1)
        self.assertEqual(c.get('/api/v1/mentors/?career_path=job').data['count'], 2)
        MentorProfile.objects.filter(user=self.mentor).update(is_available=False)
        self.assertEqual(c.get('/api/v1/mentors/?available=true').data['count'], 1)
        facets = c.get('/api/v1/mentors/facets/').data
        self.assertEqual(facets['domains'], ['Data & ML', 'Software'])

    def test_directory_access_is_role_restricted(self):
        pending = make_student('pending@study.iitm.ac.in', approved=False, roll='21f2')
        self.assertEqual(self.as_user(pending).get('/api/v1/mentors/').status_code, 403)
        self.assertEqual(self.as_user(self.mentor).get('/api/v1/mentors/').status_code, 403)
        self.assertEqual(self.as_user(self.iic).get('/api/v1/mentors/').status_code, 200)
        hidden = User.objects.get(email='hidden@example.org')
        self.assertEqual(self.as_user(self.student).get(f'/api/v1/mentors/{hidden.pk}/').status_code, 404)


class MentorProfileTests(SangamAPITestCase):
    def test_mentor_cannot_self_verify_or_publish(self):
        c = self.as_user(make_mentor('new@example.org', verified=False, alumni_roll_number='AL9'))
        r = c.patch('/api/v1/mentor/profile/', {'is_verified': True, 'is_discoverable': True, 'bio': 'Analytics lead',
                                                'skills': ['SQL', 'sql', 'Tableau']}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertFalse(r.data['is_verified'])
        self.assertFalse(r.data['is_discoverable'])
        self.assertEqual(r.data['skills'], ['SQL', 'Tableau'])

    def test_linkedin_url_validation(self):
        c = self.as_user(self.mentor)
        self.assertEqual(c.patch('/api/v1/mentor/profile/', {'linkedin_url': 'https://evil.example/in/x'}, format='json').status_code, 400)
        ok = c.patch('/api/v1/mentor/profile/', {'linkedin_url': 'https://www.linkedin.com/in/arjun'}, format='json')
        self.assertEqual(ok.status_code, 200)

    def test_iic_verification_and_publication(self):
        mentor = make_mentor('fresh@example.org', verified=False, alumni_roll_number='AL7')
        c = self.as_user(self.iic)
        self.assertEqual(c.patch(f'/api/v1/admin/mentors/{mentor.pk}/', {'is_discoverable': True}, format='json').status_code, 400)
        verified = c.post(f'/api/v1/admin/mentors/{mentor.pk}/verify/', {}, format='json')
        self.assertEqual(verified.status_code, 200)
        self.assertTrue(verified.data['is_discoverable'])
        hide = c.patch(f'/api/v1/admin/mentors/{mentor.pk}/', {'is_discoverable': False}, format='json')
        self.assertFalse(hide.data['is_discoverable'])
        listing = c.get('/api/v1/admin/mentors/?verified=true&page=1')
        self.assertIn('results', listing.data)
        self.assertEqual(self.as_user(self.student).post(f'/api/v1/admin/mentors/{mentor.pk}/verify/').status_code, 403)


class ProjectReportTests(SangamAPITestCase):
    def test_project_report_renders_docs_and_endpoint_index(self):
        response = self.client.get('/project-report/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Live endpoint index')
        self.assertContains(response, '/api/v1/mentors/')
        self.assertContains(response, 'Gap analysis')

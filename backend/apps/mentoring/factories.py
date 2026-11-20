"""Small test-data builders shared by the backend test suites (not used at runtime)."""
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from apps.accounts.models import User, StudentProfile, MentorProfile

PASSWORD = 'GoodPass123!'
PROBLEM = ('I want structured guidance on project portfolio development and preparing for technical data '
           'science interviews with specific measurable milestones.')


def make_student(email='student@study.iitm.ac.in', approved=True, **extra):
    user = User.objects.create_user(email=email, password=PASSWORD, role='STUDENT', first_name='Asha', last_name='Rao')
    StudentProfile.objects.create(user=user, iitm_roll_number=extra.get('roll', '21f1000001'), level='DEGREE',
                                  courses=['Python'], cgpa='8.0', approval_status='APPROVED' if approved else 'PENDING')
    return user


def make_mentor(email='alumni@example.org', verified=True, discoverable=True, **profile):
    user = User.objects.create_user(email=email, password=PASSWORD, role='MENTOR',
                                    first_name=profile.pop('first_name', 'Arjun'), last_name=profile.pop('last_name', 'Kumar'))
    defaults = dict(alumni_roll_number='AL1', graduation_year=2022, domain='Data & ML', specialty='Machine learning',
                    current_role='Data scientist', company='Fractal', experience_years=3, career_path='Job',
                    skills=['Python', 'SQL'], is_verified=verified, is_discoverable=discoverable and verified)
    defaults.update(profile)
    MentorProfile.objects.create(user=user, **defaults)
    return user


def make_iic(email='iic@example.org'):
    return User.objects.create_superuser(email=email, password=PASSWORD)


@override_settings(SANGAM_OLLAMA_ENABLED=False)
class SangamAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = make_student()
        self.mentor = make_mentor()
        self.iic = make_iic()
        self.request_data = {'pathway': 'JOB', 'domain': 'Data & ML', 'background': 'ML student', 'problem_statement': PROBLEM}

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        return self.client

    def submit_request(self, **overrides):
        response = self.as_user(self.student).post('/api/v1/requests/', {**self.request_data, **overrides}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def activate_pair(self, request_id=None, mentor=None):
        """Drive the full IIC workflow to an active mentorship and return its id."""
        mentor = mentor or self.mentor
        request_id = request_id or self.submit_request()['id']
        check = self.as_user(self.iic).post(f'/api/v1/admin/requests/{request_id}/availability/', {'mentor_id': mentor.pk}, format='json')
        self.assertEqual(check.status_code, 201, check.data)
        confirmed = self.as_user(mentor).post(f'/api/v1/availability/{check.data["id"]}/respond/', {'decision': 'CONFIRMED'}, format='json')
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        pair = self.as_user(self.iic).post(f'/api/v1/admin/availability/{check.data["id"]}/approve/')
        self.assertEqual(pair.status_code, 201, pair.data)
        return pair.data['id']

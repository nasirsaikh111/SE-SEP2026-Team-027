from datetime import date, timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User, StudentProfile, MentorProfile
from .models import MentoringRequest, Mentorship, Feedback, Meeting

class SangamWorkflowTests(TestCase):
    def setUp(self):
        self.student=User.objects.create_user(email='student@study.iitm.ac.in',password='GoodPass123!',role='STUDENT')
        StudentProfile.objects.create(user=self.student,iitm_roll_number='SAMPLE',level='DEGREE',courses=['Python'],cgpa='8.0',approval_status='APPROVED')
        self.mentor=User.objects.create_user(email='alumni@example.org',password='GoodPass123!',role='MENTOR')
        MentorProfile.objects.create(user=self.mentor,alumni_roll_number='AL1',graduation_year=2022,
            domain='Data & ML',specialty='Machine learning',current_role='Data scientist',experience_years=3,is_verified=True)
        self.iic=User.objects.create_superuser(email='iic@example.org',password='GoodPass123!')
        self.client=APIClient()
        self.data={'pathway':'JOB','domain':'Data & ML','background':'ML student',
            'problem_statement':'I want structured guidance on project portfolio development and preparing for technical data science interviews with specific measurable milestones.'}

    def test_student_request_and_one_open_limit(self):
        self.client.force_authenticate(user=self.student)
        first=self.client.post('/api/v1/requests/',self.data,format='json')
        self.assertEqual(first.status_code,201,first.data)
        self.assertEqual(self.client.post('/api/v1/requests/',self.data,format='json').status_code,400)

    def test_only_iic_can_recommend_and_approve(self):
        r=MentoringRequest.objects.create(student=self.student,**self.data)
        self.client.force_authenticate(user=self.student)
        self.assertEqual(self.client.get(f'/api/v1/admin/requests/{r.pk}/suggestions/').status_code,403)
        self.client.force_authenticate(user=self.iic)
        suggestions=self.client.get(f'/api/v1/admin/requests/{r.pk}/suggestions/')
        self.assertEqual(suggestions.status_code,200,suggestions.data)
        self.assertEqual(suggestions.data['candidates'][0]['mentor_id'],self.mentor.pk)
        check_response=self.client.post(f'/api/v1/admin/requests/{r.pk}/availability/',{'mentor_id':self.mentor.pk},format='json')
        self.assertEqual(check_response.status_code,201,check_response.data)
        check_id=check_response.data['id']
        self.assertEqual(self.client.post(f'/api/v1/admin/availability/{check_id}/approve/').status_code,400)
        self.client.force_authenticate(user=self.mentor)
        response=self.client.post(f'/api/v1/availability/{check_id}/respond/',{'decision':'CONFIRMED'},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.client.force_authenticate(user=self.iic)
        approved=self.client.post(f'/api/v1/admin/availability/{check_id}/approve/')
        self.assertEqual(approved.status_code,201,approved.data)
        self.assertEqual(Mentorship.objects.filter(status='ACTIVE').count(),1)
        self.assertEqual(self.client.post(f'/api/v1/admin/availability/{check_id}/approve/').status_code,400)

    def test_private_feedback_and_no_chat_field(self):
        r=MentoringRequest.objects.create(student=self.student,**self.data)
        from .models import AvailabilityCheck
        check=AvailabilityCheck.objects.create(request=r,mentor=self.mentor,status='USED')
        pair=Mentorship.objects.create(request=r,availability_check=check,student=self.student,mentor=self.mentor,approved_by=self.iic)
        Feedback.objects.create(mentorship=pair,author=self.student,kind='GENERAL',text='Private IIC note')
        self.client.force_authenticate(user=self.mentor)
        response=self.client.get(f'/api/v1/mentorships/{pair.pk}/feedback/')
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.data),0)
        self.assertNotIn('conversation', [field.name for field in Meeting._meta.fields])
        self.assertNotIn('rating', [field.name for field in Feedback._meta.fields])

    def test_mentor_does_not_see_student_contact_before_iic_approval(self):
        r=MentoringRequest.objects.create(student=self.student,**self.data)
        self.client.force_authenticate(user=self.iic)
        c=self.client.post(f'/api/v1/admin/requests/{r.pk}/availability/',{'mentor_id':self.mentor.pk},format='json')
        self.assertEqual(c.status_code,201)
        self.client.force_authenticate(user=self.mentor)
        response=self.client.get(f'/api/v1/availability/{c.data["id"]}/')
        self.assertEqual(response.status_code,200)
        self.assertNotIn('email',str(response.data).lower())

    def test_chatbot_rate_and_no_db_transcript(self):
        from apps.assistant_ai.models import KnowledgeArticle
        KnowledgeArticle.objects.create(title='Requesting a mentor',content='Submit a pathway, domain and specific question.',is_published=True)
        self.client.force_authenticate(user=self.student)
        response=self.client.post('/api/v1/ai/chat/',{'message':'How do I request a mentor?'},format='json')
        self.assertEqual(response.status_code,200,response.data)
        self.assertFalse(response.data['message_stored'])

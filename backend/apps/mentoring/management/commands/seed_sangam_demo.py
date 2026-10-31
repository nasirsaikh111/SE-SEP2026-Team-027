"""Local development only: create sample accounts so every screen can be exercised.

Refuses to run unless DJANGO_DEBUG is true. Records go through the real workflow
services, so the audit trail and status history are populated exactly as in use.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.accounts.models import User, StudentProfile, MentorProfile
from apps.assistant_ai.models import KnowledgeArticle
from apps.mentoring import services
from apps.mentoring.models import MentoringRequest

PASSWORD = 'SangamDemo!2026'

MENTORS = [
    ('arjun.k@alumni.example.org', 'Arjun', 'Kumar', 'Data & ML', 'Machine learning engineering', 'Senior Data Scientist', 'Fractal Analytics',
     'Job', 6, ['Python', 'Machine learning', 'SQL', 'Mock interviews'], 'https://www.linkedin.com/in/example-arjun'),
    ('neha.s@alumni.example.org', 'Neha', 'Sharma', 'Analytics', 'Product analytics', 'Analytics Lead', 'Swiggy',
     'Job', 5, ['SQL', 'Tableau', 'Experimentation'], ''),
    ('priya.n@alumni.example.org', 'Priya', 'Nair', 'Software', 'Backend systems', 'Software Development Engineer', 'Amazon',
     'Job', 3, ['Java', 'System design', 'DSA'], 'https://www.linkedin.com/in/example-priya'),
    ('rohan.s@alumni.example.org', 'Rohan', 'Singh', 'Higher Studies', 'MS admissions in Europe', 'MS Researcher', 'TU Munich',
     'Higher studies', 2, ['SOP writing', 'Research proposals', 'GRE'], ''),
]


class Command(BaseCommand):
    help = 'Create demo IIC, student and mentor accounts (DEBUG only).'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('Refusing to seed demo data when DJANGO_DEBUG is false.')
        iic, created = User.objects.get_or_create(email='iic.admin@iitm.ac.in', defaults={
            'role': 'ADMIN', 'is_staff': True, 'is_superuser': True, 'first_name': 'IIC', 'last_name': 'Admin'})
        if created:
            iic.set_password(PASSWORD); iic.save()
        mentors = []
        for email, first, last, domain, specialty, role, company, path, years, skills, linkedin in MENTORS:
            user, created = User.objects.get_or_create(email=email, defaults={'role': 'MENTOR', 'first_name': first, 'last_name': last})
            if created:
                user.set_password(PASSWORD); user.save()
                MentorProfile.objects.create(user=user, alumni_roll_number=f'AL{user.pk:04d}', graduation_year=2022, domain=domain,
                                             specialty=specialty, current_role=role, company=company, career_path=path,
                                             experience_years=years, skills=skills, linkedin_url=linkedin, is_verified=True,
                                             is_discoverable=True, verified_by=iic, verified_at=timezone.now())
            mentors.append(user)
        students = []
        for i, (first, approved) in enumerate([('Hemant', True), ('Asha', True), ('Kiran', False)], start=1):
            email = f'{first.lower()}@ds.study.iitm.ac.in'
            user, created = User.objects.get_or_create(email=email, defaults={'role': 'STUDENT', 'first_name': first, 'last_name': 'Demo'})
            if created:
                user.set_password(PASSWORD); user.save()
                StudentProfile.objects.create(user=user, iitm_roll_number=f'21f10000{i}', level='DEGREE', courses=['Python', 'MLF'],
                                              cgpa='8.10', approval_status='APPROVED' if approved else 'PENDING',
                                              approved_by=iic if approved else None, approved_at=timezone.now() if approved else None)
            students.append(user)
        if not MentoringRequest.objects.filter(student=students[0]).exists():
            req = services.create_request(student=students[0], data={
                'pathway': 'JOB', 'domain': 'Data & ML', 'background': 'Degree student, completed MLF and MLT.',
                'preferred_mentor': mentors[0],
                'problem_statement': 'I want guidance on building a data science portfolio and preparing for analyst interviews '
                                     'over the next two months, including which projects demonstrate the right skills.'})
            check = services.send_availability(request_id=req.pk, mentor_id=mentors[0].pk, actor=iic)
            services.respond_availability(check_id=check.pk, mentor=mentors[0], decision='CONFIRMED')
            services.approve_match(check_id=check.pk, actor=iic)
        if not MentoringRequest.objects.filter(student=students[1]).exists():
            services.create_request(student=students[1], data={
                'pathway': 'HIGHER_STUDIES', 'domain': 'Higher Studies', 'background': 'Interested in MS programmes in Europe.',
                'problem_statement': 'I need help shortlisting MS programmes in Germany and structuring my statement of purpose '
                                     'before the application deadline on 15 December.'})
        if not KnowledgeArticle.objects.exists():
            KnowledgeArticle.objects.create(title='How mentor matching works', audience='ALL', is_published=True,
                content='Submit one request with your pathway, domain and a specific question of at least 80 characters. '
                        'IIC reviews it, confirms a mentor\'s availability within 7 days and approves the final pairing. '
                        'You may name a preferred mentor from Discover Mentors, but IIC makes the final decision.')
        self.stdout.write(self.style.SUCCESS(f'Demo data ready. Password for every demo account: {PASSWORD}'))
        for email in ['iic.admin@iitm.ac.in'] + [m[0] for m in MENTORS] + [s.email for s in students]:
            self.stdout.write(f'  {email}')

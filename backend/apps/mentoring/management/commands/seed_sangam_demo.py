"""Seed script for production-grade demo data across all Sangam entities.

Populates:
- 8 Alumni Mentors (Fractal, Swiggy, Amazon, TU Munich, Google, MSFT Research, Stanford, Flipkart)
- 6 Students (Degree & Diploma levels with various approval states)
- Active Mentorships (Hemant + Arjun, Asha + Priya) with Goals, Meetings, Google Meet links & Feedback
- Requests Lifecycle (SUBMITTED, UNDER_REVIEW, WAITING/AWAITING_MENTOR, MATCHED)
- 4 Published Knowledge Base Articles
- Complete Audit Log history
"""
from datetime import date, timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User, StudentProfile, MentorProfile
from apps.assistant_ai.models import KnowledgeArticle
from apps.mentoring import services
from apps.mentoring.models import (
    MentoringRequest, AvailabilityCheck, Mentorship, Goal, Meeting,
    Feedback, Outcome, AuditLog, MeetingCalendarEvent
)

PASSWORD = 'SangamDemo!2026'

MENTORS = [
    ('arjun.k@alumni.example.org', 'Arjun', 'Kumar', 'Data & ML', 'Machine learning engineering', 'Senior Data Scientist', 'Fractal Analytics',
     'Job', 6, ['Python', 'Machine learning', 'SQL', 'Mock interviews'], 'https://www.linkedin.com/in/example-arjun'),
    ('neha.s@alumni.example.org', 'Neha', 'Sharma', 'Analytics', 'Product analytics', 'Analytics Lead', 'Swiggy',
     'Job', 5, ['SQL', 'Tableau', 'Experimentation'], 'https://www.linkedin.com/in/example-neha'),
    ('priya.n@alumni.example.org', 'Priya', 'Nair', 'Software', 'Backend systems', 'Software Development Engineer', 'Amazon',
     'Job', 3, ['Java', 'System design', 'DSA'], 'https://www.linkedin.com/in/example-priya'),
    ('rohan.s@alumni.example.org', 'Rohan', 'Singh', 'Higher Studies', 'MS admissions in Europe', 'MS Researcher', 'TU Munich',
     'Higher studies', 2, ['SOP writing', 'Research proposals', 'GRE'], 'https://www.linkedin.com/in/example-rohan'),
    ('vikram.r@alumni.example.org', 'Vikram', 'Rao', 'Software', 'Distributed systems & architecture', 'Staff Engineer', 'Google',
     'Job', 8, ['React', 'Go', 'Distributed Systems', 'Architecture'], 'https://www.linkedin.com/in/example-vikram'),
    ('ananya.m@alumni.example.org', 'Ananya', 'Mishra', 'Data & ML', 'Computer Vision & LLMs', 'AI Research Scientist', 'Microsoft Research',
     'Higher studies', 4, ['PyTorch', 'Transformers', 'GenAI', 'Papers'], 'https://www.linkedin.com/in/example-ananya'),
    ('siddharth.p@alumni.example.org', 'Siddharth', 'Patel', 'Higher Studies', 'Ph.D. & Top US Universities', 'Ph.D. Scholar', 'Stanford University',
     'Higher studies', 3, ['Admissions', 'Faculty Outreach', 'Publications'], 'https://www.linkedin.com/in/example-siddharth'),
    ('tanvi.g@alumni.example.org', 'Tanvi', 'Gupta', 'Analytics', 'Business Intelligence & Strategy', 'Product Manager', 'Flipkart',
     'Job', 5, ['Product Roadmaps', 'Metrics', 'SQL', 'Strategy'], 'https://www.linkedin.com/in/example-tanvi'),
]

STUDENTS = [
    ('hemant@ds.study.iitm.ac.in', 'Hemant', 'Dhayal', '21f100001', 'DEGREE', '8.45', ['Python', 'MLF', 'DL', 'SE'], 'APPROVED'),
    ('asha@ds.study.iitm.ac.in', 'Asha', 'Sharma', '21f100002', 'DEGREE', '8.90', ['Java', 'DSA', 'DBMS', 'System Design'], 'APPROVED'),
    ('kiran@ds.study.iitm.ac.in', 'Kiran', 'Verma', '22f100003', 'DIPLOMA', '7.80', ['Programming Concepts', 'DBMS Basics'], 'PENDING'),
    ('rahul@ds.study.iitm.ac.in', 'Rahul', 'Mehta', '21f100004', 'DEGREE', '8.15', ['Mathematics for Data Science', 'MLT'], 'APPROVED'),
    ('sneha@ds.study.iitm.ac.in', 'Sneha', 'Reddy', '21f100005', 'DEGREE', '9.10', ['Deep Learning', 'Reinforcement Learning', 'NLP'], 'APPROVED'),
    ('aditya@ds.study.iitm.ac.in', 'Aditya', 'Nair', '22f100006', 'DIPLOMA', '7.40', ['Business Analytics', 'SQL Tools'], 'APPROVED'),
]

KNOWLEDGE_ARTICLES = [
    ('How Mentor Matching Works at Sangam', 'ALL',
     'Submit one request detailing your domain, background, and a specific dilemma of at least 80 characters. '
     'IIC reviews it, verifies mentor capacity, and confirms availability within 7 days before pairing. '
     'You may name a preferred mentor from Discover Mentors, but IIC makes the final decision.'),
    ('Guidelines for Mentoring Sessions & Privacy', 'ALL',
     'To safeguard student and alumni trust, Sangam NEVER stores conversation transcripts or chat logs. '
     'Meetings are tracked by session date, duration (minutes), and attendance status only. '
     'All communication happens through official institutional email IDs and Google Meet links.'),
    ('Pathway Compass: Deciding between Job vs Higher Studies', 'STUDENT',
     'Choosing between immediate campus placement and graduate studies is a major transition for IITM BS students. '
     'This guide lays out a decision matrix based on current CGPA, coursework completion level (Diploma vs Degree), '
     'financial goals, and timelines for GRE/GATE vs Placement Drives.'),
    ('Mentor Best Practices: Setting Goals & Giving Actionable Feedback', 'MENTOR',
     'Volunteer mentoring is most effective when bounded by concrete, achievable objectives. '
     'We recommend agreeing on 2 to 3 goals during Session 1 (e.g. resume refactoring, mock interview, portfolio review) '
     'and wrapping up with a constructive closing assessment.'),
]


class Command(BaseCommand):
    help = 'Create full realistic production demo data (Admin, Mentors, Students, Mentorships, KB)'

    def handle(self, *args, **options):
        # 1. Admin account
        iic, created = User.objects.get_or_create(
            email='iic.admin@iitm.ac.in',
            defaults={'role': 'ADMIN', 'is_staff': True, 'is_superuser': True, 'first_name': 'IIC', 'last_name': 'Admin'}
        )
        if created:
            iic.set_password(PASSWORD)
            iic.save()

        # 2. Alumni Mentors (8 mentors)
        mentors_dict = {}
        for email, first, last, domain, specialty, role, company, path, years, skills, linkedin in MENTORS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'role': 'MENTOR', 'first_name': first, 'last_name': last}
            )
            if created:
                user.set_password(PASSWORD)
                user.save()
                MentorProfile.objects.create(
                    user=user,
                    alumni_roll_number=f'AL{user.pk:04d}',
                    graduation_year=2020 + (user.pk % 4),
                    domain=domain,
                    specialty=specialty,
                    current_role=role,
                    company=company,
                    career_path=path,
                    experience_years=years,
                    skills=skills,
                    linkedin_url=linkedin,
                    is_verified=True,
                    is_available=True,
                    is_discoverable=True,
                    verified_by=iic,
                    verified_at=timezone.now()
                )
            mentors_dict[email] = user

        # 3. Students (6 students)
        students_dict = {}
        for email, first, last, roll, level, cgpa, courses, status in STUDENTS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'role': 'STUDENT', 'first_name': first, 'last_name': last}
            )
            if created:
                user.set_password(PASSWORD)
                user.save()
                StudentProfile.objects.create(
                    user=user,
                    iitm_roll_number=roll,
                    level=level,
                    courses=courses,
                    cgpa=cgpa,
                    approval_status=status,
                    approved_by=iic if status == 'APPROVED' else None,
                    approved_at=timezone.now() if status == 'APPROVED' else None
                )
            students_dict[email] = user

        # 4. Mentoring Requests & Active Mentorships
        # Pair 1: Hemant + Arjun (ACTIVE MATCHED)
        hemant = students_dict['hemant@ds.study.iitm.ac.in']
        arjun = mentors_dict['arjun.k@alumni.example.org']
        if not MentoringRequest.objects.filter(student=hemant).exists():
            req_h = services.create_request(student=hemant, data={
                'pathway': 'JOB',
                'domain': 'Data & ML',
                'background': 'Degree student, completed MLF, MLT, and DL.',
                'preferred_mentor': arjun,
                'problem_statement': 'I want guidance on building a production-grade data science portfolio and preparing for '
                                     'analyst & data science technical rounds over the next two months.'
            })
            check_h = services.send_availability(request_id=req_h.pk, mentor_id=arjun.pk, actor=iic)
            services.respond_availability(check_id=check_h.pk, mentor=arjun, decision='CONFIRMED')
            pair_h = services.approve_match(check_id=check_h.pk, actor=iic)

            # Goals for Hemant + Arjun
            Goal.objects.get_or_create(mentorship=pair_h, slot=1, defaults={
                'title': 'Pick target role & analyze Job Descriptions',
                'target_date': date(2026, 10, 15),
                'completed': True,
                'completed_at': timezone.now() - timedelta(days=20)
            })
            Goal.objects.get_or_create(mentorship=pair_h, slot=2, defaults={
                'title': 'Audit existing GitHub portfolio projects & SQL schema',
                'target_date': date(2026, 10, 22),
                'completed': True,
                'completed_at': timezone.now() - timedelta(days=14)
            })
            Goal.objects.get_or_create(mentorship=pair_h, slot=3, defaults={
                'title': 'Conduct company-specific mock technical interview',
                'target_date': date(2026, 11, 12),
                'completed': False
            })

            # Sessions for Hemant + Arjun
            m1 = Meeting.objects.create(
                mentorship=pair_h,
                session_date=date(2026, 10, 17),
                duration_minutes=45,
                status=Meeting.Status.HELD,
                logged_by=arjun,
                mentor_confirmed=True,
                title='Orientation & Pathway Alignment'
            )
            m2 = Meeting.objects.create(
                mentorship=pair_h,
                session_date=date(2026, 10, 24),
                duration_minutes=60,
                status=Meeting.Status.HELD,
                logged_by=arjun,
                mentor_confirmed=True,
                title='Portfolio Audit & System Design'
            )
            # Scheduled upcoming meeting
            m3 = Meeting.objects.create(
                mentorship=pair_h,
                session_date=date(2026, 11, 12),
                duration_minutes=60,
                status=Meeting.Status.SCHEDULED,
                logged_by=arjun,
                title='Session 3: Live Mock Technical Interview'
            )
            MeetingCalendarEvent.objects.create(
                meeting=m3,
                calendar_owner=arjun,
                event_id='event_sangam_003',
                html_link='https://calendar.google.com/event?eid=sangam03',
                meet_link='https://meet.google.com/sangam-session-03',
                sync_status=MeetingCalendarEvent.SyncStatus.SYNCED
            )

            # Rating / Feedback
            Feedback.objects.create(
                mentorship=pair_h,
                author=hemant,
                kind=Feedback.Kind.PROGRESS,
                text='Arjun was extremely specific with actionable feedback on SQL indexing and real-world ML deployment trade-offs. 5/5 stars!'
            )

        # Pair 2: Asha + Priya (ACTIVE MATCHED)
        asha = students_dict['asha@ds.study.iitm.ac.in']
        priya = mentors_dict['priya.n@alumni.example.org']
        if not MentoringRequest.objects.filter(student=asha).exists():
            req_a = services.create_request(student=asha, data={
                'pathway': 'JOB',
                'domain': 'Software',
                'background': 'Degree student, strong DSA and Java foundation.',
                'preferred_mentor': priya,
                'problem_statement': 'Guidance requested on structuring SDE coding prep, system design fundamentals, and '
                                     'mock technical interview rounds for upcoming campus placement drives.'
            })
            check_a = services.send_availability(request_id=req_a.pk, mentor_id=priya.pk, actor=iic)
            services.respond_availability(check_id=check_a.pk, mentor=priya, decision='CONFIRMED')
            pair_a = services.approve_match(check_id=check_a.pk, actor=iic)

            Goal.objects.get_or_create(mentorship=pair_a, slot=1, defaults={
                'title': 'Complete 50 curated LeetCode Medium problems in Graphs/DP',
                'target_date': date(2026, 11, 10),
                'completed': True
            })
            Goal.objects.get_or_create(mentorship=pair_a, slot=2, defaults={
                'title': 'High-level system design of a distributed cache',
                'target_date': date(2026, 11, 25),
                'completed': False
            })

        # Request 3: Rahul Mehta (SUBMITTED)
        rahul = students_dict['rahul@ds.study.iitm.ac.in']
        if not MentoringRequest.objects.filter(student=rahul).exists():
            services.create_request(student=rahul, data={
                'pathway': 'HIGHER_STUDIES',
                'domain': 'Higher Studies',
                'background': 'Interested in MS Informatics in Germany.',
                'preferred_mentor': mentors_dict['rohan.s@alumni.example.org'],
                'problem_statement': 'I need assistance reviewing my Statement of Purpose (SOP), shortlisting TU9 universities, '
                                     'and understanding the DAAD scholarship application timeline before the Dec 15 deadline.'
            })

        # Request 4: Sneha Reddy (UNDER_REVIEW)
        sneha = students_dict['sneha@ds.study.iitm.ac.in']
        if not MentoringRequest.objects.filter(student=sneha).exists():
            req_s = services.create_request(student=sneha, data={
                'pathway': 'HIGHER_STUDIES',
                'domain': 'Data & ML',
                'background': 'High CGPA student focusing on pre-doctoral AI research.',
                'preferred_mentor': mentors_dict['ananya.m@alumni.example.org'],
                'problem_statement': 'Seeking guidance on preparing pre-doctoral research applications in AI, specifically on '
                                     'how to frame research publications and write outreach emails to faculty.'
            })
            services.transition_request(request_id=req_s.pk, actor=iic, to_status=MentoringRequest.Status.UNDER_REVIEW, note='IIC reviewing candidate profile')

        # Request 5: Aditya Nair (AWAITING_MENTOR / Availability Sent)
        aditya = students_dict['aditya@ds.study.iitm.ac.in']
        if not MentoringRequest.objects.filter(student=aditya).exists():
            req_ad = services.create_request(student=aditya, data={
                'pathway': 'JOB',
                'domain': 'Analytics',
                'background': 'Diploma student looking for Business Analyst entry roles.',
                'preferred_mentor': mentors_dict['neha.s@alumni.example.org'],
                'problem_statement': 'Need help translating coursework project metrics into clear business impact points on '
                                     'my resume to pass recruiter screening for Business Analyst roles.'
            })
            services.send_availability(request_id=req_ad.pk, mentor_id=mentors_dict['neha.s@alumni.example.org'].pk, actor=iic)

        # 5. Knowledge Articles
        for title, audience, content in KNOWLEDGE_ARTICLES:
            KnowledgeArticle.objects.get_or_create(
                title=title,
                defaults={'audience': audience, 'is_published': True, 'content': content}
            )

        self.stdout.write(self.style.SUCCESS(f'Full Production Demo Data Seeded!'))
        self.stdout.write(f'All accounts use Password: {PASSWORD}')
        self.stdout.write(f'  Admin:  iic.admin@iitm.ac.in')
        self.stdout.write(f'  Mentor: arjun.k@alumni.example.org')
        self.stdout.write(f'  Student: hemant@ds.study.iitm.ac.in')

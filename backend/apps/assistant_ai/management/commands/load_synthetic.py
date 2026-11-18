"""Load synthetic fixtures into a DEV/seed database:  python manage.py load_synthetic [--timelines 30]

Refuses to run against a database that already has non-synthetic users unless --force is given.
All synthetic users get emails under example.org / ds.study.iitm.ac.in placeholders and an unusable password.
"""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User, StudentProfile, MentorProfile
from apps.assistant_ai.models import KnowledgeArticle
from apps.mentoring.models import MentoringRequest, AvailabilityCheck, Mentorship, Meeting, Feedback, Goal

FIX = Path(settings.BASE_DIR) / 'fixtures' / 'synthetic'


def j(name):
    return json.loads((FIX / name).read_text(encoding='utf8'))


class Command(BaseCommand):
    help = 'Load synthetic mentors, students, requests, articles and some activity timelines (dev/seed DB only).'

    def add_arguments(self, p):
        p.add_argument('--timelines', type=int, default=30)
        p.add_argument('--force', action='store_true')

    @transaction.atomic
    def handle(self, *a, **o):
        if User.objects.exclude(email__endswith='@example.org').exclude(email__endswith='ds.study.iitm.ac.in').exclude(is_superuser=True).exists() and not o['force']:
            raise CommandError('Database has real-looking users. Use a seed database or pass --force.')
        iic, _ = User.objects.get_or_create(email='iic.synthetic@example.org', defaults={'role': 'ADMIN', 'is_staff': True})
        mentor_users = {}
        for m in j('mentors.json'):
            u, _ = User.objects.get_or_create(email=m['email'], defaults={'role': 'MENTOR', 'first_name': m['first_name'], 'last_name': m['last_name']})
            u.set_unusable_password(); u.save()
            MentorProfile.objects.update_or_create(user=u, defaults={k: m[k] for k in (
                'domain', 'specialty', 'skills', 'career_path', 'experience_years', 'bio', 'is_verified', 'is_available',
                'is_discoverable', 'company', 'current_role')})
            mentor_users[m['id']] = u
        student_users = {}
        for s in j('students.json'):
            u, _ = User.objects.get_or_create(email=s['email'], defaults={'role': 'STUDENT', 'first_name': s['first_name'], 'last_name': s['last_name']})
            u.set_unusable_password(); u.save()
            StudentProfile.objects.update_or_create(user=u, defaults={'iitm_roll_number': s['iitm_roll_number'], 'level': s['level'],
                                                                      'courses': s['courses'], 'cgpa': s['cgpa'], 'approval_status': s['approval_status']})
            student_users[s['id']] = u
        # timelines -> active mentorships with free students/mentors
        busy_m = set(Mentorship.objects.filter(status='ACTIVE').values_list('mentor_id', flat=True))
        busy_s = set(Mentorship.objects.filter(status='ACTIVE').values_list('student_id', flat=True))
        free_m = [u for u in mentor_users.values() if u.pk not in busy_m and u.mentor_profile.is_verified]
        free_s = [u for u in student_users.values() if u.pk not in busy_s and u.student_profile.approval_status == 'APPROVED']
        free_s = free_s[::-1]   # take students from the end so early students keep their open requests
        n = 0
        shift = date.today() - date(2026, 11, 18)
        for t, mu, su in zip(j('timelines.json')[:o['timelines']], free_m, free_s):
            req = MentoringRequest.objects.create(student=su, pathway='JOB', domain=mu.mentor_profile.domain, status='MATCHED',
                                                  problem_statement='Synthetic matched request for activity timeline demo. ' * 3)
            # Request submitted a few days before the mentorship started, like a real match
            MentoringRequest.objects.filter(pk=req.pk).update(
                submitted_at=timezone.make_aware(datetime.fromisoformat(t['started_at']) + shift - timedelta(days=3 + n % 9)))
            chk = AvailabilityCheck.objects.create(request=req, mentor=mu, status='USED')
            pair = Mentorship.objects.create(request=req, availability_check=chk, student=su, mentor=mu, approved_by=iic,
                                             started_at=timezone.make_aware(datetime.fromisoformat(t['started_at']) + shift))
            for mt in t['meetings']:
                Meeting.objects.create(mentorship=pair, session_date=date.fromisoformat(mt['date']) + shift, duration_minutes=45,
                                       status=mt['status'], logged_by=mu, mentor_confirmed=True)
            for fd in t['mentor_feedback']:
                f = Feedback.objects.create(mentorship=pair, author=mu, kind='PROGRESS', text='Synthetic progress note.')
                Feedback.objects.filter(pk=f.pk).update(created_at=timezone.make_aware(datetime.fromisoformat(fd) + shift))
            for slot in range(1, t['goals_total'] + 1):
                done = slot <= len(t['goal_updates']) and slot == 1
                Goal.objects.create(mentorship=pair, slot=slot, title=f'Synthetic goal {slot}', target_date=date.today() + timedelta(days=30),
                                    completed=done, completed_at=timezone.make_aware(datetime.fromisoformat(t['goal_updates'][-1]) + shift) if done and t['goal_updates'] else None)
            n += 1
        made = 0
        for r in j('requests.json'):
            st = student_users[r['student_id']]
            if Mentorship.objects.filter(student=st, status='ACTIVE').exists() or                     MentoringRequest.objects.filter(student=st, status__in=['SUBMITTED', 'UNDER_REVIEW', 'WAITING']).exists():
                continue   # one open request per student
            obj = MentoringRequest.objects.create(student=st, pathway=r['pathway'], domain=r['domain'], problem_statement=r['problem_statement'],
                                                  preferred_mentor=mentor_users.get(r['preferred_mentor_id']), status=r['status'])
            MentoringRequest.objects.filter(pk=obj.pk).update(submitted_at=timezone.make_aware(datetime.fromisoformat(r['submitted_at'])))
            made += 1
        kb = j('knowledge.json')
        for art in kb['articles']:
            KnowledgeArticle.objects.update_or_create(title=art['title'], defaults={'content': art['content'], 'audience': art['audience'], 'is_published': True})
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(mentor_users)} mentors, {len(student_users)} students, {made} requests, '
                                             f'{len(kb["articles"])} articles, {n} mentorship timelines (all synthetic).'))

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.mentoring.models import Mentorship, Meeting, Feedback, Alert, MentoringRequest
from apps.mentoring.services import inform, expire_overdue_checks
from apps.mentoring.workflow import OPEN_STATUSES

class Command(BaseCommand):
    help='Run once daily: expire 7-day checks; flag 14-day inactivity and mentor feedback due; refresh advisory priorities.'
    def handle(self,*args,**kwargs):
        now=timezone.now()
        count=expire_overdue_checks(now)
        self.stdout.write(f'Expired checks: {count}')
        for pair in Mentorship.objects.filter(status='ACTIVE').select_related('mentor'):
            latest=Meeting.objects.filter(mentorship=pair,status='HELD').order_by('-session_date').first()
            last=latest.session_date if latest else pair.started_at.date()
            if last <= now.date()-timedelta(days=14):
                period=now.date() - timedelta(days=now.date().toordinal()%14)
                a,created=Alert.objects.get_or_create(mentorship=pair,kind='INACTIVITY',period_start=period)
                if created:self.stdout.write(f'Inactivity alert for mentorship {pair.pk}')
            last_feedback=Feedback.objects.filter(mentorship=pair,author=pair.mentor,kind='PROGRESS').order_by('-created_at').first()
            since=last_feedback.created_at.date() if last_feedback else pair.started_at.date()
            if since <= now.date()-timedelta(days=14):
                period=now.date() - timedelta(days=now.date().toordinal()%14)
                _,created=Alert.objects.get_or_create(mentorship=pair,kind='FEEDBACK_DUE',period_start=period)
                if created:inform(pair.mentor,'Sangam progress update','Please send your fortnightly progress feedback to IIC.')
        from apps.assistant_ai.services import assess_request_priority
        assessed=sum(1 for r in MentoringRequest.objects.filter(status__in=OPEN_STATUSES) if assess_request_priority(r))
        self.stdout.write(f'Priorities refreshed: {assessed}')
        self.stdout.write(self.style.SUCCESS('Sangam daily checks completed.'))

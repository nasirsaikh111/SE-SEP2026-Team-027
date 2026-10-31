from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.mentoring.models import AvailabilityCheck, Mentorship, Meeting, Feedback, Alert, MentoringRequest
from apps.mentoring.services import inform

class Command(BaseCommand):
    help='Run once daily: expire 7-day checks; flag 14-day inactivity and mentor feedback due.'
    def handle(self,*args,**kwargs):
        now=timezone.now()
        expired=AvailabilityCheck.objects.filter(status='PENDING',expires_at__lte=now)
        count=expired.count()
        for check in expired.select_related('request'):
            check.status='EXPIRED';check.save(update_fields=['status'])
            if check.request.status in ('SUBMITTED','UNDER_REVIEW'):
                check.request.status='WAITING';check.request.save(update_fields=['status','updated_at'])
                inform(check.request.student,'Mentoring request waiting','Availability check expired; IIC will try another mentor.')
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
        self.stdout.write(self.style.SUCCESS('Sangam daily checks completed.'))

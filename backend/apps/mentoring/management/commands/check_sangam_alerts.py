from django.core.management.base import BaseCommand
from apps.mentoring.services import run_daily_checks

class Command(BaseCommand):
    help='Run once daily: expire 7-day checks; flag 14-day inactivity and mentor feedback due; refresh advisory priorities.'
    def handle(self,*args,**kwargs):
        summary=run_daily_checks()
        self.stdout.write(f"Expired checks: {summary['expired_checks']}")
        self.stdout.write(f"Inactivity alerts: {summary['inactivity_alerts']}")
        self.stdout.write(f"Feedback alerts: {summary['feedback_alerts']}")
        self.stdout.write(f"Priorities refreshed: {summary['priorities_refreshed']}")
        self.stdout.write(self.style.SUCCESS('Sangam daily checks completed.'))

"""Backfill timeline entries for records created before ActivityStatusHistory existed.

Additive and idempotent: only requests/mentorships without any history get entries,
and no existing row is modified.
"""
from django.db import migrations


def backfill(apps, schema_editor):
    Request = apps.get_model('mentoring', 'MentoringRequest')
    Mentorship = apps.get_model('mentoring', 'Mentorship')
    History = apps.get_model('mentoring', 'ActivityStatusHistory')
    rows = []
    for req in Request.objects.filter(status_history__isnull=True).iterator():
        rows.append(History(request_id=req.pk, event='REQUEST_SUBMITTED', to_status='SUBMITTED',
                            actor_id=req.student_id, actor_role='STUDENT', created_at=req.submitted_at,
                            note='Backfilled from existing request.'))
        if req.status != 'SUBMITTED':
            rows.append(History(request_id=req.pk, event='STATUS_BACKFILLED', from_status='SUBMITTED',
                                to_status=req.status, created_at=req.updated_at,
                                note='Current status at time of migration.'))
    for pair in Mentorship.objects.filter(status_history__isnull=True).iterator():
        rows.append(History(request_id=pair.request_id, mentorship_id=pair.pk, event='MATCH_APPROVED',
                            to_status='ACTIVE', actor_id=pair.approved_by_id, actor_role='ADMIN',
                            created_at=pair.started_at, note='Backfilled from existing mentorship.'))
        if pair.status == 'CLOSED' and pair.closed_at:
            rows.append(History(request_id=pair.request_id, mentorship_id=pair.pk, event='MENTORSHIP_CLOSED',
                                from_status='ACTIVE', to_status='CLOSED', created_at=pair.closed_at,
                                note='Backfilled from existing mentorship.'))
    History.objects.bulk_create(rows, batch_size=500)


class Migration(migrations.Migration):
    dependencies = [('mentoring', '0002_scheduling_history_calendar')]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]

"""All consequential pairing transitions happen here, never through raw model updates."""
from datetime import timedelta
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
import logging
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from apps.accounts.models import User, MentorProfile
from apps.accounts.permissions import iic
from .models import MentoringRequest, AvailabilityCheck, Mentorship, AuditLog, Notification, Alert, ActivityStatusHistory
from .workflow import OPEN_STATUSES


def log(actor, action, obj, details=None):
    return AuditLog.objects.create(actor=actor, action=action, entity_type=type(obj).__name__, entity_id=obj.pk, details=details or {})


def inform(recipient, title, message):
    note = Notification.objects.create(recipient=recipient, title=title, message=message)
    def _send():
        try:
            send_mail(title, message, settings.DEFAULT_FROM_EMAIL, [recipient.email], fail_silently=False)
        except Exception:
            logging.getLogger(__name__).exception('Sangam email delivery failed (notification %s)', note.pk)
    transaction.on_commit(_send)
    return note


def inform_iic(title, message):
    for admin in User.objects.filter(role='ADMIN', is_active=True, is_staff=True):
        Notification.objects.create(recipient=admin, title=title, message=message)


def record(*, event, to_status, request=None, mentorship=None, actor=None, from_status='', note='', visible_to_student=True):
    """Append a timeline entry. Notes are short system messages, never user narrative."""
    role = 'SYSTEM' if actor is None else ('ADMIN' if iic(actor) else actor.role)
    return ActivityStatusHistory.objects.create(
        request=request, mentorship=mentorship, event=event, from_status=from_status, to_status=to_status,
        actor=actor, actor_role=role, note=note[:300], visible_to_student=visible_to_student)


@transaction.atomic
def create_request(*, student, data):
    if Mentorship.objects.filter(student=student, status='ACTIVE').exists():
        raise ValidationError('Student already has an active mentorship.')
    if MentoringRequest.objects.select_for_update().filter(student=student, status__in=OPEN_STATUSES).exists():
        raise ValidationError('Only one open request is allowed.')
    req = MentoringRequest.objects.create(student=student, **data)
    log(student, 'REQUEST_CREATED', req, {'preferred_mentor_id': req.preferred_mentor_id})
    record(event='REQUEST_SUBMITTED', to_status='SUBMITTED', request=req, actor=student,
           note='Preferred mentor noted for IIC review.' if req.preferred_mentor_id else '')
    inform_iic('New mentoring request', f'Request #{req.pk} ({req.domain}) is awaiting IIC review.')
    from apps.assistant_ai.services import assess_request_priority
    assess_request_priority(req)
    return req


@transaction.atomic
def withdraw_request(*, request_id, student):
    req = MentoringRequest.objects.select_for_update().filter(pk=request_id, student=student).first()
    if req is None:
        from django.http import Http404
        raise Http404
    if req.status not in OPEN_STATUSES:
        raise ValidationError('Only open requests may be withdrawn.')
    previous = req.status
    req.status = 'WITHDRAWN'
    req.save(update_fields=['status', 'updated_at'])
    AvailabilityCheck.objects.filter(request=req, status__in=['PENDING', 'CONFIRMED']).update(status='EXPIRED')
    log(student, 'REQUEST_WITHDRAWN', req)
    record(event='REQUEST_WITHDRAWN', from_status=previous, to_status='WITHDRAWN', request=req, actor=student)
    return req


IIC_TRANSITIONS = {
    'UNDER_REVIEW': ('SUBMITTED',),
    'WAITING': ('SUBMITTED', 'UNDER_REVIEW'),
    'CLOSED': OPEN_STATUSES,
}


@transaction.atomic
def transition_request(*, request_id, actor, to_status, note=''):
    """IIC-only manual transitions: start review, mark waiting, or close an open request."""
    req = MentoringRequest.objects.select_for_update().get(pk=request_id)
    if to_status not in IIC_TRANSITIONS:
        raise ValidationError({'to_status': 'Use UNDER_REVIEW, WAITING or CLOSED.'})
    if req.status not in IIC_TRANSITIONS[to_status]:
        raise ValidationError(f'Cannot move a {req.status} request to {to_status}.')
    if to_status == 'CLOSED' and not note.strip():
        raise ValidationError({'note': 'A reason is required to close a request.'})
    if to_status == 'WAITING' and AvailabilityCheck.objects.filter(request=req, status='PENDING', expires_at__gt=timezone.now()).exists():
        raise ValidationError('An availability check is still pending for this request.')
    previous = req.status
    req.status = to_status
    req.save(update_fields=['status', 'updated_at'])
    if to_status == 'CLOSED':
        AvailabilityCheck.objects.filter(request=req, status__in=['PENDING', 'CONFIRMED']).update(status='EXPIRED')
        inform(req.student, 'Mentoring request closed', f'IIC closed your mentoring request. Reason: {note.strip()[:250]}')
    log(actor, 'REQUEST_' + to_status, req, {'from': previous})
    record(event='IIC_STATUS_CHANGE', from_status=previous, to_status=to_status, request=req, actor=actor,
           note=note.strip()[:300] if to_status == 'CLOSED' else '')
    return req


@transaction.atomic
def send_availability(*, request_id, mentor_id, actor):
    req = MentoringRequest.objects.select_for_update().get(pk=request_id)
    try:
        mentor = User.objects.select_for_update().get(pk=mentor_id)
    except User.DoesNotExist:
        raise ValidationError('Mentor not found.')
    if req.status not in (MentoringRequest.Status.SUBMITTED, MentoringRequest.Status.UNDER_REVIEW, MentoringRequest.Status.WAITING):
        raise ValidationError('Request is no longer eligible for matching.')
    try:
        profile = mentor.mentor_profile
    except MentorProfile.DoesNotExist:
        raise ValidationError('Mentor profile is missing.')
    if (mentor.role != 'MENTOR' or not mentor.is_active or not profile.is_verified or not profile.is_available):
        raise ValidationError('Mentor is not verified and available.')
    if Mentorship.objects.filter(mentor=mentor, status='ACTIVE').exists():
        raise ValidationError('Mentor already has an active mentee.')
    if Mentorship.objects.filter(student=req.student, status='ACTIVE').exists():
        raise ValidationError('Student already has an active mentorship.')
    if AvailabilityCheck.objects.filter(request=req, status='PENDING').exists():
        raise ValidationError('This request already has an unanswered availability check.')
    if AvailabilityCheck.objects.filter(request=req, status='CONFIRMED', expires_at__gt=timezone.now()).exists():
        raise ValidationError('A mentor has already confirmed availability; approve or close that check first.')
    check = AvailabilityCheck.objects.create(request=req, mentor=mentor, expires_at=timezone.now()+timedelta(days=7))
    previous = req.status
    req.status = 'UNDER_REVIEW'
    req.save(update_fields=['status', 'updated_at'])
    log(actor, 'AVAILABILITY_SENT', check, {'request_id': req.pk, 'mentor_id': mentor.pk,
                                            'is_student_preference': req.preferred_mentor_id == mentor.pk})
    record(event='AVAILABILITY_CHECK_SENT', from_status=previous, to_status='AVAILABILITY_CHECK_SENT', request=req,
           actor=actor, note='IIC asked a mentor to confirm availability within 7 days.')
    inform(mentor, 'Mentoring availability check', 'Please review the new mentoring need within 7 days.')
    return check


def _expire_check(check):
    """Mark a single overdue check EXPIRED and return the request to WAITING."""
    check.status = 'EXPIRED'
    check.save(update_fields=['status'])
    req = check.request
    if req.status in ('SUBMITTED', 'UNDER_REVIEW'):
        req.status = 'WAITING'
        req.save(update_fields=['status', 'updated_at'])
    record(event='AVAILABILITY_CHECK_EXPIRED', from_status='AVAILABILITY_CHECK_SENT', to_status='WAITING', request=req,
           note='Mentor did not respond within 7 days; IIC will try another mentor.')
    log(None, 'AVAILABILITY_EXPIRED', check)
    inform(req.student, 'Mentoring request waiting', 'Availability check expired; IIC will try another mentor.')
    inform_iic('Availability check expired', f'Request #{req.pk}: the mentor did not respond within 7 days. '
               'Send a check to the next suggested mentor, or leave it in the waiting queue.')


def expire_overdue_checks(now=None):
    now = now or timezone.now()
    count = 0
    for check_id in AvailabilityCheck.objects.filter(status='PENDING', expires_at__lte=now).values_list('pk', flat=True):
        with transaction.atomic():
            check = AvailabilityCheck.objects.select_for_update().select_related('request').get(pk=check_id)
            if check.status == 'PENDING':
                _expire_check(check)
                count += 1
    return count


def respond_availability(*, check_id, mentor, decision, reason=''):
    expired = False
    with transaction.atomic():
        check = AvailabilityCheck.objects.select_for_update().select_related('request').get(pk=check_id)
        if check.mentor_id != mentor.pk:
            raise PermissionDenied('This check is not assigned to you.')
        if check.status != 'PENDING':
            raise ValidationError('Availability check is already resolved.')
        if check.expires_at <= timezone.now():
            _expire_check(check)  # persisted: the error is raised after this transaction commits
            expired = True
        else:
            if decision not in ('CONFIRMED', 'DECLINED'):
                raise ValidationError('Use CONFIRMED or DECLINED.')
            if decision == 'CONFIRMED' and Mentorship.objects.filter(mentor=mentor, status='ACTIVE').exists():
                raise ValidationError('You already have an active mentee.')
            check.status, check.reason, check.responded_at = decision, (reason or '')[:500], timezone.now()
            check.save(update_fields=['status', 'reason', 'responded_at'])
            if decision == 'DECLINED':
                check.request.status = 'WAITING'
                check.request.save(update_fields=['status', 'updated_at'])
                record(event='MENTOR_DECLINED', from_status='AVAILABILITY_CHECK_SENT', to_status='WAITING',
                       request=check.request, actor=mentor, note='Mentor unavailable; IIC will try another mentor.')
                inform_iic('Mentor declined availability', f'Request #{check.request_id}: send a check to the next suggested mentor, '
                           'or leave it in the waiting queue.')
            else:
                record(event='MENTOR_CONFIRMED', from_status='AVAILABILITY_CHECK_SENT', to_status='AWAITING_IIC_APPROVAL',
                       request=check.request, actor=mentor, note='Mentor confirmed availability; awaiting IIC approval.')
                inform_iic('Mentor confirmed availability', f'Request #{check.request_id} is ready for final IIC approval.')
            log(mentor, 'AVAILABILITY_' + decision, check)
            inform(check.request.student, 'Mentoring request status', 'Your mentoring request remains under review.' if decision == 'CONFIRMED' else 'Your request is waiting for another available mentor.')
    if expired:
        raise ValidationError('Availability check has expired.')
    return check


@transaction.atomic
def approve_match(*, check_id, actor):
    check = AvailabilityCheck.objects.select_for_update().select_related('request','mentor').get(pk=check_id)
    req = MentoringRequest.objects.select_for_update().get(pk=check.request_id)
    # Lock both user rows to serialize concurrent approvals across different requests.
    list(User.objects.select_for_update().filter(pk__in=[req.student_id, check.mentor_id]).order_by('pk'))
    if check.status != 'CONFIRMED' or check.expires_at <= timezone.now():
        raise ValidationError('A current, confirmed availability check is required.')
    if req.status not in ('SUBMITTED','UNDER_REVIEW','WAITING'):
        raise ValidationError('Request is not open.')
    if not hasattr(req.student, 'student_profile') or req.student.student_profile.approval_status != 'APPROVED':
        raise ValidationError('Student must be approved by IIC.')
    profile = check.mentor.mentor_profile
    if check.mentor.role != 'MENTOR' or not check.mentor.is_active or not profile.is_verified or not profile.is_available:
        raise ValidationError('Mentor is not verified/available.')
    if Mentorship.objects.filter(status='ACTIVE', student=req.student).exists() or Mentorship.objects.filter(status='ACTIVE', mentor=check.mentor).exists():
        raise ValidationError('One-to-one capacity is already filled.')
    pair = Mentorship.objects.create(request=req, availability_check=check, student=req.student, mentor=check.mentor, approved_by=actor)
    check.status = 'USED'
    check.save(update_fields=['status'])
    previous = req.status
    req.status = 'MATCHED'
    req.save(update_fields=['status','updated_at'])
    log(actor, 'MATCH_APPROVED', pair, {'request_id': req.id})
    record(event='MATCH_APPROVED', from_status=previous, to_status='ACTIVE', request=req, mentorship=pair, actor=actor,
           note='IIC approved the pairing. Contact details are now visible to both participants.')
    inform(req.student, 'Mentor match approved', 'IIC has approved your mentorship. Mentor contact is now available in My Mentorship.')
    inform(check.mentor, 'Mentorship approved', 'IIC has approved the mentorship. Student contact is now available in your workspace.')
    return pair


@transaction.atomic
def close_mentorship(*, pair_id, actor, reason, closure_type=Mentorship.ClosureType.COMPLETED):
    pair = Mentorship.objects.select_for_update().get(pk=pair_id)
    if pair.status != 'ACTIVE':
        raise ValidationError('Mentorship already ended.')
    if not reason.strip():
        raise ValidationError('Closing reason is required.')
    if closure_type not in Mentorship.ClosureType.values:
        raise ValidationError({'closure_type': 'Invalid closure type.'})
    pair.status = 'CLOSED'
    pair.closed_at = timezone.now()
    pair.closing_reason = reason.strip()
    pair.closure_type = closure_type
    pair.closed_by = actor
    pair.save(update_fields=['status','closed_at','closing_reason','closure_type','closed_by'])
    if closure_type != Mentorship.ClosureType.REASSIGNED:
        pair.request.status = 'CLOSED'
        pair.request.save(update_fields=['status','updated_at'])
    Alert.objects.filter(mentorship=pair, resolved_at__isnull=True).update(resolved_at=pair.closed_at)
    log(actor, 'MENTORSHIP_CLOSED', pair, {'closure_type': closure_type})
    record(event='MENTORSHIP_CLOSED', from_status='ACTIVE', to_status='CLOSED', request=pair.request, mentorship=pair,
           actor=actor, note=f'Closure type: {pair.get_closure_type_display()}.')
    if closure_type != Mentorship.ClosureType.REASSIGNED:
        inform(pair.student, 'Mentorship closed', 'Your mentorship has ended. Please send IIC your closing feedback '
               'and record any outcomes (interviews, offers, admissions) in Sangam.')
    pool = ('You are back in the mentor pool for new requests.' if pair.mentor.mentor_profile.is_available
            else 'Turn on availability in Sangam when you are ready for a new mentee.')
    inform(pair.mentor, 'Mentorship closed', f'Your mentorship has ended. Please send IIC your closing feedback. {pool}')
    return pair


@transaction.atomic
def reassign_mentorship(*, pair_id, actor, reason):
    """Close the current pairing and reopen the same request so IIC can match a new mentor."""
    pair = Mentorship.objects.select_for_update().select_related('request').get(pk=pair_id)
    if pair.status != 'ACTIVE':
        raise ValidationError('Only active mentorships can be reassigned.')
    if MentoringRequest.objects.filter(student=pair.student, status__in=OPEN_STATUSES).exclude(pk=pair.request_id).exists():
        raise ValidationError('Student already has another open request.')
    close_mentorship(pair_id=pair.pk, actor=actor, reason=reason, closure_type=Mentorship.ClosureType.REASSIGNED)
    req = MentoringRequest.objects.select_for_update().get(pk=pair.request_id)
    req.status = 'WAITING'
    req.save(update_fields=['status', 'updated_at'])
    log(actor, 'MENTORSHIP_REASSIGNMENT', pair, {'request_id': req.pk})
    record(event='REASSIGNMENT_STARTED', from_status='CLOSED', to_status='WAITING', request=req, mentorship=pair,
           actor=actor, note='IIC reopened the request to find a new mentor.')
    inform(pair.student, 'Mentor reassignment', 'IIC is arranging a new mentor for you. Your request is back in the matching queue.')
    return req


def resolve_alerts(pair, kind):
    Alert.objects.filter(mentorship=pair, kind=kind, resolved_at__isnull=True).update(resolved_at=timezone.now())


def run_daily_checks(now=None):
    """Daily monitoring: expire 7-day checks, flag 14-day inactivity and mentor feedback due, refresh priorities.

    Idempotent (alerts are unique per fortnight), so it is safe to run from cron and on demand by IIC.
    """
    from .models import Meeting, Feedback
    from apps.assistant_ai.services import assess_request_priority
    now = now or timezone.now()
    today = timezone.localdate(now)
    period = today - timedelta(days=today.toordinal() % 14)
    summary = {'expired_checks': expire_overdue_checks(now), 'inactivity_alerts': 0, 'feedback_alerts': 0}
    for pair in Mentorship.objects.filter(status='ACTIVE').select_related('mentor'):
        latest = Meeting.objects.filter(mentorship=pair, status='HELD').order_by('-session_date').first()
        last = latest.session_date if latest else timezone.localdate(pair.started_at)
        if last <= today - timedelta(days=14):
            _, created = Alert.objects.get_or_create(mentorship=pair, kind='INACTIVITY', period_start=period)
            summary['inactivity_alerts'] += created
        last_feedback = Feedback.objects.filter(mentorship=pair, author=pair.mentor, kind='PROGRESS').order_by('-created_at').first()
        since = timezone.localdate(last_feedback.created_at) if last_feedback else timezone.localdate(pair.started_at)
        if since <= today - timedelta(days=14):
            _, created = Alert.objects.get_or_create(mentorship=pair, kind='FEEDBACK_DUE', period_start=period)
            if created:
                summary['feedback_alerts'] += 1
                inform(pair.mentor, 'Sangam progress update', 'Please send your fortnightly progress feedback to IIC.')
    summary['priorities_refreshed'] = sum(1 for r in MentoringRequest.objects.filter(status__in=OPEN_STATUSES) if assess_request_priority(r))
    return summary

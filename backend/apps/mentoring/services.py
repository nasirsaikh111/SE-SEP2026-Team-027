"""All consequential pairing transitions happen here, never through raw model updates."""
from datetime import timedelta
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
import logging
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from apps.accounts.models import User, MentorProfile
from .models import MentoringRequest, AvailabilityCheck, Mentorship, AuditLog, Notification


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
    check = AvailabilityCheck.objects.create(request=req, mentor=mentor, expires_at=timezone.now()+timedelta(days=7))
    req.status = 'UNDER_REVIEW'
    req.save(update_fields=['status', 'updated_at'])
    log(actor, 'AVAILABILITY_SENT', check, {'request_id': req.pk, 'mentor_id': mentor.pk})
    inform(mentor, 'Mentoring availability check', 'Please review the new mentoring need within 7 days.')
    return check


@transaction.atomic
def respond_availability(*, check_id, mentor, decision, reason=''):
    check = AvailabilityCheck.objects.select_for_update().get(pk=check_id)
    if check.mentor_id != mentor.pk:
        raise PermissionDenied('This check is not assigned to you.')
    if check.status != 'PENDING':
        raise ValidationError('Availability check is already resolved.')
    if check.expires_at <= timezone.now():
        check.status = 'EXPIRED'
        check.save(update_fields=['status'])
        raise ValidationError('Availability check has expired.')
    if decision not in ('CONFIRMED', 'DECLINED'):
        raise ValidationError('Use CONFIRMED or DECLINED.')
    if decision == 'CONFIRMED' and Mentorship.objects.filter(mentor=mentor, status='ACTIVE').exists():
        raise ValidationError('You already have an active mentee.')
    check.status, check.reason, check.responded_at = decision, reason[:500], timezone.now()
    check.save(update_fields=['status', 'reason', 'responded_at'])
    if decision == 'DECLINED':
        check.request.status = 'WAITING'
        check.request.save(update_fields=['status', 'updated_at'])
    log(mentor, 'AVAILABILITY_' + decision, check)
    inform(check.request.student, 'Mentoring request status', 'Your mentoring request remains under review.' if decision == 'CONFIRMED' else 'Your request is waiting for another available mentor.')
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
    req.status = 'MATCHED'
    req.save(update_fields=['status','updated_at'])
    log(actor, 'MATCH_APPROVED', pair, {'request_id': req.id})
    inform(req.student, 'Mentor match approved', 'IIC has approved your mentorship. Mentor contact is now available in My Mentorship.')
    inform(check.mentor, 'Mentorship approved', 'IIC has approved the mentorship. Student contact is now available in your workspace.')
    return pair


@transaction.atomic
def close_mentorship(*, pair_id, actor, reason):
    pair = Mentorship.objects.select_for_update().get(pk=pair_id)
    if pair.status != 'ACTIVE':
        raise ValidationError('Mentorship already ended.')
    if not reason.strip():
        raise ValidationError('Closing reason is required.')
    pair.status = 'CLOSED'
    pair.closed_at = timezone.now()
    pair.closing_reason = reason.strip()
    pair.save(update_fields=['status','closed_at','closing_reason'])
    pair.request.status = 'CLOSED'
    pair.request.save(update_fields=['status','updated_at'])
    log(actor, 'MENTORSHIP_CLOSED', pair)
    inform(pair.student, 'Mentorship closed', 'Your mentorship has ended.')
    inform(pair.mentor, 'Mentorship closed', 'Your mentorship has ended.')
    return pair

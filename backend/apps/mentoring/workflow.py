"""Derived workflow stages for mentoring requests.

Persisted ``MentoringRequest.status`` values are unchanged (SUBMITTED, UNDER_REVIEW,
WAITING, MATCHED, WITHDRAWN, CLOSED). The finer-grained stages shown to users are
derived from availability checks and mentorships, so no status is invented without
backend support.
"""
from django.utils import timezone

OPEN_STATUSES = ('SUBMITTED', 'UNDER_REVIEW', 'WAITING')

STAGES = {
    'SUBMITTED': 'Submitted',
    'UNDER_REVIEW': 'Under review',
    'WAITING': 'Waiting',
    'AVAILABILITY_CHECK_SENT': 'Availability check sent',
    'MENTOR_CONFIRMED': 'Mentor confirmed',
    'AWAITING_IIC_APPROVAL': 'Awaiting IIC approval',
    'MATCHED': 'Matched',
    'ACTIVE': 'Active',
    'WITHDRAWN': 'Withdrawn',
    'CLOSED': 'Closed',
}

STUDENT_NEXT_ACTION = {
    'SUBMITTED': 'No action needed. IIC will review your request.',
    'UNDER_REVIEW': 'No action needed. IIC is reviewing suitable mentors.',
    'WAITING': 'No action needed. IIC is looking for an available mentor.',
    'AVAILABILITY_CHECK_SENT': 'No action needed. IIC is confirming mentor availability.',
    'AWAITING_IIC_APPROVAL': 'No action needed. IIC is finalising the pairing.',
    'MATCHED': 'Open My Mentorship to view your mentor.',
    'ACTIVE': 'Open My Mentorship to plan meetings and goals.',
    'WITHDRAWN': '',
    'CLOSED': '',
}

IIC_NEXT_ACTION = {
    'SUBMITTED': 'Review the request and view mentor suggestions.',
    'UNDER_REVIEW': 'Send an availability check to a suitable mentor.',
    'WAITING': 'Send an availability check to another mentor.',
    'AVAILABILITY_CHECK_SENT': 'Awaiting the mentor response (expires after 7 days).',
    'AWAITING_IIC_APPROVAL': 'Approve or reconsider the final pairing.',
    'MATCHED': 'Monitor the mentorship.',
    'ACTIVE': 'Monitor the mentorship.',
    'WITHDRAWN': '',
    'CLOSED': '',
}


def _latest(items, key):
    items = list(items)
    return max(items, key=key) if items else None


def current_check(req):
    """The unexpired PENDING/CONFIRMED check for an open request, if any."""
    now = timezone.now()
    live = [c for c in req.availability_checks.all() if c.status in ('PENDING', 'CONFIRMED') and c.expires_at > now]
    return _latest(live, key=lambda c: (c.sent_at, c.pk))


def current_mentorship(req):
    return _latest(req.mentorships.all(), key=lambda m: (m.started_at, m.pk))


def request_stage(req):
    if req.status == 'MATCHED':
        pair = current_mentorship(req)
        return 'ACTIVE' if pair and pair.status == 'ACTIVE' else 'MATCHED'
    if req.status not in OPEN_STATUSES:
        return req.status
    check = current_check(req)
    if check and check.status == 'PENDING':
        return 'AVAILABILITY_CHECK_SENT'
    if check and check.status == 'CONFIRMED':
        return 'AWAITING_IIC_APPROVAL'
    return req.status

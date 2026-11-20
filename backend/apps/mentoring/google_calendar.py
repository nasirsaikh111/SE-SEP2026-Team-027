"""Google Calendar integration (OAuth 2.0 web-server flow + Calendar v3 events).

Tokens are encrypted at rest with Fernet. Events carry scheduling metadata only;
Sangam never stores or sends discussion content.
"""
import base64
import hashlib
import json
import logging
import time
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core import signing
from django.utils import timezone

from .models import GoogleCalendarConnection, MeetingCalendarEvent

logger = logging.getLogger(__name__)

AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
REVOKE_URL = 'https://oauth2.googleapis.com/revoke'
USERINFO_URL = 'https://openidconnect.googleapis.com/v1/userinfo'
EVENTS_URL = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'
SCOPES = 'openid email https://www.googleapis.com/auth/calendar.events'
STATE_SALT = 'sangam.google-calendar'


class CalendarError(Exception):
    pass


class CalendarNotConfigured(CalendarError):
    pass


class ReauthRequired(CalendarError):
    pass


def is_configured():
    return bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET)


def _fernet():
    key = settings.SANGAM_TOKEN_ENCRYPTION_KEY
    if not key:
        key = base64.urlsafe_b64encode(hashlib.sha256(('sangam-tokens:' + settings.SECRET_KEY).encode()).digest())
    return Fernet(key)


def encrypt(value):
    return _fernet().encrypt(value.encode()).decode() if value else ''


def decrypt(value):
    if not value:
        return ''
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken:
        return ''


def http_json(method, url, *, form=None, body=None, token=None):
    """Single network entry point (patched in tests). Returns (status_code, parsed_json)."""
    headers = {'Accept': 'application/json'}
    data = None
    if form is not None:
        data = urlencode(form).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    elif body is not None:
        data = json.dumps(body).encode()
        headers['Content-Type'] = 'application/json'
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        with urlopen(Request(url, data=data, headers=headers, method=method), timeout=15) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else {})
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read() or b'{}')
        except ValueError:
            payload = {}
        return exc.code, payload
    except (URLError, OSError, ValueError) as exc:
        raise CalendarError(f'Google API unreachable: {type(exc).__name__}')


def connection_status(user):
    conn = GoogleCalendarConnection.objects.filter(user=user).first()
    return {
        'configured': is_configured(),
        'status': conn.status if conn else GoogleCalendarConnection.Status.DISCONNECTED,
        'google_email': conn.google_email if conn and conn.status != 'DISCONNECTED' else '',
        'connected_at': conn.connected_at if conn and conn.status != 'DISCONNECTED' else None,
    }


def authorization_url(user):
    if not is_configured():
        raise CalendarNotConfigured('Google Calendar integration is not configured on the server.')
    state = signing.dumps({'uid': user.pk}, salt=STATE_SALT)
    params = {'client_id': settings.GOOGLE_OAUTH_CLIENT_ID, 'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI,
              'response_type': 'code', 'scope': SCOPES, 'access_type': 'offline', 'prompt': 'consent',
              'include_granted_scopes': 'true', 'state': state}
    return f'{AUTH_URL}?{urlencode(params)}'


def complete_oauth(code, state):
    from apps.accounts.models import User
    try:
        uid = signing.loads(state, salt=STATE_SALT, max_age=900)['uid']
        user = User.objects.get(pk=uid, role='MENTOR')
    except (signing.BadSignature, KeyError, TypeError, User.DoesNotExist):
        raise CalendarError('Invalid or expired authorization state.')
    status, token = http_json('POST', TOKEN_URL, form={
        'code': code, 'client_id': settings.GOOGLE_OAUTH_CLIENT_ID, 'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
        'redirect_uri': settings.GOOGLE_OAUTH_REDIRECT_URI, 'grant_type': 'authorization_code'})
    if status != 200 or 'access_token' not in token:
        raise CalendarError('Google rejected the authorization code.')
    conn, _ = GoogleCalendarConnection.objects.get_or_create(user=user)
    email = ''
    info_status, info = http_json('GET', USERINFO_URL, token=token['access_token'])
    if info_status == 200:
        email = info.get('email', '')
    conn.access_token_enc = encrypt(token['access_token'])
    if token.get('refresh_token'):
        conn.refresh_token_enc = encrypt(token['refresh_token'])
    conn.token_expires_at = timezone.now() + timedelta(seconds=int(token.get('expires_in', 3600)) - 60)
    conn.scopes = token.get('scope', SCOPES)[:500]
    conn.google_email = email
    conn.status = GoogleCalendarConnection.Status.CONNECTED
    conn.connected_at = timezone.now()
    conn.last_error = ''
    conn.save()
    return conn


def _mark_reauth(conn, message):
    conn.status = GoogleCalendarConnection.Status.REAUTH_REQUIRED
    conn.last_error = message[:300]
    conn.save(update_fields=['status', 'last_error', 'updated_at'])
    raise ReauthRequired(message)


def access_token(user):
    conn = GoogleCalendarConnection.objects.filter(user=user).first()
    if not conn or conn.status == GoogleCalendarConnection.Status.DISCONNECTED:
        raise ReauthRequired('Google Calendar is not connected.')
    if conn.status == GoogleCalendarConnection.Status.REAUTH_REQUIRED:
        raise ReauthRequired('Google Calendar needs to be reconnected.')
    if conn.token_expires_at and conn.token_expires_at > timezone.now():
        token = decrypt(conn.access_token_enc)
        if token:
            return token
    refresh = decrypt(conn.refresh_token_enc)
    if not refresh:
        _mark_reauth(conn, 'No refresh token available.')
    status, token = http_json('POST', TOKEN_URL, form={
        'client_id': settings.GOOGLE_OAUTH_CLIENT_ID, 'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
        'refresh_token': refresh, 'grant_type': 'refresh_token'})
    if status != 200 or 'access_token' not in token:
        _mark_reauth(conn, 'Google refused to refresh the access token.')
    conn.access_token_enc = encrypt(token['access_token'])
    conn.token_expires_at = timezone.now() + timedelta(seconds=int(token.get('expires_in', 3600)) - 60)
    conn.save(update_fields=['access_token_enc', 'token_expires_at', 'updated_at'])
    return token['access_token']


def disconnect(user):
    conn = GoogleCalendarConnection.objects.filter(user=user).first()
    if not conn:
        return
    refresh = decrypt(conn.refresh_token_enc) or decrypt(conn.access_token_enc)
    if refresh:
        try:
            http_json('POST', REVOKE_URL, form={'token': refresh})
        except CalendarError:
            logger.warning('Google token revocation failed for user %s', user.pk)
    conn.access_token_enc = conn.refresh_token_enc = ''
    conn.token_expires_at = None
    conn.status = GoogleCalendarConnection.Status.DISCONNECTED
    conn.google_email = ''
    conn.save()


def _event_body(meeting, add_meet):
    pair = meeting.mentorship
    body = {
        'summary': meeting.title or 'Sangam mentoring session',
        'description': 'Scheduled through Sangam (IIC mentoring). Sangam does not record session discussions.',
        'start': {'dateTime': meeting.start_at.isoformat(), 'timeZone': meeting.timezone or settings.TIME_ZONE},
        'end': {'dateTime': meeting.end_at.isoformat(), 'timeZone': meeting.timezone or settings.TIME_ZONE},
        'attendees': [{'email': pair.student.email}],
        'reminders': {'useDefault': True},
    }
    if add_meet:
        body['conferenceData'] = {'createRequest': {'requestId': f'sangam-{meeting.pk}-{int(time.time())}',
                                                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}}}
    return body


def _store_event(meeting, owner, payload, event=None):
    event = event or MeetingCalendarEvent(meeting=meeting)
    event.calendar_owner = owner
    event.event_id = payload.get('id', event.event_id)
    event.html_link = payload.get('htmlLink', event.html_link)[:500]
    event.meet_link = (payload.get('hangoutLink') or event.meet_link or '')[:500]
    event.sync_status = MeetingCalendarEvent.SyncStatus.SYNCED
    event.last_synced_at = timezone.now()
    event.last_error = ''
    event.save()
    return event


def _record_failure(meeting, owner, message, event=None):
    event = event or MeetingCalendarEvent.objects.filter(meeting=meeting).first() or MeetingCalendarEvent(meeting=meeting)
    event.calendar_owner = owner
    event.sync_status = MeetingCalendarEvent.SyncStatus.FAILED
    event.last_error = message[:300]
    event.save()
    return event


def create_event(meeting, owner, add_meet=True):
    try:
        token = access_token(owner)
        status, payload = http_json('POST', f'{EVENTS_URL}?conferenceDataVersion=1&sendUpdates=all',
                                    body=_event_body(meeting, add_meet), token=token)
    except CalendarError as exc:
        return _record_failure(meeting, owner, str(exc))
    if status not in (200, 201):
        return _record_failure(meeting, owner, f'Google Calendar returned HTTP {status}.')
    return _store_event(meeting, owner, payload)


def update_event(meeting, owner):
    event = MeetingCalendarEvent.objects.filter(meeting=meeting).first()
    if not event or not event.event_id:
        return create_event(meeting, owner, add_meet=False)
    try:
        token = access_token(owner)
        body = _event_body(meeting, add_meet=False)
        status, payload = http_json('PATCH', f'{EVENTS_URL}/{quote(event.event_id)}?sendUpdates=all',
                                    body={k: body[k] for k in ('summary', 'start', 'end')}, token=token)
    except CalendarError as exc:
        return _record_failure(meeting, owner, str(exc), event)
    if status != 200:
        return _record_failure(meeting, owner, f'Google Calendar returned HTTP {status}.', event)
    return _store_event(meeting, owner, payload, event)


def cancel_event(meeting, owner):
    event = MeetingCalendarEvent.objects.filter(meeting=meeting).first()
    if not event or not event.event_id:
        return event
    try:
        token = access_token(owner)
        status, _ = http_json('DELETE', f'{EVENTS_URL}/{quote(event.event_id)}?sendUpdates=all', token=token)
    except CalendarError as exc:
        return _record_failure(meeting, owner, str(exc), event)
    if status not in (200, 204, 410):
        return _record_failure(meeting, owner, f'Google Calendar returned HTTP {status}.', event)
    event.sync_status = MeetingCalendarEvent.SyncStatus.CANCELLED
    event.last_synced_at = timezone.now()
    event.save(update_fields=['sync_status', 'last_synced_at'])
    return event

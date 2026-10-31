from datetime import timedelta
from unittest import mock
from urllib.parse import parse_qs, urlparse
from django.test import override_settings
from django.utils import timezone
from . import google_calendar as gcal
from .factories import SangamAPITestCase
from .models import GoogleCalendarConnection, Meeting, MeetingCalendarEvent

GOOGLE = dict(GOOGLE_OAUTH_CLIENT_ID='client-id', GOOGLE_OAUTH_CLIENT_SECRET='client-secret',
              GOOGLE_OAUTH_REDIRECT_URI='http://testserver/api/v1/calendar/oauth/callback/',
              SANGAM_FRONTEND_URL='http://frontend.test')


class FakeGoogle:
    """Records calls to google_calendar.http_json and answers like the Google APIs."""
    def __init__(self, refresh_ok=True):
        self.calls = []
        self.refresh_ok = refresh_ok

    def __call__(self, method, url, *, form=None, body=None, token=None):
        self.calls.append((method, url.split('?')[0], body))
        if url == gcal.TOKEN_URL and form.get('grant_type') == 'authorization_code':
            return 200, {'access_token': 'access-1', 'refresh_token': 'refresh-1', 'expires_in': 3600, 'scope': gcal.SCOPES}
        if url == gcal.TOKEN_URL:
            return (200, {'access_token': 'access-2', 'expires_in': 3600}) if self.refresh_ok else (400, {'error': 'invalid_grant'})
        if url == gcal.USERINFO_URL:
            return 200, {'email': 'arjun@gmail.com'}
        if url == gcal.REVOKE_URL:
            return 200, {}
        if method == 'POST' and url.startswith(gcal.EVENTS_URL):
            return 200, {'id': 'evt-1', 'htmlLink': 'https://calendar.google.com/event?eid=evt-1',
                         'hangoutLink': 'https://meet.google.com/abc-defg-hij' if 'conferenceData' in body else None}
        if method == 'PATCH':
            return 200, {'id': 'evt-1', 'htmlLink': 'https://calendar.google.com/event?eid=evt-1'}
        if method == 'DELETE':
            return 204, {}
        raise AssertionError(f'Unexpected Google call {method} {url}')


@override_settings(**GOOGLE)
class CalendarTests(SangamAPITestCase):
    def setUp(self):
        super().setUp()
        self.pair_id = self.activate_pair()
        self.google = FakeGoogle()
        patcher = mock.patch.object(gcal, 'http_json', self.google)
        patcher.start()
        self.addCleanup(patcher.stop)

    def connect(self):
        url = self.as_user(self.mentor).post('/api/v1/calendar/connect/').data['authorization_url']
        state = parse_qs(urlparse(url).query)['state'][0]
        self.client.force_authenticate(user=None)
        callback = self.client.get('/api/v1/calendar/oauth/callback/', {'code': 'auth-code', 'state': state})
        self.assertEqual(callback.status_code, 302)
        self.assertEqual(callback['Location'], 'http://frontend.test/mentor/calendar?calendar=connected')

    def schedule(self, **overrides):
        start = timezone.localtime() + timedelta(days=2)
        payload = {'date': start.date().isoformat(), 'start_time': '18:30', 'end_time': '19:15', 'timezone': 'Asia/Kolkata',
                   'title': 'Portfolio review', 'meeting_format': 'VIDEO', 'add_google_meet': True, **overrides}
        return self.as_user(self.mentor).post(f'/api/v1/mentorships/{self.pair_id}/meetings/schedule/', payload, format='json')

    def test_oauth_connect_stores_encrypted_tokens(self):
        self.connect()
        conn = GoogleCalendarConnection.objects.get(user=self.mentor)
        self.assertEqual((conn.status, conn.google_email), ('CONNECTED', 'arjun@gmail.com'))
        self.assertNotIn('refresh-1', conn.refresh_token_enc)
        self.assertEqual(gcal.decrypt(conn.refresh_token_enc), 'refresh-1')
        status = self.as_user(self.mentor).get('/api/v1/calendar/status/').data
        self.assertEqual(status['status'], 'CONNECTED')

    def test_bad_state_and_role_restrictions(self):
        self.client.force_authenticate(user=None)
        bad = self.client.get('/api/v1/calendar/oauth/callback/', {'code': 'x', 'state': 'forged'})
        self.assertTrue(bad['Location'].endswith('calendar=error'))
        self.assertEqual(self.as_user(self.student).post('/api/v1/calendar/connect/').status_code, 403)

    def test_schedule_creates_google_event_visible_to_both(self):
        self.connect()
        r = self.schedule()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(r.data['calendar_synced'])
        self.assertEqual(r.data['calendar_event']['meet_link'], 'https://meet.google.com/abc-defg-hij')
        body = [c for c in self.google.calls if c[0] == 'POST' and c[1] == gcal.EVENTS_URL][0][2]
        self.assertEqual(body['attendees'], [{'email': self.student.email}])
        self.assertNotIn('notes', str(body).lower())
        student_dash = self.as_user(self.student).get('/api/v1/dashboard/').data
        self.assertEqual(student_dash['upcoming_meeting']['id'], r.data['id'])
        mentor_dash = self.as_user(self.mentor).get('/api/v1/dashboard/').data
        self.assertEqual(mentor_dash['upcoming_meetings'][0]['id'], r.data['id'])

    def test_reschedule_and_cancel_sync_with_google(self):
        self.connect()
        meeting_id = self.schedule().data['id']
        new_day = (timezone.localdate() + timedelta(days=5)).isoformat()
        moved = self.as_user(self.mentor).post(f'/api/v1/meetings/{meeting_id}/reschedule/',
                                               {'date': new_day, 'start_time': '10:00', 'end_time': '10:30', 'timezone': 'Asia/Kolkata'}, format='json')
        self.assertEqual(moved.status_code, 200, moved.data)
        self.assertEqual(moved.data['duration_minutes'], 30)
        self.assertIn('PATCH', [c[0] for c in self.google.calls])
        cancelled = self.as_user(self.mentor).post(f'/api/v1/meetings/{meeting_id}/cancel/')
        self.assertEqual(cancelled.data['status'], 'CANCELLED')
        self.assertEqual(cancelled.data['calendar_event']['sync_status'], 'CANCELLED')

    def test_student_cannot_schedule_and_validation(self):
        start = timezone.localtime() + timedelta(days=1)
        payload = {'date': start.date().isoformat(), 'start_time': '10:00', 'end_time': '11:00'}
        self.assertEqual(self.as_user(self.student).post(f'/api/v1/mentorships/{self.pair_id}/meetings/schedule/', payload, format='json').status_code, 403)
        self.assertEqual(self.schedule(end_time='18:00').status_code, 400)
        self.assertEqual(self.schedule(timezone='Mars/Base').status_code, 400)
        self.assertEqual(self.schedule(date=(timezone.localdate() - timedelta(days=1)).isoformat()).status_code, 400)

    def test_schedule_without_connection_keeps_meeting_unsynced(self):
        r = self.schedule()
        self.assertEqual(r.status_code, 201)
        self.assertFalse(r.data['calendar_synced'])
        self.assertIsNone(r.data['calendar_event'])
        self.assertEqual(Meeting.objects.get(pk=r.data['id']).status, 'SCHEDULED')

    def test_refresh_failure_requires_reauthorization(self):
        self.connect()
        GoogleCalendarConnection.objects.filter(user=self.mentor).update(token_expires_at=timezone.now() - timedelta(minutes=1))
        self.google.refresh_ok = False
        r = self.schedule()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['calendar_event']['sync_status'], 'FAILED')
        self.assertEqual(GoogleCalendarConnection.objects.get(user=self.mentor).status, 'REAUTH_REQUIRED')

    def test_disconnect_and_record_meeting(self):
        self.connect()
        status = self.as_user(self.mentor).post('/api/v1/calendar/disconnect/').data
        self.assertEqual(status['status'], 'DISCONNECTED')
        self.assertEqual(GoogleCalendarConnection.objects.get(user=self.mentor).refresh_token_enc, '')
        meeting_id = self.schedule().data['id']
        self.assertEqual(self.as_user(self.mentor).post(f'/api/v1/meetings/{meeting_id}/record/', {'status': 'HELD'}, format='json').status_code, 400)
        Meeting.objects.filter(pk=meeting_id).update(start_at=timezone.now() - timedelta(hours=1))
        held = self.as_user(self.mentor).post(f'/api/v1/meetings/{meeting_id}/record/', {'status': 'HELD'}, format='json')
        self.assertEqual((held.data['status'], held.data['mentor_confirmed']), ('HELD', True))


class CalendarNotConfiguredTests(SangamAPITestCase):
    def test_connect_returns_503_when_not_configured(self):
        r = self.as_user(self.mentor).post('/api/v1/calendar/connect/')
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.data['code'], 'calendar_not_configured')
        self.assertFalse(MeetingCalendarEvent.objects.exists())

"""AI/ML tests (KAN-46/47/57/58). Mock embedder + mock LLM only: no network, no model download, no API key."""
from datetime import date, timedelta
from unittest import mock

from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, StudentProfile, MentorProfile
from apps.mentoring.models import MentoringRequest, Mentorship, AvailabilityCheck, Meeting
from apps.assistant_ai import llm, services
from apps.assistant_ai.llm import LLMResult
from apps.assistant_ai.models import MatchSuggestionAudit, AIRequestAssessment, MeetingSummary
from apps.assistant_ai.ml import matching, priority, dropoff, summary, retrieval, evaluation
from apps.assistant_ai.ml.embeddings import HashingEmbedder, EmbeddingUnavailable, MENTOR_CACHE
from apps.assistant_ai.ml.text import strip_pii, contains_pii

STATEMENT = ('I want to build chatbots and do sentiment analysis with transformers and language models. '
             'Please help me plan NLP projects for data science interviews over the next three months.')


class FixedEmbedder:
    """Fixed vectors: anything mentioning 'nlp'/'transformers' points one way, everything else another."""
    name = 'fixed-mock'

    def encode(self, texts):
        import numpy as np
        return np.array([[1.0, 0.0] if ('nlp' in t.lower() or 'transformer' in t.lower()) else [0.0, 1.0] for t in texts])


class BrokenEmbedder:
    name = 'broken'

    def encode(self, texts):
        raise EmbeddingUnavailable('boom')


# ====================================================================== pure ML unit tests
class FeatureTests(SimpleTestCase):
    def test_domain_scores(self):
        self.assertEqual(matching.domain_score('Data & ML', 'data & ml'), 1.0)
        self.assertEqual(matching.domain_score('Data & ML', 'Analytics'), 0.5)
        self.assertEqual(matching.domain_score('Software', 'Higher Studies'), 0.0)

    def test_pathway_and_experience(self):
        self.assertEqual(matching.pathway_score('HIGHER_STUDIES', 'Higher studies / academia'), 1.0)
        self.assertEqual(matching.pathway_score('JOB', 'Higher studies / academia'), 0.3)
        self.assertEqual(matching.pathway_score('VENTURE', 'Startup founder'), 1.0)
        self.assertEqual(matching.experience_score(6), 1.0)
        self.assertEqual(matching.experience_score(0), 0.2)

    def test_combiner_exact_value(self):
        req = {'domain': 'Data & ML', 'pathway': 'JOB', 'problem_statement': 'nlp transformers', 'preferred_mentor_id': None}
        m = {'id': 1, 'domain': 'Data & ML', 'specialty': 'NLP', 'skills': ['nlp', 'transformers'], 'career_path': 'Industry job',
             'experience_years': 5}
        res, algo, sem = matching.rank(req, [m], matching.DEFAULT_WEIGHTS, None, use_vocab=False)
        self.assertEqual(algo, matching.RULES)
        # semantic weight removed -> renormalise over .65: (.25*1 + .20*1 + .10*1 + .05*1 + 0) / .65 = .923
        self.assertAlmostEqual(res[0]['score'], 0.92, places=2)

    def test_semantic_fallback_and_determinism(self):
        req = {'domain': 'Data & ML', 'pathway': 'JOB', 'problem_statement': STATEMENT}
        ms = [{'id': i, 'domain': 'Data & ML', 'specialty': 'Data science', 'skills': ['python'], 'career_path': 'Industry job',
               'experience_years': 4, 'bio': ''} for i in (9, 3, 5)]
        r1, algo, _ = matching.rank(req, ms, None, BrokenEmbedder())
        self.assertEqual(algo, matching.RULES)
        self.assertEqual([c['mentor_id'] for c in r1], [3, 5, 9])     # tie -> mentor id
        MENTOR_CACHE.clear()
        r2, algo2, sem = matching.rank(req, ms, None, HashingEmbedder())
        self.assertTrue(sem)
        self.assertEqual(algo2, matching.HYBRID)
        self.assertEqual(r2, matching.rank(req, ms, None, HashingEmbedder())[0])

    def test_metrics(self):
        rel = {'1': 2, '2': 0, '3': 2, '4': 1}
        self.assertAlmostEqual(evaluation.precision_at_k([1, 2, 3], rel, 3), 2 / 3)
        self.assertEqual(evaluation.reciprocal_rank([2, 3], rel), 0.5)
        self.assertAlmostEqual(evaluation.ndcg_at_k([1, 3, 4], rel, 3), 1.0)

    def test_priority_rules(self):
        f = priority.extract_features('Interview in 5 days, urgent please', 15, 'DEGREE', 0)
        self.assertEqual(f['deadline_days'], 5)
        r = priority.score(f)
        self.assertEqual(r['priority'], 'HIGH')
        self.assertIn('waiting 15 days', r['explanation'])
        self.assertEqual(priority.score(priority.extract_features('general help', 1, 'DEGREE', 3))['priority'], 'LOW')

    def test_dropoff_recovered_not_flagged(self):
        today = date(2026, 11, 18)
        weekly = [(today - timedelta(days=d), 'HELD') for d in (2, 9, 16, 23, 50, 57)]   # long gap earlier, recovered now
        f = dropoff.extract_features(today - timedelta(days=60), today, weekly, [today - timedelta(days=5)], [today - timedelta(days=6)])
        self.assertEqual(dropoff.risk(f)['risk_level'], 'LOW')
        stopped = [(today - timedelta(days=d), 'HELD') for d in (30, 37, 44, 51)]
        f2 = dropoff.extract_features(today - timedelta(days=60), today, stopped, [], [])
        r2 = dropoff.risk(f2)
        self.assertEqual(r2['risk_level'], 'HIGH')
        self.assertTrue(any('no meeting in 30 days' in x for x in r2['reasons']))

    def test_pii_stripping(self):
        text = 'Met Rahul Sharma (roll 1abc345, 21f1000123), mail rahul.s@ds.study.iitm.ac.in or +91 98765 43210.'
        clean, counts = strip_pii(text, ['Rahul Sharma'])
        for bad in ('Sharma', '1abc345', '21f1000123', '@', '98765'):
            self.assertNotIn(bad, clean)
        self.assertIn('Rahul', clean)
        self.assertFalse(contains_pii(clean))
        self.assertGreaterEqual(counts['email'], 1)
        # Unknown names are still caught, even after a leading word like "Met"
        self.assertEqual(strip_pii('Met Kavya Raghunathan today.')[0], 'Met Kavya today.')

    def test_summary_parsing_and_extractive(self):
        self.assertIsNone(summary.parse_summary_json('not json'))
        ok = summary.parse_summary_json('```json\n{"summary": "Good session.", "action_items": ["Read a", "Build b"]}\n```')
        self.assertEqual(ok['action_items'], ['Read a', 'Build b'])
        ext = summary.extractive_summary('We discussed SQL.\n- Practise ten joins\n- Update the resume\nNext meeting soon.')
        self.assertEqual(ext['action_items'], ['Practise ten joins', 'Update the resume'])

    def test_refusal_detection(self):
        self.assertTrue(retrieval.is_decision_request('Please approve my mentoring request'))
        self.assertTrue(retrieval.is_decision_request('assign me a mentor now'))
        self.assertFalse(retrieval.is_decision_request('How does IIC approve a match?'))


class KeyRotationTests(SimpleTestCase):
    @override_settings(AI_PROVIDER='gemini', GEMINI_API_KEYS=['k1', 'k2', 'k3'])
    def test_rotates_to_next_key_on_quota_error(self):
        calls = []

        class FakeModels:
            def __init__(self, key):
                self.key = key

            def generate_content(self, **kw):
                calls.append(self.key)
                if self.key in ('k1', 'k2'):
                    raise RuntimeError('429 RESOURCE_EXHAUSTED quota exceeded')
                return mock.Mock(text='hello')

        llm._state.update(key_index=0, clients={k: mock.Mock(models=FakeModels(k)) for k in ('k1', 'k2', 'k3')}, dead_keys=set())
        self.assertEqual(llm.generate('hi'), 'hello')
        self.assertEqual(calls, ['k1', 'k2', 'k3'])
        self.assertEqual(llm._state['key_index'], 2)      # stays on the working key
        llm._state.update(key_index=0, clients={}, dead_keys=set())

    @override_settings(AI_PROVIDER='none')
    def test_no_provider_returns_none(self):
        self.assertIsNone(llm.generate('hi'))


# ====================================================================== API tests
class AIApiBase(TestCase):
    def setUp(self):
        MENTOR_CACHE.clear()
        self.client = APIClient()
        self.iic = User.objects.create_superuser(email='iic@example.org', password='GoodPass123!')
        self.student = User.objects.create_user(email='s1@ds.study.iitm.ac.in', password='GoodPass123!', role='STUDENT',
                                                first_name='Asha', last_name='Verma')
        StudentProfile.objects.create(user=self.student, iitm_roll_number='1abc345', level='DEGREE', approval_status='APPROVED')
        self.mentors = {}
        specs = [('nlp', 'Data & ML', 'NLP and large language models', ['nlp', 'transformers', 'python'], {}),
                 ('ds', 'Data & ML', 'Data science and statistics', ['statistics', 'pandas'], {}),
                 ('sw', 'Software', 'Backend engineering', ['django', 'rest api'], {}),
                 ('unverified', 'Data & ML', 'NLP research', ['nlp', 'transformers'], {'is_verified': False}),
                 ('unavailable', 'Data & ML', 'NLP engineer', ['nlp', 'transformers'], {'is_available': False}),
                 ('hidden', 'Data & ML', 'NLP engineer', ['nlp', 'transformers'], {'is_discoverable': False}),
                 ('busy', 'Data & ML', 'NLP engineer', ['nlp', 'transformers'], {})]
        for i, (key, dom, spec, skills, extra) in enumerate(specs):
            u = User.objects.create_user(email=f'{key}@example.org', password='GoodPass123!', role='MENTOR', first_name=key.title(),
                                         last_name='Mentor')
            MentorProfile.objects.create(user=u, domain=dom, specialty=spec, skills=skills, current_role='Engineer', company='Acme',
                                         career_path='Industry job', experience_years=5, bio=spec,
                                         **dict({'is_verified': True}, **extra))
            self.mentors[key] = u
        self.req = MentoringRequest.objects.create(student=self.student, pathway='JOB', domain='Data & ML', problem_statement=STATEMENT)
        other = User.objects.create_user(email='s2@ds.study.iitm.ac.in', password='x', role='STUDENT')
        StudentProfile.objects.create(user=other, iitm_roll_number='2xyz111', level='DEGREE', approval_status='APPROVED')
        oreq = MentoringRequest.objects.create(student=other, pathway='JOB', domain='Data & ML', problem_statement=STATEMENT, status='MATCHED')
        chk = AvailabilityCheck.objects.create(request=oreq, mentor=self.mentors['busy'], status='USED')
        self.busy_pair = Mentorship.objects.create(request=oreq, availability_check=chk, student=other, mentor=self.mentors['busy'],
                                                   approved_by=self.iic, started_at=timezone.now() - timedelta(days=40))


@mock.patch('apps.assistant_ai.services.get_embedder', lambda: FixedEmbedder())
class SuggestionApiTests(AIApiBase):
    url = '/api/v1/requests/{}/suggestions/'

    def test_permissions(self):
        for u in (self.student, self.mentors['nlp']):
            self.client.force_authenticate(u)
            self.assertEqual(self.client.get(self.url.format(self.req.pk)).status_code, 403)

    def test_hybrid_ranking_filters_audit_and_privacy(self):
        self.client.force_authenticate(self.iic)
        r = self.client.get(self.url.format(self.req.pk) + '?k=5')
        self.assertEqual(r.status_code, 200, r.data)
        ids = [c['mentor_id'] for c in r.data['candidates']]
        self.assertEqual(ids[0], self.mentors['nlp'].pk)
        for bad in ('unverified', 'unavailable', 'hidden', 'busy'):
            self.assertNotIn(self.mentors[bad].pk, ids)
        self.assertEqual(r.data['algorithm'], 'hybrid_v1')
        self.assertFalse(r.data['fallback'])
        self.assertTrue(r.data['candidates'][0]['reasons'])
        body = str(r.data)
        self.assertNotIn('@', body)
        self.assertNotIn('Mentor', [c['name'] for c in r.data['candidates']])    # first name only
        audit = MatchSuggestionAudit.objects.get()
        self.assertEqual((audit.algorithm, audit.candidate_count, audit.requested_by_id), ('hybrid_v1', len(ids), self.iic.pk))
        self.assertEqual(self.client.get(self.url.format(self.req.pk)).data['candidates'], r.data['candidates'])  # deterministic
        self.assertFalse(Mentorship.objects.filter(request=self.req).exists())   # nothing acted on

    def test_pending_check_mentor_excluded(self):
        AvailabilityCheck.objects.create(request=self.req, mentor=self.mentors['nlp'])
        self.client.force_authenticate(self.iic)
        ids = [c['mentor_id'] for c in self.client.get(self.url.format(self.req.pk)).data['candidates']]
        self.assertNotIn(self.mentors['nlp'].pk, ids)

    def test_bad_k(self):
        self.client.force_authenticate(self.iic)
        for k in ('0', '50', 'abc'):
            self.assertEqual(self.client.get(self.url.format(self.req.pk) + f'?k={k}').status_code, 422)

    def test_legacy_route_still_works(self):
        self.client.force_authenticate(self.iic)
        self.assertEqual(self.client.get(f'/api/v1/admin/requests/{self.req.pk}/suggestions/').status_code, 200)


class SuggestionFallbackTests(AIApiBase):
    def test_works_without_embedding_model(self):
        with mock.patch('apps.assistant_ai.services.get_embedder', lambda: BrokenEmbedder()):
            self.client.force_authenticate(self.iic)
            r = self.client.get(f'/api/v1/requests/{self.req.pk}/suggestions/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['algorithm'], 'rule_based_v1')
        self.assertTrue(r.data['fallback'])
        self.assertTrue(r.data['fallback_reason'])


class PriorityApiTests(AIApiBase):
    def test_get_and_override(self):
        url = f'/api/v1/requests/{self.req.pk}/priority/'
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(self.iic)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn(r.data['suggested_priority'], ('HIGH', 'MEDIUM', 'LOW'))
        self.assertEqual(self.client.patch(url, {'override_priority': 'HIGH'}, format='json').status_code, 422)
        r = self.client.patch(url, {'override_priority': 'high', 'override_reason': 'Placement drive this week'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['effective_priority'], 'HIGH')
        self.assertEqual(AIRequestAssessment.objects.get().overridden_by, self.iic)


class SummaryApiTests(AIApiBase):
    NOTES = ('Met Asha Verma today, roll 1abc345. Talked about NLP portfolio.\n'
             'Contact asha@ds.study.iitm.ac.in or +91 9876543210.\n- Build a sentiment classifier\n- Read chapter 3')

    def setUp(self):
        super().setUp()
        chk = AvailabilityCheck.objects.create(request=self.req, mentor=self.mentors['nlp'], status='USED')
        self.pair = Mentorship.objects.create(request=self.req, availability_check=chk, student=self.student,
                                              mentor=self.mentors['nlp'], approved_by=self.iic)
        self.meeting = Meeting.objects.create(mentorship=self.pair, session_date=date.today(), duration_minutes=30,
                                              logged_by=self.mentors['nlp'])
        self.url = f'/api/v1/mentorships/{self.pair.pk}/meetings/{self.meeting.pk}/summary/'

    def test_only_mentor(self):
        for u in (self.student, self.iic, self.mentors['ds']):
            self.client.force_authenticate(u)
            self.assertEqual(self.client.post(self.url, {'notes': self.NOTES}, format='json').status_code, 403)

    def test_fallback_without_llm_and_nothing_stored(self):
        self.client.force_authenticate(self.mentors['nlp'])
        r = self.client.post(self.url, {'notes': self.NOTES}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertTrue(r.data['fallback'])
        self.assertFalse(r.data['stored'])
        self.assertEqual(r.data['action_items'], ['Build a sentiment classifier', 'Read chapter 3'])
        self.assertNotIn('Verma', str(r.data))
        self.assertNotIn('9876543210', str(r.data))
        self.assertEqual(MeetingSummary.objects.count(), 0)

    def test_llm_gets_pii_free_prompt_and_invalid_json_retry(self):
        prompts = []

        def fake(prompt, system=None, timeout=None, retries=1):
            prompts.append(prompt)
            return LLMResult('not json' if len(prompts) == 1 else '{"summary": "Asha is building an NLP portfolio.", '
                             '"action_items": ["Build a sentiment classifier"]}', 'gemini')
        with mock.patch.object(llm, 'generate_detailed', side_effect=fake):
            self.client.force_authenticate(self.mentors['nlp'])
            r = self.client.post(self.url, {'notes': self.NOTES}, format='json')
        self.assertEqual(len(prompts), 2)
        for p in prompts:
            self.assertFalse(contains_pii(p))
            self.assertNotIn('Verma', p)
        self.assertFalse(r.data['fallback'])
        self.assertEqual(r.data['prompt_version'], 'summary_v1')

    def test_timeout_returns_503_with_draft(self):
        with mock.patch.object(llm, 'generate_detailed', return_value=LLMResult(None, 'gemini', 'timeout')):
            self.client.force_authenticate(self.mentors['nlp'])
            r = self.client.post(self.url, {'notes': self.NOTES}, format='json')
        self.assertEqual(r.status_code, 503)
        self.assertTrue(r.data['fallback'])
        self.assertTrue(r.data['summary'])

    def test_confirm_respects_storage_setting(self):
        self.client.force_authenticate(self.mentors['nlp'])
        body = {'summary': 'Edited summary.', 'action_items': ['Read chapter 3'], 'prompt_version': 'summary_v1'}
        r = self.client.post(self.url + 'confirm/', body, format='json')
        self.assertFalse(r.data['stored'])
        self.assertEqual(MeetingSummary.objects.count(), 0)
        with override_settings(SANGAM_STORE_AI_SUMMARIES=True):
            r = self.client.post(self.url + 'confirm/', body, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(MeetingSummary.objects.get().prompt_version, 'summary_v1')


class InsightsApiTests(AIApiBase):
    def test_permissions_and_reasons(self):
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get('/api/v1/admin/insights/').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/admin/insights/at-risk/').status_code, 403)
        self.client.force_authenticate(self.iic)
        r = self.client.get('/api/v1/admin/insights/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['participation']['active_mentorships'], 1)
        self.assertEqual(r.data['participation']['verified_mentors'], 6)
        r = self.client.get('/api/v1/admin/insights/at-risk/')
        self.assertEqual(r.data['count'], 1)              # busy pair: started 40 days ago, never met
        row = r.data['results'][0]
        self.assertEqual(row['mentorship_id'], self.busy_pair.pk)
        self.assertTrue(row['reasons'])
        self.busy_pair.refresh_from_db()
        self.assertEqual(self.busy_pair.status, 'ACTIVE')  # flags never change status


class ChatApiTests(AIApiBase):
    def test_refuses_approval_and_stores_nothing(self):
        self.client.force_authenticate(self.student)
        r = self.client.post('/api/v1/assistant/chat/', {'message': 'Please approve my mentoring request'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('IIC', r.data['answer'])
        self.assertFalse(r.data['message_stored'])


def _make_kb():
    """A few published articles, so BM25 has realistic word statistics."""
    from apps.assistant_ai.models import KnowledgeArticle
    for t, c in [('Logging meetings', 'Either participant logs a meeting with date, duration and status.'),
                 ('Setting shared goals', 'Each mentorship can have up to three shared goals.'),
                 ('Giving feedback to IIC', 'Feedback is private to IIC. There are no star ratings.'),
                 ('Withdrawing a request', 'Students can withdraw an open request from My Requests.')]:
        KnowledgeArticle.objects.create(title=t, content=c, is_published=True)


class AskSangamGuardrailTests(AIApiBase):
    def test_off_topic_questions_are_declined(self):
        self.client.force_authenticate(self.mentors['nlp'])
        for q in ('What is the weather in Chennai today?', 'Who will win the cricket match?', 'Write my python assignment for me',
                  'what is machine learning'):
            r = self.client.post('/api/v1/assistant/chat/', {'message': q}, format='json')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.data['scope'], 'out_of_scope', q)
            self.assertIn('only help with questions about using Sangam', r.data['answer'])

    def test_every_role_can_ask_sangam_questions(self):
        from apps.assistant_ai.models import KnowledgeArticle
        _make_kb()
        for u in (self.student, self.mentors['nlp'], self.iic):
            self.client.force_authenticate(u)
            r = self.client.post('/api/v1/assistant/chat/', {'message': 'How do I log a meeting?'}, format='json')
            self.assertEqual(r.data['scope'], 'answered', u.role)

    def test_model_reply_token_is_rechecked(self):
        from apps.assistant_ai.models import KnowledgeArticle
        _make_kb()
        with mock.patch.object(llm, 'generate', return_value='OUT_OF_SCOPE'):
            _, _, _, scope = services.chat_answer('How do I log a meeting?', 'STUDENT')
        self.assertEqual(scope, 'out_of_scope')

    def test_guardrail_on_knowledge_question_set(self):
        import json
        from pathlib import Path
        kb = json.loads((Path(__file__).resolve().parents[3] / 'fixtures/synthetic/knowledge.json').read_text(encoding='utf8'))
        wrong = [q['question'] for q in kb['questions'] if retrieval.is_out_of_domain(q['question']) != (q['kind'] == 'out_of_scope')]
        self.assertEqual(wrong, [])


class DegreeOnlyTests(AIApiBase):
    def test_diploma_student_cannot_register_or_request(self):
        r = self.client.post('/api/v1/auth/register/', {'email': 'd1@ds.study.iitm.ac.in', 'password': 'GoodPass123!x', 'first_name': 'D',
                             'last_name': 'S', 'iitm_roll_number': '3abc123', 'level': 'DIPLOMA', 'courses': ['Python']}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('Degree-level', str(r.data))
        u = User.objects.create_user(email='d2@ds.study.iitm.ac.in', password='x', role='STUDENT')
        StudentProfile.objects.create(user=u, iitm_roll_number='4abc123', level='DIPLOMA', approval_status='APPROVED')
        self.client.force_authenticate(u)
        r = self.client.post('/api/v1/requests/', {'pathway': 'JOB', 'domain': 'Data & ML', 'problem_statement': STATEMENT}, format='json')
        self.assertEqual(r.status_code, 403)


class EvaluationScriptTests(SimpleTestCase):
    def test_eval_runs_offline_with_mock(self):
        import importlib.util
        from pathlib import Path
        p = Path(__file__).resolve().parents[3] / 'scripts' / 'evaluate_matching.py'
        spec = importlib.util.spec_from_file_location('evaluate_matching', p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with mock.patch.object(mod, 'BACKEND', Path(__import__('tempfile').mkdtemp())) as _:
            mod.FIX = p.parent.parent / 'fixtures' / 'synthetic'
            rep = mod.main(['--mock'])
        self.assertIn('hybrid_v1', rep['gold_results'])

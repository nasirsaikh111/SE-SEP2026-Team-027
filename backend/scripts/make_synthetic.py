"""Generate Sangam's synthetic datasets (Section 7 of the AI/ML work plan).

Run from backend/:  python scripts/make_synthetic.py
Output: backend/fixtures/synthetic/*.json  (every record carries "is_synthetic": true)

All data is fake. Fixed seed -> identical output on every machine.
Relevance / priority / drop-off labels are produced by the written rubrics below
(plus deliberate label noise to imitate human disagreement). The team should
spot-check the gold file before it is reported as human-labelled.
"""
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    from faker import Faker
except ImportError:  # pragma: no cover
    Faker = None

SEED = 27
OUT = Path(__file__).resolve().parent.parent / 'fixtures' / 'synthetic'
AS_OF = date(2026, 11, 18)
rng = random.Random(SEED)
fake = Faker('en_IN') if Faker else None
if fake:
    fake.seed_instance(SEED)

FALLBACK_FIRST = ['Aarav', 'Diya', 'Rohan', 'Ananya', 'Kabir', 'Isha', 'Arjun', 'Meera', 'Vikram', 'Sneha', 'Karan', 'Pooja']
FALLBACK_LAST = ['Sharma', 'Iyer', 'Reddy', 'Gupta', 'Nair', 'Das', 'Mehta', 'Khan', 'Bose', 'Patel', 'Rao', 'Singh']


def person():
    if fake:
        return fake.first_name(), fake.last_name()
    return rng.choice(FALLBACK_FIRST), rng.choice(FALLBACK_LAST)


# ---------------------------------------------------------------- topic catalogue
# skills = tags a mentor lists; phrases = how a *student* describes the same need
# Each topic: field, mentor specialty, mentor skill tags, and how students describe the need
TOPICS = {
    'backend': ('Software', 'Backend engineering and APIs',
                ['python', 'django', 'rest api', 'postgresql', 'system design', 'microservices', 'java', 'spring boot', 'redis'],
                ['building scalable web services', 'designing the server side of an app', 'database design and slow queries',
                 'how large websites handle millions of users', 'writing APIs for a mobile app', 'backend developer roles']),
    'frontend': ('Software', 'Frontend and web UI development',
                 ['javascript', 'react', 'vue', 'typescript', 'css', 'html', 'web performance', 'accessibility'],
                 ['making websites look good and load fast', 'building interactive user interfaces', 'single page web apps',
                  'frontend developer interviews', 'learning a modern web framework']),
    'devops': ('Software', 'Cloud, DevOps and infrastructure',
               ['aws', 'docker', 'kubernetes', 'ci/cd', 'linux', 'terraform', 'monitoring', 'cloud'],
               ['deploying applications to the cloud', 'automating builds and releases', 'containers and servers',
                'site reliability roles', 'cloud certification preparation']),
    'mobile': ('Software', 'Android and mobile app development',
               ['android', 'kotlin', 'flutter', 'swift', 'mobile ui', 'firebase', 'play store'],
               ['building phone apps', 'publishing an app on the play store', 'cross platform apps for android and ios',
                'mobile developer internships']),
    'dsa': ('Software', 'DSA and coding interview preparation',
            ['data structures', 'algorithms', 'competitive programming', 'leetcode', 'c++', 'problem solving', 'interviews'],
            ['cracking coding rounds at product companies', 'getting better at leetcode style problems', 'online assessments for placements',
             'graphs and dynamic programming questions', 'technical interview practice']),
    'mleng': ('Data & ML', 'Machine learning engineering and MLOps',
              ['machine learning', 'pytorch', 'mlops', 'model deployment', 'scikit-learn', 'python', 'feature engineering'],
              ['taking a model from notebook to production', 'serving predictions behind an API', 'ML engineer roles',
               'training and tuning models', 'end to end machine learning projects']),
    'nlp': ('Data & ML', 'NLP and large language models',
            ['nlp', 'transformers', 'llm', 'hugging face', 'text classification', 'python', 'prompt engineering'],
            ['building chatbots', 'sentiment analysis on reviews', 'working with language models like GPT',
             'text classification and summarisation', 'generative AI projects']),
    'cv': ('Data & ML', 'Computer vision and deep learning',
           ['computer vision', 'opencv', 'cnn', 'deep learning', 'pytorch', 'image segmentation', 'object detection'],
           ['detecting objects in images', 'face recognition projects', 'medical image analysis', 'working with camera and video data']),
    'datasci': ('Data & ML', 'Data science and statistics',
                ['statistics', 'pandas', 'hypothesis testing', 'regression', 'data science', 'python', 'kaggle'],
                ['finding insights in messy datasets', 'statistical modelling', 'kaggle competitions',
                 'data scientist interviews', 'probability and inference']),
    'bizanalytics': ('Analytics', 'Business analytics and BI dashboards',
                     ['sql', 'excel', 'power bi', 'tableau', 'dashboards', 'business analytics', 'reporting'],
                     ['making dashboards for managers', 'analyst roles in consulting', 'writing queries to answer business questions',
                      'reporting and KPIs', 'excel and visualisation skills']),
    'prodanalytics': ('Analytics', 'Product analytics and experimentation',
                      ['a/b testing', 'sql', 'product analytics', 'funnel analysis', 'experimentation', 'python', 'metrics'],
                      ['measuring how users use an app', 'running experiments on features', 'retention and funnel metrics',
                       'product analyst roles']),
    'finanalytics': ('Analytics', 'Financial and risk analytics',
                     ['finance', 'risk modelling', 'excel', 'sql', 'credit risk', 'time series', 'banking'],
                     ['analytics jobs in banks', 'credit scoring and fraud', 'stock market and forecasting', 'fintech analyst roles']),
    'pm': ('Product', 'Product management',
           ['product management', 'roadmaps', 'prd', 'user research', 'prioritisation', 'stakeholder management', 'agile'],
           ['becoming a product manager', 'deciding what features to build', 'apm program interviews',
            'writing product requirement documents', 'moving from engineering to product']),
    'ux': ('Product', 'UX and product design',
           ['ux design', 'figma', 'wireframes', 'usability testing', 'design systems', 'prototyping', 'ui design'],
           ['designing app screens', 'building a design portfolio', 'user experience careers', 'making products easy to use']),
    'growth': ('Product', 'Growth, startups and venture building',
               ['startups', 'growth marketing', 'fundraising', 'go to market', 'entrepreneurship', 'mvp', 'pitch deck'],
               ['starting my own company', 'finding first customers', 'raising money for an idea', 'building a minimum viable product']),
    'msabroad': ('Higher Studies', 'MS admissions abroad',
                 ['gre', 'toefl', 'sop', 'lor', 'ms applications', 'university shortlisting', 'scholarships'],
                 ['applying for masters in the US or Germany', 'writing a statement of purpose', 'choosing universities abroad',
                  'recommendation letters and GRE scores']),
    'phd': ('Higher Studies', 'PhD and research careers',
            ['research', 'phd', 'publications', 'research proposal', 'academia', 'literature review', 'conferences'],
            ['getting into a PhD program', 'publishing my first paper', 'research internships with professors', 'academic career']),
    'mba': ('Higher Studies', 'MBA admissions',
            ['mba', 'cat', 'gmat', 'b-school interviews', 'case studies', 'management'],
            ['preparing for CAT', 'getting into a good b-school', 'MBA after a few years of work', 'group discussion and interview prep']),
    'gate': ('Higher Studies', 'GATE and MTech in India',
             ['gate', 'mtech', 'iit admissions', 'psu jobs', 'exam strategy', 'computer science fundamentals'],
             ['preparing for GATE CS', 'MTech at an IIT', 'PSU jobs through GATE', 'exam strategy for core subjects']),
}
DOMAINS = sorted({t[0] for t in TOPICS.values()})
HIGHER = 'Higher Studies'
HINGLISH = ['mujhe samajh nahi aa raha ki kaise start karu', 'thoda confusion hai', 'kya karna chahiye pata nahi',
            'please guide karo', 'bahut time waste ho raha hai']
VAGUE = ['I need help with my career and do not know what to do next.',
         'need guidance, confused about future. please help me decide something.',
         'I want a mentor who can help me grow overall as a professional.']
URGENT = ['urgent', 'asap', 'as soon as possible', 'jaldi', 'immediately']


def typo(text, rate=0.08):
    words = text.split()
    for i, w in enumerate(words):
        if len(w) > 4 and rng.random() < rate:
            j = rng.randrange(1, len(w) - 1)
            words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:]
    return ' '.join(words)


# ---------------------------------------------------------------- mentors
# Mentors spread evenly over topics, with some deliberately ineligible
def make_mentors(n=90):
    keys = list(TOPICS)
    mentors = []
    for i in range(n):
        topic = keys[i % len(keys)] if i < len(keys) * 4 else rng.choice(keys)
        domain, specialty, skills, phrases = TOPICS[topic]
        sib = rng.choice([k for k in keys if TOPICS[k][0] == domain and k != topic] or [topic])
        if rng.random() < 0.2:  # some cross-domain mentors
            sib = rng.choice(keys)
        tags = rng.sample(skills, k=min(len(skills), rng.randint(4, 6))) + rng.sample(TOPICS[sib][2], k=2)
        tags = list(dict.fromkeys(tags))[:10]
        first, last = person()
        years = rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 10, 12])
        academic = domain == HIGHER and rng.random() < 0.7
        if topic == 'growth':
            career = 'Startup founder'
        elif academic:
            career = 'Higher studies / academia'
        else:
            career = 'Industry job'
        company = rng.choice(['Flipkart', 'Zoho', 'Infosys', 'Razorpay', 'Swiggy', 'TCS', 'Freshworks', 'Microsoft', 'Google', 'Amazon',
                              'IIT Madras', 'TU Munich', 'CMU', 'Own startup', 'Deloitte', 'HDFC Bank'])
        bio = (f'{first} has {years} years of experience in {specialty.lower()}. '
               f'Works on {rng.choice(phrases)} and {rng.choice(phrases)}. '
               f'Comfortable with {", ".join(tags[:4])}. Happy to help students with {rng.choice(phrases)} '
               f'and to share lessons from {rng.choice(TOPICS[sib][3])}.')
        # Roughly 30 percent are unverified, unavailable, hidden or already matched
        r = rng.random()
        mentors.append({
            'id': 1000 + i, 'first_name': first, 'last_name': last,
            'email': f'{first.lower()}.{last.lower()}{i}@example.org',
            'domain': domain, 'specialty': specialty, 'skills': tags, 'career_path': career,
            'current_role': rng.choice(['Senior Engineer', 'Data Scientist', 'Analyst', 'Product Manager', 'Researcher', 'Consultant', 'Founder']),
            'company': company, 'experience_years': years, 'bio': bio,
            'is_verified': r >= 0.10, 'is_available': not (0.10 <= r < 0.18), 'is_discoverable': not (0.18 <= r < 0.23),
            'has_active_mentorship': 0.23 <= r < 0.30,
            'primary_topic': topic, 'secondary_topic': sib, 'is_synthetic': True,
        })
    return mentors


def eligible(m):
    return m['is_verified'] and m['is_available'] and m['is_discoverable'] and not m['has_active_mentorship']


# ---------------------------------------------------------------- students
def make_students(n=130):
    out = []
    for i in range(n):
        first, last = person()
        # Deliberately NOT the real IITM roll format: placeholder like 1abc345
        roll = f"{rng.randint(1, 9)}{''.join(rng.choice('abcdefghjkmnpqrstuvwxyz') for _ in range(3))}{rng.randint(100, 999)}"
        # Sangam is Degree level only. This draw is unused but keeps the random stream (and the rest of the data) unchanged
        rng.choice([0, 1, 2])
        out.append({'id': 5000 + i, 'first_name': first, 'last_name': last, 'email': f'{roll}@ds.study.iitm.ac.in',
                    'iitm_roll_number': roll, 'level': 'DEGREE',
                    'courses': rng.sample(['Python', 'DBMS', 'MLF', 'MLT', 'MLP', 'BDM', 'MAD-I', 'MAD-II', 'Stats-II', 'DL', 'SE', 'PDSA'], 4),
                    'cgpa': round(rng.uniform(6.0, 9.8), 2), 'approval_status': rng.choice(['APPROVED'] * 8 + ['PENDING', 'REJECTED']),
                    'is_synthetic': True})
    return out


# ---------------------------------------------------------------- requests (+ priority ground truth)
# Requests written in student language, with typos, Hinglish and vague cases
def make_requests(students, mentors, n=180):
    keys = list(TOPICS)
    out = []
    for i in range(n):
        topic = rng.choice(keys)
        domain, specialty, skills, phrases = TOPICS[topic]
        st = students[i % len(students)]
        pathway = ('HIGHER_STUDIES' if domain == HIGHER else 'VENTURE' if topic == 'growth'
                   else rng.choice(['JOB'] * 6 + ['UNSURE']))
        # About 15 percent pick the wrong domain, like real students sometimes do
        picked_domain = domain if rng.random() > 0.15 else rng.choice([d for d in DOMAINS if d != domain])
        parts = [f'I am a {st["level"].lower()} level student in the IITM BS program.',
                 f'I am interested in {rng.choice(phrases)} and {rng.choice(phrases)}.']
        if rng.random() < 0.45:
            parts.append(f'I have tried a bit of {rng.choice(skills)} on my own.')
        parts.append(rng.choice([
            'I want a structured plan with milestones for the next three months.',
            'I am not sure which projects to build to get shortlisted.',
            'I would like feedback on my resume and project portfolio.',
            'I want to understand what the day to day work looks like and how to prepare.']))
        # priority ground truth signals
        days_waiting = rng.choice([0, 1, 2, 3, 5, 7, 9, 12, 15, 18, 22, 28])
        deadline_days = rng.choice([None, None, None, 5, 10, 20, 45])
        if deadline_days is not None:
            parts.append(rng.choice([f'My application deadline is in {deadline_days} days.',
                                     f'I have an interview in {deadline_days} days.',
                                     f'Applications close in {deadline_days} days.']))
        urgent = rng.random() < 0.2
        if urgent:
            parts.append(f'This is {rng.choice(URGENT)}, please help.')
        if rng.random() < 0.12:
            parts.append(rng.choice(HINGLISH) + '.')
        text = ' '.join(parts)
        if rng.random() < 0.08:
            text = rng.choice(VAGUE) + ' ' + parts[0]
        if rng.random() < 0.10:
            text = typo(text)
        prior_withdrawals = rng.choice([0, 0, 0, 0, 1, 1, 2, 3])
        preferred = None
        if rng.random() < 0.15:
            preferred = rng.choice([m['id'] for m in mentors if m['primary_topic'] == topic] or [None])
        submitted = datetime.combine(AS_OF - timedelta(days=days_waiting), datetime.min.time()).replace(hour=10)
        out.append({'id': 20000 + i, 'student_id': st['id'], 'pathway': pathway, 'domain': picked_domain,
                    'problem_statement': text, 'preferred_mentor_id': preferred,
                    'submitted_at': submitted.isoformat(), 'status': rng.choice(['SUBMITTED', 'UNDER_REVIEW', 'WAITING']),
                    'true_topic': topic, 'student_level': st['level'], 'prior_withdrawals': prior_withdrawals,
                    'gt_days_waiting': days_waiting, 'gt_deadline_days': deadline_days, 'gt_urgent': urgent,
                    'is_synthetic': True})
    return out


# Labelling rubric: 2 good fit, 1 fair, 0 poor
def relevance(req, m):
    """Rubric: 2 good = mentor's primary topic is the student's need; 1 fair = secondary topic or same field; 0 poor."""
    if not eligible(m):
        return 0
    t = req['true_topic']
    if m['primary_topic'] == t:
        return 2
    if m['secondary_topic'] == t or TOPICS[m['primary_topic']][0] == TOPICS[t][0]:
        return 1
    return 0


# Label every mentor for 100 requests, then split 70 tuning and 30 held-out
def make_labels(reqs, mentors):
    pool = [r for r in reqs if r['problem_statement']]
    chosen = rng.sample(pool, 100)
    labelled = []
    for r in chosen:
        rels = {}
        for m in mentors:
            rel = relevance(r, m)
            if rel and rng.random() < 0.05:   # annotator disagreement
                rel = max(0, min(2, rel + rng.choice([-1, 1])))
            rels[str(m['id'])] = rel
        labelled.append({'request_id': r['id'], 'relevance': rels, 'is_synthetic': True})
    return labelled[:70], labelled[70:]   # 70 % tuning, 30 % held-out gold


PRIORITY_RUBRIC = """High >= 3 points, Medium 1-2, Low <= 0.
+2 waiting >= 14 days, +1 waiting 7-13 days; +2 deadline/interview within 14 days, +1 within 30 days;
+1 urgency words; -1 two or more prior withdrawals. (All students are Degree level, so level is not scored.)"""


# Apply the written priority rubric, then add a little rater noise
def priority_label(r):
    pts = 0
    d = r['gt_days_waiting']
    pts += 2 if d >= 14 else 1 if d >= 7 else 0
    dl = r['gt_deadline_days']
    if dl is not None:
        pts += 2 if dl <= 14 else 1 if dl <= 30 else 0
    pts += 1 if r['gt_urgent'] else 0
    pts -= 1 if r['prior_withdrawals'] >= 2 else 0
    label = 'HIGH' if pts >= 3 else 'MEDIUM' if pts >= 1 else 'LOW'
    if rng.random() < 0.07:   # rater noise
        label = rng.choice([x for x in ('HIGH', 'MEDIUM', 'LOW') if x != label])
    return label


# ---------------------------------------------------------------- timelines (drop-off)
# Simulate weekly activity in four patterns: healthy, fading, sudden stop, recovered
def make_timelines(n=110):
    patterns = ['healthy'] * 45 + ['fading'] * 25 + ['sudden_stop'] * 20 + ['recovered'] * 20
    rng.shuffle(patterns)
    out = []
    for i in range(n):
        p = patterns[i % len(patterns)]
        weeks = rng.randint(8, 12)
        start = AS_OF - timedelta(weeks=weeks)
        meetings, days = [], []
        if p == 'healthy':
            d = rng.randint(0, 4)
            while d < weeks * 7:
                days.append(d); d += rng.choice([6, 7, 7, 8, 10, 14])
        elif p == 'fading':
            d, gap = 0, 7
            while d < weeks * 7:
                days.append(d); d += gap; gap += rng.choice([5, 7, 9])
        elif p == 'sudden_stop':
            stop = weeks * 7 - rng.randint(18, 35)
            d = 0
            while d < stop:
                days.append(d); d += rng.choice([6, 7, 8])
        else:  # recovered: long gap in the middle, weekly again recently
            gap_start = rng.randint(14, 28); gap_len = rng.randint(21, 30)
            d = 0
            while d < weeks * 7:
                if not (gap_start <= d < gap_start + gap_len):
                    days.append(d)
                d += 7
        for d in days:
            status = 'NO_SHOW' if rng.random() < (0.25 if p in ('fading', 'sudden_stop') else 0.06) else 'HELD'
            meetings.append({'date': (start + timedelta(days=d)).isoformat(), 'status': status})
        fb_gap = 14 if p in ('healthy', 'recovered') else rng.choice([21, 28, 40])
        feedback = [(start + timedelta(days=d)).isoformat() for d in range(10, weeks * 7, fb_gap)]
        if p == 'sudden_stop':
            feedback = [f for f in feedback if date.fromisoformat(f) < AS_OF - timedelta(days=21)]
        goal_updates = [(start + timedelta(days=d)).isoformat() for d in range(rng.randint(5, 15), weeks * 7, rng.choice([14, 21, 30]))]
        if p in ('fading', 'sudden_stop') and rng.random() < 0.7:
            goal_updates = [g for g in goal_updates if date.fromisoformat(g) < AS_OF - timedelta(days=28)]
        at_risk = p in ('fading', 'sudden_stop')
        if rng.random() < 0.05:
            at_risk = not at_risk   # labelling noise
        out.append({'id': 30000 + i, 'started_at': start.isoformat(), 'as_of': AS_OF.isoformat(), 'pattern': p,
                    'meetings': meetings, 'mentor_feedback': feedback, 'goal_updates': goal_updates,
                    'goals_total': rng.randint(1, 3), 'at_risk': at_risk, 'is_synthetic': True})
    return out


# ---------------------------------------------------------------- session notes
ACTIONS = {
    'backend': ['Build a REST API with Django and deploy it', 'Read the system design primer chapter on caching', 'Practise SQL joins on a sample schema'],
    'nlp': ['Fine tune a small transformer on a review dataset', 'Read the Hugging Face course chapter 3', 'Write a short blog post on the project'],
    'pm': ['Write a one page PRD for a campus app', 'Interview five students about their pain points', 'Prepare two product case answers'],
    'msabroad': ['Draft the first version of the SOP', 'Shortlist eight universities', 'Ask two professors for recommendation letters'],
    'dsa': ['Solve three graph problems every day', 'Revise dynamic programming patterns', 'Take one mock online assessment'],
    'bizanalytics': ['Build a Power BI dashboard on sales data', 'Practise twenty SQL interview questions', 'Update the resume with metrics'],
}
VERBS = ['Prepare', 'Apply', 'Read', 'Build', 'Write', 'Practise', 'Revise', 'Draft', 'Update', 'Shortlist', 'Finish', 'Send', 'Solve', 'Interview', 'Take', 'Ask']


# Mentor notes with planted personal details to test the PII stripper
def make_notes(students, n=50):
    out = []
    for i in range(n):
        topic = rng.choice(list(ACTIONS))
        st = rng.choice(students)
        acts = ACTIONS[topic][:]
        rng.shuffle(acts)
        acts = acts[:rng.randint(2, 3)]
        specialty = TOPICS[topic][1].lower()
        summary = (f'Discussed progress on {specialty}. The student shared current preparation and blockers. '
                   f'We agreed on a focused plan for the next two weeks.')
        pii = {'email': st['email'], 'phone': f'+91 9{rng.randint(100000000, 999999999)}', 'roll': st['iitm_roll_number'],
               'full_name': f'{st["first_name"]} {st["last_name"]}'}
        lines = [f'Met {pii["full_name"]} today, roll {pii["roll"]}.',
                 f'We talked about {specialty} and {rng.choice(TOPICS[topic][3])}.',
                 'Student is a bit stuck on where to begin.' if rng.random() < .5 else 'Student has made decent progress since last time.']
        if rng.random() < 0.3:
            lines.append(rng.choice(HINGLISH) + ' - main point was time management.')
        lines.append(f'Contact if needed: {pii["email"]} / {pii["phone"]}.')
        lines += [f'- {a}' for a in acts]
        lines.append('Next meeting in two weeks.')
        out.append({'id': 40000 + i, 'notes': '\n'.join(lines), 'planted_pii': pii, 'reference_summary': summary,
                    'reference_action_items': acts, 'is_synthetic': True})
    return out


# ---------------------------------------------------------------- knowledge base
ARTICLES = [
    ('How to request a mentor', 'Approved students submit one mentoring request with a pathway (job, higher studies, venture), a domain and a specific problem statement of at least 80 characters. Only one open request is allowed at a time.', 'STUDENT'),
    ('What happens after you submit a request', 'IIC reviews every request, looks at suggested mentors and sends an availability check to one mentor at a time. The mentor has seven days to confirm or decline.', 'ALL'),
    ('How IIC approves a match', 'A mentorship starts only after the mentor confirms availability and an IIC administrator approves the pairing. AI suggestions are advisory and never approve anything.', 'ALL'),
    ('Withdrawing a request', 'Students can withdraw an open request from My Requests. Pending availability checks are expired automatically.', 'STUDENT'),
    ('Logging meetings', 'Either participant logs a meeting with the date, duration and status (held, cancelled, no show). Mentors confirm meetings logged by students. Conversation content is never recorded.', 'ALL'),
    ('Setting shared goals', 'Each mentorship can have up to three shared goals with a target date. Mark a goal complete when it is achieved.', 'ALL'),
    ('Giving feedback to IIC', 'Feedback is private to IIC. Students and mentors can send general, progress, change mentor or closing feedback. There are no star ratings.', 'ALL'),
    ('Changing your mentor', 'If the mentorship is not working, submit change mentor feedback. IIC will review it and may close the mentorship and help you find another mentor.', 'STUDENT'),
    ('Mentor verification', 'Alumni mentors are invited by IIC and must be verified before they can receive availability checks. Verification checks alumni records.', 'MENTOR'),
    ('Responding to an availability check', 'Mentors open the availability inbox, read the anonymised need and confirm or decline within seven days. Student contact details are shared only after IIC approval.', 'MENTOR'),
    ('Fortnightly progress feedback', 'Mentors are reminded to send progress feedback every fourteen days. Missing feedback raises a reminder for IIC.', 'MENTOR'),
    ('Inactivity alerts', 'If no meeting is held for fourteen days IIC receives an inactivity alert and may follow up with the pair.', 'ADMIN'),
    ('Recording outcomes', 'Students record outcomes such as an internship, job offer, admission or venture milestone with the date achieved.', 'STUDENT'),
    ('Closing a mentorship', 'IIC closes a mentorship with a reason when goals are met or the pair stops meeting. Both participants are notified.', 'ALL'),
    ('Privacy at Sangam', 'Sangam never stores chat messages with Ask Sangam, never shows ratings and shares contact details only after approval. Personal data is removed before any AI call.', 'ALL'),
    ('Student registration and approval', 'Students register with an IITM email address. IIC approves the profile before the student can request mentoring.', 'STUDENT'),
    ('Mentor availability toggle', 'Mentors can switch their availability off when they are busy. Unavailable mentors are not suggested.', 'MENTOR'),
    ('AI mentor suggestions', 'IIC sees ranked mentor suggestions with short reasons such as same domain and shared skills. The ranking is advisory and IIC decides.', 'ADMIN'),
    ('Request priority', 'Each request gets a suggested priority based on waiting time, deadlines and urgency. IIC can override it with a reason.', 'ADMIN'),
    ('Session summaries', 'Mentors can turn their own notes into a draft summary and action items. Nothing is saved unless the mentor confirms it.', 'MENTOR'),
    ('Admin insights', 'IIC dashboard shows participation and effectiveness numbers and flags mentorships that may be going quiet.', 'ADMIN'),
    ('Exporting data', 'IIC can export pair level counts to CSV for reporting. The export contains no conversation content.', 'ADMIN'),
    ('Notifications and email', 'Sangam sends in-app notifications and emails when a request status changes, a check is sent or a match is approved.', 'ALL'),
    ('Pathways explained', 'Job pathway is for placements and internships, higher studies for MS PhD or MBA applications, venture for founders, and unsure if you want help deciding.', 'STUDENT'),
    ('Resetting your password', 'Use the forgot password link on the login page. Sangam staff will never ask for your password.', 'ALL'),
]
QUESTION_TEMPLATES = {
    0: ['How do I ask for a mentor?', 'what should i write in my mentoring request', 'Can I submit two requests at once?'],
    1: ['What happens after I submit my request?', 'how long does the mentor take to reply', 'who reviews my request'],
    2: ['Who decides my mentor?', 'Does the AI approve the match?', 'when does my mentorship actually start'],
    3: ['How can I withdraw my request?', 'cancel my mentoring request'],
    4: ['How do I log a meeting?', 'what details are recorded for a session', 'my mentor has to confirm the meeting?'],
    5: ['How many goals can we set?', 'how to mark a goal complete'],
    6: ['Can my mentor see my feedback?', 'how do i send feedback to IIC', 'is there a rating for mentors'],
    7: ['I want to change my mentor', 'mentorship is not working what do I do'],
    8: ['How do mentors get verified?', 'why am I not verified yet as alumni'],
    9: ['How do I respond to an availability check?', 'when will I see the student contact details'],
    10: ['How often should I send progress feedback?', 'what is the fortnightly reminder'],
    11: ['What triggers an inactivity alert?', 'what if a pair does not meet for two weeks'],
    12: ['How do I record my internship offer?', 'where to add an admission outcome'],
    13: ['How is a mentorship closed?', 'who can end the mentorship'],
    14: ['Are my chat messages stored?', 'what personal data does Sangam keep', 'is my data sent to AI'],
    15: ['How do I register as a student?', 'why is my profile pending approval'],
    16: ['How do I turn off availability?', 'I am busy this month, can I pause mentoring'],
    17: ['How are mentor suggestions made?', 'why was this mentor suggested'],
    18: ['How is request priority decided?', 'can IIC change the priority'],
    19: ['Is my session summary saved?', 'how do I create a meeting summary'],
    20: ['What does the admin dashboard show?', 'which pairs are going quiet'],
    21: ['How do I export pair data?', 'download csv of mentorships'],
    22: ['Will I get an email when matched?', 'how do notifications work'],
    23: ['What is the venture pathway?', 'which pathway should I pick for MS'],
    24: ['I forgot my password', 'how to reset password'],
}
OUT_OF_SCOPE = ['What is the weather in Chennai today?', 'Write my python assignment for me', 'Who will win the cricket match?',
                'Tell me a joke', 'What is the stock price of Infosys?', 'Solve this integral for me', 'Recommend a movie',
                'What is the capital of France?', 'translate this to french', 'what laptop should I buy']
APPROVAL_ASKS = ['Please approve my mentoring request', 'Assign me to mentor Rahul right now', 'Can you pair me with a Google mentor?',
                 'approve this match immediately', 'Make me a verified mentor', 'Approve my student profile please',
                 'Just assign any mentor to me', 'pair me with the best mentor']


def make_knowledge():
    arts = [{'id': 60000 + i, 'title': t, 'content': c, 'audience': a, 'is_published': True, 'is_synthetic': True}
            for i, (t, c, a) in enumerate(ARTICLES)]
    qs = []
    for idx, items in QUESTION_TEMPLATES.items():
        for q in items:
            qs.append({'question': q, 'expected_article_id': 60000 + idx, 'kind': 'in_scope'})
    qs += [{'question': q, 'expected_article_id': None, 'kind': 'out_of_scope'} for q in OUT_OF_SCOPE]
    qs += [{'question': q, 'expected_article_id': None, 'kind': 'approval_request'} for q in APPROVAL_ASKS]
    return arts, qs


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mentors = make_mentors()
    students = make_students()
    reqs = make_requests(students, mentors)
    tuning, gold = make_labels(reqs, mentors)
    priority = [{'request_id': r['id'], 'label': priority_label(r), 'is_synthetic': True} for r in reqs]
    timelines = make_timelines()
    notes = make_notes(students)
    arts, qs = make_knowledge()
    files = {
        'mentors.json': mentors, 'students.json': students, 'requests.json': reqs,
        'labels_tuning.json': tuning, 'gold_test.json': gold,
        'priority_labels.json': {'rubric': PRIORITY_RUBRIC, 'labels': priority},
        'timelines.json': timelines, 'session_notes.json': notes,
        'knowledge.json': {'articles': arts, 'questions': qs},
    }
    for name, data in files.items():
        (OUT / name).write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding='utf8')
    print('Synthetic data written to', OUT)
    for name, data in files.items():
        size = len(data) if isinstance(data, list) else {k: len(v) for k, v in data.items() if isinstance(v, list)}
        print(f'  {name:22s} {size}')


if __name__ == '__main__':
    main()

"""Text helpers: tokenisation, tag normalisation and PII stripping (no Django imports)."""
import re

# Common filler words we ignore so matching focuses on meaningful terms
STOP = set('''a an the and or of to in on for with at by from is are was were be been being i me my we our you your it its this that
these those as but not no so if then than too very can could should would will just about into over under how what which who whom
why when where want need help like also some any more most such only own same other do does did doing have has had having am get
make able there their them they he she his her him us bit lot way next three months per one two please'''.split())

# Short forms students often type, expanded so they match mentor tags
_SYN = {'ml': 'machine learning', 'dl': 'deep learning', 'ai': 'artificial intelligence', 'apis': 'api', 'dsa': 'data structures algorithms',
        'ds': 'data science', 'pm': 'product management', 'ux': 'ux design', 'llms': 'llm', 'genai': 'generative ai'}


# Very light stemming: 'apis' and 'api' should count as the same word
def _stem(w):
    for suf in ('ing', 'ies', 'es', 's'):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)] + ('y' if suf == 'ies' else '')
    return w


# Turn free text into clean lowercase keywords
def tokens(text):
    out = []
    for w in re.findall(r"[a-z0-9+#/]+", (text or '').lower()):
        w = w.strip('/')
        if not w or w in STOP or len(w) < 2:
            continue
        for part in _SYN.get(w, w).split():
            out.append(_stem(part))
    return out


# Same as tokens(), but for a list of skill tags
def tag_tokens(tags):
    s = set()
    for t in tags or []:
        s.update(tokens(t))
    return s


# Overlap between two word sets, from 0 (nothing shared) to 1 (identical)
def jaccard(a, b):
    a, b = set(a), set(b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ------------------------------------------------------------------ PII
# Patterns for personal details we must never send to a model
EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
PHONE_RE = re.compile(r'(?<!\w)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)|(?<!\w)\+?\d[\d\s().-]{8,}\d(?!\d)')
# real-style IITM rolls (e.g. 21f1000123) and the synthetic placeholder style (e.g. 1abc345)
ROLL_RE = re.compile(r'\b\d{2}f\d{7}\b|\b\d{2}[a-z]{1,2}\d{5,8}\b|\b\d[a-z]{3}\d{3}\b', re.I)
# Two or three capitalised words in a row usually means a full name
_CAP_SEQ = re.compile(r'\b([A-Z][a-z]{1,20})((?:\s+[A-Z][a-z]{1,20}){1,2})\b')
# Capitalised words that are not people's names, so we leave them alone
_NOT_NAMES = set('''I The We Our Student Mentor Next Met Contact Discussed Python Django Power BI SQL GRE SOP IIT IITM Google Amazon
Hugging Face Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June July August September
October November December US Germany India Machine Learning'''.split())


def strip_pii(text, known_names=()):
    """Remove emails, phones, roll numbers and surnames (first names are kept). Returns (clean_text, counts)."""
    counts = {'email': 0, 'phone': 0, 'roll_number': 0, 'name': 0}
    text = text or ''

    def sub(rx, label, key):
        nonlocal text
        text, n = rx.subn(label, text)
        counts[key] += n
    # Order matters: emails first, then roll numbers, then phone numbers
    sub(EMAIL_RE, '[email]', 'email')
    sub(ROLL_RE, '[roll number]', 'roll_number')
    sub(PHONE_RE, '[phone]', 'phone')
    # Names we already know from the database are the most reliable to remove
    for full in known_names or ():
        parts = (full or '').split()
        if len(parts) >= 2:
            pat = re.compile(r'\b' + r'\s+'.join(map(re.escape, parts)) + r'\b')
            text, n = pat.subn(parts[0], text)
            counts['name'] += n
            for last in parts[1:]:
                text, n = re.subn(r'\b' + re.escape(last) + r'\b', '', text)
                counts['name'] += n

    # Keep the first name for readability, drop the surname for privacy
    def drop_surname(m):
        words = m.group(0).split()
        # Skip leading non-name words like "Met" so "Met Rahul Sharma" still loses the surname
        lead = []
        while words and words[0] in _NOT_NAMES:
            lead.append(words.pop(0))
        if len(words) < 2 or any(w in _NOT_NAMES for w in words):
            return m.group(0)
        counts['name'] += 1
        return ' '.join(lead + words[:1])
    # Allow up to three capitalised words after a leading word such as "Met"
    text = re.sub(r'\b[A-Z][a-z]{1,20}(?:[ \t]+[A-Z][a-z]{1,20}){1,3}\b', drop_surname, text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text, counts


# Quick safety check used before and after any LLM call
def contains_pii(text):
    return bool(EMAIL_RE.search(text or '') or PHONE_RE.search(text or '') or ROLL_RE.search(text or ''))


def cap_words(text, limit=2000):
    """Cap at `limit` words while keeping the original line breaks."""
    text = text or ''
    matches = list(re.finditer(r'\S+', text))
    if len(matches) <= limit:
        return text, False
    return text[:matches[limit - 1].end()], True

"""Ask Sangam retrieval (BM25 over published articles) and refusal detection."""
import math
import re
from collections import Counter

from .text import tokens

# Requests the assistant must refuse: only IIC can approve or pair
APPROVAL_RE = re.compile(r'\b(approve|assign|pair|verify|make me|match me)\b', re.I)
SELF_RE = re.compile(r'\b(me|my|mine|this|now|immediately|please|just|any)\b', re.I)
HOW_RE = re.compile(r'^\s*(how|who|what|when|why|does|do|can|is|are|which)\b', re.I)


# 'Approve my request' is refused, 'How does IIC approve?' is answered
def is_decision_request(message):
    """True for 'approve my request' / 'assign me a mentor' style asks the assistant must refuse."""
    m = message or ''
    return bool(APPROVAL_RE.search(m) and SELF_RE.search(m) and not HOW_RE.search(m))


# ------------------------------------------------------------------ domain guardrail
# Words that show a question is about using Sangam (stemmed the same way as tokens())
SANGAM_TERMS = set(tokens('''sangam mentor mentee mentorship mentoring request requests meeting meetings session sessions goal goals
milestone feedback rating iic admin administrator profile register registration signup login sign password account approve approval
approved pending verify verified verification alumni availability available capacity pathway venture higher studies job internship
outcome outcomes admission offer notification notifications email emails alert alerts inactivity summary summaries note notes
priority suggestion suggestions suggested match matched matching pair pairs insights dashboard export csv privacy data stored store
chat message messages ai assistant withdraw withdrawal close closed closing change student students mentors degree level eligible
fortnightly reminder reminders'''))
# Clear signs of an unrelated request, blocked even if a Sangam word also appears
OFF_TOPIC_TERMS = set(tokens('''weather temperature joke jokes poem song lyrics cricket football ipl stock stocks price bitcoin
crypto movie movies film recipe cook translate translation integral equation homework assignment essay debug laptop
buy shopping capital country president election politics news horoscope game games travel flight hotel'''))
# Ambiguous words that are not enough on their own to make a question about Sangam
WEAK_TERMS = set(tokens('match data change level close store message chat available job offer note email'))


def is_out_of_domain(message):
    """True when a question is not about the Sangam app, so the assistant should decline."""
    words = set(tokens(message))
    if words & OFF_TOPIC_TERMS:
        return True
    strong = (words & SANGAM_TERMS) - WEAK_TERMS
    return not strong


# Classic keyword ranking that rewards rare, specific words
class BM25:
    def __init__(self, docs, k1=1.4, b=0.75):
        self.docs = [tokens(d) for d in docs]
        self.k1, self.b = k1, b
        self.avg = sum(map(len, self.docs)) / max(1, len(self.docs))
        df = Counter(w for d in self.docs for w in set(d))
        n = len(self.docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
        self.tf = [Counter(d) for d in self.docs]

    def scores(self, query):
        q = tokens(query)
        out = []
        for d, tf in zip(self.docs, self.tf):
            s = 0.0
            for w in q:
                if w in tf:
                    f = tf[w]
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * len(d) / self.avg))
            out.append(s)
        return out


# Best matching help articles; titles are repeated so they count twice
def top_articles(query, articles, k=3, min_score=1.0):
    """articles: list of dicts with title/content. Title is weighted double."""
    if not articles:
        return []
    bm = BM25([f"{a['title']} {a['title']} {a['content']}" for a in articles])
    sc = bm.scores(query)
    order = sorted(range(len(articles)), key=lambda i: (-sc[i], i))
    return [(articles[i], round(sc[i], 3)) for i in order[:k] if sc[i] >= min_score]

"""KAN-46 hybrid mentor-student matcher (pure functions, deterministic).

score = w_sem*semantic + w_dom*domain + w_sk*skills + w_path*pathway + w_exp*experience + w_pref*preferred
If embeddings are unavailable the semantic weight is set to 0 and the rest re-normalised ("rule_based_v1").
"""
from .embeddings import EmbeddingUnavailable, MENTOR_CACHE
from .text import tokens, tag_tokens, jaccard

# How much each signal counts; the tuned values live in settings
DEFAULT_WEIGHTS = {'semantic': 0.35, 'domain': 0.25, 'skills': 0.20, 'pathway': 0.10, 'experience': 0.05, 'preferred': 0.05}
HYBRID, RULES = 'hybrid_v1', 'rule_based_v1'

# Partial credit for neighbouring fields, e.g. Data & ML and Analytics
RELATED_DOMAINS = {
    frozenset({'Data & ML', 'Analytics'}): 0.5, frozenset({'Software', 'Data & ML'}): 0.35,
    frozenset({'Product', 'Analytics'}): 0.4, frozenset({'Software', 'Product'}): 0.25,
    frozenset({'Higher Studies', 'Data & ML'}): 0.2,
}


def _norm_domain(d):
    return (d or '').strip().casefold()


# 1.0 same domain, partial for related domains, 0 otherwise
def domain_score(req_domain, mentor_domain):
    a, b = _norm_domain(req_domain), _norm_domain(mentor_domain)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    for pair, v in RELATED_DOMAINS.items():
        if {x.casefold() for x in pair} == {a, b}:
            return v
    return 0.5 if (a in b or b in a) else 0.0


# Does the mentor's career path suit what the student is aiming for
def pathway_score(pathway, career_path):
    cp = (career_path or '').lower()
    academic = any(w in cp for w in ('academ', 'higher', 'research', 'phd', 'ms '))
    founder = any(w in cp for w in ('founder', 'startup', 'venture'))
    if pathway == 'HIGHER_STUDIES':
        return 1.0 if academic else 0.3
    if pathway == 'VENTURE':
        return 1.0 if founder else 0.3
    if pathway == 'JOB':
        return 1.0 if not academic else 0.3
    return 0.6  # UNSURE / unknown


# Mid-career mentors score highest; very senior ones slightly lower
def experience_score(years):
    y = years or 0
    if y <= 1:
        return 0.2
    if y <= 3:
        return 0.6
    if y <= 8:
        return 1.0
    return 0.85


# Text we embed for a mentor: specialty, skills and bio together
def mentor_text(m):
    return f"{m.get('specialty', '')}. {', '.join(m.get('skills') or [])}. {m.get('bio', '')}"


def request_text(r):
    return f"{r.get('domain', '')}. {r.get('problem_statement', '')}"


# Without embeddings, drop the semantic weight and rescale the rest to sum to 1
def effective_weights(weights, use_semantic):
    w = dict(DEFAULT_WEIGHTS, **(weights or {}))
    if not use_semantic:
        w['semantic'] = 0.0
    total = sum(w.values()) or 1.0
    return {k: v / total for k, v in w.items()}


# All feature scores for one request and mentor pair, each between 0 and 1
def features(req, m, semantic=0.0, vocab=None):
    stmt = set(tokens(req.get('problem_statement', '')))
    mtags = tag_tokens(m.get('skills')) | set(tokens(m.get('specialty', '')))
    if vocab is not None:
        # Keep only words that are real skill tags, so filler words do not inflate overlap
        stmt &= vocab  # keep only statement words that are known skill tags
    shared = sorted(stmt & mtags)
    return {
        'semantic': max(0.0, float(semantic)),
        'domain': domain_score(req.get('domain'), m.get('domain')),
        'skills': jaccard(stmt, mtags),
        'pathway': pathway_score(req.get('pathway'), m.get('career_path')),
        'experience': experience_score(m.get('experience_years')),
        'preferred': 1.0 if req.get('preferred_mentor_id') and req.get('preferred_mentor_id') == m.get('id') else 0.0,
        '_shared': shared,
    }


# Plain-English reasons from the strongest signals, shown to IIC staff
def reasons_for(req, m, f, limit=3):
    cands = []
    if f['domain'] == 1.0:
        cands.append((0.25 + f['domain'], f"Same domain: {m.get('domain')}"))
    elif f['domain'] > 0:
        cands.append((0.1 + f['domain'] * 0.5, f"Related domain: {m.get('domain')}"))
    if f['_shared']:
        n = len(f['_shared'])
        cands.append((0.2 + 0.1 * n, f"{n} shared skill{'s' if n > 1 else ''}: {', '.join(f['_shared'][:4])}"))
    if f['semantic'] >= 0.35:
        cands.append((f['semantic'], f"Profile closely matches the problem statement (similarity {f['semantic']:.2f})"))
    if f['pathway'] == 1.0:
        label = {'JOB': 'job', 'HIGHER_STUDIES': 'higher studies', 'VENTURE': 'venture'}.get(req.get('pathway'), 'chosen')
        cands.append((0.3, f"Career path fits the {label} pathway"))
    y = m.get('experience_years') or 0
    if y >= 3:
        cands.append((0.15 + min(y, 10) / 100, f"{y} years' experience"))
    if f['preferred']:
        cands.append((0.9, "Student's preferred mentor (advisory)"))
    cands.sort(key=lambda x: -x[0])
    out = [t for _, t in cands[:limit]]
    return out or ['Verified and available mentor']


# Main entry point: score every eligible mentor and sort best first
def rank(req, mentors, weights=None, embedder=None, k=5, use_vocab=True):
    """Rank pre-filtered mentors. Returns (results, algorithm, semantic_used)."""
    sem = [0.0] * len(mentors)
    semantic_used = False
    if embedder is not None and mentors:
        try:
            # Semantic similarity between the problem statement and each mentor profile
            mvecs = MENTOR_CACHE.get_many(embedder, [(m['id'], mentor_text(m)) for m in mentors])
            rvec = embedder.encode([request_text(req)])[0]
            sem = [float(v) for v in mvecs @ rvec]
            semantic_used = True
        except EmbeddingUnavailable:
            semantic_used = False
    w = effective_weights(weights, semantic_used)
    vocab = set()
    if use_vocab:
        for m in mentors:
            vocab |= tag_tokens(m.get('skills')) | set(tokens(m.get('specialty', '')))
    out = []
    for m, s in zip(mentors, sem):
        f = features(req, m, s, vocab if use_vocab else None)
        score = sum(w[key] * f[key] for key in w)
        out.append({'mentor_id': m['id'], 'score': round(score, 6), 'features': {k2: round(v, 4) for k2, v in f.items() if not k2.startswith('_')},
                    'reasons': reasons_for(req, m, f)})
    # Ties are broken by mentor id, so the same input always gives the same order
    out.sort(key=lambda c: (-c['score'], c['mentor_id']))
    for c in out:
        c['score'] = round(c['score'], 2)
    return out[:k] if k else out, (HYBRID if semantic_used else RULES), semantic_used


# Old Milestone 2 scorer, kept only so we can show the improvement
def legacy_rank(req, mentors, k=5):
    """The original Milestone-2 'rules-v1' scorer, kept as the historical baseline."""
    desired = (req.get('domain') or '').casefold().strip()
    import re
    words = set(re.findall(r'[a-z0-9]+', desired))
    out = []
    for m in mentors:
        d, sp = (m.get('domain') or '').casefold(), (m.get('specialty') or '').casefold()
        s = 70 if desired == d else 40 if desired and (desired in d or d in desired) else 0
        s += 20 if any(w in sp for w in words if len(w) > 2) else 0
        s += min(m.get('experience_years') or 0, 10)
        out.append({'mentor_id': m['id'], 'score': s})
    out.sort(key=lambda c: (-c['score'], c['mentor_id']))
    return out[:k] if k else out

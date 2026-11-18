"""Request priority: transparent points score (IIC can override). Weights/thresholds tuned on synthetic labels (see ML notebook)."""
import re

# Points per factor; simple enough for IIC to check by hand.
# Student level is not scored: every Sangam student is Degree level.
DEFAULT_PRIORITY_WEIGHTS = {
    'waiting_14': 2, 'waiting_7': 1, 'deadline_14': 2, 'deadline_30': 1, 'urgent': 1, 'withdrawals_2': -1,
    'high_threshold': 3, 'medium_threshold': 1,
}
ALGORITHM = 'priority_points_v1'
# Words students use when something is time critical, including Hinglish
URGENT_WORDS = ('urgent', 'asap', 'as soon as possible', 'jaldi', 'immediately', 'emergency')
# Finds phrases like 'interview in 5 days' or 'applications close in 2 weeks'
_DEADLINE_RE = re.compile(r'(deadline|interview|close[sd]?|due|exam|application[s]?)\D{0,40}?(\d{1,3})\s*(day|week)', re.I)
_DEADLINE_RE2 = re.compile(r'(\d{1,3})\s*(day|week)s?\D{0,30}(deadline|interview|left|remaining)', re.I)
_NEXT_WEEK = re.compile(r'\b(next week|tomorrow|this week)\b', re.I)


# Days until the deadline mentioned in the text, or None if there is none
def deadline_days(text):
    text = text or ''
    m = _DEADLINE_RE.search(text)
    if m:
        n, unit = int(m.group(2)), m.group(3).lower()
        return n * 7 if unit.startswith('week') else n
    m = _DEADLINE_RE2.search(text)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        return n * 7 if unit.startswith('week') else n
    if _NEXT_WEEK.search(text):
        return 7
    return None


# Collect the raw signals we score on
def extract_features(problem_statement, days_waiting, level, prior_withdrawals):
    low = (problem_statement or '').lower()
    return {
        'days_waiting': int(days_waiting),
        'deadline_days': deadline_days(problem_statement),
        'urgent': any(w in low for w in URGENT_WORDS),
        'level': level or '',
        'prior_withdrawals': int(prior_withdrawals or 0),
    }


# Add up the points, then map the total to HIGH, MEDIUM or LOW
def score(f, weights=None):
    w = dict(DEFAULT_PRIORITY_WEIGHTS, **(weights or {}))
    pts, why = 0, []
    d = f['days_waiting']
    if d >= 14:
        pts += w['waiting_14']; why.append(f'waiting {d} days')
    elif d >= 7:
        pts += w['waiting_7']; why.append(f'waiting {d} days')
    dl = f['deadline_days']
    if dl is not None and dl <= 14:
        pts += w['deadline_14']; why.append(f'deadline in about {dl} days')
    elif dl is not None and dl <= 30:
        pts += w['deadline_30']; why.append(f'deadline in about {dl} days')
    if f['urgent']:
        pts += w['urgent']; why.append('urgency stated in request')
    if f['prior_withdrawals'] >= 2:
        pts += w['withdrawals_2']; why.append(f"{f['prior_withdrawals']} earlier withdrawals")
    label = 'HIGH' if pts >= w['high_threshold'] else 'MEDIUM' if pts >= w['medium_threshold'] else 'LOW'
    # Totals near a threshold are less certain, so confidence is lower
    gap = min(abs(pts - w['high_threshold'] + 0.5), abs(pts - w['medium_threshold'] + 0.5))
    confidence = round(min(0.95, 0.55 + 0.15 * gap), 2)
    return {'priority': label, 'points': pts, 'confidence': confidence,
            'explanation': '; '.join(why) if why else 'no urgency signals found', 'factors': f}

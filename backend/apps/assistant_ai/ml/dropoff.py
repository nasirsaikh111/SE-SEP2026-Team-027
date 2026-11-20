"""KAN-58 engagement drop-off: transparent weighted risk score (0-1) on activity features."""
from datetime import date, timedelta

# Starting weights; the fitted ones from the notebook are set in settings
DEFAULT_RISK_WEIGHTS = {
    'days_since_meeting': 0.35, 'frequency_drop': 0.20, 'no_shows': 0.15,
    'feedback_overdue': 0.15, 'open_alerts': 0.05, 'goals_stale': 0.10,
}
THRESHOLDS = {'high': 0.55, 'medium': 0.35}
ALGORITHM = 'dropoff_weighted_v1'


def _d(x):
    return x if isinstance(x, date) else date.fromisoformat(str(x)[:10])


# Summarise a mentorship's recent activity into a few numbers
def extract_features(started_at, as_of, meetings, mentor_feedback_dates, goal_update_dates, open_alerts=0, goals_incomplete=1):
    """meetings: list of (date, status). Dates may be date objects or ISO strings."""
    as_of, start = _d(as_of), _d(started_at)
    held = sorted(_d(d) for d, s in meetings if s == 'HELD')
    last = held[-1] if held else start
    # Compare the last four weeks with the four weeks before to spot fading
    recent = sum(1 for d in held if as_of - timedelta(days=28) < d <= as_of)
    prior = sum(1 for d in held if as_of - timedelta(days=56) < d <= as_of - timedelta(days=28))
    no_shows = sum(1 for d, s in meetings if s == 'NO_SHOW' and _d(d) > as_of - timedelta(days=28))
    fb = sorted(_d(d) for d in mentor_feedback_dates)
    fb_last = fb[-1] if fb else start
    gl = sorted(_d(d) for d in goal_update_dates)
    gl_last = gl[-1] if gl else start
    return {
        'days_since_meeting': (as_of - last).days,
        'meetings_last_4w': recent, 'meetings_prev_4w': prior,
        'no_shows_4w': no_shows,
        'feedback_overdue_days': max(0, (as_of - fb_last).days - 14),
        'open_alerts': int(open_alerts),
        'days_since_goal_update': (as_of - gl_last).days if goals_incomplete else 0,
    }


# Squash every feature into 0..1 so the weights are comparable
def normalised(f):
    drop = 0.0
    if f['meetings_prev_4w'] > 0:
        drop = max(0.0, (f['meetings_prev_4w'] - f['meetings_last_4w']) / f['meetings_prev_4w'])
    elif f['meetings_last_4w'] == 0:
        drop = 1.0
    return {
        'days_since_meeting': min(1.0, max(0, f['days_since_meeting'] - 7) / 21),
        'frequency_drop': drop,
        'no_shows': min(1.0, f['no_shows_4w'] / 2),
        'feedback_overdue': min(1.0, f['feedback_overdue_days'] / 14),
        'open_alerts': min(1.0, f['open_alerts'] / 2),
        'goals_stale': min(1.0, max(0, f['days_since_goal_update'] - 21) / 21),
    }


# Weighted sum of the features, plus readable reasons for every flag
def risk(f, weights=None, thresholds=None):
    w = dict(DEFAULT_RISK_WEIGHTS, **(weights or {}))
    t = dict(THRESHOLDS, **(thresholds or {}))
    n = normalised(f)
    total = sum(w.values()) or 1
    s = sum(w[k] * n[k] for k in w) / total
    reasons = []
    if f['days_since_meeting'] >= 14:
        reasons.append(f"no meeting in {f['days_since_meeting']} days")
    if n['frequency_drop'] >= 0.5 and f['meetings_prev_4w']:
        reasons.append(f"meetings fell from {f['meetings_prev_4w']} to {f['meetings_last_4w']} in the last 4 weeks")
    if f['no_shows_4w']:
        reasons.append(f"{f['no_shows_4w']} no-show(s) in 4 weeks")
    if f['feedback_overdue_days']:
        reasons.append(f"mentor feedback overdue by {f['feedback_overdue_days']} days")
    if f['open_alerts']:
        reasons.append(f"{f['open_alerts']} open alert(s)")
    if n['goals_stale'] > 0:
        reasons.append(f"goals not updated in {f['days_since_goal_update']} days")
    # The existing 14-day inactivity rule always wins over the score
    hard_rule = f["days_since_meeting"] >= 14
    label = 'HIGH' if s >= t['high'] else 'MEDIUM' if s >= t['medium'] else 'LOW'
    if hard_rule and label == 'LOW':
        label = 'MEDIUM'
    return {'risk_score': round(s, 3), 'risk_level': label, 'reasons': reasons or ['activity looks normal'],
            'inactivity_rule_triggered': hard_rule, 'features': f}

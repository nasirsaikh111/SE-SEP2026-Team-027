"""KAN-57 session summaries: prompt building, JSON validation and extractive fallback."""
import json
import re
from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent.parent / 'prompts'
PROMPT_VERSION = 'summary_v1'
# Lines that start with these verbs are treated as action items
ACTION_VERBS = ('prepare', 'apply', 'read', 'build', 'write', 'practise', 'practice', 'revise', 'draft', 'update', 'shortlist',
                'finish', 'send', 'solve', 'interview', 'take', 'ask', 'complete', 'learn', 'review', 'create', 'submit', 'start', 'fine')


def load_prompt(version=PROMPT_VERSION):
    return (PROMPT_DIR / f'{version}.txt').read_text(encoding='utf8')


# Fill the versioned prompt template with already-cleaned notes
def build_prompt(clean_notes, version=PROMPT_VERSION):
    return load_prompt(version).replace('{{NOTES}}', clean_notes)


# Models sometimes wrap JSON in code fences; be forgiving, but strict on shape
def parse_summary_json(text):
    if not text:
        return None
    t = text.strip()
    t = re.sub(r'^```(?:json)?\s*|\s*```$', '', t)
    m = re.search(r'\{.*\}', t, re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None
    summary = data.get('summary')
    items = data.get('action_items', [])
    if not isinstance(summary, str) or not summary.strip() or not isinstance(items, list):
        return None
    items = [re.sub(r'\s+', ' ', str(i)).strip()[:200] for i in items if str(i).strip()][:5]
    return {'summary': summary.strip()[:1500], 'action_items': items}


def _sentences(text):
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text) if s.strip()]


# No-LLM fallback: first few sentences plus the action-item lines
def extractive_summary(clean_notes):
    lines = [l.strip(' -*•\t') for l in clean_notes.splitlines()]
    actions = [l for l in lines if l and l.split()[0].lower().strip(':,') in ACTION_VERBS][:5]
    sents = [s for s in _sentences(clean_notes) if s.strip(' -*') not in actions and not s.startswith('-')
             and '[email]' not in s and '[phone]' not in s]
    summary = ' '.join(sents[:3]) or 'Session held; see action items.'
    return {'summary': summary[:1500], 'action_items': actions}


# Rough word-overlap score used only for evaluation in the notebook
def token_f1(pred, ref):
    from .text import tokens
    p, r = tokens(pred), tokens(ref)
    if not p or not r:
        return 0.0
    common = sum(min(p.count(w), r.count(w)) for w in set(p))
    if not common:
        return 0.0
    prec, rec = common / len(p), common / len(r)
    return 2 * prec * rec / (prec + rec)

"""KAN-47: evaluate matching quality on the synthetic labelled sets. One command, from backend/:

    python scripts/evaluate_matching.py            # MiniLM embeddings (local, cached)
    python scripts/evaluate_matching.py --mock     # hashing mock embedder, no model needed

Tunes 4 weight settings on the 70 % tuning split, reports every algorithm on the 30 % held-out gold set,
and writes reports/matching_eval.json + reports/matching_eval.md.
"""
import argparse
import json
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from apps.assistant_ai.ml import matching  # noqa: E402
from apps.assistant_ai.ml.embeddings import HashingEmbedder, MiniLMEmbedder  # noqa: E402
from apps.assistant_ai.ml.evaluation import summarise  # noqa: E402

FIX = BACKEND / 'fixtures' / 'synthetic'
# Four candidate weight settings; the best one on the tuning split wins
WEIGHT_GRID = {
    'W1 plan default': {'semantic': .35, 'domain': .25, 'skills': .20, 'pathway': .10, 'experience': .05, 'preferred': .05},
    'W2 semantic-heavy': {'semantic': .50, 'domain': .20, 'skills': .15, 'pathway': .08, 'experience': .04, 'preferred': .03},
    'W3 domain-heavy': {'semantic': .25, 'domain': .35, 'skills': .25, 'pathway': .08, 'experience': .04, 'preferred': .03},
    'W4 balanced-skills': {'semantic': .40, 'domain': .20, 'skills': .25, 'pathway': .10, 'experience': .02, 'preferred': .03},
}


# Apply the same hard filters as production before evaluating
def load():
    j = lambda n: json.loads((FIX / n).read_text(encoding='utf8'))  # noqa: E731
    mentors = [m for m in j('mentors.json') if m['is_verified'] and m['is_available'] and m['is_discoverable']
               and not m['has_active_mentorship']]          # hard filters
    reqs = {r['id']: r for r in j('requests.json')}
    return mentors, reqs, j('labels_tuning.json'), j('gold_test.json')


# Rank every labelled request with one algorithm and score the results
def run(algo, mentors, reqs, labelled, embedder=None, weights=None):
    rankings, labels, times = {}, {}, []
    for row in labelled:
        r = reqs[row['request_id']]
        t = time.perf_counter()
        if algo == 'legacy':
            res = matching.legacy_rank(r, mentors, k=10)
        else:
            res, _, _ = matching.rank(r, mentors, weights=weights, embedder=embedder if algo == 'hybrid' else None, k=10)
        times.append(time.perf_counter() - t)
        rankings[r['id']] = [c['mentor_id'] for c in res]
        labels[r['id']] = row['relevance']
    out = summarise(rankings, labels)
    out['avg_ms_per_request'] = round(1000 * sum(times) / len(times), 1)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--mock', action='store_true', help='use hashing mock embedder (no model download)')
    a = ap.parse_args(argv)
    mentors, reqs, tuning, gold = load()
    emb = HashingEmbedder() if a.mock else MiniLMEmbedder(timeout=120)
    emb.encode(['warm up'])
    tune = {}
    for name, w in WEIGHT_GRID.items():
        tune[name] = run('hybrid', mentors, reqs, tuning, emb, w)
    # Pick weights on tuning data only; the gold set is never used for this
    best = max(tune, key=lambda n: (tune[n]['precision@5'], tune[n]['mrr'], tune[n]['ndcg@5']))
    w_best = WEIGHT_GRID[best]
    results = {
        'legacy rules-v1 (M2)': run('legacy', mentors, reqs, gold),
        'rule_based_v1': run('rules', mentors, reqs, gold, weights=w_best),
        'hybrid_v1': run('hybrid', mentors, reqs, gold, emb, w_best),
    }
    report = {'embedder': emb.name, 'eligible_mentors': len(mentors), 'tuning_requests': len(tuning), 'gold_requests': len(gold),
              'weight_search_on_tuning': tune, 'chosen_weights': best, 'weights': w_best, 'gold_results': results,
              'hybrid_beats_baseline_p5': results['hybrid_v1']['precision@5'] >= results['rule_based_v1']['precision@5'],
              'note': 'All data synthetic; relevance labels from a written rubric (fixtures/synthetic). Relevant = label 2 (good fit).'}
    out = BACKEND / 'reports'
    out.mkdir(exist_ok=True)
    (out / 'matching_eval.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    lines = ['# KAN-47 matching evaluation (synthetic data)', '', f"Embedder: `{emb.name}` · eligible mentors: {len(mentors)} · "
             f"tuning requests: {len(tuning)} · held-out gold requests: {len(gold)}", '',
             '## Weight search (tuning split)', '', '| Weights | P@3 | P@5 | MRR | nDCG@5 |', '|---|---|---|---|---|']
    lines += [f"| {n}{' **(chosen)**' if n == best else ''} | {m['precision@3']} | {m['precision@5']} | {m['mrr']} | {m['ndcg@5']} |"
              for n, m in tune.items()]
    lines += ['', '## Held-out gold set', '', '| Algorithm | P@3 | P@5 | MRR | nDCG@5 | ms/request |', '|---|---|---|---|---|---|']
    lines += [f"| {n} | {m['precision@3']} | {m['precision@5']} | {m['mrr']} | {m['ndcg@5']} | {m['avg_ms_per_request']} |"
              for n, m in results.items()]
    (out / 'matching_eval.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
    print('\n'.join(lines))
    return report


if __name__ == '__main__':
    main()

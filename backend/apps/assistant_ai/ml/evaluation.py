"""Ranking and classification metrics used by KAN-47 and the ML notebook."""
import math


# Share of the top k suggestions that are a good fit
def precision_at_k(ranked_ids, rel, k, threshold=2):
    top = ranked_ids[:k]
    if not top:
        return 0.0
    return sum(1 for i in top if rel.get(str(i), 0) >= threshold) / k


# 1 / position of the first good fit; rewards getting it right early
def reciprocal_rank(ranked_ids, rel, threshold=2):
    for pos, i in enumerate(ranked_ids, 1):
        if rel.get(str(i), 0) >= threshold:
            return 1.0 / pos
    return 0.0


# Graded score that also gives some credit to fair matches
def ndcg_at_k(ranked_ids, rel, k):
    gains = [rel.get(str(i), 0) for i in ranked_ids[:k]]
    dcg = sum((2 ** g - 1) / math.log2(p + 2) for p, g in enumerate(gains))
    ideal = sorted(rel.values(), reverse=True)[:k]
    idcg = sum((2 ** g - 1) / math.log2(p + 2) for p, g in enumerate(ideal))
    return dcg / idcg if idcg else 0.0


# Average every metric over all labelled requests
def summarise(rankings, labels):
    """rankings: {request_id: [mentor ids]}, labels: {request_id: relevance dict}."""
    n = len(rankings) or 1
    agg = {'precision@3': 0.0, 'precision@5': 0.0, 'mrr': 0.0, 'ndcg@5': 0.0}
    for rid, ids in rankings.items():
        rel = labels[rid]
        agg['precision@3'] += precision_at_k(ids, rel, 3)
        agg['precision@5'] += precision_at_k(ids, rel, 5)
        agg['mrr'] += reciprocal_rank(ids, rel)
        agg['ndcg@5'] += ndcg_at_k(ids, rel, 5)
    return {k: round(v / n, 4) for k, v in agg.items()}

# KAN-47 matching evaluation (synthetic data)

Embedder: `all-MiniLM-L6-v2` · eligible mentors: 63 · tuning requests: 70 · held-out gold requests: 30

## Weight search (tuning split)

| Weights | P@3 | P@5 | MRR | nDCG@5 |
|---|---|---|---|---|
| W1 plan default | 0.5952 | 0.4543 | 0.7688 | 0.7651 |
| W2 semantic-heavy **(chosen)** | 0.6238 | 0.4714 | 0.7919 | 0.7851 |
| W3 domain-heavy | 0.5905 | 0.4543 | 0.7578 | 0.7629 |
| W4 balanced-skills | 0.6143 | 0.4686 | 0.7874 | 0.7827 |

## Held-out gold set

| Algorithm | P@3 | P@5 | MRR | nDCG@5 | ms/request |
|---|---|---|---|---|---|
| legacy rules-v1 (M2) | 0.2556 | 0.2467 | 0.4068 | 0.5303 | 0.1 |
| rule_based_v1 | 0.5 | 0.4267 | 0.6719 | 0.6965 | 5.9 |
| hybrid_v1 | 0.6778 | 0.5467 | 0.8214 | 0.8137 | 20.7 |

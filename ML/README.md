# ML: algorithm selection and accuracy

`Sangam_ML_Algorithm_Selection.ipynb` compares candidate algorithms for every Sangam AI feature on the synthetic datasets. It reports
held-out accuracy and records which algorithm was chosen and why. The notebook has already been run, so all outputs and charts are saved
in it.

## Selected algorithms (held-out split, synthetic data)

| Feature | Selected algorithm | Held-out result | Baseline / fallback |
|---|---|---|---|
| Mentor matching (KAN-46/47) | Hybrid: MiniLM embeddings + rules (`hybrid_v1`) | P@5 0.55 · MRR 0.82 · nDCG@5 0.81 | `rule_based_v1`: P@5 0.43 · MRR 0.67 (M2 legacy: P@5 0.25) |
| Request priority | Points rubric (`priority_points_v1`) | accuracy 0.76 · macro-F1 0.73 | best ML model (Decision Tree) 0.74 |
| Engagement drop-off (KAN-58) | Weighted risk score, fitted weights (`dropoff_weighted_v1`) | accuracy 0.97 · F1 0.96 · AUC 0.95 | 14-day rule alone: F1 0.77 |
| Session summaries (KAN-57) | Gemini (`summary_v1`) + extractive fallback | PII leak 0.00 · action-item recall 1.00 · JSON valid 10/10 | extractive: recall 1.00 |
| Ask Sangam retrieval | BM25 + refusal guard + domain guardrail | top-1 0.84 · refusal 0.98 · off-topic detection 1.00 (74 questions) | M2 keyword lookup: 0.34 |

Full tables are in `results/*.csv`. Why each algorithm was chosen is explained in the notebook, after each section.

## Re-run

From the repository root (the backend venv has every dependency):

```bash
backend/.venv/Scripts/python backend/scripts/make_synthetic.py
```

```bash
backend/.venv/Scripts/python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=sangam ML/Sangam_ML_Algorithm_Selection.ipynb
```

Edit the notebook directly in Jupyter. The Gemini cell runs only when `backend/.env` holds keys; otherwise it is skipped and the
extractive fallback is still evaluated.

Sangam is open to IITM BS Degree-level students only, so every synthetic student is Degree level and student level is not a
priority feature.

## Caveats

* All data is synthetic. The labels come from written rubrics with 5–7 % deliberate noise. Hand-check the gold set before calling it
  human-labelled.
* The test sets are small (30 / 54 / 33 items), so differences of a few points are within noise. Section 1c shows a bootstrap interval for
  matching.

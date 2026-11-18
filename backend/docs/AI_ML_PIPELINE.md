# Sangam AI/ML pipeline (assistant_ai)

All AI is **advisory**. Only `mentoring.services.approve_match()` creates a mentorship, and only after the mentor confirms and IIC
approves. Every feature works with the LLM and the embedding model switched off.

## Layout

```
backend/
  apps/assistant_ai/
    ml/            framework-free core (also used by the notebook and scripts)
      text.py        tokens, tags, Jaccard, PII stripping
      embeddings.py  MiniLM / Gemini / hashing-mock embedders, vector cache, timeouts
      matching.py    KAN-46 hybrid matcher + rule fallback + reasons
      priority.py    request priority points rubric
      dropoff.py     KAN-58 drop-off features + weighted risk score
      summary.py     KAN-57 prompt, JSON validation, extractive fallback
      retrieval.py   BM25 for Ask Sangam + refusal guard
      evaluation.py  P@k, MRR, nDCG
    llm.py         the ONLY module that calls Gemini / Ollama (key + model rotation, timeouts, PII re-strip)
    services.py    Django glue: filters, audit rows, assessments, insights
    views.py urls.py   endpoints (see openapi/sangam_ai.yaml)
    prompts/       summary_v1.txt, explain_v1.txt, CHANGELOG.md (frozen, versioned)
    management/commands/load_synthetic.py
    tests/test_ai.py   32 tests, mocks only (no network, no model, no key)
  scripts/make_synthetic.py      synthetic datasets -> fixtures/synthetic/
  scripts/evaluate_matching.py   KAN-47 evaluation -> reports/matching_eval.md
  openapi/sangam_ai.yaml          AI endpoints, validated OpenAPI 3.0
ML/Sangam_ML_Algorithm_Selection.ipynb   algorithm comparison + accuracy
```

## Setup

```bash
cd backend && python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill it in. Never commit `.env`.

| Variable | Meaning |
|---|---|
| `AI_PROVIDER` | `gemini`, `ollama` or `none` |
| `GEMINI_API_KEYS` | one or more keys, comma-separated. On quota, expiry or an invalid key, the client rotates to the next key |
| `GEMINI_MODELS` | tried in order for each key. A 404 (model not enabled for that key) or 503 (overloaded) moves to the next model |
| `SANGAM_EMBEDDING_BACKEND` | `minilm` (default), `gemini` or `none` |
| `USE_SUPABASE` | `1` Supabase Postgres, `0` local sqlite. Tests always use sqlite |
| `SANGAM_STORE_AI_SUMMARIES` | `0` by default. Turn on only after the team/TA confirm that storing approved summaries is allowed |

New migrations: `accounts 0002` (skills, bio, is_discoverable), `mentoring 0002` (preferred_mentor), `assistant_ai 0002`
(AIRequestAssessment, MeetingSummary). Apply them with `python manage.py migrate` against the target database.

## Commands

| Task | Command (from `backend/`) |
|---|---|
| Generate synthetic data | `.venv/Scripts/python scripts/make_synthetic.py` |
| KAN-47 evaluation | `.venv/Scripts/python scripts/evaluate_matching.py` (add `--mock` to run without the model) |
| Tests (offline) | `.venv/Scripts/python -m pytest` |
| Load demo data (dev DB only) | `USE_SUPABASE=0 .venv/Scripts/python manage.py migrate && USE_SUPABASE=0 .venv/Scripts/python manage.py load_synthetic` |

## Matching (KAN-46 / KAN-47)

`score = 0.50·semantic + 0.20·domain + 0.15·skills + 0.08·pathway + 0.04·experience + 0.03·preferred`. These are the W2 weights, chosen
from 4 settings on the 70 % tuning split. If the embedding model is missing or times out, the semantic weight drops to 0, the rest are
re-normalised, and the response says `algorithm: rule_based_v1, fallback: true`.

| Held-out gold (30 requests) | P@3 | P@5 | MRR | nDCG@5 |
|---|---|---|---|---|
| legacy rules-v1 (M2) | 0.26 | 0.25 | 0.41 | 0.53 |
| rule_based_v1 | 0.50 | 0.43 | 0.67 | 0.70 |
| **hybrid_v1** | **0.69** | **0.55** | **0.82** | **0.82** |

Warm latency is about 30 ms per request for 63 eligible mentors. The model is warmed in a background thread when `runserver` starts.

## Test cases (format: API · inputs · expected · actual · result)

| # | API | Inputs | Expected | Actual | Result |
|---|---|---|---|---|---|
| 1 | GET /requests/{id}/suggestions/ | student / mentor JWT | 403 | 403 | Pass |
| 2 | GET /requests/{id}/suggestions/?k=5 | IIC, mock embedder | NLP mentor first; unverified, unavailable, hidden and busy mentors absent; no email; audit row written | as expected | Pass |
| 3 | same | same request twice | identical order | identical | Pass |
| 4 | same | embedding model broken | 200, `rule_based_v1`, `fallback: true` | as expected | Pass |
| 5 | same | k = 0, 50, abc | 422 | 422 | Pass |
| 6 | same | mentor has a pending check for this request | that mentor excluded | excluded | Pass |
| 7 | GET/PATCH /requests/{id}/priority/ | student; IIC; override without reason; with reason | 403; 200; 422; 200 with `effective_priority`=override | as expected | Pass |
| 8 | POST …/meetings/{mid}/summary/ | student, IIC, other mentor | 403 | 403 | Pass |
| 9 | same | mentor, LLM off, notes with planted PII | 200, extractive, no surname/phone, nothing stored | as expected | Pass |
| 10 | same | LLM returns invalid JSON, then valid | one retry; prompt free of PII; `fallback: false` | as expected | Pass |
| 11 | same | LLM timeout | 503, `fallback: true`, draft returned | as expected | Pass |
| 12 | POST …/summary/confirm/ | storage off / on | 200 `stored: false` / 201, prompt version saved | as expected | Pass |
| 13 | GET /admin/insights/, /at-risk/ | student; IIC | 403; counts match seed; flagged pair has reasons; status unchanged | as expected | Pass |
| 14 | POST /assistant/chat/ | "Please approve my mentoring request" | refusal pointing to IIC, `message_stored: false` | as expected | Pass |
| 15 | llm.generate | keys k1, k2 exhausted, k3 works | rotates to k3 and stays there | as expected | Pass |
| 16 | scripts/evaluate_matching.py --mock | no network | report produced | produced | Pass |

These are automated in `apps/assistant_ai/tests/test_ai.py`, and all pass.

## Demo scripts

**A. With Gemini.** Set `AI_PROVIDER=gemini`, then call `/ai/health/` (provider available). Then call `/requests/{id}/suggestions/`
(`hybrid_v1`, friendly explanations), the summary endpoint (`provider: gemini`), and `/assistant/chat/` (grounded answer plus a refusal).

**B. LLM off.** Set `AI_PROVIDER=none` and `SANGAM_EMBEDDING_BACKEND=none`. The same calls now return `rule_based_v1` with
`fallback: true`, an extractive summary, and the article snippets. Every endpoint still works.

## Ask Sangam guardrails

1. Requests to approve, assign or pair are refused (`retrieval.is_decision_request`).
2. Questions that are not about the Sangam app are declined before retrieval or any model call (`retrieval.is_out_of_domain`):
   an off-topic block list wins, otherwise the question must contain a clear Sangam term.
3. The LLM is told to answer only Sangam questions from the retrieved articles, and to reply `OUT_OF_SCOPE` otherwise.
4. That reply is re-checked and turned into the standard decline message.

The guardrail classifies all 74 synthetic help questions correctly. Ask Sangam is available to students, mentors and IIC admins.

## Eligibility

Sangam is open to IITM BS Degree-level students only. Registration rejects other levels, and only approved Degree-level students can
submit requests. Student level is therefore not used in the priority score.

## Privacy safeguards

* Emails, phones, roll numbers and surnames are stripped before every LLM or embedding call (`ml.text.strip_pii`), and stripped again
  inside `llm.generate_detailed`.
* Chat messages are never stored. Summary drafts are never stored unless confirmed and storage is enabled.
* Insights are aggregates only. AI responses never include email or phone.
* AI errors are logged by exception type only, never with content.
* Synthetic roll numbers deliberately do not follow the real IITM format (for example `1abc345@ds.study.iitm.ac.in`).

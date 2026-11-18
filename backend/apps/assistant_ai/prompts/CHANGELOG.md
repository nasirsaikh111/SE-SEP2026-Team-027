# Prompt changelog

Prompts are versioned and frozen. A changed prompt gets a new file (`summary_v2.txt`); never edit a released one.

| Version | Used by | Date | Notes |
|---|---|---|---|
| summary_v1 | `summarise_notes()` (KAN-57) | 2026-11-18 | 3–5 sentence summary + up to 5 action items, strict JSON |
| explain_v1 | `explain_candidates()` (KAN-46) | 2026-11-18 | One-sentence rephrase of template reasons; ranking unaffected |
| chat_v1 (inline in `services.chat_answer`) | Ask Sangam | 2026-11-18 | Answer only from retrieved KnowledgeArticles; refuse approve/pair asks |
| chat_v2 (inline in `services.chat_answer`) | Ask Sangam | 2026-11-19 | Domain guardrail: Sangam-only questions, `OUT_OF_SCOPE` reply token re-checked, no general career/coding advice |

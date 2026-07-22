# NewsBot — Implementation Plan

Ordered phases to fully build the application described in `spec.md`.

---

## Phase 0 — Project setup ✅

1. [x] Init Python project (`pyproject.toml` / `requirements.txt`), venv, `.gitignore`, `.env.example`
2. [x] Config module for secrets/settings (Gmail OAuth, Telegram token/chat ID, LLM base URL, label name, timezone)

---

## Phase 1 — Gmail ingestion ✅

3. [x] Enable Gmail API + service account / OAuth (read-only); credentials in `creds.json`
4. [x] Create/use Gmail label (e.g. `Newsletters`) and filter rules
5. [x] Implement Gmail client: list unread (or new) messages under that label
6. [x] Implement HTML → plain text extraction; capture subject, date, links, body
7. [x] Track processed message IDs so the same email isn’t digested twice

---

## Phase 2 — Local LLM summarizer ✅

8. [x] Wire client to Ollama/LM Studio (HTTP)
9. [x] Implement summarizer with the structured prompt (summary, key points, facts, why it matters, follow-ups)
10. [x] Parse/normalize LLM output into a stable schema

---

## Phase 3 — Vector store ✅

11. [x] Choose Chroma or FAISS; set up persistence on disk
12. [x] Embedding model (local) for summaries + questions
13. [x] `store-summary`: save text, metadata (title, date, links, message id), embedding
14. [x] Search/retrieve top-k relevant summaries for a query

---

## Phase 4 — FastAPI backend ✅

15. [x] Scaffold FastAPI app + health check
16. [x] `POST /store-summary` — persist one summary
17. [x] `POST /daily-digest` — full pipeline: fetch → extract → summarize → store → format Telegram text
18. [x] `POST /ask` — embed question → retrieve → LLM answer with context
19. [x] Wire pipeline services together (orchestration layer)

---

## Phase 5 — Telegram ✅

20. [x] Create bot via BotFather; get token + your chat ID
21. [x] Send digest messages in the agreed format (numbered items, summary, why it matters, “ask me…” footer)
22. [x] Receive user messages; forward to `/ask`; reply with the answer
23. [x] Optional: commands like `/digest` to trigger a manual run

---

## Phase 6 — Scheduler ✅

24. [x] Add APScheduler (or equivalent) cron: 8:30 AM in your timezone
25. [x] Hook cron job to `run_daily_digest`
26. [x] Ensure scheduler starts with the FastAPI app lifecycle

---

## Phase 7 — End-to-end + polish ✅

27. [x] Manual dry run with a few real newsletter emails
28. [x] Verify Telegram digest + follow-up Q&A end-to-end
29. [x] Error handling/logging (Gmail failures, LLM timeouts, empty inbox)
30. [x] README: setup (Gmail, Telegram, Ollama), env vars, how to run
31. [x] Optional: Dockerfile / compose for local deploy

---

## Suggested build order

Setup → Gmail extract → summarizer → vector store → FastAPI endpoints → Telegram → scheduler → E2E test

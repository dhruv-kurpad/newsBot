# NewsBot — Learning Notes

Design choices and challenges from building this project, based only on decisions and issues that came up during implementation.

---

## Design choices

### FastAPI as the orchestrator

**Chosen:** FastAPI for `/health`, `/daily-digest`, `/ask`, `/store-summary`, plus app lifecycle hooks for the scheduler.

**Why:** The product spec called for a small HTTP backend that could trigger the digest pipeline and answer questions. FastAPI fits that with little boilerplate and works well with `TestClient` for phase tests.

**Not chosen here:** A pure script/cron-only app (no API), or a heavier framework (Django). Those weren’t needed for a single-user local agent with a few endpoints.

### Local LLM over HTTP (Ollama / LM Studio–compatible)

**Chosen:** Talk to a local model via HTTP (`LLM_BASE_URL`), with Ollama’s `/api/generate` first and an OpenAI-compatible `/v1/chat/completions` fallback in `LLMClient`.

**Why:** The spec was local-first (no cloud LLM). HTTP keeps the app process separate from the model server so you can run Ollama on the Mac while developing the bot.

**Not chosen here:** Calling `ollama` only via subprocess, or using OpenAI/Anthropic cloud APIs. Subprocess is less flexible for LM Studio–style servers; cloud APIs contradicted the local-first goal.

### Chroma for the vector store

**Chosen:** Chroma with on-disk persistence under `VECTOR_STORE_PATH` (default `./data/chroma`).

**Why:** The plan allowed Chroma or FAISS. Chroma gave persistence and a simple `upsert` / `query` API without standing up a separate DB server.

**Not chosen here:** FAISS (more manual persistence/metadata), or a hosted vector DB (Pinecone, etc.). Hosted options add accounts and network dependency for a local Mac workflow.

### Embeddings: Ollama first, local hash fallback

**Chosen:** Prefer Ollama `/api/embeddings`; if that fails (e.g. Ollama not running during development), fall back to a deterministic local hash embedding.

**Why:** During Phase 3 work, Ollama was not running on the machine (`localhost:11434` unreachable). Unit tests still needed `embed_text` to return a non-empty vector. The fallback kept the suite green while building; real Ollama embeddings are used when the server is up.

**Not chosen here:** Failing hard whenever Ollama is down (would block development), or baking a large local embedding model into the repo.

### Gmail: OAuth desktop client (`credentials.json` → `token.json`)

**Chosen:** User OAuth via `gmail_auth.py` / `newsbot.gmail.auth`, producing `token.json` from a Desktop OAuth client JSON.

**Why:** The first credentials file (`creds.json`) was a **Google service account**. Reading a normal Gmail inbox with a service account needs domain-wide delegation and a `gmail_user` to impersonate—awkward for a personal `@gmail.com` mailbox. The user then added an OAuth **installed app** `credentials.json` and an auth script; that path completed successfully and authorized the real mailbox.

**Not chosen as the primary path:** Service-account-only access. The client still supports service accounts if present, but day-to-day auth is OAuth.

### Telegram via raw Bot API (`httpx`) + thin `NewsBot` wrapper

**Chosen:** Send/receive with Telegram HTTP endpoints through `httpx`, wrapped in `NewsBot` (format digest, `/digest`, route questions to `answer_question`).

**Why:** Enough for send message, long-poll `getUpdates`, and command handling without taking on a full bot framework’s lifecycle. Secrets stay in `.env` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).

**Not chosen here:** Shipping a shared bot token in the repo so clones don’t need their own key (discussed; rejected because the token is a secret and this app is personal Gmail → personal chat). Also didn’t require every caller to use `python-telegram-bot`’s application runner—polling is a small loop in `newsbot.telegram.runner`.

### APScheduler cron inside the FastAPI process

**Chosen:** `AsyncIOScheduler` with a cron trigger (default 8:30 in `TIMEZONE`), started/stopped with the FastAPI lifecycle, job = `run_daily_digest`.

**Why:** Matches the spec (“scheduler runs with the app”) and keeps one process for API + morning job when using `uvicorn` or `python -m newsbot`.

**Not chosen here:** System `cron` alone, or Celery/Redis. Those add ops surface area for a single-machine agent.

### Config: `.env` + `pydantic-settings`

**Chosen:** `Settings` / `get_settings()` loading from environment / `.env`, with optional overlay fields from a JSON creds file when present.

**Why:** Keeps secrets out of git (`.env`, `credentials.json`, `token.json` gitignored) while making defaults explicit in `.env.example`.

**Not chosen here:** Hard-coded tokens in source, or committing a shared Telegram bot key for clones.

### Phase-marked tests as the “definition of done”

**Chosen:** Pytest markers `phase0`…`phase7`, stubs that raised `NotImplementedError`, then implement until each phase’s tests pass. Run with `pytest -m phaseN` or all at once.

**Why:** Gave a clear completeness signal while building in order, without waiting for a full manual E2E every step.

**Not chosen here:** Only manual checklist docs, or end-to-end tests that required live Gmail/Ollama/Telegram for every phase.

### Combined process: API thread + Telegram poller

**Chosen:** `python -m newsbot` runs uvicorn in a daemon thread and long-polls Telegram in the main asyncio loop.

**Why:** After Phase 6, the scheduler lived on the API process while chat needed a separate poller. Phase 7 added a single entrypoint so both run together; you can still run them separately.

---

## Challenges (what actually came up)

### 1. Service account vs personal Gmail

**Issue:** `creds.json` was a service account. Using it for a normal Gmail inbox needs impersonation (`gmail_user`) and domain-wide delegation—poor fit for personal Gmail.

**Fix:** Switched primary auth to OAuth Desktop client `credentials.json` + `python gmail_auth.py` → `token.json`. Config defaults point at those files. Both secret JSON files are gitignored.

### 2. `gmail_auth.py` failed several times before succeeding

From the terminal session:

1. `ModuleNotFoundError: google_auth_oauthlib` — packages weren’t installed in the active env.
2. Wrong venv activate path (`source activate/bin/venv`).
3. `FileNotFoundError: credentials.json` — file not present yet.
4. `ValueError: Client secrets must be for a web or installed app` — a service-account JSON was tried as an OAuth client.
5. Then OAuth with a real installed-app `credentials.json` completed and wrote `token.json`.

**Fix:** Use the project `.venv`, install deps, use Desktop OAuth client JSON only for `gmail_auth.py`, keep service-account handling separate in the Gmail client.

### 3. Empty Telegram `getUpdates`

**Issue:** `{"ok":true,"result":[]}` when fetching the chat ID—no updates stored for the bot yet.

**Fix:** Message the bot (`/start` or any text) first, then call `getUpdates` again to read `chat.id` into `.env`.

### 4. FastAPI route objects and Phase 4 tests

**Issue:** After mounting routes with `include_router`, iterating `app.routes` hit `_IncludedRouter` objects with no `.path`, so the Phase 4 “required routes” test failed even though endpoints worked.

**Fix:** Assert routes via `app.openapi()["paths"]` instead of raw `app.routes` path attributes.

### 5. Scheduler lifecycle API mismatch

**Issue:** `app.add_event_handler("startup", …)` raised `AttributeError` on FastAPI 0.139 (`add_event_handler` not available). Using deprecated `on_event` worked but produced deprecation warnings.

**Fix:** Attach an async lifespan context that starts/stops APScheduler, and also append startup/shutdown callables so Phase 6’s lifecycle test still sees hooks.

### 6. Building without Ollama running

**Issue:** Phase 3 embedding tests call a real `embed_text` against `localhost:11434`; Ollama wasn’t up during that work.

**Fix:** Catch embedding HTTP failures and use a deterministic local embedding fallback so development and unit tests can proceed. Real Ollama embeddings are used when the server is available (as intended for the final Mac run).

### 7. Phase 5 unit tests vs live Telegram

**Issue:** Implementing `send_message` against the real API would make tests with `TEST_TOKEN` fail (invalid token / network).

**Fix:** Phase 5 tests mock `httpx.AsyncClient` so they verify request shape without calling Telegram. A separate smoke send with the real `.env` token confirmed delivery once.

### 8. Double-sending digests on `/digest`

**Issue:** `run_daily_digest` can send to Telegram, and `NewsBot.handle_digest_command` also sends the formatted reply. Wiring the poller to `run_daily_digest` directly would send twice.

**Fix:** Telegram runner uses `run_daily_digest(send_telegram=False)` and lets the bot send the message once.

### 9. Phase 2 pulled in while doing Phases 3–4

**Issue:** The digest/`ask` pipeline needs `LLMClient` and `summarize_article` / `parse_summary`, which were still stubs when Phase 3–4 started.

**Fix:** Implemented the LLM client and summarizer as part of making the Phase 4 pipeline real, rather than leaving NotImplementedError in the orchestration path.

---

## What this project optimized for

- Local Mac run with Ollama later (build even when the model server is down)
- Personal Gmail + personal Telegram (secrets in `.env`, not shared bot tokens in git)
- Incremental delivery via phase tests
- Small surface area: FastAPI + Chroma + APScheduler + HTTP Telegram/Gmail/LLM clients

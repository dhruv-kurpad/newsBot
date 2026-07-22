# NewsBot

Daily newsletter digests via Telegram, with retrieval-backed follow-up Q&A over stored summaries. Runs locally with **Gmail**, **Ollama**, and a **Telegram** bot.

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) running locally
- A Gmail account with a label for newsletters (default: `Newsletters`)
- A Telegram bot from [@BotFather](https://t.me/BotFather)

## Setup

```bash
cd NewsBot
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

### 1. Gmail OAuth

1. In Google Cloud Console, enable the Gmail API and create an **OAuth Desktop** client.
2. Download the client JSON as `credentials.json` in the project root.
3. Authorize and create `token.json`:

```bash
python gmail_auth.py
```

4. In Gmail, create a label (e.g. `Newsletters`) and filter newsletters into it.

### 2. Ollama

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

Confirm Ollama is at `http://localhost:11434` (or change `LLM_BASE_URL` in `.env`).

### 3. Telegram

1. Create a bot with BotFather and copy the token into `.env` as `TELEGRAM_BOT_TOKEN`.
2. Message the bot, then set `TELEGRAM_CHAT_ID` (from `getUpdates` or @userinfobot).

### 4. Environment

Edit `.env` (never commit this file):

| Variable | Purpose |
|----------|---------|
| `GMAIL_CREDENTIALS_PATH` | OAuth client JSON (`credentials.json`) |
| `GMAIL_TOKEN_PATH` | Saved OAuth token (`token.json`) |
| `GMAIL_LABEL` | Label to read (default `Newsletters`) |
| `LLM_BASE_URL` / `LLM_MODEL` | Ollama endpoint + chat model |
| `EMBEDDING_MODEL` | Ollama embedding model |
| `VECTOR_STORE_PATH` | Chroma persistence directory |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Bot credentials |
| `TIMEZONE` / `DIGEST_HOUR` / `DIGEST_MINUTE` | Daily schedule (default 8:30) |

## Run

**API + 8:30 AM scheduler**

```bash
uvicorn newsbot.api.app:app --reload
```

**Telegram poller** (follow-ups + `/digest`)

```bash
python -m newsbot.telegram.runner
```

**Both together**

```bash
python -m newsbot
```

### Useful endpoints

- `GET /health`
- `POST /daily-digest` — run the pipeline now
- `POST /ask` — `{"question":"..."}`
- `POST /store-summary` — persist a summary manually

### Telegram commands

- `/help` — usage
- `/digest` — run digest now
- any other text — Q&A over stored summaries

## Tests

```bash
pytest                         # all phases
pytest -m phase7               # polish checks only
./scripts/run_phase_tests.sh 3 # one phase
```

## Docker (optional)

```bash
docker compose up --build
```

Mounts `.env`, `credentials.json`, `token.json`, and `./data` for persistence. Ollama should still run on the host (`host.docker.internal:11434` on Mac).

## Project layout

- `newsbot/gmail` — Gmail fetch + extract
- `newsbot/llm` — local summarizer
- `newsbot/vectorstore` — Chroma store
- `newsbot/api` — FastAPI
- `newsbot/telegram` — bot + formatting
- `newsbot/scheduler` — APScheduler cron
- `spec.md` / `plan.md` — product spec and build plan

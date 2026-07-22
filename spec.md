# NewsBot — Product Spec

Daily newsletter digests via Telegram, with retrieval-backed follow-up Q&A over stored summaries.

---

## 1. Overview

Every morning at **8:30 AM**, the agent:

1. Checks a specific Gmail label where newsletters land
2. Pulls all new emails
3. Extracts article content
4. Summarizes each article with a local LLM
5. Sends a Telegram digest
6. Stores summaries for follow-up questions
7. Answers questions via retrieval over stored summaries

This is an agentic workflow: scheduled ingestion + on-demand Q&A over personal newsletter knowledge.

---

## 2. Architecture

### 2.1 Components

| Component | Role |
|-----------|------|
| **FastAPI backend** | Orchestrates fetch → extract → summarize → store → notify; serves Q&A |
| **Gmail watcher** | Pulls emails from a specific Gmail label |
| **LLM summarizer** | Local model (Ollama, LM Studio, etc.) |
| **Vector store** | Persists summaries + embeddings for follow-up Q&A (Chroma or FAISS) |
| **Telegram bot** | Delivers the daily digest and handles follow-up questions |
| **Scheduler** | Runs the daily job at 8:30 AM (APScheduler) |

### 2.2 Daily workflow

```
Gmail label → extract text → local LLM summarize → vector store
                                              ↓
                                    Telegram daily digest
```

**Steps:**

1. **Fetch emails** — Gmail API, filter by label (e.g. `Newsletters`)
2. **Extract article text** — Clean HTML → plain text
3. **Summarize with local LLM** — Structured prompt (see §4)
4. **Store summary + embedding** — Chroma or FAISS for retrieval
5. **Send Telegram message** — Digest with links, key points
6. **Follow-up Q&A** — On demand via Telegram → embed → retrieve → LLM answer

---

## 3. API (FastAPI)

| Endpoint | Purpose |
|----------|---------|
| `POST /daily-digest` | Run (or trigger) the full daily pipeline |
| `POST /ask` | Answer a follow-up question over stored summaries |
| `POST /store-summary` | Persist a summary + embedding (used by the pipeline) |

Scheduler invokes the digest path on cron; Telegram messages map to `/ask` (and optionally `/daily-digest` for manual runs).

---

## 4. Summarization prompt

```text
Summarize the following newsletter article into:
- Summary
- Key points
- Important facts
- Why it matters
- Follow-up questions you can ask me

Article:
{{content}}
```

---

## 5. Telegram daily digest format

```text
Daily AI News Digest — July 22

1. OpenAI releases new safety framework
   Summary: …
   Why it matters: …

2. Anthropic expands Claude API
   Summary: …

Ask me: “Tell me more about item 2” or “Explain the safety framework.”
```

Include: date title, numbered items, short summary + why it matters (and links / key points as available), plus a short prompt for how to ask follow-ups.

---

## 6. Follow-up Q&A flow

1. User asks a question in Telegram  
   e.g. *“Tell me more about the AI regulation article.”*
2. FastAPI backend receives it (`/ask`)
3. Embed the question
4. Search the vector DB for relevant summaries
5. Pass retrieved text + question to the local LLM
6. Send the answer back to Telegram

This provides ChatGPT-style Q&A over newsletter content.

---

## 7. Implementation plan

1. **Gmail API** — Enable Gmail API → OAuth → read-only access  
2. **Gmail label rule** — e.g. `Newsletters`  
3. **FastAPI backend** — `/daily-digest`, `/ask`, `/store-summary`  
4. **Scheduler** — APScheduler cron at 8:30 AM  

   ```python
   scheduler.add_job(run_daily_digest, "cron", hour=8, minute=30)
   ```

5. **LLM summarizer** — Call local model via HTTP or subprocess  
6. **Vector DB** — Store summaries + embeddings (Chroma or FAISS)  
7. **Telegram bot** — `python-telegram-bot`  
8. **Deploy (optional)** — Run locally or containerize  

---

## 8. Non-goals (initial scope)

- Multi-user / multi-tenant support  
- Cloud-hosted LLM (local-first)  
- Full article archival beyond summaries + embeddings needed for Q&A  
- Web UI (Telegram is the primary interface)

---

## 9. Success criteria

- [ ] At 8:30 AM, new emails under the configured Gmail label are processed  
- [ ] Each article yields a structured summary  
- [ ] A Telegram digest is delivered in the format above  
- [ ] Summaries are stored and searchable  
- [ ] Follow-up questions in Telegram return grounded answers from retrieved summaries  

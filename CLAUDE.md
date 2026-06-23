# Home Assistant — AI Planning Coach

Personal AI assistant running as a Telegram bot. Acts as a planning coach: monthly → weekly → daily → evening check-in. Built to be extended with new modules (journaling, learning, etc.).

## How to Run

```bash
python311 main.py bot        # start Telegram bot (polling mode)
python311 main.py ingest     # index all JSON files in data/raw/
python311 main.py ask "..."  # one-shot RAG query (CLI)
```

**Always use `python311`**, not `python`. Two Python installs exist via Scoop; packages are in `python311`.

## Stack

| Layer | Technology |
|---|---|
| LLM | DeepSeek API via `OpenAILike` (NOT `OpenAI` — model name not in OpenAI list) |
| RAG | LlamaIndex |
| Vector store | ChromaDB embedded (Windows) / Qdrant Docker (Linux) — swap via `VECTOR_BACKEND` env var |
| Embeddings | `BAAI/bge-small-en-v1.5` via sentence-transformers (local, no API cost) |
| Storage | SQLite (`data/sqlite/app.db`) |
| Chat | Telegram Bot API, polling mode (no public IP needed) |

## Project Structure

```
src/core/        — shared infrastructure, never import modules from here
  config.py      — all env vars and constants
  logger.py      — get_logger(name) → writes to data/logs/app.log + console
  db.py          — SQLite helpers (init_db, save_plan, get_tasks, etc.)
  llm.py         — DeepSeek client singleton via OpenAILike
  embedder.py    — HuggingFace embedding singleton
  vector_store.py — ChromaDB/Qdrant adapter (only file that changes per backend)
  ingest.py      — JSON file → chunks → vector store (dedup by file hash)
  query.py       — RAG: retrieve top-k chunks → LLM answer

src/bot/         — Telegram interface
  handler.py     — async command/message handlers
  router.py      — dispatches to modules, holds active sessions
  formatter.py   — Telegram Markdown helpers

src/modules/     — one file per use case
  planner.py     — planning coach (monthly/weekly/daily/evening sessions)

data/
  raw/           — JSON knowledge files (NOT git-tracked)
  chroma_db/     — ChromaDB persistence (NOT git-tracked)
  sqlite/app.db  — all plans, tasks, conversations (NOT git-tracked)
  logs/app.log   — rotating log file (NOT git-tracked)
```

## Key Conventions

**Adding a new module** (e.g., journaling):
1. Create `src/modules/journal.py`
2. Add handler functions in `src/bot/handler.py`
3. Register commands in `src/bot/router.py`
4. No changes to `src/core/`

**SQLite tables** must always have these columns:
```sql
created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
deleted     INTEGER  DEFAULT 0
```
- Soft delete: `UPDATE SET deleted=1` — always filter `WHERE deleted=0`
- Hard delete: `DELETE FROM` — only for cleanup/GDPR

**Vector store swap** (Windows → Linux):
- Set `VECTOR_BACKEND=qdrant` in `.env`
- Run `docker run -p 6333:6333 qdrant/qdrant`
- Zero code changes needed

## Environment Variables (`.env`)

```
DEEPSEEK_API_KEY=...
TELEGRAM_BOT_TOKEN=...       # from @BotFather
ALLOWED_USER_ID=...          # from @userinfobot — only this user can chat with the bot
VECTOR_BACKEND=chroma        # or "qdrant"
QDRANT_URL=http://localhost:6333
```

## Known Gotchas

- **DeepSeek needs `OpenAILike`** — `llama_index.llms.openai.OpenAI` rejects `deepseek-chat` as an unknown model. Use `llama_index.llms.openai_like.OpenAILike` with `is_chat_model=True, context_window=65536`.
- **Scoop Python conflict** — `python` points to a broken install; `python311` is the working one.
- **Telegram Markdown** — use `parse_mode="Markdown"` on all replies; escape special chars if needed.
- **Session state** — active sessions are in-memory in `src/bot/router.py`. Restarting the bot clears them.

## Logs

```bash
# tail the log in real time
Get-Content data/logs/app.log -Wait -Tail 50
```

Log levels: INFO to console + file, DEBUG to file only.

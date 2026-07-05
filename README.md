# AI Assistant — Personal Planning Coach

A self-hosted AI assistant for personal planning and knowledge management. Runs on a home server with no cloud subscription beyond the DeepSeek API. Two interfaces: a Telegram bot for daily use and a web UI for richer interaction.

---

## Features

- **Planning coach** — guided sessions for monthly, weekly, daily, and evening review
- **Free chat** — general-purpose AI conversation
- **Knowledge base** — index your own documents (JSON) and query them with RAG
- **Web UI** — browser interface with dark theme, accessible from any device on your network
- **Telegram bot** — chat commands, no browser needed
- **Multi-user** — family-friendly with `admin` and `member` roles
- **2FA** — optional TOTP (Google Authenticator) per user
- **Secure auth** — bcrypt passwords, JWT + refresh token session, login rate limiting

---

## Prerequisites

- Python 3.11 (`python311` on this machine via Scoop)
- A [DeepSeek API key](https://platform.deepseek.com/)
- A Telegram bot token (from [@BotFather](https://t.me/BotFather)) — optional if only using web UI
- Your Telegram user ID (from [@userinfobot](https://t.me/userinfobot)) — optional

---

## Setup

**1. Install dependencies**

```powershell
python311 -m pip install -r requirements.txt
```

**2. Configure environment**

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```env
DEEPSEEK_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_token_here   # optional
ALLOWED_USER_ID=123456789            # optional — your Telegram user ID

JWT_SECRET=                          # generate below
```

Generate a JWT secret:
```powershell
python311 -c "import secrets; print(secrets.token_hex(32))"
```

**3. Create the first admin account**

```powershell
python311 scripts/create_user.py --username khai --password yourpassword --role admin
```

There is no self-registration. All accounts are created this way.

**4. Apply database migrations**

```powershell
python311 main.py migrate
```

---

## Running

```powershell
# Web UI only — http://localhost:8000
python311 main.py web

# Telegram bot only
python311 main.py bot

# Both together (bot runs as a background thread)
python311 main.py both
```

---

## Usage

### Web UI

Open `http://localhost:8000` and sign in. The sidebar gives access to all features. Admin users see an extra **Admin** section for managing other users.

### Telegram Bot

| Command | What it does |
|---|---|
| `/start` | Show available commands |
| `/monthly` | Start a monthly planning session |
| `/weekly` | Start a weekly planning session |
| `/daily` | Start a daily planning session |
| `/evening` | Start an evening check-in |
| `/ask <question>` | Search the knowledge base |

### Knowledge Base

Put `.json` files in `data/raw/`, then:

```powershell
python311 main.py ingest
```

Documents are chunked, embedded locally (no API cost), and stored in ChromaDB. Query them from the web UI or Telegram with `/ask`.

### User Management

```powershell
# Create a user
python311 scripts/create_user.py --username alice --password secret --role member

# Apply DB migrations after updates
python311 main.py migrate
```

---

## Configuration

All settings live in `.env`. See `.env.example` for the full list.

| Variable | Default | Description |
|---|---|---|
| `DEEPSEEK_API_KEY` | — | Required |
| `TELEGRAM_BOT_TOKEN` | — | Required for bot |
| `ALLOWED_USER_ID` | — | Telegram user ID allowed to use the bot |
| `JWT_SECRET` | — | Required — random 32-byte hex string |
| `JWT_EXPIRY_HOURS` | `24` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRY_DAYS` | `30` | Refresh token lifetime |
| `LOGIN_MAX_ATTEMPTS` | `5` | Failed logins before lockout |
| `LOGIN_LOCKOUT_MINUTES` | `15` | Lockout duration |
| `TOTP_ISSUER` | `AI Assistant` | Name shown in authenticator apps |
| `VECTOR_BACKEND` | `chroma` | `chroma` (Windows) or `qdrant` (Docker) |
| `ENVIRONMENT` | `dev` | `prod` enables secure cookies + HSTS |

### Switching to Qdrant (Linux/Docker)

```env
VECTOR_BACKEND=qdrant
QDRANT_URL=http://localhost:6333
```

```bash
docker run -p 6333:6333 qdrant/qdrant
```

No code changes needed.

---

## Production Deployment

Set `ENVIRONMENT=prod` in `.env` to enable the `Secure` cookie flag and HSTS headers.

Recommended: expose via **Cloudflare Tunnel** — free TLS, no port forwarding, works on a home connection.

```bash
cloudflared tunnel run <tunnel-name>
```

---

## Project Structure

```
src/
  core/       — shared infrastructure (db, auth, llm, embeddings, vector store)
  bot/        — Telegram interface
  modules/    — feature logic (planner, ...)
  web/        — FastAPI app + static HTML

data/
  raw/        — your JSON knowledge files (not tracked by git)
  sqlite/     — SQLite database (not tracked by git)
  chroma_db/  — ChromaDB embeddings (not tracked by git)
  logs/       — rotating log file (not tracked by git)
  migrations/ — SQL migration files

scripts/
  create_user.py   — admin CLI for account creation
  gen_cert.py      — generate self-signed TLS cert for local HTTPS
```

---

## Stack

| | |
|---|---|
| LLM | DeepSeek (`deepseek-chat`) |
| RAG | LlamaIndex |
| Embeddings | `BAAI/bge-small-en-v1.5` (local) |
| Vector store | ChromaDB / Qdrant |
| Database | SQLite + SQLModel ORM |
| Web | FastAPI + Uvicorn |
| Bot | python-telegram-bot |
| Auth | bcrypt + JWT + TOTP |

---

## Logs

```powershell
Get-Content data/logs/app.log -Wait -Tail 50
```

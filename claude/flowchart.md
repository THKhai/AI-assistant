# System Flowchart

```mermaid
flowchart TD
    U(["📱 iPhone / Telegram"])
    UB(["🖥 Browser"])

    subgraph TelegramCloud ["Telegram Cloud"]
        TG["Telegram Servers"]
    end

    subgraph Entry ["main.py - parallel threads"]
        direction LR
        BOT["bot/handler.py\npolling - Thread 2"]
        WEB["web/app.py\nFastAPI - Thread 1"]
    end

    subgraph Router ["Routing and Sessions"]
        ROUTER["bot/router.py"]
        WSESS["web sessions dict\nsession_id to PlannerSession"]
    end

    subgraph Core ["src/core/"]
        LLM["llm.py\nDeepSeek API\nOpenAILike singleton"]
        RAG["query.py\nRAG engine"]
        INGEST["ingest.py\nJSON indexer"]
        EMB["embedder.py\nbge-small-en-v1.5"]
        MIGRATE["migrate.py\nmigration runner"]
    end

    subgraph Modules ["src/modules/"]
        PLANNER["planner.py\nPlannerSession\nmonthly, weekly, daily, evening"]
    end

    subgraph Storage ["Storage"]
        CHROMA[("ChromaDB\nvector store")]
        SQLITE[("SQLite\nplans, tasks, chats, _migrations")]
        LOGS["data/logs/app.log"]
        SQLFILES["data/migrations/*.sql"]
    end

    subgraph Knowledge ["Knowledge"]
        JSON["data/raw/*.json\nknowledge files"]
    end

    U -->|sends message| TG
    TG -->|polling| BOT
    BOT -->|/daily /weekly etc| ROUTER
    ROUTER -->|new PlannerSession| PLANNER
    ROUTER -->|/ask| RAG

    UB -->|HTTP localhost:8000| WEB
    WEB -->|POST /api/start, /api/reply| WSESS
    WSESS --> PLANNER
    WEB -->|POST /api/chat| LLM
    WEB -->|POST /api/ask| RAG
    WEB -->|POST /api/gendb| MIGRATE

    PLANNER -->|chat + history| LLM
    LLM -->|answer| PLANNER
    PLANNER --> SQLITE

    RAG --> EMB
    EMB --> CHROMA
    CHROMA -->|top-k chunks| RAG
    RAG --> LLM

    SQLFILES --> MIGRATE
    MIGRATE --> SQLITE

    JSON -->|python311 main.py ingest| INGEST
    INGEST --> EMB
    INGEST --> SQLITE

    BOT -.-> LOGS
    WEB -.-> LOGS
    LLM -.-> LOGS
    MIGRATE -.-> LOGS
    INGEST -.-> LOGS
```

## Entry points

| Command | What starts |
|---|---|
| `python311 main.py` | Both Telegram bot + Web UI (default) |
| `python311 main.py both` | Same as above |
| `python311 main.py bot` | Telegram bot only |
| `python311 main.py web` | Web UI only (`http://localhost:8000`) |
| `python311 main.py ingest` | Index JSON files into ChromaDB |
| `python311 main.py migrate` | Apply pending SQL migrations |
| `python311 main.py ask "..."` | One-shot RAG query (CLI) |

## Web UI sections

| Sidebar | Endpoint | What it does |
|---|---|---|
| 📅 Daily / 🌙 Evening / 📆 Weekly / 🗓 Monthly | `POST /api/start` then `POST /api/reply` | Planning coach session |
| 📊 Status | `GET /api/status` | Week progress summary |
| 💬 Free Chat | `POST /api/chat` | Direct DeepSeek, history stored in SQLite |
| 🔍 Ask Knowledge | `POST /api/ask` | RAG over indexed JSON files |
| 🗄 Run GenDB | `POST /api/gendb` | Apply pending migrations |
| 🗺 System Flow | — | Renders this diagram in the browser |

Render at [mermaid.live](https://mermaid.live) or with the VS Code Mermaid extension.

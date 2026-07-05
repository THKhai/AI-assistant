import sys
from src.core.logger import get_logger
from src.core.db import init_db

log = get_logger("main")


def _validate_config():
    from src.core import config
    errors = []
    if not config.JWT_SECRET:
        errors.append("JWT_SECRET is not set — generate one: python311 -c \"import secrets; print(secrets.token_hex(32))\"")
    if len(config.JWT_SECRET) < 32:
        errors.append("JWT_SECRET is too short — minimum 32 characters")
    if not config.DEEPSEEK_API_KEY:
        log.warning("DEEPSEEK_API_KEY is not set — LLM features will fail")
    if errors:
        for e in errors:
            log.error(f"Config error: {e}")
        sys.exit(1)


def run_bot():
    from src.bot.handler import build_app
    log.info("starting Telegram bot (polling mode)")
    app = build_app()
    app.run_polling(drop_pending_updates=True)


def run_web():
    import uvicorn
    from src.core.config import HTTPS_CERT_FILE, HTTPS_KEY_FILE
    ssl_kwargs = {}
    if HTTPS_CERT_FILE and HTTPS_KEY_FILE:
        ssl_kwargs = {"ssl_certfile": HTTPS_CERT_FILE, "ssl_keyfile": HTTPS_KEY_FILE}
        log.info("starting web UI at https://0.0.0.0:8000 (TLS enabled)")
    else:
        log.info("starting web UI at http://0.0.0.0:8000")
    from src.web.app import app
    uvicorn.run(app, host="0.0.0.0", port=8000, **ssl_kwargs)


def run_ingest():
    from src.core.ingest import ingest_directory
    results = ingest_directory()
    print(f"Indexed: {results['indexed']}  Skipped: {results['skipped']}")
    if results["errors"]:
        print("Errors:")
        for e in results["errors"]:
            print(f"  {e}")


def run_ask(question: str):
    from src.core.query import ask
    result = ask(question)
    print(result["answer"])
    if result["sources"]:
        print(f"\nSources: {', '.join(result['sources'])}")


def run_both():
    import threading
    log.info("starting Telegram bot + web UI in parallel")
    bot_thread = threading.Thread(target=run_bot, daemon=True, name="telegram-bot")
    bot_thread.start()
    run_web()  # blocks main thread; bot thread dies when web exits


def run_migrate():
    from src.core.migrate import run
    count = run()
    print(f"Migrations applied: {count}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "both"

    if cmd == "migrate":
        run_migrate()
    elif cmd in ("bot", "web", "both", "ingest", "ask"):
        _validate_config()
        init_db()
        if cmd == "bot":
            run_bot()
        elif cmd == "web":
            run_web()
        elif cmd == "both":
            run_both()
        elif cmd == "ingest":
            run_ingest()
        elif cmd == "ask" and len(sys.argv) > 2:
            run_ask(" ".join(sys.argv[2:]))
    else:
        print("Usage:")
        print("  python main.py both         — start Telegram bot + web UI together (default)")
        print("  python main.py bot          — start Telegram bot only")
        print("  python main.py web          — start web UI only  (http://localhost:8000)")
        print("  python main.py ingest       — index all JSON files in data/raw/")
        print('  python main.py ask "..."    — ask a question (CLI mode)')
        print("  python main.py migrate      — apply pending DB migrations")

import sys
import logging
from src.core.db import init_db

log = logging.getLogger(__name__)


def run_bot():
    from src.bot.handler import build_app
    log.info("Starting Telegram bot (polling mode)...")
    app = build_app()
    app.run_polling(drop_pending_updates=True)


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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    init_db()

    cmd = sys.argv[1] if len(sys.argv) > 1 else "bot"

    if cmd == "bot":
        run_bot()
    elif cmd == "ingest":
        run_ingest()
    elif cmd == "ask" and len(sys.argv) > 2:
        run_ask(" ".join(sys.argv[2:]))
    else:
        print("Usage:")
        print("  python main.py bot          — start Telegram bot")
        print("  python main.py ingest       — index all JSON files in data/raw/")
        print('  python main.py ask "..."    — ask a question (CLI mode)')

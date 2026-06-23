import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

from src.core import config
from src.bot import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def _guard(update: Update) -> bool:
    uid = update.effective_user.id
    if uid != config.ALLOWED_USER_ID:
        log.warning(f"Blocked unauthorized user {uid}")
        return False
    return True


async def cmd_daily(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _guard(update):
        return
    msg = router.start_planner_session(update.effective_user.id, "daily")
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_evening(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _guard(update):
        return
    msg = router.start_planner_session(update.effective_user.id, "evening")
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_weekly(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _guard(update):
        return
    msg = router.start_planner_session(update.effective_user.id, "weekly")
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_monthly(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _guard(update):
        return
    msg = router.start_planner_session(update.effective_user.id, "monthly")
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _guard(update):
        return
    msg = router.handle_status()
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _guard(update):
        return
    router.end_session(update.effective_user.id)
    await update.message.reply_text("Session ended. Use a command to start a new one.")


async def cmd_ask(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _guard(update):
        return
    question = " ".join(ctx.args)
    if not question:
        await update.message.reply_text("Usage: /ask <your question>")
        return
    await update.message.reply_text("Searching...", parse_mode="Markdown")
    msg = router.handle_ask(question, update.effective_user.id)
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_ingest(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _guard(update):
        return
    await update.message.reply_text("Indexing files...")
    msg = router.handle_ingest()
    await update.message.reply_text(msg, parse_mode="Markdown")


async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _guard(update):
        return
    text = update.message.text or ""
    msg = router.handle_message(update.effective_user.id, text)
    await update.message.reply_text(msg, parse_mode="Markdown")


def build_app():
    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("evening", cmd_evening))
    app.add_handler(CommandHandler("weekly", cmd_weekly))
    app.add_handler(CommandHandler("monthly", cmd_monthly))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler("ask", cmd_ask))
    app.add_handler(CommandHandler("ingest", cmd_ingest))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    return app

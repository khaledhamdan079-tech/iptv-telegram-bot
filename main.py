"""IPTV Telegram Bot entry point."""

import logging
import sys
from telegram import Update
from telegram.error import Conflict
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from handlers import start, cancel, handle_text

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def _on_error(update: object, context: object) -> None:
    """Log and exit on Conflict so only one bot instance runs."""
    import traceback
    exc = getattr(context, "error", None)
    if isinstance(exc, Conflict):
        logger.critical(
            "Conflict: Another instance of this bot is already running (e.g. local and Railway). "
            "Stop all other instances and use only one."
        )
        sys.exit(1)
    logger.error("Exception while handling an update: %s", exc)
    traceback.print_exc()


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in environment or .env")

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(_on_error)

    logger.info("Bot running (polling)")
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Conflict:
        logger.critical(
            "Conflict: Only one instance of this bot can run at a time. "
            "Stop the other instance (e.g. local or another deployment) and try again."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()

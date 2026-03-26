#!/usr/bin/env python3
"""Telegram bot entry point with --test mode for offline verification.

Usage:
    uv run bot.py --test "/start"    # Test mode - prints response to stdout
    uv run bot.py                    # Normal mode - connects to Telegram
"""

import asyncio
import sys
from pathlib import Path

# Add bot directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from handlers import (
    get_inline_keyboard,
    handle_help,
    handle_health,
    handle_labs,
    handle_natural_language,
    handle_scores,
    handle_start,
)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import load_config

# Command router - maps command strings to handler functions
COMMAND_HANDLERS = {
    "/start": handle_start,
    "/help": handle_help,
    "/health": handle_health,
    "/labs": handle_labs,
    "/scores": handle_scores,
}


def route_command(command: str) -> str:
    """Route a command string to the appropriate handler.

    Args:
        command: The command string (e.g., "/start" or "/scores lab-04")

    Returns:
        The handler's response string
    """
    parts = command.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if cmd in COMMAND_HANDLERS:
        return COMMAND_HANDLERS[cmd](args)
    else:
        return f"Unknown command: {cmd}. Use /help to see available commands."


def run_test_mode(command: str) -> None:
    """Run the bot in test mode - print response and exit.

    Args:
        command: The command to test (e.g., "/start" or "what labs are available")
    """
    # Check if it's a slash command or natural language
    if command.strip().startswith("/"):
        response = route_command(command)
    else:
        # Natural language query - use LLM intent router
        response = handle_natural_language(command)
    print(response)
    sys.exit(0)


async def handle_telegram_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    command: str,
) -> None:
    """Handle a Telegram command."""
    args = " ".join(context.args) if context.args else ""
    full_command = f"{command} {args}".strip()
    response = route_command(full_command)
    await update.message.reply_text(response)


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start command."""
    args = " ".join(context.args) if context.args else ""
    response = handle_start(args)
    
    # Create inline keyboard
    keyboard_data = get_inline_keyboard()
    keyboard = [
        [InlineKeyboardButton(btn["text"], callback_data=btn["callback_data"]) for btn in row]
        for row in keyboard_data
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(response, reply_markup=reply_markup)


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /help command."""
    await handle_telegram_command(update, context, "/help")


async def health_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /health command."""
    await handle_telegram_command(update, context, "/health")


async def labs_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /labs command."""
    await handle_telegram_command(update, context, "/labs")


async def scores_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /scores command."""
    await handle_telegram_command(update, context, "/scores")


async def handle_text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle plain text messages using LLM intent routing."""
    text = update.message.text
    # Send typing action while processing
    await update.message.chat.send_action(action="typing")
    response = handle_natural_language(text)
    await update.message.reply_text(response)


async def handle_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle inline keyboard button callbacks."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "cmd_labs":
        response = handle_labs("")
    elif callback_data == "cmd_scores":
        response = "Please specify a lab, e.g., /scores lab-04"
    elif callback_data == "cmd_top":
        response = handle_natural_language("Who are the top 5 students in lab 04?")
    elif callback_data == "cmd_completion":
        response = handle_natural_language("What is the completion rate for lab 04?")
    else:
        response = "Unknown action."
    
    await query.edit_message_text(response)


def run_telegram_mode() -> None:
    """Run the bot in Telegram mode - connect to Telegram API."""
    config = load_config()

    if not config.bot_token:
        print("Error: BOT_TOKEN not found in .env.bot.secret")
        sys.exit(1)

    # Build application
    application = Application.builder().token(config.bot_token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("health", health_command))
    application.add_handler(CommandHandler("labs", labs_command))
    application.add_handler(CommandHandler("scores", scores_command))

    # Add text message handler for non-command messages (LLM routing)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Add callback query handler for inline keyboard
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Start the bot using asyncio.run() for Python 3.14 compatibility
    print("Starting bot...")

    async def run_bot() -> None:
        """Run the bot polling."""
        async with application:
            await application.start()
            await application.updater.start_polling()
            # Keep running until stopped
            while True:
                await asyncio.sleep(1)

    asyncio.run(run_bot())


def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        if len(sys.argv) < 3:
            print("Usage: uv run bot.py --test \"/command [args]\"")
            sys.exit(1)
        command = " ".join(sys.argv[2:])
        run_test_mode(command)
    else:
        run_telegram_mode()


if __name__ == "__main__":
    main()

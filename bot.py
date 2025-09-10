import logging
import os
import sys
import subprocess
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telethon import TelegramClient
from telethon.sessions import StringSession

# Credentials
BOT_TOKEN = "8230628522:AAGWLsfQsLZ1DhXpktGgWk7zQwPBYgdPBt8"
api_id = 28606113
api_hash = "2eb35c593e9f213f26d0afb4472396d4"

logging.basicConfig(level=logging.INFO)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to RavenScrap Bot!\n\n"
        "Use /login to authorize your Telegram account (once).\n"
        "Then run /scrap @group_or_id [amount] [bin] [country] [keyword]"
    )


async def login_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔐 Logging in, please wait...")
    try:
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.start()
        session_str = client.session.save()
        await client.disconnect()
        with open("session.txt", "w") as f:
            f.write(session_str)
        await update.message.reply_text("✅ Login successful. Session string saved.")
        logging.info("Session string saved.")
    except Exception as e:
        await update.message.reply_text(f"❌ Login failed: {e}")
        logging.error(f"Login failed: {e}")


async def scrap_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /scrap @group_or_id [amount] [bin] [country] [keyword]")
        return

    args_str = ' '.join(context.args)
    await update.message.reply_text(f"🟡 Starting scraping with: {args_str}")
    logging.info(f"Scraping triggered with args: {args_str}")

    try:
        # ✅ use sys.executable to ensure correct Python path
        subprocess.run([sys.executable, "scraper.py"] + context.args, timeout=900)

        # Check if scraper signaled no results
        if os.path.exists("no_valid_codes.signal"):
            await update.message.reply_text("❌ No valid codes found.")
            os.remove("no_valid_codes.signal")
            return

        # Look for output files
        from glob import glob
        files = sorted(glob("Scrap By Raven - *.txt"), key=os.path.getmtime, reverse=True)

        if files:
            filepath = files[0]
            if os.path.getsize(filepath) == 0:
                await update.message.reply_text("❌ Output file is empty.")
                return

            try:
                with open(filepath, "rb") as doc:
                    await update.message.reply_document(
                        document=doc,
                        filename=os.path.basename(filepath),
                        caption="📂 Scraping results",
                        parse_mode=ParseMode.HTML
                    )
            except Exception as e:
                await update.message.reply_text(f"❌ Failed to send file: {e}")
                logging.error(f"Failed to send file {filepath}: {e}")
        else:
            await update.message.reply_text("❌ No output file found.")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("❌ Scraping timed out.")
        logging.warning("Scraper timed out.")
    except Exception as e:
        await update.message.reply_text(f"❌ Unexpected error: {e}")
        logging.error(f"Unexpected error in scrap_handler: {e}")


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", start_handler))
    app.add_handler(CommandHandler("login", login_handler))
    app.add_handler(CommandHandler("scrap", scrap_handler))
    logging.info("Bot is running...")
    app.run_polling()

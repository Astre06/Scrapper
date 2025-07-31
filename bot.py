import logging
import os
import subprocess
from glob import glob
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telethon import TelegramClient
from telethon.sessions import StringSession

# Setup logging to Render logs
logging.basicConfig(level=logging.INFO)

# Load credentials from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

async def login_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Received /login command.")
    await update.message.reply_text("Starting login. Please wait...")

    try:
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.start()
        session_str = client.session.save()
        with open("tg_cli_scraper.session", "w") as f:
            f.write(session_str)
        await client.disconnect()
        await update.message.reply_text("✅ Login complete and session saved.")
        logging.info("Session saved successfully.")
    except Exception as e:
        logging.error(f"Login failed: {e}")
        await update.message.reply_text(f"❌ Login failed: {e}")

async def scrap_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Received /scrap command.")
    if not context.args:
        await update.message.reply_text("Usage: /scrap @group [amount] [bin] [country]")
        return

    args_str = ' '.join(context.args)
    await update.message.reply_text(f"🟡 Starting scraping with: {args_str}")
    cmd = ["python", "scraper.py"] + context.args

    try:
        subprocess.run(cmd, timeout=900)
        if os.path.exists("no_valid_codes.signal"):
            await update.message.reply_text("❌ No valid codes found.")
            os.remove("no_valid_codes.signal")
            return

        files = sorted(
            glob("Scrap By Raven - *.txt"), key=os.path.getmtime, reverse=True
        )
        if files:
            await update.message.reply_document(document=open(files[0], "rb"))
            logging.info(f"Sent file: {files[0]}")
        else:
            await update.message.reply_text("❌ No output file found.")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("❌ Scraping timed out.")
        logging.warning("Scraping process timed out.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("login", login_handler))
    app.add_handler(CommandHandler("scrap", scrap_handler))
    logging.info("Bot is starting...")
    app.run_polling()

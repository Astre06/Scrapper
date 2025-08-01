import logging
import os
import subprocess
import time
from glob import glob
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telethon import TelegramClient
from telethon.sessions import StringSession

# Load from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

# In-memory user rate-limiting (optional)
user_last_scrap_time = {}

# Logging
logging.basicConfig(level=logging.INFO)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to RavenScrap Bot!\n\n"
        "Usage:\n"
        "/scrap @group [amount] [bin] [country] [keyword]\n"
        "Example:\n"
        "`/scrap @group 10 5302 US netflix`",
        parse_mode="Markdown"
    )


async def login_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Starting login. Please wait...")
    try:
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.start()
        session_str = client.session.save()
        with open("tg_cli_scraper.session", "w") as f:
            f.write(session_str)
        await client.disconnect()
        await update.message.reply_text("✅ Login complete and session saved.")
        logging.info(f"Login success by user {update.effective_user.id}")
    except Exception as e:
        logging.error(f"Login failed: {e}")
        await update.message.reply_text(f"❌ Login failed: {e}")


async def scrap_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Optional: rate-limiting
    now = time.time()
    if user_id in user_last_scrap_time and now - user_last_scrap_time[user_id] < 60:
        await update.message.reply_text("⏳ Please wait before using /scrap again.")
        return
    user_last_scrap_time[user_id] = now

    if not context.args:
        await update.message.reply_text("Usage: /scrap @group [amount] [bin] [country] [keyword]")
        return

    args_str = ' '.join(context.args)
    await update.message.reply_text(f"🟡 Starting scraping with: {args_str}")
    logging.info(f"Scraping triggered by {user_id} with args: {args_str}")

    try:
        subprocess.run(["python", "scraper.py"] + context.args, timeout=900)
        if os.path.exists("no_valid_codes.signal"):
            await update.message.reply_text("❌ No valid codes found.")
            os.remove("no_valid_codes.signal")
            return

        files = sorted(glob("Scrap By Raven - *.txt"), key=os.path.getmtime, reverse=True)
        if files:
            await update.message.reply_document(document=open(files[0], "rb"))
            logging.info(f"Sent file to {user_id}: {files[0]}")
        else:
            await update.message.reply_text("❌ No output file found.")
            logging.warning("No output file created.")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("❌ Scraping timed out.")
        logging.warning("Scraping timed out.")


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", start_handler))
    app.add_handler(CommandHandler("login", login_handler))
    app.add_handler(CommandHandler("scrap", scrap_handler))
    logging.info("Ravenscrap bot started...")
    app.run_polling()

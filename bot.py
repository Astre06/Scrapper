import logging
import os
import subprocess
from glob import glob
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telethon import TelegramClient
from telethon.sessions import StringSession

# Load from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID"))  # Set your Telegram user ID in Render

# Enable logging to Render
logging.basicConfig(level=logging.INFO)


async def login_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        logging.warning(f"Unauthorized /login attempt by {update.effective_user.id}")
        return

    await update.message.reply_text("Starting login. Please wait...")
    try:
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.start()
        session_str = client.session.save()
        with open("tg_cli_scraper.session", "w") as f:
            f.write(session_str)
        await client.disconnect()
        await update.message.reply_text("✅ Login complete and session saved.")
        logging.info("Telegram session created successfully.")
    except Exception as e:
        logging.error(f"Login failed: {e}")
        await update.message.reply_text(f"❌ Login failed: {e}")


async def scrap_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != BOT_OWNER_ID:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        logging.warning(f"Unauthorized /scrap attempt by {update.effective_user.id}")
        return

    if not context.args:
        await update.message.reply_text("Usage: /scrap @group [amount] [bin] [country] [keyword]")
        return

    args_str = ' '.join(context.args)
    await update.message.reply_text(f"🟡 Starting scraping with: {args_str}")
    logging.info(f"Running scraper with: {args_str}")

    try:
        subprocess.run(["python", "scraper.py"] + context.args, timeout=900)
        if os.path.exists("no_valid_codes.signal"):
            await update.message.reply_text("❌ No valid codes found.")
            os.remove("no_valid_codes.signal")
            return

        files = sorted(glob("Scrap By Raven - *.txt"), key=os.path.getmtime, reverse=True)
        if files:
            await update.message.reply_document(document=open(files[0], "rb"))
            logging.info(f"Sent scraped file: {files[0]}")
        else:
            await update.message.reply_text("❌ No output file found.")
            logging.warning("Scraper finished but no output file created.")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("❌ Scraping timed out.")
        logging.warning("Scraper timed out.")


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("login", login_handler))
    app.add_handler(CommandHandler("scrap", scrap_handler))
    logging.info("Ravenscrap bot started and polling...")
    app.run_polling()

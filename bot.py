import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import subprocess
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os
from glob import glob

BOT_TOKEN = "7864344868:AAFeK9th61ps_7Mc01ttE-4CSQE2DjYPE50"
api_id = 28606113
api_hash = "2eb35c593e9f213f26d0afb4472396d4"

logging.basicConfig(level=logging.INFO)


async def login_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Starting login. Please wait...")
    try:
        with TelegramClient(StringSession(), api_id, api_hash) as client:
            client.start()
            session_str = client.session.save()
            with open("tg_cli_scraper.session", "w") as f:
                f.write(session_str)
        await update.message.reply_text("✅ Login complete and session saved.")
    except Exception as e:
        await update.message.reply_text(f"❌ Login failed: {e}")


async def scrap_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /scrap @group [amount] [bin] [country]")
        return

    cmd = ["python", "scraper.py"] + context.args
    await update.message.reply_text(
        f"🟡 Starting scraping with: {' '.join(context.args)}"
    )

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
        else:
            await update.message.reply_text("❌ No output file found.")
    except subprocess.TimeoutExpired:
        await update.message.reply_text("❌ Scraping timed out.")


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("login", login_handler))
    app.add_handler(CommandHandler("scrap", scrap_handler))
    app.run_polling()

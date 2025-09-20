import re
import sys
import asyncio
import aiohttp
import logging
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

api_id = 28606113
api_hash = "2eb35c593e9f213f26d0afb4472396d4"

code_regex = re.compile(r"\b(\d{16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})\b")

bin_country_cache = {}
found_codes = set()

target_group = None
code_limit = None
bin_prefix = None
country_filter = None
message_filter = None

logging.basicConfig(level=logging.INFO)

def parse_args():
    global target_group, code_limit, bin_prefix, country_filter, message_filter
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if len(args) < 1:
        logging.error("Usage: scraper.py @group_or_id [amount] [bin_prefix] [country] [keyword]")
        sys.exit(1)
    first_arg = args[0]
    if first_arg.startswith("-100"):
        try:
            target_group = int(first_arg)
        except ValueError:
            logging.error("Invalid group ID format.")
            sys.exit(1)
    else:
        target_group = first_arg.lstrip("@")
    for arg in args[1:]:
        if arg.isdigit() and len(arg) == 6:
            bin_prefix = arg
        elif arg.isdigit() and code_limit is None:
            code_limit = int(arg)
        elif len(arg) in (2,3) and arg.isalpha():
            country_filter = arg.upper()
        else:
            message_filter = arg.lower()

async def check_bin_country(bin6):
    if bin6 in bin_country_cache:
        return bin_country_cache[bin6]
    url = f"https://bincheck.io/details/{bin6}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                text = await resp.text()
                match = re.search(r"ISO Country Code A2.*?>([A-Z]{2})<", text, re.DOTALL)
                if match:
                    country = match.group(1)
                    bin_country_cache[bin6] = country
                    return country
    except Exception as e:
        logging.warning(f"BIN country lookup failed for {bin6}: {e}")
    return None

async def main():
    parse_args()
    logging.info(f"Starting scraping for group: {target_group}")
    
    client = TelegramClient("tg_cli_scraper", api_id, api_hash)
    await client.start()
    logging.info("Telegram client started")
    
    output_filename = f"Scrap By Raven - {target_group}"
    if country_filter:
        output_filename += f" - {country_filter}"
    if code_limit:
        output_filename += f" - Limit {code_limit}"
    output_filename += ".txt"
    
    found_card_count = 0
    
    with open(output_filename, "w", encoding="utf-8") as outfile:
        async for message in client.iter_messages(target_group):  # no limit to scan all messages
            if not message.text:
                continue
            text = message.text.lower()
            if message_filter:
                filters = [f.strip().lower() for f in message_filter.split(",")]
                if not any(f in text for f in filters):
                    continue
            cards = code_regex.findall(message.text)
            for card in cards:
                card_number, mm, yy, cvv = card
                if bin_prefix and not card_number.startswith(bin_prefix):
                    continue
                if country_filter:
                    bin6 = card_number[:6]
                    country = await check_bin_country(bin6)
                    if country != country_filter:
                        continue
                card_line = f"{card_number}|{mm}|{yy}|{cvv}"
                if card_line not in found_codes:
                    found_codes.add(card_line)
                    logging.info(f"Found card: {card_line}")
                    outfile.write(card_line + "\n")
                    found_card_count += 1
                    if code_limit and found_card_count >= code_limit:
                        break
            if code_limit and found_card_count >= code_limit:
                break

    await client.disconnect()

    if found_card_count == 0:
        with open("no_valid_codes.signal", "w") as f:
            f.write("")

    logging.info(f"Scraping complete. Found {found_card_count} cards. Results saved in {output_filename}")

if __name__ == "__main__":
    asyncio.run(main())

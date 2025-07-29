import re
import os
import sys
import asyncio
import aiohttp
from telethon import TelegramClient

api_id = 28606113
api_hash = "2eb35c593e9f213f26d0afb4472396d4"
session_name = "tg_cli_scraper"

code_regex = re.compile(r"\b(\d{16})\|(\d{2})\|(\d{2})\|(\d{3,4})\b")
bin_country_cache = {}

OUTPUT_FILE = None
target_group = ""
code_limit = None
bin_prefix = None
country_filter = None
message_filter = None
found_codes = set()

def get_output_filename(count):
    suffix = f" - {country_filter.upper()}" if country_filter else ""
    return f"Scrap By Raven - {count}{suffix}.txt"

def parse_args():
    global target_group, code_limit, bin_prefix, country_filter, message_filter
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    if len(args) < 1 or args[0].lower() == "all":
        print("Usage: /scrap @group [amount] [bin_prefix] [country] [keyword]")
        sys.exit(1)

    target_group = args[0].lstrip("@")

    for arg in args[1:]:
        if arg.isdigit():
            if not code_limit:
                code_limit = int(arg)
            else:
                bin_prefix = arg
        elif len(arg) in (2, 3) and arg.isalpha():
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
                html = await resp.text()
                match = re.search(
                    r"ISO Country Code A2.*?<td[^>]*>([A-Z]{2})</td>", html, re.DOTALL
                )
                if match:
                    code = match.group(1).upper()
                    bin_country_cache[bin6] = code
                    return code
    except:
        pass
    bin_country_cache[bin6] = None
    return None

async def run_scraper():
    global OUTPUT_FILE
    parse_args()

    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        print("❗ Telegram login required. Use /login in your bot chat.")
        return

    entity = await client.get_entity(target_group)
    collected = []

    async for message in client.iter_messages(entity, limit=None):
        if not message.message:
            continue

        if message_filter and message_filter not in message.message:
            continue

        clean = (
            message.message.replace("｜", "|")
            .replace("‖", "|")
            .replace(" ", "")
            .replace("​", "")
        )
        matches = code_regex.findall(clean)
        for match in matches:
            full = "|".join(match)
            if full in found_codes:
                continue
            if bin_prefix and not match[0].startswith(bin_prefix[: len(bin_prefix)]):
                continue
            if country_filter:
                bin6 = match[0][:6]
                country = await check_bin_country(bin6)
                if not country or country_filter.upper() not in country.upper():
                    continue
            found_codes.add(full)
            collected.append(full)
            print("[+] " + full)
            if code_limit and len(collected) >= code_limit:
                break

    if collected:
        OUTPUT_FILE = get_output_filename(len(collected))
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            for c in collected:
                f.write(c + "\n")
        print(f"✅ Saved {len(collected)} codes to {OUTPUT_FILE}")
    else:
        open("no_valid_codes.signal", "w").close()
        print("❌ No valid codes found.")

if __name__ == "__main__":
    asyncio.run(run_scraper())

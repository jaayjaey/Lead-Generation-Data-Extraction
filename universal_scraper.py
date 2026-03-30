"""
Finelib.com Scraper v5.1 — Visible Browser Edition
==================================================
Run this from the command line and pass the state name:
    python universal_scraper.py Abia
"""

import argparse
import asyncio
import csv
import os
import re
import random
import urllib.parse
from urllib.parse import urljoin
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# ── SETUP DYNAMIC CONFIGURATION ───────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Scrape Finelib for a specific state.")
parser.add_argument("state", nargs="+", help="The state to scrape (e.g., Lagos, Kano, Akwa Ibom)")
args = parser.parse_args()

STATE_NAME = " ".join(args.state).title()
STATE_URL_ENCODED = urllib.parse.quote(STATE_NAME)
STATE_FILE_FORMAT = STATE_NAME.lower().replace(" ", "_")

BASE_URL   = "https://www.finelib.com"
SEARCH_URL = f"https://www.finelib.com/search.php?q={STATE_URL_ENCODED}&start={{start}}"
PAGE_SIZE  = 15

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, f"finelib_{STATE_FILE_FORMAT}_businesses.csv")
LINKS_FILE  = os.path.join(SCRIPT_DIR, f"finelib_{STATE_FILE_FORMAT}_links.txt")

FIELDNAMES  = ["name", "address", "phone", "website", "url"]
# ─────────────────────────────────────────────────────────────────────────────

async def collect_links(page):
    if os.path.exists(LINKS_FILE):
        links = []
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("|", 1)
                if len(parts) == 2:
                    links.append((parts[0], parts[1]))
        print(f"[Links] Loaded {len(links)} links from previous run.\n")
        return links

    all_links = []
    seen_urls = set()
    start     = 0
    page_num  = 1

    while True:
        url = SEARCH_URL.format(start=start)
        print(f"[Page {page_num}] {url}")
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)

            anchors = await page.query_selector_all("a[href*='/listing/']")
            
            if not anchors:
                print(f"    [INFO] No more listings found on page {page_num}. Ending collection.")
                break

            for a in anchors:
                name = (await a.inner_text()).strip()
                href = await a.get_attribute("href")
                if not href:
                    continue
                
                full_url = urljoin(BASE_URL, href)
                
                if name and full_url not in seen_urls:
                    seen_urls.add(full_url)
                    all_links.append((name, full_url))

            print(f"    → {len(all_links)} collected so far")
        except Exception as e:
            print(f"    [WARN] Page {page_num} failed: {e}")
            break 

        start    += PAGE_SIZE
        page_num += 1
        
        await asyncio.sleep(random.uniform(1.0, 2.5))

    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        for name, url in all_links:
            f.write(f"{name}|{url}\n")
    print(f"\n[Links] Saved {len(all_links)} links → {LINKS_FILE}\n")
    return all_links

async def extract_details(page, name, url):
    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)
    except PlaywrightTimeout:
        return {"name": name, "address": "N/A", "phone": "N/A", "website": "N/A", "url": url}
    except Exception as e:
        return {"name": name, "address": "N/A", "phone": "N/A", "website": "N/A", "url": url}

    body_text = await page.inner_text("body")
    lines     = [l.strip() for l in body_text.splitlines() if l.strip()]

    # Address Extraction
    address = ""
    try:
        addr_el = await page.query_selector("[itemprop='address'], .address, .listing-address")
        if addr_el:
            address = (await addr_el.inner_text()).strip()
    except Exception:
        pass

    if not address:
        addr_re = re.compile(
            r"\b(street|road|avenue|ave|close|crescent|drive|way|lane|plaza|"
            r"estate|layout|junction|bypass|expressway|GRA|floor|house|"
            r"building|no\.|plot|kilometre|km\b|off\b|beside|opposite|behind|"
            r"along|after|before)\b",
            re.IGNORECASE,
        )
        for line in lines:
            if addr_re.search(line) and 8 < len(line) < 250:
                if any(skip in line.lower() for skip in ["add your", "edit your", "terms of", "privacy", "follow us", "contact us", "about us"]):
                    continue
                address = line
                break

    # Phone Extraction
    phone = ""
    try:
        phone_el = await page.query_selector("[itemprop='telephone'], .phone, .listing-phone, a[href^='tel:']")
        if phone_el:
            phone = (await phone_el.inner_text()).strip()
            if not phone:
                phone = (await phone_el.get_attribute("href") or "").replace("tel:", "").strip()
    except Exception:
        pass

    if not phone:
        phone_re = re.compile(
            r"(\+?234[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{4}"
            r"|0[789][01]\d{8}"
            r"|0\d{2,4}[\s\-]?\d{3}[\s\-]?\d{3,5})"
        )
        m = phone_re.search(body_text)
        if m:
            phone = m.group(0).strip()

    # Website Extraction
    website = ""
    try:
        web_el = await page.query_selector("[itemprop='url'], a[href^='http']:not([href*='finelib'])")
        if web_el:
            website = (await web_el.get_attribute("href") or "").strip()
    except Exception:
        pass

    if not website:
        url_re = re.compile(r"https?://(?!www\.finelib\.com)[^\s\"'<>]+")
        m = url_re.search(body_text)
        if m:
            website = m.group(0).strip()

    return {
        "name":    name,
        "address": address or "N/A",
        "phone":   phone   or "N/A",
        "website": website or "N/A",
        "url":     url,
    }

def get_done_urls():
    done = set()
    if os.path.exists(OUTPUT_FILE) and os.path.getsize(OUTPUT_FILE) > 0:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                done.add(row.get("url", "").strip())
    return done

async def main():
    print("=" * 70)
    print(f"  Finelib Scraper v5.1 — VISIBLE BROWSER: {STATE_NAME.upper()}")
    print(f"  Output → {OUTPUT_FILE}")
    print("=" * 70 + "\n")

    async with async_playwright() as p:
        # HERE IS THE CHANGE: headless=False opens the actual Chrome window
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        all_links = await collect_links(page)
        print(f"Total unique listings found: {len(all_links)}\n")

        done_urls = get_done_urls()
        remaining = [(n, u) for n, u in all_links if u not in done_urls]
        total_done = len(done_urls)

        if done_urls:
            print(f"Resuming — {total_done} already done, {len(remaining)} to go.\n")

        file_is_new = not os.path.exists(OUTPUT_FILE) or os.path.getsize(OUTPUT_FILE) == 0
        csv_file = open(OUTPUT_FILE, "a", newline="", encoding="utf-8")
        writer   = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        if file_is_new:
            writer.writeheader()
            csv_file.flush()

        grand_total = len(all_links)

        for i, (name, url) in enumerate(remaining, start=total_done + 1):
            print(f"[{i}/{grand_total}] {name[:65]}")
            details = await extract_details(page, name, url)
            print(f"    Address : {details['address'][:70]}")
            print(f"    Phone   : {details['phone']}")
            print(f"    Website : {details['website'][:60]}")

            writer.writerow(details)
            csv_file.flush()
            os.fsync(csv_file.fileno())

            delay = random.uniform(2.0, 4.0)
            await asyncio.sleep(delay)

        csv_file.close()
        await browser.close()

    print(f"\n✅ Complete! {grand_total} businesses saved to:")
    print(f"   {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
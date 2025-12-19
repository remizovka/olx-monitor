send_telegram("Тест. GitHub Actions работает.")

import os
import sqlite3
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

SEARCH_URL = os.getenv("SEARCH_URL")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")

BASE_URL = "https://www.olx.kz"
DB_FILE = "sent.db"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/141.0.0.0 Safari/537.36"
}

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sent (
            id TEXT PRIMARY KEY,
            url TEXT,
            ts INTEGER
        )
    """)
    conn.commit()
    return conn

def is_sent(conn, ad_id):
    cur = conn.execute("SELECT 1 FROM sent WHERE id=?", (ad_id,))
    return cur.fetchone() is not None

def mark_sent(conn, ad_id, url):
    conn.execute(
        "INSERT OR IGNORE INTO sent (id, url, ts) VALUES (?, ?, strftime('%s','now'))",
        (ad_id, url)
    )
    conn.commit()

def send_to_tg(text):
    requests.post(
        f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
        json={
            "chat_id": TG_CHANNEL_ID,
            "text": text,
            "disable_web_page_preview": True
        },
        timeout=10
    )

def get_today_ads():
    r = requests.get(SEARCH_URL, headers=HEADERS, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    ads = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/obyavlenie/" not in href or "ID" not in href:
            continue

        url = urljoin(BASE_URL, href)
        ad_id = url.split("ID")[-1].split(".")[0]

        # ищем метку "Сегодня"
        parent_text = a.parent.get_text(" ", strip=True).lower()
        if "сегодня" not in parent_text:
            continue

        ads.append((ad_id, url))

    return ads

def main():
    conn = init_db()
    ads = get_today_ads()

    new_links = []
    for ad_id, url in ads:
        if not is_sent(conn, ad_id):
            new_links.append(url)
            mark_sent(conn, ad_id, url)

    if new_links:
        msg = "🆕 Новые объявления за сегодня:\n\n" + "\n".join(new_links)
        send_to_tg(msg)

    conn.close()

if __name__ == "__main__":
    main()

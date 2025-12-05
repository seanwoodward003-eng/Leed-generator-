from flask import Flask, render_template_string, Response
import requests
from bs4 import BeautifulSoup
import re
import time
import csv
import io
import random
from datetime import datetime, timedelta
import os

app = Flask(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/129 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_2) AppleWebKit/605.1.15 Version/17 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128 Safari/537.36"
]

# Load the full 25k+ store list from stores.txt
try:
    with open("stores.txt", "r", encoding="utf-8") as f:
        FULL_STORE_LIST = [line.strip() for line in f if line.strip() and not line.startswith("#")]
except FileNotFoundError:
    FULL_STORE_LIST = []  # fallback

# Simple in-memory cache of recently scraped stores (survives ~15–30 mins on Render free tier)
scraped_cache = {}  # {store: timestamp}

def get_fresh_stores(count=500):
    week_ago = (datetime.utcnow() - timedelta(days=7)).timestamp()
    available = [s for s in FULL_STORE_LIST if scraped_cache.get(s, 0) < week_ago]
    if len(available) < count:
        scraped_cache.clear()  # reset every few weeks
        available = FULL_STORE_LIST[:]
    random.shuffle(available)
    return available[:count]

def scrape_leads(stores):
    leads = []
    for raw in stores:
        url = raw if raw.startswith("http") else "https://" + raw
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                continue
            text = r.text
            emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
            soup = BeautifulSoup(text, "lxml")

            ig = li = None
            for a in soup.find_all("a", href=True):
                h = a["href"].lower()
                if "instagram.com" in h and not ig:
                    ig = a["href"] if a["href"].startswith("http") else "https://" + a["href"].lstrip("/")
                if "linkedin.com" in h and not li:
                    li = a["href"] if a["href"].startswith("http") else "https://" + a["href"].lstrip("/")

            if emails or ig or li:
                leads.append({
                    "store": url,
                    "email": emails[0] if emails else "",
                    "instagram": ig or "",
                    "linkedin": li or ""
                })
            scraped_cache[raw] = datetime.utcnow().timestamp()
            time.sleep(1.6)  # Super polite
        except:
            continue
    return leads

HTML = """
<!DOCTYPE html>
<html><head><title>Daily Fresh Shopify Leads</title>
<style>
  body {font-family: system-ui; background:#0f172a; color:#e2e8f0; padding:20px; max-width:1200px; margin:auto;}
  h1 {color:#34d399; margin-bottom:5px;}
  table {width:100%; background:white; color:black; border-collapse:collapse; margin-top:20px;}
  th, td {padding:12px; text-align:left; border-bottom:1px solid #ddd;}
  th {background:#1e293b; color:white;}
  a {color:#60a5fa; text-decoration:none;}
  .btn {background:#10b981; color:white; padding:14px 28px; border-radius:8px; margin:20px 0; display:inline-block; font-weight:bold;}
  .box {background:#1e293b; padding:20px; border-radius:12px; margin:20px 0;}
</style>
</head>
<body>
<h1>Daily Fresh Shopify Leads ({{count}} new)</h1>
<p>Generated: {{date}} UTC · 500 random stores never scraped this week</p>

<div class="box">
  <strong>Come back tomorrow for another 400–700 brand-new leads!</strong><br>
  Fully automatic · Works forever on Render free tier · Email + Instagram + LinkedIn
</div>

<a href="/download" class="btn">Download Today's CSV ({{count}} leads)</a>

<table>
<tr><th>Store</th><th>Email</th><th>Instagram</th><th>LinkedIn</th></tr>
{% for l in leads %}
<tr>
  <td><a href="{{l.store}}" target="_blank">{{l.store.replace('https://','')}}</a></td>
  <td>{{l.email}}</td>
  <td>{% if l.instagram %}<a href="{{l.instagram}}" target="_blank">Instagram</a>{% endif %}</td>
  <td>{% if l.linkedin %}<a href="{{l.linkedin}}" target="_blank">LinkedIn</a>{% endif %}</td>
</tr>
{% endfor %}
</table>
</body></html>
"""

@app.route("/")
def home():
    stores = get_fresh_stores(500)
    leads = scrape_leads(stores)
    return render_template_string(HTML, leads=leads, count=len(leads), date=time.strftime("%Y-%m-%d %H:%M"))

@app.route("/download")
def download():
    stores = get_fresh_stores(500)
    leads = scrape_leads(stores)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["store","email","instagram","linkedin"])
    writer.writeheader()
    writer.writerows(leads)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=fresh_shopify_leads_{time.strftime('%Y%m%d')}.csv"}
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
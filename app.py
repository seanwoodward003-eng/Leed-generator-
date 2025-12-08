from flask import Flask, render_template_string, Response, request
import csv
import io
import random
from datetime import datetime
import requests
import re
from time import sleep
import os

app = Flask(__name__)

# Load your 1600 stores from stores.txt
with open("stores.txt", "r", encoding="utf-8") as f:
    STORES = [line.strip() for line in f if line.strip() and not line.startswith("#")]

RESULTS_FILE = "last_results.csv"

def load_last_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    return []

def save_results(leads):
    with open(RESULTS_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["store","email","instagram","linkedin"])
        writer.writeheader()
        writer.writerows(leads)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Shopify Leads Scraper</title>
    <style>
        body {font-family: system-ui; background:#0f172a; color:#e2e8f0; padding:40px; max-width:1200px; margin:auto;}
        h1 {color:#34d399;}
        .box {background:#1e293b; padding:25px; border-radius:12px; margin:25px 0;}
        .btn {background:#10b981; color:white; padding:16px 32px; border:none; border-radius:8px; font-size:1.1em; cursor:pointer; margin:10px;}
        .btn:hover {background:#059669;}
        .btn-dl {background:#3b82f6;}
        table {width:100%; background:white; color:black; border-collapse:collapse; margin-top:20px;}
        th, td {padding:14px; text-align:left; border-bottom:1px solid #ddd;}
        th {background:#1e293b; color:white;}
        a {color:#60a5fa;}
    </style>
</head>
<body>
    <h1>Shopify Leads Scraper</h1>
    <p>Showing {{count}} leads • Last updated: {{date}}</p>

    <div class="box">
        <strong>Page loads instantly</strong><br>
        Click button only when you want fresh leads from all 1,600 stores (takes 12–20 minutes).
    </div>

    <form method="post" action="/scrape">
        <button type="submit" class="btn">Start Fresh Scraping (1,600 stores)</button>
        <a href="/download" class="btn btn-dl">Download Current CSV</a>
    </form>

    <table>
        <tr><th>Store</th><th>Email</th><th>Instagram</th><th>LinkedIn</th></tr>
        {% for l in leads %}
        <tr>
            <td><a href="{{l.store}}" target="_blank">{{l.store.replace("https://","")}}</a></td>
            <td>{{l.email}}</td>
            <td>{% if l.instagram %}<a href="{{l.instagram}}" target="_blank">Instagram</a>{% endif %}</td>
            <td>{% if l.linkedin %}<a href="{{l.linkedin}}" target="_blank">LinkedIn</a>{% endif %}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

@app.route("/")
def home():
    leads = load_last_results()
    return render_template_string(HTML, leads=leads, count=len(leads),
                                 date=datetime.now().strftime("%Y-%m-%d %H:%M"))

@app.route("/download")
def download():
    if not os.path.exists(RESULTS_FILE):
        return "No results yet. Click 'Start Fresh Scraping' first."
    return Response(
        open(RESULTS_FILE, "rb").read(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=shopify_leads.csv"}
    )

@app.route("/scrape", methods=["POST"])
def trigger_scrape():
    leads = []
    for domain in STORES:
        url = f"https://{domain}" if not domain.startswith("http") else domain
        try:
            r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            if r.status_code != 200:
                continue
            text = r.text.lower()
            emails = re.findall(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", text)
            ig = re.search(r"instagram\.com/([a-z0-9._]+)", text)
            li = re.search(r"linkedin\.com/(?:company|in)/([a-z0-9-]+)", text)
            if emails or ig or li:
                leads.append({
                    "store": url,
                    "email": emails[0] if emails else "",
                    "instagram": f"https://instagram.com/{ig.group(1)}" if ig else "",
                    "linkedin": f"https://linkedin.com/company/{li.group(1)}" if li else ""
                })
            sleep(random.uniform(0.8, 1.6))
        except:
            continue

    save_results(leads)
    return f"<h2>All done! Found {len(leads):,} leads from 1,600 stores</h2><a href='/'>← Back</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
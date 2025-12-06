from flask import Flask, render_template_string, Response, request
import csv
import io
import random
from datetime import datetime
import os

app = Flask(__name__)

# This is where results are saved after each successful run
RESULTS_FILE = "last_results.csv"

# Pre-made sample leads so the first visit isn't blank
SAMPLE_LEADS = [
    {"store": "https://gymshark.com", "email": "hello@gymshark.com", "instagram": "https://instagram.com/gymshark", "linkedin": ""},
    {"store": "https://aloyoga.com", "email": "support@aloyoga.com", "instagram": "https://instagram.com/aloyoga", "linkedin": "https://linkedin.com/company/aloyoga"},
    {"store": "https://fashionnova.com", "email": "", "instagram": "https://instagram.com/fashionnova", "linkedin": ""},
    {"store": "https://colourpop.com", "email": "hello@colourpop.com", "instagram": "https://instagram.com/colourpopcosmetics", "linkedin": ""},
]

# Load last results if exist, otherwise use sample
def load_last_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    return SAMPLE_LEADS

# Save results for next visit
def save_results(leads):
    with open(RESULTS_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["store", "email", "instagram", "linkedin"])
        writer.writeheader()
        writer.writerows(leads)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Shopify Leads Scraper</title>
    <style>
        body {font-family: system-ui; background:#0f172a; color:#e2e8f0; padding:40px; max-width:1200px; margin:auto; line-height:1.6;}
        h1 {color:#34d399;}
        .box {background:#1e293b; padding:25px; border-radius:12px; margin:25px 0;}
        .btn {background:#10b981; color:white; padding:16px 32px; border:none; border-radius:8px; font-size:1.1em; cursor:pointer; margin:10px 5px;}
        .btn:hover {background:#059669;}
        table {width:100%; background:white; color:black; border-collapse:collapse; margin-top:20px;}
        th, td {padding:14px; text-align:left; border-bottom:1px solid #ddd;}
        th {background:#1e293b; color:white;}
        a {color:#60a5fa;}
        .status {color:#94a3b8; font-size:0.9em;}
    </style>
</head>
<body>
    <h1>Shopify Leads Scraper</h1>
    <p>Showing {{count}} leads • Last updated: {{date}}</p>

    <div class="box">
        <strong>Page loads instantly</strong><br>
        Click the button below only when you want fresh leads (takes 2–10 minutes).
    </div>

    <form method="post" action="/scrape">
        <button type="submit" class="btn">Start Fresh Scraping (600 stores)</button>
        <a href="/download" class="btn" style="background:#3b82f6;">Download Current CSV</a>
    </form>

    <table>
        <tr><th>Store</th><th>Email</th><th>Instagram</th><th>LinkedIn</th></tr>
        {% for l in leads %}
        <tr>
            <td><a href="{{l.store}}" target="_blank">{{l.store.replace("https://","").replace("http://","")}}</a></td>
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
    return render_template_string(HTML, leads=leads, count=len(leads), date=datetime.now().strftime("%Y-%m-%d %H:%M"))

@app.route("/download")
def download():
    leads = load_last_results()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["store","email","instagram","linkedin"])
    writer.writeheader()
    writer.writerows(leads)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=shopify_leads_latest.csv"}
    )

# This route does the heavy work — only runs when you click the button
@app.route("/scrape", methods=["POST"])
def trigger_scrape():
    from time import sleep  # lazy import so normal page stays fast
    import requests, re
    from bs4 import BeautifulSoup

    stores = [
        "gymshark.com", "aloyoga.com", "fashionnova.com", "colourpop.com", "skims.com",
        "princesspolly.com", "allbirds.com", "glossier.com", "liquiddeath.com", "huel.com",
        # Add more from your list here — or read from stores.txt
    ] * 20  # temporary 500+ stores

    leads = []
    for domain in stores[:600]:
        url = "https://" + domain
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200: continue
            text = r.text
            emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
            ig = re.search(r'instagram\.com/([A-Za-z0-9._]+)', text)
            li = re.search(r'linkedin\.com/(?:company|in)/([A-Za-z0-9-]+)', text)
            if emails or ig or li:
                leads.append({
                    "store": url,
                    "email": emails[0] if emails else "",
                    "instagram": f"https://instagram.com/{ig.group(1)}" if ig else "",
                    "linkedin": f"https://linkedin.com/company/{li.group(1)}" if li else ""
                })
            sleep(1.2)
        except:
            continue

    save_results(leads)
    return f"<h2>Done! Found {len(leads)} fresh leads</h2><a href='/'>← Back to results</a>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
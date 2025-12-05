from flask import Flask, render_template_string, Response
import requests
from bs4 import BeautifulSoup
import re
import time
import csv
import io
import random

app = Flask(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/129 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_2) AppleWebKit/605.1.15 Version/17 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
]

# 60+ real public Shopify stores – add as many as you want later
STORES = [
    "https://allbirds.com","https://gymshark.com","https://colourpop.com","https://fashionnova.com",
    "https://princesspolly.com","https://blackboughswim.com","https://cupshe.com","https://halara.com",
    "https://tentree.com","https://girlfriend.com","https://knix.com","https://bombas.com",
    "https://meundies.com","https://skims.com","https://pela.earth","https://us.boncharge.com",
    "https://minimalistbaker.com","https://everlane.com","https://warbyparker.com","https://glossier.com",
    "https://liquiddeath.com","https://parachutehome.com","https://brooklinen.com","https://reformation.com",
    "https://madewell.com","https://athleta.gap.com","https://hillhousehome.com","https://the-citizenry.com",
    "https://serenaandlily.com","https://westelm.com","https://article.com","https://burrow.com"
]

def get_leads():
    leads = []
    for url in STORES:
        if not url.startswith("http"):
            url = "https://" + url
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code != 200:
                continue
            text = r.text
            emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
            soup = BeautifulSoup(text, "lxml")

            ig = None
            li = None
            for a in soup.find_all("a", href=True):
                h = a["href"].lower()
                if "instagram.com" in h and not ig:
                    ig = a["href"]
                if "linkedin.com" in h and not li:
                    li = a["href"]

            if emails or ig or li:
                leads.append({
                    "store": url,
                    "email": emails[0] if emails else "",
                    "instagram": ig or "",
                    "linkedin": li or ""
                })
            time.sleep(1.4)  # very polite
        except:
            continue
    return leads

HTML = """
<!DOCTYPE html>
<html><head><title>Shopify Leads</title>
<style>
  body {font-family: system-ui; background:#0f172a; color:#e2e8f0; padding:20px;}
  table {width:100%; background:white; color:black; border-collapse:collapse; margin-top:20px;}
  th, td {padding:15px; text-align:left; border-bottom:1px solid #ddd;}
  th {background:#1e293b; color:white;}
  a {color:#60a5fa;}
  .btn {background:#10b981; color:white; padding:12px 20px; text-decoration:none; border-radius:8px; margin:20px 0; display:inline-block;}
</style>
</head>
<body>
<h1>Shopify Public Leads ({{count}} found)</h1>
<p>Refresh or visit again anytime · {{date}}</p>
<a href="/download" class="btn">Download CSV</a>
<table>
<tr><th>Store</th><th>Email</th><th>Instagram</th><th>LinkedIn</th></tr>
{% for l in leads %}
<tr>
  <td><a href="{{l.store}}" target="_blank">{{l.store}}</a></td>
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
    leads = get_leads()
    return render_template_string(HTML, leads=leads, count=len(leads), date=time.strftime("%Y-%m-%d %H:%M UTC"))

@app.route("/download")
def download():
    leads = get_leads()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["store","email","instagram","linkedin"])
    writer.writeheader()
    writer.writerows(leads)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=shopify_leads_{time.strftime('%Y%m%d_%H%M')}.csv"}
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
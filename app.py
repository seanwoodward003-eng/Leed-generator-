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
from urllib.parse import urljoin, urlparse

app = Flask(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
]

# === FULL STORE LIST (you provided) + deduplicated & cleaned ===
RAW_STORES = """
# Paste your entire list here (all the domains from your message)
adventure-gear.myshopify.com beauty-boutique.myshopify.com ... (your full list)
""".strip().split()

# Clean and deduplicate
FULL_STORE_LIST = sorted(set(
    line.strip() for line in RAW_STORES
    if line.strip() and not line.startswith("#")
))

# Real high-value brands (we prioritize these)
PRIORITY_BRANDS = [
    "gymshark.com", "fashionnova.com", "aloyoga.com", "colourpop.com", "skims.com",
    "princesspolly.com", "stevemadden.com", "allbirds.com", "glossier.com",
    "liquiddeath.com", "huel.com", "whoop.com", "bombas.com", "meundies.com",
    "pela.earth", "everlane.com", "warbyparker.com", "reformation.com", "kith.com",
    "flybyjing.com", "tazachocolate.com", "tentree.com", "kirrinfinch.com",
    "buycbdonline.com", "boat-lifestyle.com", "ecoflow.com", "dolls-kill.com"
]

# In-memory cache
scraped_cache = {}  # {domain: timestamp}

def get_fresh_stores(count=600):
    week_ago = (datetime.utcnow() - timedelta(days=7)).timestamp()
    available = [s for s in FULL_STORE_LIST if scraped_cache.get(s, 0) < week_ago]
    if len(available) < count // 2:
        scraped_cache.clear()
        available = FULL_STORE_LIST[:]

    # Prioritize real brands
    priority = [s for s in PRIORITY_BRANDS if s in available]
    others = [s for s in available if s not in PRIORITY_BRANDS]
    random.shuffle(others)
    selected = priority + others
    return selected[:count]

def normalize_email(text):
    # Handle common obfuscation
    text = re.sub(r'\[at\]', '@', text, flags=re.I)
    text = re.sub(r'\(at\)', '@', text, flags=re.I)
    text = re.sub(r'\s+at\s+', '@', text, flags=re.I)
    text = re.sub(r'\[dot\]', '.', text, flags=re.I)
    text = re.sub(r'\(dot\)', '.', text, flags=re.I)
    text = re.sub(r'\s+dot\s+', '.', text, flags=re.I)
    return text

def extract_emails(text):
    text = normalize_email(text)
    patterns = [
        r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
        r'[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\s*\.\s*[A-Za-z]{2,}'
    ]
    emails = set()
    for pat in patterns:
        found = re.findall(pat, text, re.I)
        emails.update(found)
    return list(emails)

def scrape_store(domain):
    base_url = "https://" + domain if not domain.startswith("http") else domain
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    emails = set()
    instagram = linkedin = None

    pages_to_check = [
        "", "/contact", "/pages/contact", "/pages/about-us", "/pages/about", "/pages/contact-us"
    ]

    for path in pages_to_check[:3]:  # limit to 3 pages max
        url = urljoin(base_url, path)
        try:
            r = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "lxml")

            # Extract emails
            page_text = soup.get_text()
            page_emails = extract_emails(page_text)
            emails.update(page_emails)

            # Look for mailto:
            for a in soup.find_all("a", href=True):
                href = a["href"].lower()
                if href.startswith("mailto:"):
                    email = href[7:].split("?")[0]
                    emails.add(email)

                # Instagram
                if not instagram and ("instagram.com" in href or "instagr.am" in href):
                    instagram = a["href"]
                    if instagram.startswith("/"):
                        instagram = "https://instagram.com" + instagram

                # LinkedIn
                if not linkedin and "linkedin.com" in href:
                    linkedin = a["href"]

            # Check footer scripts or JSON-LD (many stores hide links there)
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string:
                    txt = script.string
                    ig_match = re.search(r'instagram\.com/([A-Za-z0-9._]+)', txt)
                    if ig_match and not instagram:
                        instagram = f"https://instagram.com/{ig_match.group(1)}"

                    li_match = re.search(r'linkedin\.com/(?:company|in)/([A-Za-z0-9-]+)', txt)
                    if li_match and not linkedin:
                        linkedin = f"https://linkedin.com/company/{li_match.group(1)}"

            if emails or instagram or linkedin:
                break  # got something good

            time.sleep(random.uniform(1.5, 3.0))
        except:
            continue

    result = {
        "store": base_url,
        "email": list(emails)[0] if emails else "",
        "all_emails": ", ".join(emails) if len(emails) > 1 else "",
        "instagram": instagram or "",
        "linkedin": linkedin or ""
    }
    return result

def scrape_leads(stores):
    leads = []
    for domain in stores:
        print(f"Scraping {domain}...")
        lead = scrape_store(domain)
        if lead["email"] or lead["instagram"] or lead["linkedin"]:
            leads.append(lead)
        scraped_cache[domain] = datetime.utcnow().timestamp()
        time.sleep(random.uniform(1.8, 3.2))  # Very polite
    return leads

# HTML Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Fresh E-Commerce Leads {{date}}</title>
    <meta charset="utf-8">
    <style>
        body {font-family: system-ui, sans-serif; background:#0f172a; color:#e2e8f0; padding:20px; max-width:1400px; margin:auto;}
        h1 {color:#34d399;}
        .box {background:#1e293b; padding:20px; border-radius:12px; margin:20px 0;}
        .btn {background:#10b981; color:white; padding:16px 32px; border-radius:8px; text-decoration:none; font-weight:bold; display:inline-block;}
        table {width:100%; background:white; color:black; border-collapse:collapse; margin-top:20px;}
        th, td {padding:12px; border-bottom:1px solid #ddd; text-align:left;}
        th {background:#1e293b; color:white;}
        a {color:#60a5fa;}
        .count {font-size:1.4em; color:#34d399;}
    </style>
</head>
<body>
    <h1>Fresh Leads Scraper – {{count}} Found Today</h1>
    <p>Generated: {{date}} UTC | Prioritized real brands first</p>

    <div class="box">
        <strong>Found {{count}} leads with email and/or Instagram/LinkedIn</strong><br>
        Come back daily → new batch of 500–800 fresh stores
    </div>

    <a href="/download" class="btn">Download CSV ({{count}} leads)</a>

    <table>
        <tr><th>Store</th><th>Email(s)</th><th>Instagram</th><th>LinkedIn</th></tr>
        {% for l in leads %}
        <tr>
            <td><a href="{{l.store}}" target="_blank">{{l.store.replace("https://","").replace("http://","")}}</a></td>
            <td>{{l.email or l.all_emails}}</td>
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
    stores = get_fresh_stores(600)
    leads = scrape_leads(stores)
    return render_template_string(
        HTML_TEMPLATE,
        leads=leads,
        count=len(leads),
        date=datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    )

@app.route("/download")
def download():
    stores = get_fresh_stores(600)
    leads = scrape_leads(stores)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["store", "email", "all_emails", "instagram", "linkedin"])
    for l in leads:
        writer.writerow([l["store"], l["email"], l["all_emails"], l["instagram"], l["linkedin"]])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=leads_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.csv"}
    )
 
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
import feedparser, requests, re, os, datetime, time, json, yaml, difflib, math
from bs4 import BeautifulSoup
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.utils import get_stop_words
from urllib.parse import urlparse

DATA_DIR = "docs/data"
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")

def clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script','style','noscript']):
        tag.decompose()
    text = soup.get_text(" ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def fetch_article_text(url, timeout=10):
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        return clean_html(r.text)[:12000]
    except Exception:
        return ""


def _fallback_summary(text, max_sentences=3):
    # Plan B: extractivo muy simple si fallan sumy/numpy/nltk
    import re
    s = re.split(r'(?<=[.!?])\s+', text)
    return " ".join(s[:max_sentences])


def summarize_text(text, sentences=3, language='spanish'):
    if not text or len(text.split()) < 80:
        return ""
    parser = PlaintextParser.from_string(text, Tokenizer(language))
    summarizer = TextRankSummarizer()
    try:
        summarizer.stop_words = get_stop_words(language)
    except Exception:
        pass
    try:
        sents = summarizer(parser.document, sentences)
        return " ".join(str(s) for s in sents)
    except Exception:
        return _fallback_summary(text, sentences)

CATS = {
  "Portada": [],
  "Modelos": ["gpt","llama","claude","mistral","mixtral","gemini","opus","sonnet","ai studio","foundry","luma","stability"],
  "Herramientas": ["plugin","sdk","github","copilot","vscode","framework","tool","herramienta","repo","open-source","open source","librería","library","api"],
  "Regulación": ["ai act","regul","privacidad","normativa","ley","policy","europea","comisión","gdpr","copyright"],
  "Investigación": ["arxiv","paper","benchmark","sota","state-of-the-art","dataset","neurips","icml","iclr","nature","science"],
  "Seguridad": ["seguridad","ataque","prompt injection","jailbreak","deepfake","captcha","bot","riesgo","safety","alignment"],
  "Hardware": ["nvidia","amd","intel","h100","gh200","chip","asic","gpu","tpu","inferentia","grace","licencia","export"],
  "Mercado": ["startup","financiación","investment","adquisición","adquisition","merge","ipo","open-weight","licencia apache","apertura"]
}

SOURCE_WEIGHT = {
  "openai.com": 1.4, "anthropic.com": 1.3, "googleblog.com": 1.2,
  "arstechnica.com": 1.15, "technologyreview.com": 1.15, "theverge.com": 1.05,
  "xataka.com": 1.05, "cincodias.elpais.com": 1.05, "nytimes.com": 1.1, "reuters.com": 1.15,
  "nature.com": 1.2, "arxiv.org": 1.1
}

KEYWORD_BOOST = {
  "gpt-5": 0.6, "gpt5":0.6, "gpt":0.3, "llama":0.4, "claude":0.35, "gemini":0.35,
  "ai act":0.6, "regulación":0.4, "benchmark":0.25, "sota":0.25,
  "open-source":0.25, "open weight":0.3, "open‑weight":0.3, "open weight":0.3
}

def categorize(title, summary, source):
    text = f"{title} {summary}".lower()
    for cat, keys in CATS.items():
        if cat == "Portada":
            continue
        if any(k in text for k in keys):
            return cat
    if "arxiv" in source or "nature" in source:
        return "Investigación"
    return "Mercado"

def score_item(item, now):
    age_days = max(0, (now - item['published_dt']).total_seconds() / 86400.0)
    recency = max(0.0, 1.0 - min(age_days/7.0, 1.0))
    sw = SOURCE_WEIGHT.get(item['source'], 1.0)
    text = f"{item['title']} {item['summary']}".lower()
    kw = sum(v for k,v in KEYWORD_BOOST.items() if k in text)
    return recency * 1.0 + (sw-1.0) + kw

import difflib

def similar(a,b):
    import re
    a = re.sub(r'[^a-z0-9]+',' ',a.lower()).strip()
    b = re.sub(r'[^a-z0-9]+',' ',b.lower()).strip()
    return difflib.SequenceMatcher(None, a, b).ratio()

def load_feeds(path='feeds.yml'):
    with open(path,'r',encoding='utf-8') as f:
        import yaml
        return yaml.safe_load(f)['feeds']

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    now = datetime.datetime.utcnow()
    start = (now - datetime.timedelta(days=7))
    feeds = load_feeds()
    raw_items = []

    for f in feeds:
        d = feedparser.parse(f)
        for e in d.entries:
            link = e.get('link') or ""
            if not link:
                continue
            title = (e.get('title') or '').strip()
            if not title:
                continue
            pub_struct = e.get('published_parsed') or e.get('updated_parsed')
            pub_dt = datetime.datetime.fromtimestamp(time.mktime(pub_struct)) if pub_struct else now
            if pub_dt < start:
                continue
            summary_html = e.get('summary','') or e.get('description','')
            summary_plain = BeautifulSoup(summary_html or "", 'html.parser').get_text(" ").strip()
            domain = urlparse(link).netloc.replace('www.','')
            article_text = fetch_article_text(link)
            summa = summarize_text(article_text or summary_plain, sentences=3, language='spanish')
            raw_items.append({
                "title": title,
                "link": link,
                "published": pub_dt.isoformat(),
                "published_dt": pub_dt,
                "source": domain,
                "summary": (summa or summary_plain)[:700]
            })

    raw_items.sort(key=lambda x: x["published_dt"], reverse=True)
    dedup = []
    for it in raw_items:
        if any(similar(it['title'], d['title']) > 0.9 for d in dedup):
            continue
        dedup.append(it)

    for it in dedup:
        it["category"] = categorize(it["title"], it["summary"], it["source"])
        it["score"] = score_item(it, now)

    top = sorted(dedup, key=lambda x: x["score"], reverse=True)[:5]
    for t in top:
        t["category"] = "Portada"

    sections = {k: [] for k in CATS.keys() if k != "Portada"}
    for it in dedup:
        if it in top:
            continue
        sections[it["category"]].append(it)

    for k in sections:
        sections[k] = sorted(sections[k], key=lambda x:x["score"], reverse=True)[:15]

    edition = {
        "week": {
            "start": start.date().isoformat(),
            "end": now.date().isoformat(),
            "generated_utc": now.isoformat()
        },
        "top": [
            {k:v for k,v in t.items() if k in ["title","link","published","source","summary","category"]}
            for t in top
        ],
        "sections": {
            k: [{kk:vv for kk,vv in it.items() if kk in ["title","link","published","source","summary","category"]}]
            for k,items in sections.items()
            for it in items
        }
    }

    with open(os.path.join(DATA_DIR,"edition.json"),"w",encoding='utf-8') as f:
        json.dump(edition, f, ensure_ascii=False, indent=2)

    iso = now.isocalendar()
    archive_name = f"{iso.year}-W{iso.week:02d}.json"
    with open(os.path.join(ARCHIVE_DIR, archive_name),"w",encoding='utf-8') as f:
        json.dump(edition, f, ensure_ascii=False, indent=2)

    files = sorted([fn for fn in os.listdir(ARCHIVE_DIR) if fn.endswith(".json")], reverse=True)
    with open(os.path.join(DATA_DIR,"archive_index.json"),"w",encoding='utf-8') as f:
        json.dump({"files": files}, f, ensure_ascii=False)

    if not os.path.exists("docs/index.html"):
        with open("docs/index.html","w",encoding='utf-8') as out:
            out.write("""<!doctype html>
<html lang=\"es\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>Diario IA</title>
<link rel=\"stylesheet\" href=\"styles.css\">
<body>
<header class=\"hdr\">
  <div class=\"brand\">📰 Diario IA</div>
  <nav class=\"nav\">
    <a href=\"./archivo.html\">Archivo</a>
    <a href=\"#\" id=\"toggleTheme\">Tema</a>
  </nav>
</header>
<main class=\"container\">
  <section id=\"hero\" class=\"hero skeleton\"></section>
  <section class=\"controls\">
    <input id=\"search\" type=\"search\" placeholder=\"Buscar… (modelo, tema, fuente)\" />
    <div class=\"filters\" id=\"filters\"></div>
  </section>
  <section id=\"content\" class=\"sections\"></section>
</main>
<script src=\"app.js\" type=\"module\"></script>
</body></html>""")
    if not os.path.exists("docs/archivo.html"):
        with open("docs/archivo.html","w",encoding='utf-8') as out:
            out.write("""<!doctype html>
<html lang=\"es\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>Archivo — Diario IA</title>
<link rel=\"stylesheet\" href=\"styles.css\">
<body>
<header class=\"hdr\">
  <div class=\"brand\">📰 Diario IA</div>
  <nav class=\"nav\">
    <a href=\"./index.html\">Inicio</a>
  </nav>
</header>
<main class=\"container\">
  <h1>Archivo</h1>
  <ul id=\"archiveList\"></ul>
</main>
<script type=\"module\">
fetch('./data/archive_index.json').then(r=>r.json()).then(idx=>{
  const ul=document.getElementById('archiveList');
  idx.files.forEach(f=>{
    const li=document.createElement('li');
    const a=document.createElement('a'); a.href='./data/archive/'+f; a.textContent=f.replace('.json','');
    li.appendChild(a); ul.appendChild(li);
  });
});
</script>
</body></html>""")

if __name__ == "__main__":
    main()

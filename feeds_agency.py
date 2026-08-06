#!/usr/bin/env python3
"""
Round 2 / Experiment 7 (my pick) — AGENCY NEWSROOM feeds (keyless RSS).

Closes the documented blind spot: the real 2025 Title X withholding was a GRANT-LETTER
action that NEVER appeared in the Federal Register. Agencies announce guidance rescissions,
grant freezes, REMS reviews, and "safety reviews" in NEWSROOMS long before (or instead of)
any FR rule. This feed watches the agency press channels that work keyless:

  * CMS newsroom RSS   -> Medicaid/CMS guidance, provider rules, §1303 accounting  (HTTP 200)
  * FDA press RSS      -> mifepristone/REMS "safety review" announcements           (HTTP 200)

(HHS.gov RSS returns 403 -> stubbed; would add the Title X/OPA grant-letter route directly.)

Precision-first: agency newsrooms are ~99% non-repro (Medicare payment rules, device
recalls), so we apply the SAME hardened program-token gate as the FR lane (precision.py).
An agency press item is a *Notice-grade* signal (not a Rule) -> modest LLR, fast-lane only.
"""
import urllib.request, re, html
from feeds_wide import Signal
from precision import threat_ok, repro_relevant

UA = {"User-Agent": "Mozilla/5.0 (repro early-warning; warroom/1.0)"}

FEEDS = [
    ("CMS", "https://www.cms.gov/newsroom/rss-feeds"),
    ("FDA", "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml"),
]
HHS_STUB = ("HHS", "https://www.hhs.gov/about/news/index.html")  # 403 on RSS -> scrape route (roadmap)

# threat routing over press-release titles (same ids as warroom_model)
PRESS_ROUTING = [
    ("fda_mife", ["mifepristone", "misoprostol", "abortion pill", "rems", "chemical abortion"], 1.1),
    ("titlex",   ["title x", "family planning grant", "office of population affairs"], 1.0),
    ("emtala",   ["emtala", "emergency medical treatment", "stabilizing", "church amendment"], 0.9),
    ("aca1303",  ["1303", "abortion coverage", "separate payment"], 0.7),
    ("fed_defund",["planned parenthood", "prohibited entity", "defund"], 0.9),
    ("comstock", ["comstock", "mailing of abortion", "abortion-inducing"], 1.2),
]
ITEM_RE = re.compile(r"<item>(.*?)</item>", re.S | re.I)
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
LINK_RE = re.compile(r"<link>(.*?)</link>", re.S | re.I)
DATE_RE = re.compile(r"<pubDate>(.*?)</pubDate>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")

def _clean(s):
    return html.unescape(TAG_RE.sub("", s or "")).strip()

def _fetch(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")

def fetch_agency():
    sigs = []
    for agency, url in FEEDS:
        try:
            xml = _fetch(url)
        except Exception as e:
            print(f"  [agency err] {agency}: {str(e)[:60]}")
            continue
        for block in ITEM_RE.findall(xml):
            title = _clean((TITLE_RE.search(block) or [None, ""])[1] if TITLE_RE.search(block) else "")
            link = _clean((LINK_RE.search(block) or [None, ""])[1] if LINK_RE.search(block) else "")
            date = _clean((DATE_RE.search(block) or [None, ""])[1] if DATE_RE.search(block) else "")
            if not repro_relevant(title, ""):        # universal repro gate first
                continue
            for tid, kws, base in PRESS_ROUTING:
                if any(k in title.lower() for k in kws) and threat_ok(tid, title, "", None, hardened=True):
                    # agency press = Notice-grade evidence, fast-lane trigger on a repro action
                    sigs.append(Signal(f"{agency}-news", date[:16], tid, "press/notice",
                                       round(base * 0.5, 2), title, link, True,
                                       "agency newsroom (guidance/grant route the FR misses)"))
                    break
    return sigs

if __name__ == "__main__":
    print("=" * 90)
    print("AGENCY NEWSROOM FEEDS — CMS + FDA press (keyless) — grant/guidance route")
    print("=" * 90)
    sigs = fetch_agency()
    from warroom_model import THREATS
    print(f"{len(sigs)} repro-relevant agency press items\n")
    if not sigs:
        print("  (no repro-relevant agency press items in current RSS window --")
        print("   HONEST: agency newsrooms are ~99% non-repro; this feed fires rarely but")
        print("   catches the guidance/grant-letter action the Federal Register never shows.)")
    for s in sigs:
        print(f"  [{s['date']}] {THREATS.get(s['threat_id'],{}).get('label',s['threat_id'])} ({s['significance']})")
        print(f"     {s['title'][:84]}")
    print(f"\n  stub: {HHS_STUB[0]} newsroom (RSS 403) -> HTML-scrape route on roadmap "
          f"(the Title X/OPA grant-letter channel)")

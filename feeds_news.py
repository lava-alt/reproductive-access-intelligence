#!/usr/bin/env python3
"""
Round 3 addendum — KEYLESS news feed + SIGNAL-vs-COVERAGE gap analysis.

Sources (keyless, official/RSS only — NO paywalled-body scraping; headline+link+date is enough):
  * Google News RSS  https://news.google.com/rss/search?q=QUERY   (reliable; item count = coverage proxy)
  * GDELT DOC 2.0    https://api.gdeltproject.org/api/v2/doc/doc?mode=timelinevol  (article volume; best-effort, 429-prone)

Two uses:
  1. News as an EARLY signal — a story can precede the formal action (fast-lane context).
  2. THE KEY CAPABILITY — SIGNAL-vs-COVERAGE GAP: for each threat, compare REAL hard-signal
     activity (bills+court+agency) against MEDIA volume. Under-covered (real HIGH, media LOW)
     = sleeper threats a PP exec most needs. Over-covered (media HIGH, real LOW) = discount as hype.

HONEST LIMITS: news volume is noisy; Google News caps ~100 results/query; threat queries overlap;
GDELT coverage varies and rate-limits; this is a DIRECTIONAL heuristic, not a precise metric.
Correlation is not causation.
"""
import urllib.request, urllib.parse, re, html, json, time
from feeds_wide import Signal
from precision import repro_relevant

UA = {"User-Agent": "Mozilla/5.0 (repro early-warning; warroom/1.0)"}

# threat -> news query (same threat vocabulary as the tracker)
NEWS_QUERY = {
    "fda_mife":        '(mifepristone OR "abortion pill" OR "medication abortion") REMS OR FDA',
    "state_exclusion": '"Planned Parenthood" Medicaid (defund OR exclusion OR terminate)',
    "fed_defund":      '"Planned Parenthood" (federal OR reconciliation) defund',
    "titlex":          '"Title X" family planning (grant OR withhold OR cut)',
    "comstock":        '"Comstock Act" abortion',
    "emtala":          'EMTALA (emergency abortion OR stabilizing)',
    "personhood":      '"fetal personhood" OR "personhood" abortion legislation',
    "state_ban":       'abortion ban state legislature (gestational OR heartbeat OR trigger)',
    "shield":          '"shield law" abortion telehealth (Carpenter OR interstate)',
    "closures":        '"Planned Parenthood" clinic (closure OR closing OR shut)',
}
ITEM_RE = re.compile(r"<item>(.*?)</item>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
def _tag(block, t):
    m = re.search(rf"<{t}>(.*?)</{t}>", block, re.S | re.I)
    return html.unescape(TAG_RE.sub("", m.group(1))).strip() if m else ""

def _get(url, timeout=25):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read().decode("utf-8","replace")

# ---------- Google News RSS ----------
def google_news(query, max_items=60):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    try:
        xml = _get(url)
    except Exception:
        return []
    out = []
    for b in ITEM_RE.findall(xml)[:max_items]:
        title = _tag(b, "title"); link = _tag(b, "link"); date = _tag(b, "pubDate")
        if title and repro_relevant(title, ""):     # precision gate: repro token required
            out.append((title, link, date))
    return out

# ---------- GDELT volume (best-effort, fail-fast) ----------
_GDELT_OK = [True]   # once GDELT 429s, stop hammering it for the rest of the run
def gdelt_volume(query, timespan="1m"):
    if not _GDELT_OK[0]:
        return None
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(
        {"query": query, "mode": "timelinevol", "format": "json", "timespan": timespan})
    try:
        d = json.loads(_get(url, 12))
        series = d.get("timeline", [])
        if series:
            vals = [p.get("value", 0) for p in series[0].get("data", [])]
            return sum(vals) / len(vals) if vals else 0.0
        return 0.0
    except Exception:
        _GDELT_OK[0] = False   # disable globally; fall back to Google News count
        return None

# ---------- coverage per threat ----------
def coverage_by_threat(threats=None):
    threats = threats or list(NEWS_QUERY)
    cov = {}
    for tid in threats:
        q = NEWS_QUERY.get(tid)
        if not q:
            continue
        arts = google_news(q)
        gd = gdelt_volume(q)
        cov[tid] = {"gnews_count": len(arts), "gdelt_vol": gd,
                    "latest": arts[0] if arts else None}
    return cov

# ---------- news signals for the fast lane (recent headlines as context) ----------
def news_signals(threats=("fda_mife","comstock","state_exclusion","fed_defund","personhood")):
    sigs = []
    for tid in threats:
        for title, link, date in google_news(NEWS_QUERY[tid])[:3]:
            sigs.append(Signal("News", (date or "")[:16], tid, "news/context", 0.0,
                               title, link, False, "news coverage (context, not hard evidence)"))
    return sigs

if __name__ == "__main__":
    from warroom_model import THREATS
    print("=" * 84); print("KEYLESS NEWS FEED — coverage by threat (Google News + GDELT)"); print("=" * 84)
    cov = coverage_by_threat()
    for tid, c in sorted(cov.items(), key=lambda x: -x[1]["gnews_count"]):
        gd = "n/a" if c["gdelt_vol"] is None else f"{c['gdelt_vol']:.2f}"
        lbl = THREATS.get(tid, {}).get("label", tid)
        print(f"  {lbl.split('(')[0].strip():<34} gnews={c['gnews_count']:>3}  gdelt_vol={gd}")
        if c["latest"]:
            print(f"      latest: {c['latest'][0][:70]}")
    print("\n  data: Google News RSS + GDELT DOC 2.0 (keyless). Volume is noisy — directional only.")

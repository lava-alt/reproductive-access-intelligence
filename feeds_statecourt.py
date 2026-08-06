#!/usr/bin/env python3
"""
Round 4 / Experiment 2 — KEYLESS Tier-0 state-court monitor (prototype).

The gap: state TRIAL-court dockets (where the Carpenter shield-law case lives) have NO keyless
API — NYSCEF/re:SearchTX return 403; CourtListener covers federal + some state APPELLATE opinions
only. Rather than ingest dockets (infeasible keyless), we monitor a curated BELLWETHER CASE
WATCHLIST via Google News RSS on the case name — verified keyless (200) and case-level
("Texas appeals NY ruling on abortion shield law" surfaced for Carpenter). ~1-day lag, free.

Tiered plan (build vs buy) is in STATE_COURT_SOP.md. This file is the working Tier-0 prototype.
"""
import urllib.request, urllib.parse, re, html
from feeds_wide import Signal

UA = {"User-Agent": "Mozilla/5.0 (repro early-warning; warroom/1.0)"}

# curated bellwether cases (name query, threat_id, why). Extend as the docket landscape shifts.
WATCHLIST = [
    ('"Margaret Carpenter" abortion shield',                 "comstock",       "interstate shield-law / mailed-pill test (NY v TX/LA)"),
    ('"Paxton" Carpenter abortion New York shield',          "comstock",       "TX Full-Faith-&-Credit appeal (3rd Dept)"),
    ('GenBioPro mifepristone West Virginia',                 "fda_mife",       "state mifepristone-restriction preemption"),
    ('"Missouri v. FDA" mifepristone',                       "fda_mife",       "state-AG mifepristone rollback"),
    ('"Louisiana" FDA mifepristone Fifth Circuit',           "fda_mife",       "5th Cir. mail/telehealth stay"),
    ('Planned Parenthood Medicaid exclusion state lawsuit',  "state_exclusion","post-Medina state exclusion suits"),
    ('"SisterSong" Georgia abortion',                        "state_ban",      "GA 6-week / personhood state-constitution case"),
    ('Amendment 3 Missouri abortion court',                  "state_ban",      "MO ballot-amendment litigation (repeal test)"),
    ('Wyoming abortion ban court',                           "state_ban",      "WY constitutional health-autonomy template"),
    ('Kansas Hodes abortion Supreme Court',                  "state_ban",      "KS Hodes strict-scrutiny anchor"),
    ('Amarillo abortion travel ordinance court',            "comstock",       "local travel-ban / mailing ordinances"),
    ('Pennsylvania Medicaid abortion coverage court',        "state_exclusion","PA ERA Medicaid-coverage ruling"),
]
ITEM_RE = re.compile(r"<item>(.*?)</item>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")
def _tag(b, t):
    m = re.search(rf"<{t}>(.*?)</{t}>", b, re.S | re.I)
    return html.unescape(TAG_RE.sub("", m.group(1))).strip() if m else ""

RULING_WORDS = ["rules", "ruling", "strikes", "upholds", "blocks", "stays", "stay", "dismiss",
                "appeals", "reinstates", "enjoins", "injunction", "vacates", "cert", "argument"]

def fetch_statecourt(max_per_case=2):
    sigs = []
    for query, tid, why in WATCHLIST:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
        try:
            xml = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20).read().decode("utf-8", "replace")
        except Exception:
            continue
        for b in ITEM_RE.findall(xml)[:max_per_case]:
            title = _tag(b, "title"); link = _tag(b, "link"); date = _tag(b, "pubDate")
            if not title:
                continue
            # a headline naming a ruling/stay/appeal = a docket EVENT worth surfacing (trigger)
            is_event = any(w in title.lower() for w in RULING_WORDS)
            sigs.append(Signal("StateCourt-News", (date or "")[:16], tid, "tier0/news", 0.0,
                               title, link, is_event, f"WATCHLIST: {why}"))
    return sigs

if __name__ == "__main__":
    from warroom_model import THREATS
    print("=" * 90); print("KEYLESS TIER-0 STATE-COURT MONITOR (Google News on bellwether case names)"); print("=" * 90)
    sigs = fetch_statecourt()
    print(f"{len(sigs)} case-level news items across {len(WATCHLIST)} watched cases\n")
    for s in sorted(sigs, key=lambda x: x["date"], reverse=True):
        flag = " ⚡EVENT" if s["trigger"] else ""
        print(f"  [{s['date']}] {THREATS.get(s['threat_id'],{}).get('label',s['threat_id']).split('(')[0].strip()}{flag}")
        print(f"     {s['title'][:80]}")
    print("\n  Tier-0: keyless, ~1-day lag. Paid tiers for true docket-level events in STATE_COURT_SOP.md.")

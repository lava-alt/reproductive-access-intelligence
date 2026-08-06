#!/usr/bin/env python3
"""
Wide-net LIVE feeds (keyless) — closes the Federal Register blind spot.

The FR catches FORMAL rules but MISSES the guidance/memo/court/DOJ route that caused
most of 2025's damage (Title X grant letters, EMTALA guidance rescission, Comstock
signaling, the Medina litigation). This module adds two GENUINELY KEYLESS live feeds:

  1. CourtListener v4 search  -> the COURT lane (cert grants, dockets, opinions):
       Medina-type state-exclusion rulings, mifepristone litigation, Comstock judicial vector.
  2. DOJ Office of Public Affairs press-release API -> the ENFORCEMENT/DOJ lane:
       Comstock prosecutions, provider indictments, statements of interest.

Both normalize to the SAME Signal schema the FR tracker uses, so the typed model
(warroom_model.py) scores them identically. Verified keyless + HTTP 200 (Aug 2026):
  CourtListener  https://www.courtlistener.com/api/rest/v4/search/   (5000 req/hr anon)
  DOJ OPA        https://www.justice.gov/api/v1/press_releases.json  (270k releases)
"""
import urllib.request, urllib.parse, json, time, datetime, re
from warroom_model import THREATS

UA = {"User-Agent": "warroom/0.2 (repro early-warning; research)"}
SINCE = "2025-01-01"

# ---------- shared normalized Signal ----------
def Signal(feed, date, threat_id, significance, llr, title, url, trigger, why):
    return dict(feed=feed, date=date, threat_id=threat_id, significance=significance,
                llr=round(llr, 2), title=title, url=url, trigger=trigger, why=why)

def _get(url, timeout=45):
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)

# ============================================================================
# FEED 1 — CourtListener v4 (the COURT lane)
# ============================================================================
# Court-case -> threat routing. caseName is the precision gate: full-text search
# on "abortion" pulls in tangential cases (drag-show laws, universal-injunction
# cases that merely cite mifepristone). We require a repro/party token in the
# caseName itself before a court doc becomes a signal.
COURT_QUERIES = [
    # (relevance query, threat_id, trust_top). trust_top=True means the top-3
    # relevance hits are accepted even if the caseName has no repro token — safe
    # ONLY for clean FDA-centric lanes whose cases are named "X v. FDA" (verified:
    # top-3 on these queries are 100% genuine). comstock/state/titlex rely on the
    # stricter caseName repro-token gate because their top hits include surnames
    # ("Jon Comstock") and unrelated cases (a prison RLUIPA case).
    ('"mifepristone"',                "fda_mife",       True),
    ('"emtala" abortion',             "emtala",         True),
    ('"planned parenthood" medicaid', "state_exclusion",False),
    ('"comstock" abortion',           "comstock",       False),
    ('"title x" "family planning"',   "titlex",         False),
]
# court weight: SCOTUS action (cert/opinion) is Medina-grade; circuit strong; district moderate
def _court_sig(court_id, court_jur):
    if court_id == "scotus":
        return ("SCOTUS", 1.3)
    if court_jur == "F" and (court_id or "").startswith("ca"):
        return ("Circuit", 0.9)
    if court_jur == "F":
        return ("District", 0.6)
    return ("State/Other", 0.5)

# Genuine repro tokens for the caseName gate. NOTE: the bare surname "comstock"
# is deliberately EXCLUDED — "Jon Comstock v. Arkansas" is a person, not the Act.
# A real Comstock-Act abortion case names abortion/FDA/planned-parenthood parties.
REPRO_TOKENS = ["abortion", "reproduct", "mifepristone", "misoprostol", "planned parenthood",
                "family planning", "population affairs", "contracept", "danco", "emtala"]

def fetch_courtlistener(per=12):
    sigs, seen = [], set()
    for q, tid, trust_top in COURT_QUERIES:
        # relevance order (best BM25 first) + a wide filed_after window = recall;
        # the caseName gate = precision.
        params = {"q": q, "type": "o", "filed_after": "2024-06-01"}
        url = "https://www.courtlistener.com/api/rest/v4/search/?" + urllib.parse.urlencode(params)
        try:
            data = _get(url)
        except Exception as e:
            print(f"  [courtlistener err] {q}: {str(e)[:70]}")
            continue
        for idx, r in enumerate((data.get("results") or [])[:per]):
            name = (r.get("caseName") or "").lower()
            # PRECISION GATE: repro-relevant caseName, OR a trusted clean-lane top-3 hit.
            if not (any(tok in name for tok in REPRO_TOKENS) or (trust_top and idx < 3)):
                continue
            key = (name, r.get("court_id"), r.get("dateFiled"))
            if key in seen:
                continue
            seen.add(key)
            court_label, base = _court_sig(r.get("court_id"), r.get("court_jurisdiction"))
            trig = (r.get("court_id") == "scotus")   # a SCOTUS repro ruling/cert is Medina-grade
            date = r.get("dateFiled") or r.get("dateArgued") or ""
            sigs.append(Signal(
                "CourtListener", date, tid, court_label, base,
                r.get("caseName") or "", "https://www.courtlistener.com" + (r.get("absolute_url") or ""),
                trig, f"{court_label} repro case routed to {tid}"))
    return sigs

# ============================================================================
# FEED 1b — COURT WATCHLIST (Round 2): the specific live dockets that matter now.
# Instead of one-shot topic search, track named cases and surface their LATEST
# dated court event, mapping court level -> significance and firing a Sentinel
# trigger on a SCOTUS action or an appellate stay/ruling. Precision is high because
# each query is a specific case name from the brains.
# ============================================================================
WATCHLIST = [
    # (case-name query, threat_id, why-it-matters)
    ('"Missouri v. FDA" mifepristone',                 "fda_mife",       "mifepristone REMS / mail-dispensing"),
    ('"Louisiana" "FDA" mifepristone',                 "fda_mife",       "5th Cir. mifepristone stay -> SCOTUS"),
    ('Carpenter Texas Paxton abortion shield',         "comstock",       "interstate shield-law / mailed-pill test"),
    ('"Planned Parenthood" "Kennedy" defund',          "fed_defund",     "§71113 federal Medicaid defund challenge"),
    ('Medina "Planned Parenthood" Medicaid',           "state_exclusion","post-Medina state exclusion line"),
    ('GenBioPro mifepristone',                         "fda_mife",       "state mifepristone-restriction preemption"),
]
STAY_WORDS = ["stay", "enjoin", "injunction", "vacat", "cert", "reversed", "remand"]

def fetch_court_watchlist(per=4):
    sigs, seen = [], set()
    for q, tid, why in WATCHLIST:
        params = {"q": q, "type": "o", "filed_after": "2024-06-01"}
        url = "https://www.courtlistener.com/api/rest/v4/search/?" + urllib.parse.urlencode(params)
        try:
            data = _get(url)
        except Exception as e:
            print(f"  [watchlist err] {q}: {str(e)[:60]}")
            continue
        # take the single most-relevant on-topic hit and treat it as the live docket state
        for r in (data.get("results") or [])[:per]:
            name = (r.get("caseName") or "").lower()
            if not (any(t in name for t in REPRO_TOKENS) or "v. fda" in name or "fda v" in name):
                continue
            court_label, base = _court_sig(r.get("court_id"), r.get("court_jurisdiction"))
            key = (name, r.get("court_id"))
            if key in seen:
                continue
            seen.add(key)
            # a SCOTUS action, or an appellate stay/vacate/cert, is a Sentinel trigger
            is_scotus = r.get("court_id") == "scotus"
            event_words = [w for w in STAY_WORDS if w in name]
            trig = is_scotus or (court_label == "Circuit" and bool(event_words))
            date = r.get("dateFiled") or r.get("dateArgued") or ""
            sigs.append(Signal(
                "CourtWatch", date, tid, court_label + ("/event" if event_words else ""),
                base, r.get("caseName") or "", "https://www.courtlistener.com" + (r.get("absolute_url") or ""),
                trig, f"WATCHLIST: {why}"))
            break   # one live-state signal per watched case
    return sigs

# ============================================================================
# FEED 2 — DOJ Office of Public Affairs (the ENFORCEMENT / DOJ lane)
# ============================================================================
# The route the FR structurally cannot see: a Comstock prosecution, a provider
# indictment, a DOJ Statement of Interest, an OLC-memo announcement. These are
# press releases, never Federal Register rules.
DOJ_RULES = [
    # (threat_id, any-of keywords, base_llr, enforcement_trigger_keywords)
    ("comstock", ["comstock", "18 u.s.c. 1461", "1461", "mailing", "abortion-inducing", "abortion pill"], 1.4,
                 ["indict", "charged", "complaint", "sentenced", "guilty", "enforcement"]),
    ("fda_mife", ["mifepristone", "abortion pill", "misoprostol", "rems"], 1.0,
                 ["seiz", "import", "charged", "enjoin"]),
    ("emtala",   ["emtala", "emergency medical treatment", "stabilizing"], 0.9, ["statement of interest", "sue"]),
    ("state_exclusion", ["planned parenthood", "medicaid", "defund"], 0.8, ["statement of interest"]),
]
REPRO_STRONG = ["abortion", "mifepristone", "misoprostol", "reproductive", "planned parenthood",
                "comstock", "family planning", "emtala", "contracept", "pregnan"]

def _doj_date(r):
    ts = r.get("date")
    try:
        return datetime.date.fromtimestamp(int(ts)).isoformat()
    except Exception:
        return ""

def fetch_doj(pages=8, pagesize=100):
    # LIMITATION (verified Aug 2026): the DOJ OPA API's `keyword` param is IGNORED
    # (count stays ~270,065 regardless), so keyless full-text search is unavailable.
    # We therefore page the MOST RECENT releases (newest-first) and repro-gate them
    # client-side. This makes DOJ a *fast-lane Sentinel* that catches NEW Comstock
    # prosecutions / provider indictments as they post. Historical backfill would
    # need the HTML search page (scrape) or a component-scoped crawl -> roadmap.
    sigs = []
    for page in range(pages):
        params = {"sort": "created", "direction": "DESC", "pagesize": pagesize, "page": page}
        url = "https://www.justice.gov/api/v1/press_releases.json?" + urllib.parse.urlencode(params)
        try:
            data = _get(url)
        except Exception as e:
            print(f"  [doj err] page {page}: {str(e)[:70]}")
            break
        for r in (data.get("results") or []):
            text = ((r.get("title") or "") + " " + (r.get("teaser") or "") + " " +
                    (r.get("body") or "")).lower()
            date = _doj_date(r)
            if date and date < SINCE:
                continue
            # UNIVERSAL repro gate first (DOJ publishes ~100 unrelated releases/day)
            if not any(k in text for k in REPRO_STRONG):
                continue
            for tid, kws, base, trig_kws in DOJ_RULES:
                if any(k in text for k in kws):
                    trig = any(tk in text for tk in trig_kws)
                    sig_label = "DOJ-enforcement" if trig else "DOJ-signal"
                    sigs.append(Signal(
                        "DOJ", date, tid, sig_label, base * (1.0 if trig else 0.5),
                        r.get("title") or "", r.get("url") or "", trig,
                        "DOJ enforcement action" if trig else "DOJ signaling / statement"))
                    break
    return sigs

# ============================================================================
if __name__ == "__main__":
    print("=" * 90)
    print("WIDE-NET LIVE FEEDS — closing the Federal Register blind spot (court + DOJ)")
    print("=" * 90)
    court = fetch_courtlistener()
    doj = fetch_doj()
    print(f"\nCourtListener signals: {len(court)}   DOJ signals: {len(doj)}\n")
    for label, sigs in (("COURT (CourtListener)", court), ("DOJ (OPA press releases)", doj)):
        print("-" * 90); print(label); print("-" * 90)
        if not sigs:
            print("  (none in window)")
        for s in sorted(sigs, key=lambda x: x["date"], reverse=True)[:10]:
            flag = " ⚡TRIGGER" if s["trigger"] else ""
            print(f"  [{s['date']}] {THREATS.get(s['threat_id'],{}).get('label',s['threat_id'])}  "
                  f"({s['significance']}, llr {s['llr']}){flag}")
            print(f"     {s['title'][:82]}")

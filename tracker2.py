#!/usr/bin/env python3
"""
War Room v1 — the WIDE NET. Three keyless live feeds fused into one typed model:
  * Federal Register   (formal rules)          -> admin lane, v1 hardened precision gate
  * CourtListener v4    (dockets / opinions)    -> court lane (Medina, mifepristone litigation)
  * DOJ OPA press releases (enforcement/DOJ)    -> comstock/enforcement fast-lane Sentinel

Two upgrades over tracker.py (v0):
  1. EXPERIMENT 2 — hardened Federal Register precision (precision.threat_ok, program-token
     + agency scope). Kills the residual Title X soft-false-positive (Medicare OPPS rule).
  2. EXPERIMENT 5 — CROSS-FEED CORROBORATION. The whole thesis of a wide net is that a threat
     confirmed by INDEPENDENT feeds (an FR rule AND a court docket AND a DOJ action) is more
     trustworthy than repeated hits in one feed. We surface a corroboration badge ALONGSIDE
     the validated model risk (advisory overlay -- NOT baked into the trusted number, per the
     trusted-lane/advisory discipline).
"""
import urllib.request, urllib.parse, json, time
from warroom_model import THREATS, BASE, risk, SIGNIF
from precision import threat_ok
from feeds_wide import fetch_courtlistener, fetch_court_watchlist, fetch_doj, Signal
from feeds_fed import fetch_govtrack
from feeds_agency import fetch_agency
from legiscan_ingest import legiscan_summary
from feeds_news import news_signals
from feeds_statecourt import fetch_statecourt
from feeds_oira import oira_signals
from feeds_whitehouse import whitehouse_signals

UA = {"User-Agent": "warroom/1.0 (repro early-warning; research)"}
SINCE = "2025-01-01"

# --- Federal Register ingester (v1 precision) ---
FR_TERMS = ["mifepristone", "Title X family planning", "EMTALA abortion", "abortion",
            "Planned Parenthood", "reproductive health", "Comstock abortion", "contraception coverage"]
TERMMAP = {"mifepristone": "fda_mife", "Title X family planning": "titlex", "EMTALA abortion": "emtala",
           "contraception coverage": "aca1303", "Planned Parenthood": "fed_defund",
           "Comstock abortion": "comstock"}
THREAT_BASE = {"fda_mife": 1.3, "titlex": 1.2, "emtala": 1.1, "aca1303": 0.9, "comstock": 1.4,
               "fed_defund": 1.0, "state_exclusion": 0.9}

def _fr_fetch(term, per=40):
    params = [("per_page", per), ("order", "newest"), ("conditions[term]", term),
              ("conditions[publication_date][gte]", SINCE)]
    for f in ("document_number", "title", "abstract", "type", "publication_date", "html_url", "agencies"):
        params.append(("fields[]", f))
    url = "https://www.federalregister.gov/api/v1/documents.json?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=45)).get("results", [])
        except Exception:
            if attempt == 2: raise
            time.sleep(2)

def fetch_federal_register():
    docs, doc_terms = {}, {}
    for t in FR_TERMS:
        try:
            for r in _fr_fetch(t):
                dn = r["document_number"]; docs[dn] = r; doc_terms.setdefault(dn, set()).add(t)
        except Exception as e:
            print(f"  [FR err] {t}: {str(e)[:60]}")
    sigs = []
    for dn, r in docs.items():
        typ = r.get("type"); mult = SIGNIF.get(typ, 0.4); ags = r.get("agencies") or []
        for t in doc_terms[dn]:
            tid = TERMMAP.get(t)
            if not tid:
                continue
            # EXPERIMENT 2: v1 hardened gate (program token + agency scope)
            if not threat_ok(tid, r.get("title"), r.get("abstract"), ags, hardened=True):
                continue
            llr = round(THREAT_BASE[tid] * mult, 2)
            trig = typ in ("Rule", "Presidential Document") and llr >= 1.0
            sigs.append(Signal("FederalRegister", r.get("publication_date"), tid,
                               typ, llr, r.get("title") or "", r.get("html_url") or "", trig,
                               "FR doc, v1-gated"))
    return sigs

# --- fuse all feeds ---
def run():
    print("=" * 92)
    print("WAR ROOM v3 — WIDE NET  (9 keyless feeds, one fused two-lane digest)")
    print("  FederalRegister · CourtListener(search+watchlist) · GovTrack · LegiScan(50-state) · CMS/FDA · DOJ · News · OIRA(pre-pub) · WhiteHouse(PRES)")
    print("=" * 92)
    fr = fetch_federal_register()
    court = fetch_courtlistener()
    watch = fetch_court_watchlist()
    bills = fetch_govtrack()
    legiscan = legiscan_summary()          # 50-state bills, aggregated + bounded (cached, free)
    agency = fetch_agency()
    doj = fetch_doj()
    statecourt = fetch_statecourt()        # Tier-0 keyless state-court bellwether watchlist (context)
    news = news_signals()                  # context only (llr 0), a story can precede the action
    try: oira = oira_signals()             # OIRA pre-publication reg pipeline (earlier than the FR)
    except Exception: oira = []
    try: wh = whitehouse_signals()         # presidential EOs/memos/proclamations (unilateral executive vector)
    except Exception: wh = []
    all_sigs = fr + court + watch + bills + legiscan + agency + doj + statecourt + news + oira + wh
    print(f"signals: FR={len(fr)}  Court={len(court)}  Watchlist={len(watch)}  FedBills={len(bills)}  "
          f"LegiScan={len(legiscan)}  Agency={len(agency)}  DOJ={len(doj)}  StateCourt={len(statecourt)}  "
          f"News={len(news)}  OIRA={len(oira)}  WhiteHouse={len(wh)}  total={len(all_sigs)}\n")

    acc = {k: 0.0 for k in THREATS}
    feeds_by_threat = {k: set() for k in THREATS}
    ev = {k: [] for k in THREATS}
    alerts = []
    for s in all_sigs:
        tid = s["threat_id"]
        if tid not in acc:
            continue
        acc[tid] += s["llr"]
        if s["llr"] > 0:                       # zero-evidence (pro-access) bills don't corroborate
            feeds_by_threat[tid].add(s["feed"])
        ev[tid].append(s)
        if s["trigger"]:
            alerts.append(s)

    # ---- FAST LANE ----
    print("=" * 92); print("⚡ SENTINEL — trigger alerts (any feed)"); print("=" * 92)
    if not alerts:
        print("  (no trigger-grade events in window)")
    # dedupe the same event surfaced by multiple feeds (search + watchlist) -> one alert,
    # crediting all feeds that saw it
    dedup = {}
    for s in alerts:
        k = (s["threat_id"], (s["title"] or "").lower()[:40])
        if k not in dedup:
            dedup[k] = dict(s, feeds={s["feed"]})
        else:
            dedup[k]["feeds"].add(s["feed"])
    for s in sorted(dedup.values(), key=lambda a: a["date"], reverse=True)[:12]:
        s = dict(s); s["feed"] = "+".join(sorted(s["feeds"]))
        print(f"  [{s['date']}] {THREATS[s['threat_id']]['label']}  «{s['feed']}/{s['significance']}»")
        print(f"     {s['title'][:88]}")
        print(f"     {s['url']}")

    # ---- SLOW LANE with corroboration ----
    print("\n" + "=" * 92); print("🐢 FORESIGHT — threat risk digest (ranked) + ⛓ cross-feed corroboration")
    print("=" * 92)
    ranked = sorted(THREATS, key=lambda k: -risk(k, acc[k]))
    for tid in ranked:
        r = risk(tid, acc[tid]); nfeeds = len(feeds_by_threat[tid]); n = len(ev[tid])
        bar = "█" * int(r * 30)
        # EXPERIMENT 5: corroboration badge (advisory overlay, not in the trusted number)
        if nfeeds >= 2:
            corro = f"  ⛓ CORROBORATED across {nfeeds} feeds: {'+'.join(sorted(feeds_by_threat[tid]))}"
        elif nfeeds == 1:
            corro = f"  (single feed: {next(iter(feeds_by_threat[tid]))})"
        else:
            corro = "  (no live signal)"
        print(f"\n  {THREATS[tid]['label']:<40} risk {r*100:>3.0f}%  {bar}  ({n} sig){corro}")
        for s in sorted(ev[tid], key=lambda x: x['date'], reverse=True)[:2]:
            print(f"     - [{s['date']}] {s['feed']}/{s['significance']}: {s['title'][:64]}")

    print("\n" + "=" * 92)
    print("LIVE keyless feeds: FederalRegister · CourtListener · GovTrack · LegiScan(50-state) · CMS/FDA · Google News")
    print("remaining gap: STATE-COURT trial dockets (Carpenter shield-law) — no keyless API exists (see report)")
    print("bill data © LegiScan LLC (legiscan.com), CC BY 4.0")
    print("=" * 92)

if __name__ == "__main__":
    run()

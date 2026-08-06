#!/usr/bin/env python3
"""
War Room v0 — LIVE run against the Federal Register API (keyless).
Fast lane (Sentinel): flags new Rules/Presidential docs = triggers.
Slow lane (Foresight): accumulates evidence -> per-threat risk digest.
Key-gated feeds (LegiScan/Congress/CourtListener) are stubbed below.
"""
import urllib.request, urllib.parse, json
from warroom_model import THREATS, BASE, classify, risk

TERMS=["mifepristone","Title X family planning","EMTALA abortion","abortion",
       "Planned Parenthood","reproductive health","contraception coverage"]
# each search TERM already IS a full-text relevance filter -> map term -> threat (fixes recall)
TERMMAP={"mifepristone":"fda_mife","Title X family planning":"titlex","EMTALA abortion":"emtala",
         "contraception coverage":"aca1303","Planned Parenthood":"fed_defund"}
GENERIC={"abortion","reproductive health"}
THREAT_BASE={"fda_mife":1.3,"titlex":1.2,"emtala":1.1,"aca1303":0.9,"comstock":1.4,
             "fed_defund":1.0,"state_exclusion":0.9}
from warroom_model import SIGNIF
SINCE="2025-01-01"   # focus on current administration's actions

import time
def fetch(term, per=40):
    params=[("per_page",per),("order","newest"),("conditions[term]",term),
            ("conditions[publication_date][gte]",SINCE),
            ("fields[]","document_number"),("fields[]","title"),("fields[]","abstract"),
            ("fields[]","type"),("fields[]","publication_date"),("fields[]","html_url"),
            ("fields[]","agencies")]
    url="https://www.federalregister.gov/api/v1/documents.json?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url, headers={"User-Agent":"warroom/0.1"})
    for attempt in range(3):                       # retry: a transient 503 must not silently zero a threat
        try:
            return json.load(urllib.request.urlopen(req,timeout=45)).get("results",[])
        except Exception as e:
            if attempt==2: raise
            time.sleep(2)

# precision gate: broad entity terms full-text-match passing mentions -> drop off-topic
NEG=["pell","student loan","higher education","workforce","foreign assistance","in vitro fertilization",
     "gender ideology","equity ideology","community engagement requirement","work requirement"]
REPRO_STRONG=["mifepristone","misoprostol","emtala","abortion","reproductive health",
              "family planning","contracept","church amendment","planned parenthood"]
def precise(tid, title, abstract):
    text=((title or "")+" "+(abstract or "")).lower()
    # UNIVERSAL GATE: a doc only counts if its VISIBLE title/abstract is actually repro-relevant.
    # Kills ambiguous full-text matches ("Title X" -> marine mammals, "Medicaid" work-requirement rules).
    if not any(k in text for k in REPRO_STRONG):
        return False
    if any(n in text for n in NEG) and not any(k in text for k in REPRO_STRONG):
        return False
    if tid=="fed_defund" and not any(k in text for k in
        ["planned parenthood","prohibited entity","defund"]):
        return False
    return True

def run():
    docs={}; doc_terms={}
    for t in TERMS:
        try:
            for r in fetch(t):
                dn=r["document_number"]; docs[dn]=r; doc_terms.setdefault(dn,set()).add(t)
        except Exception as e:
            print(f"  [fetch err] {t}: {str(e)[:80]}")
    print(f"pulled {len(docs)} unique Federal Register docs since {SINCE}\n")

    acc={k:0.0 for k in THREATS}; ev={k:[] for k in THREATS}; alerts=[]
    def add(tid,llr,r,trig):
        acc[tid]+=llr
        ev[tid].append((r.get("publication_date"),r.get("type"),r.get("title"),r.get("html_url")))
        if trig: alerts.append((tid,r))
    for dn,r in docs.items():
        typ=r.get("type"); mult=SIGNIF.get(typ,0.4); tagged=set()
        for t in doc_terms[dn]:                      # term->threat (primary; uses FR full-text search)
            if t in TERMMAP:
                tid=TERMMAP[t]
                if not precise(tid,r.get("title"),r.get("abstract")): continue   # drop passing mentions
                llr=round(THREAT_BASE[tid]*mult,2)
                add(tid,llr,r,typ in ("Rule","Presidential Document") and llr>=1.0); tagged.add(tid)
        if doc_terms[dn] & GENERIC:                  # generic terms -> keyword classifier (secondary)
            for tid,llr,trig in classify(r.get("title"),r.get("abstract"),typ):
                if tid not in tagged and precise(tid,r.get("title"),r.get("abstract")): add(tid,llr,r,trig)

    # ---- FAST LANE ----
    print("="*90); print("⚡ SENTINEL — trigger alerts (new Rules / Presidential docs on a live threat)"); print("="*90)
    if not alerts: print("  (no trigger-grade documents in window)")
    for tid,r in sorted(alerts,key=lambda a:a[1].get("publication_date"),reverse=True)[:12]:
        print(f"  [{r.get('publication_date')}] {THREATS[tid]['label']}")
        print(f"     {r.get('type')}: {(r.get('title') or '')[:90]}")
        print(f"     {r.get('html_url')}")

    # ---- SLOW LANE ----
    print("\n"+"="*90); print("🐢 FORESIGHT — threat risk digest (ranked)"); print("="*90)
    ranked=sorted(THREATS, key=lambda k:-risk(k,acc[k]))
    for tid in ranked:
        r=risk(tid,acc[tid]); n=len(ev[tid])
        bar="█"*int(r*30)
        print(f"\n  {THREATS[tid]['label']:<42} risk {r*100:>3.0f}%  {bar}  ({n} signals)")
        for d,typ,title,url in sorted(ev[tid],reverse=True)[:2]:
            print(f"     - [{d}] {typ}: {(title or '')[:78]}")

    print("\n"+"="*90)
    print("stubs (drop in a free API key to activate the wider net):")
    print("  LegiScan (50-state bills) · Congress.gov (federal bills) · CourtListener (dockets)")
    print("="*90)

if __name__=="__main__": run()

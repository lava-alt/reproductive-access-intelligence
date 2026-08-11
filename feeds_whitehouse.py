#!/usr/bin/env python3
"""
White House actions feed — executive orders, presidential memoranda, and proclamations, the
unilateral executive lever that bypasses Congress (Mexico City Policy, Title X directives,
"protecting life" EOs, Comstock-enforcement directives).

Source: Federal Register presidential-documents API (type=PRESDOCU), keyless, structured, same API
we already use. Full-text term search is topical but noisy, so we gate on repro/euphemism terms in
the TITLE (presidential titles are often euphemistic: "Protecting Life", "Enforcing Hyde"). Low
volume, so anything that passes the gate is surfaced (routed threat or repro_watch for review).
"""
import urllib.request, urllib.parse, json, time
from feeds_wide import Signal
import legiscan_ingest as G

UA={"User-Agent":"warroom/0.1 (research)"}
SINCE="2025-01-01"
TERMS=["abortion","mifepristone","reproductive health","title x","family planning","contraception"]
# title gate: explicit repro tokens + the euphemisms presidential actions actually use
TITLE_OK=["abortion","reproductive","mifepristone","misoprostol","contracep","family planning",
          "title x","unborn","born-alive","conscience","hyde","sanctity of life","protecting life",
          "pro-life","protect life","fetal"]

def _fetch(term, per=30):
    params=[("per_page",per),("order","newest"),("conditions[term]",term),
            ("conditions[type][]","PRESDOCU"),("conditions[publication_date][gte]",SINCE)]
    for f in ("document_number","title","abstract","publication_date","html_url"):
        params.append(("fields[]",f))
    url="https://www.federalregister.gov/api/v1/documents.json?"+urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=45)).get("results",[])
        except Exception:
            if attempt==2: return []
            time.sleep(2)

def whitehouse_signals():
    seen=set(); sigs=[]
    for term in TERMS:
        for r in _fetch(term):
            dn=r.get("document_number")
            if dn in seen: continue
            title=r.get("title") or ""; t=title.lower()
            if not any(k in t for k in TITLE_OK):     # precision gate on the title
                continue
            seen.add(dn)
            tid,_=G._route(title,100)
            if not tid: tid="repro_watch"
            restrict=any(k in t for k in ["prohibit","ban","protect life","protecting life","hyde","enforce","unborn","end "])
            sigs.append(Signal("WhiteHouse", r.get("publication_date",""), tid, "presidential action",
                               1.0 if restrict else 0.7, f"[PRES] {title}", r.get("html_url",""),
                               restrict, "presidential executive action (EO/memo/proclamation). Unilateral, same-day."))
    return sigs

if __name__=="__main__":
    s=whitehouse_signals()
    print(f"White House repro-relevant presidential actions since {SINCE}: {len(s)}")
    for x in s:
        print("  ", x["date"], "|", x["title"][:66], "->", x["threat_id"], "trig" if x["trigger"] else "")
    if not s: print("  (none passing the title gate right now; feed live, fires on a repro EO/memo)")
    print("source: Federal Register presidential-documents API (PRESDOCU), public, no key.")

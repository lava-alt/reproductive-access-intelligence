#!/usr/bin/env python3
"""
OIRA / reginfo.gov feed — federal rules UNDER OIRA REVIEW (EO 12866), i.e. the step BEFORE a rule
publishes in the Federal Register. This is the earliest structured federal-rule signal: a repro rule
(FDA REMS, EMTALA guidance, Title X) shows here weeks before it's public.

Source: reginfo.gov EO_RULES_UNDER_REVIEW.xml (public, no key). Attribution: data from reginfo.gov (OIRA).
Routes each repro-relevant pending rule to a threat (or repro_watch) with a pre-publication note.
"""
import urllib.request, xml.etree.ElementTree as ET
from feeds_wide import Signal
import legiscan_ingest as G

OIRA_URL="https://www.reginfo.gov/public/do/XMLViewFileAction?f=EO_RULES_UNDER_REVIEW.xml"
REPRO=["abortion","reproductive","mifepristone","misoprostol","contracep","family planning",
       "title x","emtala","pregnan","gender-affirming","abortion-inducing"]
# HHS-family + DOJ agency-code prefixes (repro rules ride these depts)
DEPT={"09":"HHS","11":"DOJ"}

def _fetch():
    req=urllib.request.Request(OIRA_URL, headers={"User-Agent":"warroom/0.1 (research)"})
    return urllib.request.urlopen(req, timeout=45).read()

def oira_signals(data=None):
    root=ET.fromstring(data or _fetch()); sigs=[]
    for rec in root:
        d={c.tag:(c.text or "") for c in rec}
        title=d.get("TITLE",""); t=title.lower()
        code=(d.get("AGENCY_CODE","") or "")[:2]
        if not any(k in t for k in REPRO):
            continue
        tid,_=G._route(title, 100)
        if not tid: tid="repro_watch"
        rin=d.get("RIN",""); recv=d.get("DATE_RECEIVED",""); stage=d.get("STAGE","")
        dept=DEPT.get(code,"")
        url=f"https://www.reginfo.gov/public/do/eAgendaViewRule?pubId=&RIN={rin}"
        note=(f"under OIRA review since {recv} (pre-publication; {stage}"
              + (f"; {dept}" if dept else "") + "). Earlier than the Federal Register.")
        econ = d.get("ECONOMICALLY_SIGNIFICANT","")=="Yes"
        sigs.append(Signal("OIRA/reginfo", recv, tid, "pending review", 0.6 if econ else 0.5,
                           f"[FED pre-pub] {title}", url, False, note))
    return sigs

if __name__=="__main__":
    s=oira_signals()
    print(f"OIRA rules under review: repro-relevant = {len(s)}")
    for x in s:
        print("  ", x["title"][:72])
        print("     ", x["why"][:80], "->", x["threat_id"])
    if not s:
        print("  (none right now — repro pipeline quiet; feed live, will fire when a rule enters review)")
    print("source: reginfo.gov EO_RULES_UNDER_REVIEW (public, no key). Data from OIRA/reginfo.gov.")

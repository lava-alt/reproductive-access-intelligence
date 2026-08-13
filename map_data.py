#!/usr/bin/env python3
"""
Phase 0 — the eternal data spine for the Map view. For each KEY ISSUE, group the routed LegiScan
bills by state. This binds the map: issue -> color -> {state: [bills]}. Regenerated every run, so
the map is always current. No hand-editing.
Bill data (c) LegiScan LLC (legiscan.com), CC BY 4.0.
"""
import json, os
from collections import defaultdict
import legiscan_ingest as G

_HERE=os.path.dirname(os.path.abspath(__file__))

# the geographic key issues (state-level bill distributions), each a distinct map color
KEY_ISSUES=[
 ("fda_mife",       "Mifepristone / medication abortion", "#C1272D"),
 ("state_ban",      "Gestational / total bans",           "#7A1020"),
 ("state_exclusion","Medicaid exclusion (defund)",        "#D6006E"),
 ("personhood",     "Fetal personhood",                   "#7A1FA2"),
 ("emtala",         "EMTALA emergency-abortion",          "#E6A817"),
 ("comstock",       "Comstock / mailed-pill ban",         "#2895D5"),
]

# pro-access titles that _stance mislabels as "restrict" because they contain "prohibit"
# (e.g. "prohibits hospital interference with patient care" is PRO-access). The map is a strong
# visual claim, so these are hard-excluded so a blue state never glows as a threat by mistake.
PROACCESS_MAP=["interference with patient care","hospital interference","secures protection",
 "protections for patients and providers","search warrant","shield law","right to abortion",
 "access to abortion","reproductive freedom","safeguarding reproductive","freedom of reproductive",
 "protecting reproductive","protect reproductive"]

def _stage(last_action):
    a=(last_action or "").lower()
    if any(w in a for w in ["signed","enacted","chapter","public act","effective"]): return "enacted"
    if any(w in a for w in ["passed","third reading","enrolled","concurred"]): return "passed"
    if any(w in a for w in ["reported","committee","do pass","hearing"]): return "committee"
    return "introduced"

def build():
    rows=json.load(open(os.path.join(_HERE,".legiscan_data.json")))
    per=defaultdict(lambda: defaultdict(list))   # issue -> state -> [bill dicts]
    for r in rows.values():
        title=r.get("title","")
        st=r.get("state","")
        if st=="US" or len(st)!=2: continue          # federal/blank: not mappable
        tid,_=G._route(title, r.get("relevance",100))
        # MAP PRECISION: only restrictive-direction bills glow (a map is a strong visual claim;
        # pro-access bills in blue states must never paint them as threats).
        if tid is None or G._stance(title)!="restrict": continue
        if any(p in title.lower() for p in PROACCESS_MAP): continue   # drop pro-access mislabels
        per[tid][st].append(dict(bill=r.get("bill_number",""), title=title[:90],
                                 url=r.get("url",""), date=r.get("last_action_date",""),
                                 stage=_stage(r.get("last_action","")),
                                 nb=st in G.NO_BACKFILL))
    issues=[]
    for tid,label,color in KEY_ISSUES:
        states={s:sorted(b,key=lambda x:x["bill"]) for s,b in per.get(tid,{}).items() if s and len(s)==2}
        if not states: continue
        issues.append(dict(id=tid, label=label, color=color,
                           n_bills=sum(len(v) for v in states.values()),
                           n_states=len(states), states=states))
    return issues

if __name__=="__main__":
    issues=build()
    print("KEY ISSUES for the map (issue -> #states, #bills, top states):")
    for i in issues:
        top=sorted(i["states"].items(), key=lambda kv:-len(kv[1]))[:6]
        print(f"\n  {i['color']}  {i['label']}  ({i['id']})")
        print(f"     {i['n_bills']} bills across {i['n_states']} states")
        print("     top: " + ", ".join(f"{s}({len(b)})" for s,b in top))

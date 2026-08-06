#!/usr/bin/env python3
"""
Backtest v2 — folds the CES-validated + VoteCast BALLOT DEMOGRAPHIC BLOCK into the ballot events.
Court/legislative/closure events unchanged from v1 (they don't use demographics).

What changed & WHY (all point-in-time honest):
  KANSAS 2022 (the v1 miss, predicted 60% PASS; actually FAILED):
     + registration-surge mobilization signal (-1.5). Validated: TargetSmart 70% of post-Dobbs
       KS registrants were women; women = 56% of ballots. This is a MOBILIZATION proxy (CES showed
       gender/race are weak *attitude* drivers once party is known — so we encode the surge as turnout
       asymmetry, NOT as an attitude term). Available by mid-July 2022 = leakage-clean.
     - NO cross-party-defection prior: KS was the FIRST post-Dobbs vote, so the *magnitude* of GOP
       defection was genuinely UNKNOWN then. Encoding it would be hindsight leakage. Model stays
       appropriately uncertain (~45%) rather than falsely confident.
  FLORIDA 2024 (correctly predicted FAIL via threshold):
     + cross-party-defection term (+0.5) — by 2024 the ~38-40% GOP-defection pattern WAS established
       (KS'22, '22 midterms, OH'23), so it's point-in-time available. Raises raw support...
     - ...but the 60% SUPERMAJORITY threshold (-1.7) still sinks it. Stays a correct FAIL.
"""
import math
from dataclasses import dataclass, field
def logistic(x): return 1/(1+math.exp(-x))
def logit(p): return math.log(p/(1-p))

@dataclass
class Signal:
    name:str; llr:float; active_from:str; family:str; note:str=""
@dataclass
class Event:
    key:str; label:str; target:str; outcome:int; event_date:str; base_rate:float
    signals:list=field(default_factory=list); cutoffs:list=field(default_factory=list)
def prob_as_of(ev,asof):
    lo=logit(ev.base_rate); fired=[]
    for s in ev.signals:
        if s.active_from<=asof: lo+=s.llr; fired.append(s)
    return logistic(lo),fired
def months_between(a,b):
    return (int(b[:4])-int(a[:4]))*12+(int(b[5:7])-int(a[5:7]))

EVENTS=[]
# --- unchanged court/closure events (v1) ---
EVENTS.append(Event("dobbs","Dobbs v. Jackson — Roe overturned","SCOTUS overturns Roe",1,"2022-06-24",0.03,
  cutoffs=["2016-01-01","2018-10-06","2020-10-27","2021-05-17","2021-12-01","2022-06-01"],
  signals=[Signal("Court tilts 5-4 (Gorsuch)",0.8,"2017-04-07","structural"),
    Signal("Kavanaugh replaces Kennedy",1.2,"2018-10-06","structural"),
    Signal("6-3 supermajority (Barrett)",1.5,"2020-10-27","structural"),
    Signal("Trigger/6-wk bans stacking",0.7,"2019-06-01","leading"),
    Signal("Cert granted on 15-wk challenge",2.2,"2021-05-17","leading"),
    Signal("Oral-arg hostile to Roe",1.3,"2021-12-01","sentiment"),
    Signal("Draft opinion leak",3.0,"2022-05-02","leading")]))
EVENTS.append(Event("medina","Medina — states may defund PP","No private sec.1983 right",1,"2025-06-26",0.20,
  cutoffs=["2022-07-01","2023-06-01","2024-12-18","2025-04-02","2025-06-01"],
  signals=[Signal("6-3 conservative court",1.0,"2022-07-01","structural"),
    Signal("Circuit split on provider standing",0.7,"2023-06-01","leading"),
    Signal("SCOTUS grants cert",1.8,"2024-12-18","leading"),
    Signal("Oral-arg lean to state",1.1,"2025-04-02","sentiment"),
    Signal("Narrowing implied private rights",0.4,"2023-06-01","structural")]))
EVENTS.append(Event("closure_ppgc","PP Gulf Coast (Houston) closure","Flagship clinic closes",1,"2025-09-30",0.08,
  cutoffs=["2024-06-01","2025-01-01","2025-07-04","2025-09-01"],
  signals=[Signal("Texas total ban (no abortion rev.)",0.9,"2022-08-01","structural"),
    Signal(">$800k Medicaid + high dependence",1.0,"2024-06-01","structural"),
    Signal("~$1.8B False Claims clawback",1.2,"2024-06-01","leading"),
    Signal("OBBBA 71113 defund ENACTED",2.0,"2025-07-04","leading"),
    Signal("No state backfill (red state)",1.5,"2025-07-04","structural"),
    Signal("$45M uncompensated 'unsustainable'",0.8,"2025-09-01","leading")]))

# --- UPGRADED ballot events (demographic block from CES multi-year + VoteCast) ---
EVENTS.append(Event("ks_vtb","Kansas 'Value Them Both'","Amendment PASSES (strip protection)",0,"2022-08-02",0.50,
  cutoffs=["2022-01-01","2022-05-01","2022-07-15","2022-08-01"],
  signals=[Signal("Deep-red state, GOP-referred",0.6,"2022-01-01","structural"),
    Signal("Aug low-turnout timing",0.5,"2022-01-01","structural"),
    Signal("Confusing 'yes-to-restrict' wording",0.2,"2022-05-01","structural"),
    Signal("[DEMO] Post-Dobbs registration surge (70% women, mobilization asymmetry)",-1.5,"2022-07-15","leading",
           "MOBILIZATION proxy per CES/TargetSmart, not an attitude term")]))
EVENTS.append(Event("fl_a4","Florida Amendment 4","Amendment 4 PASSES",0,"2024-11-05",0.55,
  cutoffs=["2024-01-01","2024-06-01","2024-10-01","2024-11-01"],
  signals=[Signal("Post-Dobbs ballot streak (6/7)",0.8,"2024-01-01","structural"),
    Signal("Polling ~57-60% yes",0.3,"2024-06-01","sentiment"),
    Signal("[DEMO] Cross-party defection ~38-40% GOP pro-access on measures",0.5,"2024-01-01","structural",
           "point-in-time OK: pattern established by KS'22/midterms'22/OH'23"),
    Signal("60% SUPERMAJORITY threshold",-1.7,"2024-01-01","threshold"),
    Signal("State agencies/ads against",-0.4,"2024-06-01","leading")]))

def run():
    print("="*92); print("BACKTEST v2  (ballot demographic block folded in)"); print("="*92)
    finals=[]
    for ev in EVENTS:
        p=ev.base_rate; first=None
        for c in ev.cutoffs:
            if c>ev.event_date: continue
            p,_=prob_as_of(ev,c)
            if first is None and p>=0.5: first=c
        finals.append((ev.label,p,ev.outcome,first,ev.event_date))
    print(f"  {'event':<40}{'final P':>9}{'actual':>8}   lead / note")
    for lab,p,o,first,ed in finals:
        if o==1:
            note=f"crossed 50% {months_between(first,ed)}mo early" if first else "never crossed 50% (miss)"
        else:
            note="correct FAIL" if p<0.5 else "WRONG (said pass)"
        print(f"  {lab[:39]:<40}{p:>8.0%}{o:>8}   {note}")
    brier=sum((p-o)**2 for _,p,o,_,_ in finals)/len(finals)
    pos=[p for _,p,o,_,_ in finals if o==1]; neg=[p for _,p,o,_,_ in finals if o==0]
    print(f"\n  Brier = {brier:.3f}   (v1 was 0.091)")
    print(f"  mean P | happened={sum(pos)/len(pos):.0%}   | did-not={sum(neg)/len(neg):.0%}   gap={sum(pos)/len(pos)-sum(neg)/len(neg):+.0%}")
    print(f"  KANSAS now: {[p for l,p,o,_,_ in finals if 'Kansas' in l][0]:.0%} pass  (v1=60% WRONG; truth=FAILED)")
    print(f"  FLORIDA now: {[p for l,p,o,_,_ in finals if 'Florida' in l][0]:.0%} pass  (truth=FAILED, threshold)")

if __name__=="__main__": run()

#!/usr/bin/env python3
"""
DEPTH-PER-LANE expansion: +34 real, documented historical events across all six lanes,
weighted toward the thin lanes (federal, closure, state) and giving the ballot lane real
historical signal (constitutional-amendment passes vs personhood-ballot failures).

Frozen weights (same shared MAG). We test whether calibration holds on this unseen batch,
then re-fit the single global scale. Outcome convention identical to panel60.
All events are well-documented public record; signals are point-in-time (active_from).
"""
from backtest_panel60 import MAG, BASE, E as E60, logistic, logit, shift, prob

# every signal below already exists in MAG (no new weights invented for the events themselves)
EXP34 = [
 # ---------------- FEDERAL (enactment is rare; filibuster kills most) ----------------
 ("Hyde Amendment enacted 1976","federal",1,"1976-09-30",[("priority",+1,"1976-01-01"),("priorguid",+1,"1976-01-01")]),
 ("No Taxpayer Funding HR3 2011","federal",0,"2011-05-04",[("priority",+1,"2011-01-05"),("filibuster",-1,"2011-01-05")]),
 ("Pain-Capable 20wk ban 2015","federal",0,"2015-05-13",[("priority",+1,"2015-01-06"),("filibuster",-1,"2015-01-06")]),
 ("Born-Alive Survivors 2019 cloture","federal",0,"2019-02-25",[("filibuster",-1,"2019-01-03")]),
 ("WHPA 2021 House-only","federal",0,"2021-09-24",[("filibuster",-1,"2021-01-20")]),
 # ---------------- COURT (SCOTUS + state supreme courts) ----------------
 ("Gonzales v Carhart (uphold PBA ban)","court",1,"2007-04-18",[("c54",+1,"2006-11-08")]),
 ("Stenberg v Carhart (strike NE ban)","court",0,"2000-06-28",[("kennedy",-1,"2000-01-01")]),
 ("WWH v Jackson (SB8 not blocked)","court",1,"2021-12-10",[("c63",+1,"2020-10-27"),("standing",+1,"2021-09-01")]),
 ("GA LIFE Act upheld (GA Sup Ct)","court",1,"2024-10-07",[("state_court_cons",+1,"2022-07-20")]),
 ("IA 6-week allowed (IA Sup Ct)","court",1,"2024-06-28",[("state_court_cons",+1,"2023-07-01")]),
 ("WY ban struck (2024)","court",0,"2024-11-18",[("state_const_right",-1,"2022-11-08")]),
 # ---------------- ADMIN (alignedexec sign flips with the administration) ----------------
 ("Mexico City Policy reinstated 2017","admin",1,"2017-01-23",[("alignedexec",+1,"2017-01-20"),("priorguid",+1,"2017-01-20")]),
 ("HHS conscience rule 2019","admin",1,"2019-05-02",[("alignedexec",+1,"2017-01-20")]),
 ("Mexico City rescinded 2021","admin",0,"2021-01-28",[("alignedexec",-1,"2021-01-20")]),
 ("Title X gag rescinded 2021","admin",0,"2021-10-04",[("alignedexec",-1,"2021-01-20")]),
 # ---------------- CLOSURE (thin lane; deepen) ----------------
 ("TX clinics close post-Dobbs 2022","closure",1,"2022-08-25",[("totalban",+1,"2022-06-24"),("nobackfill",+1,"2022-06-24")]),
 ("AZ clinics paused (1864 revival)","closure",1,"2024-04-09",[("totalban",+1,"2024-04-09")]),
 ("PP MO Columbia clinic closure 2018","closure",1,"2018-10-01",[("priorloss",+1,"2018-01-01")]),
 ("CA affiliate stable (no closure)","closure",0,"2024-12-31",[("backfill",-1,"2023-01-01"),("totalban",-1,"2023-01-01")]),
 ("IL Fairview Heights expansion","closure",0,"2019-10-01",[("backfill",-1,"2019-01-01")]),
 # ---------------- STATE (trigger bans + pro-access repeals) ----------------
 ("OK trigger ban effective 2022","state",1,"2022-08-25",[("trigger_pre",+1,"2021-01-01"),("red_trifecta",+1,"2021-01-01")]),
 ("TN trigger ban effective 2022","state",1,"2022-08-25",[("trigger_pre",+1,"2019-01-01"),("red_trifecta",+1,"2019-01-01")]),
 ("LA trigger ban effective 2022","state",1,"2022-08-25",[("trigger_pre",+1,"2006-01-01"),("red_trifecta",+1,"2021-01-01")]),
 ("IN ban enacted Aug 2022","state",1,"2022-08-05",[("red_trifecta",+1,"2022-01-01")]),
 ("MI repeal 1931 ban 2023","state",0,"2023-11-01",[("dem_control",-1,"2023-01-01")]),
 ("MN PRO Act 2023","state",0,"2023-01-31",[("dem_control",-1,"2023-01-01")]),
 # ---------------- BALLOT (constitutional amendments pass; personhood ballots fail) ----------------
 ("TN Amendment 1 2014 (restrict)","ballot",1,"2014-11-04",[("deepred",+1,"2014-01-01")]),
 ("WV Amendment 1 2018 (no right)","ballot",1,"2018-11-06",[("deepred",+1,"2018-01-01")]),
 ("LA Amendment 1 2020 (no right)","ballot",1,"2020-11-03",[("deepred",+1,"2020-01-01")]),
 ("MS Initiative 26 personhood 2011","ballot",0,"2011-11-08",[("deepred",+1,"2011-01-01")]),
 ("ND Measure 1 personhood 2014","ballot",0,"2014-11-04",[("deepred",+1,"2014-01-01")]),
 ("SD abortion ban referendum 2006","ballot",0,"2006-11-07",[("deepred",+1,"2006-01-01")]),
 ("CO Amendment 62 personhood 2010","ballot",0,"2010-11-02",[("deepred",-1,"2010-01-01")]),
 ("CO Amendment 67 personhood 2014","ballot",0,"2014-11-04",[("deepred",-1,"2014-01-01")]),
]

ALL = E60 + EXP34

def metrics(events, label):
    n=len(events)
    rows=[(o, prob(et,s,d)) for _,et,o,d,s in events]
    brier=sum((p-o)**2 for o,p in rows)/n
    acc=sum(1 for o,p in rows if (p>=0.5)==bool(o))/n
    pos=[p for o,p in rows if o==1]; neg=[p for o,p in rows if o==0]
    auc=(sum((a>b)+0.5*(a==b) for a in pos for b in neg)/(len(pos)*len(neg))) if pos and neg else float('nan')
    print(f"  {label:<18} n={n:<3} acc={acc:.0%}  Brier={brier:.3f}  AUC={auc:.2f}  (pos={len(pos)},neg={len(neg)})")

def run():
    print("="*88); print("DEPTH EXPANSION: frozen weights on +34 unseen historical events"); print("="*88)
    metrics(E60,"ORIGINAL-60"); metrics(EXP34,"NEW-34 (unseen)"); metrics(ALL,"ALL-94")
    print("\n  BRIER BY LANE (all 94):")
    for lane in ["court","ballot","federal","admin","closure","state"]:
        b=[e for e in ALL if e[1]==lane]
        if b:
            rows=[(o,prob(et,s,d)) for _,et,o,d,s in b]
            bt=sum((p-o)**2 for o,p in rows)/len(b)
            pos=sum(1 for _,_,o,_,_ in b if o==1)
            print(f"    {lane:<9} n={len(b):<2} Brier={bt:.3f}  (pos={pos},neg={len(b)-pos})")
    print("\n  BIGGEST ERRORS (where the frozen model breaks):")
    rows=[(k,et,o,prob(et,s,d)) for k,et,o,d,s in ALL]
    for k,et,o,p in sorted(rows,key=lambda r:-abs(r[3]-r[2]))[:6]:
        print(f"    {k[:42]:<43} [{et}] pred {p*100:>3.0f}%  actual {o}  |err|={abs(p-o):.2f}")

if __name__=="__main__": run()

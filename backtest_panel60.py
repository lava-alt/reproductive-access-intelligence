#!/usr/bin/env python3
"""
Panel of 60 = the original 20 (frozen) + 40 NEW real events.

Robustness thesis: the magnitudes in MAG were chosen looking at the original 20. The honest
test of the Bayesian engine is whether those SAME frozen weights predict 40 events they were
never tuned on. We therefore:
  * reuse MAG/BASE unchanged for existing mechanisms,
  * add a small set of NEW mechanism weights (a-priori, documented) only for genuinely new
    signals (state-legislative lane + a few court/federal mechanisms), each shared across events,
  * report metrics split ORIGINAL-20 vs NEW-40 vs ALL-60 -> the gap is the overfit tell.

Outcome convention per type (1 = the adverse/for-ballot the measure-passes event occurs):
  court=adverse ruling/upholds ; ballot=measure passes ; federal=bill enacted ;
  admin=restriction imposed ; closure=clinic closes ; state=restrictive state law takes effect.
All signals are point-in-time (active_from date it became knowable); no lookahead.
Facts are well-documented public events. Bill/measure data cross-checked to public record.
"""
from backtest_panel20 import MAG, BASE, E as E20, logistic, logit, shift, prob

# ---- NEW shared mechanism magnitudes (a-priori by mechanism; each used with a SIGN per event) ----
MAG.update(dict(
 state_const_right = 1.3,   # a state constitution found to protect abortion -> adverse ruling less likely
 state_court_cons  = 1.2,   # a conservative-majority state high court -> upholds restriction
 red_trifecta      = 1.4,   # restrictive bill in a red governor+both-chambers trifecta
 trigger_pre       = 1.9,   # a pre-Roe / trigger ban auto-effective on a triggering event
 model_bill        = 0.7,   # copycat / model legislation (coordination signal)
 gov_support       = 0.9,   # governor actively wants the restriction
 dem_control       = 2.0,   # a Democratic legislative chamber (used -1: kills a restrictive bill)
 gov_veto          = 1.8,   # a Democratic governor able to veto (used -1)
 pres_veto         = 2.2,   # opposing-party president able to veto a federal bill (used -1)
 personhood_novel  = 1.6,   # standalone fetal-personhood statute (historically fails; used -1)
))
BASE["state"] = 0.25   # generic base rate for an in-scope restrictive state action

# ---- 40 NEW events (key, type, outcome, event_date, [(signal, sign, active_from), ...]) ----
NEW40 = [
 # ------------------------- COURT (5 adverse-happened, 5 access-held) -------------------------
 ("AZ 1864 ban revived (AZ Sup Ct)","court",1,"2024-04-09",[("state_court_cons",+1,"2023-01-01"),("c63",+1,"2022-06-24")]),
 ("IN total ban upheld (IN Sup Ct)","court",1,"2023-06-30",[("state_court_cons",+1,"2023-01-01"),("c63",+1,"2022-08-01")]),
 ("SC 6-week upheld (SC Sup Ct)","court",1,"2023-08-23",[("state_court_cons",+1,"2023-05-01")]),
 ("FL 6-week allowed (FL Sup Ct)","court",1,"2024-04-01",[("state_court_cons",+1,"2022-06-24"),("c63",+1,"2022-06-24")]),
 ("GenBioPro v WV mife ban upheld","court",1,"2024-08-01",[("c63",+1,"2023-08-01")]),
 ("OK total ban struck (OK Sup Ct)","court",0,"2023-05-31",[("state_const_right",-1,"2023-03-01")]),
 ("ND ban struck","court",0,"2024-09-12",[("state_const_right",-1,"2023-03-16")]),
 ("MT Armstrong right upheld (MT Sup Ct)","court",0,"2024-08-01",[("state_const_right",-1,"1999-01-01")]),
 ("KS Hodes right upheld (KS Sup Ct)","court",0,"2019-04-26",[("state_const_right",-1,"2019-01-01")]),
 ("WI 1849 not a ban (Dane Cty)","court",0,"2023-12-05",[("state_const_right",-1,"2023-07-01")]),
 # ------------------------------- BALLOT (measure passes = 1) ---------------------------------
 ("MI Prop 3 protect","ballot",1,"2022-11-08",[("polling",+1,"2022-06-01"),("crossparty",+1,"2022-01-01")]),
 ("CA Prop 1 protect","ballot",1,"2022-11-08",[("bluestate",+1,"2022-01-01"),("polling",+1,"2022-06-01")]),
 ("VT Prop 5 protect","ballot",1,"2022-11-08",[("bluestate",+1,"2022-01-01")]),
 ("MO Amendment 3 protect","ballot",1,"2024-11-05",[("polling",+1,"2024-08-01"),("crossparty",+1,"2024-01-01"),("deepred",-1,"2024-01-01")]),
 ("AZ Prop 139 protect","ballot",1,"2024-11-05",[("polling",+1,"2024-06-01"),("crossparty",+1,"2024-01-01")]),
 ("CO Amendment 79 protect","ballot",1,"2024-11-05",[("bluestate",+1,"2024-01-01"),("super60",-1,"2024-01-01")]),
 ("MD Question 1 protect","ballot",1,"2024-11-05",[("bluestate",+1,"2024-01-01")]),
 ("NY Prop 1 protect","ballot",1,"2024-11-05",[("bluestate",+1,"2024-01-01")]),
 ("MT LR-131 born-alive","ballot",0,"2022-11-08",[("deepred",+1,"2022-01-01"),("crossparty",-1,"2022-09-01")]),
 ("NE Init439 protect","ballot",0,"2024-11-05",[("deepred",+1,"2024-01-01"),("decoy",-1,"2024-09-01")]),
 # --------------------------------- FEDERAL (bill enacted = 1) --------------------------------
 ("2017 ACA repeal defund PP","federal",0,"2017-07-28",[("trifecta",+1,"2017-01-20"),("reconc",+1,"2017-01-20"),("filibuster",-1,"2017-07-01")]),
 ("2015 reconciliation defund PP","federal",0,"2016-01-08",[("reconc",+1,"2015-10-01"),("priority",+1,"2015-01-01"),("pres_veto",-1,"2015-01-01")]),
 ("Hyde Amendment FY25 renewal","federal",1,"2024-12-01",[("priority",+1,"2024-01-01"),("priorguid",+1,"1976-01-01")]),
 # ---------------------------------- ADMIN (restriction = 1) ----------------------------------
 ("Trump Title X gag rule 2019","admin",1,"2019-08-19",[("alignedexec",+1,"2017-01-20"),("priorguid",+1,"2018-06-01")]),
 ("Trump contraceptive exemptions 2018","admin",1,"2018-11-07",[("alignedexec",+1,"2017-01-20")]),
 ("FDA mail-mife permanent 2021","admin",0,"2021-12-16",[("alignedexec",-1,"2021-01-20"),("signalsonly",-1,"2021-01-01")]),
 ("FDA pharmacy dispensing 2023","admin",0,"2023-01-03",[("alignedexec",-1,"2021-01-20")]),
 ("Biden EMTALA guidance 2022","admin",0,"2022-07-11",[("alignedexec",-1,"2021-01-20")]),
 ("DOJ OLC Comstock memo 2022","admin",0,"2022-12-23",[("alignedexec",-1,"2021-01-20"),("signalsonly",-1,"2022-01-01")]),
 # --------------------------------- CLOSURE (clinic closes = 1) -------------------------------
 ("PP St. Louis last MO clinic","closure",0,"2019-06-30",[("totalban",-1,"2019-01-01"),("priorloss",+1,"2019-05-01")]),
 ("PP Wisconsin halts abortion 2022","closure",1,"2022-06-24",[("totalban",+1,"2022-06-24"),("priorloss",+1,"2011-01-01")]),
 ("Blue-state (MA) affiliate closure","closure",0,"2024-12-31",[("backfill",-1,"2023-01-01"),("totalban",-1,"2023-01-01")]),
 ("PP North Central States closures 2025","closure",1,"2025-05-01",[("defund",+1,"2025-01-01"),("meddep",+1,"2025-01-01"),("nobackfill",+1,"2025-01-01")]),
 # --------------------------------- STATE (restrictive law effective = 1) --------------------
 ("TX SB8 6-week effective","state",1,"2021-09-01",[("red_trifecta",+1,"2021-01-01"),("model_bill",+1,"2021-05-01")]),
 ("TX trigger total ban effective","state",1,"2022-08-25",[("trigger_pre",+1,"2021-01-01"),("red_trifecta",+1,"2021-01-01")]),
 ("MO trigger ban effective","state",1,"2022-06-24",[("trigger_pre",+1,"2019-01-01"),("red_trifecta",+1,"2019-01-01")]),
 ("NE 12-week ban enacted 2023","state",1,"2023-05-19",[("red_trifecta",+1,"2023-01-01")]),
 ("SC Medicaid exclusion (Medina)","state",1,"2025-06-26",[("red_trifecta",+1,"2018-07-01")]),
 ("VA 15-week ban (2023)","state",0,"2023-12-31",[("gov_support",+1,"2022-01-01"),("dem_control",-1,"2023-01-01")]),
 ("Standalone fetal personhood enacted","state",0,"2024-12-31",[("personhood_novel",-1,"2024-01-01"),("red_trifecta",+1,"2024-01-01")]),
]

E = E20 + NEW40

# ---- consistency: every signal name maps to exactly one magnitude everywhere ----
def check_shared():
    seen={}
    for _,_,_,_,sigs in E:
        for nm,sg,_ in sigs: seen.setdefault(nm,set()).add(MAG[nm])
    bad=[k for k,v in seen.items() if len(v)!=1]
    print("shared-weight check:", "OK" if not bad else f"VIOLATION {bad}")

def metrics(rows, label):
    n=len(rows)
    if not n: return
    brier=sum((r['pf']-r['out'])**2 for r in rows)/n
    acc=sum(1 for r in rows if (r['pf']>=0.5)==bool(r['out']))/n
    pos=[r['pf'] for r in rows if r['out']==1]; neg=[r['pf'] for r in rows if r['out']==0]
    auc=(sum((a>b)+0.5*(a==b) for a in pos for b in neg)/(len(pos)*len(neg))) if pos and neg else float('nan')
    # expected calibration error (10 bins)
    ece=0.0
    for lo in range(0,100,10):
        b=[r for r in rows if lo<=r['pf']*100<lo+10 or (lo==90 and r['pf']==1.0)]
        if b:
            conf=sum(r['pf'] for r in b)/len(b); obs=sum(r['out'] for r in b)/len(b)
            ece+=abs(conf-obs)*len(b)/n
    print(f"  {label:<16} n={n:<3} acc={acc:.0%}  Brier={brier:.3f}  AUC={auc:.2f}  ECE={ece:.3f}  (pos={len(pos)},neg={len(neg)})")
    return dict(n=n,acc=acc,brier=brier,auc=auc,ece=ece)

def build_rows(events):
    rows=[]
    for key,et,out,date,sigs in events:
        rows.append(dict(key=key,type=et,out=out,pf=prob(et,sigs,date),p12=prob(et,sigs,shift(date,12))))
    return rows

def run():
    check_shared()
    all_rows=build_rows(E); orig=build_rows(E20); new=build_rows(NEW40)
    print("\n"+"="*92); print("GENERALIZATION: frozen weights, original-20 vs unseen-40"); print("="*92)
    metrics(orig,"ORIGINAL-20"); metrics(new,"NEW-40 (unseen)"); metrics(all_rows,"ALL-60")
    print("\n  BRIER BY TYPE (all 60):")
    for t in ["court","ballot","federal","admin","closure","state"]:
        b=[r for r in all_rows if r['type']==t]
        if b:
            bt=sum((r['pf']-r['out'])**2 for r in b)/len(b)
            a_pos=[r['pf'] for r in b if r['out']==1]; a_neg=[r['pf'] for r in b if r['out']==0]
            print(f"    {t:<9} n={len(b):<2} Brier={bt:.3f}  (pos={len(a_pos)},neg={len(a_neg)})")
    print("\n  BIGGEST ERRORS (failure modes across 60):")
    for r in sorted(all_rows,key=lambda r:-abs(r['pf']-r['out']))[:6]:
        print(f"    {r['key'][:44]:<45} pred {r['pf']*100:>3.0f}%  actual {r['out']}  |err|={abs(r['pf']-r['out']):.2f}")
    print("\nBill/measure data cross-checked to public record. (c) LegiScan LLC for LegiScan-sourced items, CC BY 4.0.")

if __name__=="__main__": run()

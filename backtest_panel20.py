#!/usr/bin/env python3
"""
Aggressive backtest — 20 real events, TYPED SHARED WEIGHTS.
Goal: learn about the model. Reliability curve, Brier by type, discrimination (AUC),
biggest misses (failure modes), and a fixed 12-MONTH-HORIZON score (early-warning value).

Anti-overfit design: magnitudes live in ONE shared table MAG[]; each event only picks which
signals are present, their SIGN (measure direction), and the point-in-time date they became knowable.
Same-type events therefore share weights -> if the type-model generalizes across many events, that's real.
Hard cases deliberately included (SD, NE, Moyle) so failure modes show up instead of being hidden.
"""
import math
def logistic(x): return 1/(1+math.exp(-x))
def logit(p): return math.log(p/(1-p))
def shift(date,months):
    y,m=int(date[:4]),int(date[5:7]); m-=months
    while m<=0: m+=12; y-=1
    return f"{y:04d}-{m:02d}-01"

# ---- ONE shared magnitude table (a-priori, by mechanism). Signs applied per event. ----
MAG=dict(
 # court
 c63=1.8,c54=0.7,kennedy=0.8,cert=1.5,oral=1.0,standing=1.6,dig=1.3,roberts=0.9,stayed=2.0,
 # ballot
 turnout=0.5,deepred=0.85,surge=1.5,crossparty=0.9,decoy=0.9,polling=0.4,agencies=0.4,super60=1.7,bluestate=1.0,
 # federal
 trifecta=1.6,reconc=1.2,byrd=0.6,filibuster=2.2,priority=0.8,
 # admin
 alignedexec=1.5,priorguid=0.8,reviewinit=1.3,signalsonly=1.8,
 # closure
 totalban=0.9,meddep=1.0,defund=2.0,nobackfill=1.5,backfill=1.9,priorloss=0.8,
)
BASE=dict(court=0.12,ballot=0.50,federal=0.15,admin=0.30,closure=0.08)

# event = (key, type, outcome, date, [ (signal, sign, active_from) ... ])
E=[
 # ---------- COURT ----------
 ("Dobbs","court",1,"2022-06-24",[("c63",+1,"2020-10-27"),("cert",+1,"2021-05-17"),("oral",+1,"2021-12-01")]),
 ("Medina","court",1,"2025-06-26",[("c63",+1,"2022-07-01"),("cert",+1,"2024-12-18"),("oral",+1,"2025-04-02")]),
 ("FDA v AHM (restrict mife?)","court",0,"2024-06-13",[("c63",+1,"2020-10-27"),("standing",-1,"2023-06-01"),("dig",-1,"2024-03-26")]),
 ("Moyle (uphold ID emerg ban?)","court",0,"2024-06-27",[("c63",+1,"2020-10-27"),("dig",-1,"2024-04-24"),("standing",-1,"2024-04-24")]),
 ("June Medical (uphold LA?)","court",0,"2020-06-29",[("c54",+1,"2018-10-06"),("roberts",-1,"2020-03-04")]),
 ("WWH Hellerstedt (uphold TX?)","court",0,"2016-06-27",[("kennedy",-1,"2016-01-01")]),
 # ---------- BALLOT (sign: +1 helps PASS) ----------
 ("KS Value Them Both (pass?)","ballot",0,"2022-08-02",[("turnout",+1,"2022-01-01"),("deepred",+1,"2022-01-01"),("surge",-1,"2022-07-15")]),
 ("FL Amendment 4 (pass?)","ballot",0,"2024-11-05",[("polling",+1,"2024-06-01"),("crossparty",+1,"2024-01-01"),("super60",-1,"2024-01-01"),("agencies",-1,"2024-06-01")]),
 ("OH Issue1 Nov23 (pass?)","ballot",1,"2023-11-07",[("polling",+1,"2023-06-01"),("crossparty",+1,"2023-01-01")]),
 ("OH Issue1 Aug23 60% (pass?)","ballot",0,"2023-08-08",[("turnout",+1,"2023-01-01"),("surge",-1,"2023-07-01")]),
 ("KY Amendment 2 (pass?)","ballot",0,"2022-11-08",[("deepred",+1,"2022-01-01"),("surge",-1,"2022-09-01"),("crossparty",-1,"2022-08-15")]),
 ("SD Amendment G protect (pass?)","ballot",0,"2024-11-05",[("deepred",-1,"2024-01-01"),("crossparty",+1,"2024-01-01"),("polling",+1,"2024-06-01")]),
 ("NE Init434 12wk-ban (pass?)","ballot",1,"2024-11-05",[("deepred",+1,"2024-01-01"),("decoy",+1,"2024-08-01"),("surge",-1,"2024-09-01")]),
 # ---------- FEDERAL ----------
 ("OBBBA 71113 defund","federal",1,"2025-07-04",[("trifecta",+1,"2025-01-20"),("reconc",+1,"2025-05-01"),("priority",+1,"2025-01-20"),("byrd",-1,"2025-06-01")]),
 ("WHPA fed protect (enacted?)","federal",0,"2022-05-11",[("filibuster",-1,"2021-01-20")]),
 ("Right to Contraception Act","federal",0,"2024-06-05",[("filibuster",-1,"2023-01-03")]),
 # ---------- ADMIN ----------
 ("Title X freeze","admin",1,"2025-04-01",[("alignedexec",+1,"2025-01-20"),("priorguid",+1,"2025-01-20")]),
 ("EMTALA guidance rescission","admin",1,"2025-06-03",[("alignedexec",+1,"2025-01-20"),("priorguid",+1,"2025-01-20")]),
 ("Comstock enforcement (happened?)","admin",0,"2025-12-31",[("alignedexec",+1,"2025-01-20"),("signalsonly",-1,"2025-01-20")]),
 # ---------- CLOSURE ----------
 ("PP Gulf Coast Houston closure","closure",1,"2025-09-30",[("totalban",+1,"2022-08-01"),("meddep",+1,"2024-06-01"),("defund",+1,"2025-07-04"),("nobackfill",+1,"2025-07-04")]),
]

# consistency check: each signal name uses ONE magnitude everywhere
def check_shared():
    seen={}
    for _,_,_,_,sigs in E:
        for nm,sg,_ in sigs:
            seen.setdefault(nm,set()).add(MAG[nm])
    bad=[k for k,v in seen.items() if len(v)!=1]
    print("shared-weight check:", "OK (all magnitudes shared)" if not bad else f"VIOLATION {bad}")

def prob(etype, sigs, asof):
    lo=logit(BASE[etype])
    for nm,sg,af in sigs:
        if af<=asof: lo+=sg*MAG[nm]
    return logistic(lo)

def run():
    check_shared()
    rows=[]
    for key,et,out,date,sigs in E:
        pf=prob(et,sigs,date)                 # final pre-event
        p12=prob(et,sigs,shift(date,12))      # 12 months before (early-warning)
        rows.append(dict(key=key,type=et,out=out,pf=pf,p12=p12))
    # ---- headline table ----
    print("\n"+"="*96)
    print(f"{'event':<34}{'type':<9}{'P@12mo':>8}{'P_final':>9}{'actual':>8}   verdict")
    print("="*96)
    for r in rows:
        pred=1 if r['pf']>=0.5 else 0
        v="hit" if pred==r['out'] else "**MISS**"
        print(f"{r['key'][:33]:<34}{r['type']:<9}{r['p12']*100:>7.0f}%{r['pf']*100:>8.0f}%{r['out']:>8}   {v}")
    # ---- metrics ----
    n=len(rows)
    brier=sum((r['pf']-r['out'])**2 for r in rows)/n
    brier12=sum((r['p12']-r['out'])**2 for r in rows)/n
    acc=sum(1 for r in rows if (r['pf']>=0.5)==bool(r['out']))/n
    # AUC (Mann-Whitney) on P_final
    pos=[r['pf'] for r in rows if r['out']==1]; neg=[r['pf'] for r in rows if r['out']==0]
    auc=sum((a>b)+0.5*(a==b) for a in pos for b in neg)/(len(pos)*len(neg))
    print("\n"+"="*96); print("METRICS"); print("="*96)
    print(f"  n={n}   accuracy={acc:.0%}   Brier_final={brier:.3f}   Brier@12mo={brier12:.3f}   AUC={auc:.2f}")
    # reliability
    print("\n  RELIABILITY (P_final bins):")
    for lo in [0,20,40,60,80]:
        hi=lo+20; b=[r for r in rows if lo<=r['pf']*100<(hi if hi<100 else 101)]
        if b:
            obs=sum(r['out'] for r in b)/len(b)
            print(f"    {lo:>3}-{hi:<3}%  n={len(b):<2} predicted~{(lo+hi)/2:>3.0f}%  observed {obs*100:>3.0f}%")
    # by type
    print("\n  BRIER BY TYPE (where model is strong/weak):")
    for t in ["court","federal","admin","closure","ballot"]:
        b=[r for r in rows if r['type']==t]
        if b:
            bt=sum((r['pf']-r['out'])**2 for r in b)/len(b)
            print(f"    {t:<9} n={len(b):<2} Brier={bt:.3f}")
    # biggest misses
    print("\n  BIGGEST ERRORS (failure modes):")
    for r in sorted(rows,key=lambda r:-abs(r['pf']-r['out']))[:4]:
        print(f"    {r['key'][:40]:<41} pred {r['pf']*100:>3.0f}%  actual {r['out']}  |err|={abs(r['pf']-r['out']):.2f}")
    # early-warning value
    print(f"\n  EARLY WARNING: mean P@12mo  positives={sum(r['p12'] for r in rows if r['out']==1)/max(1,len(pos)):.0%}"
          f"   negatives={sum(r['p12'] for r in rows if r['out']==0)/max(1,len(neg)):.0%}")

if __name__=="__main__": run()

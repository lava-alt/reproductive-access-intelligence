#!/usr/bin/env python3
"""
E1  Per-lane scale (gamma) fit by leave-one-out CV log-loss, with a shrinkage prior at gamma=1.
E2  Per-lane Brier decomposition into bias (reliability) vs discrimination (resolution).

Why this shape: our weights are a-priori (not fit from data), so the ONLY free parameter is the
log-odds scale gamma. LOO is honest because each held-out event's gamma is chosen WITHOUT it.
A shrinkage prior (strength k) pulls noisy small lanes back toward gamma=1 so a 5-event lane
cannot pick a wild scale. We select gamma by log-loss (proper) not Brier (which just rewards
extremity), per the calibration + forecasting literature.
"""
import math
from backtest_panel60 import E, E20, NEW40, MAG, BASE, logit, logistic, shift

LANES=["court","ballot","federal","admin","closure","state"]
GRID=[round(0.6+0.05*i,2) for i in range(0,39)]  # 0.60 .. 2.50
PRIOR_K=3.0   # shrinkage strength toward gamma=1 (in pseudo-observations of loss)

def clip(p,e=1e-6): return min(1-e,max(e,p))
def pscaled(et,sigs,asof,g): return logistic(logit(BASE[et]) + g*sum(sg*MAG[nm] for nm,sg,af in sigs if af<=asof))
def logloss(y,p): p=clip(p); return -(y*math.log(p)+(1-y)*math.log(1-p))
def brier(y,p): return (p-y)**2

def rows_for(events):
    return [(k,et,o,d,s) for k,et,o,d,s in events]

def fit_gamma(events, prior_k=PRIOR_K):
    """gamma minimizing mean log-loss + shrinkage penalty k*(g-1)^2/n."""
    n=len(events); best=(1.0,9e9)
    for g in GRID:
        L=sum(logloss(o, pscaled(et,s,d,g)) for _,et,o,d,s in events)/n + prior_k*(g-1)**2/n
        if L<best[1]: best=(g,L)
    return best[0]

def loo_metric(events, g_mode="fit"):
    """LOO log-loss & Brier. g_mode: 'one'=gamma1, 'global'=one gamma fit on rest,
    'lane'=gamma fit on the same-lane rest (falls back to global if lane too small)."""
    ll=bs=0.0; n=len(events)
    for i,(k,et,o,d,s) in enumerate(events):
        rest=[e for j,e in enumerate(events) if j!=i]
        if g_mode=="one": g=1.0
        elif g_mode=="global": g=fit_gamma(rest)
        else:
            lane_rest=[e for e in rest if e[1]==et]
            g=fit_gamma(lane_rest) if len(lane_rest)>=4 else fit_gamma(rest)
        p=pscaled(et,s,d,g); ll+=logloss(o,p); bs+=brier(o,p)
    return ll/n, bs/n

def e1():
    print("="*84); print("E1  PER-LANE SCALE FIT (LOO-CV log-loss, shrinkage prior at gamma=1)"); print("="*84)
    print("  full-panel gamma per lane (fit on all lane events, shrunk):")
    for lane in LANES:
        ev=[e for e in E if e[1]==lane]
        g=fit_gamma(ev)
        # plateau: loss at g vs at 1.0 and at g+-0.3
        base=sum(logloss(o,pscaled(et,s,d,1.0)) for _,et,o,d,s in ev)/len(ev)
        fit =sum(logloss(o,pscaled(et,s,d,g))   for _,et,o,d,s in ev)/len(ev)
        print(f"    {lane:<9} n={len(ev):<2}  gamma*={g:<4}  logloss 1.0->{base:.3f}  gamma*->{fit:.3f}  gain={base-fit:+.3f}")
    g_all=fit_gamma(E)
    print(f"  GLOBAL gamma* (all 60) = {g_all}  (our adopted lambda=1.2 for reference)")
    print("\n  Honest generalization (LOO over all 60):")
    for mode,lab in (("one","gamma=1.0 (no scaling)"),("global","one global gamma (CV)"),("lane","per-lane gamma (CV)")):
        ll,bs=loo_metric(E,mode)
        print(f"    {lab:<26} LOO log-loss={ll:.3f}  LOO Brier={bs:.3f}")

def e2():
    print("\n"+"="*84); print("E2  BRIER DECOMPOSITION  (bias=reliability defect, sep=resolution) per lane"); print("="*84)
    print(f"    {'lane':<9}{'n':>3}{'baserate':>10}{'mean_p':>9}{'bias':>8}{'sep(pos-neg)':>14}{'Brier':>8}   read")
    for lane in LANES:
        ev=[e for e in E if e[1]==lane]
        ys=[o for _,_,o,_,_ in ev]; ps=[pscaled(et,s,d,1.0) for _,et,o,d,s in ev]
        n=len(ev); base=sum(ys)/n; mp=sum(ps)/n; bias=mp-base
        pos=[p for p,y in zip(ps,ys) if y==1]; neg=[p for p,y in zip(ps,ys) if y==0]
        sep=(sum(pos)/len(pos)-sum(neg)/len(neg)) if pos and neg else float('nan')
        bs=sum((p-y)**2 for p,y in zip(ps,ys))/n
        if sep!=sep: read="no pos or neg"
        elif abs(bias)>0.12: read=("UNDER-conf (raise gamma)" if bias<0 else "OVER-conf (lower gamma)")
        elif sep<0.25: read="LOW RESOLUTION -> needs FEATURES, not scaling"
        else: read="ok"
        sepstr=f"{sep:+.2f}" if sep==sep else "  n/a"
        print(f"    {lane:<9}{n:>3}{base:>10.2f}{mp:>9.2f}{bias:>+8.2f}{sepstr:>14}{bs:>8.3f}   {read}")
    print("\n  bias<0 = under-confident (scaling helps). low sep = poor separation (features needed, scaling won't help).")

if __name__=="__main__":
    e1(); e2()

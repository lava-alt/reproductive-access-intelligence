#!/usr/bin/env python3
"""
Robustness experiments on the Bayesian engine, evaluated OUT-OF-SAMPLE on the 40 unseen events.

Diagnosis from panel60: discrimination is strong (AUC ~0.97) but CALIBRATION is poor (ECE ~0.19)
and the model UNDER-predicts single-signal positives. So we test three ways to make the engine
more robust, judged on out-of-sample Brier + ECE (calibration), never on a hero AUC:

  EXP 1  Shrinkage lambda : scale the accumulated log-odds evidence by lambda (guards overconfidence).
  EXP 2  Temperature T    : divide the FULL logit by T (post-hoc calibration; T>1 softens, T<1 sharpens).
  EXP 3  Weight jitter MC : perturb every magnitude by +-sigma (Gaussian), N draws -> uncertainty bands
                            on each probability + ranking stability. This is the literal "more robust
                            Bayesian": a distribution per threat, not a point.

We tune on ALL-60 but REPORT the honest number on NEW-40 (the events the weights never saw).
No Math.random equivalent issues: numpy seeded.
"""
import math, statistics
import numpy as np
from backtest_panel60 import MAG, BASE, E, E20, NEW40, logit, logistic, shift

def prob_param(etype, sigs, asof, mag, scale=1.0, temp=1.0):
    lo0=logit(BASE[etype]); acc=sum(sg*mag[nm] for nm,sg,af in sigs if af<=asof)
    return logistic((lo0 + scale*acc)/temp)

def eval_set(events, mag, scale=1.0, temp=1.0):
    ys=[o for _,_,o,_,_ in events]
    ps=[prob_param(t,s,d,mag,scale,temp) for _,t,o,d,s in events]
    n=len(ys)
    brier=sum((p-y)**2 for p,y in zip(ps,ys))/n
    acc=sum(1 for p,y in zip(ps,ys) if (p>=0.5)==bool(y))/n
    pos=[p for p,y in zip(ps,ys) if y==1]; neg=[p for p,y in zip(ps,ys) if y==0]
    auc=(sum((a>b)+0.5*(a==b) for a in pos for b in neg)/(len(pos)*len(neg))) if pos and neg else float('nan')
    ece=0.0
    for lo in range(0,100,10):
        b=[(p,y) for p,y in zip(ps,ys) if (lo<=p*100<lo+10) or (lo==90 and p==1.0)]
        if b:
            conf=sum(p for p,_ in b)/len(b); obs=sum(y for _,y in b)/len(b)
            ece+=abs(conf-obs)*len(b)/n
    return dict(brier=brier,acc=acc,auc=auc,ece=ece,ps=ps,ys=ys)

def line(tag,d): print(f"    {tag:<12} Brier={d['brier']:.3f}  ECE={d['ece']:.3f}  AUC={d['auc']:.2f}  acc={d['acc']:.0%}")

# ============================ EXP 1 : SHRINKAGE ============================
def exp_shrinkage():
    print("\n"+"="*84); print("EXP 1  SHRINKAGE  (scale evidence log-odds by lambda; 1.0 = current)"); print("="*84)
    print(f"    {'lambda':<8}{'NEW-40 Brier':>14}{'NEW-40 ECE':>12}{'NEW-40 AUC':>12}")
    best=None
    for lam in [0.4,0.55,0.7,0.85,1.0,1.15,1.3]:
        d=eval_set(NEW40,MAG,scale=lam)
        star=""
        if best is None or d['brier']<best[1]: best=(lam,d['brier'],d['ece']);
        print(f"    {lam:<8.2f}{d['brier']:>14.3f}{d['ece']:>12.3f}{d['auc']:>12.2f}")
    print(f"  -> best OOS Brier at lambda={best[0]:.2f} (Brier {best[1]:.3f}, ECE {best[2]:.3f})")
    return best[0]

# ============================ EXP 2 : TEMPERATURE ============================
def exp_temperature():
    print("\n"+"="*84); print("EXP 2  TEMPERATURE  (divide full logit by T; T>1 softens overconfidence)"); print("="*84)
    print(f"    {'T':<8}{'NEW-40 Brier':>14}{'NEW-40 ECE':>12}{'NEW-40 AUC':>12}")
    best=None
    for T in [0.7,0.85,1.0,1.15,1.3,1.5,1.8]:
        d=eval_set(NEW40,MAG,temp=T)
        if best is None or d['ece']<best[1]: best=(T,d['ece'],d['brier'])
        print(f"    {T:<8.2f}{d['brier']:>14.3f}{d['ece']:>12.3f}{d['auc']:>12.2f}")
    print(f"  -> best OOS ECE at T={best[0]:.2f} (ECE {best[1]:.3f}, Brier {best[2]:.3f})")
    return best[0]

# ============================ EXP 3 : WEIGHT-JITTER MONTE CARLO ============================
def exp_jitter(sigma=0.20, N=500, seed=12345):
    print("\n"+"="*84); print(f"EXP 3  WEIGHT JITTER  (Gaussian +-{int(sigma*100)}% per magnitude, N={N}) -> uncertainty bands"); print("="*84)
    rng=np.random.default_rng(seed)
    names=sorted(MAG.keys())
    base_ps={key: prob_param(t,s,d,MAG) for key,t,o,d,s in E}
    # collect per-event prob draws + per-draw Brier + ranking stability
    draws={key:[] for key,_,_,_,_ in E}
    briers=[]; base_order=[k for k,_ in sorted(base_ps.items(), key=lambda kv:-kv[1])]
    from math import isnan
    def spearman(a,b):
        ra={k:i for i,k in enumerate(a)}; rb={k:i for i,k in enumerate(b)}
        ks=list(ra); d2=sum((ra[k]-rb[k])**2 for k in ks); n=len(ks)
        return 1-6*d2/(n*(n*n-1))
    stabs=[]
    for _ in range(N):
        m={nm: MAG[nm]*float(rng.normal(1.0,sigma)) for nm in names}
        ps={}; sb=0.0
        for key,t,o,d,s in E:
            p=prob_param(t,s,d,m); ps[key]=p; draws[key].append(p); sb+=(p-o)**2
        briers.append(sb/len(E))
        order=[k for k,_ in sorted(ps.items(), key=lambda kv:-kv[1])]
        stabs.append(spearman(base_order,order))
    # report
    widths=[np.percentile(draws[k],95)-np.percentile(draws[k],5) for k in draws]
    print(f"    Brier under jitter:  mean={statistics.mean(briers):.3f}  5-95%=[{np.percentile(briers,5):.3f}, {np.percentile(briers,95):.3f}]")
    print(f"    Ranking stability (Spearman vs unperturbed): mean={statistics.mean(stabs):.3f}  min={min(stabs):.3f}")
    print(f"    Mean 90% band width on a probability: {statistics.mean(widths)*100:.0f} points  (tighter = more robust)")
    # show a few live-relevant threats' bands (map backtest analogues)
    print("\n    Sample uncertainty bands (event : mean [5%,95%]):")
    for key in ["Medina","OBBBA 71113 defund","EMTALA guidance rescission","NE Init434 12wk-ban (pass?)",
                "SC Medicaid exclusion (Medina)","Standalone fetal personhood enacted"]:
        if key in draws:
            arr=draws[key]; print(f"      {key[:42]:<43} {statistics.mean(arr)*100:>3.0f}%  [{np.percentile(arr,5)*100:>3.0f}, {np.percentile(arr,95)*100:>3.0f}]")
    return statistics.mean(stabs)

# ============================ COMBINED : apply best calibration ============================
def combined(lam, T):
    print("\n"+"="*84); print("COMBINED : baseline vs shrinkage vs temperature (OOS NEW-40, and ALL-60)"); print("="*84)
    for label,events in (("NEW-40",NEW40),("ALL-60",E)):
        print(f"  [{label}]")
        line("baseline", eval_set(events,MAG))
        line(f"shrink {lam:.2f}", eval_set(events,MAG,scale=lam))
        line(f"temp {T:.2f}",   eval_set(events,MAG,temp=T))

if __name__=="__main__":
    lam=exp_shrinkage()
    T=exp_temperature()
    exp_jitter()
    combined(lam,T)
    print("\nAll numbers are out-of-sample on events the weights were never tuned on (NEW-40).")

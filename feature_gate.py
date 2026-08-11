#!/usr/bin/env python3
"""
INCLUSION GATE — the reusable mini-experiment every candidate feature/signal/data-type must pass
before it enters the production model. Same held-out discipline as round5_gate, generalized.

Rule (precision-first, do-no-harm): a candidate is INCLUDED only if, evaluated OUT-OF-SAMPLE (LOO),
it (1) improves global log-loss by more than the noise margin, and (2) does NOT worsen any single
lane's Brier beyond a small tolerance. Otherwise it stays out. This stops us bolting on features
that look good in-sample but overfit or help one lane while quietly hurting another.

A candidate is a function candidate(event) -> float. The gate fits ONE weight for it by LOO
(holding the existing glass-box weights fixed), so inclusion is a single interpretable parameter.
"""
import math, statistics
from backtest_panel60 import E, MAG, BASE, logit, logistic
GAIN=1.2
LANES=["court","ballot","federal","admin","closure","state"]
def clip(p,e=1e-6): return min(1-e,max(e,p))
def logloss(y,p): p=clip(p); return -(y*math.log(p)+(1-y)*math.log(1-p))
def base_logodds(et,sigs): return logit(BASE[et]) + GAIN*sum(sg*MAG[nm] for nm,sg,af in sigs)

def _feat_vals(events, cand):
    raw=[cand(e) for e in events]
    mu=statistics.mean(raw); sd=statistics.pstdev(raw) or 1.0
    return [(v-mu)/sd for v in raw]   # standardized so weights are comparable

WGRID=[round(-2.0+0.2*i,2) for i in range(0,21)]   # -2.0 .. 2.0
def _fit_w(idx_train, base_lo, feats, ys, prior_k=2.0):
    n=len(idx_train); best=(0.0,9e9)
    for w in WGRID:
        L=sum(logloss(ys[i], logistic(base_lo[i]+w*feats[i])) for i in idx_train)/n + prior_k*w*w/n
        if L<best[1]: best=(w,L)
    return best[0]

def gate(cand, name, margin=0.005, lane_tol=0.02, events=None):
    events=list(events if events is not None else E); n=len(events)
    base_lo=[base_logodds(et,s) for _,et,_,_,s in events]
    feats=_feat_vals(events, cand)
    ys=[o for _,_,o,_,_ in events]; lanes=[et for _,et,_,_,_ in events]
    # LOO: baseline (w=0) vs candidate (w fit on the other 59)
    base_ll=base_bs=cand_ll=cand_bs=0.0
    lane_base={l:[] for l in LANES}; lane_cand={l:[] for l in LANES}; wfits=[]
    for i in range(n):
        tr=[j for j in range(n) if j!=i]
        pb=logistic(base_lo[i])
        w=_fit_w(tr, base_lo, feats, ys); wfits.append(w)
        pc=logistic(base_lo[i]+w*feats[i])
        base_ll+=logloss(ys[i],pb); base_bs+=(pb-ys[i])**2
        cand_ll+=logloss(ys[i],pc); cand_bs+=(pc-ys[i])**2
        lane_base[lanes[i]].append((pb-ys[i])**2); lane_cand[lanes[i]].append((pc-ys[i])**2)
    base_ll/=n; base_bs/=n; cand_ll/=n; cand_bs/=n
    dll=base_ll-cand_ll   # positive = candidate improves log-loss
    # lane check
    regressions=[]
    for l in LANES:
        if lane_base[l]:
            b=statistics.mean(lane_base[l]); c=statistics.mean(lane_cand[l])
            if c-b>lane_tol: regressions.append((l, c-b))
    verdict = "INCLUDE" if (dll>margin and not regressions) else "REJECT"
    print("="*84); print(f"INCLUSION GATE  candidate = {name}"); print("="*84)
    print(f"  mean LOO |w| = {statistics.mean(abs(x) for x in wfits):.2f}  (near 0 = feature carries little signal)")
    print(f"  LOO log-loss  baseline={base_ll:.3f}  +candidate={cand_ll:.3f}  delta={dll:+.3f}  (want > +{margin})")
    print(f"  LOO Brier     baseline={base_bs:.3f}  +candidate={cand_bs:.3f}  delta={base_bs-cand_bs:+.3f}")
    if regressions:
        print("  LANE REGRESSIONS (candidate hurt these > tol):")
        for l,d in regressions: print(f"    {l}: Brier +{d:.3f}")
    else:
        print("  no lane regressed beyond tolerance")
    print(f"  VERDICT: {verdict}\n")
    return verdict

# ---------------- demo candidates (computable from what we already have) ----------------
def post_dobbs(e):
    _,_,_,d,_=e; return 1.0 if d>="2022-06-24" else 0.0     # regime-shift indicator
def signal_count(e):
    _,_,_,_,s=e; return float(len(s))                        # how many signals fired
def net_signal(e):
    _,et,_,_,s=e; return sum(sg for _,sg,_ in s)             # net restrictive direction

if __name__=="__main__":
    print("Demonstrating the gate on candidate features derivable from current data.\n")
    gate(post_dobbs,  "post-Dobbs regime indicator (date >= 2022-06-24)")
    gate(signal_count,"signal count (how many signals fired)")
    gate(net_signal,  "net signal direction (sum of signs)")
    print("Interpretation: only candidates that pass BOTH tests (global gain + no lane harm) enter the model.")

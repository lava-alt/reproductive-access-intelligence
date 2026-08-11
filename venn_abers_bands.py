#!/usr/bin/env python3
"""
E3  Venn-Abers predictors -> finite-sample-calibrated probability INTERVALS per event.
Pure-python (PAV isotonic + leave-one-out), no sklearn/scipy. Offline.

Venn-Abers: for a test point with score s, fit isotonic calibration on the training
(score,label) pairs twice, once appending (s,0) and once appending (s,1). The two fitted
values (p0,p1) bracket a calibrated probability; the interval width is honest uncertainty
(wide where data is thin). Point estimate = p1 / (1 - p0 + p1).  Ref: Vovk & Petej 2012.

Score used = the model's calibrated prob (with the adopted lambda gain), so this wraps the
CURRENT engine. LOO so each event's interval is built without itself.
"""
import math
from backtest_panel60 import E, MAG, BASE, logit, logistic
GAIN=1.2
def pf(et,sigs,asof=None):
    acc=sum(sg*MAG[nm] for nm,sg,af in sigs)  # all signals active at event time
    return logistic(logit(BASE[et]) + min(GAIN*acc, 3.5))

def pav(vals):
    """Pool-adjacent-violators isotonic (non-decreasing), unit weights. Returns fitted list."""
    stack=[]  # [mean, count]
    for v in vals:
        stack.append([float(v),1])
        while len(stack)>=2 and stack[-2][0]>=stack[-1][0]:
            v2,c2=stack.pop(); v1,c1=stack.pop()
            stack.append([(v1*c1+v2*c2)/(c1+c2), c1+c2])
    out=[]
    for m,c in stack: out+=[m]*c
    return out

def isotonic_value_at(scores, labels, s, lab):
    """Append (s,lab), sort by score, PAV, return fitted value at the test point's slot."""
    pairs=[(sc,y,0) for sc,y in zip(scores,labels)]+[(s,lab,1)]  # tag test with 1
    pairs.sort(key=lambda t:(t[0], t[2]))          # ties: test after train
    fit=pav([y for _,y,_ in pairs])
    idx=next(i for i,(_,_,t) in enumerate(pairs) if t==1)
    return fit[idx]

def venn_abers_loo():
    events=list(E)
    scores=[pf(et,s) for _,et,_,d,s in events]
    ys=[o for _,_,o,_,_ in events]
    out=[]
    for i,(k,et,o,d,s) in enumerate(events):
        tr_s=[scores[j] for j in range(len(events)) if j!=i]
        tr_y=[ys[j] for j in range(len(events)) if j!=i]
        p0=isotonic_value_at(tr_s,tr_y,scores[i],0)
        p1=isotonic_value_at(tr_s,tr_y,scores[i],1)
        lo,hi=min(p0,p1),max(p0,p1)
        pt=p1/(1-p0+p1) if (1-p0+p1)!=0 else (lo+hi)/2
        out.append(dict(key=k,type=et,out=o,score=scores[i],lo=lo,hi=hi,pt=pt))
    return out

def run():
    rows=venn_abers_loo()
    widths=[r['hi']-r['lo'] for r in rows]
    print("="*88); print("E3  VENN-ABERS calibrated probability intervals (LOO over 60 events)"); print("="*88)
    print(f"  mean interval width = {sum(widths)/len(widths)*100:.0f} pts   (wider = more uncertain / thinner data)")
    # calibration check: bin by point estimate, observed frequency
    print("\n  CALIBRATION (Venn-Abers point vs observed, LOO):")
    for lo in [0,20,40,60,80]:
        hi=lo+20; b=[r for r in rows if lo<=r['pt']*100<(hi if hi<100 else 101)]
        if b:
            print(f"    {lo:>3}-{hi:<3}%  n={len(b):<2}  predicted~{(lo+hi)/2:>3.0f}%  observed {sum(r['out'] for r in b)/len(b)*100:>3.0f}%")
    print("\n  interval WIDTH by lane (thin lanes should be wider):")
    for lane in ["court","ballot","federal","admin","closure","state"]:
        b=[r for r in rows if r['type']==lane]
        if b: print(f"    {lane:<9} n={len(b):<2} mean width={sum(r['hi']-r['lo'] for r in b)/len(b)*100:>3.0f} pts")
    print("\n  Live-relevant events (Venn-Abers point [lo,hi]):")
    for key in ["Medina","OBBBA 71113 defund","EMTALA guidance rescission","SC Medicaid exclusion (Medina)",
                "Standalone fetal personhood enacted","NE Init434 12wk-ban (pass?)"]:
        r=next((r for r in rows if r['key']==key),None)
        if r: print(f"    {r['key'][:40]:<41} {r['pt']*100:>3.0f}%  [{r['lo']*100:>3.0f}, {r['hi']*100:>3.0f}]  (model score {r['score']*100:.0f}%)")

if __name__=="__main__": run()

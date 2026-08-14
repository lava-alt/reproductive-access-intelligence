#!/usr/bin/env python3
"""
Experiment harness for the LLM-verifier SUB-DECISIONS. Runs on the hand-labeled golden set
(stance_stress.GOLD) once .anthropic_key is set. We do NOT finalize the design until these run.

Tests, in order (each picks the winner for the next):
  A  PROMPT style     : zeroshot vs cot vs fewshot        (model=haiku, n=1)
  B  SELF-CONSISTENCY : n = 1, 3, 5 (unanimous+abstain)   (best style, haiku)
  C  MODEL tier       : haiku vs sonnet                    (best style, best n)

Metric priority for a trust tool: PRECISION on 'restrictive' (never flag a pro-access bill),
then recall, then abstain-rate (smaller review pile is better). Reports call count as cost proxy.
"""
import sys
from stance_stress import GOLD
import stance_llm as L

CALLS=[0]
_orig=L._call
def _counting(*a,**k): CALLS[0]+=1; return _orig(*a,**k)
L._call=_counting

def score(preds):   # preds: list of (verdict, gold)
    tp=fp=fn=ab=0
    for v,g in preds:
        flagged = (v=="restrictive")
        if v=="abstain": ab+=1
        if flagged and g: tp+=1
        elif flagged and not g: fp+=1
        elif not flagged and g: fn+=1
    prec=tp/(tp+fp) if tp+fp else 1.0; rec=tp/(tp+fn) if tp+fn else 0.0
    f1=2*prec*rec/(prec+rec) if prec+rec else 0
    return dict(precision=prec,recall=rec,f1=f1,abstain=ab,fp=fp,fn=fn)

def run_cfg(model,style,n):
    preds=[]
    for title,gold in GOLD:
        try: v=L.verify(title,model=model,style=style,n=n)
        except Exception as e: print("  ABORT:",e); sys.exit(1)
        preds.append((v,gold))
    return preds

def line(tag,s): print(f"   {tag:<22} precision={s['precision']:.2f}  recall={s['recall']:.2f}  F1={s['f1']:.2f}  abstain={s['abstain']}  FP={s['fp']} FN={s['fn']}")

if __name__=="__main__":
    npos=sum(g for _,g in GOLD)
    print("="*80); print(f"LLM VERIFIER SUB-DECISION EXPERIMENTS  (golden {len(GOLD)}: {npos} restrictive)"); print("="*80)

    print("\nEXP A — PROMPT STYLE (haiku, n=1)")
    res={}
    for style in ("zeroshot","cot","fewshot"):
        s=score(run_cfg("claude-haiku-4-5-20251001",style,1)); res[style]=s; line(style,s)
    best_style=max(res, key=lambda k:(res[k]['precision'],res[k]['recall']))
    print(f"   -> best style: {best_style}")

    print(f"\nEXP B — SELF-CONSISTENCY (haiku, style={best_style})")
    resn={}
    for n in (1,3,5):
        s=score(run_cfg("claude-haiku-4-5-20251001",best_style,n)); resn[n]=s; line(f"n={n}",s)
    best_n=max(resn, key=lambda k:(resn[k]['precision'],resn[k]['recall'],-resn[k]['abstain']))
    print(f"   -> best n: {best_n}")

    print(f"\nEXP C — MODEL TIER (style={best_style}, n={best_n})")
    for model,lab in (("claude-haiku-4-5-20251001","haiku-4.5"),("claude-sonnet-5","sonnet-5")):
        s=score(run_cfg(model,best_style,best_n)); line(lab,s)

    print(f"\nTotal API calls: {CALLS[0]}  (cost proxy; haiku is ~fractions of a cent each)")
    print("Recommendation = the config with precision 1.00 at the best recall and smallest abstain pile.")

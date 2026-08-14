#!/usr/bin/env python3
"""
DECISION-MAKER: over the full routed-bill population, compare the keyword Stage-2 gate
(stance_gate.is_restrictive) against the LLM verifier (winning config: Haiku 4.5, zeroshot, n=1)
and surface ONLY the disagreements. That short list is where the LLM earns its keep — or doesn't.

Cheap by construction: verify_cached caches every verdict, and we flush every FLUSH_EVERY bills,
so a re-run costs ~$0 and resumes instantly. Golden was saturated (both scored ~1.00); this is the
tail golden can't sample.
Bill data (c) LegiScan LLC (legiscan.com), CC BY 4.0.
"""
import json, os, sys
import legiscan_ingest as G
from stance_gate import is_restrictive
import stance_llm as L

_HERE=os.path.dirname(os.path.abspath(__file__))
MODEL="claude-haiku-4-5-20251001"; STYLE="zeroshot"; N=1
FLUSH_EVERY=25

def routed_bills():
    rows=json.load(open(os.path.join(_HERE,".legiscan_data.json")))
    out=[]
    for r in rows.values():
        title=r.get("title","")
        tid,_=G._route(title, r.get("relevance",100))
        if tid is None: continue                       # Stage 1: repro-relevant + routable
        out.append((r.get("state",""), r.get("bill_number",""), tid, title))
    return out

def main():
    bills=routed_bills()
    print(f"routed bills (Stage 1): {len(bills)}")
    agree=disagree=0; kw_only=[]; llm_only=[]; abstains=[]
    for i,(st,bn,tid,title) in enumerate(bills):
        kw = is_restrictive(title)
        try:
            v = L.verify_cached(title, model=MODEL, style=STYLE, n=N)
        except Exception as e:
            L.flush(); print("ABORT:", e, f"(done {i}/{len(bills)}, cache saved)"); sys.exit(1)
        llm = (v=="restrictive")
        if v=="abstain": abstains.append((st,bn,tid,title))
        if kw==llm:
            agree+=1
        else:
            disagree+=1
            (kw_only if kw and not llm else llm_only).append((st,bn,tid,v,title))
        if (i+1)%FLUSH_EVERY==0: L.flush(); print(f"  ...{i+1}/{len(bills)}  (agree {agree} / disagree {disagree})", flush=True)
    L.flush()

    print("\n"+"="*80)
    print(f"AGREE: {agree}   DISAGREE: {disagree}   ({100*disagree/max(len(bills),1):.1f}% disagreement)")
    print("="*80)
    print(f"\n[A] KEYWORD says RESTRICTIVE, LLM says NOT  ({len(kw_only)}) — keyword may over-flag / false threats")
    for st,bn,tid,v,title in sorted(kw_only):
        print(f"   {st:>2} {bn:<10} {tid:<16} LLM={v:<11} {title[:82]}")
    print(f"\n[B] LLM says RESTRICTIVE, KEYWORD says NOT  ({len(llm_only)}) — LLM catches tail keyword MISSES")
    for st,bn,tid,v,title in sorted(llm_only):
        print(f"   {st:>2} {bn:<10} {tid:<16} {title[:82]}")
    if abstains:
        print(f"\n[C] LLM ABSTAIN ({len(abstains)}) — only with n>1; empty at n=1")
        for st,bn,tid,title in sorted(abstains):
            print(f"   {st:>2} {bn:<10} {tid:<16} {title[:82]}")
    print(f"\ncache: {L.cache_stats()}")
    print("READ: [A] = bills the keyword paints as threats but the LLM clears (false-positive risk).")
    print("      [B] = real anti-access bills the keyword lists don't cover (the LLM's value).")
    print("      Small A+B and benign content -> keep keyword, $0/week. Real misses in B -> wire the LLM.")

if __name__=="__main__":
    main()

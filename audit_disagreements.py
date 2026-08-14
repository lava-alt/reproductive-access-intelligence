#!/usr/bin/env python3
"""
Safety pass: re-run the keyword-vs-LLM DISAGREEMENTS at n=3 (self-consistency + abstain).
Bills where the 3 samples disagree -> 'abstain' -> those route to human review (repro_watch)
instead of being auto-flagged. Catches the LLM's own over-flags on protective-sounding titles.

Compares n=1 (cached) vs n=3 for each disagreement and buckets the outcome.
Bill data (c) LegiScan LLC (legiscan.com), CC BY 4.0.
"""
import json, os, sys
import legiscan_ingest as G
from stance_gate import is_restrictive
import stance_llm as L

_HERE=os.path.dirname(os.path.abspath(__file__))
MODEL="claude-haiku-4-5-20251001"; STYLE="zeroshot"

def routed_bills():
    rows=json.load(open(os.path.join(_HERE,".legiscan_data.json")))
    out=[]
    for r in rows.values():
        title=r.get("title","")
        tid,_=G._route(title, r.get("relevance",100))
        if tid is None: continue
        out.append((r.get("state",""), r.get("bill_number",""), tid, title))
    return out

def main():
    bills=routed_bills()
    # find disagreements using the cached n=1 verdicts
    diffs=[]
    for st,bn,tid,title in bills:
        kw=is_restrictive(title)
        v1=L.verify_cached(title, model=MODEL, style=STYLE, n=1)  # cached, no new call
        if kw != (v1=="restrictive"):
            diffs.append((st,bn,tid,title,kw,v1))
    print(f"disagreements to re-check at n=3: {len(diffs)}")

    firmed=[]; abstained=[]; flipped=[]
    for i,(st,bn,tid,title,kw,v1) in enumerate(diffs):
        try:
            v3=L.verify_cached(title, model=MODEL, style=STYLE, n=3)  # new key -> live calls
        except Exception as e:
            L.flush(); print("ABORT:", e, f"(done {i}/{len(diffs)}, cache saved)"); sys.exit(1)
        rec=(st,bn,tid,v1,v3,title)
        if v3=="abstain": abstained.append(rec)
        elif v3==v1: firmed.append(rec)
        else: flipped.append(rec)
        if (i+1)%25==0: L.flush(); print(f"  ...{i+1}/{len(diffs)}", flush=True)
    L.flush()

    def show(rows):
        for st,bn,tid,v1,v3,title in sorted(rows):
            print(f"   {st:>2} {bn:<10} {tid:<16} n1={v1:<11} n3={v3:<11} {title[:70]}")

    print("\n"+"="*90)
    print(f"FIRMED (n3==n1, stable): {len(firmed)}   ABSTAIN (n3 disagreed internally): {len(abstained)}   FLIPPED (n3!=n1): {len(flipped)}")
    print("="*90)
    print(f"\n[ABSTAIN -> human review] ({len(abstained)}) — the genuinely ambiguous; NOT auto-flagged")
    show(abstained)
    print(f"\n[FLIPPED at n3] ({len(flipped)}) — verdict changed under self-consistency")
    show(flipped)
    # the restrictive catches that held firm at n=3 (the LLM's confident value-add)
    firm_restr=[r for r in firmed if r[4]=="restrictive"]
    print(f"\n[FIRM RESTRICTIVE] ({len(firm_restr)}) — anti-access bills keyword missed, LLM confident at n=3")
    show(firm_restr)
    print(f"\ncache: {L.cache_stats()}")

if __name__=="__main__":
    main()

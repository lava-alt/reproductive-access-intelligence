#!/usr/bin/env python3
"""
COVERAGE AUDIT — the mission test: is the net catching every relevant bill across all 50 states,
or are we silently dropping the sleeper? Runs against the live LegiScan cache.

Measures: state coverage, per-threat coverage, and the RECALL GAP (repro-relevant RESTRICTIVE
bills the router drops = potential misses). Spotlights Arizona. Proposes a catch-all so no
restrictive repro bill is dropped without a human seeing it.
Bill data (c) LegiScan LLC (legiscan.com), CC BY 4.0.
"""
import json, os
from collections import Counter, defaultdict
import legiscan_ingest as G

rows=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),".legiscan_data.json")))
ALLST=['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
       'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
       'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']
def repro(t): return any(k in (t or '').lower() for k in G.REPRO_TOKENS)

def audit():
    st_all=Counter(r.get('state') for r in rows.values())
    st_repro=Counter(r.get('state') for r in rows.values() if repro(r.get('title','')))
    print("="*88); print("1) STATE COVERAGE"); print("="*88)
    zero=[s for s in ALLST if st_all.get(s,0)==0]
    thin=[s for s in ALLST if 0<st_all.get(s,0)<=2]
    print(f"  states with cached bills: {sum(1 for s in ALLST if st_all.get(s,0))}/50")
    print(f"  ZERO-coverage states (blind spots): {zero if zero else 'none'}")
    print(f"  thin states (<=2 bills): {thin}")

    print("\n"+"="*88); print("2) PER-THREAT COVERAGE (routed)"); print("="*88)
    by=defaultdict(list)
    for r in rows.values():
        tid,_=G._route(r.get('title',''), r.get('relevance',100))
        if tid: by[tid].append(r)
    for tid in ["fda_mife","emtala","state_exclusion","comstock","personhood","state_ban","titlex"]:
        b=by.get(tid,[]); print(f"  {tid:<16} bills={len(b):<3} states={len({x.get('state') for x in b})}")

    print("\n"+"="*88); print("3) RECALL GAP — repro-relevant bills the router DROPS"); print("="*88)
    routed=dropped_restr=dropped_pro=dropped_neutral=0
    drop_by_state=Counter(); miss_examples=[]
    for r in rows.values():
        t=r.get('title','')
        if not repro(t): continue
        tid,_=G._route(t, r.get('relevance',100))
        if tid: routed+=1; continue
        stance=G._stance(t)
        drop_by_state[r.get('state')]+=1
        if stance=="restrict": dropped_restr+=1;  miss_examples.append((r.get('state'),r.get('bill_number'),t[:66]))
        elif stance=="protect": dropped_pro+=1
        else: dropped_neutral+=1
    total_repro=routed+dropped_restr+dropped_pro+dropped_neutral
    print(f"  repro-relevant total: {total_repro}")
    print(f"  routed to a threat:   {routed}  ({routed/total_repro*100:.0f}%)")
    print(f"  DROPPED restrictive:  {dropped_restr}   <-- potential MISSES (restrictive, unflagged)")
    print(f"  dropped pro-access:   {dropped_pro}   (ok to skip: not threats)")
    print(f"  dropped neutral/unclear: {dropped_neutral}   (mixed; some may be threats)")
    surfaced = routed/(routed+dropped_restr) if (routed+dropped_restr) else 0
    print(f"  >> RESTRICTIVE-bill recall (surfaced / restrictive): {surfaced*100:.0f}%  <-- the mission metric")
    print("  top states by dropped restrictive bills:")
    for s,c in drop_by_state.most_common(8): print(f"    {s}: {c}")
    print("  sample restrictive MISSES (dropped, should likely surface):")
    for s,b,t in miss_examples[:12]: print(f"    {s} {b}  {t}")

    print("\n"+"="*88); print("4) ARIZONA SPOTLIGHT (the sleeper test)"); print("="*88)
    az=[r for r in rows.values() if r.get('state')=='AZ' and repro(r.get('title',''))]
    print(f"  AZ repro bills in cache: {len(az)}")
    for r in sorted(az, key=lambda r:r.get('bill_number','')):
        tid,_=G._route(r.get('title',''), r.get('relevance',100))
        flag = tid if tid else f"DROPPED({G._stance(r.get('title',''))})"
        print(f"    {r.get('bill_number',''):<9} {flag:<22} {r.get('title','')[:56]}")

if __name__=="__main__": audit()

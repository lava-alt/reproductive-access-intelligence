#!/usr/bin/env python3
"""
COPYCAT-CAMPAIGN DETECTOR — the marquee: surface coordinated model-bill campaigns (near-identical
bills across multiple states) BEFORE any single one advances. Runs on the live LegiScan cache.

Method: normalize each repro bill title (strip state names, punctuation, boilerplate), then cluster
titles whose token sets are highly similar (Jaccard) ACROSS DIFFERENT states. A cluster spanning
>=3 states = a coordinated campaign. Ranked by #states and no-backfill concentration.
Bill data (c) LegiScan LLC (legiscan.com), CC BY 4.0.
"""
import json, os, re
from collections import defaultdict
import legiscan_ingest as G

rows=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),".legiscan_data.json")))
NB=G.NO_BACKFILL
STATE_WORDS=set("alabama alaska arizona arkansas california colorado connecticut delaware florida georgia hawaii idaho illinois indiana iowa kansas kentucky louisiana maine maryland massachusetts michigan minnesota mississippi missouri montana nebraska nevada hampshire jersey mexico york carolina dakota ohio oklahoma oregon pennsylvania rhode island tennessee texas utah vermont virginia washington wisconsin wyoming".split())
STOP=set("an act the of to relating a and for concerning enacting provisions provision certain amend amending code annotated title relative be it enacted".split())
def repro(t): return any(k in (t or '').lower() for k in G.REPRO_TOKENS)
def toks(t):
    t=re.sub(r'[^a-z ]',' ',(t or '').lower())
    return {w for w in t.split() if len(w)>2 and w not in STOP and w not in STATE_WORDS}
def jac(a,b):
    if not a or not b: return 0.0
    return len(a&b)/len(a|b)

def detect(min_states=3, thresh=0.55):
    bills=[(r.get('state'),r.get('bill_number'),r.get('title',''),toks(r.get('title','')),r.get('last_action_date',''))
           for r in rows.values() if repro(r.get('title','')) and G._stance(r.get('title',''))!='protect']
    n=len(bills); used=[False]*n; clusters=[]
    for i in range(n):
        if used[i] or not bills[i][3]: continue
        grp=[i]
        for j in range(i+1,n):
            if used[j] or not bills[j][3]: continue
            if jac(bills[i][3],bills[j][3])>=thresh:
                grp.append(j)
        st={bills[k][0] for k in grp}
        if len(st)>=min_states:
            for k in grp: used[k]=True
            clusters.append(grp)
    clusters.sort(key=lambda g:-len({bills[k][0] for k in g}))
    print("="*90); print(f"COPYCAT CAMPAIGNS  (>= {min_states} states, title-similarity >= {thresh})"); print("="*90)
    if not clusters: print("  none at this threshold"); return
    for g in clusters:
        st=sorted({bills[k][0] for k in g}); nb=[s for s in st if s in NB]
        rep=max(g,key=lambda k:len(bills[k][3]))
        print(f"\n  CAMPAIGN: {len(g)} bills across {len(st)} states  ({len(nb)} no-backfill: {','.join(nb)})")
        print(f"    theme: \"{bills[rep][2][:72]}\"")
        print(f"    states: {', '.join(st)}")
        for k in sorted(g,key=lambda k:bills[k][0])[:8]:
            print(f"      {bills[k][0]} {bills[k][1]:<9} {bills[k][2][:58]}  ({bills[k][4]})")
        if len(g)>8: print(f"      ... +{len(g)-8} more")

if __name__=="__main__":
    detect(min_states=3, thresh=0.55)
    print("\n"+"-"*90)
    detect(min_states=4, thresh=0.5)

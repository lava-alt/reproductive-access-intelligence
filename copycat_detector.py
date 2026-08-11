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

# generic tokens that do NOT make a distinctive campaign theme on their own
GENERIC={"abortion","reproductive","health","care","services","service","information","coverage",
         "provisions","prohibited","prohibit","women","woman","state","relating","requirements",
         "medical","pregnancy","pregnant","minor","act","law","code"}

def campaigns(min_states=3, thresh=0.5):
    """Return de-duplicated coordinated campaigns: clusters of near-identical restrictive bills
    spanning >= min_states DISTINCT states, whose shared core has >= 2 distinctive (non-generic)
    tokens (kills bare 'Abortion' placeholder clusters). Ranked by #states then no-backfill count."""
    seen=set(); bills=[]
    for r in rows.values():
        t=r.get('title','')
        if not repro(t) or G._stance(t)=='protect': continue
        key=(r.get('state'),r.get('bill_number'))
        if key in seen: continue
        seen.add(key)
        bills.append((r.get('state'),r.get('bill_number'),t,toks(t),r.get('last_action_date',''),r.get('url','')))
    n=len(bills); used=[False]*n; out=[]
    for i in range(n):
        if used[i] or len(bills[i][3])<3: continue
        grp=[i]+[j for j in range(i+1,n) if not used[j] and bills[j][3] and jac(bills[i][3],bills[j][3])>=thresh]
        st=sorted({bills[k][0] for k in grp})
        if len(st)<min_states: continue
        core=set.intersection(*[bills[k][3] for k in grp]) if len(grp)>1 else bills[grp[0]][3]
        if len(core-GENERIC)<1: continue          # require >=1 distinctive shared token (kills bare 'Abortion')
        rep=max(grp,key=lambda k:len(bills[k][3]))
        rt=bills[rep][2].lower()
        if any(p in rt for p in ["right to contracept","statutory right","freedom to","protect access",
                                 "reproductive freedom","access to abortion"]):
            continue                               # protective campaign, not a threat
        for k in grp: used[k]=True
        nb=[s for s in st if s in NB]
        out.append(dict(theme=bills[rep][2], states=st, n_states=len(st), n_bills=len(grp),
                        no_backfill=nb,
                        bills=[(bills[k][0],bills[k][1],bills[k][2],bills[k][5]) for k in sorted(grp,key=lambda k:bills[k][0])]))
    out.sort(key=lambda c:(-c['n_states'], -len(c['no_backfill'])))
    return out

def run():
    cs=campaigns()
    print("="*90); print(f"COORDINATED CAMPAIGNS DETECTED: {len(cs)}"); print("="*90)
    for c in cs:
        print(f"\n  {c['n_bills']} bills / {c['n_states']} states  ({len(c['no_backfill'])} no-backfill: {','.join(c['no_backfill']) or '-'})")
        print(f"    theme: \"{c['theme'][:72]}\"")
        print(f"    states: {', '.join(c['states'])}")

if __name__=="__main__": run()

#!/usr/bin/env python3
"""
THE EXPERIMENT — let the data cluster naturally. Pull FULL TEXT for a themed sample (the known
campaigns that TITLE-clustering shattered — pregnancy-resource-centers, born-alive, abortion-drugs —
PLUS a field of unrelated restrictive bills as noise), then run the full pipeline:

  text_ingest -> IDF -> blocking (TF-IDF candidates) -> Smith-Waterman IDF-weighted edges
             -> similarity graph -> Louvain communities -> classified campaigns/emerging.

Success test: does full-text + graph clustering RECOVER the pregnancy-resource-center campaign that
title-Jaccard fragmented (AZ/KY/SC/TX/MN/MT), WITHOUT us telling it those bills go together?

Sample is saved to campaign_engine/.sample.json so re-runs reuse cached text (cost stays near zero).
"""
import os, sys, json, random, itertools
_HERE=os.path.dirname(os.path.abspath(__file__)); _ROOT=os.path.dirname(_HERE)
sys.path.insert(0,_ROOT); sys.path.insert(0,_HERE)
import legiscan_ingest as G
from stance_gate import is_restrictive
import text_ingest, align, block, campaign_graph

SAMPLE_F=os.path.join(_HERE,".sample.json")
THEMES={
 "resource_center":["pregnancy resource","pregnancy center","maternity home","resource centers","pregnancy-related"],
 "born_alive":["born-alive","born alive"],
 "abortion_drugs":["abortion-inducing","chemical abortion","abortion pill","mail order","mail-order","inducing drug"],
 "personhood":["personhood","equal protection for the unborn","prenatal equal protection"],
}
def theme_of(t):
    tl=(t or "").lower()
    for k,ks in THEMES.items():
        if any(x in tl for x in ks): return k
    return None

def pick_sample(field_n=35, seed=7):
    rows=json.load(open(os.path.join(_ROOT,".legiscan_data.json")))
    themed=[]; field=[]
    for r in rows.values():
        t=r.get("title",""); st=r.get("state",""); bid=r.get("bill_id")
        if not bid or not st: continue
        tid,_=G._route(t, r.get("relevance",100))
        if tid is None: continue                              # must be repro-routable (Stage 1)
        th=theme_of(t)
        rec=dict(bill_id=bid, state=st, bill_number=r.get("bill_number",""), title=t,
                 theme=th, route=tid)
        # THEMED bills enter on theme match ALONE (do NOT re-apply the narrow keyword stance gate —
        # that gate is what fragmented these campaigns; the whole point is to let clustering judge).
        # FIELD (noise) is drawn from keyword-restrictive non-themed bills for realism.
        if th: themed.append(rec)
        elif is_restrictive(t): field.append(rec)
    random.Random(seed).shuffle(field)
    sample=themed + field[:field_n]                            # ALL themed (known campaigns) + noise field
    json.dump(sample, open(SAMPLE_F,"w"), indent=0)
    return sample

def main():
    sample = json.load(open(SAMPLE_F)) if os.path.exists(SAMPLE_F) else pick_sample()
    print(f"sample: {len(sample)} bills  (themed {sum(1 for s in sample if s['theme'])} / field {sum(1 for s in sample if not s['theme'])})")
    ids=[s["bill_id"] for s in sample]
    print("ingesting full text (cached by change_hash)...")
    texts=text_ingest.ingest([(s["bill_id"], "") for s in sample], sleep=0.35, log=True)
    docs={bid:txt for bid,txt in texts.items() if txt and len(txt.split())>=15}
    print(f"usable full-text docs: {len(docs)}/{len(ids)}")
    meta={s["bill_id"]:s for s in sample}

    idf=align.build_idf(docs)
    pairs,cos=block.candidate_pairs(docs, topk=12, floor=0.06)
    print(f"candidate pairs after blocking: {len(pairs)} (vs {len(docs)*(len(docs)-1)//2} all-pairs)")

    edges=[]
    for i,pr in enumerate(pairs):
        a,b=tuple(pr)
        s,_,_=align.similarity(docs[a],docs[b],idf)
        if s>0: edges.append((a,b,s))
        if (i+1)%200==0: print(f"  aligned {i+1}/{len(pairs)}", flush=True)
    print(f"alignment edges > 0: {len(edges)}")

    Gr=campaign_graph.build_graph(edges, tau=0.10)
    comms=campaign_graph.detect(Gr, meta)
    print("\n"+"="*92)
    print(f"EMERGENT COMMUNITIES: {len(comms)}  ("
          f"{sum(1 for c in comms if c['kind']=='campaign')} campaign / "
          f"{sum(1 for c in comms if c['kind']=='emerging')} emerging)")
    print("="*92)
    for c in comms:
        themes=sorted({meta[b[2]].get('theme') or meta[b[2]].get('route') for b in c['bills']})
        print(f"\n[{c['kind'].upper()}] {c['n_bills']} bills / {c['n_states']} states  cohesion={c['cohesion']}  themes={themes}")
        print("   states:", ", ".join(c['states']))
        for st,bn,bid,title in c['bills']:
            print(f"     {st:>2} {bn:<10} {title}")

if __name__=="__main__":
    if "--pick" in sys.argv:
        s=pick_sample(); print(f"picked {len(s)} bills -> {SAMPLE_F}")
    else:
        main()

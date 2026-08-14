#!/usr/bin/env python3
"""
STAGE 3 — GRAPH + COMMUNITY DETECTION. This is the step NO existing tool ships (verified across the
open-source, academic, and commercial landscape): let campaigns EMERGE as communities in a
bill-similarity graph instead of matching to a predefined model-bill library.

node   = a bill
edge   = IDF-weighted local-alignment similarity (align.similarity) above tau
cluster= a community found by Louvain modularity (NOT raw connected-components: components chain
         through boilerplate bridges and merge unrelated families; modularity resists that).

A community is classified:
  CAMPAIGN  : spans >= MIN_STATES distinct states with mean intra-edge weight >= COHESION
  EMERGING  : 2 states, or >=3 states but loose (below COHESION) -> "watch, may become a campaign"
  (single-state or singleton communities are dropped)
"""
import networkx as nx
import community as community_louvain   # python-louvain
from collections import defaultdict
from statistics import mean

MIN_STATES=3
COHESION=0.14      # mean intra-community edge weight to call it a firm campaign (tunable vs ground truth)

def build_graph(edges, tau=0.10):
    """edges: iterable of (a, b, sim). Keep edges with sim>=tau."""
    G=nx.Graph()
    for a,b,s in edges:
        if s>=tau: G.add_edge(a,b,weight=float(s))
    return G

def detect(G, meta, resolution=1.0, seed=7):
    """meta: {bill_id: {'state':.., 'bill_number':.., 'title':..}}. Returns classified communities."""
    if G.number_of_edges()==0: return []
    part=community_louvain.best_partition(G, weight="weight", resolution=resolution, random_state=seed)
    comms=defaultdict(list)
    for node,c in part.items(): comms[c].append(node)
    out=[]
    for c,nodes in comms.items():
        if len(nodes)<2: continue
        sub=G.subgraph(nodes)
        w=[d["weight"] for _,_,d in sub.edges(data=True)]
        cohesion=mean(w) if w else 0.0
        states=sorted({meta.get(n,{}).get("state","?") for n in nodes})
        n_states=len({s for s in states if s and s!="?"})
        if n_states<2: continue                                    # intra-state duplicates, not a campaign
        kind = "campaign" if (n_states>=MIN_STATES and cohesion>=COHESION) else "emerging"
        members=sorted(nodes, key=lambda n: meta.get(n,{}).get("state",""))
        out.append(dict(kind=kind, n_bills=len(nodes), n_states=n_states, states=states,
                        cohesion=round(cohesion,3),
                        bills=[(meta.get(n,{}).get("state","?"), meta.get(n,{}).get("bill_number","?"),
                                n, meta.get(n,{}).get("title","")[:70]) for n in members]))
    out.sort(key=lambda d:(d["kind"]!="campaign", -d["n_states"], -d["cohesion"]))
    return out

if __name__=="__main__":
    # synthetic: two families (born-alive x3 states, resource-center x3 states) + one bridge noise
    edges=[("a","b",.5),("b","c",.45),("a","c",.4),      # family 1
           ("d","e",.5),("e","f",.42),("d","f",.38),      # family 2
           ("c","d",.05)]                                  # weak bridge (should NOT merge families)
    meta={"a":{"state":"MO"},"b":{"state":"NJ"},"c":{"state":"US"},
          "d":{"state":"AZ"},"e":{"state":"KY"},"f":{"state":"SC"}}
    G=build_graph(edges, tau=0.1)
    for com in detect(G, meta):
        print(com["kind"], com["n_states"],"states", com["states"], "cohesion",com["cohesion"])

#!/usr/bin/env python3
"""
STAGE 2 — the EDGE: how similar are two bills, by copied language. This is the piece the experts
converged on (LID KDD'16; Desmarais 'Text as Policy' PSJ'20): word-level Smith-Waterman LOCAL
alignment, which finds a CONTIGUOUS shared passage even when buried in otherwise-different text
(the "Franken-bill" case bag-of-words/cosine misses because the word-bags look dissimilar).

Two design choices, both faithful to the literature:
  ALIGNMENT: local SW, word tokens, match=+3 mismatch=-2 gap=-3 (the desmarais-lab run_hpc.py values)
             -> gives us the best matching PASSAGE (order-aware).
  SCORING:   we score that passage by IDF, not raw length. A run of rare shared words
             ("born-alive abortion survivors protection") scores high; a run of boilerplate
             ("be it enacted by the general assembly") scores ~0. This fuses LID's n-gram
             inverse-frequency idea and Desmarais's boilerplate down-weight into one metric, so the
             generic-language problem is handled IN the score, not by a separate classifier.

similarity(a,b) = idf_weight(matched shared tokens) / min(idf_total(a), idf_total(b))  in [0,1].
"""
import re, math
import numpy as np
from difflib import SequenceMatcher
from collections import Counter

MATCH, MISMATCH, GAP = 3.0, -2.0, -3.0
CAP=4000        # cap tokens/doc for the edge: model-bill operative language is early, and this bounds
                # cost so one 18k-word omnibus can't dominate. Raise for a rigorous pass.
MIN_RUN=3       # a shared run must be >=3 consecutive tokens to count (kills incidental word matches)
_WORD=re.compile(r"[a-z0-9]+")

def tokens(text):
    return _WORD.findall((text or "").lower())

def build_idf(docs):
    """docs: {id: text}. IDF over the corpus so common legislative scaffolding gets ~0 weight."""
    N=len(docs) or 1
    df=Counter()
    for t in docs.values():
        for w in set(tokens(t)): df[w]+=1
    return {w: math.log((N+1)/(c+1))+1.0 for w,c in df.items()}   # smoothed idf, always >0

def _sw_matched(a, b):
    """Smith-Waterman local alignment on token lists a,b. Returns the list of shared tokens on the
    best local path (only the positions where a[i]==b[j] along the traceback)."""
    n,m=len(a),len(b)
    if n==0 or m==0: return []
    H=np.zeros((n+1,m+1), dtype=np.float32)
    # direction: 0 stop, 1 diag, 2 up, 3 left
    D=np.zeros((n+1,m+1), dtype=np.int8)
    bi=bj=0; best=0.0
    bidx={w:k for k,w in enumerate(set(a)|set(b))}
    ai=np.array([bidx[w] for w in a]); bj_=np.array([bidx[w] for w in b])
    for i in range(1,n+1):
        eq=(bj_==ai[i-1])                                  # vector: where b matches a[i-1]
        sub=np.where(eq, MATCH, MISMATCH).astype(np.float32)
        for j in range(1,m+1):
            diag=H[i-1,j-1]+sub[j-1]
            up  =H[i-1,j]+GAP
            left=H[i,j-1]+GAP
            v=0.0; d=0
            if diag>v: v,d=diag,1
            if up>v:   v,d=up,2
            if left>v: v,d=left,3
            H[i,j]=v; D[i,j]=d
            if v>best: best,bi,bj=v,i,j
    # traceback from best cell collecting matched-equal tokens
    matched=[]; i,j=bi,bj
    while i>0 and j>0 and D[i,j]!=0:
        d=D[i,j]
        if d==1:
            if a[i-1]==b[j-1]: matched.append(a[i-1])
            i,j=i-1,j-1
        elif d==2: i=i-1
        else: j=j-1
    return matched

def similarity(a_text, b_text, idf):
    """FAST edge (default): IDF-weighted CONTIGUOUS-passage similarity in [0,1]. difflib finds the
    shared contiguous token runs (C-speed, order-aware — the copied-passage signal); we score them
    by IDF so boilerplate runs contribute ~0. ~100x faster than pure-python Smith-Waterman and
    truer to 'verbatim copied block'. 0 = no distinctive shared passage."""
    a,b=tokens(a_text)[:CAP],tokens(b_text)[:CAP]
    if not a or not b: return 0.0, 0.0, []
    sm=SequenceMatcher(None, a, b, autojunk=False)
    matched=[]
    for i,j,n in sm.get_matching_blocks():
        if n>=MIN_RUN: matched.extend(a[i:i+n])     # only real runs (>=MIN_RUN consecutive tokens)
    if not matched: return 0.0, 0.0, []
    shared=sum(idf.get(w,1.0) for w in matched)
    ta=sum(idf.get(w,1.0) for w in a); tb=sum(idf.get(w,1.0) for w in b)   # with repetition
    return min(shared/(min(ta,tb) or 1.0), 1.0), shared, matched

def similarity_sw(a_text, b_text, idf):
    """RIGOROUS edge (slow, pure-python Smith-Waterman local alignment, match=3/mismatch=-2/gap=-3).
    Tolerates small mismatches WITHIN a copied passage where difflib would break the run. Use for a
    precision pass on a shortlist, not the full candidate set."""
    a,b=tokens(a_text)[:CAP],tokens(b_text)[:CAP]
    if not a or not b: return 0.0, 0.0, []
    matched=_sw_matched(a,b)
    if not matched: return 0.0, 0.0, []
    shared=sum(idf.get(w,1.0) for w in matched)
    ta=sum(idf.get(w,1.0) for w in set(a)); tb=sum(idf.get(w,1.0) for w in set(b))
    return min(shared/(min(ta,tb) or 1.0), 1.0), shared, matched

if __name__=="__main__":
    docs={"x":"born-alive abortion survivors protection act be it enacted by the assembly",
          "y":"an act to enact the born-alive abortion survivors protection act in this state",
          "z":"relating to the regulation of ectopic pregnancy definitions and appropriations"}
    idf=build_idf(docs)
    import itertools
    for p,q in itertools.combinations(docs,2):
        s,raw,mt=similarity(docs[p],docs[q],idf)
        print(f"{p}-{q}: sim={s:.2f} raw={raw:.1f} shared={mt}")

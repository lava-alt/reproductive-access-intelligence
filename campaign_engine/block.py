#!/usr/bin/env python3
"""
STAGE 1 — BLOCKING (candidate generation). The experts are blunt that all-pairs Smith-Waterman is
infeasible (LID: ~5,000 years on 2010-15 bills). So they first retrieve cheap candidates with an
n-gram inverted index, then align only the shortlist. We do the same with TF-IDF word n-grams +
cosine: for each bill keep its top-K most-similar others above a floor. Alignment (the O(n^2) step)
then runs ONLY on these candidate pairs, not the full N*(N-1)/2.

Returns a set of unordered (id_a, id_b) candidate pairs to hand to align.similarity().
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def candidate_pairs(docs, topk=12, floor=0.08, ngram=(1,3), min_words=15):
    """docs: {id: text}. Returns (pairs, cos) where pairs is a set of frozenset({a,b}) and cos is
    the id->id cosine lookup (for diagnostics). Bills shorter than min_words are dropped (no body)."""
    ids=[i for i,t in docs.items() if len((t or '').split())>=min_words]
    if len(ids)<2: return set(), {}
    texts=[docs[i] for i in ids]
    vec=TfidfVectorizer(lowercase=True, ngram_range=ngram, min_df=1, sublinear_tf=True,
                        token_pattern=r"[a-z0-9]+", stop_words="english")
    X=vec.fit_transform(texts)
    S=cosine_similarity(X)                      # cheap O(n^2) in vector space (NOT alignment)
    np.fill_diagonal(S,0.0)
    pairs=set(); cos={}
    for a in range(len(ids)):
        order=np.argsort(S[a])[::-1][:topk]
        for b in order:
            if S[a,b]<floor: break
            key=frozenset((ids[a],ids[b]))
            pairs.add(key); cos[key]=float(S[a,b])
    return pairs, cos

if __name__=="__main__":
    docs={"a":"born alive abortion survivors protection act enacted assembly penalty provisions",
          "b":"an act to enact the born alive abortion survivors protection act in this state penalty",
          "c":"pregnancy resource center autonomy and rights of expression grant appropriation",
          "d":"appropriation department of health pregnancy resource centers grant program",
          "e":"relating to the regulation of ectopic pregnancy medical definitions and coverage"}
    pairs,cos=candidate_pairs(docs, topk=3, floor=0.02)
    for p in sorted(pairs,key=lambda p:-cos[p]):
        a,b=tuple(p); print(f"{a}-{b}: cos={cos[p]:.2f}")

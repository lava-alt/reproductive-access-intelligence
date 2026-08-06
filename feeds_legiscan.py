"""
LegiScan feed — 50-state legislative net. Compliant with LEGISCAN_INGEST_SPEC.md.
SECURITY: key read from .legiscan_key (or LEGISCAN_KEY env); NEVER printed, NEVER logged,
URL (which carries the key as a param) is NEVER echoed, even on error.
Work loop: getSearchRaw -> bill_id + change_hash (cheap) -> only getBill on new/changed hashes.
"""
import urllib.request, urllib.parse, json, os

_HERE=os.path.dirname(os.path.abspath(__file__))
_KEYFILE=os.path.join(_HERE, ".legiscan_key")
_CACHE=os.path.join(_HERE, ".legiscan_cache.json")   # change_hash store (avoids query spend)

def _key():
    k=os.environ.get("LEGISCAN_KEY")
    if k: return k.strip()
    with open(_KEYFILE) as f: return f.read().strip()

def _call(op, **params):
    q=urllib.parse.urlencode({"key":_key(), "op":op, **params})
    req=urllib.request.Request("https://api.legiscan.com/?"+q, headers={"User-Agent":"warroom/0.1"})
    try:
        d=json.load(urllib.request.urlopen(req, timeout=45))
    except Exception as e:
        raise RuntimeError(f"LegiScan network error (op={op}): {type(e).__name__}")  # no url/key
    if d.get("status")!="OK":                                # spec: always check status
        raise RuntimeError(f"LegiScan status!=OK (op={op}): {str(d.get('alert') or d.get('status'))[:120]}")
    return d

def search_raw(query, state="ALL"):
    """getSearchRaw: returns (summary, [ {bill_id, change_hash, relevance, ...} ]). Cheap; the work-loop driver."""
    d=_call("getSearchRaw", state=state, query=query)
    res=d.get("searchresult",{})
    return res.get("summary",{}), res.get("results",[])

def _load_cache():
    try:
        with open(_CACHE) as f: return json.load(f)
    except Exception: return {}
def _save_cache(c):
    with open(_CACHE,"w") as f: json.dump(c,f)

def changed_bills(query, state="ALL"):
    """Return only bills whose change_hash is new/changed vs local cache (spec: use the hashes)."""
    _,results=search_raw(query,state)
    cache=_load_cache(); fresh=[]
    for r in results:
        bid=str(r.get("bill_id")); h=r.get("change_hash")
        if cache.get(bid)!=h:
            fresh.append(r); cache[bid]=h
    _save_cache(cache)
    return fresh

if __name__=="__main__":
    # redacted verification: ONE query, print only status/counts — never key, never url
    print("verifying LegiScan key (single getSearchRaw call)...")
    summary, results = search_raw("abortion", "ALL")
    print("  status: OK")
    print(f"  summary: {json.dumps(summary)[:200]}")
    print(f"  results on page 1: {len(results)}")
    if results:
        r=results[0]
        print(f"  sample bill: bill_id={r.get('bill_id')} state={r.get('state')} "
              f"number={r.get('bill_number')} change_hash={str(r.get('change_hash'))[:8]}...")
    print("KEY WORKS." if results or summary else "call returned empty (key ok, no results?)")

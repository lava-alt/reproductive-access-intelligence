#!/usr/bin/env python3
"""
STAGE 0 — full bill TEXT ingest. The whole thesis is that titles are too thin to cluster on;
this pulls the actual bill body so the similarity engine sees the copied language.

Per bill:  getBill -> newest doc_id -> getBillText -> base64 PDF -> pdftotext -> clean words.
Cached to .billtext/{bill_id}.json keyed by change_hash, so a re-run only re-fetches bills whose
text actually changed (LegiScan gives us change_hash for free in the search cache).

Cost (measured): 2 API calls/bill of a 30k/month free quota; ~6KB text/bill; pdftotext subsecond.
Bill data (c) LegiScan LLC (legiscan.com), CC BY 4.0.  Key read from .legiscan_key, never printed.
"""
import json, os, re, base64, subprocess, tempfile, time, urllib.request, urllib.error

_HERE=os.path.dirname(os.path.abspath(__file__))
_ROOT=os.path.dirname(_HERE)
_CACHE=os.path.join(_ROOT,".legiscan_data.json")
_TEXTDIR=os.path.join(_ROOT,".billtext")
_KEYFILE=os.path.join(_ROOT,".legiscan_key")

def _key(): return open(_KEYFILE).read().strip()

def _api(op, **p):
    q='&'.join(f'{k}={v}' for k,v in p.items())
    url=f"https://api.legiscan.com/?key={_key()}&op={op}&{q}"
    try:
        return json.load(urllib.request.urlopen(url, timeout=40))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"LegiScan HTTP {e.code} (key not shown)")

def _pdf_to_text(raw):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(raw); path=f.name
    try:
        out=subprocess.run(["pdftotext","-q",path,"-"], capture_output=True, text=True).stdout
    finally:
        os.unlink(path)
    return out

def _clean(txt):
    txt=re.sub(r"<[^>]+>"," ",txt)          # in case a state returns HTML not PDF
    return re.sub(r"\s+"," ",txt).strip()

def fetch_text(bill_id, change_hash="", sleep=0.4):
    """Return cleaned full text for a bill_id, from cache if change_hash matches, else via API."""
    os.makedirs(_TEXTDIR, exist_ok=True)
    cf=os.path.join(_TEXTDIR, f"{bill_id}.json")
    if os.path.exists(cf):
        d=json.load(open(cf))
        if d.get("change_hash")==change_hash and d.get("text"):
            return d["text"]
    b=_api("getBill", id=bill_id).get("bill",{})
    texts=b.get("texts",[])
    if not texts:
        text=""
    else:
        did=texts[-1]["doc_id"]                       # newest version
        time.sleep(sleep)
        doc=_api("getBillText", id=did).get("text",{})
        raw=base64.b64decode(doc.get("doc","")) if doc.get("doc") else b""
        mime=doc.get("mime","")
        text=_clean(_pdf_to_text(raw) if "pdf" in mime else raw.decode("utf-8","ignore"))
    json.dump({"bill_id":bill_id,"change_hash":change_hash,"state":b.get("state"),
               "bill_number":b.get("bill_number"),"text":text,"words":len(text.split())},
              open(cf,"w"))
    return text

def ingest(bill_ids, sleep=0.4, log=True):
    """Fetch/caches text for a list of bill_ids (each (bill_id, change_hash) or bare bill_id).
    Returns {bill_id: text}. Skips unchanged bills for free."""
    rows=json.load(open(_CACHE)) if os.path.exists(_CACHE) else {}
    ch={r["bill_id"]: r.get("change_hash","") for r in rows.values() if r.get("bill_id")}
    out={}
    for i,item in enumerate(bill_ids):
        bid = item[0] if isinstance(item,(list,tuple)) else item
        try:
            out[bid]=fetch_text(bid, ch.get(bid,""), sleep=sleep)
        except Exception as e:
            if log: print(f"  skip {bid}: {e}")
            out[bid]=""
        if log and (i+1)%10==0: print(f"  ...ingested {i+1}/{len(bill_ids)}", flush=True)
        time.sleep(sleep)
    return out

if __name__=="__main__":
    import sys
    ids=[int(x) for x in sys.argv[1:]] or [2054863]
    t=ingest(ids)
    for bid,txt in t.items(): print(bid, "->", len(txt.split()), "words:", txt[:80])

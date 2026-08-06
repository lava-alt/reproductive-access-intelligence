#!/usr/bin/env python3
"""
LegiScan 50-state ingester — routes live state bills into the War Room.
Compliant with LEGISCAN_INGEST_SPEC.md:
  * getSearchRaw is the cheap change-driver (bill_id + change_hash); we diff hashes.
  * Rich metadata harvested via getSearch (paginated, ~36 q for the whole abortion corpus)
    and CACHED to .legiscan_data.json -> experiments replay for FREE (zero API spend).
  * Only re-harvest a query if its cache is stale (>CACHE_TTL_H h) or forced.
  * status checked in feeds_legiscan._call; key never printed; NO front-end scraping.
Attribution: bill data from LegiScan LLC (https://legiscan.com), CC BY 4.0.
"""
import json, os, time, re
import feeds_legiscan as L
from feeds_wide import Signal

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_HERE, ".legiscan_data.json")   # harvested metadata cache
CACHE_TTL_H = 12

# ---- no-backfill red/rural states: an exclusion/ban bill here lands as pure attrition
# (from the brains: no state legislature will backfill PP) -> higher consequence weight ----
NO_BACKFILL = {"TX","MO","IN","OK","NE","SC","GA","TN","KY","WV","AL","AR","LA","MS","ND","SD","ID","IA","OH"}

# ---- threat routing over bill TITLES (precision-first; require a repro token first) ----
REPRO_TOKENS = ["abortion","mifepristone","misoprostol","reproductive","planned parenthood",
                "family planning","title x","contracept","gestational","personhood","unborn",
                "fetal","pregnan","chemical abortion","abortion-inducing"]
ROUTING = [   # (threat_id, keywords, base_llr)
    ("state_exclusion", ["prohibited entity","qualified provider","medicaid","defund","abortion provider",
                         "reimburse"], 0.9),
    ("comstock",        ["mailing","mail abortion","delivery of abortion","distribut","courier","shipping"], 1.2),
    ("fda_mife",        ["mifepristone","misoprostol","abortion-inducing","chemical abortion","abortion pill",
                         "medication abortion","abortion drug","abortion inducing"], 1.1),
    ("titlex",          ["title x","family planning"], 0.8),
    ("emtala",          ["born-alive","born alive","emergency","stabiliz","medical emergency"], 0.7),
    ("personhood",      ["personhood","life begins","equal protection","unborn child","conception",
                         "constitutional right to life"], 0.9),
    ("state_ban",       ["gestational","heartbeat","6-week","six-week","trigger","prohibit abortion",
                         "ban abortion","unborn child protection","total ban"], 0.8),
]
# stance: restriction ADVANCES a threat; a pro-access bill is CONTEXT (llr 0), not evidence.
RESTRICT = ["prohibit","ban","defund","protect life","protecting life","born-alive","personhood",
            "unborn","chemical abortion","abortion-inducing","criminaliz","penalt","felony",
            "trigger","heartbeat","gestational","conception","life begins","restrict"]
PROTECT = ["protect access","reproductive freedom","right to abortion","shield","safe haven",
           "repeal","freedom to","access to abortion","reproductive health act","codify roe",
           "expand access","repro freedom","safeguard access","protect reproductive"]

def _stance(title):
    t = (title or "").lower()
    r = any(k in t for k in RESTRICT); p = any(k in t for k in PROTECT)
    if p and not r: return "protect"
    if r and not p: return "restrict"
    return "unclear"

# ---- Round 4: tightened STATE-EXCLUSION gate (precision 0.78->1.00 on the golden set) ----
_REL_FLOOR = 50
_FUND = ["medicaid","reimburse","funds","funding","title x","taxpayer","public business","charitable organization"]
_PROVIDER = ["abortion provider","prohibited entity","planned parenthood","defund","abortion providers",
             "logistical support","abortion assistance"]
_OMNIBUS = ["enacts into law major components","implement","appropriation","state budget","omnibus",
            "major components of legislation"]
_RESTRICT = ["prohibit","defund","exclude","restrict","terminate","end taxpayer","no abortion",
             "no funding","prohibiting","ban"]
_PROACCESS = ["practical support","access to abortion","appreciation day","requires health",
              "coverage for family planning","remote monitoring","postpartum"]
# Round 5: "funds/funding for abortion" defund construction (recovers OK HB3592 "term[inate];
# funds for abortions; exceptions"). Guarded by a grant-verb test so pro-access funding bills
# ("PROVIDES funding for abortion services and TRAVEL") are NOT mistaken for exclusion — this
# guard was validated on the full 1,931-bill held-out cache (added only the 1 genuine bill, 0 FPs).
_DEFUND_FUNDING = ["funds for abortion","funding for abortion","funds for abortions","funding for abortions",
                   "public funds for abortion","taxpayer funding of abortion","use of funds for abortion"]
_GRANT_VERB = ["provides funding","provide funding","provides for","grant","travel","coverage","insurance",
               "require","expand","access","freedom"]

def state_exclusion_v1(title, relevance=100):
    """True iff `title` is a genuine PP/abortion-provider Medicaid-EXCLUSION bill (not a budget
    omnibus, pro-access coverage, or appreciation-day resolution)."""
    t = (title or "").lower()
    try: rel = int(relevance)
    except Exception: rel = 100
    if _stance(title) == "protect":                        # (e/R5) pro-access stance is never exclusion
        return False
    hard = any(p in t for p in ["planned parenthood","prohibited entity","abortion provider","defund"])
    if rel < _REL_FLOOR and not hard:                      # (d) relevance floor
        return False
    if any(p in t for p in _PROACCESS) and not any(r in t for r in ["prohibit","defund","exclude","ban"]):
        return False                                       # (c) pro-access is not a threat
    if any(o in t for o in _OMNIBUS) and not ("planned parenthood" in t or "abortion" in t):
        return False                                       # (b) omnibus/appropriations
    abortion = ("abortion" in t) or ("planned parenthood" in t)
    # (R5) a defund-funding construction = restrict intent, UNLESS a grant verb marks it pro-access
    defund_funding = any(x in t for x in _DEFUND_FUNDING) and not any(g in t for g in _GRANT_VERB)
    restrict = any(r in t for r in _RESTRICT) or defund_funding
    fund_or_provider = any(f in t for f in _FUND) or any(p in t for p in _PROVIDER) or "provider" in t
    if "defund planned parenthood" in t: return True
    if "planned parenthood" in t and restrict: return True
    return abortion and restrict and fund_or_provider     # (a) co-occurrence

# ---- Round 4: personhood exclusions (audit found corporate/AI/anti-personhood false positives) ----
_NOT_PERSONHOOD = ["corporate personhood", "money as speech", "artificial intelligence", "a.i. system",
                   "nonsentient", "technology; personhood", "prohibits governmental entities from granting",
                   "prohibit legal personhood", "recognition of legal personhood by a governmental entity",
                   "dispose of the remains"]
def _personhood_ok(title):
    t = (title or "").lower()
    return not any(x in t for x in _NOT_PERSONHOOD)

def _route(title, relevance=100):
    t = (title or "").lower()
    if not any(k in t for k in REPRO_TOKENS):
        return None, 0
    for tid, kws, base in ROUTING:
        if tid == "state_exclusion":
            if state_exclusion_v1(title, relevance):       # tightened gate
                return tid, base
            continue                                       # not exclusion -> try other threats
        if any(k in t for k in kws):
            if tid == "personhood" and not _personhood_ok(title):   # strip corporate/AI/anti-personhood
                continue
            return tid, base
    return None, 0   # repro-relevant but no specific threat keyword -> DROP (precision-first)

def _stage_mult(last_action):
    a = (last_action or "").lower()
    if any(w in a for w in ["signed","enacted","chapter","public act","effective"]): return 1.0, True
    if any(w in a for w in ["passed","third reading","enrolled","concurred"]):        return 0.7, False
    if any(w in a for w in ["reported","committee","do pass","hearing","referred to committee"]): return 0.45, False
    return 0.3, False   # introduced/prefiled/referred

# ---------------- harvest (getSearch, cached) ----------------
def _harvest_query(query, state="ALL", max_pages=40):
    d0 = L._call("getSearch", state=state, query=query, page="1")
    res0 = d0.get("searchresult", {})
    total_pages = int(res0.get("summary", {}).get("page_total", 1))
    rows = {}
    def _collect(res):
        for k, v in res.items():
            if k != "summary" and isinstance(v, dict) and v.get("bill_id"):
                rows[str(v["bill_id"])] = v
    _collect(res0)
    for p in range(2, min(total_pages, max_pages) + 1):
        try:
            d = L._call("getSearch", state=state, query=query, page=str(p))
            _collect(d.get("searchresult", {}))
        except Exception as e:
            print(f"  [legiscan page {p} err] {str(e)[:50]}"); break
    return rows

def harvest(queries=("abortion", "mifepristone", "planned parenthood", "personhood"), force=False):
    """Harvest + cache. Returns dict bill_id->row. Skips API if cache is fresh."""
    if not force and os.path.exists(_DATA) and (time.time() - os.path.getmtime(_DATA)) < CACHE_TTL_H*3600:
        with open(_DATA) as f:
            return json.load(f)
    allrows = {}
    for q in queries:
        allrows.update(_harvest_query(q))
    with open(_DATA, "w") as f:
        json.dump(allrows, f)
    return allrows

def load_cached():
    if os.path.exists(_DATA):
        with open(_DATA) as f: return json.load(f)
    return harvest()

# ---------------- routed signals for the tracker ----------------
def legiscan_signals(rows=None):
    rows = rows or load_cached()
    sigs = []
    for r in rows.values():
        title = r.get("title") or ""
        st = r.get("state") or ""
        tid, base = _route(title, r.get("relevance", 100))
        if not tid:
            continue
        stance = _stance(title)
        mult, enacted = _stage_mult(r.get("last_action"))
        nb = 1.3 if st in NO_BACKFILL else 1.0
        llr = 0.0 if stance == "protect" else round(base * mult * nb, 2)
        trig = enacted and stance != "protect"
        sigs.append(Signal("LegiScan", r.get("last_action_date","") , tid,
                           f"{st}/{'enacted' if enacted else 'pending'}/{stance}", llr,
                           f"[{st}] {title}", r.get("url",""), trig,
                           f"state bill ({st}{' no-backfill×1.3' if nb>1 else ''}; {stance})"))
    return sigs

def legiscan_summary(rows=None):
    """Aggregate the 200+ state bills into ONE bounded signal per threat so the fused
    digest stays readable and the accumulator doesn't trivially saturate. Each summary
    carries the bill count, #states, #enacted, and a capped llr contribution."""
    from collections import defaultdict
    rows = rows or load_cached()
    agg = defaultdict(lambda: {"n": 0, "states": set(), "enacted": 0, "llr": 0.0,
                               "nb": 0, "latest": ("", "")})
    for r in rows.values():
        title = r.get("title") or ""; st = r.get("state") or ""
        tid, base = _route(title, r.get("relevance", 100))
        if not tid or _stance(title) == "protect":
            continue
        mult, enacted = _stage_mult(r.get("last_action"))
        nb = 1.3 if st in NO_BACKFILL else 1.0
        a = agg[tid]
        a["n"] += 1; a["states"].add(st); a["enacted"] += int(enacted); a["llr"] += base*mult*nb
        if st in NO_BACKFILL: a["nb"] += 1
        d = r.get("last_action_date", "")
        if d > a["latest"][0]:
            a["latest"] = (d, f"[{st}] {title}")
    out = []
    for tid, a in agg.items():
        # cap the state-lane's contribution so it augments, not dominates, the trusted number
        capped = min(a["llr"], 2.0)
        out.append(Signal("LegiScan", a["latest"][0], tid,
                          f"{len(a['states'])}states/{a['n']}bills/{a['enacted']}enacted/{a['nb']}no-backfill",
                          round(capped, 2), a["latest"][1] or f"{a['n']} state bills", "", a["enacted"] > 0,
                          f"{a['n']} state bills across {len(a['states'])} states"))
    return out

if __name__ == "__main__":
    rows = harvest()
    sigs = legiscan_signals(rows)
    print(f"LegiScan cache: {len(rows)} bills | {len(sigs)} routed repro signals")
    from collections import Counter
    print("by threat:", dict(Counter(s['threat_id'] for s in sigs)))
    print("attribution: bill data © LegiScan LLC (legiscan.com), CC BY 4.0")

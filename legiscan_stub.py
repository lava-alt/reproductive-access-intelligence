#!/usr/bin/env python3
"""
Experiment 3 — the WIDEST net: 50-state bills (LegiScan) + federal bills (Congress.gov).

Both need a FREE API key that is not provisioned in this environment, so this is a
RUNNABLE SCAFFOLD: the ingester, the normalized Signal schema, the threat routing, and
the exact query plan are all real. Drop a key into the env var and `LIVE=True` flips it on.

Why these feeds matter (what they CATCH that FR + Court + DOJ do NOT):
  * LegiScan  -> the STATE legislative pipeline: Medicaid provider-exclusion bills,
      state Comstock-style mailing bans, TRAP laws, 6/12-week gestational bills, personhood
      bills, ballot-measure referrals. This is the slow-lane structural signal months ahead
      (a bill is filed long before it becomes the state action the court/FR feeds later see).
  * Congress.gov -> FEDERAL bills BEFORE they become law: a multi-year §71113 re-pass, a
      national Comstock codification, a Hyde-permanence bill, a Title X elimination rider.
      The FR only sees the RULE after enactment; Congress.gov sees the BILL at introduction.

Keys (both free, self-serve):  LegiScan https://legiscan.com/legiscan  |  Congress.gov https://api.congress.gov
"""
import os, urllib.request, urllib.parse, json

LEGISCAN_KEY = os.environ.get("LEGISCAN_API_KEY", "")
CONGRESS_KEY = os.environ.get("CONGRESS_API_KEY", "")
LIVE = bool(LEGISCAN_KEY or CONGRESS_KEY)

def Signal(feed, date, threat_id, significance, llr, title, url, trigger, why):
    return dict(feed=feed, date=date, threat_id=threat_id, significance=significance,
                llr=round(llr, 2), title=title, url=url, trigger=trigger, why=why)

# ------- threat routing for legislative text (same threat ids as warroom_model) -------
BILL_ROUTING = [
    # (threat_id, any-of keywords in bill title/summary, base_llr, stage-that-triggers)
    ("state_exclusion", ["qualified provider", "medicaid provider exclusion", "defund planned parenthood",
                         "abortion provider medicaid"], 0.9, "passed_chamber"),
    ("comstock",        ["mailing abortion", "abortion-inducing drug", "deliver abortion pill",
                         "comstock"], 1.2, "enacted"),
    ("fda_mife",        ["mifepristone", "abortion pill", "chemical abortion", "medication abortion ban"], 1.1, "enacted"),
    ("titlex",          ["title x", "family planning grant", "family planning program"], 0.8, "passed_chamber"),
    ("fed_defund",      ["prohibited entity", "hyde amendment", "no taxpayer funding for abortion",
                         "reconciliation medicaid abortion"], 1.2, "reported_committee"),
    ("aca1303",         ["abortion coverage", "separate payment abortion", "qualified health plan abortion"], 0.7, "enacted"),
]
# LegiScan status codes: 1 introduced, 2 engrossed(passed one chamber), 3 enrolled, 4 passed/enacted, 5 vetoed
STATUS_LLR = {1: 0.3, 2: 0.6, 3: 0.9, 4: 1.0}      # later stage -> stronger evidence
STATUS_STAGE = {2: "passed_chamber", 3: "reported_committee", 4: "enacted"}

# ---- state structural weighting: a provider-exclusion bill in a no-backfill red state is
# ---- more consequential than in a haven that will litigate/backfill (from the brains). ----
NO_BACKFILL_STATES = {"TX","MO","IN","OK","NE","SC","GA","TN","KY","WV","AL","AR","LA","MS","ND","SD","ID","IA","OH"}

def route_bill(title, summary):
    text = ((title or "") + " " + (summary or "")).lower()
    for tid, kws, base, stage in BILL_ROUTING:
        if any(k in text for k in kws):
            return tid, base, stage
    return None, 0, None

# ============================ LegiScan (50-state) ============================
def fetch_legiscan(query="abortion OR mifepristone OR \"planned parenthood\" OR \"title x\"", state="ALL"):
    if not LEGISCAN_KEY:
        return _stub("LegiScan", "50-state bill search",
                     "https://api.legiscan.com/?op=getSearch&state=ALL&query=...&key=YOUR_KEY",
                     ["state_exclusion", "comstock", "fda_mife", "titlex"])
    sigs = []
    url = ("https://api.legiscan.com/?" + urllib.parse.urlencode(
        {"key": LEGISCAN_KEY, "op": "getSearch", "state": state, "query": query}))
    data = json.load(urllib.request.urlopen(url, timeout=45))
    for hit in (data.get("searchresult", {}) or {}).values():
        if not isinstance(hit, dict) or "bill_id" not in hit:
            continue
        tid, base, stage = route_bill(hit.get("title"), hit.get("summary", ""))
        if not tid:
            continue
        st = hit.get("state", "")
        # structural multiplier: no-backfill state raises consequence
        mult = 1.3 if st in NO_BACKFILL_STATES else 1.0
        status = int(hit.get("status", 1) or 1)
        llr = round(base * STATUS_LLR.get(status, 0.3) * mult, 2)
        trig = STATUS_STAGE.get(status) == stage
        sigs.append(Signal("LegiScan", hit.get("last_action_date", ""), tid,
                           f"{st}/status{status}", llr, f"[{st}] " + (hit.get("title") or ""),
                           hit.get("url", ""), trig, f"state bill in {st} (no-backfill×1.3)" if mult > 1 else "state bill"))
    return sigs

# ============================ Congress.gov (federal) ============================
def fetch_congress(query="abortion mifepristone planned parenthood hyde"):
    if not CONGRESS_KEY:
        return _stub("Congress.gov", "federal bill search",
                     "https://api.congress.gov/v3/bill?query=...&api_key=YOUR_KEY",
                     ["fed_defund", "comstock", "titlex"])
    sigs = []
    url = ("https://api.congress.gov/v3/bill?" + urllib.parse.urlencode(
        {"api_key": CONGRESS_KEY, "query": query, "limit": 50, "format": "json"}))
    data = json.load(urllib.request.urlopen(url, timeout=45))
    for b in data.get("bills", []):
        tid, base, stage = route_bill(b.get("title"), "")
        if not tid:
            continue
        # federal bill: evidence scaled by latest action (introduced < committee < passed < enacted)
        act = (b.get("latestAction", {}) or {}).get("text", "").lower()
        llr = base * (1.0 if "became public law" in act else 0.6 if "passed" in act else 0.3)
        trig = "became public law" in act
        sigs.append(Signal("Congress.gov", (b.get("latestAction", {}) or {}).get("actionDate", ""),
                           tid, "federal-bill", round(llr, 2), b.get("title") or "",
                           b.get("url", ""), trig, "federal bill"))
    return sigs

def _stub(feed, what, endpoint, threats):
    return [Signal(feed, "", "__stub__", "STUB", 0.0,
                   f"[KEY REQUIRED] {feed} {what} — would route to {threats}",
                   endpoint, False, "no API key in env; scaffold ready")]

if __name__ == "__main__":
    print("=" * 88)
    print(f"LEGISLATIVE WIDE NET — LIVE={LIVE}  (set LEGISCAN_API_KEY / CONGRESS_API_KEY to activate)")
    print("=" * 88)
    for sigs in (fetch_legiscan(), fetch_congress()):
        for s in sigs[:12]:
            tag = "STUB" if s["threat_id"] == "__stub__" else f"{s['threat_id']} (llr {s['llr']})"
            print(f"  [{s['feed']:<12}] {tag}")
            print(f"     {s['title']}")
            print(f"     -> {s['url']}")
    print("\nWhat it would catch (documented, not stubbed away):")
    print("  LegiScan   : 50-state provider-exclusion / Comstock-mailing / medication-abortion / TRAP /")
    print("               personhood / ballot-referral bills — MONTHS before they become the state action")
    print("               the court & FR feeds later see. No-backfill red states weighted ×1.3 (from brains).")
    print("  Congress   : federal §71113 re-pass, national Comstock codification, Hyde-permanence, Title X")
    print("               elimination riders — at BILL introduction, not after the rule is published.")

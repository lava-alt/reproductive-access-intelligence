#!/usr/bin/env python3
"""
Round 2 / Experiment 6 — KEYLESS federal bills via GovTrack.us (Congress.gov needs a key).

Verified keyless (HTTP 200, Aug 2026): https://www.govtrack.us/api/v2/bill?q=...
GovTrack mirrors Congress.gov bill-status data. This is the SLOW-lane structural signal:
a bill at INTRODUCTION is a long-lead warning -- it appears months/years before it becomes
the enacted rule the Federal Register later publishes (e.g., a multi-year §71113 re-pass,
a national Comstock codification, a Hyde-permanence bill, a Title X elimination rider).

Routing uses the SAME threat ids as warroom_model. Evidence (LLR) scales by legislative
stage: introduced << passed-a-chamber << enacted. Introduction alone is deliberately weak
(most bills die) -- it raises *awareness*, not the trusted risk number.
"""
import urllib.request, urllib.parse, json, time
from feeds_wide import Signal

UA = {"User-Agent": "warroom/1.0 (repro early-warning; research)"}
SINCE = "2025-01-01"

# threat routing for federal bill titles (precision-first keyword sets)
BILL_ROUTING = [
    ("fed_defund",      ["prohibited entity", "defund planned parenthood", "no taxpayer funding for abortion",
                         "hyde amendment", "taxpayer funding of abortion"], 1.2),
    ("comstock",        ["comstock", "mailing of abortion", "abortion-inducing drug", "ensuring women"], 1.3),
    ("fda_mife",        ["mifepristone", "chemical abortion", "abortion pill", "medication abortion"], 1.1),
    ("titlex",          ["title x", "family planning"], 0.8),
    ("aca1303",         ["abortion coverage", "separate payment for abortion", "no abortion funding"], 0.7),
    ("emtala",          ["emergency medical treatment", "emtala", "born-alive", "conscience protection"], 0.9),
    ("state_exclusion", ["qualified provider", "medicaid provider"], 0.8),
]
# stage -> evidence multiplier. current_status strings from GovTrack.
def _stage_mult(status):
    s = (status or "").lower()
    if "enacted" in s or "signed" in s or "became law" in s:
        return 1.0, True          # enacted -> trigger
    if "passed" in s or "agreed" in s or "cloture" in s:
        return 0.6, False
    if "reported" in s or "ordered" in s:
        return 0.45, False
    return 0.3, False             # introduced/referred -> weak long-lead

# a genuine repro bill must name a repro subject (kills "State Offices of Women's Health" etc.
# that merely match a generic term)
REPRO_STRONG = ["abortion", "mifepristone", "misoprostol", "planned parenthood", "comstock",
                "title x", "family planning", "contracept", "reproductive", "hyde"]

# STANCE: keyword routing captures TOPIC, not direction. A threat only ADVANCES via a
# RESTRICTION bill; a pro-access bill ("Stop Comstock Act", "Reaffirming freedom") on the
# same topic is NOT evidence the threat is rising -> show it as context (llr 0), don't
# inflate the risk. Precision-first: unambiguous markers only; unknown -> treat as restrict
# (conservative for a threat monitor) but flagged 'unclear'.
RESTRICT = ["defund", "prohibited entity", "prohibit", "chemical abortion", "protecting life",
            "ending chemical", "safeguarding women from chemical", "born-alive", "no taxpayer funding",
            "no abortion funding", "hyde", "against abortion", "protect life", "conscience protection"]
PROTECT = ["stop comstock", "reaffirming", "freedom to decide", "right to contraception",
           "women's health protection", "protect access", "ensuring access", "expand access",
           "reproductive freedom", "support for medication", "abortion access"]

def _stance(title):
    t = (title or "").lower()
    r = any(k in t for k in RESTRICT); p = any(k in t for k in PROTECT)
    if p and not r:
        return "protect"      # opposes the threat -> context only
    if r and not p:
        return "restrict"
    return "unclear"

def _route(title):
    t = (title or "").lower()
    if not any(k in t for k in REPRO_STRONG):
        return None, 0
    for tid, kws, base in BILL_ROUTING:
        if any(k in t for k in kws):
            return tid, base
    return None, 0

QUERIES = ["mifepristone", "abortion", "planned parenthood", "title x family planning", "comstock"]

def _get(url):
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=45))
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)

def fetch_govtrack(per=25):
    sigs, seen = [], set()
    for q in QUERIES:
        url = "https://www.govtrack.us/api/v2/bill?" + urllib.parse.urlencode(
            {"q": q, "sort": "-introduced_date", "limit": per})
        try:
            data = _get(url)
        except Exception as e:
            print(f"  [govtrack err] {q}: {str(e)[:60]}")
            continue
        for b in data.get("objects", []):
            title = b.get("title") or ""
            date = b.get("introduced_date") or b.get("current_status_date") or ""
            if date and date < SINCE:
                continue
            tid, base = _route(title)
            if not tid:
                continue
            key = (b.get("congress"), b.get("bill_type_label"), b.get("number"))
            if key in seen:
                continue
            seen.add(key)
            mult, trig = _stage_mult(b.get("current_status"))
            stance = _stance(title)
            # pro-access bill on this topic -> context only (no threat evidence, no trigger)
            llr = 0.0 if stance == "protect" else round(base * mult, 2)
            trig = trig and stance != "protect"
            sigs.append(Signal("GovTrack", b.get("current_status_date") or date, tid,
                               f"bill/{b.get('current_status','introduced')}/{stance}", llr,
                               title, b.get("link") or "", trig,
                               f"federal bill (long-lead structural; stance={stance})"))
    return sigs

if __name__ == "__main__":
    print("=" * 90)
    print("KEYLESS FEDERAL BILLS — GovTrack.us  (slow-lane structural, long lead)")
    print("=" * 90)
    sigs = fetch_govtrack()
    print(f"{len(sigs)} repro-relevant federal bills since {SINCE}\n")
    from warroom_model import THREATS
    for s in sorted(sigs, key=lambda x: x["date"], reverse=True):
        flag = " ⚡ENACTED-TRIGGER" if s["trigger"] else ""
        print(f"  [{s['date']}] {THREATS.get(s['threat_id'],{}).get('label',s['threat_id'])}  "
              f"({s['significance']}, llr {s['llr']}){flag}")
        print(f"     {s['title'][:86]}")

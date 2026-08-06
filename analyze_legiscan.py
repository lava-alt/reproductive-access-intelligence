#!/usr/bin/env python3
"""
Insight engine over the cached LegiScan 50-state corpus (zero API spend — reads
.legiscan_data.json). Five experiments a PP exec would actually use:
  1. LANDSCAPE   — active repro bills by state, threat, stance, stage. Hotspots.
  2. VELOCITY    — bill activity over time (last_action_date by month).
  3. COPYCAT     — near-identical bill titles across multiple states = coordinated model-bill
                   campaign (an early-warning signal BEFORE any single bill advances).
  4. NEXT-KANSAS — restriction bills ADVANCING in no-backfill states, ranked by consequence.
  5. CORROBORATION — threats lit in BOTH the state (LegiScan) and federal (court/bill) lanes.
Attribution: bill data © LegiScan LLC (legiscan.com), CC BY 4.0.
"""
import re, json
from collections import Counter, defaultdict
from legiscan_ingest import load_cached, _route, _stance, _stage_mult, NO_BACKFILL
from warroom_model import THREATS

STOP = set("the a an of to for and or in on by with act relating provide provides amend amending "
           "concerning regarding certain state department health care requirements requiring "
           "establish create creates various sections chapter title code law laws bill".split())

def _norm_title(t):
    t = (t or "").lower()
    t = re.sub(r"[^a-z ]", " ", t)
    words = [w for w in t.split() if w not in STOP and len(w) > 2]
    return words

def _signature(t):
    """order-independent significant-word signature for copycat grouping."""
    return frozenset(_norm_title(t))

def landscape(rows):
    by_state = Counter(); by_threat = Counter(); by_stance = Counter(); by_stage = Counter()
    routed = 0
    for r in rows.values():
        tid, base = _route(r.get("title"))
        if not tid:
            continue
        routed += 1
        st = r.get("state") or "?"
        by_state[st] += 1
        by_threat[THREATS.get(tid, {}).get("label", tid)] += 1
        by_stance[_stance(r.get("title"))] += 1
        _, enacted = _stage_mult(r.get("last_action"))
        by_stage["enacted/signed" if enacted else "pending"] += 1
    print("=" * 84); print(f"1. LIVE LANDSCAPE — {routed} routed repro bills across {len(by_state)} states")
    print("=" * 84)
    print("  Top hotspot states:", ", ".join(f"{s}={n}" for s, n in by_state.most_common(12)))
    print("  By threat:", ", ".join(f"{k.split('(')[0].strip()}={v}" for k, v in by_threat.most_common()))
    print("  By stance:", dict(by_stance), " | By stage:", dict(by_stage))
    return by_state

def velocity(rows):
    by_month = Counter()
    for r in rows.values():
        if not _route(r.get("title"))[0]:
            continue
        d = (r.get("last_action_date") or "")[:7]
        if d:
            by_month[d] += 1
    print("\n" + "=" * 84); print("2. VELOCITY — repro-bill activity by month (last action)")
    print("=" * 84)
    for m in sorted(by_month)[-10:]:
        print(f"  {m}  {'█'*min(60,by_month[m])} {by_month[m]}")

def _jaccard(a, b):
    if not a or not b: return 0.0
    return len(a & b) / len(a | b)

def copycat(rows, min_states=3, thresh=0.5):
    """Greedy Jaccard clustering on title word-sets: near-identical bills across states =
    a coordinated model-bill campaign (fuzzy match, not exact — model bills vary slightly)."""
    items = []
    for r in rows.values():
        tid, _ = _route(r.get("title"))
        if not tid:
            continue
        sig = frozenset(_norm_title(r.get("title")))
        if len(sig) >= 3:
            items.append((sig, r, tid))
    clusters = []   # each: {sigs:list, rows:list}
    for sig, r, tid in items:
        placed = False
        for c in clusters:
            if _jaccard(sig, c["rep"]) >= thresh:
                c["rows"].append(r); placed = True; break
        if not placed:
            clusters.append({"rep": sig, "rows": [r], "tid": tid})
    print("\n" + "=" * 84); print(f"3. COPYCAT / MODEL-BILL DETECTION — near-identical bills across >= {min_states} states (Jaccard>={thresh})")
    print("=" * 84)
    found = []
    for c in clusters:
        states = sorted({r.get("state") for r in c["rows"]})
        if len(states) >= min_states:
            found.append((len(states), c["rows"][0].get("title"), states, c["tid"]))
    found.sort(reverse=True)
    if not found:
        print("  (no cross-state clusters at this threshold)")
    for nstates, title, states, tid in found[:12]:
        nb = sum(1 for s in states if s in NO_BACKFILL)
        print(f"  [{nstates} states, {nb} no-backfill] {THREATS.get(tid,{}).get('label',tid).split('(')[0].strip()}")
        print(f"     \"{(title or '')[:74]}\"")
        print(f"     -> {', '.join(states)}")
    return found

def next_kansas(rows, top=12):
    scored = []
    for r in rows.values():
        tid, base = _route(r.get("title"))
        if not tid:
            continue
        st = r.get("state") or "?"
        stance = _stance(r.get("title"))
        if stance == "protect":
            continue
        mult, enacted = _stage_mult(r.get("last_action"))
        nb = 1.3 if st in NO_BACKFILL else 1.0
        score = base * mult * nb
        scored.append((score, enacted, st, tid, r))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    print("\n" + "=" * 84)
    print("4. NEXT-KANSAS / NEXT-§71113 — restriction bills advancing where there is NO backfill")
    print("=" * 84)
    for score, enacted, st, tid, r in scored[:top]:
        tag = "ENACTED" if enacted else "advancing"
        flag = " ⚠NO-BACKFILL" if st in NO_BACKFILL else ""
        print(f"  {score:.2f} [{st} {tag}{flag}] {THREATS.get(tid,{}).get('label',tid).split('(')[0].strip()}")
        print(f"     \"{(r.get('title') or '')[:72]}\"  — {(r.get('last_action') or '')[:38]}")

def corroboration(rows):
    # which threats are lit in the STATE lane AND the FEDERAL lanes simultaneously?
    state_threats = Counter()
    for r in rows.values():
        tid, base = _route(r.get("title"))
        if tid and _stance(r.get("title")) != "protect":
            state_threats[tid] += 1
    print("\n" + "=" * 84); print("5. STATE×FEDERAL CORROBORATION — threats active in BOTH lanes")
    print("=" * 84)
    try:
        from feeds_fed import fetch_govtrack
        fed = Counter(s["threat_id"] for s in fetch_govtrack() if s["llr"] > 0)
    except Exception as e:
        fed = Counter(); print(f"  (federal-bill feed unavailable: {str(e)[:40]})")
    for tid in set(state_threats) | set(fed):
        s, f = state_threats.get(tid, 0), fed.get(tid, 0)
        both = "  ⛓ BOTH LANES" if s and f else ""
        print(f"  {THREATS.get(tid,{}).get('label',tid).split('(')[0].strip():<34} state={s:>3}  federal-bills={f:>2}{both}")

if __name__ == "__main__":
    rows = load_cached()
    print(f"(corpus: {len(rows)} cached LegiScan bills; data © LegiScan LLC, CC BY 4.0)\n")
    landscape(rows); velocity(rows); copycat(rows); next_kansas(rows); corroboration(rows)

#!/usr/bin/env python3
"""
THE KEY CAPABILITY (round 3) — SIGNAL-vs-COVERAGE GAP.

For each threat, compute two INDEPENDENT quantities:
  REAL ACTIVITY   = summed hard-signal weight from the tracker (LegiScan bills + CourtListener
                    + GovTrack federal bills + Federal Register).  "Is anything actually moving?"
  MEDIA COVERAGE  = article volume from the keyless news feed (Google News count; GDELT if up).
                    "Is anyone talking about it?"
Both are min-max normalized to [0,1] across threats, then GAP = activity_norm - coverage_norm.
  GAP >> 0  -> UNDER-COVERED = sleeper threat (real movement, no headlines) — the marquee output.
  GAP << 0  -> OVER-COVERED  = discount as hype/noise.

HONEST LIMITS: both inputs are noisy and on different scales; normalization is min-max across a
small threat set; Google News caps ~results and saturates on popular topics (compressing the top);
threat queries overlap; GDELT rate-limits. This is a DIRECTIONAL heuristic, not a precise metric.
Attribution: bill data © LegiScan LLC (legiscan.com), CC BY 4.0.
"""
from collections import defaultdict
from warroom_model import THREATS
from legiscan_ingest import legiscan_signals
from feeds_news import coverage_by_threat, NEWS_QUERY

def _real_activity():
    """summed llr per threat across all hard feeds (state + federal + court + agency)."""
    act = defaultdict(float); srcs = defaultdict(set)
    # LegiScan (cached, free) — the bulk of state-level activity
    for s in legiscan_signals():
        if s["llr"] > 0:
            act[s["threat_id"]] += s["llr"]; srcs[s["threat_id"]].add("LegiScan")
    # federal bills + court + FR (live; wrapped so a feed outage doesn't kill the analysis)
    try:
        from feeds_fed import fetch_govtrack
        for s in fetch_govtrack():
            if s["llr"] > 0:
                act[s["threat_id"]] += s["llr"]; srcs[s["threat_id"]].add("GovTrack")
    except Exception as e:
        print(f"  (govtrack unavailable: {str(e)[:40]})")
    try:
        from feeds_wide import fetch_courtlistener
        for s in fetch_courtlistener():
            act[s["threat_id"]] += s["llr"]; srcs[s["threat_id"]].add("Court")
    except Exception as e:
        print(f"  (court unavailable: {str(e)[:40]})")
    return act, srcs

def _minmax(d, keys):
    vals = [d.get(k, 0) for k in keys]
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return {k: 0.0 for k in keys}
    return {k: (d.get(k, 0) - lo) / (hi - lo) for k in keys}

def run():
    print("=" * 92)
    print("SIGNAL-vs-COVERAGE GAP — where real activity and media attention diverge")
    print("=" * 92)
    act, srcs = _real_activity()
    cov = coverage_by_threat()
    cov_count = {t: c["gnews_count"] for t, c in cov.items()}

    # union of threats that have EITHER hard signals OR a news query
    keys = [t for t in NEWS_QUERY if t in THREATS]
    keys += [t for t in act if t in THREATS and t not in keys]
    act_n = _minmax(act, keys)
    cov_n = _minmax(cov_count, keys)

    rows = []
    for t in keys:
        gap = act_n[t] - cov_n[t]
        rows.append((gap, t, act.get(t, 0), cov_count.get(t, 0), srcs.get(t, set())))
    rows.sort(reverse=True)

    print(f"\n  {'threat':<34}{'REAL(w)':>8}{'MEDIA':>7}{'act_n':>7}{'cov_n':>7}{'GAP':>7}   verdict")
    print("  " + "-" * 88)
    for gap, t, a, c, s in rows:
        lbl = THREATS[t]["label"].split("(")[0].strip()
        if gap >= 0.30:   v = "⚠ UNDER-COVERED (sleeper)"
        elif gap <= -0.30: v = "over-covered (hype/noise)"
        else:              v = "aligned"
        print(f"  {lbl:<34}{a:>8.1f}{c:>7}{act_n[t]:>7.2f}{cov_n[t]:>7.2f}{gap:>+7.2f}   {v}")

    sleepers = [r for r in rows if r[0] >= 0.30]
    print("\n  MARQUEE OUTPUT — under-covered sleeper threats (real movement, low headlines):")
    if not sleepers:
        print("     (none clear this run)")
    for gap, t, a, c, s in sleepers:
        print(f"     • {THREATS[t]['label'].split('(')[0].strip()}: real activity {a:.1f} "
              f"({'+'.join(sorted(s)) or 'state bills'}) vs media {c} — GAP {gap:+.2f}")
    print("\n  method: min-max normalized across threats; news=Google News count (noisy, saturating);")
    print("  real=summed hard-signal llr. Directional heuristic only. Bill data © LegiScan LLC, CC BY 4.0.")

if __name__ == "__main__":
    run()

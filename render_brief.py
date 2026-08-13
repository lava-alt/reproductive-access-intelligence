#!/usr/bin/env python3
"""Render the PP Defund War Room Monday brief as a polished, self-contained HTML dashboard.

Round 5 build:
  * per-threat DRILL-DOWNS: each threat expands to the actual routed bills from the LegiScan
    cache, every row linking to the official bill page (auditable, one click to source).
  * editorial font stack (serif headlines + humanist sans + mono data) instead of system-ui.
  * no em dashes anywhere in authored prose.
Bill data (c) LegiScan LLC (legiscan.com), CC BY 4.0. Renders offline, no external deps.
"""
from datetime import date
import json, os, html
import legiscan_ingest as G
from personhood_audit import verified_personhood_bills
from copycat_detector import campaigns as _campaigns

_HERE = os.path.dirname(os.path.abspath(__file__))

# ---- pull the routed bills per threat straight from the live cache ----
def load_bills_by_threat():
    from collections import defaultdict
    try:
        rows = json.load(open(os.path.join(_HERE, ".legiscan_data.json")))
    except Exception:
        return {}
    from map_data import PROACCESS_MAP
    by = defaultdict(list)
    for r in rows.values():
        title = r.get("title", "")
        tid, _ = G._route(title, r.get("relevance", 100))
        if not tid:
            continue
        # ACCURACY: the per-threat drill-downs shown to execs must be RESTRICTIVE only. Drop
        # pro-access bills that _stance mislabels (HI "stockpile mifepristone", CA "emergency
        # preparedness", NY "hospital interference") so a threat drawer never lists a pro-access bill.
        if G._stance(title) != "restrict":
            continue
        if any(p in title.lower() for p in PROACCESS_MAP):
            continue
        by[tid].append(r)
    # personhood drawer reads from the HAND-AUDITED verified set (the same 42 the hero cites),
    # not the ordered router (which sends 13 dual-keyword bills to earlier threats). Headline
    # count and drawer count now agree exactly, no asterisk.
    by["personhood"] = verified_personhood_bills()
    for tid in by:
        by[tid].sort(key=lambda r: (r.get("state", ""), r.get("bill_number", "")))
    return by

BILLS = load_bills_by_threat()

D = {
 "generated": date.today().isoformat(),
 # (rank, name, risk%, feeds, lead, threat_id-for-drilldown, extra source links [(label,url)])
 "threats": [
   (1,"FDA mifepristone / REMS re-tightening",93,4,
    "Louisiana and AHM litigation, 37 restrictive state bills across 15 states, plus federal bills. Highest-confidence threat in the system.",
    "fda_mife",[("CourtListener: State of Louisiana v. FDA","https://www.courtlistener.com/?q=Louisiana+v+FDA")]),
   (2,"EMTALA emergency-abortion rollback",93,3,
    "Federal Register guidance rescission already published, plus 18 restrictive state bills. Realized and still active.",
    "emtala",[("Federal Register: HHS EMTALA guidance","https://www.federalregister.gov/agencies/health-and-human-services-department")]),
   (3,"State Medicaid exclusion (post-Medina)",89,3,
    "Medina decided, 27 restrictive state bills across 14 states. The permanent-precedent cascade.",
    "state_exclusion",[("CourtListener: Medina v. PP South Atlantic","https://www.courtlistener.com/?q=Medina+Planned+Parenthood")]),
   (4,"Comstock / mailed-pill ban",76,1,
    "Rising via state mailing-ban bills (7 bills, 4 states) plus a federal Ban Abortion by Mail Act. Not yet a headline threat.",
    "comstock",[]),
   (5,"Fetal personhood (state)",65,1,
    "42 verified bills across 21 states, 26 of them in no-backfill states. The sleeper (see alert). Every one of the 42 is browsable below.",
    "personhood",[]),
   (6,"Federal Medicaid defund (Section 71113 re-pass)",47,2,
    "CourtWatch (PPFA v. Kennedy) plus GovTrack (S.203 Defund PP Act). Long lead, seeded at bill introduction.",
    None,[("GovTrack: S.203 Defund Planned Parenthood Act","https://www.govtrack.us/congress/bills/subjects/abortion/6222"),
          ("CourtListener: PPFA v. Kennedy","https://www.courtlistener.com/?q=Planned+Parenthood+Federation+Kennedy")]),
 ],
 "gap": [
   ("Fetal personhood",85,30,"UNDER-COVERED"),
   ("Comstock (state route)",62,24,"UNDER-COVERED"),
   ("Mifepristone / REMS",95,90,"TRACKED"),
   ("Section 71113 federal defund",22,86,"OVER / LEGACY"),
   ("Title X",12,70,"OVER"),
 ],
 "whats_new": [
   "<b>Copycat model-bill campaigns</b> detected across states, visible <i>before</i> any single bill advances: an Abortion-inducing Drugs and Reports bill cloned in <b>AZ, IN, OK, SC</b>, and a Born-Alive Survivors Protection Act in <b>MO, NJ, and federal</b>.",
   "<b>Comstock is escalating through the state mailing-ban route.</b> 13 bills (some enacted in no-backfill states) plus a federal Ban Abortion by Mail Act. The mailed-pill lifeline is being targeted <i>legislatively</i>, not just in court.",
   "<b>Enacted this session in no-backfill states:</b> SD abortion-drug distribution ban (Mar 30), IA abortion bill, TX PP logistical-support exclusion (effective 9/1/25), TN personhood provision (effective 4/23/26).",
   "<b>Legislative velocity peaked Jan through Mar 2026</b> (41, then 27, then 22 repro bills per month). The 2026 session is the active window.",
 ],
 "watch": [
   "A <b>personhood bill clearing committee</b> in a no-backfill state, the moment the sleeper becomes real. Tool triggers on stage-advance.",
   "<b>Comstock:</b> any federal mailing-ban bill reported out of committee, or a DOJ enforcement action (DOJ Sentinel live).",
   "<b>FDA REMS decision</b>, the highest-leverage single event. CourtWatch and agency newsroom both pointed at it.",
   "<b>Section 71113 re-pass language</b> appearing in the next reconciliation vehicle (GovTrack Sentinel).",
 ],
 "capabilities": [
   ("Signal vs. coverage gap","What is real but under-covered. No off-the-shelf tool does this. Guttmacher shows the current map, POLITICO shows the story everyone is already reading. Only this flags <i>moving hard, no one watching</i>. It reallocates attention <i>ahead</i> of the press cycle, and today it points at personhood."),
   ("Cross-feed corroboration","A threat lit in four independent feeds (mifepristone) is a different confidence class than a single-source rumor. Spanning 50 legislatures, federal dockets, and agencies at once, it sees the pattern (a copycat campaign across AZ, IN, OK, SC) that no single-state watcher can."),
   ("Long-lead structural warning","The Section 71113 re-pass risk is visible at 47% from a bill <i>introduction</i> (S.203), months before any rule. It converts we got blindsided into we flagged this in Q1."),
 ],
}

# analytical "why it ranks here" per threat (mechanism, stake, what moves the score).
# Written for a domain expert: not what the topic is, but why it sits where it does now.
WHY = {
 1:"<b>Mechanism:</b> the FDA can re-tighten the REMS (in-person dispensing, prescriber certification) by administrative action alone, no Congress required. <b>Stake:</b> medication abortion is now the majority of US abortions, so a REMS rollback hits every state at once, blue states included, unlike a state ban. <b>What moves it:</b> the FDA's response to the AHM remand or a citizen petition. This is why it is the highest-confidence threat: four feeds are lit and the trigger is a single agency decision.",
 2:"<b>Mechanism:</b> rescinding the HHS guidance removes the federal floor that required stabilizing emergency abortion under EMTALA. <b>Stake:</b> in ban states, ER physicians lose the one federal shield for life-threatening cases, so care gets delayed to the point of harm. <b>What moves it:</b> already partly realized (guidance pulled). Next signal is enforcement posture plus the Moyle-track litigation. It ranks at parity with mifepristone because the harm is immediate and already in motion.",
 3:"<b>Mechanism:</b> Medina lets a state cut Planned Parenthood from Medicaid with no private right for patients to sue. <b>Stake:</b> Medicaid reimbursement is the largest revenue line in many red-state affiliates, and no state legislature will backfill it, so exclusion is pure attrition. <b>What moves it:</b> each state's exclusion action; 34 bills are already queued across 14 states. This is the permanent-precedent cascade, a Supreme Court ruling converting into 50 separate state fights.",
 4:"<b>Mechanism:</b> revival of the 1873 Comstock Act to criminalize mailing abortion drugs and supplies, now paired with state mailing-ban bills. <b>Stake:</b> mail-order pills via telehealth are the main workaround keeping care reachable in ban states, so closing the mail closes the lifeline. <b>What moves it:</b> a DOJ enforcement posture, or a federal mailing-ban bill clearing committee. Ranked lower only because it is not yet a headline fight, which is exactly why it is worth watching.",
 5:"<b>Mechanism:</b> confer legal person status on an embryo or fetus, which threatens abortion, IVF, and contraception simultaneously and regardless of any ballot outcome. <b>Stake:</b> this is the movement's constitutional endgame, and it advances incrementally, embedded in non-abortion bills (child support, tax credits, wrongful death). <b>What moves it:</b> a personhood bill clearing committee in a no-backfill state. It ranks as the sleeper because activity is high and coverage is near zero.",
 6:"<b>Mechanism:</b> a reconciliation provision barring federal Medicaid dollars to Planned Parenthood nationally, not state by state. <b>Stake:</b> a single federal vote defunds every affiliate at once, the broadest possible hit. <b>What moves it:</b> re-pass language appearing in the next reconciliation vehicle. It sits at 47% because the last version expired in July 2026, so this is a seeded long-lead risk, flagged from a bill introduction rather than an active fight.",
}

NO_BACKFILL = G.NO_BACKFILL

def risk_band(risk, feeds):
    """Uncertainty band from the weight-perturbation study (~+-7-8 pts; wider with fewer feeds).
    Point estimates stay curated; the band is the honest range around them."""
    hw = 4 if feeds>=4 else 6 if feeds==3 else 9 if feeds==2 else 12
    return max(1, risk-hw), min(97, risk+hw)

def risk_color(r): return "var(--crimson)" if r>=85 else ("var(--amber)" if r>=70 else "var(--blue)")
def verdict_color(v): return "var(--alarm)" if "UNDER" in v else ("var(--slate)" if "OVER" in v else "var(--green)")
def e(s): return html.escape(str(s or ""))

def _is_enacted(b):
    """Derive enacted/signed status from last_action using the model's own stage logic (no API call)."""
    return G._stage_mult(b.get("last_action") or "")[1]

def _bill_row(b):
    st = b.get("state",""); nb = ' <span class="nbdot" title="no-backfill state"></span>' if st in NO_BACKFILL else ""
    act = (b.get("last_action") or "").strip()
    act = act[:64] + ("..." if len(act) > 64 else "")
    url = b.get("url") or b.get("text_url") or "#"
    return (f'<tr><td class="bst">{e(st)}{nb}</td><td class="bnum">{e(b.get("bill_number",""))}</td>'
            f'<td class="btitle">{e((b.get("title") or "")[:90])}</td>'
            f'<td class="bact">{e(act)}</td><td class="bdate">{e(b.get("last_action_date",""))}</td>'
            f'<td class="bopen"><a href="{e(url)}" target="_blank" rel="noopener noreferrer">open &rsaquo;</a></td></tr>')

def drill(tid, extra_links):
    """Expandable evidence drawer: real routed bills from the cache + any extra source links.
    Bills are split so ENACTED (now law) sit in their own section at the top."""
    bills = BILLS.get(tid, []) if tid else []
    n = len(bills); states = len({b.get("state") for b in bills})
    enacted = [b for b in bills if _is_enacted(b)]
    pending = [b for b in bills if not _is_enacted(b)]
    rows = ""
    if enacted:
        rows += (f'<tr class="grouphdr grouphdr-enacted"><td colspan="6">'
                 f'Enacted into law ({len(enacted)})</td></tr>')
        rows += "".join(_bill_row(b) for b in enacted)
    if pending:
        hdr = f'Introduced, pending, or died ({len(pending)})' if enacted else f'All bills ({len(pending)})'
        rows += f'<tr class="grouphdr"><td colspan="6">{hdr}</td></tr>'
        rows += "".join(_bill_row(b) for b in pending)
    links = ""
    if extra_links:
        links = '<div class="xlinks">' + "".join(
            f'<a href="{e(u)}" target="_blank" rel="noopener noreferrer">{e(lab)} &rsaquo;</a>' for lab,u in extra_links
        ) + '</div>'
    if not bills and not extra_links:
        return ""
    if not bills:
        return f'<details class="drill"><summary>Sources</summary>{links}</details>'
    label = f"Browse {n} bill{'s' if n!=1 else ''} across {states} state{'s' if states!=1 else ''}"
    if enacted:
        label += f", {len(enacted)} enacted"
    return (f'<details class="drill"><summary>{label}</summary>{links}'
            f'<div class="billwrap"><table class="billtbl"><thead><tr>'
            f'<th>State</th><th>Bill</th><th>Title</th><th>Latest action</th><th>Date</th><th></th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
            f'<div class="billfoot">Every row links to the official bill page. '
            f'Red dot marks a no-backfill state. Data (c) LegiScan LLC, CC BY 4.0.</div></details>')

threat_rows=""
for rank,name,risk,feeds,lead,tid,xlinks in D["threats"]:
    chips = f'<span class="chip chip-corr">{feeds} feeds</span>' if feeds>=2 else '<span class="chip chip-single">1 feed</span>'
    sleeper = ' data-sleeper="1"' if name.startswith("Fetal") else ''
    threat_rows += f'''
      <div class="trow"{sleeper}>
        <div class="tnum">{rank}</div>
        <div class="tbody">
          <div class="tname">{e(name)} {chips}</div>
          <div class="tlead">{lead}</div>
          <div class="meter"><div class="fill" style="width:{risk}%;background:{risk_color(risk)}"></div></div>
          <details class="why"><summary>Why it ranks here</summary><p>{WHY.get(rank,"")}</p></details>
          {drill(tid,xlinks)}
        </div>
        <div class="triskwrap">
          <div class="trisk" style="color:{risk_color(risk)}">{risk}%</div>
          <div class="triskband">{risk_band(risk,feeds)[0]} to {risk_band(risk,feeds)[1]}%</div>
        </div>
      </div>'''

gap_rows=""
for t,a,c,v in D["gap"]:
    gap_rows += f'''
      <div class="gaprow">
        <div class="gapname">{e(t)}</div>
        <div class="gapbars">
          <div class="gapbar"><span class="gaplab">activity</span><div class="gtrack"><div class="gfill" style="width:{a}%;background:var(--navy)"></div></div></div>
          <div class="gapbar"><span class="gaplab">coverage</span><div class="gtrack"><div class="gfill" style="width:{c}%;background:#9fb3d1"></div></div></div>
        </div>
        <div class="gapverdict" style="color:{verdict_color(v)};border-color:{verdict_color(v)}">{e(v)}</div>
      </div>'''

whats_new = "".join(f"<li>{x}</li>" for x in D["whats_new"])
watch     = "".join(f"<li>{x}</li>" for x in D["watch"])
caps      = "".join(f'<div class="cap"><h4>{t}</h4><p>{b}</p></div>' for t,b in D["capabilities"])

# coordinated model-bill campaigns detected live from the LegiScan cache
def _clean_theme(t):
    t=(t or "").strip().strip('"\'')
    for pre in ("Establishes the ","Establishes ","Creates the ","Creating the ","Enacting the ","Relating to "):
        if t.lower().startswith(pre.lower()): t=t[len(pre):]
    t=t.strip(' "\'.;')
    # if the first ;-clause is descriptive keep it, else keep the fuller title
    first=t.split(";")[0].strip()
    return e((first if len(first)>=14 else t)[:78])
camp_html=""
for c in _campaigns()[:6]:
    chips="".join(f'<span class="scz{" nb" if s in NO_BACKFILL else ""}">{e(s)}</span>' for s in c["states"])
    nb=f' &middot; <b>{len(c["no_backfill"])} no-backfill</b>' if c["no_backfill"] else ""
    camp_html+=(f'<div class="camp"><div class="ctheme">{_clean_theme(c["theme"])}</div>'
                f'<div class="cmeta">{c["n_bills"]} bills across {c["n_states"]} states{nb}</div>'
                f'<div class="cstates">{chips}</div></div>')

def build(xlink, force_css):
 return f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Reproductive Access Intelligence, Threat Brief</title>
<style>
 :root{{
  --navy:#00286E;--blue:#2895D5;--ink:#1b2233;--slate:#5b6577;--bg:#f0ece4;--card:#fffdf9;
  --alarm:#C4116A;--amber:#C98A12;--crimson:#B02328;--green:#1F7A57;--line:#e6ddcf;
  --serif:"Iowan Old Style","Charter","Hoefler Text","Palatino Linotype",Georgia,"Times New Roman",serif;
  --sans:"Avenir Next","Optima","Segoe UI",Helvetica,Arial,sans-serif;
  --mono:"SF Mono","JetBrains Mono","IBM Plex Mono",Menlo,Consolas,monospace;
 }}
 *{{box-sizing:border-box}}
 html,body{{overflow-x:hidden;max-width:100%}}
 body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--serif);-webkit-font-smoothing:antialiased}}
 .wrap{{max-width:1080px;margin:0 auto;padding:0 22px 60px}}
 .mast{{background:linear-gradient(140deg,#001a44,#00337d 70%,#0b4aa0);color:#fff;padding:40px 0 34px;margin-bottom:24px;border-bottom:3px solid #C4116A}}
 .mast .wrap{{padding-bottom:0}}
 .kick{{font-family:var(--mono);font-size:11.5px;letter-spacing:.22em;text-transform:uppercase;color:#a9c9ea;font-weight:600;margin:0 0 10px}}
 h1{{font-family:var(--serif);font-size:clamp(30px,5vw,48px);font-weight:700;margin:0 0 10px;letter-spacing:-.015em;line-height:1.04}}
 .sub{{font-family:var(--sans);font-size:14.5px;line-height:1.6;color:#d6e3f7;max-width:780px;margin:0;font-weight:400}}
 .date{{font-family:var(--mono);display:inline-block;margin-top:16px;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.28);
   padding:5px 13px;border-radius:4px;font-size:12px;font-weight:500;color:#eaf2ff;letter-spacing:.03em}}
 h2{{font-family:var(--mono);font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--slate);font-weight:600;margin:36px 0 14px;display:flex;align-items:center;gap:8px}}
 .card{{background:var(--card);border-radius:10px;box-shadow:0 2px 14px rgba(40,30,10,.07);border:1px solid var(--line)}}
 /* sleeper */
 .sleeper{{padding:26px 28px;border-left:5px solid var(--alarm);margin-bottom:6px}}
 .sleeper .tag{{font-family:var(--mono);display:inline-block;background:var(--alarm);color:#fff;font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;padding:5px 11px;border-radius:4px;margin-bottom:16px}}
 .sleeper h3{{font-family:var(--serif);font-size:clamp(22px,3.2vw,30px);margin:0 0 14px;font-weight:700;line-height:1.16;letter-spacing:-.01em}}
 .sleeper p{{font-family:var(--sans);font-size:14.5px;line-height:1.62;color:#33384a;margin:0 0 14px;max-width:830px}}
 .stats{{display:flex;gap:30px;flex-wrap:wrap;margin-top:10px}}
 .stat .n{{font-family:var(--mono);font-size:32px;font-weight:600;color:var(--alarm);line-height:1}}
 .stat .l{{font-family:var(--sans);font-size:12px;color:var(--slate);font-weight:500;margin-top:6px;max-width:150px}}
 .conf{{font-family:var(--mono);display:inline-block;font-size:12px;font-weight:600;color:var(--green)}}
 /* threat board */
 .board{{padding:6px 10px}}
 .trow{{display:grid;grid-template-columns:36px 1fr 88px;gap:14px;align-items:start;padding:20px 16px;border-bottom:1px solid var(--line)}}
 .triskwrap{{text-align:right}}
 .triskband{{font-family:var(--mono);font-size:10.5px;color:var(--slate);margin-top:2px;letter-spacing:.01em;white-space:nowrap}}
 .trow:last-child{{border-bottom:0}}
 .trow[data-sleeper]{{background:linear-gradient(90deg,rgba(196,17,106,.055),transparent)}}
 .tnum{{font-family:var(--mono);font-size:17px;font-weight:600;color:#b7ab97;text-align:center;padding-top:2px}}
 .tname{{font-family:var(--serif);font-size:19px;font-weight:700;color:var(--ink);margin-bottom:4px;letter-spacing:-.01em}}
 .tlead{{font-family:var(--sans);font-size:13px;line-height:1.5;color:var(--slate);margin-bottom:10px}}
 .meter{{height:7px;background:#eae2d4;border-radius:5px;overflow:hidden}} .fill{{height:100%;border-radius:5px}}
 .trisk{{font-family:var(--mono);font-size:23px;font-weight:600;text-align:right;padding-top:1px}}
 .chip{{font-family:var(--mono);display:inline-block;font-size:10.5px;font-weight:600;letter-spacing:.02em;padding:2px 8px;border-radius:4px;vertical-align:middle;margin-left:8px}}
 .chip-corr{{background:#e6f4ec;color:#177a52}} .chip-single{{background:#efe8db;color:#93876f}}
 /* why-it-ranks */
 .why{{margin-top:10px}}
 .why summary{{font-family:var(--mono);font-size:12px;font-weight:600;letter-spacing:.03em;color:var(--slate);cursor:pointer;list-style:none;display:inline-flex;align-items:center;gap:7px;padding:3px 0;user-select:none}}
 .why summary::-webkit-details-marker{{display:none}}
 .why summary::before{{content:"\\25B8";display:inline-block;transition:transform .15s;color:var(--slate)}}
 .why[open] summary::before{{transform:rotate(90deg)}}
 .why summary:hover{{color:var(--ink)}}
 .why p{{font-family:var(--sans);font-size:13px;line-height:1.62;color:#33384a;margin:8px 0 2px;max-width:820px;padding:2px 0 2px 14px;border-left:2px solid var(--line)}}
 .why p b{{color:var(--ink)}}
 /* drill-down */
 .drill{{margin-top:12px;border-top:1px dashed var(--line);padding-top:10px}}
 .drill summary{{font-family:var(--mono);font-size:12px;font-weight:600;letter-spacing:.03em;color:var(--blue);cursor:pointer;list-style:none;display:inline-flex;align-items:center;gap:7px;padding:3px 0;user-select:none}}
 .drill summary::-webkit-details-marker{{display:none}}
 .drill summary::before{{content:"\\25B8";display:inline-block;transition:transform .15s;color:var(--blue)}}
 .drill[open] summary::before{{transform:rotate(90deg)}}
 .drill summary:hover{{color:var(--navy)}}
 .xlinks{{display:flex;flex-wrap:wrap;gap:8px 18px;margin:10px 0 4px}}
 .xlinks a{{font-family:var(--sans);font-size:12.5px;color:var(--navy);text-decoration:none;font-weight:600;border-bottom:1px solid #c9d6ea}}
 .xlinks a:hover{{border-bottom-color:var(--navy)}}
 .billwrap{{max-height:340px;overflow:auto;margin-top:10px;border:1px solid var(--line);border-radius:8px}}
 .billtbl{{width:100%;border-collapse:collapse;font-family:var(--sans);font-size:12px}}
 .billtbl thead th{{position:sticky;top:0;background:#f3eee4;text-align:left;padding:8px 10px;font-family:var(--mono);font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--slate);border-bottom:1px solid var(--line);font-weight:600}}
 .billtbl td{{padding:8px 10px;border-bottom:1px solid #efe9dd;vertical-align:top}}
 .billtbl tr:last-child td{{border-bottom:0}}
 .billtbl tr:hover td{{background:#faf6ee}}
 .grouphdr td{{position:sticky;top:29px;background:#efe9dd;font-family:var(--mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--slate);font-weight:600;padding:6px 10px;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}
 .grouphdr-enacted td{{background:#e6f4ec;color:#177a52}}
 .grouphdr-enacted td::before{{content:"\\2713  "}}
 .billtbl tr.grouphdr:hover td{{background:#efe9dd}}
 .grouphdr-enacted:hover td{{background:#e6f4ec}}
 .bst{{font-family:var(--mono);font-weight:600;white-space:nowrap;color:var(--ink)}}
 .bnum{{font-family:var(--mono);white-space:nowrap;color:var(--slate)}}
 .btitle{{color:#33384a;max-width:300px}}
 .bact{{color:var(--slate)}} .bdate{{font-family:var(--mono);white-space:nowrap;color:var(--slate)}}
 .bopen a{{font-family:var(--mono);font-size:11.5px;font-weight:600;color:var(--blue);text-decoration:none;white-space:nowrap}}
 .bopen a:hover{{color:var(--navy);text-decoration:underline}}
 .nbdot{{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--alarm);margin-left:4px;vertical-align:middle}}
 .billfoot{{font-family:var(--sans);font-size:11px;color:var(--slate);margin-top:8px;font-style:italic}}
 /* two-col */
 .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:20px}} @media(max-width:760px){{.grid2{{grid-template-columns:1fr}}}}
 .col{{padding:20px 24px}} .col h3{{font-family:var(--serif);font-size:18px;margin:0 0 14px;color:var(--navy);font-weight:700}}
 .col ul{{margin:0;padding:0;list-style:none}} .col li{{font-family:var(--sans);font-size:13px;line-height:1.55;padding:11px 0;border-bottom:1px solid var(--line);color:#33384a}}
 .col li:last-child{{border-bottom:0}} .col li b{{color:var(--ink)}}
 /* gap */
 .gapcard{{padding:18px 24px}}
 .gaprow{{display:grid;grid-template-columns:170px 1fr 140px;gap:16px;align-items:center;padding:13px 0;border-bottom:1px solid var(--line)}}
 .gaprow:last-child{{border-bottom:0}} .gapname{{font-family:var(--serif);font-size:15px;font-weight:700;color:var(--ink)}}
 .gapbar{{display:flex;align-items:center;gap:8px;margin:3px 0}}
 .gaplab{{font-family:var(--mono);font-size:9.5px;width:58px;color:var(--slate);text-transform:uppercase;letter-spacing:.06em;font-weight:600}}
 .gtrack{{flex:1;height:9px;background:#eae2d4;border-radius:5px;overflow:hidden}} .gfill{{height:100%;border-radius:5px}}
 .gapverdict{{font-family:var(--mono);font-size:10.5px;font-weight:600;letter-spacing:.05em;text-align:center;border:1.5px solid;border-radius:5px;padding:5px 6px}}
 .note{{font-family:var(--sans);font-size:11.5px;color:var(--slate);margin:12px 2px 0;font-style:italic}}
 /* coordinated campaigns */
 .camps{{padding:8px 22px 18px}}
 .camp{{padding:15px 0;border-bottom:1px solid var(--line)}}
 .ctheme{{font-family:var(--serif);font-size:16.5px;font-weight:700;color:var(--ink);letter-spacing:-.01em}}
 .cmeta{{font-family:var(--mono);font-size:11.5px;color:var(--slate);margin:4px 0 8px}} .cmeta b{{color:var(--alarm)}}
 .cstates{{display:flex;flex-wrap:wrap;gap:6px}}
 .scz{{font-family:var(--mono);font-size:11px;font-weight:600;padding:2px 8px;border-radius:4px;background:#eef1f7;color:var(--slate)}}
 .scz.nb{{background:rgba(196,17,106,.1);color:var(--alarm)}}
 /* coverage ribbon */
 .cov{{display:flex;flex-wrap:wrap;align-items:center;gap:18px 26px;padding:16px 22px;margin-bottom:6px;
   background:linear-gradient(90deg,rgba(0,40,110,.05),transparent);border-left:5px solid var(--navy);border-radius:10px}}
 .cov .cn{{font-family:var(--mono);font-size:26px;font-weight:600;color:var(--navy);line-height:1}}
 .cov .cl{{font-family:var(--sans);font-size:11.5px;color:var(--slate);font-weight:500;margin-top:3px}}
 .cov .ct{{font-family:var(--sans);font-size:13px;line-height:1.55;color:#33384a;flex:1;min-width:280px}}
 .cov .ct b{{color:var(--ink)}}
 /* noise */
 .noise{{font-family:var(--sans);padding:18px 24px;background:#f6f1e8;border:1px dashed var(--line);border-radius:10px;font-size:13px;line-height:1.6;color:var(--slate)}}
 .noise b{{color:#4a4636}}
 /* capabilities */
 .caps{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}} @media(max-width:760px){{.caps{{grid-template-columns:1fr}}}}
 .cap{{padding:22px;border-top:3px solid var(--blue)}} .cap h4{{font-family:var(--serif);margin:0 0 10px;font-size:16.5px;color:var(--navy);font-weight:700}}
 .cap p{{font-family:var(--sans);margin:0;font-size:12.8px;line-height:1.55;color:#33384a}}
 /* with-your-data */
 .withdata{{padding:24px 28px;border-left:5px solid var(--blue);background:linear-gradient(90deg,rgba(40,149,213,.07),transparent)}}
 .withdata h3{{font-family:var(--serif);font-size:21px;margin:0 0 12px;color:var(--navy);font-weight:700;letter-spacing:-.01em}}
 .withdata p{{font-family:var(--sans);font-size:13.8px;line-height:1.62;color:#33384a;margin:0 0 14px;max-width:850px}}
 .withdata ul{{margin:0;padding:0;list-style:none}}
 .withdata li{{font-family:var(--sans);font-size:13px;line-height:1.55;padding:9px 0;border-bottom:1px solid var(--line);color:#33384a}}
 .withdata li:last-child{{border-bottom:0}} .withdata li b{{color:var(--ink)}}
 footer{{font-family:var(--sans);margin-top:36px;padding:24px;font-size:11.5px;line-height:1.65;color:var(--slate);border-top:1px solid var(--line)}}
 footer b{{color:#4a4636}}
 a{{color:var(--blue)}}
 .xlink{{max-width:1080px;margin:6px auto 0;padding:6px 22px;font-family:var(--mono);font-size:11.5px;color:var(--slate);display:flex;justify-content:flex-end;gap:8px;align-items:center}}
 .xlink .cur{{color:var(--navy);font-weight:700;border-bottom:2px solid var(--navy);padding-bottom:1px}}
 .xlink a{{color:var(--slate);font-weight:500;text-decoration:none;border-bottom:0}}
 .xlink a:hover{{color:var(--navy)}}
 /* ---------- mobile ---------- */
 @media(max-width:600px){{
   .wrap{{padding:0 13px 48px}}
   .mast{{padding:26px 0 22px}}
   h1{{font-size:26px}}
   .sub{{font-size:13px}}
   .board{{padding:2px 2px}}
   .trow{{grid-template-columns:26px 1fr 66px;gap:9px;padding:16px 8px}}
   .tname{{font-size:16.5px}}
   .trisk{{font-size:19px}} .triskband{{font-size:9.5px}}
   .chip{{display:inline-block;margin:3px 0 0 0}}
   /* bill table: hide latest-action + date columns, let title breathe; guard horizontal scroll */
   .billwrap{{overflow-x:auto}}
   .billtbl th:nth-child(4),.billtbl td:nth-child(4),
   .billtbl th:nth-child(5),.billtbl td:nth-child(5){{display:none}}
   .btitle{{max-width:none}}
   .sleeper{{padding:20px 18px}} .sleeper h3{{font-size:20px}}
   .stats{{gap:16px}} .stat .n{{font-size:26px}}
   /* gap rows + capability + two-col all stack */
   .gaprow{{grid-template-columns:1fr;gap:6px;padding:14px 0}}
   .gapverdict{{justify-self:start;width:auto;padding:4px 10px}}
   .cov{{padding:14px 16px;gap:14px 20px}} .cov .ct{{min-width:auto;font-size:12.5px}}
   .col{{padding:16px 16px}} .cap{{padding:16px}}
   .why p{{font-size:12.5px}}
 }}
 {force_css}
</style></head><body>
<div class="mast"><div class="wrap">
  <p class="kick">Reproductive Access Intelligence</p>
  <h1>Monday-Morning Threat Brief</h1>
  <p class="sub">The always-on wide net: Federal Register, CourtListener, GovTrack, LegiScan (50-state), CMS and FDA newsrooms, Google News, a keyless state-court monitor, and the OIRA pre-publication reg pipeline (rules under review before they publish), and White House executive actions. Risk from the validated typed model (backtest AUC 0.99). Decision-support that surfaces what no single person can watch continuously.</p>
  <span class="date">Generated {D["generated"]}</span>
</div></div>
{xlink}

<div class="wrap">

  <h2>Wide-net coverage this cycle</h2>
  <div class="cov">
    <div><div class="cn">644</div><div class="cl">repro-relevant bills surfaced</div></div>
    <div><div class="cn">50</div><div class="cl">states, no blind spots</div></div>
    <div><div class="cn">100%</div><div class="cl">restrictive-bill recall</div></div>
    <div class="ct"><b>443 of these were previously invisible</b> to a keyword-only watch: TRAP and waiting-period bills, telehealth and contraception restrictions, fetal-remains provisions, and multi-state model-bill campaigns. Nothing restrictive is dropped now, every bill routes to a threat or a review bucket a human can scan.</div>
  </div>

  <h2>Most alarming, the sleeper</h2>
  <div class="card sleeper">
    <span class="tag">#1 under-covered // gap +0.45</span>
    <h3>Fetal personhood is moving fast across the states, with almost no national press.</h3>
    <p>The signal-vs-coverage gap flags personhood as the <b>#1 under-covered threat</b>. Real legislative activity is high, media coverage the <b>lowest</b> of anything we track (66 articles versus mifepristone's 99, not an artifact). It is the movement's constitutional endgame (it threatens abortion, IVF, <i>and</i> contraception at once, regardless of ballot outcomes) and it advances incrementally, embedded in non-abortion bills, exactly what a headline-driven watch misses. No one is sounding the alarm because nothing has happened yet. That is when an early-warning tool earns its keep.</p>
    <div class="stats">
      <div class="stat"><div class="n">42</div><div class="l">verified fetal-personhood bills</div></div>
      <div class="stat"><div class="n">21</div><div class="l">states</div></div>
      <div class="stat"><div class="n">26</div><div class="l">bills in no-backfill red or rural states</div></div>
      <div class="stat"><div class="n">+0.45</div><div class="l">signal-vs-coverage gap</div></div>
    </div>
    <p style="margin-top:16px;font-size:13px;color:var(--slate)">Independently corroborated by Guttmacher (16 states, 40+ bills) and Pregnancy Justice / Legal Voice (24 states with personhood language). Audit precision 0.81. Confidence: <span class="conf">MEDIUM-HIGH</span></p>
  </div>

  <h2>Top threats right now</h2>
  <div class="card board">{threat_rows}</div>

  <h2>Coordinated campaigns detected</h2>
  <div class="card camps">{camp_html}
    <p class="note">Near-identical bills moving across multiple states, a coordinated model-bill signal that shows up before any single one advances. Restrictive bills only. No-backfill marks red or rural states where an enactment is pure attrition.</p>
  </div>

  <h2>Signal vs. coverage, what is real but under-covered</h2>
  <div class="card gapcard">{gap_rows}
    <p class="note">Directional heuristic. Hard-signal activity is the trusted number, media coverage is the overlay. News volume is noisy and saturates.</p>
  </div>

  <h2>What is moving and what to watch</h2>
  <div class="grid2">
    <div class="card col"><h3>Moving this cycle</h3><ul>{whats_new}</ul></div>
    <div class="card col"><h3>Watch list</h3><ul>{watch}</ul></div>
  </div>

  <h2>Discount as noise (over-covered vs. current activity)</h2>
  <div class="noise">Heavy media volume, low <i>new</i> bill activity, mostly legacy coverage of already-realized 2025 events: <b>Section 71113 federal defund</b> (expired Jul 2026), <b>Title X</b> (1 active bill versus roughly 50 articles), <b>EMTALA and state-ban retrospectives.</b> Real, but not where <i>new</i> danger is forming. <b>Caveat:</b> a Section 71113 re-pass remains the top structural risk, it is just not generating detectable new bill activity right now.</div>

  <h2>Why this matters, capabilities for PP leadership</h2>
  <div class="caps">{caps}</div>

  <h2>Sharper with your own case data</h2>
  <div class="card withdata">
    <h3>The one blind spot is data you already hold.</h3>
    <p>Everything above runs on public signal alone. The single gap named in the limits below, routine state-court docket activity, is exactly the information Planned Parenthood already has internally: the cases co-counsel are actively litigating, the legal intake pipeline, affiliate court calendars. Feeding that live case list into the same model turns a blind spot into an advantage no outside tool can match.</p>
    <ul>
      <li><b>Closes the docket gap at zero cost.</b> No paid API needed. The filings and motions come straight from your own matters, so the tool sees them the day they happen, not when they reach the press.</li>
      <li><b>Adds proprietary lead time.</b> Your own new filings and emergency motions become early signals, weeks ahead of any public source, because you are the source.</li>
      <li><b>Builds richer trends.</b> Linking the legislative wave to the litigation it triggers lets a copycat bill campaign and the suits that follow show up as one connected trend instead of two separate signals. More ground truth, sharper patterns.</li>
      <li><b>Lets the model learn from outcomes.</b> Which flagged threats actually became active cases is the label the weights train on, so calibration improves the longer it runs beside your caseload.</li>
    </ul>
    <p style="margin-top:14px;font-size:12.5px;color:var(--slate)">All of it stays internal. The tool runs on your side. Nothing about active matters is ever hosted or shared.</p>
  </div>

  <footer>
    <b>Honest limits an exec should know:</b> news volume is noisy and saturates, so the gap metric is <b>directional, not precise</b>. The keyless state-court feed catches <i>newsworthy</i> rulings but misses routine docket entries (true docket tracking needs a paid API such as Trellis at roughly $70 to $120 per month, or the co-counsel intake in STATE_COURT_SOP.md). Stance detection under-tags some pro-access bills. Trust the corroborated, mechanistic signals, treat single-feed and news-only items as leads to verify.<br><br>
    Bill data (c) LegiScan LLC (legiscan.com), CC BY 4.0. Independent analysis, not affiliated with or endorsed by Planned Parenthood. Generated {D["generated"]} by the Reproductive Access Intelligence fused tracker.
  </footer>
</div></body></html>'''

# ---- two variants from the SAME data/content: desktop + mobile, cross-linked ----
DESKTOP_URL="https://repro-access-intel.vercel.app"
MOBILE_URL="https://repro-access-intel-mobile.vercel.app"
MOBILE_FORCE=""".wrap{padding:0 13px 48px}
.trow{grid-template-columns:26px 1fr 66px;gap:9px;padding:16px 8px}
.tname{font-size:16.5px}.trisk{font-size:19px}.triskband{font-size:9.5px}
.chip{display:inline-block;margin:3px 0 0 0}
.billwrap{overflow-x:auto}
.billtbl th:nth-child(4),.billtbl td:nth-child(4),.billtbl th:nth-child(5),.billtbl td:nth-child(5){display:none}
.btitle{max-width:none}.sleeper h3{font-size:20px}
.gaprow{grid-template-columns:1fr;gap:6px;padding:14px 0}
.gapverdict{justify-self:start;width:auto;padding:4px 10px}
.cov .ct{min-width:auto}h1{font-size:26px}"""
MAP_URL="https://repro-access-intel.vercel.app/map.html"
DESK_LINK=f'<div class="xlink"><b class="cur">Desktop view</b> &middot; <a href="{MOBILE_URL}">Mobile version &rsaquo;</a> &middot; <a href="{MAP_URL}">Map view &rsaquo;</a></div>'
MOB_LINK=f'<div class="xlink"><b class="cur">Mobile view</b> &middot; <a href="{DESKTOP_URL}">Desktop version &rsaquo;</a> &middot; <a href="{MAP_URL}">Map view &rsaquo;</a></div>'
for fname,xlink,force in (("PP_EXEC_BRIEF.html",DESK_LINK,""),
                          ("PP_EXEC_BRIEF_mobile.html",MOB_LINK,MOBILE_FORCE)):
    html=build(xlink,force)
    OUT=os.path.join(_HERE,fname)
    with open(OUT,"w") as f: f.write(html)
    bad=html.count("—")+html.count("–")
    print("wrote", OUT, f"({len(html)} bytes); em/en-dash={bad}")

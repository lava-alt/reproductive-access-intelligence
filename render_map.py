#!/usr/bin/env python3
"""
Map view generator (Phases 4-5). Binds the EXISTING per-issue/per-state bill groups (map_data.build(),
from the LegiScan cache we already gathered) onto a US map.
  - each issue = a color; states glow where its restrictive bills move
  - GLOW BY STAGE: enacted brightest -> introduced dimmest (truer threat level, not just count)
  - state ABBREVIATION labels
  - "All issues" overview: each state tinted by its dominant issue
  - click a state -> its bills for that issue, grouped by stage, each linked
  - HISTORY: weekly snapshots stored (last 7), a selector to watch the spread move week over week
Self-updating, self-contained. Deployed under the existing repro-access-intel project (/map.html).
Bill data (c) LegiScan LLC (legiscan.com), CC BY 4.0.
"""
import json, os
from datetime import date
from map_data import build

_HERE=os.path.dirname(os.path.abspath(__file__))
FIPS={"01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE","11":"DC",
 "12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA","20":"KS","21":"KY","22":"LA",
 "23":"ME","24":"MD","25":"MA","26":"MI","27":"MN","28":"MS","29":"MO","30":"MT","31":"NE","32":"NV",
 "33":"NH","34":"NJ","35":"NM","36":"NY","37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA",
 "44":"RI","45":"SC","46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV",
 "55":"WI","56":"WY"}

def render():
    issues=build()
    today=date.today().isoformat()
    snap_path=os.path.join(_HERE,"map_snapshots.json")
    try: snaps=json.load(open(snap_path))
    except Exception: snaps=[]
    snaps=[s for s in snaps if s.get("date")!=today]          # replace today's
    snaps.append({"date":today,"issues":issues})
    snaps=sorted(snaps,key=lambda s:s["date"])[-7:]           # keep last 7 weeks
    json.dump(snaps, open(snap_path,"w"))

    SNAPS=json.dumps(snaps)
    FIPSJSON=json.dumps(FIPS)
    TOPO=json.dumps(json.load(open(os.path.join(_HERE,"..","access-not-survival","states-albers-10m.json"))))
    html=f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Reproductive Access Intelligence, Threat Map</title>
<style>
 :root{{--navy:#00286E;--ink:#1b2233;--slate:#5b6577;--bg:#f0ece4;--card:#fffdf9;--line:#e6ddcf;
  --serif:"Iowan Old Style","Charter","Hoefler Text","Palatino Linotype",Georgia,serif;
  --sans:"Avenir Next","Optima","Segoe UI",Helvetica,Arial,sans-serif;
  --mono:"SF Mono","JetBrains Mono","IBM Plex Mono",Menlo,Consolas,monospace;}}
 *{{box-sizing:border-box}} html,body{{margin:0;overflow-x:hidden}}
 body{{background:var(--bg);color:var(--ink);font-family:var(--serif)}}
 .mast{{background:linear-gradient(140deg,#001a44,#00337d 70%,#0b4aa0);color:#fff;padding:28px 22px 22px;border-bottom:3px solid #C4116A}}
 .kick{{font-family:var(--mono);font-size:11.5px;letter-spacing:.22em;text-transform:uppercase;color:#a9c9ea;margin:0 0 8px}}
 .mast h1{{font-family:var(--serif);font-size:clamp(24px,4vw,38px);margin:0;font-weight:700;letter-spacing:-.01em}}
 .mast .wk{{font-family:var(--mono);font-size:12px;color:#cfe0f5;margin-top:10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
 .mast select{{font-family:var(--mono);font-size:12px;background:rgba(255,255,255,.14);color:#fff;border:1px solid rgba(255,255,255,.3);border-radius:6px;padding:4px 8px}}
 .wrap{{max-width:1180px;margin:0 auto;padding:16px 22px 60px}}
 .chips{{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 14px}}
 .chip{{font-family:var(--mono);font-size:12px;font-weight:600;padding:7px 12px;border-radius:20px;border:2px solid transparent;
   cursor:pointer;background:#fff;color:var(--slate);display:flex;align-items:center;gap:7px;user-select:none}}
 .chip .dot{{width:10px;height:10px;border-radius:50%}}
 .chip.active{{color:#fff}}
 .layout{{display:grid;grid-template-columns:1fr 340px;gap:20px}} @media(max-width:860px){{.layout{{grid-template-columns:1fr}}}}
 .mapcard{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px}}
 svg{{width:100%;height:auto;display:block}}
 .state{{fill:#e6ded0;stroke:#fffdf9;stroke-width:.6;cursor:pointer;transition:fill .15s}}
 .state:hover{{stroke:#1b2233;stroke-width:1.2}}
 .lbl{{font-family:var(--mono);font-size:9px;font-weight:600;fill:#b3a894;pointer-events:none;text-anchor:middle;dominant-baseline:central}}
 .lbl.on{{fill:#3a2a2a;font-size:10px}}
 .panel{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px;min-height:220px}}
 .panel h3{{font-family:var(--serif);margin:0 0 4px;font-size:19px;color:var(--navy)}}
 .panel .sub{{font-family:var(--mono);font-size:11px;color:var(--slate);margin-bottom:8px}}
 .bill{{padding:9px 0;border-bottom:1px solid var(--line);font-family:var(--sans);font-size:13px}}
 .bill:last-child{{border-bottom:0}} .bill .bn{{font-family:var(--mono);font-weight:600;color:var(--ink)}}
 .bill a{{color:var(--navy);font-family:var(--mono);font-size:11.5px;text-decoration:none}}
 .stagehdr{{font-family:var(--mono);font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--slate);font-weight:600;margin:12px 0 2px;border-top:1px solid var(--line);padding-top:8px}}
 .stagehdr.enacted{{color:#177a52}} .stagehdr:first-child{{border-top:0;margin-top:0}}
 .hint{{font-family:var(--sans);font-size:13px;color:var(--slate)}}
 .legend{{font-family:var(--sans);font-size:11.5px;color:var(--slate);margin-top:8px}}
 @media(max-width:600px){{
   .mast{{padding:22px 16px 16px}} .mast h1{{font-size:23px}}
   .kick{{font-size:10px;letter-spacing:.1em}}
   .wrap{{padding:12px 14px 46px}}
   .chip{{font-size:11px;padding:6px 10px;white-space:normal;line-height:1.25}}
   .lbl{{display:none}} .lbl.on{{display:block;font-size:15px}}
   .panel{{min-height:120px}}
 }}
</style></head><body>
<div class="mast">
  <p class="kick">Reproductive Access Intelligence // Threat Map &middot; <a href="https://repro-access-intel.vercel.app" style="color:#a9c9ea;text-decoration:none">&lsaquo; back to brief</a></p>
  <h1>Where the threats are moving</h1>
  <div class="wk">Week of <select id="wk"></select> <span id="wknote"></span></div>
</div>
<div class="wrap">
  <div class="chips" id="chips"></div>
  <div class="layout">
    <div class="mapcard">
      <svg id="map" viewBox="0 0 975 610" preserveAspectRatio="xMidYMid meet"></svg>
      <div class="legend">Glow scales with threat level (enacted brightest, introduced dimmest) and bill count. Click a state for its bills. Restrictive-direction bills only.</div>
    </div>
    <div class="panel" id="panel"><div class="hint">Pick an issue above, then click a glowing state to see the bills moving there.</div></div>
  </div>
</div>
<script src="d3.min.js"></script>
<script src="topojson-client.min.js"></script>
<script>
const SNAPS={SNAPS}, FIPS={FIPSJSON}, US={TOPO};
const STAGEW={{enacted:1.0,passed:0.72,committee:0.48,introduced:0.28}};
const STAGES=[["enacted","Enacted into law"],["passed","Passed a chamber"],["committee","In committee"],["introduced","Introduced"]];
const ALL={{id:"__all__",label:"All issues",color:"#00286E"}};
let si=SNAPS.length-1, ISSUES=SNAPS[si].issues, byId={{}}, cur=ALL.id;
function heat(bills){{return (bills||[]).reduce((s,b)=>s+(STAGEW[b.stage]||.28),0);}}
function rebuild(){{byId=Object.fromEntries(ISSUES.map(i=>[i.id,i])); byId[ALL.id]=ALL;}}
function stateHeatFor(iss,ab){{return iss.id===ALL.id?allHeat(ab).h:heat(iss.states[ab]);}}
function allHeat(ab){{ // dominant issue for a state across all issues
  let best=null,h=0; ISSUES.forEach(i=>{{const x=heat(i.states[ab]); if(x>h){{h=x;best=i;}}}}); return {{h,best}};
}}
function maxHeat(iss){{
  if(iss.id===ALL.id){{let m=1; d3.selectAll('.state').each(function(d){{m=Math.max(m,allHeat(FIPS[d.id]).h);}}); return m;}}
  return Math.max(1,...Object.values(iss.states).map(heat));
}}
function drawChips(){{
  const chips=document.getElementById('chips'); chips.innerHTML='';
  [ALL,...ISSUES].forEach(i=>{{
    const c=document.createElement('div'); c.className='chip'+(i.id===cur?' active':'');
    c.style.borderColor=i.color; if(i.id===cur)c.style.background=i.color;
    const cnt=i.id===ALL.id?'':' ('+i.n_states+')';
    c.innerHTML=`<span class="dot" style="background:${{i.color}}"></span>${{i.label}}${{cnt}}`;
    c.onclick=()=>{{cur=i.id;drawChips();paint();document.getElementById('panel').innerHTML='<div class="hint">Click a glowing state to see its bills.</div>';}};
    chips.appendChild(c);
  }});
}}
function paint(){{
  const iss=byId[cur], mx=maxHeat(iss);
  d3.selectAll('.state').each(function(d){{
    const ab=FIPS[d.id]; if(!ab){{return;}}
    let h, color;
    if(iss.id===ALL.id){{const a=allHeat(ab); h=a.h; color=a.best?a.best.color:'#C1272D';}}
    else {{h=heat(iss.states[ab]); color=iss.color;}}
    const r=h/mx;
    this.style.fill = h>0 ? d3.interpolateRgb('#efe7d8',color)(.40+.60*r) : '#e6ded0';
    this.style.filter = h>0 ? `drop-shadow(0 0 ${{5+6*r}}px ${{color}}) drop-shadow(0 0 ${{3+20*r}}px ${{color}})` : 'none';
    this.style.strokeWidth = h>0 ? 1.1 : .6;
  }});
  d3.selectAll('.lbl').each(function(d){{
    const ab=FIPS[d.id]; const on=ab && stateHeatFor(iss,ab)>0;
    this.setAttribute('class','lbl'+(on?' on':''));
  }});
}}
function billRow(b){{return `<div class="bill"><span class="bn">${{b.bill}}</span><br>${{b.title}}<br><a href="${{b.url}}" target="_blank" rel="noopener">open bill &rsaquo;</a></div>`;}}
function stageSections(bills){{let h='';STAGES.forEach(([k,lab])=>{{const g=bills.filter(b=>b.stage===k);if(g.length)h+=`<div class="stagehdr ${{k}}">${{lab}} (${{g.length}})</div>`+g.map(billRow).join('');}});return h;}}
function showState(ab){{
  const p=document.getElementById('panel'), iss=byId[cur];
  if(iss.id===ALL.id){{
    const active=ISSUES.filter(i=>(i.states[ab]||[]).length).sort((a,b)=>heat(b.states[ab])-heat(a.states[ab]));
    if(!active.length){{p.innerHTML=`<div class="hint">No restrictive bills in ${{ab}}.</div>`;return;}}
    p.innerHTML=`<h3>${{ab}}</h3><div class="sub">${{active.length}} issue(s) active</div>`+
      active.map(i=>`<div class="stagehdr" style="color:${{i.color}}">${{i.label}} (${{i.states[ab].length}})</div>`+stageSections(i.states[ab])).join('');
    return;
  }}
  const bills=(iss.states[ab]||[]);
  if(!bills.length){{p.innerHTML=`<div class="hint">No ${{iss.label.toLowerCase()}} bills in ${{ab}}.</div>`;return;}}
  p.innerHTML=`<h3>${{ab}} &middot; ${{iss.label}}</h3><div class="sub">${{bills.length}} restrictive bill(s)</div>`+stageSections(bills);
}}
function drawWeeks(){{
  const sel=document.getElementById('wk'); sel.innerHTML='';
  SNAPS.forEach((s,idx)=>{{const o=document.createElement('option');o.value=idx;o.textContent=s.date;if(idx===si)o.selected=true;sel.appendChild(o);}});
  document.getElementById('wknote').textContent = SNAPS.length>1?`(${{SNAPS.length}} weeks stored)`:'(first snapshot)';
  sel.onchange=()=>{{si=+sel.value;ISSUES=SNAPS[si].issues;rebuild();if(!byId[cur])cur=ALL.id;drawChips();paint();document.getElementById('panel').innerHTML='<div class="hint">Click a glowing state to see its bills.</div>';}};
}}
(function(us){{
  const states=topojson.feature(us,us.objects.states).features, path=d3.geoPath();
  const g=d3.select('#map');
  g.selectAll('path').data(states).enter().append('path').attr('class','state').attr('d',path)
    .on('click',(e,d)=>{{const ab=FIPS[d.id]; if(ab)showState(ab);}});
  g.selectAll('text').data(states).enter().append('text').attr('class','lbl')
    .attr('x',d=>path.centroid(d)[0]).attr('y',d=>path.centroid(d)[1])
    .text(d=>FIPS[d.id]||'');
  rebuild(); drawWeeks(); drawChips(); paint();
  if(location.hash){{const ab=location.hash.slice(1).toUpperCase(); if(Object.values(FIPS).includes(ab)) showState(ab);}}
}})(US);
</script></body></html>"""
    out=os.path.join(_HERE,"map.html")
    open(out,"w").write(html)
    print("wrote",out,f"({len(html)} bytes); issues={len(issues)}; weeks stored={len(snaps)}")

if __name__=="__main__": render()

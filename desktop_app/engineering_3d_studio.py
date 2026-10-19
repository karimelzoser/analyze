"""Enhanced offline engineering 3D explorer with full observed layer controls.

Extends the established three-panel Plotly export rather than replacing its
audited E-W/N-S fence sections. Original SBT zone data are categorized as
zone evidence, not as continuous numeric Ic or laboratory USCS.
"""
from __future__ import annotations

import json
import re
from html import escape
from pathlib import Path

import numpy as np
from engineering_geo_explorer import export_interactive_3d, spatial_points

GROUPS = {
    "sand": ("Sand-like SBT", "#e6b86c"),
    "transition": ("Transitional sand/silt SBT", "#eaa352"),
    "silt": ("Fine-grained/silt-mixture SBT", "#e65f4b"),
    "clay": ("Clay-like/organic SBT", "#8e77c6"),
    "unknown": ("UNKNOWN / unmeasured depth", "#9aa6b2"),
}
ZONE_GROUP = {
    1: "clay", 2: "clay", 3: "clay", 4: "silt", 5: "transition",
    6: "sand", 7: "sand", 8: "transition", 9: "clay"
}


def _category(layer):
    if getattr(layer, "kind", "") == "UNKNOWN":
        return "unknown"
    ic = getattr(layer, "mean_ic", None)
    if ic is None or not np.isfinite(ic):
        return "unknown"
    return ("sand" if ic < 2.50 else "transition" if ic < 2.60
            else "silt" if ic < 2.95 else "clay")


def collect_observed_segments(data):
    """Output only valid, observed segments with explicitly sourced category."""
    points, exclusions = spatial_points(data)
    coordinates = {(p.reference, round(p.x, 4), round(p.y, 4)): p for p in points}
    if not points:
        return [], len(exclusions), (0, 0)
    origin = (min(p.x for p in points), min(p.y for p in points))
    segments = []
    for item in data:
        if isinstance(item, dict):
            ref = str(item.get("reference", ""))
            md = item
        else:
            ref = str(getattr(item, "reference", ""))
            md = getattr(item, "metadata", {}) or {}
        try:
            x, y, ground = (float(md[key]) for key in ("easting", "northing", "ground_elevation"))
        except (KeyError, TypeError, ValueError):
            continue
        key = (ref, round(x, 4), round(y, 4))
        if key not in coordinates or not np.isfinite(ground):
            continue

        if isinstance(item, dict):
            # Cached original source SBT zones are categorical, not numeric Ic.
            zone_rows = item.get("zone_segments", ())
            for layer in zone_rows:
                try:
                    top, bottom, zone = float(layer["start"]), float(layer["end"]), int(layer["zone"])
                except (KeyError, ValueError, TypeError):
                    continue
                if bottom <= top:
                    continue
                category = ZONE_GROUP.get(zone, "unknown")
                segments.append({
                    "ref": ref, "x": x-origin[0], "y": y-origin[1],
                    "top": top, "bottom": bottom, "z0": ground-top, "z1": ground-bottom,
                    "category": category, "source": f"Original XLSB cached SBT Zone {zone}",
                    "zone": zone, "quality": "CACHED ZONE; not numeric Ic"
                })
            if not zone_rows:
                for run in item.get("all_intervals", ()):
                    try:
                        top, bottom = float(run["start_raw"]), float(run["end_raw"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    if bottom > top:
                        segments.append({
                            "ref": ref, "x": x-origin[0], "y": y-origin[1],
                            "top": top, "bottom": bottom, "z0": ground-top, "z1": ground-bottom,
                            "category": "silt", "source": "Original XLSB cached positive zone-screen",
                            "zone": None, "quality": "OTHER DEPTHS UNCLASSIFIED; source lacks zone profile"
                        })
        else:
            from engineering_layers import from_analysis
            try:
                result = from_analysis(item)
            except (ValueError, TypeError, AttributeError, IndexError):
                continue
            for layer in result.layers:
                top, bottom = float(layer.start_m), float(layer.end_m)
                if bottom <= top:
                    continue
                cat = _category(layer)
                segments.append({
                    "ref": ref, "x": x-origin[0], "y": y-origin[1],
                    "top": top, "bottom": bottom, "z0": ground-top, "z1": ground-bottom,
                    "category": cat, "source": "Raw CPT Ic-based observed SBT",
                    "zone": None, "quality": str(layer.status),
                    "ic": layer.mean_ic if layer.mean_ic is not None else None,
                })
    return segments, len(exclusions), origin


PANEL_CSS = """
<style id="cpt-studio-theme">
body {background:#f4f7fb!important;color:#19334b;font-family:Segoe UI,Inter,Arial,sans-serif}
#cpt-studio {margin:12px 18px;padding:15px 18px;background:#fff;border:1px solid #dae4ef;
 box-shadow:0 3px 14px #1833490c;border-radius:14px;}
#cpt-studio h2 {font-size:18px;letter-spacing:-.3px;margin:0 0 7px;}
#cpt-studio .hint {color:#5d6e81;font-size:12px;line-height:1.5;}
.cpt-options {display:flex;flex-wrap:wrap;gap:11px 22px;align-items:center;margin:13px 0 10px}
.cpt-toggle {font-size:12px;white-space:nowrap;color:#233b52;cursor:pointer}
.cpt-toggle input {margin-right:5px;accent-color:#20547c;}
.cpt-dot {display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:4px}
.cpt-range {display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:9px 12px;
 border:1px solid #d9e4ef;border-radius:9px;background:#f7fafc;font-size:12px}
.cpt-range input[type=range] {width:205px;max-width:24vw;accent-color:#236596}
.cpt-range output {min-width:50px;color:#1d4d75;font-weight:700}
.cpt-range button,.cpt-range select {border:1px solid #bccddd;background:#fff;padding:7px 10px;
 border-radius:7px;color:#17354b;font:inherit;cursor:pointer}
.cpt-range button:hover {background:#e7f1fa}
#cpt-summary {font-size:12px;color:#50657b;margin:8px 0 0}
@media(max-width:760px){#cpt-studio{margin:8px;padding:10px}.cpt-range input[type=range]{width:130px}}
</style>
"""


def _control_html(segments, excluded):
    counts = {k:sum(s["category"] == k for s in segments) for k in GROUPS}
    choices = "".join(
        f'<label class="cpt-toggle"><input type="checkbox" data-layer="{k}" checked>'
        f'<span class="cpt-dot" style="background:{colour}"></span>'
        f'{escape(label)} ({counts[k]:,})</label>'
        for k,(label,colour) in GROUPS.items()
    )
    return (
        '<section id="cpt-studio" aria-label="CPT 3D model controls">'
        '<h2>3D soil-behaviour explorer</h2>'
        '<div class="hint">Separate observed SBT bands, source provenance and unknown portions. '
        'Any transparent inter-CPT wedge is interpretive, not measured geology. '
        'Rotate by dragging the model; use the mouse wheel to zoom.</div>'
        f'<div class="cpt-options">{choices}'
        '<label class="cpt-toggle"><input type="checkbox" id="cpt-wedges">Indicative wedges</label>'
        '</div><div class="cpt-range">'
        '<label for="cpt-top">Top BGL</label><input type="range" id="cpt-top" min="0" max="10" step="0.1" value="0">'
        '<output id="cpt-top-value">0.0 m</output>'
        '<label for="cpt-bottom">Bottom BGL</label><input type="range" id="cpt-bottom" min="0" max="10" step="0.1" value="10">'
        '<output id="cpt-bottom-value">10.0 m</output>'
        '<button id="cpt-reset" type="button">All depths</button>'
        '<label for="cpt-camera">View</label><select id="cpt-camera">'
        '<option value="isometric">Isometric</option><option value="plan">Top / plan</option>'
        '<option value="east">E-W view</option><option value="north">N-S view</option></select>'
        '<button id="cpt-scale" type="button">True XY/RL scale</button>'
        '</div>'
        f'<div id="cpt-summary" role="status">{len(segments):,} sourced layer segments; '
        f'{excluded} withheld coordinate record(s). Depth ranges are relative to each sounding ground level.</div>'
        '</section>')


def _script(segment_data, chart_id):
    # JSON_HEX_TAG avoids premature </script> termination through names.
    packed = json.dumps(segment_data, separators=(",",":"), ensure_ascii=True).replace("<","\\u003c")
    name = json.dumps(chart_id)
    return r"""
<script id="cpt-studio-interactivity">
(function(){
"use strict";
const SEGMENTS=__SEGMENTS__, CHART=__CHART__;
const COLORS={sand:"#e6b86c",transition:"#eaa352",silt:"#e65f4b",clay:"#8e77c6",unknown:"#9aa6b2"};
const LABELS={sand:"Sand-like SBT",transition:"Transitional SBT",silt:"Silt-mixture SBT",
              clay:"Clay/organic-like SBT",unknown:"UNKNOWN sensor coverage"};
const categories=Object.keys(COLORS);
const checkbox=k=>document.querySelector('[data-layer="'+k+'"]');
const $=id=>document.getElementById(id);
function start(){
 const gd=$(CHART);
 if(!gd||!window.Plotly||!gd.data||!gd.data.length) return;
 const originalN=gd.data.length;
 let fullDepth=Math.max(1,...SEGMENTS.map(x=>x.bottom));
 let minimum=Math.min(0,...SEGMENTS.map(x=>x.top));
 const maximum=Math.ceil(fullDepth*10)/10;
 $("cpt-top").max=maximum;$("cpt-bottom").max=maximum;
 $("cpt-top").value=minimum;$("cpt-bottom").value=maximum;
 // Legacy gold/red lines are intentionally hidden when the richer source
 // SBT categories are available. Gray observed sounding remains visible.
 let oldIndices=[];
 gd.data.forEach((trace,i)=>{
   if(/Other observed CPT behavior|Observed SBT-screen layers/.test(trace.name||"")) oldIndices.push(i);
 });
 if(oldIndices.length) Plotly.restyle(gd,{visible:false},oldIndices);
 // Volumetric symbol per measured CPT depth interval. Each mesh has
 // a small, FIXED schematic footprint. Nothing is interpolated between
 // sites; only the separate interpreted 3-CPT wedges imply continuity.
 let models=categories.map(k=>({
   type:"mesh3d",name:LABELS[k]+" · observed soil blocks",
   x:[],y:[],z:[],i:[],j:[],k:[],text:[],
   hoverinfo:"text",flatshading:true,
   legendgroup:"studio-"+k,showlegend:true,
   color:COLORS[k],opacity:k==="unknown"?.17:.88,visible:true
 }));
 Plotly.addTraces(gd,models).then(()=>{
   const idx=Object.fromEntries(categories.map((k,i)=>[k,originalN+i]));
   const wedges=gd.data.map((trace,i)=>/Interpreted silt-like wedge/.test(trace.name||"")?i:-1).filter(i=>i>=0);
   if(wedges.length)Plotly.restyle(gd,{visible:false},wedges);
   const maxLabel=$("cpt-summary");
   function redraw(){
      let lo=Number($("cpt-top").value), hi=Number($("cpt-bottom").value);
      if(hi<=lo){hi=Math.min(maximum,lo+0.1);$("cpt-bottom").value=hi}
      $("cpt-top-value").textContent=lo.toFixed(1)+" m";
      $("cpt-bottom-value").textContent=hi.toFixed(1)+" m";
      let rendered=0,cpts=new Set();
      let updates={x:[],y:[],z:[],i:[],j:[],k:[],text:[],visible:[]};
      for(const category of categories){
        const xs=[],ys=[],zs=[],texts=[],ii=[],jj=[],kk=[];
        for(const s of SEGMENTS){
          if(s.category!==category||s.bottom<=lo||s.top>=hi)continue;
          const top=Math.max(s.top,lo),bottom=Math.min(s.bottom,hi);
          if(!(bottom>top))continue;
          const ztop=s.z0-(top-s.top),zbottom=s.z0-(bottom-s.top);
          // Visual footprint is schematic (2m width), not claimed soil
          // influence radius or actual layer correlation.
          const w=1.0,x=s.x,y=s.y;
          const vx=[x-w,x+w,x+w,x-w,x-w,x+w,x+w,x-w];
          const vy=[y-w,y-w,y+w,y+w,y-w,y-w,y+w,y+w];
          const vz=[zbottom,zbottom,zbottom,zbottom,ztop,ztop,ztop,ztop];
          const base=xs.length;
          xs.push(...vx);ys.push(...vy);zs.push(...vz);
          const faces=[[0,1,2],[0,2,3],[4,5,6],[4,6,7],
                       [0,1,5],[0,5,4],[1,2,6],[1,6,5],
                       [2,3,7],[2,7,6],[3,0,4],[3,4,7]];
          for(const face of faces){
            ii.push(base+face[0]);jj.push(base+face[1]);kk.push(base+face[2]);
          }
          const hover="<b>"+s.ref+"</b><br>"+s.source+"<br>Measured BGL "+
             top.toFixed(2)+"–"+bottom.toFixed(2)+" m<br>"+s.quality+
             "<br>Colored column is a CPT profile SYMBOL, not continuous geology";
          for(let vertex=0;vertex<8;vertex++)texts.push(hover);
          rendered++;cpts.add(s.ref);
        }
        updates.x.push(xs);updates.y.push(ys);updates.z.push(zs);
        updates.i.push(ii);updates.j.push(jj);updates.k.push(kk);
        updates.text.push(texts);
        updates.visible.push(!!checkbox(category).checked);
      }
      Plotly.restyle(gd,updates,categories.map(k=>idx[k]));
      if(wedges.length)Plotly.restyle(gd,{visible:$("cpt-wedges").checked},wedges);
      maxLabel.textContent=rendered+" shown observed segments / "+cpts.size+
         " measured soil blocks at "+cpts.size+" surveyed CPTs, "+lo.toFixed(1)+"–"+hi.toFixed(1)+
         " m BGL. Blocks are schematic; unmeasured gaps remain UNKNOWN.";
   }
   categories.forEach(k=>checkbox(k).addEventListener("change",redraw));
   $("cpt-wedges").addEventListener("change",redraw);
   $("cpt-top").addEventListener("input",redraw);
   $("cpt-bottom").addEventListener("input",redraw);
   $("cpt-reset").addEventListener("click",()=>{$("cpt-top").value=0;$("cpt-bottom").value=maximum;redraw()});
   $("cpt-camera").addEventListener("change",event=>{
     const eyes={isometric:{x:1.65,y:-1.65,z:1.18},plan:{x:.001,y:.001,z:2.6},
                 east:{x:0,y:-2.5,z:.40},north:{x:-2.5,y:0,z:.40}};
     Plotly.relayout(gd,{"scene.camera.eye":eyes[event.target.value]});
   });
   let original=false;
   $("cpt-scale").addEventListener("click",()=>{
     original=!original;
     Plotly.relayout(gd,original?{"scene.aspectmode":"data"}:
        {"scene.aspectmode":"manual","scene.aspectratio":{x:1.45,y:1.25,z:.75}});
     $("cpt-scale").textContent=original?"Readable depth scale":"True XY/RL scale";
   });
   redraw();
 });
}
if(document.readyState==="complete")setTimeout(start,80);
else window.addEventListener("load",()=>setTimeout(start,80),{once:true});
})();
</script>""".replace("__SEGMENTS__",packed).replace("__CHART__",name)


def export_professional_3d(data,path,*,boundary=None,warning_m=.10,
                           high_m=.30,max_spacing_m=None):
    output=Path(path)
    base=export_interactive_3d(data,output,boundary=boundary,
        warning_m=warning_m,high_m=high_m,max_spacing_m=max_spacing_m)
    segments,outliers,origin=collect_observed_segments(data)
    source=output.read_text(encoding="utf-8")
    # The first Plotly plot is the measured 3D scene, followed by two fence
    # section figures. Do not change the fence plot IDs.
    found=re.search(r'Plotly\.newPlot\(\s*"([^"]+)"',source)
    if not found:
        raise ValueError("Expected offline Plotly scene missing from source exporter")
    controls=PANEL_CSS+_control_html(segments,outliers)
    # Put controls immediately below the short source legend, ABOVE the
    # primary 3D canvas. Appending below both fence charts makes them invisible
    # to most people until they scroll several screens.
    opening=re.search(r"<body[^>]*>",source,re.IGNORECASE)
    if not opening:
        raise ValueError("Expected HTML body missing")
    anchor=source.find("</div>",opening.end())
    if anchor>=0:
        cut=anchor+len("</div>")
        source=source[:cut]+controls+source[cut:]
    else:
        cut=opening.end()
        source=source[:cut]+controls+source[cut:]
    source=source.replace("</body>",_script(segments,found.group(1))+"</body>",1)
    output.write_text(source,encoding="utf-8")
    return {**base,"observed_segments":len(segments),
            "categories":{k:sum(x["category"]==k for x in segments) for k in GROUPS}}

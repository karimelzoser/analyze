"""Responsive 2D/3D map UX extension for the offline CPT model.

This retains all measured 3D blocks and original 2 fence sections. The map
adds a bounded 2D categorical soil view, magnitude colors for layer thickness,
linked CPT inspection, compact full-height layout and export controls.
"""
from __future__ import annotations

import json
from pathlib import Path

from engineering_geo_explorer import spatial_points, _triangle_mask
from engineering_3d_studio import collect_observed_segments
import numpy as np


STYLE=r"""
<style id="cpt-atlas-style">
body{background:#eef3f7!important;font-family:Segoe UI,Inter,Arial,sans-serif}
#cpt-atlas-header{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:12px 16px;
 background:#fff;border-bottom:1px solid #d9e4ed;position:sticky;top:0;z-index:12}
#cpt-atlas-header strong{font-size:19px;letter-spacing:-.5px;color:#123851;margin-right:12px}
#cpt-atlas-header button,#cpt-atlas-header select,#cpt-atlas-header input{font:13px Segoe UI,Arial,sans-serif}
#cpt-atlas-header button{border:1px solid #c8d9e6;background:#fff;color:#1b526d;
 border-radius:8px;padding:9px 13px;cursor:pointer;font-weight:650}
#cpt-atlas-header button.chosen{color:#fff;background:#0d648b;border-color:#0d648b}
#cpt-atlas-header select,#cpt-atlas-header input{border:1px solid #c8d9e6;border-radius:7px;padding:8px;background:#fff}
#cpt-atlas-header label{font-size:11px;text-transform:uppercase;color:#627a8d;font-weight:700}
#cpt-atlas-screen{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:0;height:calc(100vh - 66px);
 min-height:570px;margin:0;background:white}
#cpt-atlas-map{min-width:0;display:flex;flex-direction:column;overflow:hidden}
#cpt-atlas-graphs{position:relative;flex:1;min-height:250px;overflow:hidden}
#cpt-atlas-graphs>.plotly-graph-div,#cpt-atlas-graphs>#cpt-atlas-2d{height:100%!important;width:100%!important}
#cpt-atlas-graphs .plot-container{height:100%!important}
#cpt-atlas-info{border-top:1px solid #e0e8ef;background:#f5f9fc;padding:7px 16px;
 font-size:12px;color:#4d697d;min-height:31px}
#cpt-atlas-aside{border-left:1px solid #d9e4ed;background:#f7fafc;overflow-y:auto;padding:14px}
.atlas-panel{background:#fff;border:1px solid #dfebf2;border-radius:10px;padding:13px;margin-bottom:12px;
 box-shadow:0 2px 8px #123b5709}
.atlas-panel h3{margin:0 0 7px;font-size:13px;color:#163d56}
.atlas-panel small,.atlas-note{font-size:11px;color:#60788c;line-height:1.5}
.atlas-panel table{width:100%;border-collapse:collapse;font-size:12px}
.atlas-panel td{padding:5px 3px;border-bottom:1px solid #eef2f6;vertical-align:top}
.atlas-panel td:last-child{text-align:right;font-weight:650;color:#193c53}
.atlas-gradient{height:11px;border-radius:6px;background:linear-gradient(90deg,#31688e,#35b779,#fde725,#ef8629,#b61c49);
 margin:6px 0}.atlas-minmax{display:flex;justify-content:space-between;color:#587285;font-size:10px}
#cpt-atlas-rank button{border:0;background:none;text-align:left;color:#146790;display:block;
 padding:4px 1px;cursor:pointer;font-size:12px}
#cpt-atlas-details{overflow-wrap:anywhere}
#cpt-atlas-details h2{font-size:17px;margin:0 0 5px}
#cpt-atlas-details summary{cursor:pointer;font-size:12px;font-weight:bold}
#cpt-atlas-details .atlas-layers{max-height:205px;overflow:auto}
#cpt-studio{margin:0!important;border:0!important;border-bottom:1px solid #d7e4ed!important;
 padding:7px 13px!important;border-radius:0!important;box-shadow:none!important}
#cpt-studio h2,#cpt-studio .hint{display:none}
#cpt-studio .cpt-options{margin:5px 0;gap:9px 12px}
#cpt-studio .cpt-range{margin:5px 0;padding:5px 7px;border:0}
#cpt-studio .cpt-range input[type=range]{width:105px}
.atlas-hide{display:none!important}
.atlas-pill{background:#eff6fb;border-radius:7px;padding:6px 10px}
.atlas-visual-note{font-size:11px;color:#715f43;padding:9px;background:#fff8ea;border-left:3px solid #dba54d}
.atlas-toolbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;padding:8px 14px;background:#f5f9fc;border-bottom:1px solid #dce6ed}
.atlas-toolbar input[type=range]{width:140px}
.atlas-toolbar span{font-size:12px;color:#566e80}
.atlas-toolbar strong{color:#0e658b}
.atlas-fences{padding:0 12px 10px;background:#f4f8fb}
.atlas-fences summary{padding:12px;cursor:pointer;font-weight:700}
#cpt-atlas-2d{position:absolute;inset:0;z-index:2;background:#fff}
#cpt-atlas-header button:focus-visible,#cpt-atlas-rank button:focus-visible{
 outline:3px solid #4ca8dc;outline-offset:2px}
body.atlas-focus-map #cpt-atlas-screen{grid-template-columns:minmax(0,1fr)!important}
body.atlas-focus-map #cpt-atlas-aside{display:none}
#cpt-atlas-header button:hover{background:#e6f3fa;border-color:#69a4c9}
#cpt-atlas-header button.chosen:hover{background:#075278;color:#fff}
#atlas-depth-number{width:67px;text-align:center}
#cpt-atlas-aside{scrollbar-gutter:stable}
#cpt-atlas-graphs .modebar-container{z-index:10}
@media (max-height:760px){#cpt-atlas-screen{min-height:440px}
 #cpt-atlas-header{padding:7px 13px;gap:7px}
 #cpt-studio .cpt-options{margin:3px 0}
}
@media(max-width:970px){
 #cpt-atlas-screen{grid-template-columns:minmax(0,1fr) 260px}
 #cpt-atlas-header strong{font-size:16px}
}
@media(max-width:680px){
 #cpt-atlas-screen{display:flex;flex-direction:column;height:auto}
 #cpt-atlas-map{height:76vh;min-height:570px}
 #cpt-atlas-aside{overflow:visible}
}
</style>
"""

SCRIPT=r"""
<script id="cpt-atlas-interactive-upgrade">
(function(){
"use strict";
const SOURCE=__SOURCE__, SEG=__SEG__, FACES=__FACES__, BOUND=__BOUND__, TARGET=__TARGET__;
const COLORS={sand:"#edc96f",transition:"#efa55a",silt:"#67b4af",clay:"#9a83c3",unknown:"#9ca7b4"};
const CLASSES=["sand","transition","silt","clay"];
const PALETTE=[[49,104,142],[53,183,121],[249,214,67],[235,112,47],[176,22,64]];
const $=id=>document.getElementById(id);
const fmt=(value,n=2)=>value===null||value===undefined||!Number.isFinite(Number(value))?"—":Number(value).toFixed(n);
const clean=s=>String(s??"").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
const maxval=Math.max(.01,...SOURCE.map(p=>p.max||0));
let active2d=false,selected=null,depth=4.5,navMode="pan";
let mainGraph=null,mainPanel=null;
const byref=Object.fromEntries(SOURCE.map(p=>[p.ref,p]));
const segmap={};
SEG.forEach(s=>{(segmap[s.ref]??=[]).push(s)});
Object.values(segmap).forEach(v=>v.sort((a,b)=>a.top-b.top));
function ramp(v,m=maxval){
 let t=Math.min(.999999,Math.max(0,(v||0)/Math.max(.01,m)))*4;
 let k=Math.floor(t),f=t-k;
 return "#"+PALETTE[k].map((a,j)=>Math.round(a+(PALETTE[k+1][j]-a)*f).toString(16).padStart(2,"0")).join("");
}
function zone(p,z){
 const s=(segmap[p.ref]||[]).find(s=>z>=s.top-.00001&&z<s.bottom-.00001);
 return s&&s.category!=="unknown"?s:null;
}
function value(p){
 return $("atlas-mode").value==="max"?p.max:$("atlas-mode").value==="cum"?p.cum:
        $("atlas-mode").value==="start"?p.start:$("atlas-mode").value==="depth"?p.depth:null;
}
function sampleAt(p,z){
 if(!p.samples||!p.samples.length)return null;
 let chosen=null,gap=Infinity;
 for(const row of p.samples){
   const d=Math.abs(row[0]-z);
   if(d<gap){gap=d;chosen=row}
 }
 return chosen&&gap<=.055&&chosen[8]?chosen:null;
}
function hover(p){
 const layer=zone(p,depth),sample=sampleAt(p,depth);
 return "<b>"+clean(p.ref)+"</b><br>Easting "+fmt(p.east,3)+" · Northing "+fmt(p.north,3)+
  "<br>Ground RL "+fmt(p.rl,3)+" m · CPT depth "+fmt(p.depth,2)+
  " m<br>Max silt "+fmt(p.max,3)+" m · Cumulative "+fmt(p.cum,3)+
  " m<br>"+(layer?layer.category+" · "+fmt(layer.top,2)+"–"+fmt(layer.bottom,2)+" m BGL":"UNKNOWN at selected depth")+
  (sample?"<br>qc "+fmt(sample[1],2)+" MPa · fs "+fmt(sample[2],4)+
       " MPa · u2 "+fmt(sample[3],4)+" MPa<br>Ic "+fmt(sample[7],3)+
       " · Fr "+fmt(sample[5],2)+"% · Qtn "+fmt(sample[6],2):
       "<br>Raw measurement at this depth: unavailable")+
  "<br>"+clean(p.status)+"<extra></extra>";
}
function inspect(p){
 if(!p)return;
 selected=p.ref;
 const blocks=(segmap[p.ref]||[]);
 let rows=[["Easting",fmt(p.east,3)+" m"],["Northing",fmt(p.north,3)+" m"],
  ["Ground elevation",fmt(p.rl,3)+" m"],["Test depth",fmt(p.depth,2)+" m"],
  ["Maximum silt",fmt(p.max,3)+" m"],["Cumulative silt",fmt(p.cum,3)+" m"],
  ["First silt start",fmt(p.start,2)+" m"],["Source",clean(p.source)],["Status",clean(p.status)]];
 let table=rows.map(r=>"<tr><td>"+r[0]+"</td><td>"+r[1]+"</td></tr>").join("");
 let at=zone(p,depth),raw=sampleAt(p,depth);
 if(raw){
   rows.push(["qc at "+fmt(depth,2)+"m",fmt(raw[1],3)+" MPa"],
             ["fs at depth",fmt(raw[2],5)+" MPa"],
             ["u2 at depth",fmt(raw[3],5)+" MPa"],
             ["qt at depth",fmt(raw[4],3)+" MPa"],
             ["Fr at depth",fmt(raw[5],3)+"%"],
             ["Qtn at depth",fmt(raw[6],3)],
             ["Ic at depth",fmt(raw[7],3)]);
   table=rows.map(r=>"<tr><td>"+r[0]+"</td><td>"+r[1]+"</td></tr>").join("");
 }
 let detail=blocks.slice(0,320).map(x=>"<tr><td>"+fmt(x.top,2)+"–"+fmt(x.bottom,2)+" m</td><td>"+x.category+"</td><td>"+fmt(x.bottom-x.top,3)+"</td></tr>").join("");
 $("cpt-atlas-details").innerHTML="<h2>"+clean(p.ref)+"</h2><p class='atlas-note'>"+
 (at?("Depth "+fmt(depth,2)+" m: "+at.category+" / "+fmt(at.ic,3)+" Ic"):("Depth "+fmt(depth,2)+" m: no valid classification"))+
 "</p><table>"+table+"</table><details><summary>"+blocks.length+
 " measured/cached soil intervals · expand</summary><div class='atlas-layers'><table>"+
 "<tr><th>BGL</th><th>SBT</th><th>Thickness</th></tr>"+detail+"</table></div></details>";
 if(active2d)render2d();
}
function display(){
 const type=$("atlas-mode").value;
 const cats=SOURCE.map(p=>{let s=zone(p,depth);return s?CLASSES.indexOf(s.category):-1});
 const vals=SOURCE.map(p=>type==="soil"?(cats[SOURCE.indexOf(p)]<0?null:cats[SOURCE.indexOf(p)]):value(p));
 const xx=SOURCE.map(p=>p.x),yy=SOURCE.map(p=>p.y);
 const xmin=Math.min(...xx)-10,xmax=Math.max(...xx)+10,ymin=Math.min(...yy)-10,ymax=Math.max(...yy)+10;
 let N=96,M=96;
 const xs=Array.from({length:N},(_,i)=>xmin+(xmax-xmin)*i/(N-1));
 const ys=Array.from({length:M},(_,i)=>ymin+(ymax-ymin)*i/(M-1));
 let z=Array.from({length:M},()=>Array(N).fill(null));
 for(const [a,b,c] of FACES){
  if([a,b,c].some(i=>vals[i]===null||vals[i]===undefined||SOURCE[i].status==="REVIEW"))continue;
  const A=SOURCE[a],B=SOURCE[b],D=SOURCE[c];
  const den=(B.y-D.y)*(A.x-D.x)+(D.x-B.x)*(A.y-D.y);
  if(Math.abs(den)<1e-9)continue;
  const ix0=Math.max(0,Math.floor((Math.min(A.x,B.x,D.x)-xmin)/(xmax-xmin)*(N-1))),
    ix1=Math.min(N-1,Math.ceil((Math.max(A.x,B.x,D.x)-xmin)/(xmax-xmin)*(N-1)));
  const iy0=Math.max(0,Math.floor((Math.min(A.y,B.y,D.y)-ymin)/(ymax-ymin)*(M-1))),
    iy1=Math.min(M-1,Math.ceil((Math.max(A.y,B.y,D.y)-ymin)/(ymax-ymin)*(M-1)));
  for(let j=iy0;j<=iy1;j++)for(let i=ix0;i<=ix1;i++){
   const w1=((B.y-D.y)*(xs[i]-D.x)+(D.x-B.x)*(ys[j]-D.y))/den;
   const w2=((D.y-A.y)*(xs[i]-D.x)+(A.x-D.x)*(ys[j]-D.y))/den,w3=1-w1-w2;
   if(Math.min(w1,w2,w3)<-1e-8)continue;
   z[j][i]=type==="soil"?vals[w1>=w2&&w1>=w3?a:w2>=w3?b:c]:
     w1*vals[a]+w2*vals[b]+w3*vals[c];
  }
 }
 return {xs,ys,z,vals};
}
function render2d(){
 if(!active2d)return;
 const type=$("atlas-mode").value;
 const g=display();
 const soilColors=[[0,COLORS.sand],[.249,COLORS.sand],[.25,COLORS.transition],[.499,COLORS.transition],
 [.5,COLORS.silt],[.749,COLORS.silt],[.75,COLORS.clay],[1,COLORS.clay]];
 const continuous=[[0,"#31688e"],[.25,"#35b779"],[.5,"#f9d643"],[.75,"#eb702f"],[1,"#b01640"]];
 const nums=g.vals.filter(v=>Number.isFinite(v));
 const vmax=type==="soil"?3:Math.max(.1,...nums);
 let pmap={type:"heatmap",x:g.xs,y:g.ys,z:g.z,zsmooth:false,hoverinfo:"skip",
  colorscale:type==="soil"?soilColors:continuous,opacity:.72,zmin:0,zmax:vmax,
  showscale:type!=="soil",colorbar:{title:{text:type==="max"?"Max layer (m)":"BGL / thickness (m)",side:"right"},thickness:13}};
 const markers={type:"scattergl",mode:"markers",name:"CPT observations",
  x:SOURCE.map(p=>p.x),y:SOURCE.map(p=>p.y),customdata:SOURCE.map((p,i)=>i),
  marker:{size:SOURCE.map(p=>p.ref===selected?16:10),
   color:SOURCE.map((p,i)=>type==="soil"?(g.vals[i]===null?"#9ca3af":
    [COLORS.sand,COLORS.transition,COLORS.silt,COLORS.clay][g.vals[i]]):
    value(p)===null?"#9ca3af":ramp(value(p),vmax)),
   line:{color:"#fff",width:1.4}},
  hovertemplate:SOURCE.map(p=>hover(p)),showlegend:false};
 const outline=BOUND&&BOUND.length?[{type:"scatter",mode:"lines",
  x:[...BOUND,BOUND[0]].map(r=>r[0]),y:[...BOUND,BOUND[0]].map(r=>r[1]),
  line:{color:"#263e55",width:2},hoverinfo:"skip",showlegend:false}]:[];
 const layout={paper_bgcolor:"#fff",plot_bgcolor:"#f9fcff",
  margin:{l:60,r:type==="soil"?17:84,t:43,b:57},
  dragmode:navMode,hovermode:"closest",uirevision:"cpt-atlas-pan",
  xaxis:{title:{text:"Easting offset from "+fmt(SOURCE[0].east-SOURCE[0].x,1)+" m"},
   range:[g.xs[0],g.xs[g.xs.length-1]],showgrid:true,gridcolor:"#e3edf4"},
  yaxis:{title:{text:"Northing offset from "+fmt(SOURCE[0].north-SOURCE[0].y,1)+" m"},
   range:[g.ys[0],g.ys[g.ys.length-1]],scaleanchor:"x",scaleratio:1,gridcolor:"#e3edf4"},
  title:{text:type==="soil"?"Soil behavior at "+fmt(depth,2)+" m below ground":"Thickness / depth map · "+type,
   x:.02,font:{size:16,color:"#244258"}}};
 Plotly.react("cpt-atlas-2d",[pmap,...outline,markers],layout,{responsive:true,
  scrollZoom:true,displaylogo:false}).then(()=>{
  const el=$("cpt-atlas-2d");
  if(!el._atlasBound){
   el.on("plotly_click",evt=>{
    let event=evt.points.find(e=>e.customdata!==undefined);
    if(event)inspect(SOURCE[event.customdata]);
   });
   el._atlasBound=true;
  }
 });
 $("cpt-atlas-status").textContent=SOURCE.length+" surveyed CPTs · "+FACES.length+
  " supported triangles · "+depth.toFixed(2)+"m BGL. Colored areas are INTERPRETED; markers are MEASURED.";
}
function show3d(){
 active2d=false;$("cpt-atlas-2d").classList.add("atlas-hide");
 mainGraph.classList.remove("atlas-hide");$("atlas-2d").classList.remove("chosen");$("atlas-3d").classList.add("chosen");
 $("atlas-depth-tools").classList.add("atlas-hide");$("cpt-studio").classList.remove("atlas-hide");
 Plotly.relayout(mainGraph,{height:$("cpt-atlas-graphs").clientHeight,width:$("cpt-atlas-graphs").clientWidth});
 setTimeout(recolor3d,120);
 $("cpt-atlas-status").textContent="Observed CPT blocks · drag to rotate · wheel to zoom. Silt layer color varies by measured thickness.";
}
function show2d(){
 active2d=true;mainGraph.classList.add("atlas-hide");
 $("cpt-atlas-2d").classList.remove("atlas-hide");$("atlas-3d").classList.remove("chosen");$("atlas-2d").classList.add("chosen");
 $("cpt-studio").classList.add("atlas-hide");$("atlas-depth-tools").classList.remove("atlas-hide");
 render2d();setTimeout(()=>Plotly.Plots.resize($("cpt-atlas-2d")),60);
}
function recolor3d(){
 // Layer mesh colors and depth-window recalculation are owned by the 3D
 // studio renderer. Avoid racing its valid per-block thickness palette with
 // an array that assumes an incorrect scene vertex ordering.
}
function init(){
 mainGraph=$(TARGET);if(!mainGraph||!window.Plotly)return;
 const visual=mainGraph.parentNode;
 let host=document.createElement("div");host.id="cpt-atlas-screen";
 host.innerHTML="<div id='cpt-atlas-map'><div id='cpt-atlas-graphs'></div>"+
 "<div id='cpt-atlas-info'><span id='cpt-atlas-status'>Zoom and click any surveyed CPT</span></div></div>"+
 "<aside id='cpt-atlas-aside'>"+
 "<section class='atlas-panel'><h3>PROJECT THICKNESS</h3><div style='font-size:20px;font-weight:750;color:#1d5d81'>"+
 fmt(maxval,3)+" m <small>maximum observed SBT-screen</small></div>"+
 "<div class='atlas-gradient'></div><div class='atlas-minmax'><span>0.00 m</span><span>"+
 fmt(maxval/2,2)+" m</span><span>"+fmt(maxval,2)+" m</span></div>"+
 "<p class='atlas-note'>Continuous thickness scale is separate from the soil-type legend.</p></section>"+
 "<section class='atlas-panel'><h3>SOIL BEHAVIOR CLASSES</h3>"+
 "<p class='atlas-note'><span style='color:#edc96f'>■</span> Sand-like SBT &nbsp;"+
 "<span style='color:#efa55a'>■</span> Transitional sand/silt<br>"+
 "<span style='color:#67b4af'>■</span> Silt-mixture-like &nbsp;"+
 "<span style='color:#9a83c3'>■</span> Clay/organic-like<br>"+
 "<span style='color:#9ca7b4'>■</span> Unknown / invalid observations</p></section>"+
 "<section class='atlas-panel'><h3>INSPECT SELECTED CPT</h3><div id='cpt-atlas-details' class='atlas-note'>"+
 "Hover or click a measured CPT point; every point remains selectable.</div></section>"+
 "<section class='atlas-panel'><h3>THICKEST SOIL-SCREEN LAYERS</h3><div id='cpt-atlas-rank'></div></section>"+
 "<section class='atlas-panel'><h3>THINNEST POSITIVE SILT LAYERS</h3><div id='cpt-atlas-minrank'></div></section>"+
 "<section class='atlas-panel atlas-visual-note'>Interpreted soil zones are NOT observed geology between tests. "+
 "Unmeasured sensor depths remain unknown. No geotechnical design acceptance inferred.</section></aside>";
 let head=document.createElement("div");head.id="cpt-atlas-header";
 head.innerHTML="<strong>CPT ATLAS / Engineering soil maps</strong>"+
 "<button id='atlas-2d' class='chosen'>2D SOIL PLAN</button><button id='atlas-3d'>3D SUBSURFACE</button>"+
 "<label for='atlas-mode'>MAP VALUE</label><select id='atlas-mode'>"+
 "<option value='soil'>Soil behavior at depth</option><option value='max'>Max observed silt thickness</option>"+
 "<option value='cum'>Cumulative silt thickness</option><option value='start'>First silt-screen depth</option>"+
 "<option value='depth'>Test termination depth</option></select>"+
 "<input type='search' id='atlas-find' placeholder='Find CPT reference' aria-label='Find CPT reference'>"+
 "<button id='atlas-pan' class='chosen'>PAN</button><button id='atlas-box'>BOX ZOOM</button>"+
 "<button id='atlas-zoom-in'>ZOOM +</button><button id='atlas-zoom-out'>ZOOM −</button>"+
 "<button id='atlas-fit'>FIT VIEW</button><button id='atlas-save'>SAVE PNG</button>"+
 "<button id='atlas-expand'>HIDE DETAILS</button><button id='atlas-full'>FULL SCREEN</button>";
 let bar=document.createElement("div");bar.className="atlas-toolbar";bar.id="atlas-depth-tools";
 bar.innerHTML="<span>Depth below ground</span><input type='range' id='atlas-depth' min='0' max='15' step='.05' value='4.5'>"+
 "<strong id='atlas-depth-label'>4.50 m</strong>"+
 "<label for='atlas-depth-number'>SET DEPTH</label><input type='number' id='atlas-depth-number' step='.05' min='0' value='4.5'>"+
 "<span>Wheel to zoom · drag to pan · click a surveyed CPT to inspect</span>";
 document.body.insertBefore(head,document.body.firstChild);
 document.body.insertBefore(bar,head.nextSibling);
 document.body.insertBefore(host,bar.nextSibling);
 const graphs=$("cpt-atlas-graphs");
 graphs.appendChild(mainGraph);
 let two=document.createElement("div");two.id="cpt-atlas-2d";graphs.appendChild(two);
 const studio=$("cpt-studio");
 graphs.parentNode.insertBefore(studio,graphs);
 // Keep the original E-W and N-S fence plots as expandable secondary views.
 const rest=document.createElement("details");rest.className="atlas-fences";
 rest.innerHTML="<summary>Show E–W / N–S CPT fence sections</summary>";
 const move=[];
 [...document.querySelectorAll("body > section")].forEach(el=>{if(el!==host&&el.id!=="cpt-studio")move.push(el)});
 move.forEach(el=>rest.appendChild(el));
 document.body.appendChild(rest);
 const grand=Math.ceil(Math.max(1,...SEG.map(s=>s.bottom))*10)/10;
 $("atlas-depth").max=grand;$("atlas-depth").value=Math.min(4.5,grand);
 depth=Number($("atlas-depth").value);
 $("atlas-depth-label").textContent=fmt(depth)+" m";
 $("atlas-2d").onclick=show2d;$("atlas-3d").onclick=show3d;
 const setDepth=value=>{
  depth=Math.min(grand,Math.max(0,Number.isFinite(Number(value))?Number(value):depth));
  $("atlas-depth").value=depth;
  $("atlas-depth-number").value=depth.toFixed(2);
  $("atlas-depth-label").textContent=fmt(depth)+" m";
  if(active2d)render2d();
  if(selected)inspect(byref[selected]);
 };
 $("atlas-depth").oninput=()=>setDepth($("atlas-depth").value);
 $("atlas-depth-number").onchange=()=>setDepth($("atlas-depth-number").value);
 $("atlas-mode").onchange=()=>{if(active2d)render2d();recolor3d()};
 $("atlas-find").onchange=()=>{let v=$("atlas-find").value.toLowerCase().trim();const p=SOURCE.find(p=>p.ref.toLowerCase()===v)||
 SOURCE.find(p=>p.ref.toLowerCase().includes(v));if(p)inspect(p)};
 const pan=$("atlas-pan"),zoom=$("atlas-box");
 pan.onclick=()=>{navMode="pan";pan.classList.add("chosen");zoom.classList.remove("chosen");
  if(active2d)Plotly.relayout("cpt-atlas-2d",{dragmode:"pan"});};
 zoom.onclick=()=>{navMode="zoom";zoom.classList.add("chosen");pan.classList.remove("chosen");
  if(active2d)Plotly.relayout("cpt-atlas-2d",{dragmode:"zoom"});};
 const zoomBy=factor=>{
  if(!active2d){Plotly.relayout(mainGraph,{"scene.camera.eye":{x:1.6/factor,y:-1.6/factor,z:1.05/factor}});return;}
  const g=$("cpt-atlas-2d");
  const xr=g.layout.xaxis.range,yr=g.layout.yaxis.range;
  if(!xr||!yr)return;
  const cx=(xr[0]+xr[1])/2,cy=(yr[0]+yr[1])/2;
  const rx=(xr[1]-xr[0])/2/factor,ry=(yr[1]-yr[0])/2/factor;
  Plotly.relayout(g,{"xaxis.range":[cx-rx,cx+rx],"yaxis.range":[cy-ry,cy+ry]});
 };
 $("atlas-zoom-in").onclick=()=>zoomBy(1.45);
 $("atlas-zoom-out").onclick=()=>zoomBy(1/1.45);
 $("atlas-fit").onclick=()=>active2d?Plotly.relayout("cpt-atlas-2d",{"xaxis.autorange":true,"yaxis.autorange":true}):
 Plotly.relayout(mainGraph,{"scene.camera.eye":{x:1.6,y:-1.6,z:1.05}});
 $("atlas-expand").onclick=()=>{
  document.body.classList.toggle("atlas-focus-map");
  const focused=document.body.classList.contains("atlas-focus-map");
  $("atlas-expand").textContent=focused?"SHOW DETAILS":"HIDE DETAILS";
  setTimeout(()=>Plotly.Plots.resize(active2d?$("cpt-atlas-2d"):mainGraph),120);
 };
 $("atlas-save").onclick=()=>Plotly.downloadImage(active2d?"cpt-atlas-2d":TARGET,
  {format:"png",filename:"CPT_ATLAS_"+(active2d?"2D":"3D"),width:1800,height:1200,scale:1});
 $("atlas-full").onclick=()=>{
   if(document.fullscreenElement)document.exitFullscreen();
   else $("cpt-atlas-map").requestFullscreen();
 };
 const ranked=SOURCE.filter(p=>Number.isFinite(p.max)).sort((a,b)=>b.max-a.max);
 $("cpt-atlas-rank").innerHTML=ranked.slice(0,12).map((p,i)=>
  "<button data-id='"+clean(p.ref)+"'>#"+(i+1)+" · "+clean(p.ref)+" — "+fmt(p.max,3)+" m</button>").join("");
 $("cpt-atlas-rank").querySelectorAll("button").forEach(el=>el.onclick=()=>inspect(byref[el.dataset.id]));
 const lows=SOURCE.filter(p=>Number.isFinite(p.max)&&p.max>0).sort((a,b)=>a.max-b.max);
 const absent=SOURCE.filter(p=>p.max===0).length;
 $("cpt-atlas-minrank").innerHTML=lows.slice(0,10).map((p,i)=>
    "<button data-id='"+clean(p.ref)+"'>#"+(i+1)+" · "+clean(p.ref)+" — "+fmt(p.max,3)+" m</button>").join("")+
    "<p class='atlas-note'>"+absent+" CPTs have no qualifying observed silt screen; they are not counted as thin positive layers.</p>";
 $("cpt-atlas-minrank").querySelectorAll("button").forEach(el=>el.onclick=()=>inspect(byref[el.dataset.id]));
 // New overlay markers with continuous silt-thickness color, independent
 // from categorical SBT body block colors. All ties remain inspectable.
 const stem=SOURCE.map(p=>p.rl??0);
 Plotly.addTraces(mainGraph,{type:"scatter3d",mode:"markers",name:"Measured CPT collars · thickness",
  x:SOURCE.map(p=>p.x),y:SOURCE.map(p=>p.y),z:stem,
  customdata:SOURCE.map(p=>p.ref),hovertemplate:SOURCE.map(hover),
  marker:{size:5,color:SOURCE.map(p=>p.max),colorscale:[[0,"#31688e"],[.25,"#35b779"],
   [.5,"#fde725"],[.75,"#eb642d"],[1,"#b90d33"]],cmin:0,cmax:maxval,showscale:true,
   colorbar:{title:{text:"Max observed<br>silt thickness (m)"},thickness:12,len:.5},line:{color:"white",width:.6}}}).then(()=>{
   mainGraph.on("plotly_click",evt=>{
    const hit=evt.points.find(p=>p.customdata&&typeof p.customdata==="string");
    if(hit)inspect(byref[hit.customdata]);
   });
   for(const id of ["cpt-top","cpt-bottom"])$(id).addEventListener("input",()=>setTimeout(recolor3d,80));
   recolor3d();show2d();
 });
 window.addEventListener("resize",()=>{let el=active2d?$("cpt-atlas-2d"):mainGraph;
 if(el?.data)Plotly.Plots.resize(el)});
}
if(document.readyState==="complete")setTimeout(init,250);
else window.addEventListener("load",()=>setTimeout(init,250),{once:true});
})();
</script>
"""


def export_geo_atlas(data, path, *, boundary=None, warning_m=.10, high_m=.30,
                     max_spacing_m=None):
    """Build full offline 3D then add professional 2D/3D linked workspace."""
    from engineering_3d_studio import export_professional_3d
    target=Path(path)
    result=export_professional_3d(data,target,boundary=boundary,warning_m=warning_m,
                                  high_m=high_m,max_spacing_m=max_spacing_m)
    pts,excluded=spatial_points(data)
    segments,_,origin=collect_observed_segments(data)
    xy=np.asarray([[p.x,p.y] for p in pts],dtype=float)
    tri,indices,_=_triangle_mask(xy,boundary=boundary)
    mask=np.ma.getmaskarray(tri.triangles) if False else (
        tri.mask if tri is not None and tri.mask is not None else [])
    faces=(np.asarray(indices,dtype=int)[tri.triangles[~mask]].tolist()
           if tri is not None else [])
    source_by_ref={}
    for item in data:
        ref=item.get("reference") if isinstance(item,dict) else getattr(item,"reference",None)
        if ref is not None:source_by_ref.setdefault(str(ref),item)
    def observed_samples(item):
        if item is None or isinstance(item,dict) or not hasattr(item,"depth"):
            return []
        try:
            depth=np.asarray(item.depth,dtype=float)
            valid=np.asarray(getattr(item,"valid_sensor",np.ones(len(depth),dtype=bool)),dtype=bool)
            if len(depth)<1:return []
            take=np.unique(np.r_[np.arange(0,len(depth),max(1,int(np.ceil(len(depth)/500)))),len(depth)-1])
            result=[]
            for i in take:
                row=[round(float(depth[i]),4)]
                for field in ("qc","fs","u2","qt","fr","qtn","ic"):
                    try:
                        v=float(getattr(item,field)[i])
                        row.append(round(v,5) if np.isfinite(v) else None)
                    except (IndexError,TypeError,ValueError,AttributeError):
                        row.append(None)
                row.append(bool(valid[i] and row[-1] is not None))
                result.append(row)
            return result
        except (ValueError,TypeError,IndexError):
            return []
    data_rows=[{"ref":p.reference,"x":p.x-origin[0],"y":p.y-origin[1],
                "east":p.x,"north":p.y,"rl":p.elevation,"depth":p.depth,
                "max":p.maximum_m,"cum":p.cumulative_m,
                "start":min((r[0] for r in p.intervals),default=None),
                "source":p.source,"status":p.status,
                "samples":observed_samples(source_by_ref.get(p.reference))} for p in pts]
    boundary_rows=None
    if boundary is not None:
        polygon=np.asarray(boundary,dtype=float)
        if polygon.ndim==2 and polygon.shape[1]==2 and len(polygon)>=3:
            boundary_rows=(polygon-np.asarray(origin)).tolist()
    content=target.read_text(encoding="utf-8")
    import re
    found=re.search(r'Plotly\.newPlot\(\s*"([^"]+)"',content)
    if not found:raise ValueError("Primary Plotly model not found")
    code=(SCRIPT.replace("__SOURCE__",json.dumps(data_rows,separators=(",",":")).replace("<","\\u003c"))
          .replace("__SEG__",json.dumps(segments,separators=(",",":")).replace("<","\\u003c"))
          .replace("__FACES__",json.dumps(faces,separators=(",",":")))
          .replace("__BOUND__",json.dumps(boundary_rows,separators=(",",":")))
          .replace("__TARGET__",json.dumps(found.group(1))))
    content=content.replace("</body>",STYLE+code+"</body>",1)
    target.write_text(content,encoding="utf-8")
    return {**result,"atlas":True,"plan_faces":len(faces),"hover_cpts":len(pts)}

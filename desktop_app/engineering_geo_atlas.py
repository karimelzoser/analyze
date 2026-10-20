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
#cpt-atlas-svg3d{position:absolute;inset:0;z-index:3;background:linear-gradient(155deg,#f5fafe,#ffffff);
 cursor:grab;touch-action:none;overflow:hidden}
#cpt-atlas-svg3d:active{cursor:grabbing}
#cpt-atlas-svg3d svg{width:100%;height:100%;display:block}
#cpt-atlas-svg3d .soil-svg-body{transition:stroke-width .12s}
#cpt-atlas-svg3d .soil-svg-body:hover{stroke:#102d43!important;stroke-width:1.8px!important}
#cpt-atlas-svg3d .soil-svg-top:hover{stroke:#102d43!important}
#cpt-atlas-svg3d .soil-svg-label{font:11px Segoe UI,Arial,sans-serif;fill:#233e54}
body.atlas-mode-3d #atlas-depth-tools > *:not(#atlas-vertical):not(#atlas-vertical-label):not(#atlas-silt-only):not(#atlas-all-layers):not(#atlas-depth):not(#atlas-depth-label):not(#atlas-depth-number):not(#atlas-geology-wrap):not(#atlas-slab-wrap):not(#atlas-measured-wrap):not(#atlas-detail-wrap):not(#atlas-stack-wrap){display:none!important}
#atlas-geology-wrap,#atlas-slab-wrap{grid-column:1/-1;display:flex;gap:8px;align-items:center;flex-wrap:wrap;line-height:1.3;font:600 12px Segoe UI,Arial,sans-serif;color:#1b4963}
#atlas-slab-wrap input{flex:1;min-width:85px;accent-color:#11748e}
#atlas-geology{width:18px;height:18px;accent-color:#11748e}
#atlas-measured{width:18px;height:18px;accent-color:#11748e}
#atlas-measured-wrap{grid-column:1/-1;display:flex;gap:8px;align-items:center;line-height:1.3;font:600 12px Segoe UI,Arial,sans-serif;color:#1b4963}
#atlas-detail-wrap{grid-column:1/-1;display:flex;flex-direction:column;gap:5px;
 font:700 11px Segoe UI,Arial,sans-serif;color:#1b4963}
#atlas-stack-wrap{grid-column:1/-1;display:flex;flex-direction:column;gap:5px;font:700 11px Segoe UI,Arial,sans-serif;color:#1b4963}
#atlas-stack{width:100%;box-sizing:border-box;padding:8px;border:1px solid #c8d9e6;border-radius:7px;background:#fff}
#atlas-detail{width:100%;box-sizing:border-box;padding:8px;border:1px solid #c8d9e6;
 border-radius:7px;background:#fff;color:#174462}
#cpt-atlas-svg3d .soil-svg-body{stroke-opacity:.8;transition:opacity .15s}
#cpt-atlas-svg3d .soil-svg-body:hover{filter:drop-shadow(0 0 2px #1e5074)}
.soil-layer-ribbon{stroke:#526c80;stroke-width:.6;stroke-dasharray:2 3;cursor:help}
#cpt-atlas-details .atlas-depth-column{height:240px;width:42px;position:relative;border:1px solid #9cb5c7;flex:none;background:#edf2f6;border-radius:4px;overflow:hidden}
#cpt-atlas-details .atlas-profile-grid{display:flex;align-items:flex-start;gap:13px;padding:9px;border:1px solid #e4edf4;border-radius:9px;background:#fbfdff;margin:7px 0}
#cpt-atlas-details .atlas-depth-band{position:absolute;left:0;width:100%;box-sizing:border-box;border-bottom:1px solid #ffffff77}
#cpt-atlas-details .atlas-depth-info{font-size:11px;color:#37556c;line-height:1.7}
#cpt-atlas-details .atlas-depth-info strong{font-size:12px;color:#183d55}
#cpt-atlas-details .atlas-depth-caption{font-size:11px;color:#697c8e;margin:5px 0}

#atlas-silt-only,#atlas-all-layers{border:1px solid #a3c2d7;background:#fff;color:#235876;
 border-radius:7px;padding:7px 12px;cursor:pointer;font-weight:700}
#atlas-silt-only.chosen,#atlas-all-layers.chosen{background:#0d648b;color:white}
#atlas-vertical{width:98px;vertical-align:middle}

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

/* Workspace layout v4: map owns the center; tools in independently scrolling rail. */
#cpt-atlas-screen{grid-template-columns:340px minmax(0,1fr)!important;grid-template-rows:minmax(0,1fr);
 height:100vh!important;min-height:490px!important;max-height:100vh;margin:0!important}
#cpt-atlas-map{grid-column:2;grid-row:1;min-height:0;height:100%;position:relative}
#cpt-atlas-graphs{min-height:0!important;flex:1;contain:layout paint}
#cpt-atlas-aside{grid-column:1;grid-row:1;overflow:auto;overscroll-behavior:contain;
 background:#f3f7fb;border-right:1px solid #d5e2ec;border-left:0;padding:10px 12px!important;
 box-shadow:3px 0 15px #123b570a;scrollbar-gutter:stable}
#cpt-atlas-header{position:static!important;display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr));
 width:100%;padding:6px 0 12px!important;margin:0 0 10px!important;gap:7px!important;
 border-bottom:1px solid #dce7f0!important;background:transparent!important}
#cpt-atlas-header strong{grid-column:1/-1;line-height:1.15;font-size:19px!important;margin:0 0 5px!important}
#cpt-atlas-header button{white-space:normal;min-height:37px;line-height:1.15;padding:7px 6px!important;font-size:11px!important}
#cpt-atlas-header label{grid-column:1/-1;align-self:end}
#atlas-mode{grid-column:1/-1;min-width:0;width:100%}
#atlas-find{grid-column:1/-1;min-width:0;width:100%}
#atlas-2d,#atlas-3d{font-size:12px!important}
#atlas-full{grid-column:1/-1}
#atlas-depth-tools{padding:10px!important;display:grid;grid-template-columns:1fr auto;gap:8px;
 margin:0 0 10px!important;border:1px solid #dae6f0!important;border-radius:9px;background:white!important}
#atlas-depth-tools > span:first-child{grid-column:1/-1;font-weight:700}
#atlas-depth{grid-column:1;max-width:100%;width:100%}
#atlas-depth-label{grid-column:2}
#atlas-depth-number{grid-column:1/-1;width:100%!important;box-sizing:border-box}
#atlas-silt-only,#atlas-all-layers{grid-column:auto;min-height:37px}
#atlas-vertical{grid-column:1;max-width:100%}
#cpt-studio{padding:10px!important;margin:0 0 10px!important;background:white;border:1px solid #dae6f0!important;
 border-radius:9px!important}
#cpt-studio .cpt-options{display:flex!important;flex-direction:column;align-items:stretch!important;
 gap:7px!important;overflow:visible;white-space:normal}
#cpt-studio .cpt-options label{max-width:100%!important;white-space:normal!important;font-size:11px}
#cpt-studio .cpt-range{display:flex;flex-wrap:wrap;gap:6px}
#cpt-studio .cpt-range input[type=range]{width:100%!important}
#cpt-atlas-aside .atlas-panel{margin-bottom:10px}
#cpt-atlas-graphs svg{user-select:none}
body.atlas-focus-map #cpt-atlas-screen{grid-template-columns:minmax(0,1fr)!important}
body.atlas-focus-map #cpt-atlas-map{grid-column:1}
@media(max-width:860px){
 #cpt-atlas-screen{grid-template-columns:280px minmax(0,1fr)!important}
 #cpt-atlas-header button{font-size:10px!important;padding:7px 4px!important}
}
@media(max-width:630px){
 #cpt-atlas-screen{grid-template-columns:minmax(0,1fr)!important}
 #cpt-atlas-map{grid-column:1;grid-row:1}
 #cpt-atlas-aside{position:fixed;top:0;left:0;bottom:0;width:min(320px,85vw);max-width:85vw;
  z-index:50;box-shadow:4px 0 25px #112b4670}
 body.atlas-focus-map #cpt-atlas-aside{display:none}
}

/* Accessible restore control remains visible when the sidebar is collapsed. */
#atlas-show-panel{display:none;position:absolute;top:14px;left:14px;z-index:25;
 border:1px solid #bed4e5;background:#fff;color:#14516e;padding:10px 14px;
 border-radius:9px;box-shadow:0 3px 16px #153b5944;cursor:pointer;font:700 12px Segoe UI,Arial,sans-serif}
body.atlas-focus-map #atlas-show-panel{display:block}
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
let atlas2dFrame=0;
function schedule2d(){if(atlas2dFrame)return;atlas2dFrame=requestAnimationFrame(()=>{atlas2dFrame=0;render2d();});}
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
function focusCpt(p){
 if(!p)return;
 inspect(p);
 if(!active2d)show2d();
 const graph=$("cpt-atlas-2d");
 let rx=20,ry=20;
 try{
  let x=graph.layout.xaxis.range,y=graph.layout.yaxis.range;
  if(x&&y){rx=Math.min(40,Math.max(10,Math.abs(x[1]-x[0])*.18));
            ry=Math.min(40,Math.max(10,Math.abs(y[1]-y[0])*.18));}
 }catch(e){}
 Plotly.relayout(graph,{"xaxis.range":[p.x-rx,p.x+rx],
                        "yaxis.range":[p.y-ry,p.y+ry]});
}
function inspect(p,skipRedraw=false){
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
 let detail=blocks.slice(0,320).map(x=>"<tr><td>"+fmt(x.top,2)+"–"+fmt(x.bottom,2)+" m</td><td>"+clean(x.category)+"</td><td>"+fmt(x.bottom-x.top,3)+"</td></tr>").join("");
 const depthExtent=Math.max(1,p.depth||1);
 const bars=blocks.filter(x=>x.bottom>x.top).map(x=>{
  const topPct=Math.max(0,Math.min(100,100*x.top/depthExtent));
  const hPct=Math.max(.5,Math.min(100-topPct,100*(x.bottom-x.top)/depthExtent));
  return "<span class='atlas-depth-band' style='top:"+topPct+"%;height:"+hPct+
    "%;background:"+(COLORS[x.category]||COLORS.unknown)+"' title='"+
    clean(x.category)+" "+fmt(x.top,2)+"–"+fmt(x.bottom,2)+" m'></span>";
 }).join("");
 const depthProfile="<div class='atlas-profile-grid'><div class='atlas-depth-column' aria-label='Full observed CPT soil column'>"+
 bars+"</div><div class='atlas-depth-info'><strong>Measured CPT soil profile</strong><br>"+
 "0.00 m — Ground surface<br>"+fmt(depthExtent,2)+" m — Sounding end<br>"+
 "<div class='atlas-depth-caption'>Gold sand · orange transition · teal silt-mixture · purple clay · gray unknown</div>"+
 "<b>"+blocks.length+"</b> classified/unknown intervals<br>"+
 "<b>"+fmt(p.max,2)+" m</b> thickest screening layer<br>"+
 "Click the colored column to inspect a band</div></div>";
 $("cpt-atlas-details").innerHTML="<h2>"+clean(p.ref)+"</h2><p class='atlas-note'>"+
 (at?("Depth "+fmt(depth,2)+" m: "+at.category+" / "+fmt(at.ic,3)+" Ic"):("Depth "+fmt(depth,2)+" m: no valid classification"))+
 "</p>"+depthProfile+"<table>"+table+"</table><details open><summary>"+blocks.length+
 " measured/cached soil intervals</summary><div class='atlas-layers'><table>"+
 "<tr><th>BGL</th><th>SBT</th><th>Thickness</th></tr>"+detail+"</table></div></details>";
 if(active2d && !skipRedraw)schedule2d();
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
 // SVG markers stay interactive even when Edge/Chrome disables extra WebGL contexts.
 const markers={type:"scatter",mode:"markers",name:"CPT observations",
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
// GPU-independent 3D projection. Every face belongs to one measured CPT
// depth interval; it never invents a continuous subsurface between tests.
const SVGNS="http://www.w3.org/2000/svg";
const iso={az:-.70,elev:.53,zoom:1,tx:0,ty:0,vertical:6,drag:false,
            pointerX:0,pointerY:0,moved:false,shift:false};
function svgNode(name,attrs={},text=null){
 const el=document.createElementNS(SVGNS,name);
 Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,String(v)));
 if(text!==null)el.textContent=String(text);
 return el;
}
function renderSvg3d(preview=false){
 const svg=$("cpt-atlas-isometric"),host=$("cpt-atlas-svg3d");
 if(!svg||!host)return;
 const w=Math.max(320,host.clientWidth),h=Math.max(270,host.clientHeight);
 svg.setAttribute("viewBox","0 0 "+w+" "+h);
 svg.replaceChildren();
 const xs=SOURCE.map(p=>p.x),ys=SOURCE.map(p=>p.y);
 if(!xs.length)return;
 const midx=(Math.min(...xs)+Math.max(...xs))/2;
 const midy=(Math.min(...ys)+Math.max(...ys))/2;
 const span=Math.max(15,Math.max(...xs)-Math.min(...xs),Math.max(...ys)-Math.min(...ys));
 // Fit to actual CPT depths. Former h/86 scale reduced 6m to just ~30px.
 const deepest=Math.max(3,...SEG.map(s=>Number(s.bottom)||0));
 const nominalXY=Math.min((w-92)/(span*1.22),(h-64)/(span*1.05))*iso.zoom;
 const nominalZ=Math.min(52,h*.52/deepest)*(iso.vertical/6)*iso.zoom;
 const meanGround=SOURCE.reduce((a,p)=>a+Number(p.rl||0),0)/SOURCE.length;
 const midz=meanGround-deepest*.47;
 const cos=Math.cos(iso.az),sin=Math.sin(iso.az);
 // Fit BOTH collar tops and measured sounding tips to the visible viewport.
 // Previously a fixed depth exaggeration cut some CPTs off above/below.
 const projectedRange=SOURCE.flatMap(p=>{
  const dx=p.x-midx,dy=p.y-midy,ry=dx*sin+dy*cos;
  const ground=Number(p.rl||meanGround),bottom=ground-Number(p.depth||deepest);
  return [ry*nominalXY*iso.elev-(ground-midz)*nominalZ,
          ry*nominalXY*iso.elev-(bottom-midz)*nominalZ];
 });
 const lower=Math.min(...projectedRange),upper=Math.max(...projectedRange);
 const fit=Math.min(1,(h-155)/Math.max(1,upper-lower));
 const hscale=nominalXY*fit,vertical=nominalZ*fit;
 const verticalCenter=(upper+lower)*.5*fit;
 function project(x,y,z){
  const dx=x-midx,dy=y-midy;
  const rx=dx*cos-dy*sin,ry=dx*sin+dy*cos;
  return [w/2+iso.tx+rx*hscale,
          h/2+iso.ty+ry*hscale*iso.elev-(z-midz)*vertical-verticalCenter];
 }
 const bg=svgNode("g");
 for(let q=0;q<9;q++){
  const offset=(q-4)*span/6;
  const a=project(midx-span/2,midy+offset,midz-5);
  const b=project(midx+span/2,midy+offset,midz-5);
  bg.appendChild(svgNode("line",{x1:a[0],y1:a[1],x2:b[0],y2:b[1],
                   stroke:"#e1eaf2","stroke-width":1}));
 }
 svg.appendChild(bg);
 const stTop=Number($("cpt-top")?.value??0);
 const stBot=Number($("cpt-bottom")?.value??1e3);
 const surfaceColor=$("cpt-thickness-color")?.checked!==false;
 if(BOUND&&BOUND.length){
  const poly=[...BOUND,BOUND[0]];
  const coords=poly.map(([x,y])=>project(x,y,midz));
  svg.appendChild(svgNode("polyline",{
   points:coords.map(q=>q.join(",")).join(" "),fill:"none",
   stroke:"#4b647b","stroke-width":2,"stroke-dasharray":"6 3"
  }));
 }
 // Spatial soil ribbons are CONCEPTUAL interpolation only.
 // Each surveyed triangle is subdivided into three nearest-CPT regions,
 // preserving soil classes and never extrapolating outside its measured hull.
 // Small translucent depth bands make layers legible without hiding real CPTs.
 let ribbonsDrawn=0;
 if($("atlas-geology")?.checked && !preview){
  const thickness=Math.max(.1,Math.min(1.5,Number($("atlas-slab")?.value||.5)));
  const blanket=svgNode("g",{id:"atlas-inferred-layer-volume","aria-label":"Evidence-bounded interpreted soil horizons, NOT direct observations between CPTs"});
  const levelCount=Number($("atlas-stack")?.value||3);
  const horizonOffsets=levelCount===1?[0]:levelCount===5?[-1.2,-.6,0,.6,1.2]:[-.7,0,.7];
  for(const relativeDepth of horizonOffsets){
  const horizonDepth=Math.max(.05,depth+relativeDepth);
  for(const [ia,ib,ic] of FACES){
   const ps=[SOURCE[ia],SOURCE[ib],SOURCE[ic]];
   if(ps.some(p=>!p||p.status==="REVIEW"||p.rl===null||p.rl===undefined))continue;
   const zs=ps.map(p=>zone(p,horizonDepth));
   if(zs.some(z=>!z))continue;
   const mean=(i,j)=>({x:(ps[i].x+ps[j].x)/2,y:(ps[i].y+ps[j].y)/2,
                       rl:(ps[i].rl+ps[j].rl)/2});
   const ctr={x:(ps[0].x+ps[1].x+ps[2].x)/3,
              y:(ps[0].y+ps[1].y+ps[2].y)/3,
              rl:(ps[0].rl+ps[1].rl+ps[2].rl)/3};
   for(let k=0;k<3;k++){
    const prev=(k+2)%3,next=(k+1)%3;
    const nodes=[ps[k],mean(k,next),ctr,mean(k,prev)];
    const top=nodes.map(p=>project(p.x,p.y,p.rl-horizonDepth));
    const bot=nodes.map(p=>project(p.x,p.y,p.rl-horizonDepth-thickness));
    const color=COLORS[zs[k].category]||COLORS.unknown;
    const face=svgNode("polygon",{
       points:top.map(p=>p.join(",")).join(" "),fill:color,
       "fill-opacity":levelCount>1?.31:.49,class:"soil-layer-ribbon"});
    face.appendChild(svgNode("title",{},
       "INTERPRETED "+zs[k].category+" at "+fmt(horizonDepth,2)+"–"+
       fmt(horizonDepth+thickness,2)+" m BGL (nearest CPT "+ps[k].ref+")"));
    blanket.appendChild(face);
    for(const side of [[1,2],[2,3]]){
      const [i,j]=side;
      const poly=svgNode("polygon",{
         points:[top[i],top[j],bot[j],bot[i]].map(p=>p.join(",")).join(" "),
         fill:color,"fill-opacity":levelCount>1?.14:.24,stroke:color,"stroke-opacity":.35,
         "stroke-width":.45});
      blanket.appendChild(poly);
    }
    ribbonsDrawn++;
   }
  }
  } // next interpreted horizon depth
  svg.appendChild(blanket);
 }
 const selectable=[];
 const focusBand=Math.max(.12,Math.min(1.5,Number($("atlas-slab")?.value||.5)));
 const allLayers=$("atlas-detail")?.value==="all";
 let candidates=SEG.filter(s=>s.bottom>stTop&&s.top<stBot&&
   (allLayers || s.ref===selected || (s.top<=depth+focusBand&&s.bottom>=depth-focusBand))&&
   (document.querySelector("[data-layer='"+s.category+"']")?.checked!==false))
  .map(s=>({...s,drawTop:Math.max(s.top,stTop),
             drawBottom:Math.min(s.bottom,stBot)}))
  .filter(s=>s.drawBottom>s.drawTop)
  .map(s=>({...s,sort:(project(s.x,s.y,s.z0)[1])}))
  .sort((a,b)=>a.sort-b.sort);
 const availableSegments=candidates.length;
 // Engineering overview has a LEGIBILITY budget, not a data deletion.
 // Preserve EVERY measured layer in SEG and the "ALL MEASURED LAYERS" mode.
 // A deterministic round-robin selection gives each surveyed CPT a fair
 // representation rather than allowing dense/noisy CPTs to monopolize 3D.
 if(!allLayers && !preview && candidates.length>700){
   const buckets=new Map();
   for(const s of candidates){
     if(!buckets.has(s.ref))buckets.set(s.ref,[]);
     buckets.get(s.ref).push(s);
   }
   for(const [ref,group] of buckets){
     group.sort((a,b)=>Math.abs((a.drawTop+a.drawBottom)/2-depth)-
                       Math.abs((b.drawTop+b.drawBottom)/2-depth));
   }
   const references=[...buckets.keys()].sort((a,b)=>{
     if(a===selected)return -1;if(b===selected)return 1;
     return a.localeCompare(b);
   });
   const display=[];
   let more=true;
   while(more && display.length<700){
     more=false;
     for(const ref of references){
       const group=buckets.get(ref);
       if(group.length){
         more=true;display.push(group.shift());
         if(display.length===700)break;
       }
     }
   }
   candidates=display.sort((a,b)=>a.sort-b.sort);
 }
 const previewStep=preview?Math.max(1,Math.ceil(candidates.length/650)):1;
 if($("atlas-measured")?.checked!==false)
 for(let pass=0;pass<candidates.length;pass+=previewStep){
  const s=candidates[pass];
  const collar=byref[s.ref];if(!collar)continue;
  const zTop=s.z0-(s.drawTop-s.top),zBot=s.z0-(s.drawBottom-s.top);
  const top=project(s.x,s.y,zTop),bot=project(s.x,s.y,zBot);
  const bw=Math.max(4,Math.min(11,hscale*.7)),d=Math.max(2,bw*.55);
  // Numeric heat applies only to silt-like material; other blocks use soil colors.
  const fillColor=surfaceColor && s.category==="silt" ? ramp(collar.max) :
                  COLORS[s.category]||COLORS.unknown;
  const main=svgNode("polygon",{
    points:[[top[0]-bw,top[1]],[top[0]+bw,top[1]],
            [bot[0]+bw,bot[1]],[bot[0]-bw,bot[1]]].map(q=>q.join(",")).join(" "),
    fill:fillColor,stroke:"#ffffff",
    "stroke-width":.65,class:"soil-svg-body"
  });
  const side=svgNode("polygon",{
    points:[[top[0]+bw,top[1]],[top[0]+bw+d,top[1]-d],
            [bot[0]+bw+d,bot[1]-d],[bot[0]+bw,bot[1]]].map(q=>q.join(",")).join(" "),
    fill:fillColor,"fill-opacity":.72,
    stroke:"#ffffff","stroke-width":.5
  });
  const cap=svgNode("polygon",{
    points:[[top[0]-bw,top[1]],[top[0]+bw,top[1]],
            [top[0]+bw+d,top[1]-d],[top[0]-bw+d,top[1]-d]].map(q=>q.join(",")).join(" "),
    fill:fillColor,"fill-opacity":.86
  });
  const label=s.ref+" | "+s.category+" | BGL "+fmt(s.drawTop,2)+
       "–"+fmt(s.drawBottom,2)+" m | CPT maximum "+fmt(collar.max,3)+" m";
  main.appendChild(svgNode("title",{},label));
  side.appendChild(svgNode("title",{},label));
  for(const el of (preview?[main]:[main,side,cap])){
   el.style.cursor="pointer";
   el.addEventListener("click",e=>{
      if(iso.moved)return;
      e.stopPropagation();inspect(collar);renderSvg3d();
   });
   svg.appendChild(el);
  }
 }
 for(const p of SOURCE){
  const pos=project(p.x,p.y,p.rl??midz);
  const radius=p.ref===selected?7.6:5;
  const circle=svgNode("circle",{cx:pos[0],cy:pos[1],r:radius,
    fill:surfaceColor?ramp(p.max):"#1b688c",
    stroke:p.ref===selected?"#0c2439":"#ffffff",
    "stroke-width":p.ref===selected?2.7:1.6,
    style:"cursor:pointer"});
  circle.appendChild(svgNode("title",{},p.ref+" — max silt "+fmt(p.max,3)+
      " m; cumulative "+fmt(p.cum,3)+" m; click to inspect"));
  circle.addEventListener("click",e=>{
    if(iso.moved)return;
    e.stopPropagation();inspect(p);renderSvg3d();
  });
  svg.appendChild(circle);
  if(p.ref===selected){
    svg.appendChild(svgNode("text",{x:pos[0]+11,y:pos[1]-8,
                   class:"soil-svg-label","font-weight":"bold"},p.ref));
  }
 }
 svg.appendChild(svgNode("text",{x:20,y:30,fill:"#21445f",
        style:"font:600 15px Segoe UI,Arial,sans-serif"},
        "Interactive CPT 3D columns · surveyed XY and actual measured depths"));
 svg.appendChild(svgNode("text",{x:20,y:50,fill:"#657e90",
        style:"font:11px Segoe UI,Arial,sans-serif"},
        "Drag to rotate · Shift+drag to pan · Wheel to zoom · Click a CPT"));
 svg.appendChild(svgNode("text",{x:20,y:h-16,fill:"#657e90",
        style:"font:11px Segoe UI,Arial,sans-serif"},
        (availableSegments>candidates.length ?
          ("FOCUSED 3D: "+candidates.length+" of "+availableSegments+
            " visible measured intervals · choose ALL for the complete set") :
          ribbonsDrawn ? ("INTERPRETED "+ribbonsDrawn+" soil cells · CPT columns are measured") :
            "Only surveyed CPT columns shown · no inferred geological volume")));
}
function setSvg3dVisible(visible){
 const svg=$("cpt-atlas-svg3d");
 if(visible)svg.classList.remove("atlas-hide");else svg.classList.add("atlas-hide");
 $("atlas-vertical").classList.toggle("atlas-hide",!visible);
 $("atlas-vertical-label").classList.toggle("atlas-hide",!visible);
 $("atlas-silt-only").classList.toggle("atlas-hide",!visible);
 $("atlas-all-layers").classList.toggle("atlas-hide",!visible);
 $("atlas-geology-wrap")?.classList.toggle("atlas-hide",!visible);
 $("atlas-slab-wrap")?.classList.toggle("atlas-hide",!visible);
 $("atlas-measured-wrap")?.classList.toggle("atlas-hide",!visible);
 $("atlas-detail-wrap")?.classList.toggle("atlas-hide",!visible);
 $("atlas-stack-wrap")?.classList.toggle("atlas-hide",!visible);
}
let isoFrame=0,isoPendingFull=false;
function scheduleIsoFrame(preview=false){
 if(!preview)isoPendingFull=true;
 if(isoFrame)return;
 isoFrame=requestAnimationFrame(()=>{
  isoFrame=0;
  const final=isoPendingFull;isoPendingFull=false;
  renderSvg3d(!final && preview && iso.drag);
 });
}
function initIsoInteraction(){
 const host=$("cpt-atlas-svg3d");if(!host)return;
 host.addEventListener("pointerdown",e=>{
   iso.drag=true;iso.moved=false;iso.shift=e.shiftKey;
   iso.pointerX=e.clientX;iso.pointerY=e.clientY;
   host.setPointerCapture(e.pointerId);
 });
 host.addEventListener("pointermove",e=>{
   if(!iso.drag)return;
   const dx=e.clientX-iso.pointerX,dy=e.clientY-iso.pointerY;
   if(Math.abs(dx)+Math.abs(dy)>2)iso.moved=true;
   if(iso.shift){iso.tx+=dx;iso.ty+=dy;}
   else{iso.az+=dx*.011;iso.elev=Math.max(.14,Math.min(.88,iso.elev+dy*.004));}
   iso.pointerX=e.clientX;iso.pointerY=e.clientY;
   scheduleIsoFrame(true);
 });
 host.addEventListener("pointerup",e=>{
   iso.drag=false;
   scheduleIsoFrame(false);
   setTimeout(()=>{iso.moved=false},70);
 });
 host.addEventListener("wheel",e=>{
   if(host.classList.contains("atlas-hide"))return;
   e.preventDefault();
   iso.zoom=Math.max(.4,Math.min(10,iso.zoom*(e.deltaY<0?1.12:.89)));
   scheduleIsoFrame(false);
 },{passive:false});
 $("atlas-vertical").oninput=e=>{iso.vertical=Number(e.target.value);scheduleIsoFrame(false);};
 for(const id of ["cpt-top","cpt-bottom"])
   $(id)?.addEventListener("input",()=>{if(!host.classList.contains("atlas-hide"))renderSvg3d();});
 document.querySelectorAll("[data-layer]").forEach(el=>
   el.addEventListener("change",()=>{if(!host.classList.contains("atlas-hide"))renderSvg3d();}));
 $("cpt-thickness-color")?.addEventListener("change",()=>renderSvg3d());
 $("atlas-geology")?.addEventListener("change",()=>scheduleIsoFrame(false));
 $("atlas-measured")?.addEventListener("change",()=>scheduleIsoFrame(false));
 $("atlas-detail")?.addEventListener("change",()=>scheduleIsoFrame(false));
 $("atlas-stack")?.addEventListener("change",()=>scheduleIsoFrame(false));
 $("atlas-slab")?.addEventListener("input",event=>{
    $("atlas-slab-label").textContent=fmt(Number(event.target.value),2)+" m";
    scheduleIsoFrame(false);
 });
}
function show3d(){
 active2d=false;document.body.classList.add("atlas-mode-3d");
 $("cpt-atlas-2d").classList.add("atlas-hide");
 mainGraph.classList.add("atlas-hide");
 setSvg3dVisible(true);
 $("atlas-2d").classList.remove("chosen");$("atlas-webgl").classList.remove("chosen");
 $("atlas-3d").classList.add("chosen");
 $("atlas-depth-tools").classList.remove("atlas-hide");
 $("cpt-studio").classList.remove("atlas-hide");
 renderSvg3d();
 $("cpt-atlas-status").textContent="SOIL SECTION MODE: show nearby measured intervals + translucent, locally supported class bands. For all layers switch 3D DETAIL. Click CPT for full profile. Inferred soil volumes are NOT direct measurements.";
}
function showWebgl(){
 active2d=false;document.body.classList.remove("atlas-mode-3d");
 $("cpt-atlas-2d").classList.add("atlas-hide");
 setSvg3dVisible(false);
 mainGraph.classList.remove("atlas-hide");
 $("atlas-2d").classList.remove("chosen");$("atlas-3d").classList.remove("chosen");
 $("atlas-webgl").classList.add("chosen");
 $("atlas-depth-tools").classList.add("atlas-hide");
 $("cpt-studio").classList.remove("atlas-hide");
 requestAnimationFrame(resizeVisibleAtlas);
 $("cpt-atlas-status").textContent="GPU-accelerated 3D. If graphics are unavailable, choose 3D SOIL COLUMNS for reliable interactive viewing.";
}
function show2d(){
 active2d=true;document.body.classList.remove("atlas-mode-3d");
 mainGraph.classList.add("atlas-hide");setSvg3dVisible(false);
 $("cpt-atlas-2d").classList.remove("atlas-hide");
 $("atlas-3d").classList.remove("chosen");$("atlas-webgl").classList.remove("chosen");
 $("atlas-2d").classList.add("chosen");
 $("cpt-studio").classList.add("atlas-hide");$("atlas-depth-tools").classList.remove("atlas-hide");
 render2d();setTimeout(resizeVisibleAtlas,80);
}
function recolor3d(){
 if(!$("cpt-atlas-svg3d")?.classList.contains("atlas-hide"))renderSvg3d();
}
function resizeVisibleAtlas(){
 const isoHost=$("cpt-atlas-svg3d");
 if(isoHost&&!isoHost.classList.contains("atlas-hide")){renderSvg3d();return;}
 const el=active2d?$("cpt-atlas-2d"):mainGraph;
 // Plotly.Plots.resize throws if a plot is HIDDEN. Never resize the
 // hidden WebGL scene while GPU-independent SVG 3D soil is displayed.
 if(!el||el.classList.contains("atlas-hide")||!el.isConnected||
    !el.getClientRects().length||el.clientWidth<10||el.clientHeight<10||
    !el._fullLayout||!el.data)return;
 try{Promise.resolve(Plotly.Plots.resize(el)).catch(err=>{
  console.warn("Atlas plot resize skipped",String(err));
 });}
 catch(err){console.warn("Atlas plot resize skipped",String(err));}
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
 "<button id='atlas-2d' class='chosen'>2D SOIL PLAN</button><button id='atlas-3d'>3D SOIL COLUMNS</button>"+
 "<button id='atlas-webgl' title='Optional graphics-accelerated 3D'>WEBGL (GPU)</button>"+
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
 "<span>Wheel zoom / drag pan · click CPT for measurements</span>"+
 "<button type='button' id='atlas-silt-only' class='atlas-hide'>SILT ONLY</button>"+
 "<button type='button' id='atlas-all-layers' class='atlas-hide chosen'>ALL SOIL TYPES</button>"+
 "<label for='atlas-vertical' id='atlas-vertical-label' class='atlas-hide'>3D depth exaggeration</label>"+
 "<input type='range' id='atlas-vertical' class='atlas-hide' min='2' max='12' step='.5' value='6'>"+
 "<label id='atlas-geology-wrap' class='atlas-hide'><input type='checkbox' id='atlas-geology' checked>INTERPRETED SOIL-LAYER VOLUME <small>(not measured between CPTs)</small></label>"+
 "<label id='atlas-measured-wrap' class='atlas-hide'><input type='checkbox' id='atlas-measured' checked>SHOW SURVEYED CPT COLUMNS</label>"+
 "<label id='atlas-detail-wrap' class='atlas-hide'>3D DETAIL <select id='atlas-detail'><option value='section' selected>SECTION + LOCAL LAYERS (FAST)</option><option value='all'>ALL MEASURED LAYERS (SLOW)</option></select></label>"+
 "<label id='atlas-slab-wrap' class='atlas-hide'>Vertical section thickness <input type='range' min='.1' max='1.5' step='.1' value='.5' id='atlas-slab'><output id='atlas-slab-label'>0.50 m</output></label>"+
 "<label id='atlas-stack-wrap' class='atlas-hide'>INTERPRETED SOIL STACKS <select id='atlas-stack'><option value='1'>Single depth layer</option><option value='3' selected>3 depth layers (recommended)</option><option value='5'>5 depth layers (more detail)</option></select></label>";
 document.body.insertBefore(head,document.body.firstChild);
 document.body.insertBefore(bar,head.nextSibling);
 document.body.insertBefore(host,bar.nextSibling);
 const graphs=$("cpt-atlas-graphs");
 graphs.appendChild(mainGraph);
 let two=document.createElement("div");two.id="cpt-atlas-2d";graphs.appendChild(two);
 let isoview=document.createElement("div");isoview.id="cpt-atlas-svg3d";
 isoview.className="atlas-hide";graphs.appendChild(isoview);
 isoview.innerHTML="<svg id='cpt-atlas-isometric' aria-label='Interactive measured CPT 3D soil columns'></svg>";
 // In focus-map mode the entire sidebar is hidden; a permanently reachable
 // restore button MUST remain on the map canvas, not inside the hidden rail.
 const showPanel=document.createElement("button");
 showPanel.id="atlas-show-panel";showPanel.type="button";
 showPanel.textContent="SHOW MAP CONTROLS";
 showPanel.setAttribute("aria-label","Restore map controls sidebar");
 $("cpt-atlas-map").appendChild(showPanel);
 showPanel.onclick=()=>{document.body.classList.remove("atlas-focus-map");
   $("atlas-expand").textContent="HIDE DETAILS";requestAnimationFrame(resizeVisibleAtlas)};
 const studio=$("cpt-studio");
 // Relocate the existing REAL controls instead of duplicating them. All
 // event handlers keep operating on the same DOM nodes and one map canvas.
 const rail=$("cpt-atlas-aside");
 rail.insertBefore(head,rail.firstChild);
 rail.insertBefore(bar,head.nextSibling);
 rail.insertBefore(studio,bar.nextSibling);

 // Keep the original E-W and N-S fence plots as expandable secondary views.
 const rest=document.createElement("details");rest.className="atlas-fences";
 rest.innerHTML="<summary>Show E–W / N–S CPT fence sections</summary>";
 const move=[];
 [...document.querySelectorAll("body > section")].forEach(el=>{if(el!==host&&el.id!=="cpt-studio")move.push(el)});
 move.forEach(el=>rest.appendChild(el));
 document.body.appendChild(rest);
 const grand=Math.ceil(Math.max(1,...SEG.map(s=>s.bottom))*10)/10;
 // Choose a representative starting depth with actual class diversity.
 // Showing 4.50m for every project can yield a flat yellow sand map even
 // when strong soil contrasts exist at 4.8 or 5.2m.
 let suggestedDepth=Math.min(4.5,grand),bestScore=-Infinity;
 for(let d=1.0;d<=Math.min(grand,9);d+=.10){
   const classified=SOURCE.map(p=>p.status==="REVIEW"?null:zone(p,d)?.category??null)
      .filter(Boolean);
   const coverage=classified.length/Math.max(1,SOURCE.length);
   if(coverage<.55)continue;
   const count=Object.fromEntries(CLASSES.map(k=>[k,classified.filter(x=>x===k).length]));
   const richness=CLASSES.filter(k=>count[k]>0).length;
   const entropy=-CLASSES.reduce((s,k)=>{
      const f=count[k]/Math.max(1,classified.length);
      return s+(f?f*Math.log(f):0);
   },0);
   const score=richness*4+entropy*3+coverage-0.06*Math.abs(d-4.5);
   if(score>bestScore){bestScore=score;suggestedDepth=d;}
 }
 $("atlas-depth").max=grand;$("atlas-depth").value=suggestedDepth.toFixed(2);
 depth=Number($("atlas-depth").value);
 $("atlas-depth-number").value=depth.toFixed(2);
 $("atlas-depth-label").textContent=fmt(depth)+" m";
 $("atlas-2d").onclick=show2d;$("atlas-3d").onclick=show3d;
 $("atlas-webgl").onclick=showWebgl;
 function applyLayerPreset(siltOnly){
  document.querySelectorAll("[data-layer]").forEach(el=>{
   el.checked=!siltOnly||el.dataset.layer==="silt";
  });
  $("atlas-silt-only").classList.toggle("chosen",siltOnly);
  $("atlas-all-layers").classList.toggle("chosen",!siltOnly);
  if(!$("cpt-atlas-svg3d").classList.contains("atlas-hide"))renderSvg3d();
 }
 $("atlas-silt-only").onclick=()=>applyLayerPreset(true);
 $("atlas-all-layers").onclick=()=>applyLayerPreset(false);
 initIsoInteraction();
 const setDepth=value=>{
  depth=Math.min(grand,Math.max(0,Number.isFinite(Number(value))?Number(value):depth));
  $("atlas-depth").value=depth;
  $("atlas-depth-number").value=depth.toFixed(2);
  $("atlas-depth-label").textContent=fmt(depth)+" m";
  if(active2d)schedule2d();
  if(!$("cpt-atlas-svg3d")?.classList.contains("atlas-hide"))scheduleIsoFrame(false);
  if(selected)inspect(byref[selected],true);
 };
 $("atlas-depth").oninput=()=>setDepth($("atlas-depth").value);
 $("atlas-depth-number").onchange=()=>setDepth($("atlas-depth-number").value);
 $("atlas-mode").onchange=()=>{if(active2d)render2d();recolor3d()};
 $("atlas-find").onchange=()=>{let v=$("atlas-find").value.toLowerCase().trim();const p=SOURCE.find(p=>p.ref.toLowerCase()===v)||
 SOURCE.find(p=>p.ref.toLowerCase().includes(v));if(p)focusCpt(p)};
 const pan=$("atlas-pan"),zoom=$("atlas-box");
 pan.onclick=()=>{navMode="pan";pan.classList.add("chosen");zoom.classList.remove("chosen");
  if(active2d)Plotly.relayout("cpt-atlas-2d",{dragmode:"pan"});};
 zoom.onclick=()=>{navMode="zoom";zoom.classList.add("chosen");pan.classList.remove("chosen");
  if(active2d)Plotly.relayout("cpt-atlas-2d",{dragmode:"zoom"});};
 const zoomBy=factor=>{
  if(!$("cpt-atlas-svg3d").classList.contains("atlas-hide")){
    iso.zoom=Math.max(.4,Math.min(10,iso.zoom*factor));renderSvg3d();return;
  }
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
 $("atlas-fit").onclick=()=>{
   if(!$("cpt-atlas-svg3d").classList.contains("atlas-hide")){
      iso.zoom=1;iso.tx=0;iso.ty=0;iso.az=-.7;iso.elev=.53;renderSvg3d();
   }else if(active2d){
      Plotly.relayout("cpt-atlas-2d",{"xaxis.autorange":true,"yaxis.autorange":true});
   }else Plotly.relayout(mainGraph,{"scene.camera.eye":{x:1.6,y:-1.6,z:1.05}});
 };
 $("atlas-expand").onclick=()=>{
  document.body.classList.toggle("atlas-focus-map");
  const focused=document.body.classList.contains("atlas-focus-map");
  $("atlas-expand").textContent=focused?"SHOW DETAILS":"HIDE DETAILS";
  setTimeout(resizeVisibleAtlas,120);
 };
 $("atlas-save").onclick=()=>{
   if(!$("cpt-atlas-svg3d").classList.contains("atlas-hide"))saveIsometricPng();
   else Plotly.downloadImage(active2d?"cpt-atlas-2d":TARGET,{
        format:"png",filename:"CPT_ATLAS_"+(active2d?"2D":"WEBGL_3D"),
        width:1800,height:1200,scale:1});
 };
 function saveIsometricPng(){
   const svg=$("cpt-atlas-isometric");
   const w=Math.round($("cpt-atlas-svg3d").clientWidth||1100);
   const h=Math.round($("cpt-atlas-svg3d").clientHeight||750);
   const xml=new XMLSerializer().serializeToString(svg);
   const url="data:image/svg+xml;charset=utf-8,"+encodeURIComponent(xml);
   const pic=new Image();
   pic.onload=()=>{
     const cv=document.createElement("canvas");cv.width=w*2;cv.height=h*2;
     const ctx=cv.getContext("2d");ctx.fillStyle="#fff";ctx.fillRect(0,0,cv.width,cv.height);
     ctx.scale(2,2);ctx.drawImage(pic,0,0,w,h);
     cv.toBlob(blob=>{
       if(!blob)return;
       const u=URL.createObjectURL(blob),link=document.createElement("a");
       link.href=u;link.download="CPT_ATLAS_3D_MEASURED_SOIL.png";link.click();
       setTimeout(()=>URL.revokeObjectURL(u),1200);
     },"image/png");
   };
   pic.src=url;
 }
 $("atlas-full").onclick=()=>{
   if(document.fullscreenElement)document.exitFullscreen();
   else $("cpt-atlas-map").requestFullscreen();
 };
 const ranked=SOURCE.filter(p=>Number.isFinite(p.max)).sort((a,b)=>b.max-a.max);
 $("cpt-atlas-rank").innerHTML=ranked.slice(0,12).map((p,i)=>
  "<button data-id='"+clean(p.ref)+"'>#"+(i+1)+" · "+clean(p.ref)+" — "+fmt(p.max,3)+" m</button>").join("");
 $("cpt-atlas-rank").querySelectorAll("button").forEach(el=>el.onclick=()=>focusCpt(byref[el.dataset.id]));
 const lows=SOURCE.filter(p=>Number.isFinite(p.max)&&p.max>0).sort((a,b)=>a.max-b.max);
 const absent=SOURCE.filter(p=>p.max===0).length;
 $("cpt-atlas-minrank").innerHTML=lows.slice(0,10).map((p,i)=>
    "<button data-id='"+clean(p.ref)+"'>#"+(i+1)+" · "+clean(p.ref)+" — "+fmt(p.max,3)+" m</button>").join("")+
    "<p class='atlas-note'>"+absent+" CPTs have no qualifying observed silt screen; they are not counted as thin positive layers.</p>";
 $("cpt-atlas-minrank").querySelectorAll("button").forEach(el=>el.onclick=()=>inspect(byref[el.dataset.id]));
 // Initialize the important 2D engineering view immediately. It must NOT
 // depend on the GPU-intensive 3D scene finishing its asynchronous traces.
 // This isolates the 2D map from WebGL context limits on engineering laptops.
 show2d();
 // Start in the meaningful full stratigraphy explorer, not the old static
 // point-plan. 2D can still be selected at any moment; its Plotly data and
 // depth controls are already initialized before this transition.
 setTimeout(()=>{try{show3d()}catch(err){
   console.warn("3D isometric initialization failed; keeping measured 2D plan",err);
   show2d();
 }},220);
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
   const thicknessToggle=$("cpt-thickness-color");
   const collarIndex=mainGraph.data.findIndex(t=>t.name==="Measured CPT collars · thickness");
   if(thicknessToggle&&collarIndex>=0){
     thicknessToggle.onchange=()=>Plotly.restyle(mainGraph,
                                  {visible:thicknessToggle.checked},[collarIndex]);
   }
   for(const id of ["cpt-top","cpt-bottom"])$(id).addEventListener("input",()=>setTimeout(recolor3d,80));
   recolor3d();
 }).catch(error=>{
   console.warn("3D collar overlay unavailable; independent 2D map remains functional",error);
   $("cpt-atlas-status").textContent="2D working. 3D graphics acceleration unavailable; inspect source CPTs in the 2D plan.";
 });
 window.addEventListener("resize",()=>requestAnimationFrame(resizeVisibleAtlas));
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

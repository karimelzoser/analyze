from __future__ import annotations

import math
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.figure import Figure
import numpy as np

from cpt_core import CPTAnalysis
from reporting_pro import analysis_record, sbtn_background, IC_BOUNDS, IC_NAMES, IC_COLORS, SBTN_COLORS, _finite, _fmt, _date_display


def draw_reference_sbtn(ax, a: CPTAnalysis):
    _fr, _q, F, Q, _ic, zone = sbtn_background(360)
    cmap=ListedColormap(SBTN_COLORS); norm=BoundaryNorm(np.arange(.5,10.5,1),cmap.N)
    ax.pcolormesh(F,Q,zone,cmap=cmap,norm=norm,shading="auto",rasterized=True)
    ax.contour(F,Q,zone,levels=np.arange(1.5,9.5,1),colors="black",linewidths=.72)
    for num,x,y in [(1,.30,3.5),(2,7.0,1.8),(3,3.0,7),(4,1.3,15),(5,.60,30),(6,.28,90),(7,.18,430),(8,3.0,450),(9,6.0,220)]:
        ax.text(x,y,str(num),ha="center",va="center",fontsize=9)
    m=np.isfinite(a.fr)&np.isfinite(a.qtn)&(a.fr>0)&(a.qtn>0)
    fx,qy,dz=a.fr[m],a.qtn[m],a.depth[m]
    if len(fx):
        lo,hi=float(np.nanmin(dz)),float(np.nanmax(dz)); rel=(dz-lo)/max(hi-lo,1e-9)
        for gm,color in [(rel<.36,"#ff5a1f"),((rel>=.36)&(rel<.73),"#b56576"),(rel>=.73,"#a00078")]:
            if np.any(gm): ax.scatter(fx[gm],qy[gm],s=7,marker="s",linewidths=0,color=color,alpha=.95,zorder=4)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(.1,10); ax.set_ylim(1,1000)
    ax.set_xlabel("Normalized Friction Ratio, Fr, %",fontsize=6); ax.set_ylabel("Normalized Cone Resistance Qtn",fontsize=6)
    ax.tick_params(labelsize=5.5); ax.grid(False)
    for sp in ax.spines.values(): sp.set_linewidth(.8); sp.set_color("black")


def _level_axis(a):
    """Use measured sounding extents, not a fixed ±10m axis that hides detail."""
    depth=np.asarray(a.depth,dtype=float)
    valid=depth[np.isfinite(depth)]
    if not len(valid):
        return depth,"Depth below ground, m",(0,1)
    g=a.metadata.get("ground_elevation")
    if isinstance(g,(int,float)) and math.isfinite(float(g)):
        level=float(g)-depth
        measured=level[np.isfinite(level)]
        upper=math.ceil((float(np.max(measured))+.03)*2)/2
        lower=math.floor((float(np.min(measured))-.03)*2)/2
        if upper-lower<.5:lower=upper-.5
        return level,"Elevation RL, m",(upper,lower)
    top=max(0.,math.floor((float(np.min(valid))-.03)*2)/2)
    bottom=math.ceil((float(np.max(valid))+.03)*2)/2
    if bottom-top<.5:bottom=top+.5
    return depth,"Depth BGL, m",(top,bottom)


def report_page(a: CPTAnalysis) -> Figure:
    fig=Figure(figsize=(8.27,11.69),dpi=150)
    gs=fig.add_gridspec(30,14,left=.035,right=.975,top=.952,bottom=.035,hspace=.82,wspace=.95)
    md=a.metadata
    fig.text(.04,.976,"Client     :",fontsize=8.5,weight="bold",va="top"); fig.text(.125,.976,str(md.get("client") or "N/A - not supplied"),fontsize=8.5,weight="bold",va="top")
    fig.text(.04,.957,"Project   :",fontsize=8.5,weight="bold",va="top"); fig.text(.125,.957,str(md.get("project_name") or md.get("project_id") or "N/A - not supplied"),fontsize=8.5,weight="bold",va="top")
    fig.text(.965,.976,"SGP    CTSG    CTS GULF    TERRA FIRMA",ha="right",va="top",fontsize=8.8,weight="bold")
    fig.lines.extend([
        matplotlib.lines.Line2D([.03,.98],[.985,.985],transform=fig.transFigure,color="black",lw=.8),matplotlib.lines.Line2D([.03,.98],[.944,.944],transform=fig.transFigure,color="black",lw=.8),
        matplotlib.lines.Line2D([.03,.03],[.985,.04],transform=fig.transFigure,color="black",lw=.8),matplotlib.lines.Line2D([.98,.98],[.985,.04],transform=fig.transFigure,color="black",lw=.8)])
    vertical,ylab,ylim=_level_axis(a)
    axq=fig.add_subplot(gs[2:18,0:4]); axf=fig.add_subplot(gs[2:18,5:9]); axi=fig.add_subplot(gs[2:18,10:14])
    qvals=_finite(a.qc); qmax=max(50.0,math.ceil((float(np.nanmax(qvals)) if len(qvals) else 50)/10)*10)
    axq.plot(a.qc,vertical,color="black",lw=.85); axq.set_xlim(0,qmax); axq.set_title("Cone resistance, qc, MPa",fontsize=7.2); axq.xaxis.tick_top(); axq.set_ylabel(ylab,fontsize=6.5)
    fvals=_finite(a.fs); fmax=max(.5,math.ceil((float(np.nanmax(fvals)) if len(fvals) else .5)*10)/10)
    axf.plot(a.fs,vertical,color="#7b2cbf",lw=.8); axf.set_xlim(0,fmax); axf.set_title("Sleeve Friction, fs, MPa",fontsize=7.2); axf.xaxis.tick_top(); axf.tick_params(axis="x",bottom=False,labelbottom=False)
    axu=axf.twiny(); axu.plot(a.u2,vertical,color="#21a366",ls="--",lw=.75); uv=_finite(a.u2); umax=max(.05,float(np.nanpercentile(np.abs(uv),99))*1.15 if len(uv) else .05); axu.set_xlim(umax,0); axu.xaxis.set_ticks_position("bottom"); axu.xaxis.set_label_position("bottom"); axu.spines["bottom"].set_position(("outward",2)); axu.spines["bottom"].set_visible(True); axu.spines["top"].set_visible(False); ticks=np.linspace(umax,0,6); axu.set_xticks(ticks); axu.set_xticklabels([f"{v:.1f}" for v in ticks]); axu.tick_params(axis="x",labelsize=5,pad=0); axu.set_xlabel("Pore Pressure, u2, MPa",fontsize=5.7,labelpad=-1)
    for c,(lo,hi) in enumerate(zip(IC_BOUNDS[:-1],IC_BOUNDS[1:])): axi.axvspan(lo,hi,color=IC_COLORS[c],alpha=.95,lw=0)
    axi.plot(a.ic,vertical,color="black",lw=.85); axi.set_xlim(0,5); axi.set_title("Soil Behaviour Type Index, Ic",fontsize=7.2); axi.xaxis.tick_top(); axi.set_xticks([0,1.31,2.05,2.60,2.95,3.60,5]); axi.set_xticklabels(["0","1.31","2.05","2.60","2.95","3.60","5.00"],fontsize=5.3)
    for ax in (axq,axf,axi):
        ax.set_ylim(*ylim); ax.grid(True,which="major",lw=.3,color="#dddddd"); ax.tick_params(labelsize=5.4,length=2.5); [sp.set_linewidth(.75) for sp in ax.spines.values()]
    fig.text(.16,.366,"— Cone resistance",fontsize=5.2,ha="center"); fig.text(.445,.366,"— Sleeve friction",fontsize=5.2,ha="center"); fig.text(.565,.366,"-- Pore Pressure",fontsize=5.2,ha="center"); fig.text(.84,.366,"— Soil behavior type index",fontsize=5.2,ha="center")
    leg=fig.add_subplot(gs[19:24,0:7]); leg.axis("off")
    for i,(name,color) in enumerate(zip(IC_NAMES,IC_COLORS)):
        r,c=divmod(i,2); x=.02+c*.52; y=.84-r*.25; leg.add_patch(matplotlib.patches.Rectangle((x,y-.055),.035,.11,transform=leg.transAxes,color=color)); leg.text(x+.045,y,name,fontsize=5.5,va="center",transform=leg.transAxes)
    meta=fig.add_subplot(gs[24:30,0:8]); meta.axis("off"); e,n=md.get("easting"),md.get("northing"); g=md.get("ground_elevation")
    rows=[["Main Contractor:",str(md.get("main_contractor") or "NOT SUPPLIED IN CPT SOURCE")],
          ["Test Location:",a.reference],
          ["Ground Elevation:",_fmt(g,2) if g is not None else "NOT RECORDED"],
          ["Coordinates:",(f"Easting {_fmt(e,3)}      Northing {_fmt(n,3)}"
                if e is not None and n is not None else "NOT RECORDED IN SOURCE")],
          ["Cone ID:",str(md.get("cone_id") or "NOT RECORDED IN SOURCE")],
          ["Test Date:",_date_display(md.get("test_date")) if md.get("test_date") else
                        "NOT RECORDED (SEE FILE DATE BELOW)"],
          ["GEF File Date:",_date_display(md.get("file_date")) if md.get("file_date") else
                        "NOT RECORDED IN SOURCE"],
          ["Source / data quality:",str(md.get("pore_pressure_source") or
                                     "Original CPT numerical source; verify instrumentation")]]
    tbl=meta.table(cellText=rows,colWidths=[.34,.66],loc="center",cellLoc="left"); tbl.auto_set_font_size(False); tbl.set_fontsize(5.9); tbl.scale(1,1.18)
    for (r,c),cell in tbl.get_celld().items(): cell.set_edgecolor("#999"); cell.set_linewidth(.45); cell.set_facecolor("#ddd") if c==0 else None; cell.set_text_props(weight="bold") if c==0 else None
    sbt=fig.add_subplot(gs[19:30,8:14]); draw_reference_sbtn(sbt,a)
    return fig


def analysis_page(a: CPTAnalysis) -> Figure:
    r=analysis_record(a); fig=Figure(figsize=(8.27,11.69),dpi=150); ax=fig.add_subplot(111); ax.axis("off")
    fig.text(.07,.95,"CPT ANALYSIS SUMMARY",fontsize=16,weight="bold"); fig.text(.07,.918,a.reference,fontsize=11,weight="bold")
    rows=[["Verification status",r["status"]],["Silt start - reported",str(r["start"]) if isinstance(r["start"],str) else _fmt(r["start"],2," m")],["Silt start RL - reported",_fmt(r["start_rl"],2," m")],["Silt end - reported",_fmt(r["end"],2," m")],["Silt end RL - reported",_fmt(r["end_rl"],2," m")],["Silt thickness - reported",_fmt(r["thickness"],2," m")],["Sand layer thickness",_fmt(r["sand"],2," m")],["Raw interpolated silt start",_fmt(r["raw_start"],3," m")],["Raw analysis end",_fmt(r["raw_end"],3," m")],["Raw interval thickness",_fmt(r["raw_thickness"],3," m")],["Corrected sounding depth",_fmt(r["test_depth_raw"],3," m")],["Maximum valid Ic",_fmt(r["max_ic"],3)],["Ic at silt start",_fmt(r["ic_start"],3)],["Soil behaviour at silt start",r["behavior"]],["Qtn / Fr at start",f"{_fmt(r['qtn_start'],3)} / {_fmt(r['fr_start'],3,'%')}"],["qc / fs / u2 at start",f"{_fmt(r['qc_start'],4)} / {_fmt(r['fs_start'],4)} / {_fmt(r['u2_start'],4)} MPa"],["Detected silt intervals",str(r["interval_count"])],["Selected interval",r["selected_interval"]],["Pass 1",r["pass1"]],["Pass 2",r["pass2"]],["Terminal sensor dropout",_fmt(r["dropout_depth"],3," m") if r["dropout"] else "None detected"]]
    tbl=ax.table(cellText=rows,colWidths=[.38,.56],cellLoc="left",bbox=[.08,.38,.84,.47]); tbl.auto_set_font_size(False); tbl.set_fontsize(7.2)
    for (rr,cc),cell in tbl.get_celld().items(): cell.set_edgecolor("#b5b5b5"); cell.set_linewidth(.55); cell.set_facecolor("#eee") if cc==0 else None; cell.set_text_props(weight="bold") if cc==0 else None
    ax.text(.08,.33,"Verification note",transform=ax.transAxes,fontsize=9.5,weight="bold"); ax.text(.08,.295,r["note"],transform=ax.transAxes,fontsize=7.5,wrap=True,va="top")
    ax.text(.08,.23,"Calculation basis",transform=ax.transAxes,fontsize=9.5,weight="bold"); ax.text(.08,.195,"Raw GEF/GFF corrected depth, qc, fs and u2 are used for qt, Fr, Qtn and Robertson-style Ic. The Ic=2.60 crossing is interpolated. Short terminal exact-zero sleeve-friction dropout is excluded from Ic. Two independent passes must agree; disagreements receive sensitivity rechecks. Reported start/end are rounded to 0.10 m and reported thickness is end minus start.",transform=ax.transAxes,fontsize=7.3,wrap=True,va="top")
    return fig


def generate_pdf(a:CPTAnalysis,output_path:str|Path)->Path:
    p=Path(output_path); p.parent.mkdir(parents=True,exist_ok=True)
    with PdfPages(p) as pdf:
        f=report_page(a); pdf.savefig(f); f.clear(); f=analysis_page(a); pdf.savefig(f); f.clear()
    return p

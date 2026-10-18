"""Audited raw PRE/POST CPT comparisons on an observed common depth grid.

No extrapolation into unmeasured layers or across invalid sensor readings.
A depth-wise rise in qc does not by itself prove acceptance of ground improvement.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import math
import numpy as np


FIELDS=("qc","fs","u2","qt","fr","qtn","ic")
LABELS={"qc":"Cone resistance qc (MPa)","fs":"Sleeve friction fs (MPa)",
        "u2":"Pore pressure u2 (MPa)","qt":"Corrected cone resistance qt (MPa)",
        "fr":"Friction ratio Fr (%)","qtn":"Normalized cone resistance Qtn (-)",
        "ic":"Soil behavior index Ic (-)"}


@dataclass
class DepthChange:
    pre_reference: str
    post_reference: str
    depth_m: np.ndarray
    metrics: dict
    statistics: dict
    mode: str
    notes: tuple[str,...]
    coordinate_offset_m: float|None
    pre_window: int
    post_window: int


def _coordinate_offset(a,b):
    try:
        axy=(float(a.metadata["easting"]),float(a.metadata["northing"]))
        bxy=(float(b.metadata["easting"]),float(b.metadata["northing"]))
    except (KeyError,TypeError,ValueError,AttributeError):
        return None
    if not all(map(math.isfinite,axy+bxy)):return None
    return math.hypot(axy[0]-bxy[0],axy[1]-bxy[1])


def _smooth(values,valid,window):
    """Centered moving mean restricted to consecutive valid observations."""
    from engineering_layers import _smooth_contiguous
    return _smooth_contiguous(np.asarray(values,float),np.asarray(valid,bool),int(window))


def _interpolate_observed(depth,values,grid,*,max_gap_m=.06):
    """Piecewise interpolate ONLY between adjacent valid points less than max_gap_m apart."""
    z=np.asarray(depth,float);v=np.asarray(values,float);g=np.asarray(grid,float)
    if len(z)!=len(v) or len(z)<2 or np.any(np.diff(z)<=0):
        raise ValueError("CPT corrected depths must be strictly increasing and aligned")
    i=np.searchsorted(z,g,side="right")-1
    i=np.clip(i,0,len(z)-2)
    lo=z[i];hi=z[i+1];v0=v[i];v1=v[i+1]
    observed=(g>=z[0])&(g<=z[-1])&(hi-lo>0)&(hi-lo<=max_gap_m)
    observed&=np.isfinite(v0)&np.isfinite(v1)
    answer=np.full(len(g),np.nan)
    answer[observed]=v0[observed]+(v1[observed]-v0[observed])*(
                        (g[observed]-lo[observed])/(hi[observed]-lo[observed]))
    return answer


def compare_depth_profiles(pre,post,*,mode="harmonized",common_window=3,
                           pre_reference_window=3,post_reference_window=10,
                           depth_step_m=.02,max_gap_m=.06,
                           coordinate_tolerance_m=2.,allow_unlocated=False):
    """Compare two explicitly paired raw CPT analyses.

    mode='reference' reflects engineer-specified PRE=3 / POST=10 Ic
    smoothing but has a method-confounding warning. mode='harmonized'
    applies one common Ic window to both profiles.
    """
    if mode not in ("harmonized","reference"):
        raise ValueError("mode must be 'harmonized' or 'reference'")
    if not (0<depth_step_m<=.1 and 0<max_gap_m<=.2):
        raise ValueError("Invalid comparison depth step or gap")
    offset=_coordinate_offset(pre,post)
    if offset is None and not allow_unlocated:
        raise ValueError("Matching coordinates are required unless explicitly overridden")
    if offset is not None and offset>coordinate_tolerance_m:
        raise ValueError("Different CPT locations: coordinate offset %.2f m exceeds %.2f m"%
                         (offset,coordinate_tolerance_m))
    zpre=np.asarray(pre.depth,float)
    zpost=np.asarray(post.depth,float)
    start=max(float(zpre[0]),float(zpost[0]))
    end=min(float(zpre[-1]),float(zpost[-1]))
    if end-start<depth_step_m*2:
        raise ValueError("No sufficiently overlapping observed depth range")
    grid=np.arange(start,end+depth_step_m*.3,depth_step_m)
    grid=grid[grid<=end+1e-9]
    wp,wq=(int(common_window),int(common_window)) if mode=="harmonized" else (
        int(pre_reference_window),int(post_reference_window))
    metrics={};statistics={}
    pre_icvalid=np.isfinite(pre.ic)&np.asarray(pre.valid_sensor,bool)
    post_icvalid=np.isfinite(post.ic)&np.asarray(post.valid_sensor,bool)
    for field in FIELDS:
        before=np.asarray(getattr(pre,field),float).copy()
        after=np.asarray(getattr(post,field),float).copy()
        if field=="ic":
            before=_smooth(before,pre_icvalid,wp)
            after=_smooth(after,post_icvalid,wq)
            before[~pre_icvalid]=np.nan
            after[~post_icvalid]=np.nan
        pre_line=_interpolate_observed(zpre,before,grid,max_gap_m=max_gap_m)
        post_line=_interpolate_observed(zpost,after,grid,max_gap_m=max_gap_m)
        aligned=np.isfinite(pre_line)&np.isfinite(post_line)
        change=np.where(aligned,post_line-pre_line,np.nan)
        metrics[field]={"pre":pre_line,"post":post_line,"delta":change,"paired_valid":aligned}
        vals=change[aligned]
        statistics[field]={
            "paired_samples":int(aligned.sum()),
            "paired_coverage_m":float(aligned.sum()*depth_step_m),
            "mean_delta":float(np.mean(vals)) if len(vals) else None,
            "median_delta":float(np.median(vals)) if len(vals) else None,
            "min_delta":float(np.min(vals)) if len(vals) else None,
            "max_delta":float(np.max(vals)) if len(vals) else None,
        }
    notes=[
       "All delta values mean POST minus PRE, not proof of engineering compliance.",
       "Only interpolated values bracketed by two valid measured samples are compared.",
       "No interval extending through a sampling gap or missing sensor data is compared.",
       "The original GEF files are authoritative; Ic is a behavior index not laboratory USCS.",
       "Smoothing affects only the plotted/compared Ic curve in this implementation;",
       "workbook formula-order parity is not certified.",
    ]
    if mode=="reference":
        notes.append("Reference PRE(3)/POST(10) smoothing differs and can create apparent changes.")
    try:
        pre_elev=float(pre.metadata["ground_elevation"])
        post_elev=float(post.metadata["ground_elevation"])
        if abs(pre_elev-post_elev)>.02:
            notes.append("PRE and POST ground elevations differ by %.3fm. BGL depth-wise pairing is provisional; review common elevation datum." % (post_elev-pre_elev))
    except (KeyError,TypeError,ValueError):
        notes.append("Ground elevations not both available; BGL depth alignment requires engineer review.")
    return DepthChange(str(pre.reference),str(post.reference),grid,metrics,statistics,mode,
                        tuple(notes),offset,wp,wq)


def export_depth_change(change:DepthChange,output_dir:str|Path)->dict[str,Path]:
    """Write depth-by-depth Excel/PNG/PDF with traceable pre/post, delta and QA."""
    import xlsxwriter
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_pdf import PdfPages
    d=Path(output_dir);d.mkdir(parents=True,exist_ok=True)
    xlsx=d/"CPT_Depth_Comparison.xlsx"
    wb=xlsxwriter.Workbook(str(xlsx))
    header=wb.add_format({"bold":True,"font_color":"#fff","bg_color":"#163047",
                          "text_wrap":True,"valign":"vcenter"})
    number=wb.add_format({"num_format":"0.000","align":"center"})
    ws=wb.add_worksheet("Depth Profiles")
    cols=["Depth BGL (m)"]
    for f in FIELDS:
        cols.extend([f+" PRE",f+" POST",f+" delta",f+" paired-valid"])
    for c,t in enumerate(cols):ws.write(0,c,t,header)
    for i,z in enumerate(change.depth_m,1):
        ws.write_number(i,0,float(z),number)
        col=1
        for f in FIELDS:
            vals=change.metrics[f]
            for side in ("pre","post","delta"):
                v=vals[side][i-1]
                if np.isfinite(v):ws.write_number(i,col,float(v),number)
                col+=1
            ws.write_boolean(i,col,bool(vals["paired_valid"][i-1]));col+=1
    ws.freeze_panes(1,1);ws.autofilter(0,0,len(change.depth_m),len(cols)-1)
    ws.set_column(0,0,18);ws.set_column(1,len(cols)-1,17)
    qa=wb.add_worksheet("Comparison QA")
    qa.set_column(0,0,35);qa.set_column(1,1,110)
    for col,t in enumerate(["Parameter","Value"]):qa.write(0,col,t,header)
    facts=[("PRE CPT",change.pre_reference),("POST CPT",change.post_reference),
           ("Comparison mode",change.mode),("PRE rolling window",change.pre_window),
           ("POST rolling window",change.post_window),
           ("Matched distance (m)",change.coordinate_offset_m),
           ("Depth min (m)",float(change.depth_m[0])),
           ("Depth max (m)",float(change.depth_m[-1]))]
    facts += [("Engineering note",note) for note in change.notes]
    for i,(k,v) in enumerate(facts,1):
        qa.write(i,0,k);qa.write(i,1,str(v) if v is not None else "NOT VERIFIED")
    stats=wb.add_worksheet("Statistics")
    stat_names=["Metric","Paired samples","Paired coverage (m)","Mean delta","Median delta","Minimum delta","Maximum delta"]
    for j,name in enumerate(stat_names):stats.write(0,j,name,header)
    for i,f in enumerate(FIELDS,1):
        s=change.statistics[f]
        stats.write(i,0,LABELS[f])
        for j,key in enumerate(["paired_samples","paired_coverage_m","mean_delta","median_delta","min_delta","max_delta"],1):
            if s[key] is not None:stats.write_number(i,j,float(s[key]),number)
    stats.set_column(0,0,38);stats.set_column(1,6,22)
    wb.close()
    fig=Figure(figsize=(12,9.5),dpi=120,facecolor="white")
    for i,f in enumerate(("qc","fr","ic","qtn"),1):
        ax=fig.add_subplot(2,2,i)
        group=change.metrics[f]
        ax.plot(group["pre"],change.depth_m,linewidth=1.15,label="PRE")
        ax.plot(group["post"],change.depth_m,linewidth=1.15,label="POST")
        if f=="ic":ax.axvline(2.6,color="#dc2626",linestyle="--",linewidth=1)
        ax.invert_yaxis();ax.grid(alpha=.15);ax.set_xlabel(LABELS[f])
        ax.set_ylabel("BGL (m)");ax.legend(fontsize=8)
    fig.suptitle("Paired CPT depth profiles | "+change.mode+" | PRE/POST",fontweight="bold")
    fig.tight_layout(rect=[0,.035,1,.95])
    fig.text(.04,.02,"Engineering comparison only. See Excel QA for matching and method restrictions.",fontsize=8)
    png=d/"CPT_Depth_Comparison.png";fig.savefig(png,dpi=170)
    pdf=d/"CPT_Depth_Comparison.pdf"
    with PdfPages(pdf) as pages:pages.savefig(fig)
    return {"xlsx":xlsx,"png":png,"pdf":pdf}

from __future__ import annotations

import datetime as dt
import math
from pathlib import Path
from typing import Iterable, Sequence

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.figure import Figure
import numpy as np
import xlsxwriter

from cpt_core import CPTAnalysis, natural_ref_key

IC_BOUNDS = [0.0, 1.31, 2.05, 2.60, 2.95, 3.60, 5.0]
IC_NAMES = [
    "Gravelly sand to dense sand", "Clean to silty sand", "Silty sand to sandy silt",
    "Clayey silt to silty clay", "Silty clay to clay", "Organic soil - clay",
]
IC_COLORS = ["#FFD75A", "#F6B26B", "#A8DADC", "#79C6C5", "#4F86C6", "#7D9668"]
SBTN_COLORS = ["#ff7777", "#6f9178", "#7789e8", "#86b8b6", "#a7d5df", "#ffba78", "#ffe188", "#d0d0d0", "#b7b7b7"]


def _finite(v):
    a = np.asarray(v, dtype=float)
    return a[np.isfinite(a)]


def _fmt(v, n=2, suffix=""):
    if v is None:
        return ""
    try:
        f = float(v)
    except Exception:
        return str(v)
    if not math.isfinite(f):
        return ""
    return f"{f:.{n}f}{suffix}"


def _date_display(raw) -> str:
    s = str(raw or "")
    for sep in (",", "-", "/"):
        parts = [p.strip() for p in s.split(sep)]
        if len(parts) >= 3:
            try:
                nums = [int(x) for x in parts[:3]]
                if nums[0] > 1900:
                    return dt.date(nums[0], nums[1], nums[2]).strftime("%d-%b-%Y")
            except Exception:
                pass
    return s


def _area(ref: str) -> str:
    parts = str(ref).split("-")
    return parts[1] if len(parts) >= 3 and parts[0].upper() == "CPT" else ""


def _interp(a: CPTAnalysis, values, depth) -> float | None:
    if depth is None:
        return None
    d, v = np.asarray(a.depth, float), np.asarray(values, float)
    m = np.isfinite(d) & np.isfinite(v)
    if np.count_nonzero(m) < 2:
        return None
    d, v = d[m], v[m]
    if float(depth) < d[0] or float(depth) > d[-1]:
        return None
    return float(np.interp(float(depth), d, v))


def analysis_record(a: CPTAnalysis) -> dict:
    md = a.metadata
    z = a.final_interval
    ground = md.get("ground_elevation") if isinstance(md.get("ground_elevation"), (int, float)) else None
    start_raw = z.start_raw if z else None
    end_raw = z.end_raw if z else None
    valid_ic = _finite(a.ic)
    max_ic = float(np.max(valid_ic)) if len(valid_ic) else None
    mean_ic = float(np.mean(valid_ic)) if len(valid_ic) else None
    start_rl = float(ground) - z.start if z and ground is not None else None
    end_rl = float(ground) - z.end if z and ground is not None else None
    raw_start_rl = float(ground) - z.start_raw if z and ground is not None else None
    raw_end_rl = float(ground) - z.end_raw if z and ground is not None else None
    test_end_rl = float(ground) - a.test_depth_raw if ground is not None else None
    ic_start = _interp(a, a.ic, start_raw)
    if z and ic_start is not None and abs(ic_start - 2.60) <= 0.03:
        behavior = "Ic 2.60 boundary: silty sand / clayey silt"
    elif z and ic_start is not None:
        behavior = next((name for lo, hi, name in zip(IC_BOUNDS[:-1], IC_BOUNDS[1:], IC_NAMES) if lo <= ic_start < hi), IC_NAMES[-1])
    else:
        behavior = "NO SILT" if a.status == "NO SILT" else "REVIEW"
    return {
        "reference": a.reference, "area": _area(a.reference), "source": a.source_path.name,
        "date": _date_display(md.get("file_date")), "client": md.get("client", ""),
        "project": md.get("project_name") or md.get("project_id") or "", "contractor": md.get("main_contractor", ""),
        "location": md.get("location", ""), "cone_id": md.get("cone_id", ""), "standard": md.get("standard", ""),
        "records": md.get("records", len(a.depth)), "ground": ground, "easting": md.get("easting"), "northing": md.get("northing"),
        "area_ratio": md.get("area_ratio"), "gamma": md.get("analysis_gamma_soil_kn_m3", md.get("gamma_soil", 18.0)), "water_table": md.get("analysis_water_table_bgl_m", md.get("water_table_depth", None)),
        "test_depth": a.test_depth, "test_depth_raw": a.test_depth_raw, "test_end_rl": test_end_rl,
        "sand": (a.sand_layer_thickness if a.status=="VERIFIED" else None),
        "start": z.start if z else ("NO SILT" if a.status == "NO SILT" else "REVIEW"),
        "start_num": z.start if z else None, "start_rl": start_rl,
        "end": z.end if z else None, "end_rl": end_rl,
        "thickness": z.thickness if z else (0.0 if a.status == "NO SILT" else None),
        "raw_start": start_raw, "raw_start_rl": raw_start_rl, "raw_end": end_raw, "raw_end_rl": raw_end_rl,
        "raw_thickness": z.thickness_raw if z else None, "max_ic": max_ic, "mean_ic": mean_ic,
        "valid_ic_points": int(np.count_nonzero(np.isfinite(a.ic))), "ic_start": ic_start, "behavior": behavior,
        "qtn_start": _interp(a, a.qtn, start_raw), "fr_start": _interp(a, a.fr, start_raw),
        "qc_start": _interp(a, a.qc, start_raw), "fs_start": _interp(a, a.fs, start_raw), "u2_start": _interp(a, a.u2, start_raw),
        "interval_count": len(a.all_intervals), "selected_interval": (f"{len(a.all_intervals)}/{len(a.all_intervals)} (deepest terminal)" if z and len(a.all_intervals) > 1 else ("1/1 (terminal)" if z else "NONE")),
        "dropout": a.sensor_dropout_depth is not None, "dropout_depth": a.sensor_dropout_depth,
        "pass1": (f"{a.pass1.start:.2f} / {a.pass1.thickness:.2f}" if a.pass1 else "NO SILT"),
        "pass2": (f"{a.pass2.start:.2f} / {a.pass2.thickness:.2f}" if a.pass2 else "NO SILT"),
        "status": a.status, "note": a.verification_note,
    }


def sbtn_background(n=320):
    fr = np.logspace(-1, 1, n)
    q = np.logspace(0, 3, n)
    F, Q = np.meshgrid(fr, q)
    ic = np.sqrt((3.47 - np.log10(Q)) ** 2 + (np.log10(F) + 1.22) ** 2)
    zone = np.full_like(ic, 7, dtype=int)
    zone[ic >= 1.31] = 6
    zone[ic >= 2.05] = 5
    zone[ic >= 2.60] = 4
    zone[ic >= 2.95] = 3
    zone[ic >= 3.60] = 2
    zone[Q < 12.0 * np.exp(-1.4 * F)] = 1
    denom = 0.005 * (F - 1.0) - 0.0003 * (F - 1.0) ** 2 - 0.002
    stiff = (denom > 0) & (Q > 1.0 / denom)
    zone[stiff & (F <= 4.5)] = 8
    zone[stiff & (F > 4.5)] = 9
    return fr, q, F, Q, ic, zone


def draw_sbtn(ax, a: CPTAnalysis):
    fr, q, F, Q, ic, zone = sbtn_background()
    cmap = ListedColormap(SBTN_COLORS)
    norm = BoundaryNorm(np.arange(0.5, 10.5, 1), cmap.N)
    ax.pcolormesh(F, Q, zone, cmap=cmap, norm=norm, shading="auto", rasterized=True)
    ax.contour(F, Q, zone, levels=np.arange(1.5, 9.5, 1), colors="black", linewidths=.75)
    for num, x, y in [(1,.3,3.5),(2,7.0,1.8),(3,3.0,7),(4,1.3,15),(5,.6,30),(6,.28,90),(7,.18,430),(8,3.0,450),(9,6.0,220)]:
        ax.text(x, y, str(num), ha="center", va="center", fontsize=9)
    m = np.isfinite(a.fr) & np.isfinite(a.qtn) & (a.fr > 0) & (a.qtn > 0)
    fx, qy, dz = a.fr[m], a.qtn[m], a.depth[m]
    if len(fx):
        ax.plot(fx, qy, color="#777777", lw=.45, alpha=.55, zorder=3)
        lo, hi = float(np.nanmin(dz)), float(np.nanmax(dz))
        rel = (dz - lo) / max(hi - lo, 1e-9)
        groups = [(rel < .36, "#ff5a1f"), ((rel >= .36) & (rel < .73), "#b56576"), (rel >= .73, "#a00078")]
        for gm, color in groups:
            if np.any(gm):
                ax.scatter(fx[gm], qy[gm], s=7, marker="s", linewidths=0, color=color, alpha=.92, zorder=4)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(.1, 10); ax.set_ylim(1, 1000)
    ax.set_xlabel("Normalized Friction Ratio, Fr, %", fontsize=6)
    ax.set_ylabel("Normalized Cone Resistance Qtn", fontsize=6)
    ax.tick_params(labelsize=5.5); ax.grid(False)
    for sp in ax.spines.values(): sp.set_linewidth(.8); sp.set_color("black")


def _level_axis(a: CPTAnalysis):
    ground = a.metadata.get("ground_elevation")
    if isinstance(ground, (int, float)):
        return float(ground) - a.depth, "Level, m", (-10, 10)
    return a.depth, "Depth below ground, m", (10, 0)


def report_page(a: CPTAnalysis) -> Figure:
    fig = Figure(figsize=(8.27, 11.69), dpi=150)
    gs = fig.add_gridspec(28, 14, left=.035, right=.975, top=.955, bottom=.035, hspace=.78, wspace=.95)
    md = a.metadata
    fig.text(.04,.976,"Client     :",fontsize=8.5,weight="bold",va="top"); fig.text(.125,.976,str(md.get("client") or ""),fontsize=8.5,weight="bold",va="top")
    fig.text(.04,.957,"Project   :",fontsize=8.5,weight="bold",va="top"); fig.text(.125,.957,str(md.get("project_name") or md.get("project_id") or ""),fontsize=8.5,weight="bold",va="top")
    fig.text(.965,.976,"SGP   CTSG   CTS GULF   TERRA FIRMA",ha="right",va="top",fontsize=9,weight="bold")
    fig.lines.extend([
        matplotlib.lines.Line2D([.03,.98],[.985,.985],transform=fig.transFigure,color="black",lw=.8),
        matplotlib.lines.Line2D([.03,.98],[.944,.944],transform=fig.transFigure,color="black",lw=.8),
        matplotlib.lines.Line2D([.03,.03],[.985,.04],transform=fig.transFigure,color="black",lw=.8),
        matplotlib.lines.Line2D([.98,.98],[.985,.04],transform=fig.transFigure,color="black",lw=.8),
    ])
    vertical, ylab, ylim = _level_axis(a)
    ax_qc=fig.add_subplot(gs[2:17,0:4]); ax_fs=fig.add_subplot(gs[2:17,5:9]); ax_ic=fig.add_subplot(gs[2:17,10:14])
    qmax=max(50.0, math.ceil((float(np.nanmax(_finite(a.qc))) if len(_finite(a.qc)) else 50)/10)*10)
    ax_qc.plot(a.qc,vertical,color="black",lw=.85); ax_qc.set_xlim(0,qmax); ax_qc.set_title("Cone resistance, qc, MPa",fontsize=7.2); ax_qc.xaxis.tick_top(); ax_qc.set_ylabel(ylab,fontsize=6.5)
    fsmax=max(.5, math.ceil((float(np.nanmax(_finite(a.fs))) if len(_finite(a.fs)) else .5)*10)/10)
    ax_fs.plot(a.fs,vertical,color="#7b2cbf",lw=.8); ax_fs.set_xlim(0,fsmax); ax_fs.set_title("Sleeve Friction, fs, MPa",fontsize=7.2); ax_fs.xaxis.tick_top()
    ax_u=ax_fs.twiny(); ax_u.plot(a.u2,vertical,color="#21a366",ls="--",lw=.75); umax=max(.05,float(np.nanpercentile(np.abs(_finite(a.u2)),99))*1.15 if len(_finite(a.u2)) else .05); ax_u.set_xlim(umax,0); ax_u.xaxis.set_ticks_position("bottom"); ax_u.xaxis.set_label_position("bottom"); ax_u.set_xlabel("Pore Pressure, u2, MPa",fontsize=5.8,labelpad=6); ax_u.tick_params(labelsize=5)
    for c,(lo,hi) in enumerate(zip(IC_BOUNDS[:-1],IC_BOUNDS[1:])): ax_ic.axvspan(lo,hi,color=IC_COLORS[c],alpha=.95,lw=0)
    ax_ic.plot(a.ic,vertical,color="black",lw=.85); ax_ic.set_xlim(0,5); ax_ic.set_title("Soil Behaviour Type Index, Ic",fontsize=7.2); ax_ic.xaxis.tick_top(); ax_ic.set_xticks([0,1.31,2.05,2.60,2.95,3.60,5]); ax_ic.set_xticklabels(["0","1.31","2.05","2.60","2.95","3.60","5.00"],fontsize=5.3)
    for ax in (ax_qc,ax_fs,ax_ic):
        ax.set_ylim(*ylim); ax.grid(True,which="major",lw=.3,color="#dddddd"); ax.tick_params(labelsize=5.4,length=2.5); [sp.set_linewidth(.75) for sp in ax.spines.values()]
    fig.text(.16,.375,"— Cone resistance",fontsize=5.2,ha="center"); fig.text(.47,.375,"— Sleeve friction   -- Pore Pressure",fontsize=5.2,ha="center"); fig.text(.84,.375,"— Soil behavior type index",fontsize=5.2,ha="center")
    ax_leg=fig.add_subplot(gs[18:23,0:7]); ax_leg.axis("off")
    for i,(name,color) in enumerate(zip(IC_NAMES,IC_COLORS)):
        r,c=divmod(i,2); x=.02+c*.52; y=.84-r*.25; ax_leg.add_patch(matplotlib.patches.Rectangle((x,y-.055),.035,.11,transform=ax_leg.transAxes,color=color)); ax_leg.text(x+.045,y,name,fontsize=5.5,va="center",transform=ax_leg.transAxes)
    ax_meta=fig.add_subplot(gs[23:28,0:8]); ax_meta.axis("off")
    e,n=md.get("easting"),md.get("northing"); ground=md.get("ground_elevation")
    rows=[
        ["Main Contractor:",str(md.get("main_contractor") or "")],["Test Location:",a.reference],
        ["Ground Elevation:",_fmt(ground,2)],["Coordinates:",f"Easting {_fmt(e,3)}      Northing {_fmt(n,3)}"],
        ["Cone ID:",str(md.get("cone_id") or "")],["Test Date:",_date_display(md.get("file_date"))],
    ]
    tbl=ax_meta.table(cellText=rows,colWidths=[.34,.66],loc="center",cellLoc="left"); tbl.auto_set_font_size(False); tbl.set_fontsize(5.9); tbl.scale(1,1.20)
    for (r,c),cell in tbl.get_celld().items():
        cell.set_edgecolor("#999999"); cell.set_linewidth(.45)
        if c==0: cell.set_facecolor("#dddddd"); cell.set_text_props(weight="bold")
    ax_sbt=fig.add_subplot(gs[18:28,8:14]); draw_sbtn(ax_sbt,a)
    return fig


def analysis_page(a: CPTAnalysis) -> Figure:
    r=analysis_record(a); fig=Figure(figsize=(8.27,11.69),dpi=150); ax=fig.add_subplot(111); ax.axis("off")
    fig.text(.07,.95,"CPT ANALYSIS SUMMARY",fontsize=16,weight="bold"); fig.text(.07,.918,a.reference,fontsize=11,weight="bold")
    rows=[
        ["Verification status",r["status"]],["Silt start - reported",str(r["start"]) if isinstance(r["start"],str) else _fmt(r["start"],2," m")],
        ["Silt start RL - reported",_fmt(r["start_rl"],2," m")],["Silt end - reported",_fmt(r["end"],2," m")],["Silt end RL - reported",_fmt(r["end_rl"],2," m")],
        ["Silt thickness - reported",_fmt(r["thickness"],2," m")],["Depth to selected silt, not sand thickness",_fmt(r["sand"],2," m")],
        ["Raw interpolated silt start",_fmt(r["raw_start"],3," m")],["Raw analysis end",_fmt(r["raw_end"],3," m")],["Raw interval thickness",_fmt(r["raw_thickness"],3," m")],
        ["Corrected sounding depth",_fmt(r["test_depth_raw"],3," m")],["Maximum valid Ic",_fmt(r["max_ic"],3)],["Ic at silt start",_fmt(r["ic_start"],3)],
        ["Soil behaviour at silt start",r["behavior"]],["Qtn / Fr at start",f"{_fmt(r['qtn_start'],3)} / {_fmt(r['fr_start'],3,'%')}"],
        ["qc / fs / u2 at start",f"{_fmt(r['qc_start'],4)} / {_fmt(r['fs_start'],4)} / {_fmt(r['u2_start'],4)} MPa"],
        ["Detected silt intervals",str(r["interval_count"])],["Selected interval",r["selected_interval"]],["Pass 1",r["pass1"]],["Pass 2",r["pass2"]],
        ["Terminal sensor dropout",_fmt(r["dropout_depth"],3," m") if r["dropout"] else "None detected"],
    ]
    tbl=ax.table(cellText=rows,colWidths=[.38,.56],cellLoc="left",bbox=[.08,.38,.84,.47]); tbl.auto_set_font_size(False); tbl.set_fontsize(7.2)
    for (rr,cc),cell in tbl.get_celld().items():
        cell.set_edgecolor("#b5b5b5"); cell.set_linewidth(.55)
        if cc==0: cell.set_facecolor("#eeeeee"); cell.set_text_props(weight="bold")
    ax.text(.08,.33,"Verification note",transform=ax.transAxes,fontsize=9.5,weight="bold"); ax.text(.08,.295,r["note"],transform=ax.transAxes,fontsize=7.5,wrap=True,va="top")
    ax.text(.08,.23,"Calculation basis",transform=ax.transAxes,fontsize=9.5,weight="bold")
    ax.text(.08,.195,"Raw GEF/GFF corrected depth, qc, fs and u2 are used for qt, Fr, Qtn and Robertson-style Ic. The Ic=2.60 crossing is interpolated. Short terminal exact-zero sleeve-friction dropout is excluded from Ic. Two independent passes must agree; disagreements receive sensitivity rechecks. Reported start/end are rounded to 0.10 m and reported thickness is end minus start.",transform=ax.transAxes,fontsize=7.3,wrap=True,va="top")
    return fig


def generate_pdf(a: CPTAnalysis, output_path: str|Path) -> Path:
    p=Path(output_path); p.parent.mkdir(parents=True,exist_ok=True)
    with PdfPages(p) as pdf:
        f=report_page(a); pdf.savefig(f); f.clear()
        f=analysis_page(a); pdf.savefig(f); f.clear()
    return p


FULL_HEADERS = [
    "SI.No","CPT REFERENCE","Area","Source File","Test Date","Client","Project","Main Contractor","Location","Cone ID","Standard","Records",
    "Ground Elevation (m)","Easting","Northing","Cone Area Ratio","Soil Unit Weight (kN/m3)","Groundwater Depth BGL (m)",
    "Corrected Test Depth (m)","Test End RL (m)","Depth to selected silt (m), NOT continuous sand","Silt Start Reported (m)","Silt Start RL Reported (m)",
    "Silt End Reported (m)","Silt End RL Reported (m)","Silt Thickness Reported (m)","Raw Silt Start (m)","Raw Silt Start RL (m)",
    "Raw Silt End (m)","Raw Silt End RL (m)","Raw Silt Thickness (m)","Maximum Valid Ic","Mean Valid Ic","Valid Ic Points","Ic at Silt Start",
    "Soil Behaviour at Silt Start","Qtn at Silt Start","Fr at Silt Start (%)","qc at Silt Start (MPa)","fs at Silt Start (MPa)","u2 at Silt Start (MPa)",
    "Detected Silt Intervals","Selected Interval","Terminal Sensor Dropout","Dropout Depth (m)","Pass 1 Result (Start/Thickness)","Pass 2 Result (Start/Thickness)","Verification Status","Verification Note"
]


def _full_row(i,a,r):
    return [i,r["reference"],r["area"],r["source"],r["date"],r["client"],r["project"],r["contractor"],r["location"],r["cone_id"],r["standard"],r["records"],
        r["ground"],r["easting"],r["northing"],r["area_ratio"],r["gamma"],r["water_table"],r["test_depth_raw"],r["test_end_rl"],r["sand"],r["start"],r["start_rl"],r["end"],r["end_rl"],r["thickness"],
        r["raw_start"],r["raw_start_rl"],r["raw_end"],r["raw_end_rl"],r["raw_thickness"],r["max_ic"],r["mean_ic"],r["valid_ic_points"],r["ic_start"],r["behavior"],r["qtn_start"],r["fr_start"],r["qc_start"],r["fs_start"],r["u2_start"],
        r["interval_count"],r["selected_interval"],"YES" if r["dropout"] else "NO",r["dropout_depth"],r["pass1"],r["pass2"],r["status"],r["note"]]


def export_excel(analyses: Iterable[CPTAnalysis], output_path: str|Path, errors: Sequence[tuple[str,str]]|None=None) -> Path:
    analyses=sorted(list(analyses),key=lambda a:natural_ref_key(a.reference)); recs=[analysis_record(a) for a in analyses]; errors=list(errors or [])
    p=Path(output_path); p.parent.mkdir(parents=True,exist_ok=True); wb=xlsxwriter.Workbook(str(p))
    hdr=wb.add_format({"bold":True,"font_color":"#FFC000","bg_color":"#000000","border":1,"align":"center","valign":"vcenter","text_wrap":True})
    text=wb.add_format({"border":1}); center=wb.add_format({"border":1,"align":"center"}); num=wb.add_format({"border":1,"align":"center","num_format":"0.00"}); num3=wb.add_format({"border":1,"align":"center","num_format":"0.000"})
    label=wb.add_format({"bold":True,"bg_color":"#E7E6E6","border":1}); val=wb.add_format({"border":1,"align":"center","num_format":"0.00"})
    ws=wb.add_worksheet("CPT Analysis"); simple=["SI.No","CPT REFERENCE","Silt start depth after (m)","silt depth (m)"]
    for c,h in enumerate(simple): ws.write(0,c,h,hdr)
    ws.freeze_panes(1,0); ws.autofilter(0,0,max(1,len(analyses)),3); ws.set_column(0,0,9); ws.set_column(1,1,28); ws.set_column(2,3,25)
    for i,(a,r) in enumerate(zip(analyses,recs),1):
        ws.write_number(i,0,i,center); ws.write(i,1,a.reference,text)
        if a.status=="NO SILT": ws.write(i,2,"NO SILT",center); ws.write_number(i,3,0,num)
        elif a.final_interval: ws.write_number(i,2,a.final_interval.start,num); ws.write_number(i,3,a.final_interval.thickness,num)
        else: ws.write(i,2,"REVIEW",center); ws.write_blank(i,3,None,num)
    wd=wb.add_worksheet("Full Analysis")
    for c,h in enumerate(FULL_HEADERS): wd.write(0,c,h,hdr)
    wd.freeze_panes(1,2); wd.autofilter(0,0,max(1,len(analyses)),len(FULL_HEADERS)-1); wd.set_row(0,38); wd.set_column(0,0,8); wd.set_column(1,4,22); wd.set_column(5,10,22); wd.set_column(11,47,18); wd.set_column(48,48,60)
    for i,(a,r) in enumerate(zip(analyses,recs),1):
        row=_full_row(i,a,r)
        for c,v in enumerate(row):
            if isinstance(v,(int,float,np.integer,np.floating)) and not isinstance(v,bool) and np.isfinite(float(v)): wd.write_number(i,c,float(v),num3 if c in {26,27,28,29,30,31,32,34,36,37,38,39,40,44} else num)
            elif v is None: wd.write_blank(i,c,None,center)
            else: wd.write(i,c,str(v),text if c in {1,2,3,4,5,6,7,8,9,10,35,42,43,45,46,47,48} else center)
    if len(analyses):
        wd.conditional_format(1,47,len(analyses),47,{"type":"text","criteria":"containing","value":"REVIEW","format":wb.add_format({"bg_color":"#FFC7CE","font_color":"#9C0006"})})
        wd.conditional_format(1,25,len(analyses),25,{"type":"data_bar"})
    wi=wb.add_worksheet("Detected Intervals"); ih=["CPT REFERENCE","Interval No.","Raw Start (m)","Raw End (m)","Raw Thickness (m)","Selected"]
    for c,h in enumerate(ih): wi.write(0,c,h,hdr)
    rr=1
    for a in analyses:
        for j,(s,e) in enumerate(a.all_intervals,1):
            wi.write(rr,0,a.reference,text); wi.write_number(rr,1,j,center); wi.write_number(rr,2,s,num3); wi.write_number(rr,3,e,num3); wi.write_number(rr,4,max(0,e-s),num3); wi.write(rr,5,"YES" if a.final_interval and j==len(a.all_intervals) else "NO",center); rr+=1
    wi.set_column(0,0,28); wi.set_column(1,5,18); wi.freeze_panes(1,0)
    sm=wb.add_worksheet("Summary")
    verified=[r for r in recs if r["status"]=="VERIFIED" and r["thickness"] is not None]; no_silt=[r for r in recs if r["status"]=="NO SILT"]; reviews=[r for r in recs if r["status"]=="REVIEW"]
    mx=max([r["thickness"] for r in verified],default=None); mxrefs=[r["reference"] for r in verified if mx is not None and abs(r["thickness"]-mx)<1e-9]
    mn=min([r["thickness"] for r in verified],default=None); avg=float(np.mean([r["thickness"] for r in verified])) if verified else None
    sands=[r["sand"] for r in recs if isinstance(r["sand"],(int,float))]; starts=[r for r in verified if isinstance(r["start_num"],(int,float))]
    shallow=min([r["start_num"] for r in starts],default=None); deep=max([r["start_num"] for r in starts],default=None)
    metrics=[("Total CPTs",len(recs)),("Verified silt CPTs",len(verified)),("NO SILT CPTs",len(no_silt)),("REVIEW CPTs",len(reviews)),("Processing errors",len(errors)),
        ("Maximum silt thickness (m)",mx),("CPT(s) at maximum",", ".join(mxrefs)),("Minimum silt thickness (m)",mn),("Average silt thickness (m)",avg),
        ("Shallowest silt start (m)",shallow),("CPT(s) shallowest",", ".join(r["reference"] for r in starts if shallow is not None and abs(r["start_num"]-shallow)<1e-9)),
        ("Deepest silt start (m)",deep),("CPT(s) deepest",", ".join(r["reference"] for r in starts if deep is not None and abs(r["start_num"]-deep)<1e-9)),
        ("Maximum depth to selected silt (m)",max(sands) if sands else None),("Mean depth to selected silt (m)",float(np.mean(sands)) if sands else None)]
    for c,h in enumerate(["Project KPI","Value"]): sm.write(0,c,h,hdr)
    for i,(k,v) in enumerate(metrics,1): sm.write(i,0,k,label); sm.write_number(i,1,float(v),val) if isinstance(v,(int,float)) and v is not None else sm.write(i,1,"" if v is None else str(v),center)
    sm.set_column(0,0,32); sm.set_column(1,1,54)
    top=sorted(verified,key=lambda r:r["thickness"],reverse=True)[:25]; base=18; sm.write(base,0,"Top silt thickness CPTs",hdr); sm.write(base,1,"Thickness (m)",hdr)
    for j,r in enumerate(top,base+1): sm.write(j,0,r["reference"],text); sm.write_number(j,1,r["thickness"],num)
    ch=wb.add_worksheet("Charts"); ch.write(0,0,"PRINTABLE PROJECT CHARTS",hdr); ch.set_column(0,0,2); ch.set_column(1,20,12)
    if analyses:
        n=len(analyses); cats=["Full Analysis",1,1,n,1]
        chart1=wb.add_chart({"type":"column"}); chart1.add_series({"name":"Depth to silt","categories":cats,"values":["Full Analysis",1,20,n,20]}); chart1.add_series({"name":"Silt thickness","categories":cats,"values":["Full Analysis",1,25,n,25]}); chart1.set_title({"name":"Depth to Silt and Selected Silt Thickness by CPT"}); chart1.set_y_axis({"name":"Thickness (m)"}); chart1.set_x_axis({"name":"CPT Reference"}); chart1.set_size({"width":850,"height":430}); ch.insert_chart("B3",chart1)
        chart2=wb.add_chart({"type":"column","subtype":"stacked"}); chart2.add_series({"name":"Depth to silt","categories":cats,"values":["Full Analysis",1,20,n,20]}); chart2.add_series({"name":"Silt layer","categories":cats,"values":["Full Analysis",1,25,n,25]}); chart2.set_title({"name":"Depth to Silt and Selected Silt Screen (not stratigraphy)"}); chart2.set_y_axis({"name":"Thickness (m)"}); chart2.set_size({"width":850,"height":430}); ch.insert_chart("B25",chart2)
        chart3=wb.add_chart({"type":"line"}); chart3.add_series({"name":"Silt start","categories":cats,"values":["Full Analysis",1,21,n,21]}); chart3.add_series({"name":"Silt end","categories":cats,"values":["Full Analysis",1,23,n,23]}); chart3.add_series({"name":"Test depth","categories":cats,"values":["Full Analysis",1,18,n,18]}); chart3.set_title({"name":"Silt Start / End / Test Depth"}); chart3.set_y_axis({"name":"Depth BGL (m)","reverse":True}); chart3.set_size({"width":850,"height":430}); ch.insert_chart("B47",chart3)
        if top:
            chart4=wb.add_chart({"type":"bar"}); chart4.add_series({"name":"Silt thickness","categories":["Summary",base+1,0,base+len(top),0],"values":["Summary",base+1,1,base+len(top),1]}); chart4.set_title({"name":"Highest Silt Thickness - Top 25"}); chart4.set_x_axis({"name":"Thickness (m)"}); chart4.set_size({"width":850,"height":430}); ch.insert_chart("B69",chart4)
        coords=[(idx,r) for idx,r in enumerate(recs,1) if isinstance(r["easting"],(int,float)) and isinstance(r["northing"],(int,float))]
        if coords:
            chart5=wb.add_chart({"type":"scatter","subtype":"straight_with_markers"}); chart5.add_series({"name":"CPT locations","categories":["Full Analysis",1,13,n,13],"values":["Full Analysis",1,14,n,14]}); chart5.set_title({"name":"CPT Coordinate Map"}); chart5.set_x_axis({"name":"Easting"}); chart5.set_y_axis({"name":"Northing"}); chart5.set_size({"width":850,"height":430}); ch.insert_chart("B91",chart5)
    er=wb.add_worksheet("Processing Errors"); er.write(0,0,"Source File",hdr); er.write(0,1,"Error",hdr); er.set_column(0,0,35); er.set_column(1,1,90)
    for i,(src,msg) in enumerate(errors,1): er.write(i,0,src,text); er.write(i,1,msg,text)
    wb.close(); return p

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Iterable

import numpy as np
import xlsxwriter
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_pdf import PdfPages

from cpt_core import CPTAnalysis, natural_ref_key, summarize_analyses

ZONE_BOUNDS = [0.0, 1.31, 2.05, 2.60, 2.95, 3.60, 5.00]
ZONE_NAMES = [
    "Gravelly sand to dense sand", "Clean to silty sand", "Silty sand to sandy silt",
    "Clayey silt to silty clay", "Silty clay to clay", "Organic soil - clay",
]
ZONE_COLORS = ["#ffd65a", "#f7b267", "#a8dadc", "#75c9c8", "#4f86c6", "#789262"]


def _finite_xy(x, y):
    x, y = np.asarray(x), np.asarray(y)
    m = np.isfinite(x) & np.isfinite(y)
    return x[m], y[m]


def _display_date(raw_date: str) -> str:
    try:
        yy, mm, dd = [int(x.strip()) for x in str(raw_date).split(",")[:3]]
        return dt.date(yy, mm, dd).strftime("%d-%b-%Y")
    except Exception:
        return str(raw_date or "")


def _report_page(a: CPTAnalysis) -> Figure:
    fig = Figure(figsize=(8.27, 11.69), dpi=150)
    gs = fig.add_gridspec(24, 14, left=.035, right=.975, top=.965, bottom=.035, hspace=.7, wspace=.9)
    md = a.metadata
    client = str(md.get("client") or "")
    project = str(md.get("project_name") or md.get("project_id") or "")
    fig.text(.04,.977,"Client    :",fontsize=8.5,weight="bold",va="top")
    fig.text(.125,.977,client,fontsize=8.5,weight="bold",va="top")
    fig.text(.04,.958,"Project  :",fontsize=8.5,weight="bold",va="top")
    fig.text(.125,.958,project,fontsize=8.5,weight="bold",va="top")
    fig.text(.965,.974,"CPT REPORT",fontsize=9.5,weight="bold",ha="right",va="top")
    fig.lines.extend([Line2D([.03,.98],[.985,.985],transform=fig.transFigure,color="black",lw=.8), Line2D([.03,.98],[.944,.944],transform=fig.transFigure,color="black",lw=.8)])

    ax_qc = fig.add_subplot(gs[2:16,0:4])
    ax_fs = fig.add_subplot(gs[2:16,5:9])
    ax_ic = fig.add_subplot(gs[2:16,10:14])
    ground = md.get("ground_elevation")
    vertical = float(ground) - a.depth if isinstance(ground,(int,float)) else a.depth
    ylab = "Level, m" if isinstance(ground,(int,float)) else "Depth below ground, m"

    ax_qc.plot(a.qc,vertical,color="black",lw=.9)
    ax_qc.set_title("Cone resistance, qc, MPa",fontsize=7.5); ax_qc.xaxis.set_label_position("top"); ax_qc.xaxis.tick_top(); ax_qc.set_ylabel(ylab,fontsize=7); ax_qc.set_xlim(left=0)
    ax_fs.plot(a.fs,vertical,color="#7b2cbf",lw=.85)
    ax_u2 = ax_fs.twiny(); ax_u2.plot(a.u2,vertical,color="#2a9d8f",lw=.8,ls="--")
    ax_fs.set_title("Sleeve Friction, fs, MPa",fontsize=7.5); ax_fs.xaxis.set_label_position("top"); ax_fs.xaxis.tick_top(); ax_fs.set_xlim(left=0)
    finite_u = a.u2[np.isfinite(a.u2)]
    if len(finite_u):
        umax = max(.05,float(np.nanpercentile(np.abs(finite_u),99))*1.15)
        ax_u2.set_xlim(umax,0.0); ax_u2.xaxis.set_ticks_position("bottom"); ax_u2.xaxis.set_label_position("bottom")
        ax_u2.spines["bottom"].set_position(("axes",0.0)); ax_u2.spines["bottom"].set_visible(True); ax_u2.spines["top"].set_visible(False)
        ax_u2.tick_params(axis="x",labelsize=5.3,pad=1); ax_u2.set_xlabel("Pore Pressure, u2, MPa",fontsize=6.2,labelpad=7)

    for i,(lo,hi) in enumerate(zip(ZONE_BOUNDS[:-1],ZONE_BOUNDS[1:])):
        ax_ic.axvspan(lo,hi,color=ZONE_COLORS[i],alpha=.92,lw=0)
    ax_ic.plot(a.ic,vertical,color="black",lw=.9)
    for bound in ZONE_BOUNDS[1:]: ax_ic.axvline(bound,color="#777",lw=.35)
    ax_ic.set_xlim(0,5); ax_ic.set_title("Soil Behaviour Type Index, Ic",fontsize=7.5); ax_ic.xaxis.set_label_position("top"); ax_ic.xaxis.tick_top()
    ax_ic.set_xticks([0,1.31,2.05,2.60,2.95,3.60,5.00]); ax_ic.set_xticklabels(["0","1.31","2.05","2.60","2.95","3.60","5.00"],fontsize=5.4)

    for ax in (ax_qc,ax_fs,ax_ic):
        ax.set_ylim(-10,10) if isinstance(ground,(int,float)) else ax.set_ylim(10,0)
        ax.grid(True,which="major",lw=.3,color="#ddd"); ax.tick_params(labelsize=5.8,width=.6,length=2.5)
        for spine in ax.spines.values(): spine.set_linewidth(.75)

    ax_leg = fig.add_subplot(gs[16:20,0:7]); ax_leg.axis("off")
    for idx,(name,color) in enumerate(zip(ZONE_NAMES,ZONE_COLORS)):
        r,c=divmod(idx,2); x=.02+c*.51; y=.80-r*.24
        ax_leg.add_patch(Rectangle((x,y-.06),.035,.12,transform=ax_leg.transAxes,color=color)); ax_leg.text(x+.045,y,name,fontsize=5.8,va="center",transform=ax_leg.transAxes)

    ax_sbt = fig.add_subplot(gs[16:24,8:14])
    fx,qy = _finite_xy(a.fr,a.qtn); mask=np.isfinite(a.fr)&np.isfinite(a.qtn); icf=a.ic[mask]; bins=np.digitize(icf,ZONE_BOUNDS[1:-1],right=False)
    for i in range(6):
        m=bins==i
        if np.any(m): ax_sbt.scatter(fx[m],qy[m],s=4,alpha=.72,color=ZONE_COLORS[i])
    ax_sbt.set_xscale("log"); ax_sbt.set_yscale("log"); ax_sbt.set_xlim(.1,10); ax_sbt.set_ylim(1,1000)
    ax_sbt.set_xlabel("Normalized Friction Ratio, Fr, %",fontsize=5.5); ax_sbt.set_ylabel("Normalized Cone Resistance Qtn",fontsize=5.5)
    ax_sbt.grid(True,which="both",lw=.25,color="#ddd"); ax_sbt.tick_params(labelsize=5)

    ax_meta=fig.add_subplot(gs[20:24,0:8]); ax_meta.axis("off")
    e,n=md.get("easting"),md.get("northing")
    rows=[
        ("Main Contractor:",str(md.get("main_contractor") or "")),
        ("Test Location:",a.reference),
        ("Ground Elevation:",f"{float(ground):.2f}" if isinstance(ground,(int,float)) else ""),
        ("Coordinates:",f"Easting {float(e):.3f}    Northing {float(n):.3f}" if isinstance(e,(int,float)) and isinstance(n,(int,float)) else ""),
        ("Cone ID:",str(md.get("cone_id") or "")),
        ("Test Date:",_display_date(str(md.get("file_date") or ""))),
    ]
    table=ax_meta.table(cellText=rows,colWidths=[.35,.65],loc="center",cellLoc="left"); table.auto_set_font_size(False); table.set_fontsize(6.1); table.scale(1,1.25)
    for (r,c),cell in table.get_celld().items():
        cell.set_edgecolor("#999"); cell.set_linewidth(.45)
        if c==0: cell.set_facecolor("#dedede"); cell.set_text_props(weight="bold")
    return fig


def _analysis_page(a: CPTAnalysis) -> Figure:
    fig=Figure(figsize=(8.27,11.69),dpi=150); ax=fig.add_subplot(111); ax.axis("off")
    fig.text(.07,.94,"CPT ANALYSIS SUMMARY",fontsize=16,weight="bold"); fig.text(.07,.905,a.reference,fontsize=11,weight="bold")
    if a.status=="NO SILT":
        rs,re,rt="NO SILT","-","0.00 m"; rrs=rre=rrt="-"
    elif a.final_interval is None:
        rs="REVIEW"; re=rt=rrs=rre=rrt="-"
    else:
        z=a.final_interval; rs=f"{z.start:.2f} m"; re=f"{z.end:.2f} m"; rt=f"{z.thickness:.2f} m"; rrs=f"{z.start_raw:.3f} m"; rre=f"{z.end_raw:.3f} m"; rrt=f"{z.thickness_raw:.3f} m"
    sand=a.sand_layer_thickness
    rows=[
        ["Status",a.status],["Silt start - reported",rs],["Silt end - reported",re],["Silt thickness - reported",rt],
        ["Sand layer thickness",f"{sand:.2f} m" if sand is not None else "REVIEW"],["Raw interpolated silt start",rrs],
        ["Raw analysis end",rre],["Raw interval thickness",rrt],["Corrected sounding depth",f"{a.test_depth_raw:.3f} m"],
        ["Terminal sensor dropout",f"{a.sensor_dropout_depth:.3f} m" if a.sensor_dropout_depth is not None else "None detected"],
        ["Verification","Two-pass verified" if a.status=="VERIFIED" else a.status],
    ]
    tbl=ax.table(cellText=rows,colWidths=[.36,.58],cellLoc="left",bbox=[.08,.42,.84,.42]); tbl.auto_set_font_size(False); tbl.set_fontsize(8)
    for (r,c),cell in tbl.get_celld().items():
        cell.set_edgecolor("#b5b5b5"); cell.set_linewidth(.6)
        if c==0: cell.set_facecolor("#eee"); cell.set_text_props(weight="bold")
    ax.text(.08,.34,"Calculation basis",transform=ax.transAxes,fontsize=10,weight="bold")
    ax.text(.08,.30,"Raw GEF/GFF qc, fs and u2 are used to calculate qt, Fr, Qtn and Robertson-style Ic. Terminal exact-zero sleeve-friction dropout is excluded from Ic. Threshold crossings are linearly interpolated. The project output reports start/end to 0.10 m and calculates reported thickness as reported end minus reported start.",transform=ax.transAxes,fontsize=8,wrap=True,va="top")
    return fig


def generate_pdf(analysis: CPTAnalysis, output_path: str|Path) -> Path:
    output_path=Path(output_path); output_path.parent.mkdir(parents=True,exist_ok=True)
    with PdfPages(output_path) as pdf:
        p1=_report_page(analysis); pdf.savefig(p1); p1.clear()
        p2=_analysis_page(analysis); pdf.savefig(p2); p2.clear()
    return output_path


def export_excel(analyses: Iterable[CPTAnalysis], output_path: str|Path) -> Path:
    output_path=Path(output_path); output_path.parent.mkdir(parents=True,exist_ok=True)
    analyses=sorted(list(analyses),key=lambda a:natural_ref_key(a.reference)); summary=summarize_analyses(analyses)
    wb=xlsxwriter.Workbook(str(output_path))
    hdr=wb.add_format({"bold":True,"font_color":"#FFC000","bg_color":"#000000","border":1,"align":"center","valign":"vcenter","text_wrap":True})
    num=wb.add_format({"num_format":"0.00","align":"center","border":1}); num3=wb.add_format({"num_format":"0.000","align":"center","border":1})
    integer=wb.add_format({"align":"center","border":1}); text=wb.add_format({"border":1}); center=wb.add_format({"align":"center","border":1})
    klabel=wb.add_format({"bold":True,"bg_color":"#E7E6E6","border":1}); kval=wb.add_format({"bold":True,"align":"center","border":1,"num_format":"0.00"})

    ws=wb.add_worksheet("CPT Analysis"); headers=["SI.No","CPT REFERENCE","Silt start depth after (m)","silt depth (m)"]
    for c,h in enumerate(headers): ws.write(0,c,h,hdr)
    ws.set_row(0,32); ws.freeze_panes(1,0); ws.autofilter(0,0,max(1,len(analyses)),3); ws.set_column(0,0,9); ws.set_column(1,1,28); ws.set_column(2,2,29); ws.set_column(3,3,17)
    for i,a in enumerate(analyses,start=1):
        ws.write_number(i,0,i,integer); ws.write(i,1,a.reference,text)
        if a.status=="NO SILT": ws.write(i,2,"NO SILT",center); ws.write_number(i,3,0.0,num)
        elif a.final_interval is not None: ws.write_number(i,2,a.final_interval.start,num); ws.write_number(i,3,a.final_interval.thickness,num)
        else: ws.write(i,2,"REVIEW",center); ws.write_blank(i,3,None,num)

    wd=wb.add_worksheet("Full Analysis")
    dh=["SI.No","CPT REFERENCE","Sand layer thickness (m)","Silt start reported (m)","Silt end reported (m)","Silt thickness reported (m)","Raw silt start (m)","Raw silt end (m)","Raw silt thickness (m)","Corrected test depth (m)","Status"]
    for c,h in enumerate(dh): wd.write(0,c,h,hdr)
    wd.freeze_panes(1,2); wd.autofilter(0,0,max(1,len(analyses)),len(dh)-1); wd.set_column(0,0,8); wd.set_column(1,1,27); wd.set_column(2,9,20); wd.set_column(10,10,14)
    for i,a in enumerate(analyses,start=1):
        wd.write_number(i,0,i,integer); wd.write(i,1,a.reference,text)
        sand=a.sand_layer_thickness; wd.write(i,2,"REVIEW",center) if sand is None else wd.write_number(i,2,sand,num)
        if a.status=="NO SILT":
            wd.write(i,3,"NO SILT",center); wd.write_blank(i,4,None,num); wd.write_number(i,5,0.0,num)
            for c in [6,7,8]: wd.write_blank(i,c,None,num3)
        elif a.final_interval is not None:
            z=a.final_interval; wd.write_number(i,3,z.start,num); wd.write_number(i,4,z.end,num); wd.write_number(i,5,z.thickness,num); wd.write_number(i,6,z.start_raw,num3); wd.write_number(i,7,z.end_raw,num3); wd.write_number(i,8,z.thickness_raw,num3)
        else:
            wd.write(i,3,"REVIEW",center)
            for c in range(4,9): wd.write_blank(i,c,None,num3 if c>=6 else num)
        wd.write_number(i,9,a.test_depth_raw,num3); wd.write(i,10,a.status,center)

    ss=wb.add_worksheet("Summary"); ss.set_column("A:A",28); ss.set_column("B:B",35); ss.write("A1","Full CPT Analysis Summary",hdr)
    for row,label,key in [(3,"Total CPTs","total"),(4,"Verified silt","verified"),(5,"No silt","no_silt"),(6,"Review required","review")]: ss.write(f"A{row}",label,klabel); ss.write_number(f"B{row}",summary[key],kval)
    ss.write("A8","Maximum silt thickness (m)",klabel)
    if summary["max_silt_thickness"] is not None: ss.write_number("B8",summary["max_silt_thickness"],kval)
    ss.write("A9","CPT(s) at maximum thickness",klabel); ss.write("B9",", ".join(summary["max_silt_refs"]),text)
    ss.write("A10","Average verified silt thickness (m)",klabel)
    if summary["avg_silt_thickness"] is not None: ss.write_number("B10",summary["avg_silt_thickness"],kval)
    if analyses:
        chart=wb.add_chart({"type":"line"}); n=len(analyses)+1
        chart.add_series({"name":"Silt thickness","categories":f"='Full Analysis'!$B$2:$B${n}","values":f"='Full Analysis'!$F$2:$F${n}"})
        chart.add_series({"name":"Sand layer thickness","categories":f"='Full Analysis'!$B$2:$B${n}","values":f"='Full Analysis'!$C$2:$C${n}"})
        chart.set_title({"name":"Full Analysis - Layer Thickness"}); chart.set_y_axis({"name":"Thickness (m)"}); chart.set_x_axis({"name":"CPT Reference","label_position":"low"}); chart.set_legend({"position":"bottom"}); chart.set_size({"width":980,"height":420}); ss.insert_chart("D2",chart)
    wb.close(); return output_path

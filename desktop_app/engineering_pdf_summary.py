"""One complete engineering appendix for raw GEF and original PDF inputs.

Unobserved values are explicit N/A, not empty cells. REVIEW is a recorded
engineering limitation with supporting measured evidence when available.
"""
from __future__ import annotations
from math import isfinite
import textwrap
import numpy as np
from matplotlib.figure import Figure
from matplotlib.table import Table


def _num(v,precision=3,unit=""):
    try:
        f=float(v)
        if not isfinite(f):return "N/A - not observed"
        return f"{f:.{precision}f}"+(f" {unit}" if unit else "")
    except (TypeError,ValueError):
        return "N/A - not observed"


def _cell(v):
    if v is None or str(v).strip()=="":
        return "N/A - not recorded"
    return str(v)


def engineering_analysis_page(a):
    md=getattr(a,"metadata",{}) or {}
    interval=getattr(a,"final_interval",None)
    ground=md.get("ground_elevation")
    status=str(getattr(a,"status","REVIEW"))
    source=str(getattr(getattr(a,"source_path",None),"name","N/A"))
    valid=np.asarray(getattr(a,"ic",[]),float)
    max_ic=float(np.max(valid[np.isfinite(valid)])) if np.isfinite(valid).any() else None
    try:
        from engineering_layers import from_analysis
        layers=from_analysis(a)
        observed=[(x.start_m,x.end_m,x.thickness_m)
                  for x in layers.layers if x.kind!="UNKNOWN"]
        threshold_runs=layers.silt_intervals
        brief=layers.brief_exceedances
        unknown=layers.unknown_m
    except Exception:
        observed=[];threshold_runs=tuple(getattr(a,"all_intervals",[]) or [])
        brief=[];unknown=None

    report_start=_num(interval.start,2,"m") if interval else ("NO QUALIFYING SILT" if status=="NO SILT" else "REVIEW - not confirmed")
    report_end=_num(interval.end,2,"m") if interval else "N/A - no verified boundary"
    thickness=_num(interval.thickness,2,"m") if interval else ("0.00 m measured qualifying thickness" if status=="NO SILT" else "N/A - not verified")
    raw_start=_num(interval.start_raw,3,"m") if interval else "N/A - no selected interval"
    raw_end=_num(interval.end_raw,3,"m") if interval else "N/A - no selected interval"
    raw_thick=_num(interval.thickness_raw,3,"m") if interval else "N/A - no selected interval"
    if interval is None and brief:
        # Even where reporting persistence rejects it, preserve exact evidence.
        raw_start="; ".join(f"{x:.3f}" for x,_ in brief[:3])+" m (brief crossing only)"
        raw_end="; ".join(f"{y:.3f}" for _,y in brief[:3])+" m (not a verified layer)"
        raw_thick="; ".join(f"{y-x:.3f}" for x,y in brief[:3])+" m (below persistence)"

    rows=[
        ("Verification status",status),
        ("CPT reference",_cell(getattr(a,"reference",None))),
        ("Source file",source),
        ("Source quality",_cell(md.get("source_quality") or ("RAW NUMERICAL" if source.lower().endswith((".gef",".gff")) else "VECTOR PDF / GRAPHICAL"))),
        ("Project / client",_cell(md.get("project_name") or md.get("project_id"))+" / "+_cell(md.get("client"))),
        ("Main contractor",_cell(md.get("main_contractor"))),
        ("CPT location / area",_cell(md.get("location"))),
        ("Cone serial / type",_cell(md.get("cone_id"))),
        ("Testing standard",_cell(md.get("standard"))),
        ("Test date",_cell(md.get("test_date")) if md.get("test_date") else "NOT RECORDED; file date is not test date"),
        ("Processing stage",_cell(md.get("cpt_stage") or "PRE (default)")),
        ("Smoothing window",str(md.get("analysis_smoothing_window_samples") or "N/A - PDF source") +" observations"),
        ("Ground elevation",_num(ground,3,"m RL")),
        ("Easting / Northing",_num(md.get("easting"),3)+" / "+_num(md.get("northing"),3)),
        ("Corrected test end BGL",_num(getattr(a,"test_depth_raw",None),3,"m")),
        ("Soil unit weight",_num(md.get("analysis_gamma_soil_kn_m3"),2,"kN/m3")),
        ("Groundwater level",_num(md.get("analysis_water_table_bgl_m"),2,"m BGL")),
        ("Cone area ratio",_num(md.get("area_ratio"),3)),
        ("Pore pressure u2 source",_cell(md.get("pore_pressure_source") or
             ("PDF graphical/source unavailable" if source.lower().endswith(".pdf") else
              "NOT RECORDED — verify whether u2 was measured"))),
        ("Ic criterion","Ic >= 2.60, sustained 0.05 m minimum"),
        ("Silt start (reported)",report_start),
        ("Silt end (reported)",report_end),
        ("Silt thickness (reported)",thickness),
        ("Sand before selected silt",_num(getattr(a,"sand_layer_thickness",None),2,"m") if status!="REVIEW" else "N/A - not verified"),
        ("Raw observed silt start",raw_start),
        ("Raw observed silt end",raw_end),
        ("Raw observed thickness",raw_thick),
        ("Maximum measured valid Ic",_num(max_ic,3)),
        ("Number of qualifying intervals",str(len(threshold_runs))),
        ("Number of brief Ic crossings",str(len(brief))),
        ("Unclassified sensor depth",_num(unknown,3,"m")),
        ("Terminal friction dropout",_num(getattr(a,"sensor_dropout_depth",None),3,"m") if getattr(a,"sensor_dropout_depth",None) is not None else "None recorded"),
        ("First sensitivity window",_num(a.pass1.start,2)+" / "+_num(a.pass1.thickness,2) if a.pass1 else "NO PERSISTENT LAYER"),
        ("Project stage primary window",_num(a.pass2.start,2)+" / "+_num(a.pass2.thickness,2) if a.pass2 else "NO PERSISTENT LAYER"),
        ("File export / recorded date",_cell(md.get("file_date"))),
    ]
    fig=Figure(figsize=(8.27,11.69),dpi=150,facecolor="#ffffff")
    ax=fig.add_axes((.06,.18,.88,.69));ax.axis("off")
    fig.text(.06,.965,"CPT PDF ANALYSIS SUMMARY | ENGINEERING REPORT",fontsize=15,weight="bold",color="#14344b")
    fig.text(.06,.939,_cell(a.reference),fontsize=10.5,weight="bold",color="#426377")
    fig.text(.94,.943,"MEASURED / INFERRED / UNKNOWN",ha="right",fontsize=8,color="#4e6980")
    row_height=1.0/len(rows)
    table=Table(ax,bbox=[0,0,1,1])
    for i,(label,value) in enumerate(rows):
        a0=table.add_cell(i,0,width=.42,height=row_height,text=label,
                          loc="left",facecolor="#e8f0f7",edgecolor="#becdd8")
        b0=table.add_cell(i,1,width=.58,height=row_height,text=str(value),
                          loc="left",facecolor="#ffffff",edgecolor="#d5dfe7")
        a0.get_text().set_weight("bold")
        a0.PAD=.022;b0.PAD=.022
        if i==0:
            b0.set_facecolor("#dff2e8" if status=="VERIFIED" else "#fff0db" if status=="REVIEW" else "#e6f1fc")
        a0.get_text().set_fontsize(7.0);b0.get_text().set_fontsize(7.0)
    ax.add_table(table)
    fig.text(.065,.150,"Verification & interpretation",fontsize=9.4,weight="bold",color="#14344b")
    note=str(getattr(a,"verification_note","") or "No explicit verification note recorded.")
    if status=="NO SILT":
        note += " NO SILT means no persistent qualifying OBSERVED Ic interval; unmeasured depths are not declared clean sand."
    # Explicit line budget avoids the previous overlap between a long
    # sensitivity-verification note and the Engineering basis footer.
    note_lines=textwrap.wrap(note,117,break_long_words=False)
    for index,line in enumerate(note_lines[:4]):
        fig.text(.065,.139-index*.014,line,fontsize=7.0,va="top",color="#334155")
    if len(note_lines)>4:
        fig.text(.065,.083,"Full unabridged verification evidence is in the Excel Source Audit sheet.",
                 fontsize=7.0,color="#8b4513")
    fig.text(.065,.068,"Engineering basis",fontsize=9.1,weight="bold",color="#14344b")
    method=("CPT behavior-based screening, not laboratory USCS. Corrected BGL "
       "depth, qc/fs/u2, qt, Qtn/Fr and Ic. Invalid sensor tails are UNKNOWN; "
       "original workbook outputs are reference checks, not silent substitutions.")
    for index,line in enumerate(textwrap.wrap(method,115)[:3]):
        fig.text(.065,.048-index*.013,line,fontsize=6.8,va="top",color="#475569")
    return fig

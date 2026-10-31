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
    from engineering_reporting_policy import visible_silt_layers, display_silt_summary
    display_status,display_layers=display_silt_summary(a)
    # A short/raw 0.05-0.10m screening interval is evidence, but explicitly
    # NOT a displayed, accepted silt layer. Do not claim its thickness is zero.
    visible_selected=(interval if interval is not None
                      and float(interval.thickness_raw)>0.10+1e-9 else None)
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

    # Keep a defensible *measured* candidate visible even when conflicting
    # test revisions require REVIEW. "Provisional" must remain explicit to
    # prevent its use as an accepted geotechnical design value.
    qualifier=" [PROVISIONAL]" if status=="REVIEW" and interval is not None else ""
    report_start=(_num(visible_selected.start,2,"m")+qualifier) if visible_selected else display_status
    report_end=(_num(visible_selected.end,2,"m")+qualifier) if visible_selected else "Not displayed"
    thickness=(_num(visible_selected.thickness,2,"m")+qualifier) if visible_selected else "Not reported (< or = 0.10m)"
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
        ("Ic screening input","Ic >= 2.60, raw persistence >=0.05m; unchanged"),
        ("Visible silt display rule","ALL distinct intervals strictly >0.10m"),
        ("Visible qualifying depth intervals",f"{len(display_layers)} (see Silt Layers page)"),
        ("Silt start (reported)",report_start),
        ("Silt end (reported)",report_end),
        ("Silt thickness (reported)",thickness),
        ("Depth to selected Ic horizon (NOT continuous sand)",
         (_num(getattr(a,"sand_layer_thickness",None),2,"m")+
          (" [PROVISIONAL]" if status=="REVIEW" else ""))
         if visible_selected is not None and getattr(a,"sand_layer_thickness",None) is not None
         else "N/A - no established qualifying interval"),
        ("Raw observed silt start",raw_start),
        ("Raw observed silt end",raw_end),
        ("Raw observed thickness",raw_thick),
        ("Maximum measured valid Ic",_num(max_ic,3)),
        ("Number of REPORTABLE >0.10m intervals",str(len(display_layers))),
        ("Number of raw screened intervals (audit only)",str(len(threshold_runs))),
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


def reportable_silt_pages(analysis, *, page_size=23):
    """Print every separated observed >0.10m screened horizon in source PDF.

    An empty list gets a clear explanatory page but no invented zero-thickness
    layer. UNKNOWN material below any horizon remains UNKNOWN, not clay.
    """
    from engineering_reporting_policy import visible_silt_layers, display_silt_summary
    layers=visible_silt_layers(analysis)
    display_status,_=display_silt_summary(analysis)
    batches=[layers[i:i+page_size] for i in range(0,len(layers),page_size)]
    if not batches:batches=[()]
    pages=[]
    for page_index,part in enumerate(batches,1):
        fig=Figure(figsize=(8.27,11.69),dpi=150,facecolor="white")
        fig.text(.06,.965,"ALL OBSERVED SILT-SCREENED DEPTH INTERVALS",fontsize=14,
                 weight="bold",color="#153851")
        fig.text(.06,.937,f"{analysis.reference} · Page {page_index}/{len(batches)}",
                 fontsize=9,color="#475569")
        fig.text(.06,.905,"DISPLAY: each separate Ic>=2.60 interval strictly >0.10 m.",
                 fontsize=9,color="#14344b")
        fig.text(.06,.882,"Not a laboratory USCS soil classification. Thin observations are",
                 fontsize=8,color="#9a3412")
        fig.text(.06,.863,"excluded from DISPLAY, never converted to a zero-thickness layer.",
                 fontsize=8,color="#9a3412")
        ax=fig.add_axes((.06,.23,.88,.585));ax.axis("off")
        labels=("Layer #","Start BGL (m)","End BGL (m)","Thickness (m)","Status")
        items=[labels]+[(str(i+(page_index-1)*page_size),f"{l.start:.3f}",
                            f"{l.end:.3f}",f"{l.thickness:.3f}",
                            "OBSERVED / REVIEW" if analysis.status=="REVIEW"
                            else "OBSERVED") for i,l in enumerate(part,1)]
        if not part:
            items.append(("-", "-", "-", "NOT REPORTED",
                          "No measured layer >0.10m"))
        h=min(.64,max(.09,.038*len(items)))
        table=Table(ax,bbox=[0,1-h/.585,1,h/.585])
        sizes=(.1,.21,.21,.20,.28)
        for i,row in enumerate(items):
            for j,val in enumerate(row):
                cell=table.add_cell(i,j,width=sizes[j],height=1/len(items),
                    text=val,loc="left",
                    facecolor="#173d59" if i==0 else "#f2f7fb" if i%2 else "#fff",
                    edgecolor="#d0dbe6")
                cell.get_text().set_fontsize(8)
                if i==0:
                    cell.get_text().set_color("white")
                    cell.get_text().set_weight("bold")
        ax.add_table(table)
        fig.text(.06,.153,"ENGINEERING AND COVERAGE LIMITATIONS",fontsize=9,
                 color="#153851",weight="bold")
        note=(f"Original engine status: {analysis.status}. Display: {display_status}. "
              "Unmeasured soil after silt is UNKNOWN, never presumed CLAY. "
              "Raw Ic measurements and short crossings are available in Excel "
              "for independent engineering review.")
        for i,line in enumerate(textwrap.wrap(note,111)[:6]):
            fig.text(.06,.130-.018*i,line,fontsize=8,color="#334155")
        pages.append(fig)
    return pages

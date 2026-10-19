"""Compact production workbook — only actionable engineering analysis tabs.

All full-depth measurements, source QA, project maps and optional reference
comparison are in ONE XLSX. No instructions-only or duplicate chart tabs.
"""
from __future__ import annotations
from pathlib import Path
from io import BytesIO
from collections import Counter
from math import isfinite
import numpy as np
import xlsxwriter

BASE_SHEETS=("Summary","CPT Analysis","Charts","CPT Curves","Full Analysis","All Soil Layers",
             "CPT Measurements","Project Maps","Source Audit")


def num(x):
    try:
        value=float(x)
        return value if isfinite(value) else None
    except (ValueError,TypeError):return None


def _styles(book):
    return {"title":book.add_format({"font_name":"Aptos Display","font_size":18,"font_color":"#18364f","bold":True}),
     "header":book.add_format({"font_color":"#ffffff","bg_color":"#173e59","bold":True,
                       "text_wrap":True,"valign":"vcenter","font_name":"Aptos"}),
     "plain":book.add_format({"font_name":"Aptos","font_size":10,"valign":"top"}),
     "number":book.add_format({"font_name":"Aptos","font_size":10,"num_format":"0.000","valign":"top"}),
     "review":book.add_format({"bg_color":"#fff0df","font_color":"#9a3412","font_name":"Aptos"}),
     "warn":book.add_format({"bg_color":"#fae0de","font_color":"#981b1b","font_name":"Aptos"}),
     "good":book.add_format({"bg_color":"#edf7ef","font_color":"#166534","font_name":"Aptos"}),
     "small":book.add_format({"font_name":"Aptos","font_size":9,"font_color":"#607184"})}


def _sheet(wb,styles,name,headers,rows,widths=None):
    sheet=wb.add_worksheet(name)
    sheet.set_tab_color("#173e59" if name in ("Summary","CPT Analysis") else "#7d9eb6")
    for j,h in enumerate(headers):sheet.write(0,j,h,styles["header"])
    sheet.set_row(0,39)
    sheet.freeze_panes(1,1)
    sheet.set_column(0,0,27)
    sheet.set_column(1,len(headers)-1,18)
    if widths:
        for index,width in widths.items():sheet.set_column(index,index,width)
    total=0
    for i,row in enumerate(rows,1):
        total=i
        for j,val in enumerate(row):
            if val is None:
                sheet.write(i,j,"NOT RECORDED / UNAVAILABLE",styles["small"])
                continue
            if isinstance(val,(int,float)) and num(val) is not None:
                sheet.write_number(i,j,float(val),styles["number"])
            else:sheet.write(i,j,str(val)[:32000],styles["plain"])
    if total:sheet.autofilter(0,0,total,len(headers)-1)
    sheet.set_landscape()
    sheet.fit_to_pages(1,0)
    sheet.repeat_rows(0)
    return sheet,total


def _save_figure(fig):
    stream=BytesIO()
    fig.savefig(stream,format="png",dpi=110,facecolor="white")
    stream.seek(0)
    return stream


def export_excel(analyses, output_path, errors=None, source_audit=None, *,
                 original_xlsb=None, foundation_xlsx=None, site_boundary=None,
                 comparison_result=None):
    """Clean deliverable. Extra original-source tabs exist only when the source exists."""
    from cpt_core import natural_ref_key
    from reporting_pro import analysis_record
    from engineering_layers import from_analysis
    from engineering_geo_explorer import risk_plan,spatial_points
    analyses=sorted(list(analyses),key=lambda a:natural_ref_key(a.reference))
    audits=list(source_audit or [])
    errors=list(errors or [])
    output=Path(output_path)
    output.parent.mkdir(parents=True,exist_ok=True)
    book=xlsxwriter.Workbook(str(output),{"constant_memory":True})
    style=_styles(book)
    records=[analysis_record(a) for a in analyses]
    points=[]
    layer_rows=[]
    detail=[]
    quick=[]
    for i,(a,r) in enumerate(zip(analyses,records),1):
        md=getattr(a,"metadata",{}) or {}
        z=a.final_interval
        try:observed=from_analysis(a)
        except (TypeError,ValueError,AttributeError,IndexError,KeyError):observed=None
        maximum=observed.maximum_silt_m if observed else None
        cumulative=observed.cumulative_silt_m if observed else None
        unknown=observed.unknown_m if observed else None
        count=observed.silt_count if observed else None
        # A genuine conflicting full-depth CPT remains REVIEW, but the
        # measured candidate is still a quantitative observation. Do not
        # erase it from the five-column summary. Make its provisional
        # status unmistakable through cell comments / amber formatting.
        quick.append((i,a.reference,
                z.start if z is not None else
                ("NO SILT" if a.status=="NO SILT" else "REVIEW"),
                z.thickness if z is not None else
                (0.0 if a.status=="NO SILT" else None),
                a.sand_layer_thickness))
        detail.append((a.reference,a.status,num(md.get("easting")),num(md.get("northing")),
            num(md.get("ground_elevation")),num(getattr(a,"test_depth_raw",None)),
            z.start if z else None,z.end if z else None,z.thickness if z else None,
            z.start_raw if z else None,z.end_raw if z else None,z.thickness_raw if z else None,
            count,cumulative,maximum,unknown,md.get("analysis_gamma_soil_kn_m3"),
            md.get("analysis_water_table_bgl_m"),md.get("area_ratio"),
            getattr(a,"sensor_dropout_depth",None),str(a.source_path),
            str(getattr(a,"verification_note",""))))
        if observed:
            for l in observed.layers:
                layer_rows.append((a.reference,l.number,l.kind,l.start_m,l.end_m,
                  l.thickness_m,l.mean_ic,l.status,
                  "YES" if l.silt_screen else "NO",str(a.source_path.name)))
        points.append(a)

    # Preserve ALL available original source header/metadata, including
    # distinctions between field test date and GEF export date. The quick
    # five-column sheet remains concise while nothing disappears from Excel.
    meta_rows=[]
    for a in analyses:
        md=getattr(a,"metadata",{}) or {}
        def extent(attr):
            try:
                arr=np.asarray(getattr(a,attr),dtype=float)
                values=arr[np.isfinite(arr)]
                return ((float(np.min(values)),float(np.max(values))) if len(values)
                        else (None,None))
            except (AttributeError,TypeError,ValueError):
                return (None,None)
        qc_lo,qc_hi=extent("qc")
        fs_lo,fs_hi=extent("fs")
        u_lo,u_hi=extent("u2")
        ic_lo,ic_hi=extent("ic")
        meta_rows.append((a.reference,a.source_path.name,a.source_path.suffix.upper(),
          md.get("client"),md.get("project_name") or md.get("project_id"),
          md.get("main_contractor"),md.get("location"),
          md.get("test_date") or "NOT RECORDED — source file date is separate",
          md.get("file_date"),md.get("cone_id"),md.get("standard"),
          md.get("area_ratio"),md.get("ground_elevation"),md.get("easting"),
          md.get("northing"),md.get("records",len(getattr(a,"depth",[]))),
          getattr(a,"test_depth_raw",None),md.get("analysis_gamma_soil_kn_m3"),
          md.get("analysis_water_table_bgl_m"),md.get("cpt_stage"),
          md.get("analysis_smoothing_window_samples"),qc_lo,qc_hi,
          fs_lo,fs_hi,u_lo,u_hi,ic_lo,ic_hi,
          getattr(a,"sensor_dropout_depth",None),a.status,
          getattr(a,"verification_note",None),md.get("source_selection_reason"),
          md.get("source_quality")))
    _sheet(book,style,"CPT Metadata",
        ["CPT REFERENCE","Original file","Source format","Client","Project",
         "Main contractor","Area / location","Field test date (if recorded)",
         "Source FILEDATE (not test date)","Cone ID","CPT standard",
         "Cone area ratio","Ground elevation RL (m)","Survey Easting",
         "Survey Northing","Measurement records","Sounding depth BGL (m)",
         "Soil unit weight kN/m3","Groundwater BGL (m)","PRE/POST stage",
         "Smoothing window samples","qc minimum MPa","qc maximum MPa",
         "fs minimum MPa","fs maximum MPa","u2 minimum MPa","u2 maximum MPa",
         "Ic minimum","Ic maximum","Terminal sensor dropout (m)",
         "Engineering status","Verification notes","Revision/source decision",
         "Source quality"],meta_rows,{0:27,1:44,7:36,8:35,31:92,32:92})

    # Raw GEF/GFF headers are contractual input evidence. Keep every original
    # key and value in this SAME workbook, not merely the selected fields in
    # the concise CPT Metadata tab. Never pretend that missing u2 was measured.
    full_headers=[]
    for a in analyses:
        meta=getattr(a,"metadata",{}) or {}
        for order,part in enumerate(meta.get("source_header_entries",[]) or [],1):
            try:
                key,value=part
            except (TypeError,ValueError):
                continue
            full_headers.append((a.reference,a.source_path.name,order,key,value))
        if getattr(a.source_path,"suffix","").lower() in (".gef",".gff"):
            full_headers.append((a.reference,a.source_path.name,
                   len(meta.get("source_header_entries",[]) or [])+1,
                   "PORE_PRESSURE_CALCULATION_SOURCE",
                   meta.get("pore_pressure_source","NOT DETERMINED")))
    if full_headers:
        _sheet(book,style,"Original GEF Headers",
               ["CPT REFERENCE","Input file","Header order","Original GEF field",
                "Original GEF value / declared assumption"],full_headers,
               {0:28,1:46,3:34,4:105})

    # Main deliverable: the user's original five columns; no extra fields here.
    quick_summary=_sheet(book,style,"CPT Analysis",
           ["SI.No","CPT REFERENCE","Silt start depth after (m)","silt depth (m)",
            "Sand layer thickness before silt (m)"],quick,{1:29,2:25,3:19,4:25})
    # Five numeric columns remain unchanged. Source conflicts show the
    # provisional numeric interpretation with an amber marker/comment;
    # Full Analysis and Source Audit retain REVIEW, never VERIFIED.
    for idx,a in enumerate(analyses,1):
        if a.status=="REVIEW":
            quick_summary.set_row(idx,None,style["review"])
            explanation=("ENGINEERING REVIEW — NOT VERIFIED. "+
                         str(getattr(a,"verification_note",""))+
                         " If numerical silt is shown, it is the selected"
                         " candidate only; competing full-depth revisions"
                         " must be independently reconciled.")
            quick_summary.write_comment(idx,1,explanation[:30000])
    _sheet(book,style,"Full Analysis",
           ["CPT REFERENCE","Status","Easting","Northing","Ground elevation RL (m)",
            "Sounding depth BGL (m)","Reported silt start (m)","Reported silt end (m)",
            "Reported silt thickness (m)","Observed raw start (m)","Observed raw end (m)",
            "Observed raw thickness (m)","Qualifying layer count",
            "Cumulative qualifying thickness (m)","Maximum observed interval (m)",
            "Unknown sensor depth (m)","Soil unit weight (kN/m3)",
            "Water table BGL (m)","Cone area ratio","Terminal sensor dropout BGL (m)",
            "Input source","Verification notes"],detail,{0:30,20:55,21:100})
    _sheet(book,style,"All Soil Layers",
           ["CPT REFERENCE","Layer","SBT estimated type (not lab USCS)",
            "Top BGL (m)","Base BGL (m)","Observed thickness (m)",
            "Mean Ic","Quality","Ic >= 2.60 screened","Source file"],layer_rows,
           {0:28,2:37,7:25,9:40})

    # Preserve ALL raw readings across numbered worksheets when the
    # project exceeds Excel's million-row physical sheet limit.
    from engineering_excel_paging import write_cpt_measurements,write_paged_rows
    row,measurement_ranges,measurement_pages=write_cpt_measurements(
        book,style,analyses)

    # A REVIEW result must never look like an empty CPT. Keep all measured
    # candidate intervals as EVIDENCE ONLY, separate from reportable VERIFIED
    # thickness. Where a PDF has no usable vector trace, explain that explicitly.
    reviews=[]
    for a in analyses:
        if a.status!="REVIEW":continue
        evidence=[]
        metadata=getattr(a,"metadata",{}) or {}
        # A verified graphical Ic crossing may be thinner than the 0.1 m
        # project reporting increment. Do not erase measured data just
        # because it is not yet approved for rounding in the summary.
        observed_start=num(metadata.get("thin_interval_unrounded_start"))
        observed_end=num(metadata.get("thin_interval_unrounded_end"))
        observed_thickness=num(metadata.get("thin_interval_unrounded_thickness"))
        if (observed_start is not None and observed_end is not None and
             observed_thickness is not None and observed_thickness>0):
            evidence.append(("OBSERVED THIN LAYER - reporting convention needs approval",
                         observed_start,observed_end,observed_thickness))
        try:
            observation=from_analysis(a)
            evidence.extend(("SUSTAINED - UNVERIFIED",x,y,y-x)
                            for x,y in observation.silt_intervals)
            evidence.extend(("BRIEF BELOW PERSISTENCE",x,y,y-x)
                            for x,y in observation.brief_exceedances)
        except (AttributeError,TypeError,ValueError,IndexError):
            pass
        if not evidence:
            evidence=[("NO RELIABLE NUMERICAL INTERVAL",None,None,None)]
        for kind,start,end,thickness in evidence:
            reviews.append((a.reference,kind,start,end,thickness,
                getattr(a,"sensor_dropout_depth",None),
                getattr(a,"test_depth_raw",None),a.source_path.name,
                str(getattr(a,"verification_note","") or
                    "See Source Audit; input data do not establish a reportable layer."),
                "PRELIMINARY ONLY — NOT VERIFIED FOR DESIGN"))
    if reviews:
        _sheet(book,style,"Review Evidence",
               ["CPT REFERENCE","Observed interval evidence","Top BGL (m)",
                "Base BGL (m)","Measured candidate thickness (m)",
                "Terminal sensor dropout (m)","Sounding depth (m)",
                "Original file","Reason analysis was not verified","Use limitation"],
                reviews,{0:29,1:34,7:44,8:105,9:55})

    # Each unresolved CPT gets one actionable row with actual observed
    # geometry where available, rather than a context-free REVIEW label.
    from engineering_review_triage import review_register
    triage_rows=review_register(analyses)
    if triage_rows:
        _sheet(book,style,"Review Resolution",
            ["CPT REFERENCE","Review category","Original file",
             "Observed start BGL (m)","Observed end BGL (m)",
             "Observed thickness (m)","Sounding depth (m)",
             "Sensor dropout depth (m)","Revision / survey conflict",
             "Required engineering resolution","Exact source evidence",
             "Disposition"],[
                (r["reference"],r["category"],r["source"],
                 r["measured_start_m"],r["measured_end_m"],
                 r["measured_thickness_m"],r["test_depth_m"],
                 r["sensor_dropout_m"],r["conflict_fields"],
                 r["required_action"],r["evidence"],
                 r["engineering_disposition"])
                for r in triage_rows],
            {0:28,1:31,2:49,8:32,9:100,10:105,11:70})

    # Audit source conflicts, unclassified tails and processing exceptions
    audit_rows=[]
    for r in audits:
        # select_project_results returns physical source keys
        # 'family'/'source_file', not the old 'reference'/'source' aliases.
        # Preserve one identifiable row for every physical original file.
        audit_rows.append((
           r.get("family") or r.get("reference"),
           r.get("source_file") or r.get("source"),
           r.get("source_type"),r.get("revision"),r.get("selected"),
           r.get("status"),r.get("silt_start"),r.get("silt_thickness"),
           r.get("selection_reason") or r.get("reason"),
           r.get("verification_note") or r.get("verification"),
           r.get("source_quality")))
    # When called directly from CLI with no multi-source audit, selected
    # results are still individually documented with exact input filenames.
    if not audits:
        for a in analyses:
            z=getattr(a,"final_interval",None)
            audit_rows.append((a.reference,a.source_path.name,
                 a.source_path.suffix.upper().lstrip("."),
                 (getattr(a,"metadata",{}) or {}).get("source_revision",0),
                 "YES",a.status,z.start if z else None,
                 z.thickness if z else None,
                 (getattr(a,"metadata",{}) or {}).get("source_selection_reason") or
                 "Analyzed selected input source.",
                 getattr(a,"verification_note",""),
                 (getattr(a,"metadata",{}) or {}).get("source_quality")))
    for name,note in errors:
        if not any(str(r[1])==str(name) for r in audit_rows):
            audit_rows.append(("PROCESSING ERROR",name,None,None,"NO","ERROR",
                               None,None,note,note,"UNREADABLE SOURCE"))
    _sheet(book,style,"Source Audit",
           ["CPT REFERENCE","Physical input filename","Source type",
            "Revision","Selected","Status","Selected silt start BGL (m)",
            "Selected silt thickness (m)","Source decision / conflict reason",
            "Verification and data-quality evidence","Source quality"],
          audit_rows,{0:30,1:48,2:14,3:12,4:13,5:19,6:21,7:22,8:83,9:115,10:24})

    # Optional user-provided engineering data; no empty foundation tabs.
    cached=[]
    extra_pages=[]
    if original_xlsb:
        from engineering_reference_project import analyze_original_xlsb
        from engineering_reference_parity import compare_engine_to_reference
        source_settings,cached,_=analyze_original_xlsb(original_xlsb)
        _sheet(book,style,"Foundation Results",
           ["CPT","Easting","Northing","Raft settlement (mm), SAVED XLSB",
            "Min liquefaction FOS, SAVED XLSB","Robertson BC (kPa)",
            "Aramco BC (kPa)","Original settlement check"],[
             (x["reference"],x["easting"],x["northing"],x["settlement_mm"],
              x["minimum_liquefaction_fos"],x["robertson_bc_kpa"],
              x["aramco_bc_kpa"],x["settlement_check_original"]) for x in cached])
        if analyses:
            checks=compare_engine_to_reference(analyses,cached,
                      water_table=(analyses[0].metadata or {}).get("analysis_water_table_bgl_m"),
                      reference_settings=source_settings)
            _sheet(book,style,"Reference Comparison",
                 ["CPT","Comparison status","Native start","Native thickness",
                  "Source SBT start","Source SBT thickness","Start delta",
                  "Thickness delta","Coordinate difference (m)","Explanation"],[
                    (c["reference"],c["status"],c["native_start"],c["native_thickness"],
                     c["reference_start"],c["reference_thickness"],c["difference_start"],
                     c["difference_thickness"],c["point_offset"],c["notes"])
                    for c in checks],{9:85})
        # Full original source series, not just precomputed intervals:
        # every saved elevation/qc/categorical-zone sample is retained.
        from engineering_xlsb_reference import ReferenceWorkbookCache
        with ReferenceWorkbookCache(original_xlsb) as cache:
            original_points=cache.mapped_profiles()
        point_count=sum(len(curve) for curve in original_points.values())
        # The complete XLSB source profile is paginated, never rejected or clipped.
        ground={p["reference"]:num(p.get("ground_elevation")) for p in cached}
        def original_rows():
            for ref,curve in original_points.items():
                gl=ground.get(ref)
                for elevation,qc,zone in curve:
                    yield (ref,elevation,None if gl is None else gl-elevation,
                           qc,zone,"ZONE 1-4 screen" if zone is not None and zone<=4
                           else "Other SBT zone / UNKNOWN",
                           "Original XLSB cached categorical zone, NOT numeric Ic")
        write_paged_rows(book,style,"Original SBT Curves",
               ["CPT","Elevation RL (m)","Depth BGL (m)","Saved qc (MPa)",
                "Saved SBT zone (1-9)","Source zone screen","Provenance"],
               original_rows(),widths={0:28,5:32,6:70})
    if foundation_xlsx:
        # Original XLSB holds the project's cached raft results, while the
        # supplied pre-CPT workbook also carries separate ISOLATED cases.
        # Both must be retained when both source workbooks are supplied.
        from engineering_comparison import read_summary_xlsx
        foundations=read_summary_xlsx(foundation_xlsx)
        _sheet(book,style,"Supplied Footing Cases" if original_xlsb else "Foundation Results",
           ["CPT","Footing type","Easting","Northing","Settlement (mm) SOURCE",
            "Min FOS SOURCE","Footing width (m)","Footing L/B",
            "Original settlement check","Original FOS check","Source worksheet"],
           [(f.reference,f.foundation,f.east,f.north,
             f.metrics.get("settlement_mm"),f.metrics.get("fos"),
             f.footing_width_m,f.footing_lb_ratio,
             f.reported_settlement_check,f.reported_fos_check,
             f.source_sheet) for f in foundations],
           {0:29,1:17,8:25,9:25,10:30})
    if comparison_result:
        _sheet(book,style,"Pre Post Changes",
              ["PRE reference","POST reference","Metric","PRE","POST","Change",
               "% change","Matching method"],[
                (m["pre"].reference,m["post"].reference,key,v.get("pre"),
                 v.get("post"),v.get("delta"),v.get("percent"),
                 m.get("matching_method")) for m in comparison_result.get("matched",[])
                 for key,v in m["metrics"].items()])

    # Maps and project summary are dynamic, not static instructions.
    source_data=cached if cached else analyses
    plan_points,excluded=spatial_points(source_data)
    fig=__import__("matplotlib.figure",fromlist=["Figure"]).Figure(
        figsize=(11.5,7),dpi=100,facecolor="white")
    drawn=risk_plan(fig,source_data,boundary=site_boundary,
                    warning_m=.10,high_m=.30,show_interpretive_surface=True)
    map_images=[_save_figure(fig)]
    try:
        from engineering_3d_map import site_3d_figure
        fig3,info=site_3d_figure(source_data,site_boundary)
        map_images.append(_save_figure(fig3))
    except (RuntimeError,ValueError,TypeError):
        # Two-dimensional map remains available if the 3D engine cannot run.
        info={"plotted":0}
    map_sheet=book.add_worksheet("Project Maps")
    map_sheet.set_tab_color("#306d9f")
    map_sheet.set_column(0,0,3);map_sheet.set_column(1,15,12)
    map_sheet.merge_range("B2:N2","SITE SURVEY — SCREENING PLAN & STRATIGRAPHIC VIEW",style["header"])
    map_sheet.set_row(1,32)
    map_sheet.insert_image("B4","plan.png",{"image_data":map_images[0],"x_scale":.49,"y_scale":.49})
    if len(map_images)>1:map_sheet.insert_image("B51","subsurface.png",{
        "image_data":map_images[1],"x_scale":.49,"y_scale":.49})
    map_sheet.write("B97",f"Observed points: {len(plan_points)} | coordinate exceptions: {len(excluded)} | "
                    "3D is a visual screening representation, not a validated geological volume.",style["small"])
    if excluded:
        _sheet(book,style,"Coordinate QA",
               ["CPT","Easting (original)","Northing (original)","Survey QA"],
               [(p.reference,p.x,p.y,"Outlier withheld from map; original data unchanged")
                for p in excluded])

    # Restored, fully editable Excel Charts and CPT Curves worksheets.
    # Chart objects reference these workbook cells and are not static PNGs.
    from engineering_excel_charts import restore_project_charts
    restore_project_charts(book,plan_points,analyses,measurement_ranges)

    # First sheet and clean summary display (put summary first in Excel tabs).
    summary=book.add_worksheet("Summary")
    summary.set_tab_color("#0b6b5a")
    summary.set_column("A:A",36);summary.set_column("B:B",22)
    summary.set_column("D:N",13)
    summary.merge_range("A1:N2","CPT PROJECT | ENGINEERING OVERVIEW",style["header"])
    summary.set_row(1,39)
    total_high=len(drawn["high"])
    # Separate the two actionable causes of PDF REVIEW instead of counting
    # them all as failed calculations. A measured thin positive layer is not
    # the same uncertainty as contradictory physical test revisions.
    review_thin=review_conflicts=review_other=0
    for a in analyses:
        if a.status!="REVIEW":continue
        meta=getattr(a,"metadata",{}) or {}
        if any(bool(meta.get(k)) for k in
               ("source_revision_conflict","source_spatial_conflict","source_datum_conflict")):
            review_conflicts+=1
        elif (num(meta.get("thin_interval_unrounded_thickness")) or 0)>0:
            review_thin+=1
        else:
            review_other+=1
    metrics=[("CPT locations",len(analyses)),
            ("Verified silt",sum(a.status=="VERIFIED" for a in analyses)),
            ("No sustained silt",sum(a.status=="NO SILT" for a in analyses)),
            ("Engineering review",sum(a.status=="REVIEW" for a in analyses)),
            ("REVIEW — measured thin positive intervals",review_thin),
            ("REVIEW — conflicting physical source revisions",review_conflicts),
            ("REVIEW — other missing/uncertain evidence",review_other),
            ("HIGH screening points ≥0.30m",total_high),
            ("Coordinate exceptions",len(excluded)),
            ("Raw measurement records",row),
            ("Largest observed continuous interval (m)",
             max((p.maximum_m or 0 for p in plan_points),default=0)),
            ("Source reference dataset","Original XLSB (cached)" if cached else "Current CPT batch"),
            ("Field verification","Required for REVIEW, coordinates and unapproved assumptions")]
    for i,(name,value) in enumerate(metrics,4):
        summary.write(i,0,name,style["plain"])
        if isinstance(value,(float,int)):summary.write_number(i,1,float(value),style["number"])
        else:summary.write(i,1,str(value),style["plain"])
    highs=drawn["high"]
    summary.write("D4","ALL HIGH SCREENING POINTS",style["header"])
    for i,p in enumerate(highs,5):
        summary.write(i,3,p.reference,style["plain"])
        summary.write_number(i,4,p.maximum_m,style["number"])
    summary.insert_image("G4","plan.png",{"image_data":map_images[0],"x_scale":.30,"y_scale":.30})
    # Contract: the editable/readable five-column CPT Analysis is the FIRST
    # workbook tab and the default open view. Summary and 2D/3D maps remain
    # adjacent in this same XLSX rather than separate output artifacts.
    quick_sheet=next(x for x in book.worksheets_objs if x.name=="CPT Analysis")
    book.worksheets_objs.remove(quick_sheet)
    book.worksheets_objs.insert(0,quick_sheet)
    book.worksheets_objs.remove(summary)
    book.worksheets_objs.insert(1,summary)
    for offset,name in enumerate(("Charts","CPT Curves"),2):
        sheet=next(x for x in book.worksheets_objs if x.name==name)
        book.worksheets_objs.remove(sheet)
        book.worksheets_objs.insert(offset,sheet)
    # The sheet objects were deliberately reordered after they were created.
    # XlsxWriter stores worksheet.index separately from the list order, so
    # activate()/set_first_sheet() would otherwise write stale activeTab and
    # firstSheet values despite the visible CPT Analysis sheet being first.
    for zero_based_index,sheet in enumerate(book.worksheets_objs):
        sheet.index=zero_based_index
    quick_sheet.activate()
    quick_sheet.set_first_sheet()
    book.close()
    return output

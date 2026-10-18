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

BASE_SHEETS=("Summary","CPT Analysis","Full Analysis","All Soil Layers",
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
        quick.append((i,a.reference,
                "REVIEW" if a.status=="REVIEW" else
                "NO SILT" if z is None else z.start,
                None if a.status=="REVIEW" else 0.0 if z is None else z.thickness,
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

    # Main deliverable: the user's original five columns; no extra fields here.
    _sheet(book,style,"CPT Analysis",
           ["SI.No","CPT REFERENCE","Silt start depth after (m)","silt depth (m)",
            "Sand layer thickness before silt (m)"],quick,{1:29,2:25,3:19,4:25})
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

    # Store every real numeric CPT point, not just chart summaries.
    # Excel's million-row hard cap is enforced with an explicit error;
    # outputs are never silently truncated.
    total_measure=sum(len(getattr(a,"depth",[])) for a in analyses)
    if total_measure>1_048_575:
        book.close()
        output.unlink(missing_ok=True)
        raise ValueError("More than Excel's 1,048,575 data rows. Split batches or use a detail database, never silently truncate.")
    ws=book.add_worksheet("CPT Measurements")
    measurement_columns=["CPT REFERENCE","Depth BGL (m)","qc (MPa)","fs (MPa)",
      "u2 (MPa)","qt (MPa)","Fr (%)","Qtn","Ic","Measurement validity","Source type"]
    for j,h in enumerate(measurement_columns):ws.write(0,j,h,style["header"])
    ws.set_row(0,36);ws.freeze_panes(1,2);ws.set_column(0,0,29)
    ws.set_column(1,8,16);ws.set_column(9,10,24)
    row=0
    for a in analyses:
        if not hasattr(a,"depth"):continue
        try:
            arrays=[np.asarray(getattr(a,key),dtype=float) for key in
                    ("depth","qc","fs","u2","qt","fr","qtn","ic")]
            valid=np.asarray(a.valid_sensor,bool)
        except (AttributeError,TypeError,ValueError):continue
        n=len(arrays[0])
        if any(len(x)!=n for x in arrays) or len(valid)!=n:
            raise ValueError("CPT data arrays have inconsistent depths: "+a.reference)
        for k in range(n):
            row+=1
            ws.write(row,0,a.reference,style["plain"])
            for j,arr in enumerate(arrays,1):
                v=float(arr[k])
                if isfinite(v):
                    ws.write_number(row,j,v,style["number"])
                else:
                    ws.write(row,j,"NOT MEASURED",style["small"])
            ws.write(row,9,"VALID" if valid[k] and isfinite(arrays[-1][k]) else "UNKNOWN",style["plain"])
            ws.write(row,10,str(a.source_path.suffix).upper(),style["plain"])
    if row:ws.autofilter(0,0,row,len(measurement_columns)-1)

    # Audit source conflicts, unclassified tails and processing exceptions
    audit_rows=[]
    for r in audits:
        audit_rows.append((r.get("reference"),r.get("source"),r.get("selected"),
           r.get("status"),r.get("selection_reason") or r.get("reason"),
           r.get("verification_note") or r.get("verification"),r.get("source_quality")))
    for name,note in errors:audit_rows.append(("PROCESSING ERROR",name,"NO","REVIEW",note,"",""))
    for a in analyses:
        if a.status=="REVIEW":
            audit_rows.append((a.reference,a.source_path.name,"YES",a.status,
                              "Engineering interpretation requires review",
                              a.verification_note,""))
    _sheet(book,style,"Source Audit",
           ["CPT REFERENCE","Input file","Selected","Status",
            "Why this source/result","Verification and data-quality notes","Source quality"],
          audit_rows,{0:30,1:44,4:80,5:100})

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
        if point_count>1_048_575:
            raise ValueError("Original XLSB has more SBT samples than one Excel worksheet can hold.")
        ground={p["reference"]:num(p.get("ground_elevation")) for p in cached}
        def original_rows():
            for ref,curve in original_points.items():
                gl=ground.get(ref)
                for elevation,qc,zone in curve:
                    yield (ref,elevation,None if gl is None else gl-elevation,
                           qc,zone,"ZONE 1-4 screen" if zone is not None and zone<=4
                           else "Other SBT zone / UNKNOWN",
                           "Original XLSB cached categorical zone, NOT numeric Ic")
        _sheet(book,style,"Original SBT Curves",
               ["CPT","Elevation RL (m)","Depth BGL (m)","Saved qc (MPa)",
                "Saved SBT zone (1-9)","Source zone screen","Provenance"],
               original_rows(),{0:28,5:32,6:70})
    elif foundation_xlsx:
        from engineering_comparison import read_summary_xlsx
        foundations=read_summary_xlsx(foundation_xlsx)
        _sheet(book,style,"Foundation Results",
           ["CPT","Footing type","Easting","Northing","Settlement (mm) SOURCE",
            "Min FOS SOURCE","Source workbook"],
           [(f.reference,f.foundation,f.east,f.north,
             f.metrics.get("settlement_mm"),f.metrics.get("fos"),
             f.source_sheet) for f in foundations])
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

    # First sheet and clean summary display (put summary first in Excel tabs).
    summary=book.add_worksheet("Summary")
    summary.set_tab_color("#0b6b5a")
    summary.set_column("A:A",36);summary.set_column("B:B",22)
    summary.set_column("D:N",13)
    summary.merge_range("A1:N2","CPT PROJECT | ENGINEERING OVERVIEW",style["header"])
    summary.set_row(1,39)
    total_high=len(drawn["high"])
    metrics=[("CPT locations",len(analyses)),
            ("Verified silt",sum(a.status=="VERIFIED" for a in analyses)),
            ("No sustained silt",sum(a.status=="NO SILT" for a in analyses)),
            ("Engineering review",sum(a.status=="REVIEW" for a in analyses)),
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
    # Place Summary first for quick consumption; sheets have independent IDs
    # in the package, XlsxWriter supports reordered worksheets via objs.
    book.worksheets_objs.remove(summary)
    book.worksheets_objs.insert(0,summary)
    # selected worksheet should be Overview, not a deep data table
    summary.activate()
    summary.set_first_sheet()
    book.close()
    return output

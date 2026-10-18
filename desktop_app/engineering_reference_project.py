"""Whole-project interpretation of saved ORIGINAL Excel XLSB cached SBT regions.

Reference SBT zone codes are categorical, *not numerical Ic values*.
This does not execute source VBA or independently solve raft settlement.
"""
from __future__ import annotations
from pathlib import Path
import math
from decimal import Decimal,ROUND_HALF_UP

def _tenth(value):
    return float(Decimal(str(value)).quantize(Decimal("0.1"),rounding=ROUND_HALF_UP))

def _segments(profile,ground_elevation, min_m=.05):
    """Parse all contiguous observed SBT zones 1..4 as project 'silt-like'.

    Excel zones 1/2/3 can include organic/clay behavior: they are screened
    as fine-grained-like, NOT claimed definitive USCS silt. A zone >4 is
    outside the project fine-grained screening threshold.
    """
    points=[]
    for elevation,qc,zone in profile:
        if zone is None or zone<1 or zone>9:continue
        depth=float(ground_elevation)-float(elevation)
        if not math.isfinite(depth) or depth<-.03:continue
        points.append((round(max(0,depth),5),float(qc),int(zone)))
    points.sort()
    runs=[];brief=[];start=None;last=None;zones=set()
    def flush(next_depth=None):
        nonlocal start,last,zones
        if start is None:return
        end=last if next_depth is None else min(next_depth,last+.025)
        # Current cells are sampled at 0.01m: a classification cannot
        # extend through gaps; use one sample cell width only at boundary.
        end=max(start,end)
        data={"start_raw":start,"end_raw":end,
              "thickness_raw":max(0,end-start),"zone_codes":sorted(zones),
              "reported_start":_tenth(start),"reported_end":_tenth(end)}
        data["reported_thickness"]=round(data["reported_end"]-data["reported_start"],2)
        (runs if data["thickness_raw"]>=min_m-1e-9 else brief).append(data)
        start=None;last=None;zones=set()
    for depth,qc,zone in points:
        if start is not None and depth-last>.035:flush()
        flag=zone<=4
        if flag:
            if start is None:start=depth
            last=depth;zones.add(zone)
        elif start is not None:
            flush(depth)
    flush()
    return runs,brief


def analyze_original_xlsb(path):
    from engineering_xlsb_reference import ReferenceWorkbookCache
    with ReferenceWorkbookCache(path) as model:
        project=model.foundation_summary()
        profiles=model.mapped_profiles()
        meta=model.summary()
    point_summary={r["CPT REFERENCE"]:r for r in project}
    analyses=[]
    for ref,profile in profiles.items():
        summary=point_summary.get(ref,{})
        elev=summary.get("Current  Level")
        if not isinstance(elev,(int,float)):
            elev=profile[0][0] if profile else None
        if elev is None:continue
        intervals,spikes=_segments(profile,elev)
        first=min((s["start_raw"] for s in intervals),default=None)
        largest=max((s["thickness_raw"] for s in intervals),default=0)
        total=sum(s["thickness_raw"] for s in intervals)
        final=max(intervals,key=lambda r:r["end_raw"],default=None)
        all_valid_depths=[float(elev)-float(point_elev) for point_elev,_,zone in profile
                          if isinstance(point_elev,(int,float))]
        tested=max((d for d in all_valid_depths if math.isfinite(d) and d>=0),default=0.0)
        analyses.append({
           "reference":ref,"easting":summary.get("Easting"),
           "northing":summary.get("Norting"),"ground_elevation":elev,
           "silt_start_m":None if final is None else final["reported_start"],
           "silt_thickness_m":0 if final is None else final["reported_thickness"],
           "sand_before_silt_m":None if final is None else final["reported_start"],
           "cumulative_silt_screen_m":total,"max_contiguous_silt_screen_m":largest,
           "first_silt_screen_m":first,"silt_layer_count":len(intervals),
           "all_intervals":intervals,"brief_exceedances":spikes,
           "qc_data_count":len(profile),
           "test_depth_m":tested,
           "settlement_mm":summary.get("Settlement (mm)"),
           "minimum_liquefaction_fos":summary.get("min. FOS"),
           "robertson_bc_kpa":summary.get("Robertson Ultimate BC [kPa]"),
           "aramco_bc_kpa":summary.get("ARAMCO Ultimate BC [kPa]"),
           "settlement_check_original":summary.get("Settlement Check"),
           "status":"REFERENCE-CACHED" if intervals else "REFERENCE-NO QUALIFYING SBT INTERVAL",
        })
    return meta,analyses,project


def export_original_project(path,folder,site_boundary=None):
    """Export original cached project results with embedded map images and QA."""
    import xlsxwriter
    import numpy as np
    from matplotlib.figure import Figure
    from engineering_maps import filter_coordinate_outliers
    meta,results,project=analyze_original_xlsb(path)
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    output=folder/"Original_XLSB_Project_Analysis.xlsx"
    wb=xlsxwriter.Workbook(str(output))
    head=wb.add_format({"bold":True,"bg_color":"#18364e","font_color":"white",
                        "border":0,"text_wrap":True})
    normal=wb.add_format({"num_format":"0.000"})
    def sheet(name,columns,values):
        ws=wb.add_worksheet(name)
        for i,col in enumerate(columns):ws.write(0,i,col,head)
        ws.set_row(0,35)
        for i,row in enumerate(values,1):
            for j,val in enumerate(row):
                if val is None:continue
                if isinstance(val,(int,float)) and math.isfinite(val):
                    ws.write_number(i,j,float(val),normal)
                else:ws.write(i,j,str(val))
        ws.freeze_panes(1,1)
        if values:ws.autofilter(0,0,len(values),len(columns)-1)
        ws.set_column(0,0,25);ws.set_column(1,max(1,len(columns)-1),19)
        return ws
    quick=[]
    for i,row in enumerate(results,1):
        quick.append((i,row["reference"],row["silt_start_m"] if row["silt_start_m"] is not None else "NO QUALIFYING SBT",
           row["silt_thickness_m"],row["sand_before_silt_m"]))
    sheet("CPT Analysis",["SI.No","CPT REFERENCE","Silt start depth after (m)",
         "silt depth (m)","Sand layer thickness before silt (m)"],quick)
    layer_rows=[]
    for r in results:
        for i,layer in enumerate(r["all_intervals"],1):
            layer_rows.append((r["reference"],i,layer["start_raw"],layer["end_raw"],
                layer["thickness_raw"],layer["reported_start"],layer["reported_end"],
                layer["reported_thickness"],",".join(map(str,layer["zone_codes"]))))
    sheet("All Silt-Screen Intervals",["CPT","Interval","Observed start","Observed end",
         "Observed thickness","Reported start","Reported end","Reported thickness",
         "Original SBT zone(s)"],layer_rows)
    columns=["CPT Reference","Easting","Northing","Ground Elevation","First silt-screen start",
         "Qualifying intervals","Cumulative SBT screen (m)","Maximum continuous SBT screen (m)",
         "Cached settlement mm","Cached minimum liquefaction FOS",
         "Cached Robertson ultimate BC (kPa)","Cached ARAMCO ultimate BC (kPa)",
         "Original settlement check","Classification source"]
    rows=[(r["reference"],r["easting"],r["northing"],r["ground_elevation"],
            r["first_silt_screen_m"],r["silt_layer_count"],r["cumulative_silt_screen_m"],
            r["max_contiguous_silt_screen_m"],r["settlement_mm"],
            r["minimum_liquefaction_fos"],r["robertson_bc_kpa"],r["aramco_bc_kpa"],
            r["settlement_check_original"],r["status"]) for r in results]
    sheet("Full Original Model",columns,rows)
    coord_candidates=[(r["reference"],r["easting"],r["northing"],r)
               for r in results if isinstance(r["easting"],(int,float)) and isinstance(r["northing"],(int,float))]
    mapped,withheld=filter_coordinate_outliers(coord_candidates)
    sheet("Coordinate QA",["CPT Reference","Source Easting","Source Northing","Status"],[
        (t[0],t[1],t[2],"WITHHELD - gross coordinate outlier; survey verification required")
        for t in withheld])
    excluded_ids={t[0] for t in withheld}
    inputs=[("Reference XLSB",meta["source"]),("Reference SHA256",meta["sha256"]),
            ("Cached project CPT",meta["cached_selected_cpt"]),
            ("Cone area ratio",meta["cone_ratio"]),("Groundwater level BGL (m)",meta["water_depth_m"]),
            ("Rolling mean above",meta["rolling_mean_above"]),
            ("Rolling mean below",meta["rolling_mean_below"]),
            ("Saved summary points",meta["cpt_summary_count"]),
            ("Gross coordinate outliers withheld",len(withheld)),
            ("Zone criterion","Source soil-behavior zones 1-4 are screened as fine-grained-like; this is not a laboratory USCS silt classification."),
            ("IMPORTANT","Values originate from original workbook CACHED results; VBA and native engineering formulas are not independently executed."),
            ("Thickness convention","Observed layer boundaries are derived from 0.01 m SBT cells; reported values use 0.1 m HALF_UP rounding. Borderline/thin layers require review.") ]
    sheet("Source Model Parameters",["Parameter","Value"],inputs)
    map_paths=[]
    maps_sheet=wb.add_worksheet("Project Maps")
    maps_sheet.set_column(0,0,3)
    maps_sheet.set_column(1,13,12)
    maps_sheet.write(0,1,"Original XLSB Project Coordinate Maps",head)
    maps_sheet.write(1,1,"Cached engineering values only; outlying survey coordinates excluded, not corrected.")
    for key,title in [("max_contiguous_silt_screen_m","Thickest fine-grained-like layer"),
                      ("cumulative_silt_screen_m","Cumulative fine-grained-like intervals"),
                      ("settlement_mm","Original raft settlement (mm)"),
                      ("minimum_liquefaction_fos","Original minimum liquefaction FOS")]:
        located=[r for r in results if isinstance(r["easting"],(int,float)) and
                  isinstance(r["northing"],(int,float)) and
                  isinstance(r[key],(int,float)) and math.isfinite(r[key]) and
                  r["reference"] not in excluded_ids]
        fig=Figure(figsize=(11,8),dpi=120)
        ax=fig.add_subplot(111)
        if located:
            sc=ax.scatter([r["easting"] for r in located],[r["northing"] for r in located],
                       c=[r[key] for r in located],cmap="viridis",s=18)
            fig.colorbar(sc,ax=ax,label=title)
        if site_boundary is not None:
            polygon=np.asarray(site_boundary,dtype=float)
            if polygon.ndim==2 and polygon.shape[1]==2 and len(polygon)>=3 and np.isfinite(polygon).all():
                closed=np.vstack([polygon,polygon[0]])
                ax.plot(closed[:,0],closed[:,1],linewidth=1.5,label="Imported site limits")
                ax.legend(fontsize=8)
        ax.set_title(title+" — ORIGINAL XLSB CACHED RESULTS (%d coordinates withheld)"%len(withheld))
        ax.set_xlabel("Project Easting");ax.set_ylabel("Project Northing")
        ax.set_aspect("equal",adjustable="datalim");ax.grid(alpha=.15)
        fig.tight_layout()
        p=folder/(key+".png");fig.savefig(p,dpi=150);map_paths.append(p)
        map_index=len(map_paths)-1
        excel_row=4+map_index*43
        maps_sheet.write(excel_row-1,1,title,head)
        maps_sheet.insert_image(excel_row,1,str(p),{"x_scale":0.34,"y_scale":0.34})
    wb.close()
    return {"workbook":output,"maps":map_paths,"source_summary":meta,
            "project_cpt_count":len(results)}

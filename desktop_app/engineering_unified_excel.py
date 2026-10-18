"""All deliverables inside ONE XLSX: project summary, raw profiles, maps, 3D,
reference data, foundation cases, source QA and optional before/after changes.

Draws into the production XlsxWriter workbook before it is closed.
No sidecar PNGs or secondary Excel workbooks are required.
"""
from __future__ import annotations
from io import BytesIO
from math import isfinite
import numpy as np
from matplotlib.figure import Figure


def _numeric(value):
    try:
        n=float(value)
        return n if isfinite(n) else None
    except (TypeError,ValueError):
        return None


def _header(wb):
    return wb.add_format({"bold":True,"font_color":"#ffffff","bg_color":"#163550",
                          "valign":"vcenter","border_color":"#385570","text_wrap":True})


def _rows(wb,name,headings,records,widths=None):
    ws=wb.add_worksheet(name)
    fmt=_header(wb)
    for col,label in enumerate(headings):ws.write(0,col,label,fmt)
    ws.set_row(0,36);ws.freeze_panes(1,1)
    ws.set_column(0,0,26)
    ws.set_column(1,len(headings)-1,19)
    for i,rec in enumerate(records,1):
        for j,val in enumerate(rec):
            if val is None:
                ws.write(i,j,"N/A — not measured")
            elif isinstance(val,(float,int)) and _numeric(val) is not None:
                ws.write_number(i,j,float(val))
            else:ws.write(i,j,str(val)[:32000])
    if records:ws.autofilter(0,0,len(records),len(headings)-1)
    if widths:
        for index,width in widths.items():ws.set_column(index,index,width)
    return ws


def _make_plan_chart(points,boundary):
    from engineering_maps import filter_coordinate_outliers
    coords=[(r["reference"],r["easting"],r["northing"],r) for r in points
            if _numeric(r.get("easting")) is not None and _numeric(r.get("northing")) is not None]
    inside,outliers=filter_coordinate_outliers(coords)
    rows=[r[3] for r in inside]
    fig=Figure(figsize=(11,7.5),dpi=110,facecolor="white")
    ax=fig.add_subplot(111)
    valid=[r for r in rows if _numeric(r.get("metric")) is not None]
    if valid:
        scatter=ax.scatter([r["easting"] for r in valid],[r["northing"] for r in valid],
              c=[r["metric"] for r in valid],cmap="viridis",s=25,edgecolors="white",
              linewidths=.3,zorder=3)
        fig.colorbar(scatter,ax=ax,pad=.02,label="Maximum observed SBT fine-grained screen (m)")
    unknown=[r for r in rows if _numeric(r.get("metric")) is None]
    if unknown:
        ax.scatter([r["easting"] for r in unknown],[r["northing"] for r in unknown],
                  marker="x",color="#b45309",label="Unknown / review")
    if boundary:
        p=np.asarray(boundary,float)
        if p.ndim==2 and p.shape[1]==2 and len(p)>=3 and np.isfinite(p).all():
            closed=np.vstack([p,p[:1]])
            ax.plot(closed[:,0],closed[:,1],color="#334155",linewidth=1.6,label="Project site limits")
    if len(valid)<=30:
        for r in valid:
            ax.annotate(r["reference"],(r["easting"],r["northing"]),xytext=(3,3),
                        textcoords="offset points",fontsize=7)
    if unknown or boundary:ax.legend(loc="lower right",fontsize=8)
    ax.set_xlabel("Survey Easting (project grid)");ax.set_ylabel("Survey Northing (project grid)")
    ax.set_aspect("equal",adjustable="datalim");ax.grid(alpha=.16)
    ax.set_title("Measured CPT points — Project-wide Ic soil-behavior screening",
                 fontsize=13,fontweight="bold")
    fig.text(.09,.02,"%d surveyed points | %d coordinate outliers withheld. No extrapolation."%
             (len(rows),len(outliers)),fontsize=8,color="#64748b")
    fig.tight_layout(rect=(0,.045,1,.98))
    return fig,outliers


def _in_memory_image(figure,dpi=135):
    stream=BytesIO()
    figure.savefig(stream,format="png",dpi=dpi,facecolor="white")
    stream.seek(0)
    return stream


def extend_project_workbook(wb,analyses,*,source_audit=None,
                           original_xlsb=None,foundation_xlsx=None,
                           site_boundary=None,comparison_result=None,
                           include_profiles=True):
    """Appends sheets and in-memory figures to existing production workbook.

    To preserve the original model, source values are labelled CACHED/IMPORTED
    and are not silently written into the native verified results.
    """
    from engineering_3d_map import site_3d_figure
    from engineering_layers import from_analysis
    from engineering_maps import filter_coordinate_outliers
    from engineering_comparison import read_summary_xlsx
    raw_profiles=[]
    points=[]
    nprofiles=0
    for a in analyses:
        md=getattr(a,"metadata",{}) or {}
        try:
            observation=from_analysis(a)
            maxlayer=observation.maximum_silt_m
            cumulative=observation.cumulative_silt_m
            unknown=observation.unknown_m
            layercount=observation.silt_count
        except Exception:
            maxlayer=cumulative=unknown=None
            layercount=0
        points.append({"reference":a.reference,"easting":_numeric(md.get("easting")),
            "northing":_numeric(md.get("northing")),
            "ground_elevation":_numeric(md.get("ground_elevation")),
            "metric":maxlayer,"cumulative":cumulative,"status":a.status,
            "silt_count":layercount,"unknown_m":unknown,
            "test_depth":_numeric(getattr(a,"test_depth_raw",None)),
            "source":str(a.source_path)})
        if include_profiles and hasattr(a,"depth"):
            fields=("depth","qc","fs","u2","qt","fr","qtn","ic")
            arrays=[np.asarray(getattr(a,f),dtype=float) for f in fields]
            valid=np.asarray(a.valid_sensor,bool)
            for i in range(len(arrays[0])):
                row=[a.reference]
                for column in arrays:
                    value=float(column[i])
                    row.append(value if isfinite(value) else "N/A — invalid measurement")
                row.extend(["VALID" if valid[i] and isfinite(arrays[7][i]) else "UNKNOWN",
                            str(a.status),str(a.source_path.name)])
                raw_profiles.append(tuple(row))
            nprofiles+=1

    _rows(wb,"CPT Coordinates",
          ["CPT Reference","Easting","Northing","Ground elevation RL","Max SBT screen thickness",
          "Cumulative SBT screen thickness","SBT layer count","Unknown depth (m)",
          "CPT test depth (m)","Status","Original source"],[
              (p["reference"],p["easting"],p["northing"],p["ground_elevation"],
               p["metric"],p["cumulative"],p["silt_count"],p["unknown_m"],p["test_depth"],
               p["status"],p["source"]) for p in points],{10:62})

    source_profile={}
    if original_xlsb is not None:
        from engineering_reference_project import analyze_original_xlsb
        original_model,original_profiles,foundation_rows=analyze_original_xlsb(original_xlsb)
        for p in original_profiles:
            source_profile[p["reference"]]=p
        _rows(wb,"Original XLSB Foundation",
              ["CPT reference","Easting","Northing","Ground elevation",
               "Raft settlement mm (cached)","Minimum liquefaction FOS (cached)",
               "Silt-screen start","Silt-screen thickness","Max layer thickness",
               "Cumulative fine-grained-like thickness","Original source status"],[
                   (r["reference"],r["easting"],r["northing"],r["ground_elevation"],
                    r["settlement_mm"],r["minimum_liquefaction_fos"],
                    r["silt_start_m"],r["silt_thickness_m"],
                    r["max_contiguous_silt_screen_m"],r["cumulative_silt_screen_m"],r["status"])
                   for r in original_profiles])
        import hashlib
        _rows(wb,"Original Source Settings",["Parameter","Saved Excel value"],[
            (key,str(value)) for key,value in original_model.items()])
        from engineering_reference_parity import compare_engine_to_reference
        checks=compare_engine_to_reference(analyses,original_profiles,
               water_table=(analyses[0].metadata or {}).get("analysis_water_table_bgl_m") if analyses else None,
               reference_settings=original_model)
        _rows(wb,"Native vs Source XLSB",
              ["CPT","Comparison status","Native start","Native thickness","Original start",
               "Original thickness","Start difference","Thickness difference","Coordinate offset","Reason"],[
              (r["reference"],r["status"],r["native_start"],r["native_thickness"],
               r["reference_start"],r["reference_thickness"],r["difference_start"],
               r["difference_thickness"],r["point_offset"],r["notes"]) for r in checks],{9:85})

    if foundation_xlsx is not None:
        external=read_summary_xlsx(foundation_xlsx)
        for foundation,tab in (("RAFT","Raft Foundation"),("ISOLATED","Isolated Foundation")):
            selected=[r for r in external if r.foundation==foundation]
            _rows(wb,tab,["CPT","Easting","Northing","Settlement mm (source)",
                  "Minimum FOS (source)","Footing width","Length/width ratio","Source review notes"],[
                   (r.reference,r.east,r.north,r.metrics.get("settlement_mm"),
                    r.metrics.get("fos"),r.footing_width_m,r.footing_lb_ratio,
                    "IMPORTED SOURCE RESULT — verify original design acceptance") for r in selected])

    if comparison_result:
        matched=comparison_result.get("matched",[])
        _rows(wb,"Pre Post Matched Changes",
              ["PRE reference","POST reference","Foundation","Metric","PRE","POST","Delta",
               "Percentage change","Matching method","Coordinate offset"],[
                 (entry["pre"].reference,entry["post"].reference,entry["pre"].foundation,metric,
                  val.get("pre"),val.get("post"),val.get("delta"),val.get("percent"),
                  entry.get("matching_method"),entry.get("distance"))
                 for entry in matched for metric,val in entry["metrics"].items()])
        _rows(wb,"Pre Post Matching QA",["Status","Reference","Details"],[
            ("UNMATCHED PRE",r.reference,"No approved pair")
            for r in comparison_result.get("unmatched_pre",[])]+[
            ("UNMATCHED POST",r.reference,"No approved pair")
            for r in comparison_result.get("unmatched_post",[])]+[
            ("AMBIGUOUS",entry.reference,", ".join(x.reference for x in options))
            for entry,options in comparison_result.get("ambiguous",[])],{2:78})

    if include_profiles:
        _rows(wb,"CPT Measurements",
            ["CPT","Depth BGL m","qc MPa","fs MPa","u2 MPa","qt MPa","Fr %",
             "Qtn","Ic","Data validity","Final status","Source"],raw_profiles,{11:60})

    selected_original=bool(source_profile)
    if selected_original:
        plot_points=[{
            "reference":x["reference"],"easting":x["easting"],"northing":x["northing"],
            "ground_elevation":x["ground_elevation"],
            "metric":x["max_contiguous_silt_screen_m"],
            "all_intervals":x["all_intervals"],
            "test_depth_m":max((v["end_raw"] for v in x["all_intervals"]),default=0),
            "status":"CACHED SOURCE SBT"} for x in source_profile.values()]
    else:plot_points=points
    coords=[(p["reference"],p["easting"],p["northing"],p)
            for p in plot_points if _numeric(p.get("easting")) is not None and
                                      _numeric(p.get("northing")) is not None]
    _,withheld=filter_coordinate_outliers(coords)
    _rows(wb,"Survey Coordinate QA",["CPT","Easting","Northing","Reason"],[
        (r[0],r[1],r[2],"Withheld gross coordinate outlier (verify original survey)") for r in withheld])

    visual=wb.add_worksheet("Project Maps")
    visual.set_column(0,0,2);visual.set_column(1,13,12)
    fmt=_header(wb)
    visual.merge_range("B2:N2","CPT ENGINEERING | SITE PLAN & 3D SUBSURFACE",fmt)
    visual.set_row(1,32)
    visual.write("B3","2D survey plan + measured source screening values. 3D depicts vertical observed/cached CPT zones, NOT a continuous interpolated surface.")
    fig,outliers=_make_plan_chart(plot_points,site_boundary)
    visual.insert_image("B5","measured_site_plan.png",{
        "image_data":_in_memory_image(fig), "x_scale":.49,"y_scale":.49})
    fig3,stats=site_3d_figure(source_profile.values() if selected_original else analyses,site_boundary)
    visual.insert_image("B50","observed_3d_cpt.png",{
        "image_data":_in_memory_image(fig3),"x_scale":.49,"y_scale":.49})
    visual.write("B92",f"Grounded surveyed CPT columns: {stats['plotted']} | Gross coordinate exceptions: {len(withheld)}")
    visual.write("B93","Maps are based only on observed/cached input; original workbook formulas and project soil classification need engineering approval.")

    summary=wb.add_worksheet("Project Dashboard")
    summary.set_column("A:A",38);summary.set_column("B:B",34)
    summary.set_column("D:N",12)
    summary.merge_range("A1:N2","CPT PROJECT ENGINEERING OVERVIEW",fmt)
    summaries=[
        ("CPTs in current analysis",len(analyses)),
        ("CPTs with recorded source coordinates",len(coords)),
        ("Coordinate exceptions",len(withheld)),
        ("Original source CPT profiles",len(source_profile)),
        ("Native verified CPTs",sum(a.status=="VERIFIED" for a in analyses)),
        ("Native no qualifying silt",sum(a.status=="NO SILT" for a in analyses)),
        ("Native engineering REVIEW",sum(a.status=="REVIEW" for a in analyses)),
        ("Maximum observed continuous screen (m)",max((x["metric"] or 0 for x in plot_points),default=0)),
        ("Source footing workbook",str(foundation_xlsx or "Not provided")),
        ("Original XLSB reference",str(original_xlsb or "Not provided")),
        ("Maps","See embedded 2D and 3D images in Project Maps"),
        ("Data points",len(raw_profiles)),
    ]
    for i,(label,value) in enumerate(summaries,4):
        summary.write(i,0,label)
        if isinstance(value,(int,float)):summary.write_number(i,1,value)
        else:summary.write(i,1,value)
    summary.write("A20","SOURCE SAFETY NOTE",fmt)
    summary.write("B20","SBT Ic and cached source model values are not a substitute for approved geotechnical design. 'NO SILT' means no sustained qualifying Ic-screen interval, not proven absence of fines.")
    return {"cpt_data_rows":len(raw_profiles),"project_coords":len(coords),
            "coordinate_outliers":len(withheld),"source_points":len(source_profile)}

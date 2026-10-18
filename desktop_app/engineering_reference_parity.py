"""Numerical/source-result parity QA between CPT engine and original XLSB caches.

This compares *saved original soil behavior ZONES* to native Ic-derived project
intervals. It does not declare either source geotechnically certified.
"""
from pathlib import Path
import math
import re


def _alias(value):
    ref=str(value or "").strip().upper().replace(".100","-100")
    return re.sub(r"(CPT-A\d+-)B(?=\d+-100)",r"\1",ref)


def _xy(metadata):
    try:
        x=float(metadata["easting"]);y=float(metadata["northing"])
        return (x,y) if math.isfinite(x) and math.isfinite(y) else None
    except (AttributeError,TypeError,ValueError,KeyError):
        return None


def compare_engine_to_reference(analyses,reference_rows,*,tolerance_m=.05,
                                xy_tolerance_m=.5,water_table=None,
                                reference_settings=None):
    reference_rows=list(reference_rows)
    out=[]
    for a in analyses:
        source_xy=_xy(getattr(a,"metadata",{}) or {})
        candidates=[]
        for source in reference_rows:
            if _alias(source["reference"])!=_alias(a.reference):continue
            target_xy=_xy({"easting":source.get("easting"),"northing":source.get("northing")})
            if source_xy is None or target_xy is None:continue
            difference=math.hypot(source_xy[0]-target_xy[0],source_xy[1]-target_xy[1])
            if difference<=xy_tolerance_m:candidates.append((difference,source))
        if len(candidates)!=1:
            out.append({"reference":a.reference,"status":"REVIEW - "+("MISSING" if not candidates else "AMBIGUOUS")+" SOURCE MATCH",
                        "native_start":getattr(getattr(a,"final_interval",None),"start",None),
                        "native_thickness":getattr(getattr(a,"final_interval",None),"thickness",None),
                        "reference_start":None,"reference_thickness":None,
                        "difference_start":None,"difference_thickness":None,
                        "point_offset":None,"notes":"Confirm reference and measured coordinates."})
            continue
        xy_distance,ref=candidates[0]
        native=getattr(a,"final_interval",None)
        nstart=getattr(native,"start",None)
        nthick=getattr(native,"thickness",None)
        rstart=ref.get("silt_start_m");rthick=ref.get("silt_thickness_m")
        if (native is None and a.status=="NO SILT" and rstart is None):
            status="AGREE: NO QUALIFYING INTERVAL"
        elif nstart is None or nthick is None or rstart is None or rthick is None:
            status="REVIEW - INCOMPLETE MEASUREMENT"
        else:
            status="AGREE" if (abs(nstart-rstart)<=tolerance_m and
                             abs(nthick-rthick)<=tolerance_m) else "MISMATCH - ENGINEERING REVIEW"
        notes=[]
        if getattr(a,"status","")=="REVIEW":notes.append("Native analysis marked REVIEW.")
        if reference_settings:
            try:
                wtref=float(reference_settings.get("water_depth_m"))
                if water_table is not None and abs(wtref-float(water_table))>.05:
                    notes.append("Groundwater discrepancy: XLSB %.2fm vs native %.2fm" % (wtref,float(water_table)))
            except (TypeError,ValueError):pass
            try:
                ar=float((getattr(a,"metadata",{}) or {}).get("area_ratio"))
                area_ref=float(reference_settings.get("cone_ratio"))
                if abs(ar-area_ref)>.001:
                    notes.append("Cone area-ratio discrepancy: XLSB %.3f vs raw %.3f"%(area_ref,ar))
            except (TypeError,ValueError):pass
        out.append({"reference":a.reference,"status":status,
                    "native_start":nstart,"native_thickness":nthick,
                    "reference_start":rstart,"reference_thickness":rthick,
                    "difference_start":None if nstart is None or rstart is None else nstart-rstart,
                    "difference_thickness":None if nthick is None or rthick is None else nthick-rthick,
                    "point_offset":xy_distance,"notes":"; ".join(notes) or
                    "Original XLSB zone classification vs independently derived Ic threshold."})
    return out


def export_parity_workbook(rows,path,source_description="Original XLSB saved SBT zones"):
    import xlsxwriter
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    wb=xlsxwriter.Workbook(str(path))
    sheet=wb.add_worksheet("Native vs Original")
    header=wb.add_format({"bg_color":"#16334e","font_color":"white","bold":True,"text_wrap":True})
    warning=wb.add_format({"bg_color":"#fff4dd","font_color":"#92400e"})
    names=["CPT Reference","Comparison status","Native silt start (m)",
           "Native thickness (m)","XLSB zone start (m)","XLSB zone thickness (m)",
           "Start difference (m)","Thickness difference (m)","Coordinate offset (m)",
           "Processing / engineering notes"]
    for c,n in enumerate(names):sheet.write(0,c,n,header)
    for i,v in enumerate(rows,1):
        vals=[v["reference"],v["status"],v["native_start"],v["native_thickness"],
              v["reference_start"],v["reference_thickness"],v["difference_start"],
              v["difference_thickness"],v["point_offset"],v["notes"]]
        for j,x in enumerate(vals):
            if x is None:continue
            if isinstance(x,(int,float)) and math.isfinite(x):
                sheet.write_number(i,j,float(x))
            else:sheet.write(i,j,str(x),warning if j==1 and "MISMATCH" in str(x) else None)
    sheet.set_column(0,0,25);sheet.set_column(1,1,34);sheet.set_column(2,8,20)
    sheet.set_column(9,9,88);sheet.set_row(0,42)
    sheet.freeze_panes(1,2)
    if rows:sheet.autofilter(0,0,len(rows),len(names)-1)
    summary=wb.add_worksheet("Reference Parity QA")
    refs=[
       ("Reference source",source_description),
       ("Scope","Saved source XLSB integer SBT zones vs native direct GEF/PDF Ic."),
       ("IMPORTANT","An original cache match is not proof of correct or approved geotechnical engineering formulas."),
       ("Groundwater and cone ratio","Source and native parameters are not silently overwritten; differences listed per CPT."),
       ("Total CPTs compared",len(rows)),
       ("Agree",sum(r["status"].startswith("AGREE") for r in rows)),
       ("Mismatched",sum("MISMATCH" in r["status"] for r in rows)),
       ("Unmatched/uncertain",sum("REVIEW" in r["status"] for r in rows)),
    ]
    for i,(name,value) in enumerate(refs):
        summary.write(i,0,name,header if i==0 else None)
        summary.write(i,1,value)
    summary.set_column(0,0,26);summary.set_column(1,1,110)
    wb.close()
    return path


def compare_against_xlsb(analyses,xlsb_path,output_path,*,water_table=None):
    from engineering_reference_project import analyze_original_xlsb
    model,reference,original=analyze_original_xlsb(xlsb_path)
    rows=compare_engine_to_reference(analyses,reference,water_table=water_table,
                                     reference_settings=model)
    output=export_parity_workbook(rows,output_path,str(xlsb_path))
    return output,rows

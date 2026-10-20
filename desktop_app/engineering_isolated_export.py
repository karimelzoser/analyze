"""Append independently auditable, provisional isolated-footing results to ONE XLSX.

Imported reference results and native 2:1 strain-screening estimates are never
silently merged into a single apparently approved settlement column.
"""
from __future__ import annotations

from engineering_isolated_settlement import IsolatedInputs,attach_isolated_estimates


def append_isolated_sheets(workbook,analyses,source_points,inputs=None):
    cfg=inputs or IsolatedInputs()
    cfg.validate()
    estimates=attach_isolated_estimates(analyses,source_points,cfg)
    sources=[p for p in source_points if p.foundation=="ISOLATED"]
    results=workbook.add_worksheet("Isolated Settlement Results")
    headings=[
        "CPT reference","Source Easting","Source Northing","Source settlement (mm)",
        "Original settlement check","Original FOS","CPT screened settlement (mm)",
        "Measured partial strain settlement (mm)","Measured depth coverage (%)",
        "Screening result status","Screening - Source (mm)",
        "40 mm source-flag QA","Design acceptance","Evidence/limitations",
        "Stress-weighted coverage (%)","Unobserved influence depth (m)",
        "Unobserved BGL intervals","Last measured qt depth (m)"]
    head=workbook.add_format({"bold":True,"font_color":"white","bg_color":"#173b57",
                              "text_wrap":True,"valign":"vcenter"})
    good=workbook.add_format({"num_format":"0.000","border":1,"border_color":"#e2e8f0"})
    warn=workbook.add_format({"bg_color":"#fff5e9","font_color":"#92400e",
                              "text_wrap":True})
    for col,title in enumerate(headings):results.write(0,col,title,head)
    results.set_row(0,48);results.freeze_panes(1,3)
    results.set_column(0,0,27);results.set_column(1,11,20)
    results.set_column(12,12,34);results.set_column(13,13,93)
    results.set_column(14,15,25);results.set_column(16,16,70)
    results.set_column(17,17,25)
    for i,(source,estimate) in enumerate(zip(sources,estimates),1):
        refvalue=source.metrics.get("settlement_mm")
        old_flag=str(source.reported_settlement_check or "").strip().upper()
        inconsistency=(refvalue is not None and refvalue>40 and old_flag=="PASS")
        qa=("CONFLICT: source says Pass but saved result exceeds 40 mm"
            if inconsistency else "MISSING original settlement"
            if refvalue is None else "Confirm project approved settlement limit")
        row=[source.reference,source.east,source.north,refvalue,
             source.reported_settlement_check,source.metrics.get("fos"),
             estimate.calculated_settlement_mm,estimate.observed_settlement_mm,
             estimate.coverage_percent,estimate.status,estimate.source_delta_mm,
             qa,estimate.criterion_status,estimate.warning,
             estimate.stress_coverage_percent,estimate.missing_depth_m,
             "; ".join("%.2f–%.2f m"%(a,b) for a,b in estimate.missing_intervals_bgl or []),
             estimate.last_valid_depth_m]
        for j,val in enumerate(row):
            if val is None:
                results.write(i,j,"NOT AVAILABLE",warn)
            elif isinstance(val,(float,int)):
                results.write_number(i,j,val,good)
            else:
                results.write(i,j,str(val),warn if j in (9,11,12,13) else None)
    # Append all raw CPTs that are absent from the uploaded reference summary.
    # A recent A2 GEF campaign may have no overlap with the older A1/A2 source
    # workbook. New calculations must still be visible in this same table.
    by_ref={str(getattr(a,"reference","")):a for a in analyses}
    for i,estimate in enumerate(estimates[len(sources):],len(sources)+1):
        raw=by_ref.get(estimate.reference)
        md=(getattr(raw,"metadata",{}) or {}) if raw is not None else {}
        values=[estimate.reference,md.get("easting"),md.get("northing"),
                "NO MATCHING SOURCE RECORD","NOT REPORTED",None,
                estimate.calculated_settlement_mm,estimate.observed_settlement_mm,
                estimate.coverage_percent,estimate.status,None,
                "NEW RAW CPT — NOT PRESENT IN REFERENCE SUMMARY",
                estimate.criterion_status,estimate.warning,
                estimate.stress_coverage_percent,estimate.missing_depth_m,
                "; ".join("%.2f–%.2f m"%(a,b) for a,b in estimate.missing_intervals_bgl or []),
                estimate.last_valid_depth_m]
        for j,val in enumerate(values):
            if val is None:results.write(i,j,"NOT AVAILABLE",warn)
            elif isinstance(val,(float,int)):results.write_number(i,j,val,good)
            else:results.write(i,j,str(val),warn if j in (3,9,11,12,13) else None)
    if estimates:results.autofilter(0,0,len(estimates),len(headings)-1)
    # Independent coverage QA for operators: a 90% depth threshold does not
    # mean 90% of the engineering stress influence has been observed.
    coverage_sheet=workbook.add_worksheet("Isolated Coverage QA")
    coverage_headers=["CPT","Status","BGL influence start (m)","BGL influence end (m)",
        "Observed depth coverage (%)","Stress-weighted observed coverage (%)",
        "Unobserved depth (m)","Unobserved BGL intervals","Last observed depth (m)",
        "Source/reference status"]
    for j,title in enumerate(coverage_headers):coverage_sheet.write(0,j,title,head)
    coverage_sheet.freeze_panes(1,1)
    coverage_sheet.set_column(0,0,27)
    coverage_sheet.set_column(1,1,39)
    coverage_sheet.set_column(2,6,23)
    coverage_sheet.set_column(7,7,78)
    coverage_sheet.set_column(8,9,25)
    for rowno,item in enumerate(estimates,1):
        v=[item.reference,item.status,item.influence_start_bgl_m,
           item.influence_end_bgl_m,item.coverage_percent,
           item.stress_coverage_percent,item.missing_depth_m,
           "; ".join("%.2f–%.2f m"%(a,b) for a,b in item.missing_intervals_bgl or []) or "NONE",
           item.last_valid_depth_m,
           "MATCHED ORIGINAL" if item.source_settlement_mm is not None else "NO APPROVED REFERENCE VALUE"]
        for j,value in enumerate(v):
            if value is None:coverage_sheet.write(rowno,j,"NOT MEASURED",warn)
            elif isinstance(value,(float,int)):coverage_sheet.write_number(rowno,j,float(value),good)
            else:coverage_sheet.write(rowno,j,str(value),warn if j in (1,7,9) else None)
    if estimates:coverage_sheet.autofilter(0,0,len(estimates),len(coverage_headers)-1)
    trace=workbook.add_worksheet("Isolated Strain Integration")
    for j,label in enumerate(["CPT","Depth BGL (m)","qt (MPa)","Stress increment (kPa)",
            "Modulus M (kPa)","Strain (-)","Incremental settlement (mm)","Result class"]):
        trace.write(0,j,label,head)
    trace.freeze_panes(1,1)
    trace.set_column(0,0,26);trace.set_column(1,6,22);trace.set_column(7,7,42)
    n=1
    for r in estimates:
        for step in r.integration:
            trace.write(n,0,r.reference)
            for col,key in enumerate(("depth_bgl_m","qt_mpa","stress_kpa",
                   "modulus_kpa","strain","incremental_settlement_mm"),1):
                trace.write_number(n,col,step[key],good)
            trace.write(n,7,r.status);n+=1
    if n>1:trace.autofilter(0,0,n-1,7)
    settings=workbook.add_worksheet("Isolated Model QA")
    settings.set_column(0,0,46);settings.set_column(1,1,108)
    inputs=[
      ("Width B (m)",cfg.width_m),("Length L (m)",cfg.length_m),
      ("Applied NET pressure (kPa)",cfg.net_pressure_kpa),("Footing embedment (m)",cfg.embedment_m),
      ("Influence depth = B * multiplier",cfg.influence_b),
      ("Provisional constrained modulus factor M/qt",cfg.qc_modulus_factor),
      ("Maximum measured CPT depth gap (m)",cfg.max_sample_gap_m),
      ("Integration depth step (m)",cfg.step_m),("Required valid influence coverage",cfg.min_coverage),
      ("Source isolated records",len(sources)),
      ("Saved source settlement values",sum(p.metrics.get("settlement_mm") is not None for p in sources)),
      ("Absent source settlement values",sum(p.metrics.get("settlement_mm") is None for p in sources)),
      ("CPT provisional estimates with threshold coverage",sum(r.calculated_settlement_mm is not None for r in estimates)),
      ("Incomplete due to stress-weighted depth coverage",
       sum(r.status=="INCOMPLETE — STRESS-WEIGHTED DEPTH COVERAGE" for r in estimates)),
      ("Missing influence BGL intervals (total across records)",
       sum(len(r.missing_intervals_bgl or []) for r in estimates)),
      ("Source check flags contradicting 40 mm limit",
       sum(p.metrics.get("settlement_mm") is not None and
           p.metrics["settlement_mm"]>40 and
           str(p.reported_settlement_check or "").strip().upper()=="PASS" for p in sources)),
      ("ENGINEERING CLASSIFICATION","CPT modulus empirical correlation is not calibrated/approved. NO new design PASS/FAIL is issued."),
      ("Missing or unknown qc/qt","Unknown strata remain uncomputed; no extrapolation into missing influence zone."),
      ("Calculation method","2:1 rectangular stress spread integrated with M(z)=alpha_M * qt(z) * 1000kPa."),
      ("This method is NOT","An independently validated match to the original XLSB or a substitute for licensed design checks."),
    ]
    for i,(name,value) in enumerate(inputs):
        settings.write(i,0,name,head if i==0 else None)
        if isinstance(value,(float,int)):settings.write_number(i,1,value)
        else:settings.write(i,1,str(value))
    return {"source_count":len(sources),
            "new_raw_without_source":len(estimates)-len(sources),
            "computed":sum(r.calculated_settlement_mm is not None for r in estimates),
            "incomplete":sum(r.calculated_settlement_mm is None for r in estimates),
            "trace_rows":n-1,"estimates":estimates}

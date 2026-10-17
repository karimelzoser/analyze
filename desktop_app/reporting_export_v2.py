from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import xlsxwriter

from cpt_core import CPTAnalysis, natural_ref_key
from reporting_pro import FULL_HEADERS, _full_row, analysis_record


def export_excel(
    analyses: Iterable[CPTAnalysis],
    output_path: str | Path,
    errors: Sequence[tuple[str, str]] | None = None,
    source_audit: Sequence[dict] | None = None,
) -> Path:
    """Export the production workbook.

    ``analyses`` contains one authoritative project result per CPT location.
    ``source_audit`` may contain every physical GEF/GFF/PDF revision considered
    during source selection so project rows stay clean without losing traceability.
    """
    analyses = sorted(list(analyses), key=lambda a: natural_ref_key(a.reference))
    recs = [analysis_record(a) for a in analyses]
    errors = list(errors or [])
    source_audit = list(source_audit or [])
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    wb = xlsxwriter.Workbook(str(p))
    hdr = wb.add_format({
        "bold": True, "font_color": "#FFFFFF", "bg_color": "#0B1F33", "border": 1,
        "border_color": "#38536A", "align": "center", "valign": "vcenter", "text_wrap": True,
    })
    text = wb.add_format({"border": 1, "border_color": "#D9E2EC"})
    wrap = wb.add_format({"border": 1, "border_color": "#D9E2EC", "text_wrap": True, "valign": "top"})
    center = wb.add_format({"border": 1, "border_color": "#D9E2EC", "align": "center"})
    num = wb.add_format({"border": 1, "border_color": "#D9E2EC", "align": "center", "num_format": "0.00"})
    num3 = wb.add_format({"border": 1, "border_color": "#D9E2EC", "align": "center", "num_format": "0.000"})
    label = wb.add_format({"bold": True, "bg_color": "#EAF0F7", "border": 1, "border_color": "#D9E2EC"})
    val = wb.add_format({"border": 1, "border_color": "#D9E2EC", "align": "center", "num_format": "0.00"})
    green = wb.add_format({"bg_color": "#DCFCE7", "font_color": "#166534"})
    amber = wb.add_format({"bg_color": "#FEF3C7", "font_color": "#92400E"})
    blue = wb.add_format({"bg_color": "#E0F2FE", "font_color": "#075985"})
    red = wb.add_format({"bg_color": "#FEE2E2", "font_color": "#991B1B"})
    grey = wb.add_format({"bg_color": "#F1F5F9", "font_color": "#475569"})

    # 1) Quick project sheet - exactly one row per selected CPT family.
    ws = wb.add_worksheet("CPT Analysis")
    simple = [
        "SI.No", "CPT REFERENCE", "Silt start depth after (m)",
        "silt depth (m)", "Sand layer thickness before silt (m)",
    ]
    for c, h in enumerate(simple):
        ws.write(0, c, h, hdr)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, max(1, len(analyses)), 4)
    ws.set_row(0, 36)
    ws.set_column(0, 0, 9)
    ws.set_column(1, 1, 28)
    ws.set_column(2, 4, 28)
    for i, (a, r) in enumerate(zip(analyses, recs), 1):
        ws.write_number(i, 0, i, center)
        ws.write(i, 1, a.reference, text)
        if a.status == "NO SILT":
            ws.write(i, 2, "NO SILT", center)
            ws.write_number(i, 3, 0, num)
        elif a.final_interval:
            ws.write_number(i, 2, a.final_interval.start, num)
            ws.write_number(i, 3, a.final_interval.thickness, num)
        else:
            ws.write(i, 2, "REVIEW", center)
            ws.write_blank(i, 3, None, num)
        if isinstance(r["sand"], (int, float)) and np.isfinite(float(r["sand"])):
            ws.write_number(i, 4, float(r["sand"]), num)
        else:
            ws.write(i, 4, "REVIEW", center)
    if analyses:
        ws.conditional_format(1, 2, len(analyses), 2, {"type": "text", "criteria": "containing", "value": "NO SILT", "format": blue})
        ws.conditional_format(1, 2, len(analyses), 2, {"type": "text", "criteria": "containing", "value": "REVIEW", "format": amber})
        ws.conditional_format(1, 3, len(analyses), 3, {"type": "data_bar", "bar_color": "#7C3AED"})
        ws.conditional_format(1, 4, len(analyses), 4, {"type": "data_bar", "bar_color": "#2563EB"})

    # 2) Full engineering data for selected project sources.
    wd = wb.add_worksheet("Full Analysis")
    for c, h in enumerate(FULL_HEADERS):
        wd.write(0, c, h, hdr)
    wd.freeze_panes(1, 2)
    wd.autofilter(0, 0, max(1, len(analyses)), len(FULL_HEADERS)-1)
    wd.set_row(0, 40)
    wd.set_column(0, 0, 8)
    wd.set_column(1, 4, 22)
    wd.set_column(5, 10, 22)
    wd.set_column(11, 47, 18)
    wd.set_column(48, 48, 60)
    for i, (a, r) in enumerate(zip(analyses, recs), 1):
        row = _full_row(i, a, r)
        for c, v in enumerate(row):
            if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool) and np.isfinite(float(v)):
                wd.write_number(i, c, float(v), num3 if c in {26,27,28,29,30,31,32,34,36,37,38,39,40,44} else num)
            elif v is None:
                wd.write_blank(i, c, None, center)
            else:
                wd.write(i, c, str(v), text if c in {1,2,3,4,5,6,7,8,9,10,35,42,43,45,46,47,48} else center)
    if analyses:
        wd.conditional_format(1, 47, len(analyses), 47, {"type": "text", "criteria": "containing", "value": "VERIFIED", "format": green})
        wd.conditional_format(1, 47, len(analyses), 47, {"type": "text", "criteria": "containing", "value": "NO SILT", "format": blue})
        wd.conditional_format(1, 47, len(analyses), 47, {"type": "text", "criteria": "containing", "value": "REVIEW", "format": amber})
        wd.conditional_format(1, 25, len(analyses), 25, {"type": "data_bar", "bar_color": "#7C3AED"})

    # 3) Every detected qualifying interval from the selected project source.
    wi = wb.add_worksheet("Detected Intervals")
    ih = ["CPT REFERENCE", "Interval No.", "Raw Start (m)", "Raw End (m)", "Raw Thickness (m)", "Selected"]
    for c, h in enumerate(ih):
        wi.write(0, c, h, hdr)
    rr = 1
    for a in analyses:
        for j, (s, e) in enumerate(a.all_intervals, 1):
            wi.write(rr, 0, a.reference, text)
            wi.write_number(rr, 1, j, center)
            wi.write_number(rr, 2, s, num3)
            wi.write_number(rr, 3, e, num3)
            wi.write_number(rr, 4, max(0, e-s), num3)
            wi.write(rr, 5, "YES" if a.final_interval and j == len(a.all_intervals) else "NO", center)
            rr += 1
    wi.set_column(0, 0, 28)
    wi.set_column(1, 5, 18)
    wi.freeze_panes(1, 0)

    # 4) Project KPIs and rankings.
    sm = wb.add_worksheet("Summary")
    verified = [r for r in recs if r["status"] == "VERIFIED" and r["thickness"] is not None]
    no_silt = [r for r in recs if r["status"] == "NO SILT"]
    reviews = [r for r in recs if r["status"] == "REVIEW"]
    mx = max([r["thickness"] for r in verified], default=None)
    mxrefs = [r["reference"] for r in verified if mx is not None and abs(r["thickness"]-mx) < 1e-9]
    mn = min([r["thickness"] for r in verified], default=None)
    avg = float(np.mean([r["thickness"] for r in verified])) if verified else None
    sands = [r["sand"] for r in recs if isinstance(r["sand"], (int, float))]
    starts = [r for r in verified if isinstance(r["start_num"], (int, float))]
    shallow = min([r["start_num"] for r in starts], default=None)
    deep = max([r["start_num"] for r in starts], default=None)

    selected_audit = [r for r in source_audit if str(r.get("selected", "")).upper() == "YES"]
    fallback_count = sum("selected highest conclusive revision" in str(r.get("selection_reason", "")).lower() for r in selected_audit)
    superseded_count = max(0, len(source_audit) - len(selected_audit))
    source_review_count = sum(str(r.get("status", "")).upper() == "REVIEW" for r in source_audit)

    metrics = [
        ("Unique project CPTs", len(recs)),
        ("Physical input sources", len(source_audit) if source_audit else len(recs)),
        ("Revision / duplicate sources retained in audit", superseded_count),
        ("Selected fallback revisions", fallback_count),
        ("Physical source files marked REVIEW", source_review_count),
        ("Verified silt CPTs", len(verified)),
        ("NO SILT CPTs", len(no_silt)),
        ("Final project REVIEW CPTs", len(reviews)),
        ("Processing errors", len(errors)),
        ("Maximum silt thickness (m)", mx),
        ("CPT(s) at maximum", ", ".join(mxrefs)),
        ("Minimum silt thickness (m)", mn),
        ("Average silt thickness (m)", avg),
        ("Shallowest silt start (m)", shallow),
        ("CPT(s) shallowest", ", ".join(r["reference"] for r in starts if shallow is not None and abs(r["start_num"]-shallow) < 1e-9)),
        ("Deepest silt start (m)", deep),
        ("CPT(s) deepest", ", ".join(r["reference"] for r in starts if deep is not None and abs(r["start_num"]-deep) < 1e-9)),
        ("Maximum sand thickness before silt (m)", max(sands) if sands else None),
        ("Average sand thickness before silt (m)", float(np.mean(sands)) if sands else None),
    ]
    for c, h in enumerate(["Project KPI", "Value"]):
        sm.write(0, c, h, hdr)
    for i, (k, v) in enumerate(metrics, 1):
        sm.write(i, 0, k, label)
        if isinstance(v, (int, float)) and v is not None:
            sm.write_number(i, 1, float(v), val)
        else:
            sm.write(i, 1, "" if v is None else str(v), center)
    sm.set_column(0, 0, 46)
    sm.set_column(1, 1, 70)

    top = sorted(verified, key=lambda r: r["thickness"], reverse=True)[:25]
    base = len(metrics) + 3
    sm.write(base, 0, "Top silt thickness CPTs", hdr)
    sm.write(base, 1, "Thickness (m)", hdr)
    for j, r in enumerate(top, base+1):
        sm.write(j, 0, r["reference"], text)
        sm.write_number(j, 1, r["thickness"], num)

    # 5) Printable project charts, based only on authoritative project rows.
    ch = wb.add_worksheet("Charts")
    ch.write(0, 0, "PROJECT ANALYSIS CHARTS", hdr)
    ch.set_column(0, 0, 2)
    ch.set_column(1, 20, 12)
    if analyses:
        n = len(analyses)
        cats = ["Full Analysis", 1, 1, n, 1]
        chart1 = wb.add_chart({"type": "column"})
        chart1.add_series({"name": "Sand before silt", "categories": cats, "values": ["Full Analysis", 1, 20, n, 20], "fill": {"color": "#60A5FA"}})
        chart1.add_series({"name": "Silt thickness", "categories": cats, "values": ["Full Analysis", 1, 25, n, 25], "fill": {"color": "#7C3AED"}})
        chart1.set_title({"name": "Sand and Silt Thickness by CPT"})
        chart1.set_y_axis({"name": "Thickness (m)"})
        chart1.set_x_axis({"name": "CPT Reference"})
        chart1.set_legend({"position": "bottom"})
        chart1.set_size({"width": 900, "height": 430})
        ch.insert_chart("B3", chart1)

        chart2 = wb.add_chart({"type": "column", "subtype": "stacked"})
        chart2.add_series({"name": "Sand / overlying layer", "categories": cats, "values": ["Full Analysis", 1, 20, n, 20], "fill": {"color": "#F2C94C"}})
        chart2.add_series({"name": "Terminal silt layer", "categories": cats, "values": ["Full Analysis", 1, 25, n, 25], "fill": {"color": "#4F86C6"}})
        chart2.set_title({"name": "Stacked Layer Thickness"})
        chart2.set_y_axis({"name": "Thickness (m)"})
        chart2.set_legend({"position": "bottom"})
        chart2.set_size({"width": 900, "height": 430})
        ch.insert_chart("B25", chart2)

        chart3 = wb.add_chart({"type": "line"})
        chart3.add_series({"name": "Silt start", "categories": cats, "values": ["Full Analysis", 1, 21, n, 21], "line": {"color": "#D97706"}})
        chart3.add_series({"name": "Silt end", "categories": cats, "values": ["Full Analysis", 1, 23, n, 23], "line": {"color": "#7C3AED"}})
        chart3.add_series({"name": "Test depth", "categories": cats, "values": ["Full Analysis", 1, 18, n, 18], "line": {"color": "#475569"}})
        chart3.set_title({"name": "Silt Start / End / Test Depth"})
        chart3.set_y_axis({"name": "Depth BGL (m)", "reverse": True})
        chart3.set_legend({"position": "bottom"})
        chart3.set_size({"width": 900, "height": 430})
        ch.insert_chart("B47", chart3)

        if top:
            chart4 = wb.add_chart({"type": "bar"})
            chart4.add_series({
                "name": "Silt thickness",
                "categories": ["Summary", base+1, 0, base+len(top), 0],
                "values": ["Summary", base+1, 1, base+len(top), 1],
                "fill": {"color": "#7C3AED"},
            })
            chart4.set_title({"name": "Highest Silt Thickness - Top 25"})
            chart4.set_x_axis({"name": "Thickness (m)"})
            chart4.set_legend({"none": True})
            chart4.set_size({"width": 900, "height": 430})
            ch.insert_chart("B69", chart4)

        coords = [(idx, r) for idx, r in enumerate(recs, 1) if isinstance(r["easting"], (int, float)) and isinstance(r["northing"], (int, float))]
        if coords:
            chart5 = wb.add_chart({"type": "scatter", "subtype": "straight_with_markers"})
            chart5.add_series({"name": "CPT locations", "categories": ["Full Analysis", 1, 13, n, 13], "values": ["Full Analysis", 1, 14, n, 14]})
            chart5.set_title({"name": "CPT Coordinate Map"})
            chart5.set_x_axis({"name": "Easting"})
            chart5.set_y_axis({"name": "Northing"})
            chart5.set_size({"width": 900, "height": 430})
            ch.insert_chart("B91", chart5)

    # 6) Full physical-source audit: every report revision stays traceable.
    au = wb.add_worksheet("Source Audit")
    audit_headers = [
        "CPT FAMILY", "SOURCE FILE", "TYPE", "REVISION", "SOURCE QUALITY",
        "ANALYSIS STATUS", "SILT START (m)", "SILT THICKNESS (m)",
        "SELECTED FOR PROJECT", "SELECTION REASON", "VERIFICATION NOTE",
    ]
    for c, h in enumerate(audit_headers):
        au.write(0, c, h, hdr)
    au.freeze_panes(1, 1)
    au.autofilter(0, 0, max(1, len(source_audit)), len(audit_headers)-1)
    au.set_row(0, 38)
    au.set_column(0, 0, 25)
    au.set_column(1, 1, 40)
    au.set_column(2, 5, 17)
    au.set_column(6, 7, 18)
    au.set_column(8, 8, 20)
    au.set_column(9, 10, 70)

    for i, row in enumerate(source_audit, 1):
        values = [
            row.get("family"), row.get("source_file"), row.get("source_type"), row.get("revision"),
            row.get("source_quality"), row.get("status"), row.get("silt_start"), row.get("silt_thickness"),
            row.get("selected"), row.get("selection_reason"), row.get("verification_note"),
        ]
        for c, v in enumerate(values):
            if c in {6, 7} and isinstance(v, (int, float)):
                au.write_number(i, c, float(v), num)
            elif c == 3 and isinstance(v, (int, float)):
                au.write_number(i, c, float(v), center)
            else:
                au.write(i, c, "" if v is None else str(v), wrap if c in {9, 10} else center if c in {2,3,4,5,8} else text)
        au.set_row(i, 34)
    if source_audit:
        au.conditional_format(1, 5, len(source_audit), 5, {"type": "text", "criteria": "containing", "value": "VERIFIED", "format": green})
        au.conditional_format(1, 5, len(source_audit), 5, {"type": "text", "criteria": "containing", "value": "NO SILT", "format": blue})
        au.conditional_format(1, 5, len(source_audit), 5, {"type": "text", "criteria": "containing", "value": "REVIEW", "format": amber})
        au.conditional_format(1, 5, len(source_audit), 5, {"type": "text", "criteria": "containing", "value": "ERROR", "format": red})
        au.conditional_format(1, 8, len(source_audit), 8, {"type": "text", "criteria": "containing", "value": "YES", "format": green})
        au.conditional_format(1, 8, len(source_audit), 8, {"type": "text", "criteria": "containing", "value": "NO", "format": grey})

    # 7) Processing issues kept separate from engineering rows.
    er = wb.add_worksheet("Processing Errors")
    er.write(0, 0, "Source File", hdr)
    er.write(0, 1, "Error", hdr)
    er.set_column(0, 0, 35)
    er.set_column(1, 1, 90)
    for i, (src, msg) in enumerate(errors, 1):
        er.write(i, 0, src, text)
        er.write(i, 1, msg, wrap)
        er.set_row(i, 28)
    if errors:
        er.conditional_format(1, 0, len(errors), 1, {"type": "no_blanks", "format": red})

    wb.close()
    return p

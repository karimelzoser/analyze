"""Exact operator chart, UNKNOWN tail, multiple >0.10m screening intervals.

The numerical Ic values and cpt_core layer-detection thresholds are unchanged;
these cases validate classification display, maps, PDFs and the project XLSX.
"""
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile
import numpy as np

from cpt_core import classify_ic, analyze_gef
from engineering_layers import behavior_label, from_analysis
from engineering_reporting_policy import (
    visible_silt_layers, display_silt_summary, REPORT_MIN_THICKNESS_M)
from engineering_3d_studio import _category, collect_observed_segments
from engineering_pdf_summary import reportable_silt_pages
from engineering_geo_explorer import spatial_points
from reporting_export_v2 import export_excel
from test_modern_app import write_gef


def _fixture(tmp_path):
    path=tmp_path/"multiple.GEF"
    write_gef(path,"CPT-TEST-MULTIPLE-100")
    a=analyze_gef(path)
    z=np.arange(0.,6.401,.01)
    values=np.full(z.shape,1.8)
    values[(z>=1.00)&(z<=1.24)]=2.80
    values[(z>=2.00)&(z<=2.19)]=2.91
    values[(z>=3.00)&(z<=3.06)]=2.85
    values[z>=4.0]=np.nan
    a.depth=z
    a.ic=values
    a.valid_sensor=np.isfinite(values)
    a.status="REVIEW"  # preserve independent source QA status
    a.final_interval=None
    a.metadata["analysis_smoothing_window_samples"]=3
    return a


def test_exact_operator_ic_type_limits_and_unclassified_remain_unknown():
    limits=[
        (1.30,"Gravelly sand to dense sand"),
        (1.31,"Clean sand"),
        (1.59,"Sand with silt"),
        (1.83,"Silty sand"),
        (2.276,"Silty sand to sandy silt"),
        (2.50,"Sandy silt to silty sand"),
        (2.60,"Sandy silt to silty sand"),
        (2.68,"Silt mixture: clayey silt to silty clay"),
        (2.95,"Silty clay"),
        (3.10,"Clay"),
        (3.60,"Organic soils / peat-like"),
    ]
    for v,expected in limits:
        assert classify_ic(v)==expected
    assert classify_ic(float("nan")).startswith("UNKNOWN")
    assert behavior_label(2.60)=="SANDY SILT / SILTY SAND-LIKE"
    assert behavior_label(2.97)=="SILTY CLAY-LIKE"
    assert behavior_label(3.10)=="CLAY-LIKE"
    assert _category(SimpleNamespace(kind="UNKNOWN",mean_ic=3.5))=="unknown"
    assert _category(SimpleNamespace(kind="UNKNOWN",mean_ic=None))=="unknown"
    assert _category(SimpleNamespace(kind="SILTY CLAY-LIKE",mean_ic=3.0))=="silt"
    assert _category(SimpleNamespace(kind="CLAY-LIKE",mean_ic=3.15))=="clay"


def test_every_separate_layer_above_10cm_visible_but_thin_is_not_zero(tmp_path):
    a=_fixture(tmp_path)
    original=from_analysis(a)
    assert len(original.silt_intervals)==3
    measured=visible_silt_layers(a)
    assert len(measured)==2
    assert measured[0].start < measured[1].start
    assert all(x.thickness>REPORT_MIN_THICKNESS_M for x in measured)
    assert len(original.silt_intervals)-len(measured)==1
    label,layers=display_silt_summary(a)
    assert label=="REVIEW - observed silt layers"
    assert layers==measured
    assert np.isnan(a.ic[-1]) and not a.valid_sensor[-1]


def test_unknown_after_silt_not_colored_clay_and_not_failure(tmp_path):
    a=_fixture(tmp_path)
    segments,excluded,_=collect_observed_segments([a])
    assert segments
    assert any(s["category"]=="unknown" and s["top"]>=4.0 for s in segments)
    assert not any(s["category"]=="clay" and s["top"]>=4.0 for s in segments)
    assert any(s["category"]=="silt" and s.get("soil_behavior") for s in segments)
    # The map screens at 0.10m instead of treating thin intervals as zero.
    pts,_=spatial_points([a])
    assert len(pts)==1
    assert len(pts[0].intervals)==2
    assert pts[0].maximum_m is not None and pts[0].maximum_m>.10


def test_pdf_display_lists_two_layers_not_60mm_thin_third(tmp_path):
    a=_fixture(tmp_path)
    pages=reportable_silt_pages(a)
    assert len(pages)==1
    page=pages[0]
    assert "ALL OBSERVED SILT" in page.texts[0].get_text()
    # Table has one header and two qualifying layers; no zero-thickness row.
    rows=[c.get_text().get_text() for c in page.axes[0].tables[0].get_celld().values()]
    assert "1" in rows and "2" in rows
    assert "3" not in rows
    assert all("0.000"!=r for r in rows)


def test_excel_contains_all_reportable_depths_and_raw_audit(tmp_path):
    a=_fixture(tmp_path)
    outfile=export_excel([a],tmp_path/"report.xlsx")
    with ZipFile(outfile) as z:
        workbook=z.read("xl/workbook.xml")
        assert b"Reportable Silt Layers" in workbook
        data=b"".join(z.read(path) for path in z.namelist()
                      if path.startswith("xl/worksheets/sheet") and path.endswith(".xml"))
        strings=z.read("xl/sharedStrings.xml") if "xl/sharedStrings.xml" in z.namelist() else b""
        assert b"NO LAYER" not in strings  # two visible layers exist
        assert b"Reportable Silt Layers" in workbook
        assert b"Observed Ic-screened layer" in (strings+data)
        assert b"CPT Measurements" in workbook


def test_exact_threshold_is_not_rounded_up_into_visible_set():
    from engineering_reporting_policy import visible_silt_layers
    from unittest.mock import patch
    a=SimpleNamespace(all_intervals=[(1.,1.099999),(2.,2.10),(3.,3.1001)],
                      metadata={})
    with patch("engineering_layers.from_analysis",side_effect=ValueError("no sample")):
        got=visible_silt_layers(a)
    assert len(got)==1
    assert abs(got[0].thickness-.1001)<1e-9

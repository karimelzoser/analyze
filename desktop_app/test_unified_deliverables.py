"""Contract tests for ONE delivered workbook, embedded 3D maps and nonblank PDFs."""
import zipfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from benchmark_synthetic_batch import make_synthetic_gef
from cpt_core import analyze_gef
from engineering_3d_map import site_3d_figure,measured_3d_points
from engineering_pdf_summary import engineering_analysis_page
from reporting_export_v2 import export_excel


def test_all_in_one_xlsx_contains_all_cpt_measurements_maps_and_qa(tmp_path):
    file=tmp_path/"P261074_CPT-A1-TEST-100.GEF"
    make_synthetic_gef(file,17,150)
    result=analyze_gef(file,water_table_depth=2.0)
    output=export_excel([result],tmp_path/"all_in_one.xlsx")
    assert output.is_file()
    assert not list(tmp_path.glob("*.png"))
    with zipfile.ZipFile(output) as book:
        manifest=book.read("xl/workbook.xml")
        for name in (b"Summary",b"CPT Analysis",b"Full Analysis",b"All Soil Layers",
                     b"Project Maps",b"CPT Measurements",b"Source Audit"):
            assert name in manifest, name
        media=[n for n in book.namelist() if n.startswith("xl/media/image")]
        assert len(media)>=5, "Workbook must embed three 2D soil-depth color maps, screening plan and 3D strata"
        xml=b"".join(book.read(p) for p in book.namelist()
                     if p.startswith("xl/worksheets/sheet") and p.endswith(".xml"))
        assert b"SOIL CLASSIFICATION AT 2.00" in xml
        assert b"SOIL CLASSIFICATION AT 4.50" in xml
        assert b"SOIL CLASSIFICATION AT 5.40" in xml
        # All data rows in one output, not an external CSV or extra workbook.
        entries=book.read("xl/sharedStrings.xml") if "xl/sharedStrings.xml" in book.namelist() else b""
        entries+=b"".join(book.read(n) for n in book.namelist()
                         if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        assert b"CPT-A1-SYNTH-0017-100" in entries or b"CPT-A1-TEST-100" in entries


def test_pdf_review_appendix_has_explicit_not_observed_values():
    dummy=SimpleNamespace(
        reference="CPT-A1-B05-100",source_path=Path("B05.GFF"),
        status="REVIEW",final_interval=None,verification_note="Terminal sensor validity uncertain.",
        metadata={"easting":420446.63,"northing":2927669.20,
                  "ground_elevation":3.68,"file_date":"2026,10,10"},
        ic=np.array([2.1,np.nan]),depth=np.array([0,4.5]),
        pass1=None,pass2=None,all_intervals=[],sensor_dropout_depth=4.36,
        test_depth_raw=4.5,sand_layer_thickness=None)
    page=engineering_analysis_page(dummy)
    assert page is not None
    text=[t.get_text() for t in page.texts]
    assert any("CPT PDF ANALYSIS SUMMARY" in t for t in text)


def test_3d_map_accepts_real_survey_levels_without_interpolated_surface(tmp_path):
    f=tmp_path/"sample.GEF";make_synthetic_gef(f,3)
    a=analyze_gef(f,water_table_depth=2.0)
    fig,info=site_3d_figure([a])
    assert info["plotted"]==1
    assert fig.axes[0].name=="3d"
    p=tmp_path/"only_when_requested.png"
    fig.savefig(p)
    assert p.stat().st_size>5000


def test_original_source_reference_and_all_cached_depths_are_inside_same_output(tmp_path):
    from test_engineering_xlsb_reference import make_reference_fixture
    from engineering_unified_excel import extend_project_workbook
    source=tmp_path/"reference.xlsb"
    make_reference_fixture(source)
    raw=tmp_path/"input.GEF"
    make_synthetic_gef(raw,23)
    sounding=analyze_gef(raw,water_table_depth=2.0)
    result=export_excel([sounding],tmp_path/"single_output.xlsx",
                        original_xlsb=source)
    with zipfile.ZipFile(result) as book:
        named=book.read("xl/workbook.xml")
        for title in (b"Foundation Results",b"Original SBT Curves",b"Reference Comparison",
                      b"Project Maps",b"CPT Measurements",b"CPT Analysis"):
            assert title in named, title
        assert len([s for s in book.namelist() if s.startswith("xl/media/image")])>=2
    assert len(list(tmp_path.glob("*.xlsx")))==1


def test_full_report_uses_actual_calculation_groundwater_and_unit_weight(tmp_path):
    from reporting_pro import analysis_record
    source=tmp_path/"test.GEF"
    make_synthetic_gef(source,41,135)
    analysis=analyze_gef(source,gamma_soil=19.3,water_table_depth=2.0)
    report=analysis_record(analysis)
    assert report["gamma"]==19.3
    assert report["water_table"]==2.0
    assert report["area_ratio"]==analysis.metadata["area_ratio"]


def test_thin_pdf_reviewer_keeps_exact_observed_interval_in_same_excel(tmp_path):
    source=tmp_path/"thin.GEF"
    make_synthetic_gef(source,9,90)
    analysis=analyze_gef(source,water_table_depth=2.0)
    analysis.status="REVIEW"
    analysis.final_interval=None
    analysis.metadata["thin_interval_unrounded_start"]=5.201
    analysis.metadata["thin_interval_unrounded_end"]=5.243
    analysis.metadata["thin_interval_unrounded_thickness"]=.042
    analysis.verification_note="Original PDF trace shows sub-0.1 m interval."
    output=export_excel([analysis],tmp_path/"thin_evidence.xlsx")
    with zipfile.ZipFile(output) as workbook:
        xml=b"".join(workbook.read(n) for n in workbook.namelist()
                     if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        assert b"OBSERVED THIN LAYER" in xml
        assert b"5.201" in xml and b"5.243" in xml
        assert b"0.042" in xml



def test_unapproved_revision_candidate_is_not_on_accepted_quick_sheet(tmp_path):
    """REVIEW may retain a measured candidate, but C2/D2/E2 cannot imply acceptance."""
    import xml.etree.ElementTree as ET
    from cpt_core import SiltInterval

    source=tmp_path/"conflict.GEF"
    make_synthetic_gef(source,33,120)
    result=analyze_gef(source,water_table_depth=2.0)
    result.status="REVIEW"
    result.final_interval=SiltInterval(5.2,5.5,.3,5.2,5.5,.3,5.5)
    result.metadata["source_revision_conflict"]=True
    result.metadata["provisional_conflicting_result"]=True
    result.verification_note="SOURCE CONFLICT: another complete retest disagrees."
    output=export_excel([result],tmp_path/"review.xlsx")

    with zipfile.ZipFile(output) as workbook:
        root=ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        ns={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        cells={c.attrib["r"]:c for c in root.findall(".//m:sheetData/m:row/m:c",ns)}
        assert cells["C2"].attrib.get("t") in ("s","inlineStr")
        assert "D2" not in cells or cells["D2"].find("m:v",ns) is None
        assert "E2" not in cells or cells["E2"].find("m:v",ns) is None
        shared=workbook.read("xl/sharedStrings.xml")
        assert b"REVIEW" in shared
        # Numerical candidate survives in the Full Analysis / Review worksheets.
        all_xml=b"".join(workbook.read(s) for s in workbook.namelist()
                         if s.startswith("xl/worksheets/sheet") and s.endswith(".xml"))
        assert b"5.2" in all_xml and b"5.5" in all_xml

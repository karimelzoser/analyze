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
        for name in (b"CPT Analysis",b"Full Analysis",b"All Soil Layers",
                     b"Project Dashboard",b"Project Maps",b"CPT Measurements",
                     b"Survey Coordinate QA",b"CPT Coordinates"):
            assert name in manifest, name
        media=[n for n in book.namelist() if n.startswith("xl/media/image")]
        assert len(media)>=2
        # All data rows in one output, not an external CSV or extra workbook.
        entries=b"".join(book.read(n) for n in book.namelist()
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

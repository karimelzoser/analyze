"""A reviewed, conflicting CPT must not lose measured candidate values in PDF."""
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
import pymupdf
from engineering_pdf_summary import engineering_analysis_page


def test_review_pdf_shows_observed_candidate_with_provisional_warning(tmp_path):
    a=SimpleNamespace(
        reference="CPT-A2-B254-100",
        source_path=Path("P261074_CPT-A2-B254-100-1.GEF"),
        metadata={"project_name":"DAMMAM LOGISTICS ZONE","client":"SAUDI GLOBAL PORTS",
                  "easting":421269.814,"northing":2927368.449,
                  "ground_elevation":3.93,"area_ratio":.75,
                  "analysis_gamma_soil_kn_m3":18,"analysis_water_table_bgl_m":2},
        status="REVIEW",
        final_interval=SimpleNamespace(start=5.55,end=5.63,thickness=.08,
            start_raw=5.554136,end_raw=5.630478,thickness_raw=.076342),
        sand_layer_thickness=5.55,
        test_depth_raw=5.74,
        sensor_dropout_depth=5.64046,
        pass1=None,pass2=None,all_intervals=[],
        ic=np.array([2.1,2.7,3.0]),
        verification_note="Two substantial full-depth revisions conflict; approval required.",
    )
    page=engineering_analysis_page(a)
    pdf=tmp_path/"review.pdf"
    with PdfPages(pdf) as writer:writer.savefig(page)
    page.clear()
    with pymupdf.open(pdf) as document:
        text=document[0].get_text()
    assert "5.55 m [PROVISIONAL]" in text
    assert "0.08 m [PROVISIONAL]" in text
    assert "REVIEW" in text
    assert "Groundwater level" in text
    assert "5.55" in text

from pathlib import Path
from types import SimpleNamespace
from engineering_review_ui import qa_record, qa_summary, export_qa_csv


def _example(ref="CPT-A1-B05-100", status="REVIEW", kind=".GEF"):
    return SimpleNamespace(reference=ref,status=status,
        source_path=Path(ref+kind),
        metadata={"source_quality":"RAW NUMERICAL" if kind!=".pdf" else "VECTOR PDF"},
        final_interval=None,depth=[0,1],sensor_dropout_depth=4.4,
        test_depth_raw=4.5,verification_note="Uncertain end-of-test sleeve friction")


def test_qa_flags_sensor_dropouts_and_uncertain_classification():
    row=qa_record(_example())
    assert row["status"]=="REVIEW"
    assert len(row["issues"])>=2
    assert any("Terminal sensor dropout" in issue for issue in row["issues"])
    assert qa_summary([row])["Review"]==1
    assert qa_summary([row])["QC flags"]==1


def test_qa_pdf_confidence_visible_and_utf8_csv(tmp_path):
    x=qa_record(_example(kind=".pdf"))
    assert any("PDF-derived" in item for item in x["issues"])
    report=export_qa_csv([x],tmp_path/"CPT_QA.csv")
    text=report.read_text(encoding="utf-8-sig")
    assert "source_quality" in text
    assert "VECTOR PDF" in text
    assert "CPT-A1-B05-100" in text
    assert "Uncertain end-of-test" in text


def test_empty_project_qa_counts():
    assert qa_summary([])=={"CPTs":0,"Verified":0,"No silt":0,"Review":0,"QC flags":0}


def test_pdf_review_ui_shows_observed_positive_thickness_not_empty():
    sample=_example(ref="CPT-A1-B56-100",kind=".pdf")
    sample.metadata["thin_interval_unrounded_start"]=4.851
    sample.metadata["thin_interval_unrounded_end"]=4.921
    sample.metadata["thin_interval_unrounded_thickness"]=.070
    row=qa_record(sample)
    assert row["status"]=="REVIEW"
    assert row["review_category"]=="OBSERVED THIN INTERVAL"
    assert row["silt_thickness"] is None  # engineering value not yet approved
    assert row["observed_candidate_thickness"]==.070
    assert any("OBSERVED THIN INTERVAL" in issue for issue in row["issues"])

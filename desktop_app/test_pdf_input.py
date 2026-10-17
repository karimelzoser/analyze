from pathlib import Path

import pytest
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from pdf_analysis import analyze_pdf, append_pdf_analysis
from app_pdf_enabled import collect_project_folder, prefer_best_sources


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "pdfs" / "pdf_Single"


@pytest.mark.parametrize(
    "filename, expected_start, expected_thickness",
    [
        ("P261074_CPT-A1-B342-100.pdf", 6.20, 0.40),
        ("P261074_CPT-A1-B343-100.pdf", 6.20, 0.30),
        ("P261074_CPT-A1-B355-100.pdf", 6.30, 0.30),
        ("P261074_CPT-A1-B356-100.pdf", 6.40, 0.20),
    ],
)
def test_vector_pdf_engine_matches_validated_project_anchors(filename, expected_start, expected_thickness):
    path = PDF_DIR / filename
    assert path.exists(), f"Missing regression fixture: {path}"
    a = analyze_pdf(path)
    assert a.status == "VERIFIED"
    assert a.final_interval is not None
    assert a.final_interval.start == expected_start
    assert a.final_interval.thickness == expected_thickness
    assert a.metadata.get("source_quality") == "VECTOR PDF"


def test_pdf_output_preserves_source_pages_and_appends_analysis(tmp_path):
    source = PDF_DIR / "P261074_CPT-A1-B355-100.pdf"
    a = analyze_pdf(source)
    out = append_pdf_analysis(source, a, tmp_path / "B355_analyzed.pdf")
    with fitz.open(source) as src, fitz.open(out) as dst:
        assert dst.page_count == src.page_count + 1
        assert dst[0].get_text("text") == src[0].get_text("text")
        assert "CPT PDF ANALYSIS SUMMARY" in dst[-1].get_text("text")


def test_scanned_or_unsupported_pdf_is_review_not_guess(tmp_path):
    blank = tmp_path / "CPT-SCANNED-LIKE.pdf"
    doc = fitz.open()
    doc.new_page(width=612, height=792)
    doc.save(blank)
    doc.close()
    a = analyze_pdf(blank)
    assert a.status == "REVIEW"
    assert a.final_interval is None
    assert "not be verified" in a.verification_note


def test_mixed_input_prefers_raw_file_over_same_reference_pdf(tmp_path):
    raw = tmp_path / "P261074_CPT-A1-B355-100.GEF"
    pdf = tmp_path / "P261074_CPT-A1-B355-100.pdf"
    other = tmp_path / "P261074_CPT-A1-B356-100.pdf"
    raw.write_text("raw")
    pdf.write_bytes(b"pdf")
    other.write_bytes(b"pdf")
    selected, skipped = prefer_best_sources([pdf, raw, other])
    assert raw in selected
    assert pdf in skipped
    assert other in selected


def test_folder_collection_includes_raw_and_pdf(tmp_path):
    (tmp_path / "a.GEF").write_text("x")
    (tmp_path / "b.gff").write_text("x")
    (tmp_path / "c.pdf").write_bytes(b"x")
    (tmp_path / "ignore.txt").write_text("x")
    selected, _ = collect_project_folder(tmp_path)
    assert {p.suffix.lower() for p in selected} == {".gef", ".gff", ".pdf"}

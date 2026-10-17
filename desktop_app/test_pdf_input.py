from pathlib import Path
import zipfile

import pytest
try:
    import pymupdf as fitz
except ImportError:
    import fitz

from pdf_analysis_refined import analyze_pdf, append_pdf_analysis
from app_pdf_enabled import (
    canonical_reference,
    collect_project_folder,
    prefer_best_sources,
    select_project_results,
    source_revision,
)
from reporting_export_v2 import export_excel


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


def test_revision_names_collapse_to_one_project_family():
    names = [
        "P261074_CPT-A1-B84-100.pdf",
        "P261074_CPT-A1-B84-100-1.pdf",
        "P261074_CPT-A1-B84-100-2.pdf",
        "P261074_CPT-A1-B84-100(3).pdf",
        "P261074_CPT-A1-B84.100.pdf",
    ]
    assert {canonical_reference(x) for x in names} == {"CPT-A1-B84-100"}
    assert source_revision(names[0]) == 0
    assert source_revision(names[1]) == 1
    assert source_revision(names[2]) == 2
    assert source_revision(names[3]) == 3


def test_input_collection_keeps_pdf_revisions_for_post_analysis_qa(tmp_path):
    raw = tmp_path / "P261074_CPT-A1-B355-100.GEF"
    pdf = tmp_path / "P261074_CPT-A1-B355-100.pdf"
    rev = tmp_path / "P261074_CPT-A1-B355-100-1.pdf"
    other = tmp_path / "P261074_CPT-A1-B356-100.pdf"
    raw.write_text("raw")
    pdf.write_bytes(b"pdf")
    rev.write_bytes(b"pdf")
    other.write_bytes(b"pdf")
    selected, skipped = prefer_best_sources([pdf, raw, rev, other])
    assert set(selected) == {raw, pdf, rev, other}
    assert skipped == []


def test_folder_collection_includes_raw_pdf_and_revisions(tmp_path):
    (tmp_path / "P261074_CPT-A1-B1-100.GEF").write_text("x")
    (tmp_path / "P261074_CPT-A1-B2-100.gff").write_text("x")
    (tmp_path / "P261074_CPT-A1-B3-100.pdf").write_bytes(b"x")
    (tmp_path / "P261074_CPT-A1-B3-100-1.pdf").write_bytes(b"x")
    (tmp_path / "ignore.txt").write_text("x")
    selected, _ = collect_project_folder(tmp_path)
    assert len(selected) == 4
    assert {p.suffix.lower() for p in selected} == {".gef", ".gff", ".pdf"}


def test_real_revision_family_collapses_review_files_to_one_verified_project_row():
    family = [
        PDF_DIR / "P261074_CPT-A1-B84-100.pdf",
        PDF_DIR / "P261074_CPT-A1-B84-100-1.pdf",
        PDF_DIR / "P261074_CPT-A1-B84-100-2.pdf",
    ]
    for p in family:
        assert p.exists(), f"Missing revision fixture: {p}"
    analyses = [analyze_pdf(p) for p in family]
    selected, audit = select_project_results(analyses, family)
    assert len(selected) == 1
    a = selected[0]
    assert a.reference == "CPT-A1-B84-100"
    assert a.status == "VERIFIED"
    assert a.final_interval is not None
    assert (a.final_interval.start, a.final_interval.thickness) == (4.80, 0.50)
    assert a.source_path.name.endswith("B84-100-2.pdf")
    assert len(audit) == 3
    assert sum(r["selected"] == "YES" for r in audit) == 1


def test_verified_sub_tenth_pdf_layer_never_reports_zero_thickness():
    source = PDF_DIR / "P261074_CPT-A1-B56-100.pdf"
    assert source.exists(), f"Missing regression fixture: {source}"
    a = analyze_pdf(source)
    assert a.status == "VERIFIED"
    assert a.final_interval is not None
    assert a.final_interval.thickness >= 0.10
    assert a.final_interval.end - a.final_interval.start == pytest.approx(a.final_interval.thickness)


def test_source_audit_sheet_is_written(tmp_path):
    source = PDF_DIR / "P261074_CPT-A1-B355-100.pdf"
    a = analyze_pdf(source)
    selected, audit = select_project_results([a], [source])
    xlsx = export_excel(selected, tmp_path / "audit.xlsx", source_audit=audit)
    with zipfile.ZipFile(xlsx) as z:
        workbook = z.read("xl/workbook.xml")
        assert b"Source Audit" in workbook
        assert b"CPT Analysis" in workbook
        assert b"Summary" in workbook

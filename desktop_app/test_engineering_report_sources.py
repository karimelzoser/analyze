from pathlib import Path
from types import SimpleNamespace
from engineering_report_sources import choose_official_pdf


def _source(filename,e=421092.370,n=2928336.250,z=3.46,date="21-Sep-2026"):
    return SimpleNamespace(source_path=Path(filename),metadata={
        "easting":e,"northing":n,"ground_elevation":z,"file_date":date})


def test_raw_analysis_preserved_and_matching_original_pdf_selected():
    original=_source("P261074_CPT-A1-292-100.GEF")
    matching=_source("P261074_CPT-A1-292-100.pdf")
    official,reason=choose_official_pdf(original,[original,matching])
    assert official is matching
    assert "preserved" in reason.lower()


def test_mismatched_coordinates_or_datum_cannot_be_used_as_official_report():
    raw=_source("P261074_CPT-A1-292-100.GEF")
    far=_source("P261074_CPT-A1-292-100.pdf",e=421098)
    wrong_level=_source("P261074_CPT-A1-292-100-1.pdf",z=3.15)
    selected,note=choose_official_pdf(raw,[far,wrong_level])
    assert selected is None
    assert "No matching" in note


def test_mismatched_survey_date_blocks_reference_pdf():
    raw=_source("P261074_CPT-A1-292-100.GEF")
    pdf=_source("P261074_CPT-A1-292-100.pdf",date="22-Sep-2026")
    selected,note=choose_official_pdf(raw,[pdf])
    assert selected is None
    assert "test dates conflict" in note


def test_missing_raw_coordinates_prevents_unverified_chart_reuse():
    raw=_source("P261074_CPT-A1-292-100.GEF")
    del raw.metadata["easting"]
    pdf=_source("P261074_CPT-A1-292-100.pdf")
    selected,note=choose_official_pdf(raw,[pdf])
    assert selected is None
    assert "coordinates missing" in note

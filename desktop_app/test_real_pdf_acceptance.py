from pathlib import Path
import csv
import json
import zipfile
import pytest

from real_pdf_acceptance import run_real_pdf_acceptance


ROOT=Path(__file__).resolve().parents[1]
SOURCES=ROOT/"pdfs"/"pdf_Single"


def test_actual_pdf_acceptance_has_100_percent_source_manifest_and_one_workbook(tmp_path):
    inputs=tmp_path/"inputs"
    inputs.mkdir()
    for name in ("P261074_CPT-A1-B355-100.pdf",
                 "P261074_CPT-A1-B356-100.pdf"):
        (inputs/name).write_bytes((SOURCES/name).read_bytes())
    out=tmp_path/"out"
    result=run_real_pdf_acceptance(inputs,out,expected_physical=2)
    assert result["physical_pdfs"]==2
    assert result["parsed_pdf_files"]==2
    assert result["parse_errors"]==0
    assert result["unique_cpt_references"]==2
    assert result["selected_sources"]==2
    with (out/"PDF_Source_Manifest.csv").open(encoding="utf-8-sig",newline="") as fd:
        rows=list(csv.DictReader(fd))
    assert len(rows)==2
    assert all(len(x["sha256"])==64 for x in rows)
    assert all(x["parsed"]=="YES" for x in rows)
    with zipfile.ZipFile(out/"Real_Project_PDF_Acceptance.xlsx") as archive:
        workbook=archive.read("xl/workbook.xml")
        assert b"CPT Analysis" in workbook
        assert b"Source Audit" in workbook
        assert b"Project Maps" in workbook
        # First/default visible view must be the requested five-column sheet,
        # not a stale Excel tab index left over after worksheet rearrangement.
        import xml.etree.ElementTree as ET
        namespace="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        parsed=ET.fromstring(workbook)
        tabs=parsed.find(f"{namespace}bookViews/{namespace}workbookView")
        assert tabs is not None
        assert tabs.get("activeTab")=="0"
        assert tabs.get("firstSheet")=="0"
        selected=archive.read("xl/worksheets/sheet1.xml")
        assert b'tabSelected="1"' in selected
        assert len([n for n in archive.namelist()
                    if n.startswith("xl/media/image")])>=2


def test_acceptance_rejects_unexpected_source_count_without_partial_outputs(tmp_path):
    p=tmp_path/"inputs";p.mkdir()
    (p/"P261074_CPT-A1-B355-100.pdf").write_bytes(
        (SOURCES/"P261074_CPT-A1-B355-100.pdf").read_bytes())
    with pytest.raises(ValueError,match="Expected 2"):
        run_real_pdf_acceptance(p,tmp_path/"output",expected_physical=2,
                                write_workbook=False)
    assert not (tmp_path/"output"/"PDF_Acceptance_Result.json").exists()

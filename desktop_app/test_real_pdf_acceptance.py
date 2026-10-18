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
        # OOXML omits default zero-valued view attributes in valid workbooks.
        assert tabs.get("activeTab","0")=="0"
        assert tabs.get("firstSheet","0")=="0"
        selected=archive.read("xl/worksheets/sheet1.xml")
        assert b'tabSelected="1"' in selected
        assert len([n for n in archive.namelist()
                    if n.startswith("xl/media/image")])>=2
        # Source Audit must refer to actual physical PDFs. Historically the
        # exporter looked up 'reference'/'source' instead of 'family'/
        # 'source_file' and wrote NOT RECORDED in both audit columns.
        sheets={item.get("name"):item.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            for item in parsed.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet")}
        relroot=ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rels={entry.get("Id"):entry.get("Target")
              for entry in relroot.findall(
                "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")}
        target=rels[sheets["Source Audit"]].lstrip("/")
        if not target.startswith("xl/"):target="xl/"+target
        audit=ET.fromstring(archive.read(target))
        row2=audit.find(
           "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheetData/"
           "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row[@r='2']")
        assert row2 is not None
        values={}
        for cell in row2:
            location=cell.get("r")
            text="".join(t.text or "" for t in cell.iter(
              "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
            values[location]=text
        assert values["A2"].startswith("CPT-A1-B")
        assert values["B2"].startswith("P261074_CPT-A1-B")
        assert values["C2"]=="PDF"


def test_acceptance_rejects_unexpected_source_count_without_partial_outputs(tmp_path):
    p=tmp_path/"inputs";p.mkdir()
    (p/"P261074_CPT-A1-B355-100.pdf").write_bytes(
        (SOURCES/"P261074_CPT-A1-B355-100.pdf").read_bytes())
    with pytest.raises(ValueError,match="Expected 2"):
        run_real_pdf_acceptance(p,tmp_path/"output",expected_physical=2,
                                write_workbook=False)
    assert not (tmp_path/"output"/"PDF_Acceptance_Result.json").exists()

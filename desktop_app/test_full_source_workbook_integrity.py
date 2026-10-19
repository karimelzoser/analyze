"""One file must contain both optional engineering reference sources.

The original XLSB caches RAFT results. The separate supplied pre-CPT XLSX
contains ISOLATED as well as RAFT cases, and must never be dropped simply
because the original XLSB is also present.
"""
import zipfile
from pathlib import Path
import xlsxwriter
from benchmark_synthetic_batch import make_synthetic_gef
from cpt_core import analyze_gef
from reporting_export_v2 import export_excel
from test_engineering_xlsb_reference import make_reference_fixture


def test_one_workbook_preserves_original_xlsb_and_isolated_foundation_rows(tmp_path):
    raw=tmp_path/"synthetic.GEF"
    make_synthetic_gef(raw,3)
    analysis=analyze_gef(raw)
    xlsb=tmp_path/"original_model.xlsb"
    make_reference_fixture(xlsb)

    input_summary=tmp_path/"Pre CPT Summary.xlsx"
    wb=xlsxwriter.Workbook(str(input_summary))
    raft=wb.add_worksheet("Raft Summary")
    isolated=wb.add_worksheet("Isolated Summary")
    headers=["CPT REFERENCE","Easting","Northing","Settlement (mm)","min. FOS"]
    for ws in (raft,isolated):
        ws.write_row(0,0,headers)
    raft.write_row(1,0,["CPT-A1-B1-100",421000,2928000,70.0,2.4])
    isolated.write_row(1,0,["CPT-A1-B1-100",421000,2928000,34.0,2.0])
    wb.close()

    result=export_excel(
        [analysis],tmp_path/"all-in-one.xlsx",
        original_xlsb=xlsb,foundation_xlsx=input_summary)
    with zipfile.ZipFile(result) as z:
        names=z.read("xl/workbook.xml")
        assert b"Foundation Results" in names
        assert b"Supplied Footing Cases" in names
        assert b"Original SBT Curves" in names
        assert b"Project Maps" in names
        assert b"CPT Measurements" in names
        assert len([p for p in z.namelist() if p.startswith("xl/media/")])>=2
        assert z.testzip() is None

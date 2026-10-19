"""Regression: actual Isolated Summary settlement reaches the single Excel output.

Read-only reference values, not inferred settlement from Ic.
"""
from pathlib import Path
import zipfile
import xlsxwriter
from engineering_comparison import read_summary_xlsx
from engineering_unified_excel import extend_project_workbook


def _foundation_fixture(path):
    wb=xlsxwriter.Workbook(str(path))
    for case in ("Raft Summary","Isolated Summary"):
        ws=wb.add_worksheet(case)
        ws.write_row(0,0,["PROJECT REFERENCE",case])
        ws.write_row(1,0,["SI.No","CPT REFERENCE","Easting","Norting",
                         "Footing Type","Settlement (mm)","min. FOS",
                         "Footing Width [m]","Footing L/B"])
        typ="Isolated" if case.startswith("Isolated") else "Raft"
        value=55.04 if typ=="Isolated" else 71.54
        ws.write_row(2,0,[1,"CPT-A1-B363-100",421207.000,2928197.111,
                          typ,value,2.1867755,3.0 if typ=="Isolated" else 50.0,
                          1.0 if typ=="Isolated" else 1.2])
    wb.close()


def test_imported_isolated_settlement_and_raft_values_remain_separate(tmp_path):
    src=tmp_path/"Pre CPT Summary.xlsx";_foundation_fixture(src)
    rows=read_summary_xlsx(src)
    assert {r.foundation for r in rows}=={"RAFT","ISOLATED"}
    isolated=[r for r in rows if r.foundation=="ISOLATED"]
    assert len(isolated)==1
    assert isolated[0].metrics["settlement_mm"]==55.04
    assert abs(isolated[0].metrics["fos"]-2.1867755)<1e-8
    assert isolated[0].footing_width_m==3.0


def test_single_workbook_has_isolated_footing_settlement_and_2d_3d_map(tmp_path):
    src=tmp_path/"Pre CPT Summary.xlsx";_foundation_fixture(src)
    output=tmp_path/"Unified CPT.xlsx"
    wb=xlsxwriter.Workbook(str(output))
    info=extend_project_workbook(wb,[],foundation_xlsx=src)
    wb.close()
    with zipfile.ZipFile(output) as pkg:
        names=pkg.read("xl/workbook.xml")
        assert b"Isolated Foundation" in names
        assert b"Raft Foundation" in names
        assert b"Project Maps" in names
        assert len([n for n in pkg.namelist() if n.startswith("xl/media/image")])>=2
        # Settlement is from original supplied fixture and must survive the
        # import/export chain in an actual worksheet value, not just in a title.
        texts=b"".join(pkg.read(n) for n in pkg.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        assert b"55.04" in texts
        assert b"71.54" in texts


def test_production_export_contains_complete_isolated_records_and_missing_flags(tmp_path):
    from reporting_export_v2 import export_excel
    source=tmp_path/"Pre CPT Summary.xlsx"
    wb=xlsxwriter.Workbook(str(source))
    for name in ("Raft Summary","Isolated Summary"):
        sh=wb.add_worksheet(name)
        sh.write_row(0,0,["BANNER",name])
        sh.write_row(1,0,["SI.No","CPT REFERENCE","Easting","Norting",
                           "Settlement (mm)","min. FOS","Footing Width [m]",
                           "Footing L/B"])
        sh.write_row(2,0,[1,"CPT-A2-B230-100",421000,2928000,
                           62.48 if name=="Isolated Summary" else 41.30,
                           2.1,3 if name=="Isolated Summary" else 50,1])
        if name=="Isolated Summary":
            sh.write_row(3,0,[2,"CPT-A2-B231-100",421020,2928000,None,
                              2.5,3,1])
    wb.close()
    out=export_excel([],tmp_path/"CPT_Final.xlsx",foundation_xlsx=source)
    with zipfile.ZipFile(out) as pack:
        workbook=pack.read("xl/workbook.xml")
        assert b"Foundation Results" in workbook
        assert b"Footing Calculation QA" in workbook
        data=b"".join(pack.read(n) for n in pack.namelist()
                  if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        assert b"62.48" in data
        assert b"41.3" in data
        assert b"NOT CALCULATED / NOT PROVIDED IN SOURCE" in data

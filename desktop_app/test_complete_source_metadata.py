"""The deliverable must include original GEF headers, explicit u2 assumptions
and all source input evidence in the SAME Excel as numerical CPT data.
"""
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from cpt_core import parse_gef, analyze_gef
from reporting_export_v2 import export_excel
from engineering_pdf_summary import engineering_analysis_page


def _sample(path,with_u2=False):
    n=5 if with_u2 else 4
    head=[
       "#GEFID= 1, 1, 0","#PROJECTID= P_TEST",
       "#PROJECTNAME= Example site",
       "#COLUMN= "+str(n),
       "#COLUMNINFO= 1, m, penetration length, 1",
       "#COLUMNINFO= 2, MPa, tip resistance, 2",
       "#COLUMNINFO= 3, MPa, local sleeve friction, 3",
       "#COLUMNINFO= 4, m, corrected depth, 11",
    ]
    if with_u2:head.append("#COLUMNINFO= 5, MPa, pore pressure, 6")
    head.extend(["#MEASUREMENTTEXT= 1, TEST CLIENT, client",
                 "#MEASUREMENTTEXT= 4, CONE123, cone serial",
                 "#MEASUREMENTVAR= 3, 0.8, -, ratio",
                 "#XYID= 1, 421092.37, 2928336.25",
                 "#ZID= 31000, 3.46, 0.001",
                 "#TESTDATE= 2026-09-21",
                 "#TESTID= CPT-A1-TEST-100",
                 "#EOH="])
    for i in range(101):
        z=i/100
        qc=10.0 if z < .5 else .7
        fs=.10 if z < .5 else .15
        row=f"{z:.2f} {qc:.4f} {fs:.4f} {z:.2f}"
        if with_u2:row+=" 0.12"
        head.append(row)
    path.write_text("\n".join(head),encoding="ascii")


def test_missing_u2_is_declared_not_called_measured(tmp_path):
    path=tmp_path/"no_u2.gef";_sample(path)
    g=parse_gef(path)
    assert not g.metadata["pore_pressure_measured"]
    assert "assumed u2=0" in g.metadata["pore_pressure_source"]
    assert g.metadata["test_date"]=="2026-09-21"
    assert any(k=="MEASUREMENTTEXT" for k,v in g.metadata["source_header_entries"])
    analysis=analyze_gef(path)
    xlsx=export_excel([analysis],tmp_path/"unified.xlsx")
    with ZipFile(xlsx) as z:
        catalog=z.read("xl/workbook.xml")
        assert b"Original GEF Headers" in catalog
        assert b"CPT Measurements" in catalog
        assert b"Project Maps" in catalog
        # The operator's five-column quick sheet must be FIRST, not hidden
        # behind a dashboard or source-metadata worksheet.
        import xml.etree.ElementTree as ET
        xml=ET.fromstring(catalog)
        ns={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        sheet_names=[x.get("name") for x in xml.findall(".//m:sheets/m:sheet",ns)]
        assert sheet_names[0]=="CPT Analysis"
        assert sheet_names[1]=="Summary"
        assert sum(s.startswith("xl/media/image") for s in z.namelist())>=2
        texts="".join(z.read(name).decode("utf-8","replace") for name in z.namelist()
                      if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
        assert "PORE_PRESSURE_CALCULATION_SOURCE" in texts
        assert "assumed u2=0" in texts
    fig=engineering_analysis_page(analysis)
    assert fig is not None
    assert any("Pore pressure u2 source" in str(cell.get_text().get_text())
               for axis in fig.axes for table in axis.tables for cell in table.get_celld().values())


def test_true_u2_is_preserved_and_not_marked_missing(tmp_path):
    path=tmp_path/"u2.gef";_sample(path,with_u2=True)
    gef=parse_gef(path)
    assert gef.metadata["pore_pressure_measured"]
    assert gef.metadata["pore_pressure_source"]=="MEASURED"
    assert abs(gef.columns["u2"][0]-.12)<1e-8

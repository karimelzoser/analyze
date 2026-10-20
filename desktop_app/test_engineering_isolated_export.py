"""Ensure source-isolated settlement gaps are visible and screening trace auditable."""
from types import SimpleNamespace
import zipfile
import numpy as np
import xlsxwriter

from engineering_comparison import SummaryPoint
from engineering_isolated_export import append_isolated_sheets
from engineering_isolated_settlement import IsolatedInputs


def _point(i,settlement):
    return SummaryPoint(
        reference="CPT-A2-B%d-100" % (190+i),
        foundation="ISOLATED",east=421200.+i*7,north=2927500.+i*5,
        metrics={"settlement_mm":settlement,"fos":2.2},
        source_sheet="Isolated Summary",footing_width_m=3.0,
        footing_lb_ratio=1.0,
        reported_settlement_check="Pass")


def test_393_isolated_rows_preserved_with_214_missing_source_results(tmp_path):
    source=[_point(i,None if i<214 else (55.0 if i==214 else 32.0))
            for i in range(393)]
    out=tmp_path/"IsolatedResults.xlsx"
    book=xlsxwriter.Workbook(str(out))
    result=append_isolated_sheets(book,[],source)
    book.close()
    assert result["source_count"]==393
    assert result["computed"]==0
    assert result["incomplete"]==393
    with zipfile.ZipFile(out) as file:
        names=file.read("xl/workbook.xml")
        assert b"Isolated Settlement Results" in names
        assert b"Isolated Strain Integration" in names
        assert b"Isolated Model QA" in names
        xml=b"".join(file.read(n) for n in file.namelist() if
                     n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        assert b"NOT AVAILABLE" in xml
        assert b"CONFLICT: source says Pass but saved result exceeds 40 mm" in xml
        assert b"393" in xml and b"214" in xml


def test_observed_raw_qt_populates_computed_and_incremental_rows(tmp_path):
    z=np.arange(.02,5.99,.02)
    a=SimpleNamespace(reference="CPT-A2-B190-100",depth=z,
        qt=np.full(len(z),9.0),source_path="CPT-A2-B190-100.GEF",
        metadata={"easting":421200.,"northing":2927500.})
    out=tmp_path/"FoundationReview.xlsx"
    book=xlsxwriter.Workbook(str(out))
    result=append_isolated_sheets(book,[a],[_point(0,None)],
        IsolatedInputs(influence_b=1.5))
    book.close()
    assert result["computed"]==1
    assert result["trace_rows"]>150
    with zipfile.ZipFile(out) as file:
        data=b"".join(file.read(n) for n in file.namelist() if
                  n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        assert b"ESTIMATE" in data
        assert b"NOT ASSESSED" in data

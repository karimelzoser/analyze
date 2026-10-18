"""Ensure large Excel sources stream to numbered sheets without data loss."""
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import numpy as np
import xlsxwriter

from engineering_excel_paging import write_cpt_measurements, write_paged_rows


def style_for(wb):
    return {
        "header":wb.add_format({"bold":True}),
        "number":wb.add_format({"num_format":"0.00"}),
        "plain":wb.add_format(),
        "small":wb.add_format({"font_color":"#666666"}),
    }


def fake(ref,n):
    z=np.arange(n,dtype=float)*.01
    return SimpleNamespace(
        reference=ref,source_path=Path(ref+".GEF"),
        metadata={"pore_pressure_measured":True},
        depth=z,qc=z+2,fs=z*.001+0.03,u2=np.full(n,.02),
        qt=z+2.005,fr=np.ones(n),qtn=np.ones(n)*100,
        ic=np.ones(n)*2.1,valid_sensor=np.ones(n,dtype=bool))


def test_numeric_samples_roll_to_multiple_sheets(tmp_path):
    p=tmp_path/"paged.xlsx"
    book=xlsxwriter.Workbook(str(p),{"constant_memory":True})
    total,ranges,pages=write_cpt_measurements(book,style_for(book),
                           [fake("CPT-A1-TEST-1",14),fake("CPT-A1-TEST-2",9)],
                           page_limit=10)
    book.close()
    assert total==23
    assert pages==["CPT Measurements","CPT Measurements 02","CPT Measurements 03"]
    assert [r[1] for r in ranges]==["CPT Measurements","CPT Measurements 02",
                                  "CPT Measurements 02","CPT Measurements 03"]
    with ZipFile(p) as archive:
        xml=archive.read("xl/workbook.xml")
        assert b"CPT Measurements 03" in xml
        assert len([n for n in archive.namelist() if n.startswith("xl/worksheets/sheet")])==3


def test_original_source_zone_paging_is_in_same_workbook(tmp_path):
    p=tmp_path/"source.xlsx"
    book=xlsxwriter.Workbook(str(p),{"constant_memory":True})
    values=((i,f"CPT-{i}") for i in range(17))
    count,pages=write_paged_rows(book,style_for(book),
                   "Original SBT Curves",["Sample","CPT"],values,page_limit=7)
    book.close()
    assert count==17
    assert len(pages)==3
    with ZipFile(p) as archive:
        assert b"Original SBT Curves 03" in archive.read("xl/workbook.xml")

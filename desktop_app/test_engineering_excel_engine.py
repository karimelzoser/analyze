from pathlib import Path
import pytest
from engineering_excel_engine import input_matrix_from_gef,_EXCEL_WORKER


def _write_gef(path,header_rows=61):
    header=["#GEFID= 1, 1, 0"]
    while len(header)<header_rows-2:
        header.append("#MEASUREMENTTEXT= 1, SOME, TEXT")
    header.extend(["#TESTID= CPT-A1-292-100","#EOH="])
    assert len(header)==header_rows
    values=[f"{i*.01:.3f} 1.2 .04 .005 .01 .01 33 {i*.01:.3f} {i}" for i in range(30)]
    path.write_text("\n".join(header+values),encoding="utf-8")


def test_original_excel_gef_input_matrix_honors_template_header_rows(tmp_path):
    source=tmp_path/"x.GEF";_write_gef(source)
    matrix,ref=input_matrix_from_gef(source)
    assert ref=="CPT-A1-292-100"
    assert len(matrix)==91
    assert matrix[59]==["#TESTID=","CPT-A1-292-100"]
    assert matrix[60]==["#EOH="]
    assert matrix[61][0]==0.0
    assert len(matrix[61])==9
    assert matrix[90][7]==.29


def test_mismatched_gef_header_is_rejected_not_written_to_wrong_excel_cells(tmp_path):
    source=tmp_path/"y.GEF";_write_gef(source,header_rows=60)
    with pytest.raises(ValueError,match="Field-by-field alignment"):
        input_matrix_from_gef(source)


def test_original_excel_run_requires_installation_and_disables_macros():
    assert "$xl.AutomationSecurity=3" in _EXCEL_WORKER
    assert "$book.Close($false)" in _EXCEL_WORKER
    assert "CalculateFullRebuild()" in _EXCEL_WORKER

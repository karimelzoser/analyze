import zipfile
from pathlib import Path
from engineering_reference_audit import audit_xlsb
from engineering_pdf_parity import pdf_visual_regression
try:
    import pymupdf
except ImportError:
    import fitz as pymupdf


def test_read_only_chart_reference_inventory(tmp_path):
    ref=tmp_path/"test.xlsb"
    chart='''<?xml version="1.0" encoding="utf-8"?>
<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart">
<c:f>'Analysis-Case 1'!$BC$6:$BC$25</c:f>
<c:numCache><c:ptCount val="2"/><c:pt idx="0"><c:v>2.1</c:v></c:pt>
<c:pt idx="1"><c:v>2.9</c:v></c:pt></c:numCache></c:chartSpace>'''
    with zipfile.ZipFile(ref,"w") as z:
        z.writestr("xl/workbook.bin",b"example")
        z.writestr("xl/worksheets/sheet1.bin",b"data")
        z.writestr("xl/charts/chart1.xml",chart.encode())
    result=audit_xlsb(ref)
    assert result["embedded_chart_count"]==1
    assert result["binary_sheets"]==1
    assert "Analysis-Case 1" in result["identified_model_sheets"]
    assert "NOT VERIFIED" in result["engineering_assessment"]
    assert result["chart_series_references"][0]["cached_preview"][0][1]["value"]=="2.9"


def test_pdf_parity_self_identical_and_different(tmp_path):
    a=tmp_path/"reference.pdf"
    b=tmp_path/"variant.pdf"
    doc=pymupdf.open()
    page=doc.new_page(width=612,height=792)
    page.insert_text((30,48),"CPT engineering reference",fontsize=18)
    doc.save(a);doc.close()
    doc=pymupdf.open(str(a))
    doc[0].insert_text((45,140),"Additional soil note")
    doc.save(b);doc.close()
    same=pdf_visual_regression(a,a,tmp_path/"same",dpi=80)
    assert same["exact_layout_near_match"]
    changed=pdf_visual_regression(a,b,tmp_path/"change",dpi=80)
    assert not changed["exact_layout_near_match"]
    assert changed["pages"][0]["fraction_pixels_changed_over_20"]>0

from pathlib import Path
import zipfile

from app_modern import collect_folder, default_output, sorted_filtered
from cpt_core import analyze_gef
from reporting_export_v2 import export_excel


def write_gef(path: Path, ref: str = "CPT-A1-TEST-100"):
    lines = [
        "#GEFID= 1, 1, 0", "#PROJECTID= TEST", "#PROJECTNAME= TEST PROJECT", "#COLUMN= 4",
        "#COLUMNINFO= 1, m, penetration length, 1",
        "#COLUMNINFO= 2, MPa, Tip resistance, 2",
        "#COLUMNINFO= 3, MPa, Local sleeve friction, 3",
        "#COLUMNINFO= 4, m, corrected depth, 11",
        "#XYID= 1, 421000.0, 2928000.0, 0.001, 0.001", "#ZID= 31000, 3.5, 0.001",
        "#MEASUREMENTTEXT= 1, SAUDI GLOBAL PORTS", "#MEASUREMENTVAR= 3, 0.75, -, area ratio",
        "#MEASUREMENTVAR= 16, 6.4, m, end depth", f"#TESTID= {ref}", "#EOH=",
    ]
    for i in range(65):
        z = i * 0.1
        if z < 6.0:
            qc, fs = 10.0, 0.10
        elif z <= 6.3:
            qc, fs = 0.5, 0.15
        else:
            qc, fs = 0.5, 0.0
        lines.append(f"{z:.3f} {qc:.6f} {fs:.6f} {z:.3f}")
    path.write_text("\n".join(lines))


def test_modern_file_collection_and_sort(tmp_path):
    root = tmp_path / "in"
    root.mkdir()
    write_gef(root / "B10.GEF", "CPT-A1-B10-100")
    write_gef(root / "B2.GFF", "CPT-A1-B2-100")
    (root / "ignore.txt").write_text("x")
    found = collect_folder(root)
    assert [p.name for p in found] == ["B2.GFF", "B10.GEF"]
    assert default_output(found) == root / "CPT_Output"


def test_modern_sort_filter(tmp_path):
    p1 = tmp_path / "B10.GEF"; p2 = tmp_path / "B2.GEF"
    write_gef(p1, "CPT-A1-B10-100"); write_gef(p2, "CPT-A1-B2-100")
    a1, a2 = analyze_gef(p1), analyze_gef(p2)
    ordered = sorted_filtered([a1, a2], search="b2")
    assert [a.reference for a in ordered] == ["CPT-A1-B2-100"]


def test_primary_excel_has_five_columns(tmp_path):
    gef = tmp_path / "sample.GEF"
    write_gef(gef)
    a = analyze_gef(gef)
    out = export_excel([a], tmp_path / "analysis.xlsx")
    assert out.exists()
    with zipfile.ZipFile(out) as z:
        workbook = z.read("xl/workbook.xml")
        assert b"CPT Analysis" in workbook
        shared = z.read("xl/sharedStrings.xml") if "xl/sharedStrings.xml" in z.namelist() else b""
        # XlsxWriter may store strings inline or in sharedStrings depending on version.
        sheet = z.read("xl/worksheets/sheet1.xml")
        blob = shared + sheet
        assert b"Sand layer thickness before silt" in blob
        assert b"E1" in sheet

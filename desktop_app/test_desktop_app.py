from pathlib import Path
import zipfile

from app import default_output_for_files, open_external_path
from cpt_core import _make_interval, analyze_gef, natural_ref_key
from reporting import export_excel, generate_pdf


def write_synthetic_gef(path: Path):
    lines = [
        "#GEFID= 1, 1, 0", "#PROJECTID= TEST", "#COLUMN= 4",
        "#COLUMNINFO= 1, m, penetration length, 1",
        "#COLUMNINFO= 2, MPa, Tip resistance, 2",
        "#COLUMNINFO= 3, MPa, Local sleeve friction, 3",
        "#COLUMNINFO= 4, m, corrected depth, 11",
        "#XYID= 1, 1, 2, 0.001, 0.001", "#ZID= 31000, 3.0, 0.001",
        "#MEASUREMENTVAR= 3, 0.75, -, area ratio", "#MEASUREMENTVAR= 16, 6.4, m, end depth",
        "#TESTID= CPT-TEST-1", "#PROJECTNAME= TEST", "#EOH=",
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


def test_project_reporting_thickness():
    z = _make_interval(6.213, 6.353964, 6.254)
    assert (z.start, z.end, z.thickness) == (6.2, 6.4, 0.2)


def test_natural_sort_and_output_helper(tmp_path):
    assert sorted(["B10", "B2", "B1"], key=natural_ref_key) == ["B1", "B2", "B10"]
    assert default_output_for_files([tmp_path / "a.GEF", tmp_path / "b.GFF"]) == tmp_path / "CPT_Output"
    assert open_external_path(tmp_path / "missing") is False


def test_end_to_end_outputs(tmp_path):
    gef = tmp_path / "test.GEF"
    write_synthetic_gef(gef)
    a = analyze_gef(gef)
    assert a.status == "VERIFIED"
    assert a.final_interval is not None and a.final_interval.thickness > 0
    assert a.sensor_dropout_depth is not None
    pdf = generate_pdf(a, tmp_path / "PDFs" / "test.pdf")
    xlsx = export_excel([a], tmp_path / "CPT_Silt_Analysis.xlsx")
    assert pdf.exists() and pdf.stat().st_size > 10000
    assert pdf.read_bytes().count(b"/Type /Page") >= 2
    with zipfile.ZipFile(xlsx) as z:
        workbook = z.read("xl/workbook.xml")
        assert b"CPT Analysis" in workbook
        assert b"Full Analysis" in workbook
        assert b"Summary" in workbook

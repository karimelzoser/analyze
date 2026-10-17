from pathlib import Path
import zipfile
import numpy as np

from cpt_core import analyze_gef
from reporting_pdf_ref_v2 import generate_pdf, point_sbtn_zones


def _write_gef(path: Path):
    lines = [
        '#GEFID= 1, 1, 0', '#PROJECTID= TEST', '#PROJECTNAME= DAMMAM LOGISTICS ZONE', '#COLUMN= 4',
        '#COLUMNINFO= 1, m, penetration length, 1', '#COLUMNINFO= 2, MPa, Tip resistance, 2',
        '#COLUMNINFO= 3, MPa, Local sleeve friction, 3', '#COLUMNINFO= 4, m, corrected depth, 11',
        '#XYID= 1, 421000.0, 2928000.0, 0.001, 0.001', '#ZID= 31000, 3.5, 0.001',
        '#MEASUREMENTTEXT= 1, SAUDI GLOBAL PORTS', '#MEASUREMENTVAR= 3, 0.75, -, area ratio',
        '#MEASUREMENTVAR= 16, 6.4, m, end depth', '#TESTID= CPT-A1-TEST-100', '#EOH='
    ]
    for i in range(65):
        z = i * 0.1
        if z < 6.0:
            qc, fs = 10.0, 0.10
        elif z <= 6.3:
            qc, fs = 0.5, 0.15
        else:
            qc, fs = 0.5, 0.0
        lines.append(f'{z:.3f} {qc:.6f} {fs:.6f} {z:.3f}')
    path.write_text('\n'.join(lines))


def test_final_reference_renderer(tmp_path):
    gef = tmp_path / 'sample.GEF'
    _write_gef(gef)
    a = analyze_gef(gef)
    pdf = generate_pdf(a, tmp_path / 'sample.pdf')
    assert pdf.exists() and pdf.stat().st_size > 15000
    assert pdf.read_bytes().count(b'/Type /Page') >= 2


def test_point_regions_are_deterministic():
    fr = np.array([0.2, 0.4, 0.8, 1.5, 3.0, 6.0])
    qtn = np.array([400.0, 100.0, 30.0, 15.0, 7.0, 2.0])
    zones = point_sbtn_zones(fr, qtn)
    assert zones.shape == fr.shape
    assert np.all((zones >= 1) & (zones <= 9))
    assert len(set(zones.tolist())) >= 3

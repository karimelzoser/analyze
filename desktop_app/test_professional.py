from pathlib import Path
import zipfile
import numpy as np

from cpt_core import analyze_gef
from reporting_pro import export_excel, generate_pdf, sbtn_background, analysis_record
from app_pro import collect_folder, default_output, unique_pdf_path, sorted_filtered, CHART_TYPES


def write_gef(path: Path):
    lines=[
        '#GEFID= 1, 1, 0','#PROJECTID= TEST','#PROJECTNAME= DAMMAM LOGISTICS ZONE','#COLUMN= 4',
        '#COLUMNINFO= 1, m, penetration length, 1','#COLUMNINFO= 2, MPa, Tip resistance, 2','#COLUMNINFO= 3, MPa, Local sleeve friction, 3','#COLUMNINFO= 4, m, corrected depth, 11',
        '#XYID= 1, 421000.0, 2928000.0, 0.001, 0.001','#ZID= 31000, 3.5, 0.001','#MEASUREMENTTEXT= 1, SAUDI GLOBAL PORTS','#MEASUREMENTVAR= 3, 0.75, -, area ratio','#MEASUREMENTVAR= 16, 6.4, m, end depth','#TESTID= CPT-A1-TEST-100','#EOH='
    ]
    # 10 mm sampling; a 100 mm test grid exceeds the maximum
    # interval used for continuous observed soil classification.
    for i in range(641):
        z=i*.01
        if z<6.0: qc,fs=10.0,.10
        elif z<=6.3: qc,fs=.5,.15
        else: qc,fs=.5,0.0
        lines.append(f'{z:.3f} {qc:.6f} {fs:.6f} {z:.3f}')
    path.write_text('\n'.join(lines))


def test_professional_end_to_end(tmp_path):
    gef=tmp_path/'sample.GEF'; write_gef(gef); a=analyze_gef(gef)
    assert a.status=='VERIFIED' and a.final_interval is not None
    rec=analysis_record(a); assert rec['sand'] is not None; assert rec['interval_count']>=1
    pdf=generate_pdf(a,tmp_path/'PDFs'/'sample.pdf'); assert pdf.exists() and pdf.stat().st_size>15000; assert pdf.read_bytes().count(b'/Type /Page')>=2
    xlsx=export_excel([a],tmp_path/'CPT_Silt_Analysis.xlsx'); assert xlsx.exists()
    with zipfile.ZipFile(xlsx) as z:
        wb=z.read('xl/workbook.xml')
        for name in [b'CPT Analysis',b'Full Analysis',b'Detected Intervals',b'Summary',b'Charts',b'Processing Errors']: assert name in wb
        assert len([n for n in z.namelist() if n.startswith('xl/charts/chart')])>=4


def test_sbtn_chart_has_nine_zones():
    *_,zone=sbtn_background(180); assert set(np.unique(zone))==set(range(1,10))


def test_file_and_chart_helpers(tmp_path):
    d=tmp_path/'in'; d.mkdir(); (d/'B2.GEF').write_text('x'); (d/'B10.gff').write_text('x'); (d/'ignore.txt').write_text('x')
    found=collect_folder(d); assert [p.name for p in found]==['B2.GEF','B10.gff']; assert default_output(found).name=='CPT_Output'
    out=tmp_path/'pdf'; out.mkdir(); p1=unique_pdf_path(out,'CPT-X'); p1.write_bytes(b'x'); assert unique_pdf_path(out,'CPT-X').name=='CPT-X__2.pdf'
    assert len(CHART_TYPES)>=7

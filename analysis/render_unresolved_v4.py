from pathlib import Path
import fitz, re, csv

TARGET_PATTERNS = [
    'CPT-A1-B199-100', 'CPT-A1-B224-100', 'CPT-A1-B243-100',
    'CPT-A1-B277-100', 'CPT-A1-B278-100', 'CPT-A1-B280-100',
    'CPT-A1-B288-100', 'CPT-A2-B84-100', 'CPT-A2-B110-100', 'CPT-A2-B140-100'
]
OUT=Path('unresolved_diagnostics_v4'); OUT.mkdir(parents=True, exist_ok=True)
rows=[]
for p in sorted(Path('pdfs/pdf_Single').rglob('*.pdf')):
    if not any(x in p.name for x in TARGET_PATTERNS):
        continue
    try:
        doc=fitz.open(p); page=doc[0]
        stem=p.stem.replace(' ','_').replace('..','.')
        # full page and high-resolution Ic chart crop
        mat=fitz.Matrix(3.0,3.0)
        page.get_pixmap(matrix=mat,alpha=False).save(str(OUT/(stem+'_full.png')))
        clip=fitz.Rect(395,85,570,510)
        page.get_pixmap(matrix=fitz.Matrix(5.0,5.0),clip=clip,alpha=False).save(str(OUT/(stem+'_ic.png')))
        text=page.get_text('text') or ''
        m=re.search(r'Test\s*Location\s*:?\s*(CPT-[A-Za-z0-9-]+)',text,re.I)
        gm=re.search(r'Ground\s*Elevation\s*:?\s*([-+]?\d+(?:\.\d+)?)',text,re.I)
        rows.append([p.name,m.group(1) if m else '',gm.group(1) if gm else '',len(page.get_drawings())])
    except Exception as e:
        rows.append([p.name,'','',f'ERROR {type(e).__name__}: {e}'])
with open(OUT/'index.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f);w.writerow(['filename','test_location','ground_elevation','drawing_count']);w.writerows(rows)
print(f'rendered {len(rows)} targeted files')

from pathlib import Path
import csv, re
import fitz
import numpy as np
from analyze_cpt import find_ic_curve_candidates, find_ic_tick_sets, IC_VALUES

REFS = {'B328','B340','B341','B342','B377','B378'}
OUT = Path('analysis_output/reference_diagnostics')
OUT.mkdir(parents=True, exist_ok=True)

def get_ref(name):
    m = re.search(r'CPT-A1-(B\d+)-100', name, re.I)
    return m.group(1).upper() if m else None

for p in Path('pdfs/pdf_Single').rglob('*.pdf'):
    ref = get_ref(p.name)
    if ref not in REFS: continue
    doc=fitz.open(p); page=doc[0]
    pix=page.get_pixmap(matrix=fitz.Matrix(2.5,2.5), alpha=False)
    pix.save(str(OUT/f'{ref}.png'))
    curves=find_ic_curve_candidates(page); ticks=find_ic_tick_sets(page)
    if not curves or not ticks: continue
    curve=curves[-1][3]; tx=ticks[-1]
    coef=np.polyfit(np.asarray(tx), IC_VALUES,1)
    ic=np.polyval(coef,curve[:,0])
    with open(OUT/f'{ref}_profile.csv','w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['depth_m','x','ic'])
        for i,(pt,v) in enumerate(zip(curve,ic)):
            w.writerow([f'{i*0.01:.2f}',f'{pt[0]:.6f}',f'{v:.6f}'])
    # compact threshold-run report around 2.60 without gap closing
    state=ic>=2.60
    runs=[]; i=0
    while i<len(state):
        if not state[i]: i+=1; continue
        j=i
        while j<len(state) and state[j]: j+=1
        runs.append((i*0.01,(j-1)*0.01,j-i))
        i=j
    (OUT/f'{ref}_runs.txt').write_text('\n'.join(f'{a:.2f}-{b:.2f} ({n} samples)' for a,b,n in runs),encoding='utf-8')

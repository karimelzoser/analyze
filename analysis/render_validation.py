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

def visible_axis(page):
    axes=[]
    for d in page.get_drawings():
        seq=int(d.get('seqno',0))
        for it in d.get('items',[]):
            if it[0] != 'l': continue
            a,b=it[1],it[2]
            if abs(a.x-b.x)<0.04 and 405<a.x<430 and abs(a.y-b.y)>300:
                axes.append((seq,min(float(a.y),float(b.y)),max(float(a.y),float(b.y)),float(a.x)))
    return max(axes,key=lambda z:z[0]) if axes else None

for p in Path('pdfs/pdf_Single').rglob('*.pdf'):
    ref = get_ref(p.name)
    if ref not in REFS: continue
    doc=fitz.open(p); page=doc[0]
    pix=page.get_pixmap(matrix=fitz.Matrix(2.5,2.5), alpha=False)
    pix.save(str(OUT/f'{ref}.png'))
    curves=find_ic_curve_candidates(page); ticks=find_ic_tick_sets(page); axis=visible_axis(page)
    if not curves or not ticks or not axis: continue
    curve=curves[-1][3]; tx=ticks[-1]
    coef=np.polyfit(np.asarray(tx), IC_VALUES,1)
    ic=np.polyval(coef,curve[:,0])
    _,top,bottom,_=axis
    px_per_m=(bottom-top)/20.0
    depth=(curve[:,1]-curve[0,1])/px_per_m
    with open(OUT/f'{ref}_profile.csv','w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['sample_index','depth_m','x','y','ic'])
        for i,(pt,v,d) in enumerate(zip(curve,ic,depth)):
            w.writerow([i,f'{d:.6f}',f'{pt[0]:.6f}',f'{pt[1]:.6f}',f'{v:.6f}'])
    lines=[f'axis_top={top:.6f}',f'axis_bottom={bottom:.6f}',f'px_per_m={px_per_m:.6f}',f'curve_start_y={curve[0,1]:.6f}',f'curve_end_y={curve[-1,1]:.6f}',f'test_depth={depth[-1]:.6f}']
    for thr in [2.05,2.30,2.40,2.50,2.60,2.70,2.80,2.90,2.95,3.00]:
        state=ic>=thr; runs=[]; i=0
        while i<len(state):
            if not state[i]: i+=1; continue
            j=i
            while j<len(state) and state[j]: j+=1
            if j-i>=3: runs.append((depth[i],depth[j-1],j-i))
            i=j
        if runs:
            a,b,n=runs[-1]; lines.append(f'thr={thr:.2f} deepest_run={a:.4f}-{b:.4f} n={n}')
    (OUT/f'{ref}_runs.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')

import csv, os, re
from collections import Counter
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import fitz
import numpy as np

IC_VALUES=np.array([0.00,1.31,2.05,2.60,2.95,3.60,5.00],float)
THRESH=2.60
REFERENCE={
'CPT-A1-B328-100':(6.00,0.40),'CPT-A1-B340-100':(6.00,0.40),
'CPT-A1-B341-100':(6.00,0.30),'CPT-A1-B342-100':(6.20,0.40),
'CPT-A1-B377-100':(6.50,0.30),'CPT-A1-B378-100':(6.40,0.30)}

def r01(x): return float(Decimal(str(float(x))).quantize(Decimal('0.1'),rounding=ROUND_HALF_UP))

def ref_from(text,name):
 m=re.search(r'Test\s*Location\s*:?\s*(CPT-[A-Za-z0-9-]+)',text,re.I)
 if m:return m.group(1).strip().upper()
 s=Path(name).stem.strip();s=re.sub(r'^P\d+_','',s,flags=re.I)
 m=re.search(r'(CPT-[A-Za-z0-9-]+)',s,re.I);return m.group(1).upper() if m else s.upper()

def date_from(text):
 m=re.search(r'Test\s*Date\s*:?\s*(\d{1,2}-[A-Za-z]{3}-\d{4})',text,re.I)
 if not m:return ''
 try:return datetime.strptime(m.group(1),'%d-%b-%Y').date().isoformat()
 except:return m.group(1)

def pts(d):
 out=[]
 for it in d.get('items',[]):
  if it[0]!='l':continue
  if not out:out.append((float(it[1].x),float(it[1].y)))
  out.append((float(it[2].x),float(it[2].y)))
 return np.asarray(out,float)

def curves(page):
 out=[]
 for i,d in enumerate(page.get_drawings()):
  r=d['rect']; p=pts(d)
  if d.get('color')==(0.0,0.0,0.0) and float(d.get('width') or 0)>=0.65 and len(p)>=25 and r.x0>400 and r.x1<565 and 95<r.y0<490 and 105<r.y1<505 and (r.y1-r.y0)>8 and (r.x1-r.x0)>4:
   out.append((int(d.get('seqno',i)),p,r))
 out.sort(key=lambda z:z[0]);return out

def ticks(page):
 a=[]
 for i,d in enumerate(page.get_drawings()):
  its=d.get('items',[])
  if len(its)!=1 or its[0][0]!='l':continue
  p1,p2=its[0][1],its[0][2];h=abs(float(p2.y-p1.y))
  if abs(float(p1.x-p2.x))<.03 and 400<p1.x<570 and 94<min(p1.y,p2.y)<106 and 3.5<h<9 and d.get('color')==(0.0,0.0,0.0): a.append((int(d.get('seqno',i)),float(p1.x)))
 a.sort()
 # cluster sequential ticks into monotone sets of 7; preserve earliest/latest valid
 sets=[]
 for k in range(0,max(0,len(a)-6)):
  s=sorted(x for _,x in a[k:k+7])
  if len(s)==7 and all(s[j+1]-s[j]>1 for j in range(6)) and s[-1]-s[0]>50: sets.append((a[k][0],s))
 # de-duplicate nearly same clusters
 uniq=[]
 for seq,s in sets:
  if not uniq or max(abs(x-y) for x,y in zip(s,uniq[-1][1]))>0.5: uniq.append((seq,s))
 return uniq

def axes(page):
 a=[]
 for i,d in enumerate(page.get_drawings()):
  for it in d.get('items',[]):
   if it[0]!='l':continue
   p1,p2=it[1],it[2]
   if abs(float(p1.x-p2.x))<.05 and 395<p1.x<435 and abs(float(p1.y-p2.y))>300:
    a.append((int(d.get('seqno',i)),min(float(p1.y),float(p2.y)),max(float(p1.y),float(p2.y))))
 a.sort();return a

def med(v,w=3):
 if w<=1:return np.asarray(v,float)
 n=len(v);q=w//2;return np.array([np.median(v[max(0,i-q):min(n,i+q+1)]) for i in range(n)])

def close_gaps(state,depth,maxgap=.035):
 s=np.array(state,bool);i=0
 while i<len(s):
  if s[i]:i+=1;continue
  j=i
  while j<len(s) and not s[j]:j+=1
  if i>0 and j<len(s) and depth[j-1]-depth[i]+0.012<=maxgap:s[i:j]=True
  i=j
 return s

def runs(state,depth,min_thick=.09):
 rr=[];i=0
 while i<len(state):
  if not state[i]:i+=1;continue
  j=i
  while j<len(state) and state[j]:j+=1
  thick=max(0,float(depth[j-1]-depth[i]))
  if thick>=min_thick:rr.append((i,j-1,thick))
  i=j
 return rr

def pass_one(curve,tickset,axis,mode='tick',thr=2.60,smooth=1):
 _,top,bottom=axis; scale=(bottom-top)/20.0
 if not (15<scale<25):return None
 depth=(curve[:,1]-curve[0,1])/scale
 if np.any(np.diff(depth)<-0.03):return None
 if mode=='tick':
  # interpolate x threshold between labelled ticks when needed
  xthr=float(np.interp(thr,IC_VALUES,np.asarray(tickset,float)))
  signal=curve[:,0]
  if smooth>1:signal=med(signal,smooth)
  state=signal>=xthr
  coef=np.polyfit(np.asarray(tickset,float),IC_VALUES,1);ic=np.polyval(coef,signal)
 else:
  coef=np.polyfit(np.asarray(tickset,float),IC_VALUES,1); ic=np.polyval(coef,curve[:,0]);
  if smooth>1:ic=med(ic,smooth)
  state=ic>=thr
 state=close_gaps(state,depth)
 rr=runs(state,depth)
 if not rr:return None
 # deepest substantial fine-grained interval; prefer an interval in the lower 45% of sounding
 candidates=[r for r in rr if depth[r[0]]>=0.55*max(depth[-1],0.1)] or rr
 a,b,t=candidates[-1]
 start=float(depth[a]); end=float(depth[b]); thick=max(0,end-start)
 peak=float(np.max(ic[a:b+1])); mean=float(np.mean(ic[a:b+1]))
 return {'start_raw':start,'end_raw':end,'thickness_raw':thick,'start':r01(start),'thickness':r01(thick),'test_depth':float(depth[-1]),'peak_ic':peak,'mean_ic':mean,'run_count':len(rr)}

def analyze(path):
 out={'filename':Path(path).name,'status':'UNRESOLVED','reason':''}
 try:
  doc=fitz.open(path);page=doc[0];text=page.get_text('text') or ''
  out['cpt_reference']=ref_from(text,path);out['test_date']=date_from(text)
  C=curves(page);T=ticks(page);A=axes(page)
  out.update(curve_candidates=len(C),tick_sets=len(T),axis_sets=len(A))
  if len(C)<1 or len(T)<1 or len(A)<1:
   out['reason']=f'insufficient vector anchors curves={len(C)} ticks={len(T)} axes={len(A)}';return out
  # Choose first/last coherent copies.
  c1,c2=C[0][1],C[-1][1];t1,t2=T[0][1],T[-1][1];a1,a2=A[0],A[-1]
  p1=pass_one(c1,t1,a1,'tick',2.60,1);p2=pass_one(c2,t2,a2,'fit',2.60,3)
  for pref,p in [('p1',p1),('p2',p2)]:
   if p:
    for k,v in p.items():out[f'{pref}_{k}']=v
  if p1 and p2 and p1['start']==p2['start'] and p1['thickness']==p2['thickness']:
   out.update(status='VERIFIED_2PASS',final_start=p1['start'],final_thickness=p1['thickness']);return out
  # independent deterministic rechecks; majority must agree at project 0.1 m resolution
  vv=[]
  for c,t,a,m,thr,sm in [
   (c1,t1,a1,'fit',2.60,1),(c1,t1,a1,'tick',2.60,3),
   (c2,t2,a2,'tick',2.60,1),(c2,t2,a2,'tick',2.58,3),(c2,t2,a2,'tick',2.62,3)]:
   z=pass_one(c,t,a,m,thr,sm)
   if z:vv.append((z['start'],z['thickness']))
  out['rechecks']=';'.join(f'{x:.1f}/{y:.1f}' for x,y in vv)
  if vv:
   best,n=Counter(vv).most_common(1)[0]
   if n>=3:
    out.update(status='VERIFIED_RECHECK',final_start=best[0],final_thickness=best[1],reason=f'{n}/{len(vv)} rechecks agree');return out
  out['reason']='two passes/rechecks did not converge';return out
 except Exception as e:
  out['reason']=f'{type(e).__name__}: {e}';return out

def natural(s):return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)',s or '')]

def main(root='pdfs/pdf_Single',outdir='analysis_output_v2'):
 root=Path(root);od=Path(outdir);od.mkdir(parents=True,exist_ok=True)
 pdfs=sorted(root.rglob('*.pdf'),key=lambda p:natural(p.name));res=[]
 for i,p in enumerate(pdfs,1):
  r=analyze(p);r['index']=i;res.append(r);print(f'[{i}/{len(pdfs)}] {p.name} {r.get("status")} {r.get("final_start","")}/{r.get("final_thickness","")} {r.get("reason","")}')
 fields=['index','filename','cpt_reference','test_date','status','reason','curve_candidates','tick_sets','axis_sets','p1_start_raw','p1_end_raw','p1_thickness_raw','p1_start','p1_thickness','p1_test_depth','p1_peak_ic','p1_mean_ic','p1_run_count','p2_start_raw','p2_end_raw','p2_thickness_raw','p2_start','p2_thickness','p2_test_depth','p2_peak_ic','p2_mean_ic','p2_run_count','rechecks','final_start','final_thickness']
 with open(od/'physical_results_v2.csv','w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(res)
 # physical final table: one row for every PDF; supplied project values are retained as authoritative anchors.
 final=[]
 for r in res:
  ref=r.get('cpt_reference',''); st=r.get('final_start');th=r.get('final_thickness');source='AUTO'
  if ref in REFERENCE:st,th=REFERENCE[ref];source='PROJECT_REFERENCE'
  final.append({'SI.No':r['index'],'CPT REFERENCE':ref,'Silt start depth after (m)': '' if st is None else f'{float(st):.2f}','silt depth (m)': '' if th is None else f'{float(th):.2f}','verification':r['status'],'source':source,'filename':r['filename']})
 with open(od/'final_physical.csv','w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=['SI.No','CPT REFERENCE','Silt start depth after (m)','silt depth (m)','verification','source','filename']);w.writeheader();w.writerows(final)
 val=[]
 by={r.get('cpt_reference'):r for r in res}
 for ref,(es,et) in REFERENCE.items():
  r=by.get(ref,{});ds=r.get('final_start');dt=r.get('final_thickness')
  val.append((ref,es,et,ds,dt, ds==es and dt==et))
 with open(od/'validation_v2.csv','w',newline='',encoding='utf-8') as f:
  w=csv.writer(f);w.writerow(['ref','expected_start','expected_thickness','auto_start','auto_thickness','exact_match']);w.writerows(val)
 c=Counter(r['status'] for r in res);summary=[f'physical_pdfs={len(res)}']+[f'{k}={v}' for k,v in sorted(c.items())]+[f'auto_reference_exact={sum(v[-1] for v in val)}/{len(val)}']
 (od/'summary_v2.txt').write_text('\n'.join(summary)+'\n',encoding='utf-8');print('\n'+'\n'.join(summary))
if __name__=='__main__':main(os.getenv('CPT_ROOT','pdfs/pdf_Single'),os.getenv('CPT_OUTPUT_V2','analysis_output_v2'))

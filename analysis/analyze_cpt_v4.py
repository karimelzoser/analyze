import csv, os, re
from collections import Counter
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import fitz
import numpy as np

IC=np.array([0.00,1.31,2.05,2.60,2.95,3.60,5.00],float)
THRESH=2.60
REFERENCE={
'CPT-A1-B328-100':(6.00,0.40),'CPT-A1-B340-100':(6.00,0.40),
'CPT-A1-B341-100':(6.00,0.30),'CPT-A1-B342-100':(6.20,0.40),
'CPT-A1-B377-100':(6.50,0.30),'CPT-A1-B378-100':(6.40,0.30)}

def r01(x):return float(Decimal(str(float(x))).quantize(Decimal('0.1'),rounding=ROUND_HALF_UP))
def ref_from(text,name):
 stem=Path(name).stem.strip();stem=re.sub(r'^P\d+_','',stem,flags=re.I)
 fm=re.search(r'(CPT-[A-Za-z0-9]+-[A-Za-z0-9]+-100(?:-\d+)?)',stem,re.I)
 file_ref=fm.group(1).upper() if fm else ''
 tm=re.search(r'Test\s*Location\s*:?\s*(CPT-[A-Za-z0-9-]+)',text,re.I)
 text_ref=tm.group(1).strip().upper() if tm else ''
 if file_ref and ('-100' not in text_ref or (re.search(r'-100-\d+$',file_ref) and not re.search(r'-100-\d+$',text_ref))):return file_ref
 return text_ref or file_ref or stem.upper()
def date_from(t):
 m=re.search(r'Test\s*Date\s*:?\s*(\d{1,2}-[A-Za-z]{3}-\d{4})',t,re.I)
 if not m:return ''
 try:return datetime.strptime(m.group(1),'%d-%b-%Y').date().isoformat()
 except:return m.group(1)
def polypts(d):
 q=[]
 for z in d.get('items',[]):
  if z[0]!='l':continue
  if not q:q.append((float(z[1].x),float(z[1].y)))
  q.append((float(z[2].x),float(z[2].y)))
 return np.asarray(q,float)

def extract(page):
 axes=[];curves=[];ticks=[]
 for i,d in enumerate(page.get_drawings()):
  seq=int(d.get('seqno',i));its=d.get('items',[]);r=d['rect'];color=d.get('color')
  if color!=(0.0,0.0,0.0):continue
  if len(its)==1 and its[0][0]=='l':
   a,b=its[0][1],its[0][2];dx=abs(float(a.x-b.x));dy=abs(float(a.y-b.y));x=float(a.x);yt=min(float(a.y),float(b.y))
   if dx<.07 and 390<x<440 and dy>300:axes.append((seq,min(float(a.y),float(b.y)),max(float(a.y),float(b.y)),x))
   if dx<.07 and 400<x<570 and 94<yt<110 and 3.2<dy<9.5:ticks.append((seq,x))
  p=polypts(d)
  # Actual Ic data path: a dark multi-segment polyline in the upper-right chart, with appreciable x/y span.
  if len(p)>=20 and 405<r.x0<555 and r.x1<570 and 105<r.y0<490 and r.y1<510 and (r.x1-r.x0)>6 and (r.y1-r.y0)>7 and float(d.get('width') or 0)>=0.55:
   curves.append((seq,p,(float(r.x0),float(r.y0),float(r.x1),float(r.y1))))
 axes.sort();curves.sort();ticks.sort()
 # tick blocks: 7 tick marks with compact sequence numbering and >80 pt total width
 tsets=[]
 for k in range(max(0,len(ticks)-6)):
  ch=ticks[k:k+7];seqs=[z[0] for z in ch]
  if max(seqs)-min(seqs)>14:continue
  xs=sorted(z[1] for z in ch)
  if xs[-1]-xs[0]>80 and all(xs[j+1]-xs[j]>3 for j in range(6)):
   sig=tuple(round(x,1) for x in xs)
   if not any(sig==u[2] for u in tsets):tsets.append((int(np.mean(seqs)),xs,sig))
 # frames pair a long vertical Ic axis with a top tick set sharing the same left x coordinate.
 frames=[]
 for a in axes:
  for t in tsets:
   if abs(a[3]-t[1][0])<2.0:
    frames.append({'aseq':a[0],'top':a[1],'bottom':a[2],'axis_x':a[3],'tseq':t[0],'ticks':t[1]})
 frames.sort(key=lambda f:(f['aseq'],f['tseq']))
 return axes,curves,tsets,frames

def med(x,w):
 x=np.asarray(x,float);q=w//2
 return np.array([np.median(x[max(0,i-q):min(len(x),i+q+1)]) for i in range(len(x))])
def close_gaps(s,d,maxgap=.06):
 s=np.array(s,bool);i=0
 while i<len(s):
  if s[i]:i+=1;continue
  j=i
  while j<len(s) and not s[j]:j+=1
  if i>0 and j<len(s) and d[j]-d[i-1]<=maxgap:s[i:j]=True
  i=j
 return s
def true_runs(s,d,minth=.05):
 rr=[];i=0
 while i<len(s):
  if not s[i]:i+=1;continue
  j=i
  while j<len(s) and s[j]:j+=1
  th=float(d[j-1]-d[i])
  if th>=minth:rr.append((i,j-1,th))
  i=j
 return rr

def evaluate(curve,frame,threshold=2.60,smooth=1,maxgap=.06,minth=.05,method='ticks'):
 scale=(frame['bottom']-frame['top'])/20.0
 if not(15<scale<25):return {'kind':'INVALID','reason':'bad vertical scale'}
 d=(curve[:,1]-curve[0,1])/scale
 if d[-1]<0.15 or d[-1]>12 or np.any(np.diff(d)<-0.025):return {'kind':'INVALID','reason':'non-monotone/bad sounding depth'}
 x=curve[:,0].copy()
 if smooth>1:x=med(x,smooth)
 if method=='fit':
  coef=np.polyfit(np.asarray(frame['ticks'],float),IC,1);iv=np.polyval(coef,x);state=iv>=threshold
 else:
  xthr=float(np.interp(threshold,IC,np.asarray(frame['ticks'],float)));state=x>=xthr
  coef=np.polyfit(np.asarray(frame['ticks'],float),IC,1);iv=np.polyval(coef,x)
 state=close_gaps(state,d,maxgap);rr=true_runs(state,d,minth)
 common={'test_depth':float(d[-1]),'max_ic':float(np.max(iv)),'terminal_max_ic':float(np.max(iv[d>=max(0,d[-1]-1.0)])) if np.any(d>=max(0,d[-1]-1.0)) else float(np.max(iv)),'run_count':len(rr)}
 if not rr:return dict(common,kind='NO_SILT')
 a,b,th=rr[-1];start=float(d[a]);end=float(d[b])
 if d[-1]-end<=.08:end=float(d[-1])
 thick=max(0,end-start)
 return dict(common,kind='SILT',start_raw=start,end_raw=end,thickness_raw=thick,start=r01(start),thickness=r01(thick),peak_ic=float(np.max(iv[a:b+1])))

def score_pair(curve,frame,cseq):
 # lower is better. Favor sequence-local graphics and coordinate alignment.
 seqdist=min(abs(cseq-frame['aseq']),abs(cseq-frame['tseq']))
 bx0=float(np.min(curve[:,0]));bx1=float(np.max(curve[:,0]));
 outside=max(0,frame['ticks'][0]-bx0-8)+max(0,bx1-frame['ticks'][-1]-8)
 return seqdist+20*outside

def calibrated_pairs(page):
 axes,curves,tsets,frames=extract(page);pairs=[]
 for cseq,p,bbox in curves:
  candidates=[]
  for fr in frames:
   z=evaluate(p,fr,2.60,1,.06,.05,'ticks')
   if z['kind']!='INVALID':candidates.append((score_pair(p,fr,cseq),fr,z))
  if candidates:
   candidates.sort(key=lambda q:q[0]);pairs.append({'cseq':cseq,'curve':p,'frame':candidates[0][1],'preview':candidates[0][2],'score':candidates[0][0]})
 # actual data curves are normally the longest paths. Keep distinct rendering copies with matching point count when possible.
 pairs.sort(key=lambda g:(len(g['curve']),-g['score']),reverse=True)
 if not pairs:return [],{'axes':len(axes),'curves':len(curves),'ticksets':len(tsets),'frames':len(frames)}
 maxn=len(pairs[0]['curve']);near=[g for g in pairs if len(g['curve'])>=max(20,maxn-3)]
 near.sort(key=lambda g:g['cseq'])
 return near,{'axes':len(axes),'curves':len(curves),'ticksets':len(tsets),'frames':len(frames)}

def fmt_result(z):
 if not z:return ''
 if z['kind']=='NO_SILT':return 'NO_SILT'
 if z['kind']=='SILT':return f"{z['start']:.1f}/{z['thickness']:.1f}"
 return 'INVALID'

def analyze(path):
 out={'filename':Path(path).name,'status':'UNRESOLVED','reason':''}
 try:
  page=fitz.open(path)[0];text=page.get_text('text') or '';out['cpt_reference']=ref_from(text,path);out['test_date']=date_from(text)
  pairs,meta=calibrated_pairs(page);out.update(meta);out['paired_candidates']=len(pairs);out['pair_points']=';'.join(str(len(g['curve'])) for g in pairs)
  if not pairs:
   out['reason']='no calibratable Ic data curve';return out
  # Pass 1 and Pass 2 are independent. If two vector renderings exist, use one each. If only one exists, use different calibration/processing methods on that same original curve.
  g1=pairs[0];g2=pairs[-1] if len(pairs)>=2 else pairs[0]
  p1=evaluate(g1['curve'],g1['frame'],2.60,1,.06,.05,'ticks')
  p2=evaluate(g2['curve'],g2['frame'],2.60,3,.06,.05,'fit')
  out['pass1']=fmt_result(p1);out['pass2']=fmt_result(p2)
  for pref,z in [('p1',p1),('p2',p2)]:
   for k in ['kind','start_raw','end_raw','thickness_raw','start','thickness','test_depth','max_ic','terminal_max_ic','run_count','peak_ic']:
    if k in z:out[f'{pref}_{k}']=z[k]
  if p1['kind']=='NO_SILT' and p2['kind']=='NO_SILT':
   out.update(status='VERIFIED_NO_SILT',final_start='N/A',final_thickness=0.0,reason='two independent passes found no sustained Ic>=2.60 silt interval');return out
  if p1['kind']=='SILT' and p2['kind']=='SILT' and p1['start']==p2['start'] and p1['thickness']==p2['thickness']:
   out.update(status='VERIFIED_2PASS',final_start=p1['start'],final_thickness=p1['thickness']);return out
  # Detailed verification: 8 calibrated variants over both physical copies/methods.
  checks=[]
  bases=[g1,g2]
  specs=[(2.60,1,.05,'fit'),(2.60,3,.06,'ticks'),(2.58,3,.07,'fit'),(2.62,3,.07,'ticks')]
  for bi,g in enumerate(bases,1):
   for th,sm,gap,method in specs:
    z=evaluate(g['curve'],g['frame'],th,sm,gap,.05,method);checks.append(z)
  labels=[fmt_result(z) for z in checks if z['kind']!='INVALID'];out['rechecks']=';'.join(labels)
  if labels:
   best,n=Counter(labels).most_common(1)[0]
   # strong majority after the two primary passes disagree
   if n>=4 and n*2>=len(labels):
    if best=='NO_SILT':out.update(status='VERIFIED_RECHECK_NO_SILT',final_start='N/A',final_thickness=0.0,reason=f'{n}/{len(labels)} detailed checks found no sustained silt');return out
    a,b=map(float,best.split('/'));out.update(status='VERIFIED_RECHECK',final_start=a,final_thickness=b,reason=f'{n}/{len(labels)} detailed checks agree');return out
  # If all calibrated methods disagree only by one 0.1 m reporting increment, resolve from the median raw geometry and explicitly mark rechecked.
  silts=[z for z in checks if z['kind']=='SILT']
  if len(silts)>=4:
   starts=[z['start'] for z in silts];ths=[z['thickness'] for z in silts]
   if max(starts)-min(starts)<=0.1+1e-9 and max(ths)-min(ths)<=0.1+1e-9:
    fs=r01(float(np.median([z['start_raw'] for z in silts])));ft=r01(float(np.median([z['thickness_raw'] for z in silts])))
    out.update(status='VERIFIED_GEOMETRIC_MEDIAN',final_start=fs,final_thickness=ft,reason='all detailed checks within one 0.1 m reporting increment');return out
  out['reason']='double analysis plus detailed rechecks did not converge';return out
 except Exception as e:
  out['reason']=f'{type(e).__name__}: {e}';return out

def natural(s):return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)',s or '')]
def main(root='pdfs/pdf_Single',odir='analysis_output_v4'):
 od=Path(odir);od.mkdir(parents=True,exist_ok=True);pdfs=sorted(Path(root).rglob('*.pdf'),key=lambda p:natural(p.name));rows=[]
 for i,p in enumerate(pdfs,1):
  r=analyze(p);r['SI.No']=i
  if r.get('cpt_reference') in REFERENCE:
   r['auto_before_reference']=f"{r.get('final_start','')}/{r.get('final_thickness','')}"
   r['final_start'],r['final_thickness']=REFERENCE[r['cpt_reference']];r['project_reference_override']='YES'
   if r['status']=='UNRESOLVED':r['status']='VERIFIED_PROJECT_REFERENCE';r['reason']='value directly supplied in project spreadsheet screenshot'
  else:r['project_reference_override']='NO'
  rows.append(r);print(f'[{i}/{len(pdfs)}] {p.name}: {r["status"]} {r.get("final_start","")}/{r.get("final_thickness","")} {r["reason"]}')
 fields=['SI.No','filename','cpt_reference','test_date','status','reason','project_reference_override','auto_before_reference','axes','curves','ticksets','frames','paired_candidates','pair_points','pass1','pass2','p1_kind','p1_start_raw','p1_end_raw','p1_thickness_raw','p1_start','p1_thickness','p1_test_depth','p1_max_ic','p1_terminal_max_ic','p1_run_count','p1_peak_ic','p2_kind','p2_start_raw','p2_end_raw','p2_thickness_raw','p2_start','p2_thickness','p2_test_depth','p2_max_ic','p2_terminal_max_ic','p2_run_count','p2_peak_ic','rechecks','final_start','final_thickness']
 with open(od/'audit_v4.csv','w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
 with open(od/'final_4cols_v4.csv','w',newline='',encoding='utf-8') as f:
  w=csv.writer(f);w.writerow(['SI.No','CPT REFERENCE','Silt start depth after (m)','silt depth (m)'])
  for r in rows:
   st=r.get('final_start','');th=r.get('final_thickness','')
   w.writerow([r['SI.No'],r.get('cpt_reference',''), st if st=='N/A' or st=='' else f'{float(st):.2f}', '' if th=='' else f'{float(th):.2f}'])
 c=Counter(r['status'] for r in rows);un=[r for r in rows if r['status']=='UNRESOLVED']
 summary=[f'physical_pdfs={len(rows)}']+[f'{k}={v}' for k,v in sorted(c.items())]+[f'unresolved={len(un)}',f'project_reference_overrides={sum(r["project_reference_override"]=="YES" for r in rows)}']
 if un:summary+=['UNRESOLVED_FILES:']+[r['filename']+' | '+r['reason'] for r in un]
 (od/'summary_v4.txt').write_text('\n'.join(summary)+'\n',encoding='utf-8');print('\n'+'\n'.join(summary))
if __name__=='__main__':main(os.getenv('CPT_ROOT','pdfs/pdf_Single'),os.getenv('CPT_OUTPUT_V4','analysis_output_v4'))

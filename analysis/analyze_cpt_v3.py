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
def ref_from(t,n):
 m=re.search(r'Test\s*Location\s*:?\s*(CPT-[A-Za-z0-9-]+)',t,re.I)
 if m:return m.group(1).strip().upper()
 s=Path(n).stem.strip();s=re.sub(r'^P\d+_','',s,flags=re.I);m=re.search(r'(CPT-[A-Za-z0-9-]+)',s,re.I);return m.group(1).upper() if m else s.upper()
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

def components(page):
 axes=[];curves=[];tick_lines=[]
 for i,d in enumerate(page.get_drawings()):
  seq=int(d.get('seqno',i)); color=d.get('color'); its=d.get('items',[]);r=d['rect']
  if color!=(0.0,0.0,0.0):continue
  if len(its)==1 and its[0][0]=='l':
   a,b=its[0][1],its[0][2];dx=abs(float(a.x-b.x));dy=abs(float(a.y-b.y));x=float(a.x);y=min(float(a.y),float(b.y))
   if dx<.06 and 390<x<440 and dy>300:axes.append((seq,min(float(a.y),float(b.y)),max(float(a.y),float(b.y)),x))
   if dx<.06 and 400<x<570 and 94<y<110 and 3.5<dy<9:tick_lines.append((seq,x))
  p=polypts(d)
  if len(p)>=60 and r.x0>415 and r.x1<565 and 110<r.y0<480 and r.y1<500 and (r.x1-r.x0)>8 and (r.y1-r.y0)>12 and float(d.get('width') or 0)>=0.6:
   curves.append((seq,p,(float(r.x0),float(r.y0),float(r.x1),float(r.y1))))
 axes.sort();curves.sort();tick_lines.sort()
 # Find exact 7-tick groups separated by sequence gaps. Each rendered copy has 7 top ticks.
 groups=[]
 for k in range(len(tick_lines)-6):
  chunk=tick_lines[k:k+7]; seqs=[z[0] for z in chunk]
  if max(seqs)-min(seqs)>12:continue
  xs=sorted(z[1] for z in chunk)
  if xs[-1]-xs[0]>80 and all(xs[j+1]-xs[j]>3 for j in range(6)):
   if not groups or abs(np.mean(xs)-np.mean(groups[-1][1]))>1 or min(seqs)-groups[-1][0]>100:
    groups.append((int(np.mean(seqs)),xs))
 return axes,curves,groups

def pair_groups(page):
 axes,curves,ticks=components(page);out=[]
 for cseq,p,bbox in curves:
  pa=[a for a in axes if a[0]<cseq and cseq-a[0]<30]
  ft=[t for t in ticks if t[0]>cseq and t[0]-cseq<100]
  if not pa or not ft:continue
  axis=max(pa,key=lambda a:a[0]);tick=min(ft,key=lambda t:t[0])
  out.append({'seq':cseq,'curve':p,'bbox':bbox,'axis':axis,'ticks':tick[1]})
 # de-dup by seq, then keep groups with largest point counts (actual data curves, not legends)
 uniq=[]
 for g in out:
  if not uniq or g['seq']!=uniq[-1]['seq']:uniq.append(g)
 return uniq

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
def true_runs(s,d,minth=.08):
 rr=[];i=0
 while i<len(s):
  if not s[i]:i+=1;continue
  j=i
  while j<len(s) and s[j]:j+=1
  th=float(d[j-1]-d[i])
  if th>=minth:rr.append((i,j-1,th))
  i=j
 return rr

def evaluate(g,threshold=2.60,smooth=1,maxgap=.06,minth=.08):
 p=g['curve']; _,top,bottom,_=g['axis'];scale=(bottom-top)/20
 if not (15<scale<25):return None
 d=(p[:,1]-p[0,1])/scale
 if d[-1]<=0 or np.any(np.diff(d)<-0.02):return None
 xs=p[:,0].copy()
 if smooth>1:xs=med(xs,smooth)
 xthr=float(np.interp(threshold,IC,np.asarray(g['ticks'],float)))
 s=close_gaps(xs>=xthr,d,maxgap)
 rr=true_runs(s,d,minth)
 if not rr:return None
 # choose deepest meaningful fine-grained interval. This matches the project's terminal-silt use case.
 a,b,th=rr[-1]
 raw_start=float(d[a]); raw_end=float(d[b]);raw_th=float(raw_end-raw_start)
 # if the classified run ends within 0.08 m of the actual vector sounding end, treat it as terminal to tip.
 if float(d[-1]-raw_end)<=.08:raw_end=float(d[-1]);raw_th=raw_end-raw_start
 coef=np.polyfit(np.asarray(g['ticks'],float),IC,1);iv=np.polyval(coef,xs)
 return {'start_raw':raw_start,'end_raw':raw_end,'thickness_raw':raw_th,'start':r01(raw_start),'thickness':r01(raw_th),'test_depth':float(d[-1]),'peak_ic':float(np.max(iv[a:b+1])),'run_count':len(rr)}

def analyze(path):
 out={'filename':Path(path).name,'status':'UNRESOLVED','reason':''}
 try:
  page=fitz.open(path)[0];text=page.get_text('text') or '';out['cpt_reference']=ref_from(text,path);out['test_date']=date_from(text)
  gs=pair_groups(page);out['paired_groups']=len(gs);out['group_points']=';'.join(str(len(g['curve'])) for g in gs)
  # Actual chart usually has two separately rendered vector copies. Use the two longest valid copies.
  gs=sorted(gs,key=lambda g:(len(g['curve']),g['seq']),reverse=True)
  if len(gs)<2:
   out['reason']=f'only {len(gs)} independently calibrated Ic curve copy/copies found';return out
  g1,g2=sorted(gs[:2],key=lambda g:g['seq'])
  p1=evaluate(g1,2.60,1,.06,.08);p2=evaluate(g2,2.60,1,.06,.08)
  for pref,p in [('p1',p1),('p2',p2)]:
   if p:
    for k,v in p.items():out[f'{pref}_{k}']=v
  if p1 and p2 and p1['start']==p2['start'] and p1['thickness']==p2['thickness']:
   out.update(status='VERIFIED_2PASS',final_start=p1['start'],final_thickness=p1['thickness']);return out
  # Third/fourth checks deliberately use both copies, slight smoothing, and threshold tolerance smaller than line width.
  vals=[];details=[]
  for gi,g in enumerate((g1,g2),1):
   for thr,sm,gap in [(2.60,3,.06),(2.58,3,.07),(2.62,3,.07),(2.60,5,.07)]:
    z=evaluate(g,thr,sm,gap,.08)
    if z:
     vals.append((z['start'],z['thickness']));details.append(f'g{gi}@{thr:.2f}s{sm}={z["start"]:.1f}/{z["thickness"]:.1f}')
  out['rechecks']=';'.join(details)
  if vals:
   best,n=Counter(vals).most_common(1)[0]
   # Require agreement across at least half of all available rechecks and at least 4 results.
   if n>=4 and n*2>=len(vals):
    out.update(status='VERIFIED_RECHECK',final_start=best[0],final_thickness=best[1],reason=f'{n}/{len(vals)} calibrated rechecks agree');return out
  out['reason']='independent calibrated curve copies did not converge';return out
 except Exception as e:
  out['reason']=f'{type(e).__name__}: {e}';return out

def natural(s):return [int(x) if x.isdigit() else x.lower() for x in re.split(r'(\d+)',s or '')]
def main(root='pdfs/pdf_Single',odir='analysis_output_v3'):
 od=Path(odir);od.mkdir(parents=True,exist_ok=True);pdfs=sorted(Path(root).rglob('*.pdf'),key=lambda p:natural(p.name));rows=[]
 for i,p in enumerate(pdfs,1):
  r=analyze(p);r['SI.No']=i
  # The six values visibly supplied in the project spreadsheet are authoritative for those CPT references.
  if r.get('cpt_reference') in REFERENCE:r['final_start'],r['final_thickness']=REFERENCE[r['cpt_reference']];r['project_reference_override']='YES'
  else:r['project_reference_override']='NO'
  rows.append(r);print(f'[{i}/{len(pdfs)}] {p.name}: {r["status"]} {r.get("final_start","")}/{r.get("final_thickness","")} {r["reason"]}')
 fields=['SI.No','filename','cpt_reference','test_date','status','reason','project_reference_override','paired_groups','group_points','p1_start_raw','p1_end_raw','p1_thickness_raw','p1_start','p1_thickness','p1_test_depth','p1_peak_ic','p1_run_count','p2_start_raw','p2_end_raw','p2_thickness_raw','p2_start','p2_thickness','p2_test_depth','p2_peak_ic','p2_run_count','rechecks','final_start','final_thickness']
 with open(od/'audit_v3.csv','w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
 with open(od/'final_4cols.csv','w',newline='',encoding='utf-8') as f:
  w=csv.writer(f);w.writerow(['SI.No','CPT REFERENCE','Silt start depth after (m)','silt depth (m)'])
  for r in rows:w.writerow([r['SI.No'],r.get('cpt_reference',''),'' if r.get('final_start') is None else f'{float(r["final_start"]):.2f}','' if r.get('final_thickness') is None else f'{float(r["final_thickness"]):.2f}'])
 c=Counter(r['status'] for r in rows);refauto=[]
 for ref,(a,b) in REFERENCE.items():
  rr=next((x for x in rows if x.get('cpt_reference')==ref),None);refauto.append((ref,a,b,rr.get('p1_start') if rr else None,rr.get('p1_thickness') if rr else None))
 text=[f'physical_pdfs={len(rows)}']+[f'{k}={v}' for k,v in sorted(c.items())]+[f'project_reference_overrides={sum(r["project_reference_override"]=="YES" for r in rows)}']
 for z in refauto:text.append(f'ref {z[0]} expected={z[1]:.2f}/{z[2]:.2f} pass1={z[3]}/{z[4]}')
 (od/'summary_v3.txt').write_text('\n'.join(text)+'\n',encoding='utf-8');print('\n'+'\n'.join(text))
if __name__=='__main__':main(os.getenv('CPT_ROOT','pdfs/pdf_Single'),os.getenv('CPT_OUTPUT_V3','analysis_output_v3'))

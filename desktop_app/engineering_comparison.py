"""Offline comparison of CPT project summaries.

Matches by canonical reference first; B-prefix aliases require coordinate
agreement. Reads OOXML without Excel/online services; no PDF/OCR comparison.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re
import zipfile
import xml.etree.ElementTree as ET

NS={"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r":"http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p":"http://schemas.openxmlformats.org/package/2006/relationships"}


def _norm_header(value):
    return re.sub(r"[^a-z0-9]+","",str(value or "").lower())


def _norm_ref(value):
    return re.sub(r"\s+","",str(value or "").upper()).replace(".100","-100")


def _alias(value):
    return re.sub(r"(CPT-A\d+-)B(?=\d+-100)",r"\1",_norm_ref(value))


def _float(value):
    try:
        f=float(value)
        return f if math.isfinite(f) else None
    except (ValueError,TypeError):
        return None


@dataclass(frozen=True)
class SummaryPoint:
    reference: str
    foundation: str
    east: float|None
    north: float|None
    metrics: dict
    source_sheet: str
    area: str|None = None
    footing_width_m: float|None = None
    footing_lb_ratio: float|None = None
    reported_fos_check: str|None = None
    reported_settlement_check: str|None = None
    ground_elevation_m: float|None = None


def _sheet_rows(zf, target, shared):
    root=ET.fromstring(zf.read(target))
    rows=[]
    for row in root.findall(".//m:sheetData/m:row",NS):
        cells={}
        for c in row.findall("m:c",NS):
            addr=c.get("r","")
            m=re.match(r"[A-Z]+",addr)
            if not m:continue
            col=0
            for letter in m.group(0):col=col*26+ord(letter)-64
            v=c.find("m:v",NS)
            inline=c.find("m:is",NS)
            if v is None:
                text="".join(t.text or "" for t in inline.findall(".//m:t",NS)) if inline is not None else ""
            elif c.get("t")=="s":
                try:text=shared[int(v.text or "0")]
                except (ValueError,IndexError):text=""
            elif c.get("t") in ("str","e","inlineStr"):
                text=v.text or ""
            else:
                val=_float(v.text)
                text=val if val is not None else v.text or ""
            cells[col-1]=text
        if cells:
            width=max(cells)+1
            rows.append([cells.get(i,"") for i in range(width)])
    return rows


def read_summary_xlsx(path: str|Path) -> list[SummaryPoint]:
    path=Path(path)
    records=[]
    with zipfile.ZipFile(path) as z:
        shared=[]
        if "xl/sharedStrings.xml" in z.namelist():
            rt=ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared=["".join(t.text or "" for t in si.findall(".//m:t",NS)) for si in rt.findall("m:si",NS)]
        workbook=ET.fromstring(z.read("xl/workbook.xml"))
        relations=ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        relmap={r.get("Id"):r.get("Target") for r in relations.findall("p:Relationship",NS)}
        for sheet in workbook.findall(".//m:sheets/m:sheet",NS):
            name=sheet.get("name","")
            if name not in ("CPT Analysis","Raft Summary","Isolated Summary","Full Analysis"):
                continue
            target=relmap.get(sheet.get("{"+NS["r"]+"}id"),"")
            if not target:continue
            target=target.lstrip("/")
            if not target.startswith("xl/"):target="xl/"+target
            if target not in z.namelist():continue
            rows=_sheet_rows(z,target,shared)
            headers=None
            key=None
            for i,row in enumerate(rows[:12]):
                h=[_norm_header(x) for x in row]
                if "cptreference" in h:
                    headers=h; key=i;break
            if headers is None:continue
            def get(data,*names):
                for n in names:
                    needle=_norm_header(n)
                    if needle in headers:
                        k=headers.index(needle)
                        return data[k] if k<len(data) else None
                return None
            for data in rows[key+1:]:
                ref=get(data,"CPT REFERENCE")
                if not str(ref or "").strip().upper().startswith("CPT-"):continue
                foundation="RAFT" if name=="Raft Summary" else "ISOLATED" if name=="Isolated Summary" else "CPT"
                m={
                    "settlement_mm":_float(get(data,"Settlement (mm)")),
                    "fos":_float(get(data,"min. FOS")),
                    "silt_start_m":_float(get(data,"Silt start depth after (m)")),
                    "silt_thickness_m":_float(get(data,"silt depth (m)")),
                    "sand_before_silt_m":_float(get(data,"Sand layer thickness before silt (m)")),
                }
                records.append(SummaryPoint(_norm_ref(ref),foundation,
                    _float(get(data,"Easting")),_float(get(data,"Northing","Norting")),
                    m,name,
                    area=str(get(data,"Area") or "").strip() or None,
                    footing_width_m=_float(get(data,"Footing Width [m]")),
                    footing_lb_ratio=_float(get(data,"Footing L/B")),
                    reported_fos_check=str(get(data,"FOS check") or "").strip() or None,
                    reported_settlement_check=str(get(data,"Settlement check") or "").strip() or None,
                    ground_elevation_m=_float(get(data,"Current Level"))))
    if not records:
        raise ValueError("No supported CPT Analysis, Full Analysis or Raft/Isolated Summary table found")
    # Prefer foundation-specific sheet over generic CPT Analysis when both present,
    # and avoid duplicate generic rows when the detailed sheet repeats the same CPT.
    seen=set();out=[]
    for p in sorted(records,key=lambda p: {"RAFT":0,"ISOLATED":0,"CPT":1}[p.foundation]):
        key=(p.reference,p.foundation)
        if key in seen:continue
        seen.add(key);out.append(p)
    return out


def _distance(a,b):
    if None in (a.east,a.north,b.east,b.north):return None
    return math.hypot(a.east-b.east,a.north-b.north)


def compare_summaries(pre,post,*,coordinate_tolerance:float=2.0):
    """Return matched points, unmatched points and explicit ambiguous candidates."""
    if coordinate_tolerance<=0:raise ValueError("Coordinate tolerance must be positive")
    pre=list(pre);post=list(post)
    matched=[];unmatched_pre=[];unmatched_post=set(range(len(post)));ambiguous=[]
    used=set()
    for a in pre:
        viable=[]
        for j,b in enumerate(post):
            if j in used or a.foundation!=b.foundation:continue
            same=_norm_ref(a.reference)==_norm_ref(b.reference)
            alias=_alias(a.reference)==_alias(b.reference)
            dist=_distance(a,b)
            if same and (dist is None or dist<=coordinate_tolerance):
                viable.append((0,j,dist))
            elif alias and dist is not None and dist<=coordinate_tolerance:
                viable.append((1,j,dist))
        viable.sort(key=lambda x:(x[0], x[2] or 0))
        if not viable:
            unmatched_pre.append(a);continue
        if len(viable)>1 and viable[0][0]==viable[1][0]:
            ambiguous.append((a,[post[x[1]] for x in viable]));continue
        _,j,dist=viable[0]
        b=post[j];used.add(j);unmatched_post.discard(j)
        diffs={}
        for metric in a.metrics.keys()|b.metrics.keys():
            before=a.metrics.get(metric);after=b.metrics.get(metric)
            if before is None or after is None:
                diffs[metric]={"pre":before,"post":after,"delta":None,"percent":None}
            else:
                delta=after-before
                diffs[metric]={"pre":before,"post":after,"delta":delta,
                               "percent":delta/before*100 if before!=0 else None}
        matched.append({"pre":a,"post":b,"distance":dist,"metrics":diffs})
    return {"matched":matched,"unmatched_pre":unmatched_pre,
            "unmatched_post":[post[i] for i in sorted(unmatched_post)],
            "ambiguous":ambiguous}


def export_comparison(results,output_path: str|Path) -> Path:
    """Auditable engineering Excel; differences do NOT represent design pass/fail."""
    import xlsxwriter
    dest=Path(output_path);dest.parent.mkdir(parents=True,exist_ok=True)
    book=xlsxwriter.Workbook(str(dest))
    h=book.add_format({"bold":True,"bg_color":"#142a40","font_color":"white","text_wrap":True})
    n=book.add_format({"num_format":"0.000","border":1,"border_color":"#e2e8f0"})
    txt=book.add_format({"border":1,"border_color":"#e2e8f0"})
    ws=book.add_worksheet("Matched Changes")
    cols=["Foundation","CPT PRE","CPT POST","Coordinate offset","Metric","PRE","POST","Delta","Percent Change","Interpretation"]
    for j,c in enumerate(cols):ws.write(0,j,c,h)
    i=1
    for m in results["matched"]:
        a,b=m["pre"],m["post"]
        for key,v in sorted(m["metrics"].items()):
            ws.write_row(i,0,[a.foundation,a.reference,b.reference],txt)
            for j in (3,5,6,7,8):
                value=m["distance"] if j==3 else v[["pre","post","delta","percent"][[5,6,7,8].index(j)]]
                if value is not None:ws.write_number(i,j,value,n)
            ws.write(i,4,key,txt)
            desc="NOT COMPARABLE" if v["delta"] is None else "INCREASE" if v["delta"]>0 else "DECREASE" if v["delta"]<0 else "UNCHANGED"
            ws.write(i,9,desc,txt)
            i+=1
    ws.freeze_panes(1,4);ws.autofilter(0,0,max(i-1,1),9)
    ws.set_column(0,2,23);ws.set_column(3,8,17);ws.set_column(9,9,22)
    audit=book.add_worksheet("Matching QA")
    audit.write_row(0,0,["Status","CPT reference","Foundation","Source sheet","Notes"],h)
    r=1
    for kind,items in (("UNMATCHED PRE",results["unmatched_pre"]),("UNMATCHED POST",results["unmatched_post"])):
        for v in items:
            audit.write_row(r,0,[kind,v.reference,v.foundation,v.source_sheet,"No approved matching point"],txt);r+=1
    for v,options in results["ambiguous"]:
        audit.write_row(r,0,["AMBIGUOUS",v.reference,v.foundation,v.source_sheet,
                             "Candidates: "+", ".join(x.reference for x in options)],txt);r+=1
    audit.set_column(0,0,20);audit.set_column(1,3,25);audit.set_column(4,4,75)
    summary=book.add_worksheet("Summary")
    summary.write_row(0,0,["Measure","Value"],h)
    for r,(k,val) in enumerate([("Matched pairs",len(results["matched"])),
        ("Unmatched PRE",len(results["unmatched_pre"])),("Unmatched POST",len(results["unmatched_post"])),
        ("Ambiguous pairs",len(results["ambiguous"]))],1):
        summary.write(r,0,k,txt);summary.write_number(r,1,val,n)
    summary.write(7,0,"Positive delta means POST minus PRE is positive; not automatically engineering improvement.")
    summary.write(8,0,"Differences in smoothing, equipment, depth coverage and test location require engineering review.")
    summary.set_column(0,0,100);summary.set_column(1,1,22)
    book.close()
    return dest


def read_site_boundary_xlsx(path: str|Path):
    """Load ordered main-site limit Easting/Northing points (not geographical CRS)."""
    with zipfile.ZipFile(path) as z:
        strings=[]
        if "xl/sharedStrings.xml" in z.namelist():
            s=ET.fromstring(z.read("xl/sharedStrings.xml"))
            strings=["".join(t.text or "" for t in el.findall(".//m:t",NS)) for el in s.findall("m:si",NS)]
        wb=ET.fromstring(z.read("xl/workbook.xml"))
        rel=ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        paths={el.get("Id"):el.get("Target") for el in rel.findall("p:Relationship",NS)}
        for sh in wb.findall(".//m:sheets/m:sheet",NS):
            if sh.get("name")!="Site Limit":continue
            key=sh.get("{"+NS["r"]+"}id")
            target=(paths.get(key) or "").lstrip("/")
            if not target.startswith("xl/"):target="xl/"+target
            if target not in z.namelist():break
            rows=_sheet_rows(z,target,strings)
            xy=[]
            for row in rows[2:]:
                # Existing site workbook main setting-out polygon in C/D.
                # Stop at first non-coordinate line after the started polygon.
                east=_float(row[2] if len(row)>2 else None)
                north=_float(row[3] if len(row)>3 else None)
                if east is None or north is None:
                    if xy:break
                    continue
                xy.append((east,north))
            if len(xy)>=3:return xy
            break
    raise ValueError("No suitable ordered main boundary found in Site Limit worksheet")

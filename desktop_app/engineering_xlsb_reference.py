"""Read-only original Excel XLSB reference values using native BIFF12 record decoding.

No external spreadsheet library. Never runs VBA, external links, or formulas.
Returns cached data with explicit provenance, not independent engineering design.
"""
from __future__ import annotations
from pathlib import Path
from zipfile import ZipFile
from struct import unpack_from,pack,unpack
import math,hashlib,xml.etree.ElementTree as ET


def _records(binary):
    buf=memoryview(binary);p=0;end=len(buf)
    while p<end:
        rid=0
        for i in range(4):
            v=int(buf[p]);p+=1;rid|=v<<(8*i)
            if v<128:break
        size=0
        for i in range(4):
            v=int(buf[p]);p+=1;size|=(v&127)<<(7*i)
            if v<128:break
        if p+size>end:raise ValueError("Corrupt BIFF12 record")
        yield rid,buf[p:p+size]
        p+=size


def _string(data,pos):
    count=unpack_from("<I",data,pos)[0];pos+=4;last=pos+count*2
    if last>len(data):raise ValueError("Truncated XLSB string")
    return bytes(data[pos:last]).decode("utf-16le","replace"),last


def _rknumber(data):
    n=unpack_from("<i",data,8)[0]
    result=float(n>>2) if n&2 else unpack("<d",b"\0\0\0\0"+pack("<I",n&0xfffffffc))[0]
    return result/100 if n&1 else result


class ReferenceWorkbookCache:
    def __init__(self,path):
        self.path=Path(path)
        if self.path.suffix.lower()!=".xlsb":raise ValueError("Select original .xlsb reference model")
        self.archive=ZipFile(self.path)
        parts=set(self.archive.namelist())
        if not {"xl/workbook.bin","xl/sharedStrings.bin","xl/_rels/workbook.bin.rels"}.issubset(parts):
            raise ValueError("Not a supported XLSB model")
        self.names={}
        for rid,data in _records(self.archive.read("xl/workbook.bin")):
            if rid==0x19c:
                rel,offset=_string(data,8);name,_=_string(data,offset)
                self.names[name]=rel
        ns="{http://schemas.openxmlformats.org/package/2006/relationships}"
        doc=ET.fromstring(self.archive.read("xl/_rels/workbook.bin.rels"))
        relmap={elem.get("Id"):elem.get("Target") for elem in doc.findall(ns+"Relationship")}
        self.sheetfiles={}
        for name,rel in self.names.items():
            target=relmap.get(rel,"").lstrip("/")
            p=target if target.startswith("xl/") else "xl/"+target
            if p in parts:self.sheetfiles[name]=p
        self.strings=[_string(data,1)[0] for rid,data in _records(self.archive.read("xl/sharedStrings.bin")) if rid==0x13]

    def close(self):self.archive.close()
    def __enter__(self):return self
    def __exit__(self,*exc):self.close()

    def rows(self,name,cols=None,stop=None):
        if name not in self.sheetfiles:raise ValueError("Missing reference sheet: "+name)
        wanted=set(cols) if cols is not None else None
        row=None;values={}
        for rid,data in _records(self.archive.read(self.sheetfiles[name])):
            if rid==0:
                newrow=unpack_from("<I",data)[0]
                if row is not None and values:yield row+1,values
                if stop is not None and newrow>=stop:return
                row=newrow;values={}
            elif rid in (2,4,5,7,8,9,10) and row is not None:
                col=unpack_from("<I",data)[0]
                if wanted is not None and col not in wanted:continue
                if rid==2:value=_rknumber(data)
                elif rid in (5,9):value=unpack_from("<d",data,8)[0]
                elif rid==7:
                    index=unpack_from("<I",data,8)[0]
                    value=self.strings[index] if index<len(self.strings) else None
                elif rid==8:value=_string(data,8)[0]
                else:value=bool(data[8])
                if value is not None:values[col]=value
        if row is not None and values:yield row+1,values

    def input_parameters(self):
        return {str(values[0]).strip():{col:val for col,val in values.items() if col!=0}
                for _,values in self.rows("Input") if isinstance(values.get(0),str)}

    def foundation_summary(self):
        heading={};output=[]
        for lineno,values in self.rows("Summary",stop=10000):
            if lineno==2:
                heading={c:str(s).replace("\n"," ").strip() for c,s in values.items()}
            elif lineno>2:
                ref=values.get(2)
                if not isinstance(ref,str) or not ref.startswith("CPT-"):continue
                out={title:values.get(c) for c,title in heading.items()}
                out["reference_xlsb_row"]=lineno
                out["source_workbook"]=self.path.name
                out["method"]="ORIGINAL XLSB CACHED RESULT (not independently recalculated)"
                output.append(out)
        return output

    def mapped_profiles(self):
        """Each triple is (elevation BGL-derived, qc, INTEGER SBT ZONE).
        The column named 'Ic' in Combined CPTs is categorical and MUST NOT be
        interpreted as numerical Ic. Profiles are for reference plots only.
        """
        profiles={};reference_columns={}
        for lineno,values in self.rows("Combined CPTs"):
            if lineno==1:
                for col,ref in values.items():
                    if isinstance(ref,str) and ref.startswith("CPT-"):
                        profiles[ref]=[];reference_columns[col]=ref
            elif lineno>2:
                for col,ref in reference_columns.items():
                    z,qc,zone=values.get(col),values.get(col+1),values.get(col+2)
                    if isinstance(z,(float,int)) and isinstance(qc,(float,int)):
                        profiles[ref].append((float(z),float(qc),
                            int(zone) if isinstance(zone,(int,float)) else None))
        return profiles

    def summary(self):
        params=self.input_parameters()
        results=self.foundation_summary()
        return {
            "source":self.path.name,
            "sha256":hashlib.sha256(self.path.read_bytes()).hexdigest(),
            "sheets":list(self.sheetfiles),
            "cpt_summary_count":len(results),
            "cached_selected_cpt":params.get("CPT reference",{}).get(1),
            "cone_ratio":params.get("net area ratio in the cone, a (a - factor)",{}).get(1),
            "water_depth_m":params.get("Water Level (m)",{}).get(1),
            "rolling_mean_above":params.get("Above",{}).get(1),
            "rolling_mean_below":params.get("Below",{}).get(1),
            "warning":"Values are saved XLSB calculation caches; formulas and VBA were NOT independently executed."
        }


def reference_foundations(path):
    from engineering_comparison import SummaryPoint
    with ReferenceWorkbookCache(path) as cache:
        return [SummaryPoint(
            reference=str(r["CPT REFERENCE"]),foundation=str(r.get("Footing Type") or "RAFT").upper(),
            east=r.get("Easting"),north=r.get("Norting"),
            metrics={
                "settlement_mm":r.get("Settlement (mm)"),
                "fos":r.get("min. FOS"),
                "bearing_capacity_robertson_kpa":r.get("Robertson Ultimate BC [kPa]"),
                "bearing_capacity_aramco_kpa":r.get("ARAMCO Ultimate BC [kPa]"),
                "liquefaction_settlement_mm":r.get("settlement [mm]"),
            },source_sheet="Original XLSB Summary (cached)",
            footing_width_m=r.get("Footing Width [m]"),
            footing_lb_ratio=r.get("Footing L/B"),
            reported_fos_check=r.get("FOS check"),
            reported_settlement_check=r.get("Settlement Check"),
            ground_elevation_m=r.get("Current  Level"),
        ) for r in cache.foundation_summary()]

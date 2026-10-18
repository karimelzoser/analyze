"""Read-only forensic audit of the original binary Excel CPT workbook.

XLSB stores calculation cells as binary .bin structures. This auditor extracts
worksheet/chart inventories and XML chart formula references plus cached points.
It does NOT claim to decode underlying worksheet formulas or run VBA.
"""
from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import re
import xml.etree.ElementTree as ET


CHART_NS={"c":"http://schemas.openxmlformats.org/drawingml/2006/chart"}
TARGETS=("Analysis-Case 1","Analysis-Case 2","Analysis-Case 3",
         "CPT-Graphs","Analysis-Graph","Liquefaction","Liq-Graphs")


def _sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()


def audit_xlsb(path: str|Path, *,cached_values_per_series=6) -> dict:
    path=Path(path)
    if path.suffix.lower()!=".xlsb":
        raise ValueError("Reference workbook must be an XLSB")
    with ZipFile(path,"r") as archive:
        names=archive.namelist()
        charts=sorted((n for n in names if re.fullmatch(r"xl/charts/chart\d+\.xml",n)),
                      key=lambda n:int(re.search(r"chart(\d+)",n).group(1)))
        sheets=sorted(n for n in names if re.fullmatch(r"xl/worksheets/sheet\d+\.bin",n))
        macros=[n for n in names if "vbaProject" in n or "vba" in n.lower() and n.endswith(".bin")]
        inventory=[]
        for name in charts:
            root=ET.fromstring(archive.read(name))
            formulas=[t.text or "" for t in root.findall(".//c:f",CHART_NS)]
            count=[int(t.get("val") or "0") for t in root.findall(".//c:ptCount",CHART_NS)]
            cached=[]
            # Point values are cached snapshots; they are not necessarily
            # current workbook calculations or verified engineering evidence.
            for c in root.findall(".//c:numCache",CHART_NS):
                points=c.findall(".//c:pt",CHART_NS)
                valid=[]
                for item in points:
                    v=item.find("c:v",CHART_NS)
                    if v is not None and v.text is not None:
                        valid.append({"i":int(item.get("idx") or "0"),"value":v.text})
                    if len(valid)>=cached_values_per_series:break
                cached.append(valid)
            inventory.append({"file":name,"source_ranges":formulas,
                              "point_counts":count[:20],"cached_preview":cached[:10]})
    referenced=sorted({s for a in inventory for s in a["source_ranges"]})
    target_names=[s for s in TARGETS if any(s.lower() in f.lower() for f in referenced)]
    return {
        "file":path.name,"sha256":_sha256(path),
        "file_bytes":path.stat().st_size,"binary_sheets":len(sheets),
        "embedded_chart_count":len(charts),"has_vba":bool(macros),
        "macro_paths":macros,"identified_model_sheets":target_names,
        "chart_series_references":inventory,
        "engineering_assessment":"CHART/STRUCTURE AUDIT ONLY. Binary cell formulas, VBA behavior, reference assumptions and updated calculation parity NOT VERIFIED.",
        "approval_gate":"Engineer must validate source equations and input assumptions before native results are certified.",
    }


def audit_to_json(source:str|Path,out:str|Path) -> Path:
    report=audit_xlsb(source)
    target=Path(out);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    return target


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description="Read-only XLSB chart and source-model audit")
    parser.add_argument("source");parser.add_argument("--out",default="CPT_Reference_XLSB_Audit.json")
    args=parser.parse_args()
    print(audit_to_json(args.source,args.out))

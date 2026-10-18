"""Validation of imported foundation summary outputs against explicit user criteria.

This is a QA comparison of externally calculated values; it is NOT a settlement,
liquefaction or foundation design formula implementation.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import math
import xlsxwriter
from engineering_comparison import SummaryPoint


@dataclass(frozen=True)
class FoundationValidation:
    reference: str
    foundation: str
    settlement_mm: float|None
    fos: float|None
    settlement_result: str
    fos_result: str
    imported_settlement_check: str|None
    imported_fos_check: str|None
    discrepancy: tuple[str,...]


def check_foundation_results(points:Iterable[SummaryPoint],*,
        allowable_settlement_mm:float|None,
        minimum_fos:float|None)->list[FoundationValidation]:
    """Compare results only where a licensed engineer provides acceptance criteria."""
    if allowable_settlement_mm is not None and allowable_settlement_mm<=0:
        raise ValueError("Allowable settlement must be >0")
    if minimum_fos is not None and minimum_fos<=0:
        raise ValueError("Minimum FOS must be >0")
    rows=[]
    for p in points:
        if p.foundation not in ("RAFT","ISOLATED"):continue
        settlement=p.metrics.get("settlement_mm")
        fos=p.metrics.get("fos")
        measured_settlement = settlement is not None and math.isfinite(float(settlement))
        measured_fos = fos is not None and math.isfinite(float(fos))
        s=("NOT ASSESSED" if allowable_settlement_mm is None or not measured_settlement
           else "PASS" if settlement<=allowable_settlement_mm else "FAIL")
        f=("NOT ASSESSED" if minimum_fos is None or not measured_fos
           else "PASS" if fos>=minimum_fos else "FAIL")
        discrepancy=[]
        if (p.reported_settlement_check and s in ("PASS","FAIL")
            and p.reported_settlement_check.upper()!=s):
            discrepancy.append("Imported settlement check disagrees with supplied threshold")
        if (p.reported_fos_check and f in ("PASS","FAIL")
            and p.reported_fos_check.upper()!=f):
            discrepancy.append("Imported FOS check disagrees with supplied threshold")
        rows.append(FoundationValidation(p.reference,p.foundation,
                         settlement if measured_settlement else None,
                         fos if measured_fos else None,s,f,
                         p.reported_settlement_check,p.reported_fos_check,tuple(discrepancy)))
    return rows


def export_foundation_validation(rows:Iterable[FoundationValidation], path:str|Path):
    dest=Path(path);dest.parent.mkdir(parents=True,exist_ok=True)
    wb=xlsxwriter.Workbook(str(dest))
    ws=wb.add_worksheet("Foundation Criteria QA")
    h=wb.add_format({"bold":True,"bg_color":"#142b42","font_color":"#ffffff","text_wrap":True})
    row=wb.add_format({"border":1,"border_color":"#e2e8f0"})
    heads=["CPT Reference","Footing","Imported settlement (mm)","Imported minimum FOS",
           "Supplied settlement criterion","Supplied FOS criterion",
           "Source settlement check","Source FOS check","Discrepancy",
           "Design-model validation"]
    for j,t in enumerate(heads):ws.write(0,j,t,h)
    for i,p in enumerate(rows,1):
        vals=[p.reference,p.foundation,p.settlement_mm,p.fos,
              p.settlement_result,p.fos_result,p.imported_settlement_check,p.imported_fos_check,
              "; ".join(p.discrepancy),"NOT VERIFIED: independently reproduce workbook equations before signoff"]
        for j,value in enumerate(vals):
            if value is None:continue
            if isinstance(value,(float,int)):ws.write_number(i,j,float(value),row)
            else:ws.write(i,j,str(value),row)
    ws.freeze_panes(1,2);ws.set_column(0,0,27);ws.set_column(1,7,24);ws.set_column(8,9,65)
    wb.close()
    return dest

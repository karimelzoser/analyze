"""Streaming XLSX pages for projects exceeding Excel's hard row limit.

One workbook, many numbered detail sheets. Repeated headings and consistent
column semantics; not a single CPT sample is silently dropped.
"""
from __future__ import annotations
from math import isfinite
import numpy as np

MAX_DATA_ROWS = 1_048_575  # Excel row 0 is occupied by the header.


def _open_sheet(workbook,style,base,page,header,widths=None):
    name=base if page==1 else f"{base} {page:02d}"
    ws=workbook.add_worksheet(name)
    ws.set_tab_color("#5d87ac")
    ws.set_row(0,36)
    for j,text in enumerate(header):ws.write(0,j,text,style["header"])
    ws.freeze_panes(1,1)
    ws.set_column(0,0,28)
    ws.set_column(1,len(header)-1,19)
    for col,width in (widths or {}).items():ws.set_column(col,col,width)
    return ws,name


def write_paged_rows(workbook,style,base,header,rows,*,page_limit=MAX_DATA_ROWS,
                     widths=None):
    if not 1<=page_limit<=MAX_DATA_ROWS:raise ValueError("Invalid page limit")
    page=1;index=0;total=0
    ws,name=_open_sheet(workbook,style,base,page,header,widths)
    names=[name]
    for record in rows:
        if index==page_limit:
            if index:ws.autofilter(0,0,index,len(header)-1)
            page+=1;index=0
            ws,name=_open_sheet(workbook,style,base,page,header,widths)
            names.append(name)
        index+=1;total+=1
        for j,val in enumerate(record):
            if val is None:ws.write(index,j,"NOT RECORDED / UNAVAILABLE",style["small"])
            elif isinstance(val,(int,float)) and isfinite(float(val)):
                ws.write_number(index,j,float(val),style["number"])
            else:ws.write(index,j,str(val)[:32000],style["plain"])
    if index:ws.autofilter(0,0,index,len(header)-1)
    return total,names


def write_cpt_measurements(workbook,style,analyses,*,page_limit=MAX_DATA_ROWS):
    """Stream real qc/fs/u2/qt/Fr/Qtn/Ic data with no fixed-sheet overflow."""
    columns=["CPT REFERENCE","Depth BGL (m)","qc (MPa)","fs (MPa)",
      "u2 (MPa)","qt (MPa)","Fr (%)","Qtn","Ic","Measurement validity","Source type"]
    if not 1<=page_limit<=MAX_DATA_ROWS:
        raise ValueError("Invalid Excel data-page limit")
    page=1;index=0;total=0
    ws,name=_open_sheet(workbook,style,"CPT Measurements",page,columns,
                        {0:29,1:17,8:17,9:25,10:24})
    ranges=[];pages=[name]
    for a in analyses:
        if not hasattr(a,"depth"):continue
        fields=("depth","qc","fs","u2","qt","fr","qtn","ic")
        arrays=[np.asarray(getattr(a,key),dtype=float) for key in fields]
        valid=np.asarray(a.valid_sensor,bool)
        if any(len(field)!=len(arrays[0]) for field in arrays) or len(valid)!=len(arrays[0]):
            raise ValueError("CPT profile arrays inconsistent for "+a.reference)
        current_start=None;last_name=name
        for k in range(len(arrays[0])):
            if index==page_limit:
                if current_start is not None and index>=current_start:
                    ranges.append((a.reference,name,current_start,index))
                if index:ws.autofilter(0,0,index,len(columns)-1)
                page+=1;index=0
                ws,name=_open_sheet(workbook,style,"CPT Measurements",page,columns,
                                    {0:29,1:17,8:17,9:25,10:24})
                pages.append(name);current_start=None
            index+=1;total+=1
            if current_start is None:current_start=index
            ws.write(index,0,a.reference,style["plain"])
            for j,array in enumerate(arrays,1):
                if (j==4 and (getattr(a,"metadata",{}) or {}).get("pore_pressure_measured") is False):
                    ws.write(index,j,"NOT MEASURED - 0 ASSUMED FOR qt",style["small"])
                    continue
                value=float(array[k])
                if isfinite(value):ws.write_number(index,j,value,style["number"])
                else:ws.write(index,j,"NOT MEASURED",style["small"])
            ws.write(index,9,"VALID" if valid[k] and isfinite(arrays[-1][k]) else "UNKNOWN",style["plain"])
            ws.write(index,10,str(a.source_path.suffix).upper(),style["plain"])
        if current_start is not None and index>=current_start:
            ranges.append((a.reference,name,current_start,index))
    if index:ws.autofilter(0,0,index,len(columns)-1)
    return total,ranges,pages

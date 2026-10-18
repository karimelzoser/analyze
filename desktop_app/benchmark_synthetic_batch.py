"""Large synthetic project benchmark for regression/performance smoke.

This is NOT a validation of 400 real project sources or workbook formula
equivalence. It measures the offline numerical and Excel/chart batch workflow
on deterministic test data without publishing confidential CPT observations.
"""
from __future__ import annotations

import json
import os
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cpt_core import analyze_gef
from reporting_export_v2 import export_excel
from engineering_maps import render_site_map


def make_synthetic_gef(path:Path,index:int,points:int=130)->None:
    x=420500.0+(index%25)*25.0
    y=2928000.0+(index//25)*25.0
    lines=[
        "#GEFID= 1, 1, 0","#PROJECTID= PERFORMANCE","#PROJECTNAME= SYNTHETIC",
        "#COLUMN= 4","#COLUMNINFO= 1, m, penetration length, 1",
        "#COLUMNINFO= 2, MPa, Tip resistance, 2",
        "#COLUMNINFO= 3, MPa, Local sleeve friction, 3",
        "#COLUMNINFO= 4, m, corrected depth, 11",
        f"#XYID= 1, {x:.3f}, {y:.3f}, 0.001, 0.001",
        "#ZID= 31000, 3.5, 0.001",
        "#MEASUREMENTVAR= 3, 0.75, -, area ratio",
        f"#TESTID= CPT-A1-SYNTH-{index:04d}-100","#EOH="
    ]
    for j in range(points):
        z=j*.05
        if z>5.5 and index%3!=0:
            qc,fs=.7,.12
        else:qc,fs=12.0,.09
        # Terminal dropout in some samples; interpreted length is never
        # permitted to extend through these missing sleeve readings.
        if j>points-9 and index%7==0:fs=0.
        lines.append(f"{z:.3f} {qc:.5f} {fs:.5f} {z:.3f}")
    path.write_text("\n".join(lines),encoding="ascii")


def run_benchmark(count:int=400)->dict:
    if count<1:raise ValueError("count must be positive")
    with tempfile.TemporaryDirectory(prefix="cpt_large_batch_") as scratch:
        temp=Path(scratch)
        files=[]
        for i in range(count):
            f=temp/f"Synthetic_{i:04d}.GEF"
            make_synthetic_gef(f,i)
            files.append(f)
        t0=time.perf_counter()
        workers=max(1,min(8,os.cpu_count() or 4,count))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            result=list(executor.map(analyze_gef,files))
        t1=time.perf_counter()
        assert len(result)==count and len({x.reference for x in result})==count
        workbook=export_excel(result,temp/"CPT_Synthetic_Test.xlsx")
        t2=time.perf_counter()
        for metric in ("maximum_silt","cumulative_silt","silt_start","test_depth"):
            render_site_map(result,temp/(metric+".png"),metric=metric)
        t3=time.perf_counter()
        assert workbook.stat().st_size>10000
        return {"benchmark":"SYNTHETIC - not source project qualification",
                "soundings":len(files),"workers":workers,
                "numerical_seconds":round(t1-t0,2),
                "workbook_seconds":round(t2-t1,2),
                "four_project_maps_seconds":round(t3-t2,2),
                "total_seconds":round(t3-t0,2),
                "verified":sum(a.status=="VERIFIED" for a in result),
                "review":sum(a.status=="REVIEW" for a in result),
                "no_silt":sum(a.status=="NO SILT" for a in result),
                "output_xlsx_bytes":workbook.stat().st_size}


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--count",type=int,default=400)
    args=parser.parse_args()
    result=run_benchmark(args.count)
    print(json.dumps(result,indent=2))

"""Execute an auditable full-project acceptance pass on existing repository PDFs.

This is a genuine source-format integration and exception-accounting test, NOT
engineering approval of Ic/fines, ground-improvement, or foundation design.
One project XLSX plus machine-readable source QA are emitted. Every physical
input file must appear exactly once in the source audit, including failures.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

from app_pdf_enabled import select_project_results
from pdf_analysis_refined import analyze_pdf
from reporting_export_v2 import export_excel


def source_digest(path):
    hasher=hashlib.sha256()
    with Path(path).open("rb") as src:
        for blob in iter(lambda:src.read(1024*1024),b""):
            hasher.update(blob)
    return hasher.hexdigest()


def run_real_pdf_acceptance(root, out, *, expected_physical=None,
                            write_workbook=True, progress_callback=None):
    root=Path(root).resolve()
    out=Path(out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    sources=sorted((p for p in root.rglob("*") if p.is_file() and p.suffix.lower()==".pdf"),
                   key=lambda x:str(x.relative_to(root)).lower())
    if not sources:
        raise ValueError(f"No source PDFs under {root}")
    if expected_physical is not None and len(sources)!=expected_physical:
        raise ValueError(f"Expected {expected_physical} actual CPT PDF files, found {len(sources)}")

    start_time=time.perf_counter()
    results=[];failures={};manifest=[]
    for idx,path in enumerate(sources,1):
        item={"file":str(path.relative_to(root)),"size_bytes":path.stat().st_size,
              "sha256":source_digest(path),"ordinal":idx}
        try:
            reading=analyze_pdf(path)
            results.append(reading)
            item.update({"parsed":"YES","reference":reading.reference,
                         "analysis_status":reading.status,
                         "reason":str(getattr(reading,"verification_note","") or "")})
        except Exception as exc:
            reason=f"{type(exc).__name__}: {exc}"
            item.update({"parsed":"NO","reference":None,
                         "analysis_status":"ERROR","reason":reason})
            failures[str(path.resolve()).lower()]=reason
        manifest.append(item)
        if progress_callback and (idx%25==0 or idx==len(sources)):
            progress_callback(idx,len(sources))
    unique,audit=select_project_results(results,sources,failures)
    if len(audit)!=len(sources):
        raise RuntimeError("Source audit failed physical-file accounting: "
                           f"{len(audit)} audit rows for {len(sources)} PDFs")
    count=collections.Counter(r["source_file"] for r in audit)
    # Filenames may repeat in different subfolders; this is an explicit
    # ambiguity, not permission to discard or attribute one to another.
    repeated_filenames=[name for name,n in count.items() if n>1]
    if repeated_filenames:
        raise RuntimeError("Same PDF filename exists in more than one folder; "
                           "source-audit filenames need disambiguation: "+
                           ", ".join(repeated_filenames[:8]))
    for item in manifest:
        if count[item["file"].split("/")[-1]]!=1:
            raise RuntimeError("Physical PDF omitted from source audit: "+item["file"])
    families=collections.Counter(row["family"] for row in audit)
    if len(unique)!=len(families):
        raise RuntimeError(f"{len(unique)} CPT outcomes for {len(families)} physical source families")
    selected_count=sum(row["selected"]=="YES" for row in audit)
    if selected_count!=len(unique):
        raise RuntimeError(f"{selected_count} selected physical sources but {len(unique)} output CPTs")

    manifest_file=out/"PDF_Source_Manifest.csv"
    with manifest_file.open("w",newline="",encoding="utf-8-sig") as fd:
        cols=["ordinal","file","size_bytes","sha256","parsed","reference",
              "analysis_status","reason"]
        writer=csv.DictWriter(fd,fieldnames=cols)
        writer.writeheader()
        writer.writerows(manifest)

    source_audit_file=out/"PDF_Source_Audit.csv"
    with source_audit_file.open("w",newline="",encoding="utf-8-sig") as fd:
        cols=["family","source_file","source_type","revision","source_quality",
              "status","silt_start","silt_thickness","selected",
              "selection_reason","verification_note"]
        writer=csv.DictWriter(fd,fieldnames=cols)
        writer.writeheader()
        writer.writerows(audit)

    workbook=None
    if write_workbook:
        workbook=export_excel(unique,out/"Real_Project_PDF_Acceptance.xlsx",
                              errors=[(Path(x).name,y) for x,y in failures.items()],
                              source_audit=audit)
        if not workbook.is_file():
            raise RuntimeError("Main consolidated project workbook was not created")

    physical=collections.Counter(row["status"] for row in audit)
    project=collections.Counter(row.status for row in unique)
    warnings=[]
    for row in unique:
        if row.status=="REVIEW":
            warnings.append({"reference":row.reference,"status":"REVIEW",
                  "reason":str(getattr(row,"verification_note","") or ""),
                  "source":row.source_path.name})
    from engineering_review_triage import review_register,triage_counts
    triage=review_register(unique)
    summary={
      "review_category_counts":triage_counts(unique),
      "review_resolution_register":triage,
      "disposition":"SOURCE PIPELINE AUDIT ONLY — not engineer-approved CPT design",
      "source_root":str(root),
      "physical_pdfs":len(sources),
      "parsed_pdf_files":len(results),
      "parse_errors":len(failures),
      "unique_cpt_references":len(unique),
      "revision_or_duplicate_files":len(sources)-len(unique),
      "selected_sources":selected_count,
      "physical_statuses":dict(sorted(physical.items())),
      "unique_cpt_statuses":dict(sorted(project.items())),
      "review_reasons":warnings,
      "elapsed_seconds":round(time.perf_counter()-start_time,2),
      "artifacts":{"manifest":manifest_file.name,"audit":source_audit_file.name,
                   "workbook":workbook.name if workbook is not None else None},
      "interpretation_warning":"Ic >= 2.60 is only a project soil-behavior screening convention; missing/ambiguous readings remain REVIEW.",
    }
    (out/"PDF_Acceptance_Result.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),
                                                   encoding="utf-8")
    return summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",default="pdfs/pdf_Single")
    p.add_argument("--out",default="acceptance-artifacts")
    p.add_argument("--expect",type=int)
    p.add_argument("--without-workbook",action="store_true")
    args=p.parse_args()
    def progress(n,total):
        print(f"Processed {n}/{total} actual PDF source files",flush=True)
    try:
        summary=run_real_pdf_acceptance(args.source,args.out,
                expected_physical=args.expect,write_workbook=not args.without_workbook,
                progress_callback=progress)
    except Exception as exc:
        print(f"ACCEPTANCE PIPELINE FAILED: {type(exc).__name__}: {exc}",file=sys.stderr)
        return 1
    print(json.dumps({k:v for k,v in summary.items() if k!="review_reasons"},indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())

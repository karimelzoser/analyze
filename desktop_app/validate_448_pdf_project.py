"""Full, real 448-PDF corpus engineering acceptance runner.

Exercises the exact Windows desktop analysis worker on every tracked project
report. Emits a comprehensive XLSX, generated PDF appendices, QA JSON and CSV.
No arbitrary reclassification or forced 'VERIFIED' status.
"""
from __future__ import annotations
import csv
import json
import os
import time
from pathlib import Path
from collections import Counter
import zipfile


def validate_project_corpus(project_dir:Path,output_dir:Path,*,expected_sources=448):
    import pymupdf
    from engineering_review_ui import EngineeringReviewApp
    source_files=sorted(project_dir.rglob("*.pdf"),key=lambda p:p.name.lower())
    if len(source_files)!=expected_sources:
        raise RuntimeError(f"Expected {expected_sources} repository PDFs, located {len(source_files)}")
    output_dir.mkdir(parents=True,exist_ok=True)
    app=EngineeringReviewApp()
    app.withdraw()
    started=time.perf_counter()
    try:
        app.files=source_files
        app.output_var.set(str(output_dir))
        result=app._work_batch(output_dir,18.0,2.0,True)
        events=[]
        while not app.messages.empty():
            events.append(app.messages.get_nowait())
        completions=[e for e in events if e[0]=="done"]
        if not completions:raise RuntimeError("Worker did not return a final completed project")
        _,_,pdfdir,xlsx,analyses,errors=completions[-1]
        statuses=Counter(a.status for a in analyses)
        pdf_outputs=sorted(Path(pdfdir).glob("*.pdf"))
        summaries=[]
        malformed=[]
        for a in analyses:
            interval=a.final_interval
            summaries.append({
                "cpt":a.reference,"status":a.status,
                "source":a.source_path.name,
                "corrected_test_depth_m":getattr(a,"test_depth_raw",None),
                "silt_start_m":None if interval is None else interval.start,
                "silt_thickness_m":None if interval is None else interval.thickness,
                "verification":str(getattr(a,"verification_note","") or "")[:2000],
            })
        for report in pdf_outputs:
            try:
                with pymupdf.open(str(report)) as document:
                    if document.page_count<2:
                        malformed.append({"file":report.name,"problem":"No analysis appendix"})
                    elif not document[-1].get_text().strip():
                        malformed.append({"file":report.name,"problem":"Empty final report appendix"})
            except Exception as exc:
                malformed.append({"file":report.name,"problem":str(exc)})
        with zipfile.ZipFile(xlsx) as z:
            workbook=z.read("xl/workbook.xml")
            for sheet in (b"CPT Analysis",b"Summary",b"Charts",b"CPT Curves",
                          b"All Soil Layers",b"CPT Measurements",b"Source Audit",b"Project Maps"):
                if sheet not in workbook:raise RuntimeError(f"Missing full project worksheet {sheet!r}")
            native_charts=len([n for n in z.namelist() if
                               n.startswith("xl/charts/chart") and n.endswith(".xml")])
            if native_charts<8:raise RuntimeError(f"Only {native_charts} Excel charts; expected 8")
        all_details=len(summaries)
        if all_details<350:
            raise RuntimeError(f"Only {all_details} project CPT locations; expected at least 350")
        if len(pdf_outputs)!=all_details:
            raise RuntimeError(f"Generated {len(pdf_outputs)} PDFs for {all_details} selected CPT results")
        if errors or malformed:
            raise RuntimeError(f"{len(errors)} processing errors; {len(malformed)} malformed report PDFs")
        elapsed=time.perf_counter()-started
        report={"source_type":"REAL TRACKED REPOSITORY PDF CORPUS",
            "source_physical_pdfs":len(source_files),
            "final_cpt_locations":all_details,
            "generated_pdfs":len(pdf_outputs),
            "excel_native_charts":native_charts,
            "classification_counts":dict(statuses),
            "review_not_assumed_valid":statuses.get("REVIEW",0),
            "elapsed_s":round(elapsed,2),
            "errors":errors,
            "malformed_reports":malformed,
            "input_folder":str(project_dir),
            "generated_excel":Path(xlsx).name,
            "scope":"PDF-only field corpus. No new raw GEF, actual source workbook VBA, or independent design formula validation.",
            "result":"PASS - CORPUS WORKFLOW (not geotechnical signoff)"}
        (output_dir/"Project_Corpus_Acceptance.json").write_text(json.dumps(report,indent=2),
                  encoding="utf-8")
        with (output_dir/"CPT_Review_Register.csv").open("w",newline="",encoding="utf-8-sig") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(summaries[0]))
            writer.writeheader();writer.writerows(summaries)
        return report
    finally:
        app.destroy()


if __name__=="__main__":
    folder=Path(__file__).resolve().parents[1]/"pdfs"/"pdf_Single"
    out=Path(__file__).resolve().parent/"field_acceptance_output"
    print(json.dumps(validate_project_corpus(folder,out),indent=2))

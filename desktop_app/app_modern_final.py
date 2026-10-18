import app_modern
import engineering_workspace
import reporting_export_v2

# Production wiring:
# - five-column engineering workbook exporter
# - modern maximized desktop shell
# - reliable latest-workbook opening
# - mixed GEF/GFF/PDF input with raw-source preference
# - validated native-vector PDF analysis and appended PDF summary pages
app_modern.export_excel = reporting_export_v2.export_excel


def _packaged_gui_smoke():
    """Create the real Tk UI and visit every integrated workspace.

    Used by CI twice: from Python source and from the PyInstaller EXE.
    """
    import os
    import sys
    import traceback
    from pathlib import Path
    output=os.environ.get("CPT_SMOKE_OUT")
    root=None
    try:
        root=engineering_workspace.EngineeringWorkspaceApp()
        root.update_idletasks()
        root.update()
        texts=[root.notebook.tab(tab,"text").strip() for tab in root.notebook.tabs()]
        needed={"Setup","Results","Charts","Soil Layers","Site Map","Foundations","Pre / Post"}
        missing=needed-set(texts)
        if missing:
            raise RuntimeError("Missing UI workspaces: "+repr(sorted(missing)))
        for index in range(len(root.notebook.tabs())):
            root.notebook.select(index)
            root.update_idletasks()
            root.update()
        if "--integration-smoke" in sys.argv:
            import tempfile
            import zipfile
            from cpt_core import analyze_gef
            from app_modern_v2 import latest_excel_path
            import pymupdf
            with tempfile.TemporaryDirectory(prefix="cpt_gui_e2e_") as scratch:
                rootdir=Path(scratch)
                sample=rootdir/"synthetic.GEF"
                rows=[
                    "#GEFID= 1, 1, 0","#PROJECTID= VALIDATION",
                    "#COLUMN= 4","#COLUMNINFO= 1, m, penetration length, 1",
                    "#COLUMNINFO= 2, MPa, Tip resistance, 2",
                    "#COLUMNINFO= 3, MPa, Local sleeve friction, 3",
                    "#COLUMNINFO= 4, m, corrected depth, 11",
                    "#XYID= 1, 421000, 2928000, 0.001, 0.001",
                    "#ZID= 31000, 3.5, 0.001",
                    "#MEASUREMENTVAR= 3, 0.75, -, area ratio",
                    "#TESTID= CPT-A1-SMOKE-100","#EOH=",
                ]
                for i in range(65):
                    z=i*.1
                    qc,fs=(10.,.10) if z<6. else ((.5,.15) if z<=6.3 else (.5,0.))
                    rows.append(f"{z:.3f} {qc:.5f} {fs:.5f} {z:.3f}")
                sample.write_text("\n".join(rows),encoding="ascii")
                root.files=[sample]
                destination=rootdir/"CPT_Output"
                root._worker(destination,18.,0.,True)
                messages=[]
                while not root.messages.empty():
                    messages.append(root.messages.get_nowait())
                errors=[m for m in messages if m[0] in ("analysis_error","pdf_error")]
                if errors:raise RuntimeError("End-to-end analysis/report errors: "+repr(errors))
                finals=[m for m in messages if m[0]=="done"]
                if not finals:raise RuntimeError("No analysis completion event")
                latest=latest_excel_path(destination)
                if latest is None or not latest.exists():
                    raise RuntimeError("Open Latest Excel could not resolve completed workbook")
                with zipfile.ZipFile(latest) as book:
                    workbook=book.read("xl/workbook.xml")
                    for sheet in (b"CPT Analysis",b"Full Analysis",b"All Soil Layers",
                                  b"Methodology and QA",b"Source Audit",b"Summary"):
                        if sheet not in workbook:raise RuntimeError("Missing workbook sheet "+repr(sheet))
                reports=list((destination/"PDFs").glob("*.pdf"))
                if len(reports)!=1:raise RuntimeError("Expected exactly one generated CPT report")
                with pymupdf.open(str(reports[0])) as report:
                    if report.page_count<2:raise RuntimeError("Generated report missing appendix")
                maps=list((destination/"Charts").glob("*.png"))
                if len(maps)<3:raise RuntimeError("Expected project map image exports")
                result_detail=f" | END-TO-END one GEF -> {len(reports)} PDF, XLSX, {len(maps)} maps"
        else:
            result_detail=""
        result="PASS: GUI opened; "+", ".join(texts)+result_detail
        if output:
            Path(output).write_text(result,encoding="utf-8")
        else:
            print(result)
        return 0
    except Exception:
        failure=traceback.format_exc()
        if output:
            Path(output).write_text("FAIL: "+failure,encoding="utf-8")
        else:
            print(failure,file=sys.stderr)
        return 1
    finally:
        if root is not None:
            try:root.destroy()
            except Exception:pass


if __name__ == "__main__":
    import sys
    if "--smoke-test" in sys.argv or "--integration-smoke" in sys.argv:
        raise SystemExit(_packaged_gui_smoke())
    engineering_workspace.EngineeringWorkspaceApp().mainloop()

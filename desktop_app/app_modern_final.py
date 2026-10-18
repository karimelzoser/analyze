import app_modern
import engineering_review_ui
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
        root=engineering_review_ui.EngineeringReviewApp()
        root.update_idletasks()
        root.update()
        texts=[root.notebook.tab(tab,"text").strip() for tab in root.notebook.tabs()]
        needed={"Setup","Results","Charts","Soil Layers","Site Map","Foundations","Pre / Post","QA & Review"}
        missing=needed-set(texts)
        if missing:
            raise RuntimeError("Missing UI workspaces: "+repr(sorted(missing)))
        snapshot=os.environ.get("CPT_SCREENSHOT_DIR")
        if snapshot:
            from PIL import ImageGrab
            screenshot_dir=Path(snapshot)
            screenshot_dir.mkdir(parents=True,exist_ok=True)
        for index in range(len(root.notebook.tabs())):
            root.notebook.select(index)
            root.update_idletasks()
            root.update()
            if snapshot:
                import time
                time.sleep(.08)
                root.update_idletasks()
                x,y=root.winfo_rootx(),root.winfo_rooty()
                w,h=root.winfo_width(),root.winfo_height()
                if w<800 or h<500:
                    raise RuntimeError("GUI rendering is below minimum usable dimensions")
                name="".join(ch if ch.isalnum() else "_" for ch in root.notebook.tab(index,"text").strip())
                ImageGrab.grab(bbox=(x,y,x+w,y+h),all_screens=True).save(
                    screenshot_dir/f"{index+1:02d}_{name}.png")
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
                delivered=list(destination.glob("*.xlsx"))
                if len(delivered)!=1:
                    raise RuntimeError("Expected ONE comprehensive XLSX per run, found "+repr([p.name for p in delivered]))
                with zipfile.ZipFile(latest) as book:
                    workbook=book.read("xl/workbook.xml")
                    for sheet in (b"CPT Analysis",b"Full Analysis",b"All Soil Layers",
                                  b"Methodology and QA",b"Source Audit",b"Summary"):
                        if sheet not in workbook:raise RuntimeError("Missing workbook sheet "+repr(sheet))
                reports=list((destination/"PDFs").glob("*.pdf"))
                if len(reports)!=1:raise RuntimeError("Expected exactly one generated CPT report")
                with pymupdf.open(str(reports[0])) as report:
                    if report.page_count<2:raise RuntimeError("Generated report missing appendix")
                with zipfile.ZipFile(latest) as book:
                    sheetlist=book.read("xl/workbook.xml")
                    for name in (b"Project Maps",b"Project Dashboard",b"CPT Coordinates",
                                 b"CPT Measurements",b"Survey Coordinate QA"):
                        if name not in sheetlist:
                            raise RuntimeError("Unified Excel lacks "+str(name))
                    if len([n for n in book.namelist() if n.startswith("xl/media/image")])<2:
                        raise RuntimeError("Unified Excel lacks embedded 2D/3D map images")
                result_detail=f" | END-TO-END one GEF -> {len(reports)} PDF and 1 all-in-one XLSX with 2D/3D maps"
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


def launch_desktop(*, check_normal_startup=False):
    """Single entry point used by BOTH double-click startup and CI.

    The normal-startup smoke tests the real constructor/mainloop call, not a
    separate helper constructor that could mask a broken Windows launcher.
    """
    import os
    from pathlib import Path
    app = engineering_review_ui.EngineeringReviewApp()
    if check_normal_startup:
        # Allow the actual Tk event loop to render, then exit deterministically
        # so this verification works for the console-less Windows executable.
        app.after(400, app.destroy)
    app.mainloop()
    if check_normal_startup:
        output = os.environ.get("CPT_STARTUP_SMOKE_OUT")
        if output:
            Path(output).write_text(
                "PASS: normal desktop startup created EngineeringReviewApp "
                "and entered/exited its real Tk mainloop", encoding="utf-8")
    return 0


if __name__ == "__main__":
    import sys
    if "--smoke-test" in sys.argv or "--integration-smoke" in sys.argv:
        raise SystemExit(_packaged_gui_smoke())
    raise SystemExit(launch_desktop(
        check_normal_startup="--normal-startup-smoke" in sys.argv))

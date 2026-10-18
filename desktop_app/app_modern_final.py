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
            if not root.progress.winfo_ismapped():
                raise RuntimeError("Global analysis progress bar hidden by tab navigation: "+texts[index])
            if texts[index]=="Site Map" and not root.map_open_3d_btn.winfo_ismapped():
                raise RuntimeError("Primary interactive 3D model action is hidden on Site Map")
            if texts[index]=="Setup" and root.settings_form.winfo_ismapped():
                raise RuntimeError("Engineering advanced options should be collapsed in the simple intake workflow")
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
        # Also validate the *offline* 3D viewer in both the source GUI and
        # the frozen Windows EXE; PyInstaller must include local Plotly.js.
        import tempfile
        from engineering_geo_explorer import export_interactive_3d
        with tempfile.TemporaryDirectory(prefix="cpt_3d_bundle_smoke_") as scene_dir:
            points=[
                {"reference":f"CPT-3D-{i}","easting":float(e),"northing":float(n),
                 "ground_elevation":3.5,"test_depth_m":5.4,
                 "max_contiguous_silt_screen_m":.22,
                 "cumulative_silt_screen_m":.22,
                 "status":"REFERENCE-CACHED",
                 "all_intervals":[{"start_raw":4.70,"end_raw":4.92}]}
                for i,(e,n) in enumerate([(0,0),(20,0),(0,20),(20,20)])
            ]
            html=export_interactive_3d(points,Path(scene_dir)/"offline_3d.html",
                                       max_spacing_m=40)
            if html["file"].stat().st_size<1_000_000 or html["wedges"]<1:
                raise RuntimeError("Offline 3D bundled Plotly mesh has no local assets or supported layer wedges")
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
                    for sheet in (b"Summary",b"CPT Analysis",b"Full Analysis",
                                  b"All Soil Layers",b"Source Audit",b"Project Maps"):
                        if sheet not in workbook:raise RuntimeError("Missing workbook sheet "+repr(sheet))
                reports=list((destination/"PDFs").glob("*.pdf"))
                if len(reports)!=1:raise RuntimeError("Expected exactly one generated CPT report")
                with pymupdf.open(str(reports[0])) as report:
                    if report.page_count<3:raise RuntimeError("Generated report needs source chart, QA summary, full-layer appendix")
                    if "CPT FULL SOIL-BEHAVIOR DEPTH PROFILE" not in report[-1].get_text():
                        raise RuntimeError("PDF full-layer appendix missing")
                    if "NOT PROVIDED" not in report[0].get_text():
                        raise RuntimeError("Missing source metadata must be explicitly labeled in PDF")
                with zipfile.ZipFile(latest) as book:
                    sheetlist=book.read("xl/workbook.xml")
                    for name in (b"Project Maps",b"Summary",b"Full Analysis",
                                 b"CPT Measurements",b"Source Audit"):
                        if name not in sheetlist:
                            raise RuntimeError("Unified Excel lacks "+str(name))
                    if len([n for n in book.namelist() if n.startswith("xl/media/image")])<2:
                        raise RuntimeError("Unified Excel lacks embedded 2D/3D map images")
                from threading import Event
                root.cancel_event=Event()
                root.cancel_event.set()
                cancel_dir=rootdir/"Cancel_Output"
                root._worker(cancel_dir,18.,2.,True)
                cancellation=[]
                while not root.messages.empty():
                    cancellation.append(root.messages.get_nowait())
                if not any(m[0]=="cancelled" for m in cancellation):
                    raise RuntimeError("Cancellation did not emit a safe completion status")
                if list(cancel_dir.glob("*.xlsx")):
                    raise RuntimeError("Cancellation published an incomplete Excel workbook")
                result_detail=f" | END-TO-END one GEF -> {len(reports)} PDF and 1 all-in-one XLSX with 2D/3D maps; safe Cancel verified"
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

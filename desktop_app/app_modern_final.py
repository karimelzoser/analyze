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
        result="PASS: GUI opened; "+", ".join(texts)
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
    if "--smoke-test" in sys.argv:
        raise SystemExit(_packaged_gui_smoke())
    engineering_workspace.EngineeringWorkspaceApp().mainloop()

"""Ensure a catastrophic Excel failure cannot strand the Windows interface."""
from pathlib import Path
from queue import Queue
from types import SimpleNamespace
from app_pdf_enabled import PDFEnabledCPTApp


def test_worker_failure_yields_ui_recovery_signal_and_diagnostic(tmp_path):
    # Invoke the actual PDFEnabledCPTApp._worker on a lightweight object
    # with no Tk initialization; only the safe worker wrapper is exercised.
    context=SimpleNamespace(messages=Queue())
    def fail(*args,**kwargs):
        raise RuntimeError("Synthetic workbook disk-full problem")
    context._work_batch=fail
    PDFEnabledCPTApp._worker(context,tmp_path,18.,2.,False)
    notice=context.messages.get_nowait()
    assert notice[0]=="fatal"
    assert "disk-full" in notice[1]
    logfile=Path(notice[2])
    assert logfile.is_file()
    assert "RuntimeError" in logfile.read_text(encoding="utf-8")


def test_no_partial_output_selected_as_completed_workbook(tmp_path):
    from app_modern_v2 import latest_excel_path
    partial=tmp_path/"CPT_Silt_Analysis_20261018.partial.xlsx"
    partial.write_bytes(b"INCOMPLETE")
    assert latest_excel_path(tmp_path) is None


def test_unexpected_tk_action_logs_locally_and_displays_recoverable_warning(tmp_path,monkeypatch):
    import sys
    from engineering_review_ui import EngineeringReviewApp
    from tkinter import messagebox
    monkeypatch.setenv("CPT_LOG_DIR",str(tmp_path))
    alerts=[]
    monkeypatch.setattr(messagebox,"showerror",lambda title,body:alerts.append((title,body)))
    class Status:
        def set(self,value):self.last=value
    ctx=SimpleNamespace(qa_status=Status())
    try:
        raise RuntimeError("Simulated GUI callback failure")
    except RuntimeError:
        kind,value,tb=sys.exc_info()
        EngineeringReviewApp.report_callback_exception(ctx,kind,value,tb)
    files=list(tmp_path.glob("gui_error_*.log"))
    assert len(files)==1
    assert "Simulated GUI callback failure" in files[0].read_text(encoding="utf-8")
    assert "unexpected UI error" in ctx.qa_status.last
    assert len(alerts)==1
    assert str(files[0]) in alerts[0][1]

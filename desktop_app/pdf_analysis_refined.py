"""Engineering-safe PDF wrapper.

A raw qualifying graphical layer must not be made thicker just to avoid a
0.00m displayed thickness. Flag a REVIEW and preserve raw evidence instead.
"""
from __future__ import annotations
from pathlib import Path
import pdf_analysis as _pdf_base
from engineering_pdf_summary import engineering_analysis_page
_pdf_base._pdf_analysis_figure = engineering_analysis_page
from pdf_analysis import append_pdf_analysis as _append_pdf_analysis
from pdf_analysis import analyze_pdf as _analyze_pdf


def analyze_pdf(path: str | Path):
    analysis=_analyze_pdf(path)
    z=analysis.final_interval
    if analysis.status=="VERIFIED" and z is not None and z.thickness_raw>0 and z.thickness <= 0:
        analysis.metadata=dict(analysis.metadata)
        analysis.metadata["thin_interval_unrounded_start"]=z.start_raw
        analysis.metadata["thin_interval_unrounded_end"]=z.end_raw
        analysis.metadata["thin_interval_unrounded_thickness"]=z.thickness_raw
        analysis.verification_note+=(
            " REVIEW: observed PDF layer is positive but its independently rounded"
            " boundaries coincide. Thickness cannot be inflated to 0.10 m"
            " without a project-approved thin-layer reporting rule."
        )
        analysis.status="REVIEW"
        analysis.final_interval=None
    return analysis


def append_pdf_analysis(source_pdf: str | Path, analysis, output_path: str | Path):
    """Preserve untouched source PDF pages and append complete engineering data."""
    from tempfile import NamedTemporaryFile
    from matplotlib.backends.backend_pdf import PdfPages
    from engineering_report_layers import full_layer_pages
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf
    source=Path(source_pdf);dest=Path(output_path)
    dest.parent.mkdir(parents=True,exist_ok=True)
    with NamedTemporaryFile(suffix=".pdf",delete=False) as tmp:
        supplement=Path(tmp.name)
    try:
        with PdfPages(supplement) as pages:
            summary=engineering_analysis_page(analysis)
            pages.savefig(summary);summary.clear()
            for fig in full_layer_pages(analysis):
                pages.savefig(fig);fig.clear()
        with pymupdf.open(str(source)) as initial, pymupdf.open(str(supplement)) as extra:
            output=pymupdf.open()
            try:
                output.insert_pdf(initial)
                output.insert_pdf(extra)
                output.save(str(dest),garbage=4,deflate=True)
            finally:
                output.close()
    finally:
        supplement.unlink(missing_ok=True)
    return dest

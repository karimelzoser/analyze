"""Engineering-safe PDF wrapper.

A raw qualifying graphical layer must not be made thicker just to avoid a
0.00m displayed thickness. Flag a REVIEW and preserve raw evidence instead.
"""
from __future__ import annotations
from pathlib import Path
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
    return _append_pdf_analysis(source_pdf,analysis,output_path)

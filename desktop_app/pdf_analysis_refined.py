from __future__ import annotations

from pathlib import Path

from cpt_core import SiltInterval, round_01
from pdf_analysis import append_pdf_analysis as _append_pdf_analysis
from pdf_analysis import analyze_pdf as _analyze_pdf


MIN_REPORTED_LAYER = 0.10


def _normalize_interval(interval: SiltInterval | None) -> tuple[SiltInterval | None, bool]:
    """Prevent a verified graphical layer from being reported as 0.00 m.

    The PDF engine already requires at least 0.05 m raw sustained thickness.
    When both independently rounded boundaries land on the same 0.10 m tick,
    preserve the reported start and represent the verified layer at the minimum
    project reporting increment of 0.10 m. This keeps the invariant
    ``reported thickness = reported end - reported start``.
    """
    if interval is None:
        return None, False
    if interval.thickness > 0.0 or interval.thickness_raw < 0.05:
        return interval, False

    interval.end = round_01(interval.start + MIN_REPORTED_LAYER)
    interval.thickness = round_01(interval.end - interval.start)
    return interval, True


def analyze_pdf(path: str | Path):
    analysis = _analyze_pdf(path)
    changed = False

    analysis.pass1, c1 = _normalize_interval(analysis.pass1)
    analysis.pass2, c2 = _normalize_interval(analysis.pass2)
    analysis.final_interval, c3 = _normalize_interval(analysis.final_interval)
    changed = c1 or c2 or c3

    if changed and analysis.status == "VERIFIED":
        analysis.verification_note += (
            " A qualifying raw PDF interval was thinner than one 0.10 m reporting increment; "
            "it is reported as 0.10 m so a verified layer is never represented as 0.00 m."
        )
    return analysis


def append_pdf_analysis(source_pdf: str | Path, analysis, output_path: str | Path):
    return _append_pdf_analysis(source_pdf, analysis, output_path)

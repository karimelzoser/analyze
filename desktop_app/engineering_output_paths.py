"""Prevent Windows WinError 206 from deeply nested OneDrive CPT output paths.

The Windows desktop application and some downstream libraries do not reliably
support extended-length (\\\\?\\) paths. Preflight for the traditional Win32
path budget before doing expensive numerical analysis. This module NEVER
alters source GEF/GFF/PDF measurements or the CPT calculation method.
"""
from __future__ import annotations

import hashlib
import ntpath
import os
from pathlib import Path
import re
import unicodedata

# Be conservative: Windows' classic MAX_PATH is 260 UTF-16 characters,
# including the terminating null. External plotting/PDF libraries also create
# temporary names, so leave ~25 characters of headroom.
LEGACY_WINDOWS_SAFE_LIMIT = 235
PDF_NAME_LIMIT = 92
_RUN_DIR = "Run_20261231_235959_999999"
_LONG_WORKBOOK = "CPT_Silt_Analysis_20261231_235959_999.partial.xlsx"
_LONG_REPORT = "CPT_" + "X" * (PDF_NAME_LIMIT - len("CPT_") - 4) + ".pdf"


def _win_length(path: str | Path) -> int:
    # ntpath works on both Unix pytest and real Windows; callers always pass
    # an absolute path on Windows. Do not produce \\?\ paths for PyMuPDF.
    return len(ntpath.normpath(str(path)))


def maximum_planned_path_length(directory: str | Path) -> int:
    """Longest prospective output path, including future PDFs and temp XLSX."""
    folder = str(directory)
    return max(_win_length(ntpath.join(folder, "PDFs", _RUN_DIR, _LONG_REPORT)),
               _win_length(ntpath.join(folder, _LONG_WORKBOOK)),
               _win_length(ntpath.join(folder, "CPT_Interactive_2D_3D_Atlas.html")),
               _win_length(ntpath.join(folder, "CPT_Processing_Failure.log")))


def windows_output_risk(directory: str | Path, *, platform_windows: bool | None = None) -> bool:
    """Conservatively flag output paths likely to produce WinError 206."""
    if platform_windows is None:
        platform_windows = os.name == "nt"
    return bool(platform_windows and
                maximum_planned_path_length(directory) > LEGACY_WINDOWS_SAFE_LIMIT)


def recommended_short_output() -> Path:
    """Permanent user-owned output folder outside nested OneDrive projects."""
    return Path.home() / "CPT_Results"


def output_path_guidance(directory: str | Path) -> str:
    return (
        "Windows cannot safely create PDF and Excel files under this deeply "
        "nested folder (WinError 206 — path too long).\n\n"
        f"Selected output:\n{directory}\n\n"
        f"Recommended short output folder:\n{recommended_short_output()}\n\n"
        "Only OUTPUT files move. GEF/GFF/PDF inputs remain in their original "
        "locations. Calculations and original measured files do not change."
    )


def safe_pdf_basename(reference: str, parent: str | Path) -> str:
    """Use the human-readable CPT reference when safe; hash unusually long IDs."""
    raw = str(reference)
    normalized = unicodedata.normalize("NFKC", raw)
    base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", normalized)
    base = base.strip(" .") or "CPT"
    # Keep a stable unique suffix when a reference must be shortened.
    suffix = ".pdf"
    max_stem = PDF_NAME_LIMIT - len(suffix)
    if len(base) > max_stem:
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
        base = base[: max_stem-len(digest)-1].rstrip(" ._-") + "_" + digest
    result = base + suffix
    if os.name == "nt" and _win_length(ntpath.join(str(parent), result)) > LEGACY_WINDOWS_SAFE_LIMIT:
        raise OSError(206, "PDF folder path is too long. Change the CPT output "
                          f"directory to {recommended_short_output()}.")
    return result

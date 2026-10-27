"""Regression for legacy Windows WinError 206 in nested OneDrive CPT projects.

This exercises path planning without real long folders. Windows CI additionally
runs the actual batch-worker preflight before any GEF calculations or mkdir.
"""
from pathlib import Path
import os
import re

import pytest

from engineering_output_paths import (
    LEGACY_WINDOWS_SAFE_LIMIT, PDF_NAME_LIMIT, maximum_planned_path_length,
    output_path_guidance, recommended_short_output, safe_pdf_basename,
    windows_output_risk,
)


LONG_ONEDRIVE = (
    r"C:\Users\Lenovo\OneDrive - Mofareh Marzouq Al-Harbi & Partners CO.LTD"
    r"\TRFR - P261074-Dammam Logistic Zone-CTS"
    r"\400 TECHNICAL DOCUMENTS\450 TESTS RESULTS\451 PRE-tests"
    r"\261022 Pre CPT GEF\261022 Pre CPT GEF\A2\CPT_Output"
)


def test_report_output_preflight_detects_real_user_one_drive_path():
    assert windows_output_risk(LONG_ONEDRIVE, platform_windows=True)
    assert maximum_planned_path_length(LONG_ONEDRIVE) > LEGACY_WINDOWS_SAFE_LIMIT
    guidance=output_path_guidance(LONG_ONEDRIVE)
    assert "WinError 206" in guidance
    assert "GEF/GFF/PDF inputs remain" in guidance
    assert "CPT_Results" in guidance


def test_short_user_owned_output_preserves_legacy_max_path_budget():
    short=r"C:\Users\Lenovo\CPT_Results"
    assert not windows_output_risk(short, platform_windows=True)
    assert maximum_planned_path_length(short) <= LEGACY_WINDOWS_SAFE_LIMIT
    assert recommended_short_output().name=="CPT_Results"


def test_windows_guard_is_inactive_on_other_operating_systems():
    assert not windows_output_risk(LONG_ONEDRIVE,platform_windows=False)


def test_pdf_names_remain_readable_for_normal_cpt_and_two_source_retests():
    folder=Path("CPT_Output")/"PDFs"/"Run_20261027_091509_589188"
    for ref in ("CPT-A2-B254-100",
                "CPT-A2-B254-100 (FILE 1 OF 2)",
                "CPT-A2-B254-100 (FILE 2 OF 2)"):
        name=safe_pdf_basename(ref,folder)
        assert name==ref+".pdf"
        assert len(name)<=PDF_NAME_LIMIT


def test_unusually_long_or_unsafe_pdf_id_has_stable_collision_resistant_name():
    folder=Path("CPT_Output")/"PDFs"
    prefix="CPT-A2-SAMPLE-"+"N"*200
    a=safe_pdf_basename(prefix+":A?",folder)
    b=safe_pdf_basename(prefix+":B?",folder)
    assert a!=b
    assert a==safe_pdf_basename(prefix+":A?",folder)
    for name in (a,b):
        assert len(name)<=PDF_NAME_LIMIT
        assert name.endswith(".pdf")
        assert not re.search(r'[<>:"/\\|?*]',name)


@pytest.mark.skipif(os.name!="nt",reason="Real Windows MAX_PATH enforcement")
def test_actual_worker_rejects_unsafe_output_before_processing_any_raw_data():
    from app_pdf_enabled import PDFEnabledCPTApp
    from types import SimpleNamespace
    fake=SimpleNamespace(files=[],messages=None)
    with pytest.raises(OSError,match="WinError 206"):
        PDFEnabledCPTApp._work_batch(fake,Path(LONG_ONEDRIVE),
                                     gamma=18.0,wt=2.0,make_pdfs=True)

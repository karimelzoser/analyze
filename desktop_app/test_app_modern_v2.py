from pathlib import Path
import os
import time

from app_modern_v2 import latest_excel_path, timestamped_excel_path


def test_latest_excel_path_prefers_newest_completed_workbook(tmp_path: Path):
    old = tmp_path / "CPT_Silt_Analysis_20260101_010101_000.xlsx"
    new = tmp_path / "CPT_Silt_Analysis_20260101_010102_000.xlsx"
    unrelated = tmp_path / "other.xlsx"
    lock = tmp_path / "~$CPT_Silt_Analysis.xlsx"

    old.write_bytes(b"old")
    time.sleep(0.01)
    new.write_bytes(b"new")
    unrelated.write_bytes(b"other")
    lock.write_bytes(b"lock")

    resolved = latest_excel_path(tmp_path, old)
    assert resolved == new


def test_latest_excel_path_uses_preferred_when_it_is_only_candidate(tmp_path: Path):
    preferred = tmp_path / "CPT_Silt_Analysis_Custom.xlsx"
    preferred.write_bytes(b"xlsx")
    assert latest_excel_path(tmp_path, preferred) == preferred


def test_timestamped_excel_name_is_unique_run_style(tmp_path: Path):
    p = timestamped_excel_path(tmp_path)
    assert p.parent == tmp_path
    assert p.suffix == ".xlsx"
    assert p.name.startswith("CPT_Silt_Analysis_")
    assert p.name != "CPT_Silt_Analysis.xlsx"

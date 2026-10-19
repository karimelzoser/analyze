"""Engineering regressions motivated by the 71-field-file A2 batch.

Full-depth B253/B256 re-tests supersede aborted initial pushes at the same
coordinates. Alternate smoothing windows remain a QA sensitivity check,
not a ballot to erase valid measurements.
"""
from pathlib import Path
from types import SimpleNamespace
import numpy as np

from app_pdf_enabled import select_project_results


def fake(path,depth,status,interval=None,e=421260.275,n=2927344.958):
    return SimpleNamespace(
        source_path=Path(path),reference="CPT-A2-B253-100",
        status=status,final_interval=interval,verification_note="synthetic regression",
        metadata={"easting":e,"northing":n,"ground_elevation":3.98},
        test_depth_raw=depth)


def test_aborted_push_is_not_full_depth_conflict():
    short=fake("P261074_CPT-A2-B253-100.GEF",.27,"NO SILT")
    full=fake("P261074_CPT-A2-B253-100-1.GEF",6.09,"VERIFIED",
         SimpleNamespace(start=5.7,end=5.8,thickness=.1))
    selected,audit=select_project_results([short,full],
         [short.source_path,full.source_path])
    assert len(selected)==1
    assert selected[0].status=="VERIFIED"
    assert selected[0].final_interval.thickness==.1
    assert selected[0].metadata["incomplete_source_count"]==1
    assert selected[0].metadata["source_revision_conflict"] is False
    assert any("ABORTED" in str(row["selection_reason"]) for row in audit)


def test_comparable_full_depth_revisions_with_different_interpretation_remain_review():
    first=fake("P261074_CPT-A2-B253-100.GEF",5.99,"VERIFIED",
         SimpleNamespace(start=5.5,end=5.8,thickness=.3))
    second=fake("P261074_CPT-A2-B253-100-1.GEF",6.09,"VERIFIED",
         SimpleNamespace(start=5.7,end=5.8,thickness=.1))
    selected,_=select_project_results([first,second],[first.source_path,second.source_path])
    assert selected[0].status=="REVIEW"
    assert selected[0].metadata["source_revision_conflict"] is True

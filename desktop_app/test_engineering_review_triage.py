"""Verification of actionable CPT REVIEW triage without invented silt."""
from pathlib import Path
from types import SimpleNamespace
from engineering_review_triage import triage_review,review_register,triage_counts


def _sample(status="REVIEW",**metadata):
    return SimpleNamespace(reference="CPT-A1-B56-100",status=status,
        source_path=Path("P261074_CPT-A1-B56-100.pdf"),
        metadata=metadata,verification_note="Vector trace reconstructed and checked.",
        test_depth_raw=5.0,sensor_dropout_depth=None)


def test_thin_pdf_measurement_is_retained_as_evidence_not_fabricated_silt():
    sample=_sample(thin_interval_unrounded_start=4.851,
                   thin_interval_unrounded_end=4.921,
                   thin_interval_unrounded_thickness=.070)
    result=triage_review(sample)
    assert result["category"]=="OBSERVED THIN INTERVAL"
    assert abs(result["measured_thickness_m"]-.070)<1e-10
    assert "never round" in result["required_action"].lower()
    assert "AWAITING REVIEW" in result["engineering_disposition"]


def test_conflicting_revisions_take_precedence_over_thin_reporting():
    sample=_sample(source_revision_conflict=True,
                   thin_interval_unrounded_thickness=.07)
    result=triage_review(sample)
    assert result["category"]=="SOURCE CONFLICT"
    assert "source_revision_conflict" in result["conflict_fields"]


def test_unknown_or_no_silt_is_not_forced_into_review():
    assert triage_review(_sample(status="NO SILT")) is None
    assert triage_review(_sample(status="VERIFIED")) is None


def test_register_and_category_counts_match_without_duplicate_evidence():
    samples=[_sample(thin_interval_unrounded_start=1.,thin_interval_unrounded_end=1.07,
                     thin_interval_unrounded_thickness=.07),
             _sample(source_spatial_conflict=True),
             _sample(status="NO SILT")]
    rows=review_register(samples)
    assert len(rows)==2
    assert triage_counts(samples)=={"OBSERVED THIN INTERVAL":1,"SOURCE CONFLICT":1}

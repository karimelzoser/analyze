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


def test_conflicting_full_length_retest_shows_provisional_measured_boundary():
    from types import SimpleNamespace
    sample=_sample(source_revision_conflict=True)
    sample.source_path=Path("P261074_CPT-A2-B254-100-1.GEF")
    sample.reference="CPT-A2-B254-100"
    sample.final_interval=SimpleNamespace(
        start=5.55,end=5.63,thickness=.08,
        start_raw=5.554,end_raw=5.630,thickness_raw=.076)
    result=triage_review(sample)
    assert result["category"]=="SOURCE CONFLICT"
    assert abs(result["measured_start_m"]-5.554)<1e-10
    assert abs(result["measured_end_m"]-5.630)<1e-10
    assert abs(result["measured_thickness_m"]-.076)<1e-10
    assert result["engineering_disposition"].startswith("AWAITING REVIEW")


def test_smoothing_disagreement_is_not_mislabeled_sensor_failure():
    # Typical A2 field pattern: ordinary 0.1m terminal unknown, but the
    # actual REVIEW trigger was 2-of-4 method sensitivity.
    sample=_sample(sensitivity_disagreement_review=True)
    sample.source_path=Path("P261074_CPT-A2-B238-100.GEF")
    sample.sensor_dropout_depth=5.708389
    sample.verification_note="2/4 sensitivity windows agree. Terminal sleeve friction dropout."
    item=triage_review(sample)
    assert item["category"]=="PROCESSING SENSITIVITY"
    assert "smoothing" in item["required_action"].lower()
    assert item["sensor_dropout_m"]==5.708389

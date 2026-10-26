"""Reference-output regression: conservative Ic screening acceptance.

The raw CPT stage-primary candidate always remains in the measurement/layer
audit. Only a 3-of-4 window agreement can yield a reportable final interval.
The baseline is the operator-accepted reference release; this is not an
independent laboratory USCS classification or foundation design validation.
"""
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import cpt_core


def _run(monkeypatch, window_intervals, stage="PRE"):
    source=SimpleNamespace(metadata={"reference":"CPT-TEST-100","ground_elevation":3.65})
    z=np.arange(0.,6.01,.01)
    base=np.ones_like(z)
    calc=dict(depth=z,qc=base,fs=base*.01,u2=base*.01,
              qt=base,fr=base,qtn=base,ic=base*2.8,
              sensor_valid=np.ones(len(z),bool),
              dropout_start=5.9,labels=["SAND-LIKE"]*len(z))
    monkeypatch.setattr(cpt_core,"parse_gef",lambda path:source)
    monkeypatch.setattr(cpt_core,"compute_robertson",lambda *args,**kw:calc)
    monkeypatch.setattr(cpt_core,"_profile_screening_interval",
        lambda depth,ic,valid,window:(
          window_intervals.get(window),
          [] if window_intervals.get(window) is None else
             [(window_intervals[window].start_raw,window_intervals[window].end_raw)],
          SimpleNamespace(brief_exceedances=[])))
    return cpt_core.analyze_gef(Path("not_needed.GEF"),stage=stage)


def _interval(start=5.3, end=5.7, thickness=.4):
    return cpt_core.SiltInterval(start,end,thickness,start,end,thickness,end)


def test_two_of_four_is_review_not_verified(monkeypatch):
    primary=_interval()
    other=_interval(5.2,5.7,.5)
    result=_run(monkeypatch,{3:primary,1:other,5:other,7:primary})
    assert result.status=="REVIEW"
    assert result.final_interval is None
    assert result.metadata["processing_sensitivity_support"]==2
    assert result.metadata["sensitivity_disagreement_review"] is True
    assert result.metadata["primary_candidate_raw_thickness_m"]==.4
    assert "REVIEW" in result.verification_note


def test_three_of_four_matching_primary_is_verified(monkeypatch):
    primary=_interval()
    other=_interval(5.2,5.7,.5)
    result=_run(monkeypatch,{3:primary,1:primary,5:primary,7:other})
    assert result.status=="VERIFIED"
    assert result.final_interval is primary
    assert result.metadata["processing_sensitivity_support"]==3
    assert result.metadata["calculation_policy"]=="REFERENCE_CONSENSUS_3_OF_4_V1"


def test_thin_positive_interval_does_not_silently_change_precision(monkeypatch):
    thin=cpt_core.SiltInterval(5.7,5.7,0.,5.6708,5.7251,.0543,5.7251)
    result=_run(monkeypatch,{3:thin,1:thin,5:thin,7:thin})
    assert result.status=="REVIEW"
    assert result.final_interval is None
    assert result.metadata["thin_interval_unrounded_start"]==5.6708
    assert result.metadata["thin_interval_unrounded_thickness"]==.0543
    assert "0.01m" in result.verification_note


def test_no_primary_and_disagreement_is_review_not_no_silt(monkeypatch):
    observed=_interval(3.8,4.0,.2)
    result=_run(monkeypatch,{3:None,1:observed,5:None,7:observed})
    assert result.status=="REVIEW"
    assert result.final_interval is None
    assert result.metadata["processing_sensitivity_support"]==2


def test_three_agree_no_primary_is_no_silt(monkeypatch):
    observed=_interval(3.8,4.0,.2)
    result=_run(monkeypatch,{3:None,1:None,5:None,7:observed})
    assert result.status=="NO SILT"
    assert result.final_interval is None
    assert result.metadata["processing_sensitivity_support"]==3


def test_post_primary_10_sample_has_same_consensus_gate(monkeypatch):
    primary=_interval()
    other=_interval(5.2,5.7,.5)
    result=_run(monkeypatch,{10:primary,7:primary,9:other,11:other},stage="POST")
    assert result.status=="REVIEW"
    assert result.metadata["analysis_smoothing_window_samples"]==10
    assert result.metadata["processing_sensitivity_support"]==2

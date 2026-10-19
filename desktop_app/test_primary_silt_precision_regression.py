"""Prevent smoothing-window consensus from deleting actual measured CPT layers."""
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import cpt_core


def _run(monkeypatch, window_intervals):
    source=SimpleNamespace(metadata={"reference":"CPT-A2-B238-100","ground_elevation":3.65})
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
    return cpt_core.analyze_gef(Path("not_needed.GEF"),stage="PRE")


def test_declared_primary_pre_window_is_not_overruled_by_sensitivity(monkeypatch):
    a=cpt_core.SiltInterval(5.3,5.7,.4,5.25,5.70,.45,5.70)
    b=cpt_core.SiltInterval(5.2,5.7,.5,5.20,5.70,.50,5.70)
    result=_run(monkeypatch,{3:a,1:b,5:b,7:a})
    assert result.status=="VERIFIED"
    assert result.final_interval is a
    assert result.metadata["processing_sensitivity_warning"] is True
    assert "SENSITIVITY WARNING" in result.verification_note


def test_observed_thin_interval_rounding_preserves_0_01m_precision(monkeypatch):
    thin=cpt_core.SiltInterval(5.7,5.7,0.,5.6708,5.7251,.0543,5.7251)
    result=_run(monkeypatch,{3:thin,1:thin,5:thin,7:thin})
    assert result.status=="VERIFIED"
    assert result.final_interval is not None
    assert result.final_interval.thickness>0
    assert result.final_interval.start==5.67
    assert result.final_interval.end==5.73
    assert result.final_interval.thickness==.06
    assert result.metadata["thin_precision_display_m"]==.01


def test_no_primary_sustained_layer_is_no_silt_with_separate_sensitivity_note(monkeypatch):
    thin=cpt_core.SiltInterval(3.8,4.0,.2,3.8,4.0,.2,4.0)
    result=_run(monkeypatch,{3:None,1:thin,5:None,7:thin})
    assert result.status=="NO SILT"
    assert result.final_interval is None
    assert result.metadata["processing_sensitivity_warning"] is True
    assert "SENSITIVITY WARNING" in result.verification_note

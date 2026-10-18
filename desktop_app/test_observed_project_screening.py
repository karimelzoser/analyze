"""Regression for project-screened, observed continuous Ic intervals.

The annotated real geotechnical field files are kept private; these synthetic
depth/trace fixtures reproduce the critical edge cases without uploading
confidential surveyed CPT data to a public GitHub repository.
"""
import numpy as np
from cpt_core import _profile_screening_interval
from engineering_layers import analyze_stratigraphy, from_analysis
from types import SimpleNamespace


def _profile(segment, *, end=1.0):
    z=np.round(np.arange(0,end+.001,.01),2)
    ic=np.full(len(z),2.2)
    for start,finish,value in segment:
        ic[(z>=start)&(z<=finish)]=value
    return z,ic,np.ones(len(z),dtype=bool)


def test_pre_three_sample_does_not_join_separate_silt_excursions():
    z,ic,valid=_profile([(0.50,0.73,2.9),(0.74,0.79,2.15),
                         (0.80,0.82,2.9)])
    layer,intervals,detail=_profile_screening_interval(z,ic,valid,3)
    assert layer is not None
    assert layer.end_raw < 0.76
    assert 0.2<=layer.thickness_raw<=0.26
    assert detail.brief_exceedances


def test_post_window_ten_is_explicit_and_does_not_bridge_dropout():
    z,ic,valid=_profile([(0.75,1.0,2.85)])
    valid[z>=.91]=False
    ic[~valid]=np.nan
    layer,intervals,detail=_profile_screening_interval(z,ic,valid,10)
    assert layer is not None
    assert layer.end_raw<=.9+1e-8
    assert detail.unknown_m>=.09-1e-8


def test_short_threshold_spikes_not_a_sustained_layer():
    z,ic,valid=_profile([(0.53,0.54,3.0)])
    for k in (1,3,5):
        selected,intervals,details=_profile_screening_interval(z,ic,valid,k)
        assert selected is None and not intervals


def test_default_profile_follows_selected_stage():
    z,ic,valid=_profile([(0.6,0.9,2.9)])
    p=SimpleNamespace(depth=z,ic=ic,valid_sensor=valid,
                      metadata={"analysis_smoothing_window_samples":10})
    result=from_analysis(p)
    assert result.rolling_window==10
    pre=from_analysis(p,rolling_window=3)
    assert pre.rolling_window==3

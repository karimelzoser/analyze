import numpy as np
import pytest
from engineering_layers import analyze_stratigraphy, behavior_label


def test_full_layers_include_every_alternating_type():
    z=np.arange(0,1.01,.01)
    ic=np.where(z < .3,1.75,np.where(z < .5,2.82,np.where(z < .7,1.80,3.20)))
    strat=analyze_stratigraphy(z,ic,rolling_window=1)
    assert len(strat.layers) >= 4
    assert strat.silt_count >= 2
    assert strat.cumulative_silt_m > .30
    assert strat.maximum_silt_m >= .15
    assert strat.layers[0].kind.startswith("SAND")


def test_terminal_fs_dropout_is_unknown_not_silt():
    z=np.arange(0,1.01,.01)
    ic=np.where(z >= .70,2.9,1.7).astype(float)
    valid=z < .91
    ic[~valid]=np.nan
    strat=analyze_stratigraphy(z,ic,valid)
    assert strat.unknown_m >= .08
    assert strat.silt_intervals
    assert strat.silt_intervals[-1][1] <= .90 + 1e-9
    assert strat.cumulative_silt_m < .25


def test_threshold_spike_recorded_but_not_counted_as_sustained_layer():
    z=np.arange(0,.31,.01)
    ic=np.full(len(z),2.2)
    ic[12]=3.0
    strat=analyze_stratigraphy(z,ic,min_silt_m=.05)
    assert strat.silt_count == 0
    assert len(strat.brief_exceedances) == 1


def test_thin_observed_layer_not_inflated_by_reporting():
    z=np.arange(0,.51,.01)
    ic=np.full(len(z),2.0)
    ic[20:27]=2.80
    strat=analyze_stratigraphy(z,ic)
    assert len(strat.silt_intervals)==1
    thickness=strat.cumulative_silt_m
    assert .05 < thickness < .08


def test_smoothing_does_not_bridge_missing_or_gap():
    z=np.arange(0,.41,.01)
    z=np.r_[z[:20],z[20:]+.2]
    ic=np.full(len(z),2.8)
    ic[15:18]=np.nan
    s=analyze_stratigraphy(z,ic,rolling_window=10)
    assert s.unknown_m > .15
    assert s.silt_count>=1


def test_bad_depths_rejected():
    with pytest.raises(ValueError):
        analyze_stratigraphy([0,.2,.1],[2,2.8,3])


def test_reference_categories_are_behavior_not_uscs():
    assert behavior_label(2.6)=="SANDY SILT-LIKE"
    assert behavior_label(3.2)=="CLAY-LIKE"

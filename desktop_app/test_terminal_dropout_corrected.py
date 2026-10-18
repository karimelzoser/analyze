import numpy as np
from cpt_core import _detect_interval


def test_terminal_sensor_dropout_not_included_in_silt_thickness():
    depth=np.round(np.arange(0.0,6.41,.01),2)
    ic=np.where(depth>=6.2,2.8,2.1).astype(float)
    good=depth<=6.3
    ic[~good]=np.nan
    z,all_segments=_detect_interval(depth,ic,good,6.4,6.31,2.60,1,.06,.05)
    assert z is not None
    assert z.end_raw <=6.30001
    assert z.thickness_raw <=.12
    assert z.end <=6.3
    assert all_segments


def test_no_terminal_dropout_only_spike_rejected():
    depth=np.round(np.arange(0,1.01,.01),2)
    ic=np.full(len(depth),2.1)
    ic[-12:-10]=2.9
    valid=np.ones(len(ic),bool)
    valid[-10:]=False
    ic[-10:]=np.nan
    result,_=_detect_interval(depth,ic,valid,1.0,.91,2.60,1,.06,.05)
    assert result is None


def test_short_real_reversal_splits_main_silt_from_secondary_spike():
    # Replicates B18-like pattern: 0.20m sustained main Ic exceedance,
    # a 0.03m below-threshold reversal, then an isolated 0.03m high spike.
    depth=np.round(np.arange(0,4.65,.01),2)
    ic=np.full(len(depth),2.20)
    ic[(depth>=4.29)&(depth<=4.49)]=3.0
    ic[(depth>=4.53)&(depth<=4.56)]=3.1
    good=np.ones(len(depth),bool)
    good[(depth>=4.59)]=False
    ic[~good]=np.nan
    result,runs=_detect_interval(depth,ic,good,4.64,4.59,2.60,1,.025,.05)
    assert result is not None
    assert result.start==4.3
    assert result.end==4.5
    assert result.thickness==0.2
    assert len(runs)==1


def test_without_sustained_interval_short_threshold_crossing_is_not_silt():
    depth=np.round(np.arange(0,4.6,.01),2)
    ic=np.full(len(depth),2.15)
    ic[(depth>=4.28)&(depth<=4.31)]=2.75
    valid=np.ones(len(depth),bool)
    interval,runs=_detect_interval(depth,ic,valid,4.59,None,2.60,1,.025,.05)
    assert interval is None
    assert not runs

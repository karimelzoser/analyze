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

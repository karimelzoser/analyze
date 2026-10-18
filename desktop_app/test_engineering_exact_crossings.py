import numpy as np
from cpt_core import _detect_interval,_terminal_sensor_valid


def test_valid_falling_threshold_is_interpolated_not_left_at_previous_sample():
    z=np.arange(4.2,4.701,.01)
    ic=np.where(z<4.31,2.1,np.where(z<4.55,2.8,2.1))
    good=np.ones(len(z),bool)
    value,_=_detect_interval(z,ic,good,float(z[-1]),None,2.60,1,.06,.05)
    assert value is not None
    assert value.start==4.3
    assert value.end==4.6
    assert value.thickness==.3
    assert 4.55<value.end_raw<4.56


def test_sensor_dropout_does_not_infer_end_beyond_last_valid_record():
    z=np.arange(6.0,6.361,.01)
    ic=np.where(z>=6.20,2.8,2.2).astype(float)
    good=np.ones(len(z),bool)
    good[z>=6.26]=False
    ic[~good]=np.nan
    value,_=_detect_interval(z,ic,good,z[-1],6.26,2.60,1,.06,.045)
    assert value is not None
    assert value.start==6.2
    assert value.end==6.3
    assert value.thickness==.1
    assert value.end_raw<=6.261  # final valid sample; never inferred into dropout

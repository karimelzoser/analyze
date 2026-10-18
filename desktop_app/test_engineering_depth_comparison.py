from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import zipfile
from engineering_depth_comparison import compare_depth_profiles, export_depth_change


def _sample(name,easting=421092.37,offset=.0,missing=False):
    z=np.round(np.arange(0.1,1.01,.01),3)
    qc=5.0+2*z+offset
    ic=2.0+0.2*z+offset/10
    valid=np.ones(len(z),bool)
    if missing:
        valid[(z>.64)&(z<.76)]=False
        ic[~valid]=np.nan
    return SimpleNamespace(
        reference=name,metadata={"easting":easting,"northing":2928336.25,"ground_elevation":3.46},
        depth=z,qc=qc,fs=qc/100,u2=qc/60,qt=qc+.02,fr=qc/10,qtn=qc*20,
        ic=ic,valid_sensor=valid)


def test_identical_profile_has_zero_delta():
    p=_sample("CPT-A1-B1-100")
    change=compare_depth_profiles(p,p)
    for key in ("qc","fr","qtn","ic"):
        vals=change.metrics[key]["delta"]
        assert np.nanmax(np.abs(vals))<1e-10


def test_qc_delta_not_smoothing_artifact():
    a=_sample("CPT-A1-B1-100")
    b=_sample("CPT-A1-B1-100",offset=1.5)
    change=compare_depth_profiles(a,b,mode="harmonized")
    assert abs(change.statistics["qc"]["mean_delta"]-1.5)<1e-9
    assert change.statistics["ic"]["paired_samples"]>20
    change2=compare_depth_profiles(a,b,mode="reference")
    assert change2.pre_window==3 and change2.post_window==10
    assert any("apparent changes" in note for note in change2.notes)


def test_sensor_dropout_is_not_bridge_interpolated():
    a=_sample("CPT-A1-B1-100")
    b=_sample("CPT-A1-B1-100",offset=1.0,missing=True)
    ch=compare_depth_profiles(a,b)
    no=(ch.depth_m>.67)&(ch.depth_m<.72)
    assert np.isnan(ch.metrics["ic"]["delta"][no]).all()
    # qc is still measured, but the invalid Ic sensor is never invented.
    assert np.isfinite(ch.metrics["qc"]["delta"][no]).all()


def test_coordinate_mismatch_is_blocked():
    a=_sample("CPT-A1-B1-100")
    b=_sample("CPT-A1-B1-100",easting=421200)
    try:
        compare_depth_profiles(a,b)
    except ValueError as err:
        assert "coordinate" in str(err)
    else:
        assert False,"Must reject unrelated points"


def test_export_workbook_and_pdf_and_png(tmp_path):
    data=compare_depth_profiles(_sample("PRE"),_sample("POST",offset=1.0))
    artifacts=export_depth_change(data,tmp_path)
    assert set(artifacts)=={"xlsx","png","pdf"}
    for path in artifacts.values():
        assert path.exists() and path.stat().st_size>2000
    with zipfile.ZipFile(artifacts["xlsx"]) as archive:
        names=archive.read("xl/workbook.xml")
        assert b"Depth Profiles" in names and b"Statistics" in names and b"Comparison QA" in names

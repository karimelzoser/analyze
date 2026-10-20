"""Regression tests for physically bounded isolated foundation screening."""
import math
from types import SimpleNamespace

import numpy as np
import pytest

from engineering_isolated_settlement import (
    IsolatedInputs, derive_isolated_settlement, attach_isolated_estimates)


def test_zero_source_pressure_is_invalid_not_automatically_passed():
    with pytest.raises(ValueError):
        IsolatedInputs(net_pressure_kpa=0).validate()


def _cpt(qt=6.0, depth_end=10.0, reference="CPT-A1-B299-100"):
    z=np.arange(.02,depth_end+.0001,.02)
    return SimpleNamespace(
        reference=reference,source_path="measured.GEF",
        depth=z,qt=np.full(len(z),qt,dtype=float),
        metadata={"easting":421012.0,"northing":2928012.0})


def test_higher_modulus_reduces_settlement_load_increases_settlement():
    input=IsolatedInputs(width_m=3.,length_m=3.,net_pressure_kpa=150.,
                        embedment_m=1.,influence_b=2.,
                        qc_modulus_factor=5.,min_coverage=.95)
    baseline=derive_isolated_settlement(_cpt(),input)
    hard=derive_isolated_settlement(_cpt(qt=12),input)
    heavy=derive_isolated_settlement(_cpt(),IsolatedInputs(
        net_pressure_kpa=300.,min_coverage=.95))
    assert baseline.status=="ESTIMATE — COVERAGE SUFFICIENT"
    assert baseline.calculated_settlement_mm>0
    assert hard.calculated_settlement_mm==pytest.approx(
        baseline.calculated_settlement_mm/2,rel=.001)
    assert heavy.calculated_settlement_mm==pytest.approx(
        baseline.calculated_settlement_mm*2,rel=.001)
    assert baseline.criterion_status.startswith("NOT ASSESSED")


def test_partial_soundings_preserve_observed_strain_but_no_fake_total():
    r=derive_isolated_settlement(_cpt(depth_end=5.5),IsolatedInputs())
    assert r.status=="INCOMPLETE — DEPTH COVERAGE"
    assert r.calculated_settlement_mm is None
    assert r.observed_settlement_mm is not None
    assert 65<r.coverage_percent<85
    assert r.last_valid_depth_m<7.
    assert len(r.integration)>0


def test_invalid_qt_gap_never_interpolated_and_reduces_coverage():
    x=_cpt()
    x.qt[(x.depth>2.4)&(x.depth<2.9)]=np.nan
    r=derive_isolated_settlement(x,IsolatedInputs(min_coverage=.95))
    assert r.calculated_settlement_mm is None
    assert r.coverage_percent<95
    assert not any(2.4<d["depth_bgl_m"]<2.9 for d in r.integration)


def test_source_matching_requires_same_reference_and_location():
    from engineering_comparison import SummaryPoint
    a=_cpt()
    good=SummaryPoint(a.reference,"ISOLATED",421012.1,2928012.05,
        {"settlement_mm":55.0},"Isolated Summary",footing_width_m=3.)
    miss=SummaryPoint("CPT-A1-B299-100","ISOLATED",421100,2928012,
        {"settlement_mm":60.0},"Isolated Summary")
    results=attach_isolated_estimates([a],[good,miss],IsolatedInputs())
    assert results[0].calculated_settlement_mm is not None
    assert results[0].source_settlement_mm==55.0
    assert results[0].source_delta_mm is not None
    assert results[1].calculated_settlement_mm is None
    assert results[1].status.startswith("NOT CALCULABLE")

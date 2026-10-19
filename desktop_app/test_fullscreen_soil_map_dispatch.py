"""Regression: full-screen depth-classified soil map must show COLOR REGIONS,
not switch silently to risk-score or point-only scatter."""
from matplotlib.figure import Figure
import numpy as np
from pathlib import Path
from types import SimpleNamespace
from engineering_map_dispatch import render_fullscreen_map


def _point(ref,x,y,ic):
    z=np.arange(0,6.01,.01)
    return SimpleNamespace(reference=ref,source_path=Path(ref+".GEF"),
        depth=z,ic=np.full(len(z),ic,dtype=float),
        valid_sensor=np.ones(len(z),dtype=bool),
        metadata={"easting":x,"northing":y,"ground_elevation":3.7},
        status="VERIFIED",test_depth_raw=6.0)


def test_fullscreen_renders_colored_soil_classes_at_selected_depth(tmp_path):
    pts=[
        _point("B1",421000,2928000,1.70),
        _point("B2",421030,2928000,2.30),
        _point("B3",421000,2928030,2.75),
        _point("B4",421030,2928030,3.10),
    ]
    fig=Figure(figsize=(8,6),dpi=110)
    result=render_fullscreen_map(fig,pts,"Soil-behaviour color map",
        slice_top_m=4.0,slice_bottom_m=5.0,interpretive_fill=True)
    assert result["classified"]==4
    assert result["supported_triangles"]>=1
    assert result["filled_cells"]>0
    assert result["unknown"]==0
    assert len(fig.axes)==1
    out=tmp_path/"soil_full_screen.png"
    fig.savefig(out)
    assert out.stat().st_size>6000


def test_fullscreen_map_rejects_invalid_depth_band():
    import pytest
    with pytest.raises(ValueError,match="depth window"):
        render_fullscreen_map(Figure(),[],"Soil-behaviour color map",
                              slice_top_m=5.,slice_bottom_m=4.)

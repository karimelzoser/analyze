"""Functional assertions for locally bounded colored soil maps and 3D blocks."""
import numpy as np
from types import SimpleNamespace
from matplotlib.figure import Figure

from engineering_soil_maps import soil_depth_plan
from engineering_3d_map import site_3d_figure
from engineering_3d_studio import export_professional_3d


def _cpt(i,x,y,ic):
    z=np.round(np.arange(.0,1.01,.01),3)
    return SimpleNamespace(reference=f"CPT-A2-B{i}-100",status="VERIFIED",
        source_path=__import__("pathlib").Path(f"CPT-A2-B{i}-100.GEF"),
        metadata={"easting":x,"northing":y,"ground_elevation":3.5},
        depth=z,ic=np.full(len(z),ic,dtype=float),
        valid_sensor=np.ones(len(z),dtype=bool),test_depth_raw=1.0)


def _project():
    return [_cpt(1,421000,2927000,1.75),
            _cpt(2,421025,2927000,2.32),
            _cpt(3,421000,2927025,2.8),
            _cpt(4,421025,2927025,3.25)]


def test_2d_filled_soil_color_regions_at_selected_depth(tmp_path):
    fig=Figure(figsize=(8,6),dpi=90)
    summary=soil_depth_plan(fig,_project(),depth_m=.5,
                            max_spacing_m=50,fill_interpretation=True)
    assert summary["classified"]==4
    assert summary["supported_triangles"]>=1
    assert summary["filled_cells"]>0
    fig.savefig(tmp_path/"soil_levels.png")
    assert (tmp_path/"soil_levels.png").stat().st_size>3000


def test_3d_contains_measured_colored_solid_faces(tmp_path):
    fig,s=site_3d_figure(_project())
    assert s["plotted"]==4
    assert any(hasattr(item,"get_facecolor") for item in fig.axes[0].collections)
    fig.savefig(tmp_path/"soil_blocks.png")
    assert (tmp_path/"soil_blocks.png").stat().st_size>3000


def test_offline_interactive_3d_contains_togglable_mesh_prisms(tmp_path):
    try:
        result=export_professional_3d(_project(),tmp_path/"3d_layers.html")
    except ImportError:
        import pytest
        pytest.skip("Plotly not installed in source-only environment")
    html=result["file"].read_text(encoding="utf-8")
    assert 'type:"mesh3d"' in html
    assert "interpolated" in html.lower() or "interpreted" in html.lower()
    assert "observed soil blocks" in html

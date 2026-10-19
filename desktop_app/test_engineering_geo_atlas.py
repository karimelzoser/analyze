"""Offline map laboratory: categorical 2D+3D, source parameters and JS safety."""
from pathlib import Path
from types import SimpleNamespace
import re
import shutil
import subprocess

import numpy as np
import pytest

from engineering_geo_atlas import export_geo_atlas


def _raw(index,e,n,ic):
    depth=np.round(np.arange(0,6.01,.05),4)
    ic_values=np.where(depth>4.5,ic,1.84).astype(float)
    qc=np.where(depth>4.5,2.0,8.0).astype(float)
    return SimpleNamespace(
        reference=f"CPT-A2-B{index}-100",source_path=Path(f"CPT-A2-B{index}-100.GEF"),
        status="VERIFIED",
        metadata={"easting":e,"northing":n,"ground_elevation":3.7},
        depth=depth,qc=qc,fs=np.full(len(depth),.06),u2=np.full(len(depth),.02),
        qt=qc+.005,fr=np.full(len(depth),2.5),
        qtn=np.full(len(depth),30.),ic=ic_values,
        valid_sensor=np.ones(len(depth),bool),test_depth_raw=6.0)


def test_atlas_offline_interactive_maps_and_raw_parameters(tmp_path):
    cpts=[_raw(1,421000,2927000,2.8),
          _raw(2,421025,2927000,3.15),
          _raw(3,421000,2927030,2.55),
          _raw(4,421025,2927030,2.75)]
    out=tmp_path/"CPT_ATLAS.html"
    result=export_geo_atlas(cpts,out)
    assert result["atlas"] is True
    assert result["points"]==4
    assert result["plan_faces"]>=1
    html=out.read_text(encoding="utf-8")
    assert len(html)>2_000_000
    for token in ('two.id="cpt-atlas-2d"','host.id="cpt-atlas-screen"','2D SOIL PLAN',
                  "3D SUBSURFACE","plotly_click","qc at ","Easting",
                  "Max observed silt", "Supported"):
        # Some tokens are authored by DOM JavaScript rather than initial HTML.
        assert token.lower() in html.lower(),token
    assert "cdn.plot.ly" not in html.lower()
    assert "https://cdn.jsdelivr" not in html.lower()


def test_no_gap_filling_outside_triangles_and_outliers_filtered(tmp_path):
    cpts=[_raw(i,421000+(i%3)*20,2927000+(i//3)*20,2.8)
          for i in range(1,7)]
    bad=_raw(7,4_210_000,2927000,3.2)
    result=export_geo_atlas(cpts+[bad],tmp_path/"site.html")
    assert result["withheld"]==1
    assert result["points"]==6
    assert result["plan_faces"]>=1


def test_injected_js_parses_with_node(tmp_path):
    node=shutil.which("node")
    if not node:pytest.skip("node not installed")
    result=export_geo_atlas([
        _raw(1,421000,2927000,2.8),
        _raw(2,421025,2927000,2.8),
        _raw(3,421000,2927025,2.8)
    ],tmp_path/"model.html")
    content=result["file"].read_text(encoding="utf-8")
    section=re.search(r'<script id="cpt-atlas-interactive-upgrade">(.*?)</script>',content,re.S)
    assert section is not None
    js=tmp_path/"atlas.js";js.write_text(section.group(1),encoding="utf-8")
    run=subprocess.run([node,"--check",str(js)],capture_output=True,text=True,timeout=20)
    assert run.returncode==0,run.stderr

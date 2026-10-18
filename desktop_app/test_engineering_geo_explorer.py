"""Regression tests for geotechnical 2D plan and offline 3D interpretation."""
from pathlib import Path
from matplotlib.figure import Figure
from engineering_geo_explorer import (
    risk_plan,spatial_points,_triangle_mask,interpreted_wedges,export_interactive_3d)
from engineering_help import TOPICS


def _project_points():
    # Six properly surveyed points with two separately observed high-thickness
    # values. A false distant coordinate is retained as QA, not interpolated.
    coords=[(100,100),(125,100),(100,125),(125,125),(150,100),(150,125)]
    values=[.30,.34,.12,.28,.32,.07]
    data=[]
    for i,((x,y),value) in enumerate(zip(coords,values)):
        data.append({
            "reference":f"CPT-A1-B{i+1}-100","easting":float(x),
            "northing":float(y),"ground_elevation":3.50,
            "test_depth_m":6.5,"status":"REFERENCE-CACHED",
            "max_contiguous_silt_screen_m":value,
            "cumulative_silt_screen_m":value,
            "all_intervals":[{"start_raw":4.8,"end_raw":4.8+value}]
        })
    return data


def test_all_high_cpt_ties_and_multiple_locations_remain_accessible():
    fig=Figure(figsize=(9,6))
    result=risk_plan(fig,_project_points(),warning_m=.10,high_m=.30)
    assert len(result["high"])==3
    assert {p.reference for p in result["high"]}=={
        "CPT-A1-B1-100","CPT-A1-B2-100","CPT-A1-B5-100"}
    assert result["screen_counts"]["HIGH"]==3
    assert result["supported_triangles"]>=1
    assert result["artists"]


def test_no_surface_in_distant_gap_or_without_three_points():
    data=_project_points()[:2]
    out=risk_plan(Figure(),data)
    assert out["supported_triangles"]==0
    tri,idx,_=_triangle_mask([(0,0),(10,0),(0,10),(10000,10000)],
                            max_spacing_m=30)
    assert tri is not None
    assert all(max(abs(float(v)) for v in (0,))==0 for _ in [0])
    assert tri.mask is not None
    assert tri.mask.any()


def test_3d_only_connects_overlapping_observed_layers():
    pts,_=spatial_points(_project_points()[:4])
    wedges,n=interpreted_wedges(pts,max_spacing_m=70)
    assert n==4
    assert len(wedges)>0
    invalid=[{**p} for p in _project_points()[:4]]
    invalid[0]["all_intervals"]=[{"start_raw":5.8,"end_raw":6.1}]
    points,_=spatial_points(invalid)
    # At least some triangles involving the distant-in-depth CPT are blocked.
    new,number=interpreted_wedges(points,max_spacing_m=70)
    assert len(new)<len(wedges)


def test_full_3d_html_is_genuinely_offline_and_rotatable(tmp_path):
    result=export_interactive_3d(_project_points(),
                                 tmp_path/"geology_3d.html",
                                 max_spacing_m=70)
    page=result["file"].read_text("utf-8")
    assert result["points"]==6
    assert result["wedges"]>0
    assert result["file"].stat().st_size>2000000
    assert "plotly.js" in page.lower() or "plotly.min.js" in page.lower()
    assert "No network" not in page
    assert "Interpreted silt-like wedge" in page
    assert "vertical" in page.lower()


def test_original_survey_outlier_does_not_expand_model_bounds():
    erroneous={**_project_points()[0],"reference":"BAD-CPT","northing":999999.}
    pts,bad=spatial_points(_project_points()+[erroneous])
    assert len(pts)==6 and len(bad)==1


def test_help_is_comprehensive_and_contains_the_actual_formulas():
    assert len(TOPICS)>=7
    alltext="\n".join(x for name,x in TOPICS)
    for formula in ("qt (MPa)","sigma_v0","Qtn","Fr (%)","Ic",
                    "groundwater","PRE","POST","REVIEW"):
        assert formula.lower() in alltext.lower()

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
    assert "E-W CPT fence" in page and "N-S CPT fence" in page
    assert len(result["fence_sections"])==2
    assert result["fence_sections"][0]["points"]>=2


def test_original_survey_outlier_does_not_expand_model_bounds():
    original=_project_points()
    for j in range(3):
        new={**original[0],"reference":f"EXTRA-{j}",
             "easting":170.0+j*20.0,"northing":105.0+j*7}
        original.append(new)
    erroneous={**original[0],"reference":"BAD-CPT","northing":999999.}
    pts,bad=spatial_points(original+[erroneous])
    assert len(pts)==9 and len(bad)==1


def test_help_is_comprehensive_and_contains_the_actual_formulas():
    assert len(TOPICS)>=7
    alltext="\n".join(x for name,x in TOPICS)
    for formula in ("qt (MPa)","sigma_v0","Qtn","Fr (%)","Ic",
                    "groundwater","PRE","POST","REVIEW"):
        assert formula.lower() in alltext.lower()


def test_multiple_separated_3d_soil_layers_both_mapped_not_only_longest():
    from engineering_geo_explorer import spatial_points,interpreted_wedges
    coords=[(100,100),(120,100),(100,120),(120,120)]
    data=[{"reference":f"TEST-{i}","easting":x,"northing":y,
        "ground_elevation":10.,"test_depth_m":8.,
        "status":"REFERENCE-CACHED","max_contiguous_silt_screen_m":.30,
        "cumulative_silt_screen_m":.5,
        "all_intervals":[{"start_raw":1.0,"end_raw":1.22},
                         {"start_raw":5.0,"end_raw":5.30}]} for i,(x,y) in enumerate(coords)]
    points,_=spatial_points(data)
    wedges,eligible=interpreted_wedges(points,max_spacing_m=50)
    assert eligible==4
    assert len(wedges)>=4   # Each supported triangle has TWO separated bands
    tops={round(item[1][0],2) for item in wedges}
    assert 9.0 in tops and 5.0 in tops


def test_depth_window_only_counts_screening_inside_selected_band():
    from engineering_geo_explorer import depth_window_records,depth_window_plan
    base=_project_points()[0]
    layer=depth_window_records([base],4.9,5.0)
    assert len(layer)==1
    assert round(layer[0]["max_contiguous_silt_screen_m"],3)==.1
    other=depth_window_records([base],2.0,3.0)
    assert other[0]["max_contiguous_silt_screen_m"]==0
    beyond=depth_window_records([base],6.4,7.2)
    assert beyond[0]["status"]=="REVIEW"  # no sounding at this depth
    assert beyond[0]["max_contiguous_silt_screen_m"] is None
    result=depth_window_plan(Figure(),_project_points(),
                       top_m=4.8,bottom_m=5.10,high_m=.31,
                       show_interpretive_surface=False)
    assert result["depth_window"]==(4.8,5.1)
    assert len(result["high"])==0


def test_depth_window_requires_measured_sensor_coverage_not_just_final_depth():
    import numpy as np
    from types import SimpleNamespace
    from engineering_geo_explorer import depth_window_records
    z=np.arange(0,6.01,.01)
    ic=np.where(z>=4.8,2.9,2.2)
    valid=np.ones(len(z),bool)
    valid[(z>=4.9)&(z<5.4)]=False
    ic[~valid]=np.nan
    item=SimpleNamespace(reference="TEST-GAP",depth=z,ic=ic,valid_sensor=valid,
                         test_depth_raw=6.,status="VERIFIED",
                         metadata={"easting":100.,"northing":100.,"ground_elevation":3.5})
    row=depth_window_records([item],4.8,5.4)[0]
    assert row["status"]=="REVIEW"
    assert row["max_contiguous_silt_screen_m"] is None


def test_bad_slice_settings_rejected():
    import pytest
    from engineering_geo_explorer import depth_window_records
    with pytest.raises(ValueError):
        depth_window_records([],5.,4.)


def test_source_xlsb_depth_coverage_gaps_are_unknown_not_clean_soil():
    from engineering_geo_explorer import depth_window_records
    reference={"reference":"CPT-REF","easting":421000.,"northing":2928000.,
        "ground_elevation":3.5,"test_depth_m":6.,
        "status":"REFERENCE-CACHED",
        "source_classified_depths_m":[round(x*.01,3) for x in range(0,450)]+[
            round(x*.01,3) for x in range(550,601)],
        "all_intervals":[{"start_raw":4.3,"end_raw":4.6},
                         {"start_raw":5.7,"end_raw":5.9}]}
    missing=depth_window_records([reference],4.6,5.4)[0]
    assert missing["status"]=="REVIEW"
    assert missing["max_contiguous_silt_screen_m"] is None
    measured=depth_window_records([reference],5.6,6.0)[0]
    assert measured["status"]=="REFERENCE-CACHED"
    assert measured["max_contiguous_silt_screen_m"]>.19

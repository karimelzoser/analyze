from engineering_reference_project import _segments,_tenth,analyze_original_xlsb,export_original_project
from test_engineering_xlsb_reference import make_reference_fixture
from pathlib import Path


def test_cached_sbt_zones_reproduce_documented_a1_292_terminal_change():
    # Extracted behavior of actual source 'Combined CPTs' for A1-292:
    # Zone 5 through 6.19m, Zone 4 at 6.20..6.28, Zone 5 at 6.29m.
    ground=3.46
    records=[(ground-i*.01,2.0,5) for i in range(610,620)]
    records +=[(ground-i*.01,1.2,4) for i in range(620,629)]
    records +=[(ground-i*.01,.8,5) for i in range(629,633)]
    detected,brief=_segments(records,ground)
    assert len(detected)==1
    first=detected[0]
    assert first["reported_start"]==6.2
    assert first["reported_end"]==6.3
    assert first["reported_thickness"]==.1
    assert abs(first["thickness_raw"]-.09)<1e-8


def test_all_reference_layers_and_thin_exceedances_are_separate():
    points=[]
    ground=3.
    for i in range(100):
        code=4 if 20<=i<25 or 60<=i<75 else 5
        points.append((ground-i*.01,2.,code))
    layers,brief=_segments(points,ground)
    assert len(layers)==2
    assert sum(x["thickness_raw"] for x in layers)>.19


def test_original_model_project_excel_maps_run_without_excel(tmp_path):
    path=tmp_path/"model.xlsb"
    make_reference_fixture(path)
    result=export_original_project(path,tmp_path/"out")
    assert result["project_cpt_count"]==1
    assert result["workbook"].is_file()
    assert len(result["maps"])==4
    assert all(x.stat().st_size>1500 for x in result["maps"])

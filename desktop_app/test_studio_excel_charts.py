"""Regression contract for the restored Excel Charts sheet and new 3D UI."""
from pathlib import Path
from zipfile import ZipFile

from benchmark_synthetic_batch import make_synthetic_gef
from cpt_core import analyze_gef
from engineering_3d_studio import collect_observed_segments,export_professional_3d
from reporting_export_v2 import export_excel
from test_engineering_geo_explorer import _project_points


def test_five_distinct_3d_layer_categories_and_unknown(tmp_path):
    p=tmp_path/"CPT.GEF"
    make_synthetic_gef(p,2,155)
    a=analyze_gef(p,water_table_depth=2.)
    segments,excluded,_=collect_observed_segments([a])
    assert segments and excluded==0
    assert all(s["bottom"]>s["top"] for s in segments)
    assert all(s["category"] in ("sand","transition","silt","clay","unknown") for s in segments)


def test_categorical_original_xlsb_zone_layers_not_confused_with_ic():
    sample={**_project_points()[0]}
    sample["zone_segments"]=[
        {"start":0,"end":.6,"zone":6},
        {"start":.6,"end":.8,"zone":5},
        {"start":.8,"end":1.1,"zone":4},
        {"start":1.1,"end":1.4,"zone":3},
        {"start":1.4,"end":1.6,"zone":9},
    ]
    segments,excluded,_=collect_observed_segments([sample])
    cats={s["category"] for s in segments}
    assert {"sand","transition","silt","clay"}.issubset(cats)
    assert all("cached SBT Zone" in s["source"] for s in segments)


def test_offline_html_controls_are_above_first_3d_plot(tmp_path):
    output=export_professional_3d(_project_points(),
                                  tmp_path/"CPT_3D_Studio.html",max_spacing_m=70)
    html=output["file"].read_text(encoding="utf-8")
    assert output["points"]==6
    for term in ("3D soil-behaviour explorer","cpt-top","cpt-bottom",
                 "cpt-camera","data-layer=\"unknown\"",
                 "cpt-wedges","cpt-reset","E-W CPT fence","N-S CPT fence"):
        assert term in html,term
    assert html.index('id="cpt-studio"') < html.index('Plotly.newPlot(')
    assert '<script src="https://cdn.plot.ly' not in html
    assert output["file"].stat().st_size>2000000


def test_one_excel_workbook_restores_8_real_charts_and_data(tmp_path):
    source=tmp_path/"sample.GEF"
    make_synthetic_gef(source,20,140)
    analysis=analyze_gef(source,water_table_depth=2.)
    path=export_excel([analysis],tmp_path/"restored.xlsx")
    with ZipFile(path) as archive:
        workbook=archive.read("xl/workbook.xml")
        assert b'Charts' in workbook and b'CPT Curves' in workbook
        charts=[p for p in archive.namelist() if
                p.startswith("xl/charts/chart") and p.endswith(".xml")]
        assert len(charts)>=8,charts
        # Every data series should refer to auditable Excel workbook values.
        content=b"".join(archive.read(p) for p in charts)
        assert b'CPT Measurements' in content
        assert b'Charts' in content
        assert len([x for x in archive.namelist() if x.startswith("xl/media/")])>=2

from pathlib import Path
from types import SimpleNamespace
from engineering_reference_parity import compare_engine_to_reference,export_parity_workbook


def _native(start=6.2,thickness=.2,e=421092.37):
    return SimpleNamespace(reference="CPT-A1-292-100",source_path=Path("A1-292.GEF"),
        metadata={"easting":e,"northing":2928336.25,"area_ratio":.75},
        status="VERIFIED",final_interval=SimpleNamespace(start=start,thickness=thickness))


def _saved():
    return [{"reference":"CPT-A1-292-100","easting":421092.37,
             "northing":2928336.25,"silt_start_m":6.2,"silt_thickness_m":.1}]


def test_a1_292_legacy_twenty_centimeter_result_is_not_silently_accepted():
    rows=compare_engine_to_reference([_native()],_saved(),water_table=0,
                           reference_settings={"water_depth_m":2.,"cone_ratio":.8})
    assert len(rows)==1
    r=rows[0]
    assert "MISMATCH" in r["status"]
    assert abs(r["difference_thickness"]-.1)<1e-8
    assert "Groundwater discrepancy" in r["notes"]
    assert "Cone area-ratio discrepancy" in r["notes"]


def test_same_assumption_and_source_result_matches_and_exports(tmp_path):
    a=_native(thickness=.1)
    a.metadata["area_ratio"]=.8
    rows=compare_engine_to_reference([a],_saved(),water_table=2,
                            reference_settings={"water_depth_m":2.,"cone_ratio":.8})
    assert rows[0]["status"]=="AGREE"
    out=export_parity_workbook(rows,tmp_path/"reference-qa.xlsx")
    assert out.stat().st_size>2000


def test_wrong_coordinates_block_reference_pairing():
    rows=compare_engine_to_reference([_native(e=422092)],_saved())
    assert rows[0]["reference_start"] is None
    assert rows[0]["status"].startswith("REVIEW")

from pathlib import Path
import xlsxwriter
from engineering_comparison import SummaryPoint, compare_summaries, read_summary_xlsx, export_comparison
from engineering_maps import render_site_map,render_layer_profile,coordinate_rows
import numpy as np
from types import SimpleNamespace


def test_comparison_paired_and_unpaired_uses_coordinate_guard():
    a=[SummaryPoint("CPT-A1-B292-100","RAFT",421092.37,2928336.25,{"settlement_mm":70.0,"fos":2.4},"Raft Summary")]
    b=[SummaryPoint("CPT-A1-292-100","RAFT",421092.38,2928336.28,{"settlement_mm":55.0,"fos":2.6},"Raft Summary")]
    c=compare_summaries(a,b,coordinate_tolerance=2)
    assert len(c["matched"])==1
    assert c["matched"][0]["metrics"]["settlement_mm"]["delta"]==-15
    assert c["matched"][0]["metrics"]["fos"]["delta"]>0
    far=[SummaryPoint("CPT-A1-292-100","RAFT",421200,2928336,{"settlement_mm":55},"Raft Summary")]
    assert not compare_summaries(a,far)["matched"]


def test_no_fabricated_percent_from_zero_baseline():
    a=[SummaryPoint("CPT-A1-B1-100","CPT",None,None,{"silt_thickness_m":0.0},"CPT Analysis")]
    b=[SummaryPoint("CPT-A1-B1-100","CPT",None,None,{"silt_thickness_m":.2},"CPT Analysis")]
    c=compare_summaries(a,b)
    assert c["matched"][0]["metrics"]["silt_thickness_m"]["percent"] is None


def test_xlsx_import_and_export_roundtrip(tmp_path):
    def source(path,value):
        w=xlsxwriter.Workbook(str(path));s=w.add_worksheet("CPT Analysis")
        s.write_row(0,0,["SI.No","CPT REFERENCE","Silt start depth after (m)","silt depth (m)","Sand layer thickness before silt (m)"])
        s.write_row(1,0,[1,"CPT-A1-B1-100",6.0,value,6.0]);w.close()
    src1=tmp_path/"pre.xlsx";src2=tmp_path/"post.xlsx"
    source(src1,.3);source(src2,.2)
    pre=read_summary_xlsx(src1);post=read_summary_xlsx(src2)
    result=compare_summaries(pre,post)
    assert len(result["matched"])==1
    assert abs(result["matched"][0]["metrics"]["silt_thickness_m"]["delta"]+.1)<1e-8
    out=export_comparison(result,tmp_path/"comparison.xlsx")
    assert out.is_file() and out.stat().st_size>3000


def test_map_and_layer_profile_can_export(tmp_path):
    depth=np.arange(0,1.01,.01)
    ic=np.where(depth>.6,2.8,1.7).astype(float)
    a=SimpleNamespace(reference="CPT-A1-B1-100",metadata={"easting":421000,"northing":2928000},
        depth=depth,ic=ic,valid_sensor=np.ones(len(depth),dtype=bool),
        status="VERIFIED",test_depth_raw=1.0)
    assert coordinate_rows([a])[0][0]=="CPT-A1-B1-100"
    assert render_site_map([a],tmp_path/"map.png").stat().st_size>5000
    assert render_layer_profile(a,tmp_path/"profile.png").stat().st_size>5000


def test_ambiguous_duplicate_reference_preserved_not_silently_merged():
    from engineering_comparison import SummaryPoint, compare_summaries
    a=SummaryPoint("CPT-A1-B55-100","RAFT",421000,2928000,
                   {"settlement_mm":65.0},"Raft Summary")
    b=SummaryPoint("CPT-A1-B55-100","RAFT",421000.05,2928000.01,
                   {"settlement_mm":115.0},"Raft Summary")
    post=SummaryPoint("CPT-A1-B55-100","RAFT",421000.02,2928000.00,
                      {"settlement_mm":80.0},"Raft Summary")
    result=compare_summaries([a,b],[post])
    assert not result["matched"]
    assert len(result["ambiguous"])==2

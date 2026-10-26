"""Ensure every physical GEF/GFF sounding survives into independent outputs.

Do not modify cpt_core/engineering_layers numerical calculations, including
when TESTID and surveyed XY are repeated. The project-level output reference
is allowed a source label, preserving original TESTID in metadata.
"""
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import numpy as np

from app_pdf_enabled import retain_physical_cpt_results
from cpt_core import analyze_gef
from engineering_geo_explorer import spatial_points
from reporting_export_v2 import export_excel
from test_modern_app import write_gef


def test_same_cpt_two_raw_gefs_stay_as_two_independent_results(tmp_path):
    first=tmp_path/"P261074_CPT-A2-B254-100.GEF"
    second=tmp_path/"P261074_CPT-A2-B254-100-1.GEF"
    write_gef(first,"CPT-A2-B254-100")
    write_gef(second,"CPT-A2-B254-100")
    # Physically distinct qc/fs readings despite identical TESTID and XY.
    modified=second.read_text().replace("0.500000 0.150000","0.900000 0.130000")
    second.write_text(modified)
    a,b=analyze_gef(first),analyze_gef(second)
    original=[(x.status,x.depth.copy(),x.qc.copy(),x.fs.copy(),
               x.ic.copy(),x.final_interval) for x in (a,b)]
    results,audit=retain_physical_cpt_results([a,b],[first,second])
    assert len(results)==2 and len(audit)==2
    assert all(row["selected"]=="YES" for row in audit)
    assert len({a.reference for a in results})==2
    assert [x.metadata["same_point_file_index"] for x in results]==[1,2]
    assert all(x.metadata["same_point_file_count"]==2 for x in results)
    assert all(x.metadata["canonical_reference"]=="CPT-A2-B254-100" for x in results)
    assert all("SAME CPT POINT" in x.metadata["same_point_note"] for x in results)
    assert all(x.source_path in (first,second) for x in results)
    for x,(status,depth,qc,fs,ic,interval) in zip(results,original):
        assert x.status==status
        np.testing.assert_array_equal(x.depth,depth)
        np.testing.assert_array_equal(x.qc,qc)
        np.testing.assert_array_equal(x.fs,fs)
        np.testing.assert_allclose(x.ic,ic,equal_nan=True)
        assert x.final_interval==interval
    pts,_=spatial_points(results)
    assert len(pts)==2
    assert all(p.status=="REVIEW" for p in pts)  # map-only conservatism
    assert all(x.status==original[i][0] for i,x in enumerate(results))


def test_duplicate_records_are_in_xlsx_and_source_register(tmp_path):
    p=tmp_path/"P261074_CPT-A2-B254-100.GEF"
    q=tmp_path/"P261074_CPT-A2-B254-100-1.GEF"
    for path in (p,q):write_gef(path,"CPT-A2-B254-100")
    data,audit=retain_physical_cpt_results(
        [analyze_gef(p),analyze_gef(q)],[p,q])
    outfile=export_excel(data,tmp_path/"same_point.xlsx",source_audit=audit)
    with ZipFile(outfile) as z:
        names=z.read("xl/workbook.xml")
        assert b"Repeated CPT Files" in names
        assert b"CPT Analysis" in names
        shared=z.read("xl/sharedStrings.xml")
        assert b"FILE 1 OF 2" in shared and b"FILE 2 OF 2" in shared
        assert b"SAME CPT POINT" in shared
        assert b"NOT a continuous sand" in shared
        assert p.name.encode() in shared and q.name.encode() in shared
        sheets=b"".join(z.read(n) for n in z.namelist()
                        if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        assert b"FILE 1 OF 2" in shared+sheets
        assert b"FILE 2 OF 2" in shared+sheets


def test_raw_gef_and_matched_pdf_are_not_double_counted_as_two_soundings(tmp_path):
    p=tmp_path/"P261074_CPT-A2-B254-100.GEF"
    write_gef(p,"CPT-A2-B254-100")
    a=analyze_gef(p)
    pdf_path=tmp_path/"CPT-A2-B254-100.pdf"
    pdf_path.write_bytes(b"placeholder test only")
    pdf=SimpleNamespace(source_path=pdf_path,reference="CPT-A2-B254-100",
                        status="VERIFIED",final_interval=None,
                        metadata={"easting":421000,"northing":2928000},
                        verification_note="Official PDF visual evidence")
    results,audit=retain_physical_cpt_results([a,pdf],[p,pdf_path])
    assert len(results)==1 and results[0].source_path==p
    assert next(x for x in audit if x["source_file"]==p.name)["selected"]=="YES"
    assert next(x for x in audit if x["source_file"]==pdf_path.name)["selected"]=="NO"


def test_pdf_only_source_revisions_are_both_preserved():
    pdf1=SimpleNamespace(source_path=Path("CPT-A2-B254-100.pdf"),
        reference="CPT-A2-B254-100",status="REVIEW",
        final_interval=None,metadata={},verification_note="source 1")
    pdf2=SimpleNamespace(source_path=Path("CPT-A2-B254-100-1.pdf"),
        reference="CPT-A2-B254-100",status="REVIEW",
        final_interval=None,metadata={},verification_note="source 2")
    results,audit=retain_physical_cpt_results([pdf2,pdf1])
    assert len(results)==2 and len(audit)==2
    assert all(x["selected"]=="YES" for x in audit)
    assert [x.source_path.name for x in results]==[
        "CPT-A2-B254-100.pdf","CPT-A2-B254-100-1.pdf"]
    assert results[0].reference.endswith("(FILE 1 OF 2)")
    assert results[1].reference.endswith("(FILE 2 OF 2)")


def test_short_aborted_soundings_are_still_preserved(tmp_path):
    p=tmp_path/"P261074_CPT-A2-B253-100.GEF"
    q=tmp_path/"P261074_CPT-A2-B253-100-1.GEF"
    write_gef(p,"CPT-A2-B253-100")
    write_gef(q,"CPT-A2-B253-100")
    first=analyze_gef(p);second=analyze_gef(q)
    first.depth=first.depth[:3]  # shortened source for retention policy only
    original_statuses=[first.status,second.status]
    results,audit=retain_physical_cpt_results([first,second],[p,q])
    assert len(results)==2
    assert [x.status for x in results]==original_statuses
    assert len([row for row in audit if row["selected"]=="YES"])==2

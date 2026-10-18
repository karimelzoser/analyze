from engineering_comparison import SummaryPoint
from engineering_foundations import check_foundation_results,export_foundation_validation
import zipfile
import pytest


def _record(ref,settlement,fos,sc="Pass",fc="Pass"):
    return SummaryPoint(ref,"RAFT",421092.37,2928336.25,
        {"settlement_mm":settlement,"fos":fos},"Raft Summary",
        reported_settlement_check=sc,reported_fos_check=fc,
        footing_width_m=50,footing_lb_ratio=1.2)


def test_explicit_engineer_limits_and_disagreement_detection(tmp_path):
    rows=[_record("CPT-A1-B292-100",71.54,2.43)]
    good=check_foundation_results(rows,allowable_settlement_mm=100.,minimum_fos=2.)
    assert good[0].settlement_result=="PASS"
    assert good[0].fos_result=="PASS"
    assert not good[0].discrepancy
    bad=check_foundation_results(rows,allowable_settlement_mm=50.,minimum_fos=2.5)
    assert bad[0].settlement_result=="FAIL"
    assert bad[0].fos_result=="FAIL"
    assert len(bad[0].discrepancy)==2
    out=export_foundation_validation(bad,tmp_path/"criteria.xlsx")
    with zipfile.ZipFile(out) as z:
        assert b"Foundation Criteria QA" in z.read("xl/workbook.xml")


def test_no_assumed_acceptance_or_invented_design_pass():
    p=_record("CPT-A1-B292-100",71.54,2.43)
    outcome=check_foundation_results([p],allowable_settlement_mm=None,minimum_fos=None)[0]
    assert outcome.settlement_result=="NOT ASSESSED"
    assert outcome.fos_result=="NOT ASSESSED"
    with pytest.raises(ValueError):
        check_foundation_results([p],allowable_settlement_mm=-1,minimum_fos=None)

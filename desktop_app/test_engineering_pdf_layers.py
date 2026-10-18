from types import SimpleNamespace
from pathlib import Path
import numpy as np
from engineering_report_layers import full_layer_pages
from engineering_pdf_summary import engineering_analysis_page


def _analysis(note=""):
    depth=np.arange(0,1.01,.01)
    ic=np.where((depth>=.6)&(depth<.8),2.83,1.71)
    ic[depth>=.9]=np.nan
    valid=np.isfinite(ic)
    return SimpleNamespace(reference="CPT-A1-LAYER-100",source_path=Path("synthetic.GEF"),
         depth=depth,ic=ic,valid_sensor=valid,status="REVIEW",
         final_interval=None,test_depth_raw=1.0,
         sensor_dropout_depth=.90,pass1=None,pass2=None,metadata={
             "project_id":"REFERENCE PROJECT","easting":421092.37,
             "northing":2928336.25,"ground_elevation":3.46},
         verification_note=note or "Sensor dropout leaves unknown terminal depth.")


def test_full_layer_pdf_has_table_depth_log_and_ic_curve_without_oversize_rows():
    figs=full_layer_pages(_analysis())
    assert figs
    fig=figs[0]
    assert len(fig.axes)>=3  # table, vertical SBT strip, Ic trace
    profile_ax=fig.axes[-1]
    assert any(abs(line.get_xdata()[0]-2.6)<1e-9 for line in profile_ax.lines
               if len(line.get_xdata())>0)


def test_long_verification_notes_cannot_overlap_pdf_methodology_title():
    report=engineering_analysis_page(_analysis("Long engineering evidence. "*150))
    labels=[(x.get_text(),x.get_position()[1]) for x in report.texts]
    heading=next(y for txt,y in labels if txt=="Engineering basis")
    assert heading<.075
    note_lines=[y for txt,y in labels if "Long engineering evidence" in txt]
    assert note_lines and min(note_lines)>.09
    assert any("unabridged" in txt for txt,y in labels)

"""Single map-mode dispatcher shared by the embedded and full-screen review maps.

No silent substitution of a risk/thickness scatter for a selected categorical
soil-zone map. All soil polygons are bounded indicative interpretations.
"""
from __future__ import annotations

from engineering_geo_explorer import risk_plan, depth_window_plan
from engineering_soil_maps import soil_depth_plan


def render_fullscreen_map(fig, data, mode, *, slice_top_m=4.0,
                          slice_bottom_m=5.0, boundary=None,
                          watch_m=.10, high_m=.30,
                          interpretive_fill=True):
    top=float(slice_top_m);bottom=float(slice_bottom_m)
    if mode in ("Soil-behaviour color map","Depth slice plan") and not (0<=top<bottom):
        raise ValueError("Soil depth window must have 0 <= top < bottom")
    if mode=="Soil-behaviour color map":
        return soil_depth_plan(
            fig,data,depth_m=(top+bottom)/2,
            boundary=boundary,fill_interpretation=bool(interpretive_fill))
    settings={"boundary":boundary,"warning_m":float(watch_m),
              "high_m":float(high_m),"show_interpretive_surface":bool(interpretive_fill)}
    if mode=="Depth slice plan":
        return depth_window_plan(fig,data,top_m=top,bottom_m=bottom,**settings)
    if mode in ("Risk screening plan","2D measured plan"):
        return risk_plan(fig,data,**settings)
    raise ValueError("Choose a supported 2D soil map mode")

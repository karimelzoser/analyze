"""Depth-selectable CPT soil-behaviour map.

Measured SBT at each CPT is shown exactly as sampled. A categorical
nearest-vertex color region is only drawn inside short, well supported
triangles and, when supplied, the surveyed boundary. It is an *indicative
spatial interpretation*, never observed soil between soundings.
"""
from __future__ import annotations

import math
import numpy as np
from matplotlib.figure import Figure
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch

# Colors are intentionally geological/soil-map rather than risk-score colors.
SOIL_CLASSES = ("Sand-like", "Sand/silt transitional", "Silt-mixture-like",
                "Clay/organic-like")
SOIL_COLORS = ("#efcf79", "#e89f56", "#77b7b8", "#a491ca")


def _category_for_ic(value):
    return 0 if value < 2.05 else 1 if value < 2.60 else 2 if value < 2.95 else 3


def _category_for_zone(zone):
    # Source XLSB field 'Ic' is categorical SBT ZONE; not continuous Ic.
    mapping={1:3,2:3,3:3,4:2,5:1,6:0,7:0,8:1,9:3}
    return mapping.get(zone)


def observed_soil_at_depth(item, depth_m, *, max_gap_m=.06):
    """Return observed class + provenance, or None for missing coverage."""
    depth_m=float(depth_m)
    if not math.isfinite(depth_m) or depth_m<0:
        raise ValueError("Depth below ground must be finite and nonnegative")
    if isinstance(item,dict):
        layers=item.get("zone_segments") or ()
        for layer in layers:
            try:
                start=float(layer["start"]);end=float(layer["end"]);zone=int(layer["zone"])
            except (TypeError,KeyError,ValueError):continue
            if start-1e-8<=depth_m<end-1e-8:
                kind=_category_for_zone(zone)
                return (kind,"ORIGINAL XLSB CACHED SBT ZONE") if kind is not None else None
        return None
    z=np.asarray(getattr(item,"depth",[]),float)
    v=np.asarray(getattr(item,"ic",[]),float)
    sensor=np.asarray(getattr(item,"valid_sensor",[]),bool)
    if len(z)<2 or len(z)!=len(v) or len(z)!=len(sensor) or depth_m<z[0] or depth_m>z[-1]:
        return None
    k=int(np.searchsorted(z,depth_m,side="right"))-1
    k=max(0,min(k,len(z)-2))
    # Never bridge dropout or even a nominal 10 cm missing measurement run.
    if not (sensor[k] and sensor[k+1] and np.isfinite(v[k]) and np.isfinite(v[k+1])
            and 0<z[k+1]-z[k]<=max_gap_m):
        return None
    fraction=(depth_m-z[k])/(z[k+1]-z[k])
    ic=float(v[k]+fraction*(v[k+1]-v[k]))
    return _category_for_ic(ic),"RAW CPT CALCULATED Ic (not laboratory USCS)"


def soil_at_depth_records(data, depth_m):
    from engineering_maps import filter_coordinate_outliers
    raw=[]
    for item in data:
        md=item if isinstance(item,dict) else getattr(item,"metadata",{}) or {}
        try:
            x=float(md.get("easting"));y=float(md.get("northing"))
        except (TypeError,ValueError):continue
        if not (math.isfinite(x) and math.isfinite(y)):continue
        ref=str(item.get("reference","") if isinstance(item,dict) else item.reference)
        result=observed_soil_at_depth(item,depth_m)
        status=str(item.get("status","") if isinstance(item,dict)
                   else getattr(item,"status",""))
        conflict=bool(md.get("source_revision_conflict") or md.get("source_spatial_conflict")
                      or md.get("source_datum_conflict"))
        raw.append((ref,x,y,{"reference":ref,"x":x,"y":y,
            "category":result[0] if result else None,
            "provenance":result[1] if result else "NO COVERAGE",
            "status":status,"source_conflict":conflict}))
    good,excluded=filter_coordinate_outliers(raw)
    return [item[3] for item in good],[item[3] for item in excluded]


def soil_depth_plan(fig:Figure,data,*,depth_m,boundary=None,
                    max_spacing_m=None,resolution=130,
                    fill_interpretation=True):
    from engineering_geo_explorer import _triangle_mask,_survey_polygon
    from matplotlib.path import Path as PolygonPath
    depth_m=float(depth_m)
    if not math.isfinite(depth_m) or depth_m<0:
        raise ValueError("Choose a nonnegative finite depth BGL")
    if resolution<40 or resolution>400:
        raise ValueError("Resolution must be between 40 and 400")
    points,excluded=soil_at_depth_records(data,depth_m)
    valid=[p for p in points if p["category"] is not None]
    # REVIEW from processing sensitivity is still a MEASURED CLASS at the
    # sounding point, but never use conflicting physical test revisions.
    suitable=[p for p in valid if not p["source_conflict"]]
    fig.clear();ax=fig.add_subplot(111)
    fig.patch.set_facecolor("white")
    polygon=_survey_polygon(boundary)
    if polygon is not None:
        closed=np.vstack((polygon,polygon[0]))
        ax.fill(closed[:,0],closed[:,1],color="#f1f5f9",zorder=0)
        ax.plot(closed[:,0],closed[:,1],color="#36485e",lw=1.65,zorder=5)
    triangles=0
    filled=0
    cmap=ListedColormap(SOIL_COLORS)
    norm=BoundaryNorm(np.arange(-.5,4.5,1),cmap.N)
    if fill_interpretation and len(suitable)>=3:
        coords=np.asarray([(p["x"],p["y"]) for p in suitable],float)
        tri,idx,_=_triangle_mask(coords,max_spacing_m=max_spacing_m,boundary=boundary)
        if tri is not None:
            faces=tri.triangles
            mask=tri.mask if tri.mask is not None else np.zeros(len(faces),dtype=bool)
            triangles=int(np.count_nonzero(~mask))
            if triangles:
                # Fast NumPy rasterisation of categorical nearest-sounding
                # classes *within* locally supported triangulated survey area.
                ux=np.linspace(float(coords[:,0].min()),float(coords[:,0].max()),resolution)
                uy=np.linspace(float(coords[:,1].min()),float(coords[:,1].max()),resolution)
                xx,yy=np.meshgrid(ux,uy)
                grid=np.column_stack((xx.ravel(),yy.ravel()))
                finder=tri.get_trifinder()
                face_idx=np.asarray(finder(grid[:,0],grid[:,1]),dtype=int)
                keep=face_idx>=0
                if polygon is not None:
                    keep&=PolygonPath(polygon).contains_points(grid,radius=1e-6)
                categories=np.full(len(grid),np.nan)
                where=np.flatnonzero(keep)
                if len(where):
                    nearest_vertices=faces[face_idx[where]]
                    original=coords[idx]
                    distances=np.sum((original[nearest_vertices]-grid[where,None,:])**2,axis=2)
                    nearest_local=nearest_vertices[np.arange(len(where)),np.argmin(distances,axis=1)]
                    values=np.asarray([p["category"] for p in suitable],int)[idx]
                    categories[where]=values[nearest_local]
                filled=int(np.isfinite(categories).sum())
                ax.pcolormesh(xx,yy,np.ma.masked_invalid(categories.reshape(xx.shape)),
                              cmap=cmap,norm=norm,shading="auto",alpha=.88,zorder=1,
                              rasterized=True)
    if valid:
        grouped={}
        for kind in range(4):
            subset=[p for p in valid if p["category"]==kind]
            if subset:
                artist=ax.scatter([p["x"] for p in subset],[p["y"] for p in subset],
                    c=[SOIL_COLORS[kind]],s=12,edgecolors="#ffffff",lw=.25,
                    zorder=7,picker=6)
                grouped[artist]=subset
    else:grouped={}
    unknown=[p for p in points if p["category"] is None or p["source_conflict"]]
    if unknown:
        artist=ax.scatter([p["x"] for p in unknown],[p["y"] for p in unknown],
                          marker="x",s=28,color="#718096",zorder=8,picker=6)
        grouped[artist]=unknown
    if not points:
        ax.text(.5,.5,"No CPT locations with surveyed coordinates",transform=ax.transAxes,
                ha="center",va="center",fontsize=11)
    elif not filled:
        ax.text(.02,.015,"Color field unavailable: fewer than 3 nearby classified CPTs / unsupported spans",
                transform=ax.transAxes,ha="left",va="bottom",fontsize=8,
                bbox={"facecolor":"white","alpha":.90,"edgecolor":"none","pad":5})
    legends=[Patch(facecolor=c,label=n) for c,n in zip(SOIL_COLORS,SOIL_CLASSES)]
    legends.append(Patch(facecolor="#b5bec9",label="Unmeasured / conflicting (no interpretation)"))
    ax.legend(handles=legends,loc="best",fontsize=8,framealpha=.93)
    ax.set_xlabel("Project Easting (m)");ax.set_ylabel("Project Northing (m)")
    ax.set_aspect("equal",adjustable="datalim");ax.grid(alpha=.07,zorder=0)
    ax.set_title(f"Soil-behaviour zones at {depth_m:.2f} m BGL | locally supported categorical map",
                 loc="left",fontsize=12,fontweight="bold")
    fig.text(.07,.011,
             f"{len(valid)} observed/cached classifications • {len(unknown)} unknown • "
             f"{len(excluded)} survey outliers • {triangles} supported triangles. "
             "Fill is indicative nearest-observation interpolation, NOT verified soil geology.",
             fontsize=8,color="#56687d")
    fig.tight_layout(rect=(0,.04,1,.97))
    return {"points":points,"outliers":excluded,"classified":len(valid),
            "unknown":len(unknown),"supported_triangles":triangles,
            "filled_cells":filled,"artists":grouped,"depth_m":depth_m}

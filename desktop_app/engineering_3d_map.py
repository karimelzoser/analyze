"""Truthful 3D CPT site visualization: surveyed XY and observed sounding depths.

No invented subsurface interpolation. Each column is one observed CPT, with
individual >=2.60 behavior-screened intervals drawn within the measured depth.
"""
from __future__ import annotations
import math
import numpy as np
from matplotlib.figure import Figure


def _valid_number(value):
    try:
        x=float(value)
        return x if math.isfinite(x) else None
    except (ValueError,TypeError):
        return None


def measured_3d_points(analyses):
    from engineering_maps import filter_coordinate_outliers
    points=[]
    for analysis in analyses:
        if isinstance(analysis,dict):
            e,n,z=[_valid_number(analysis.get(k)) for k in
                    ("easting","northing","ground_elevation")]
            if e is None or n is None or z is None:continue
            intervals=analysis.get("all_intervals") or []
            runs=tuple((float(x.get("start_raw")),float(x.get("end_raw"))) for x in intervals
                       if x.get("start_raw") is not None and x.get("end_raw") is not None)
            last=max((b for a,b in runs),default=0)
            last=max(last,float(analysis.get("test_depth_m") or 0))
            if last<=0:continue
            points.append({"reference":str(analysis.get("reference")),"easting":e,"northing":n,
                "ground":z,"depth":last,"layers":runs,"unknown":0,
                "status":str(analysis.get("status","REFERENCE-CACHED"))})
            continue
        md=getattr(analysis,"metadata",{}) or {}
        e,n,z=[_valid_number(md.get(key)) for key in ("easting","northing","ground_elevation")]
        if e is None or n is None or z is None:continue
        bottom=_valid_number(getattr(analysis,"test_depth_raw",None))
        if bottom is None or bottom<=0:continue
        from engineering_layers import from_analysis
        try:
            layers=from_analysis(analysis).silt_intervals
            unknown=from_analysis(analysis).unknown_m
        except (AttributeError,ValueError,TypeError,IndexError):
            layers=()
            unknown=bottom
        points.append({"reference":str(analysis.reference),"easting":e,"northing":n,
            "ground":z,"depth":bottom,"layers":layers,"unknown":unknown,
            "status":str(analysis.status)})
    coord_rows=[(p["reference"],p["easting"],p["northing"],p) for p in points]
    accepted,excluded=filter_coordinate_outliers(coord_rows)
    return [p[3] for p in accepted],[p[3] for p in excluded]


def site_3d_figure(analyses,site_boundary=None,*,max_labels=12,figure=None):
    analyses=list(analyses)
    points,withheld=measured_3d_points(analyses)
    fig=Figure(figsize=(11.8,8.2),dpi=120,facecolor="#ffffff") if figure is None else figure
    fig.clear()
    ax=fig.add_subplot(111,projection="3d")
    if not points:
        ax.text2D(.24,.50,"No CPTs with confirmed coordinates and ground levels",
                  transform=ax.transAxes,fontsize=13)
        return fig,{"plotted":0,"withheld":len(withheld),"reference_xy":None}
    east0=min(p["easting"] for p in points)
    north0=min(p["northing"] for p in points)
    legend_used=set()
    for p in points:
        x,y=p["easting"]-east0,p["northing"]-north0
        top=p["ground"];base=top-p["depth"]
        ax.plot([x,x],[y,y],[base,top],color="#bdc6d0",lw=.9,alpha=.50,
                label="CPT sounding depth" if "base" not in legend_used else None)
        legend_used.add("base")
        ax.scatter([x],[y],[top],color="#1a6da3",s=9,depthshade=False)
    # Group thousands of segment lines into five vectorized artists for a
    # responsive matplotlib preview. The interactive HTML provides per-CPT
    # hover, depth filters, scene camera and wedge controls.
    from engineering_3d_studio import collect_observed_segments,GROUPS
    segments,_,_ = collect_observed_segments(analyses)
    for category,(label,color) in GROUPS.items():
        coords=[s for s in segments if s["category"]==category]
        if not coords:continue
        xs=[];ys=[];zs=[]
        for seg in coords:
            xs.extend([seg["x"],seg["x"],np.nan])
            ys.extend([seg["y"],seg["y"],np.nan])
            zs.extend([seg["z0"],seg["z1"],np.nan])
        ax.plot(xs,ys,zs,color=color,linewidth=3 if category!="unknown" else 1.9,
                alpha=.9,label=label)
    if site_boundary is not None:
        try:
            poly=np.asarray(site_boundary,dtype=float)
            if len(poly)>=3 and poly.ndim==2 and poly.shape[1]==2 and np.isfinite(poly).all():
                zref=float(np.median([p["ground"] for p in points]))
                outline=np.vstack([poly,poly[:1]])
                ax.plot(outline[:,0]-east0,outline[:,1]-north0,
                    np.full(len(outline),zref),color="#22364c",lw=1.8,
                    label="Survey site boundary")
        except (ValueError,TypeError):
            pass
    # On a large project the 2D/3D spreadsheet preview is a spatial
    # overview. Printing labels for 400 closely spaced vertical columns
    # makes the geology illegible. The offline interactive 3D explorer
    # retains the full CPT reference in hover/click details.
    tops=sorted(points,key=lambda p:max((b-a for a,b in p["layers"]),default=0),reverse=True)
    label_limit=min(max_labels,len(points)) if len(points)<=30 else 0
    for p in tops[:label_limit]:
        ax.text(p["easting"]-east0,p["northing"]-north0,
                p["ground"]+.12,p["reference"],fontsize=6.5)
    ax.set_xlabel(f"Easting offset from {east0:,.1f} m")
    ax.set_ylabel(f"Northing offset from {north0:,.1f} m")
    ax.set_zlabel("Elevation RL (m)")
    ax.view_init(elev=25,azim=-65)
    ax.set_title("3D CPT SBT Layers | Sand · Transition · Silt · Clay · Unknown",loc="left",
                 fontsize=13,fontweight="bold")
    ax.legend(loc="upper left",fontsize=7,frameon=False)
    fig.text(.06,.02,f"{len(points)} surveyed columns | {len(withheld)} coordinate outlier(s) withheld | "
             ("Point labels suppressed for overview; explore exact CPT IDs interactively. "
              if label_limit==0 else "")+
             "SBT is not laboratory USCS.",fontsize=8.5,color="#64748b")
    fig.subplots_adjust(left=.02,right=.97,bottom=.06,top=.91)
    return fig,{"plotted":len(points),"withheld":len(withheld),"reference_xy":(east0,north0)}

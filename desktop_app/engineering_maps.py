"""Offline engineering visualizations based exclusively on measured CPT coordinates.

No basemap, no unapproved coordinate transform, no contour extrapolation.
"""
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
from matplotlib.figure import Figure


def coordinate_rows(analyses, metric="maximum_silt"):
    from engineering_layers import from_analysis
    rows=[]
    for a in analyses:
        e,n=a.metadata.get("easting"),a.metadata.get("northing")
        try:
            e,n=float(e),float(n)
        except (TypeError,ValueError):
            continue
        if not math.isfinite(e) or not math.isfinite(n):
            continue
        if metric == "maximum_silt":
            value=from_analysis(a).maximum_silt_m
        elif metric=="cumulative_silt":
            value=from_analysis(a).cumulative_silt_m
        elif metric=="silt_start":
            st=from_analysis(a).silt_intervals
            value=st[0][0] if st else math.nan
        elif metric=="test_depth":
            value=a.test_depth_raw
        else:
            raise ValueError("Unsupported mapped metric: "+str(metric))
        rows.append((str(a.reference),e,n,float(value),a.status))
    return rows


def render_site_map(analyses, output_path: str | Path, metric="maximum_silt", title=None,
                    site_boundary=None, crs_label="Project grid (CRS not verified)") -> Path:
    """Measured CPT point map, with colorbar, optional supplied polygon and max label.

    Undefined values and REVIEW source data never get a fabricated numeric color.
    """
    p=Path(output_path)
    p.parent.mkdir(parents=True,exist_ok=True)
    rows=coordinate_rows(analyses,metric)
    fig=Figure(figsize=(10.8,7.4),dpi=140,facecolor="#ffffff")
    ax=fig.add_subplot(111)
    if site_boundary is not None:
        poly=np.asarray(site_boundary,dtype=float)
        if poly.ndim!=2 or poly.shape[1]!=2 or len(poly)<3 or not np.isfinite(poly).all():
            raise ValueError("Boundary must contain >=3 finite Easting/Northing pairs")
        closed=np.vstack((poly,poly[0]))
        ax.plot(closed[:,0],closed[:,1],linewidth=1.6,color="#64748b",label="Survey boundary")
    conclusive=[r for r in rows if math.isfinite(r[3]) and r[4]!="REVIEW"]
    uncertain=[r for r in rows if r not in conclusive]
    if conclusive:
        xs=[r[1] for r in conclusive];ys=[r[2] for r in conclusive];val=[r[3] for r in conclusive]
        art=ax.scatter(xs,ys,c=val,cmap="viridis",s=45,edgecolor="white",linewidth=.6,zorder=3)
        cb=fig.colorbar(art,ax=ax,fraction=.035,pad=.02);cb.set_label(metric.replace("_"," ").title()+" (m)")
        top=max(val)
        for ref,e,n,v,_ in conclusive:
            if abs(v-top)<1e-9:
                ax.annotate(ref,(e,n),xytext=(6,8),textcoords="offset points",fontsize=7,
                            color="#111827",fontweight="bold")
    if uncertain:
        ax.scatter([r[1] for r in uncertain],[r[2] for r in uncertain],marker="x",
                   s=42,color="#be123c",label="REVIEW / unavailable")
    if not rows:
        ax.text(.5,.5,"No valid measured CPT coordinate pairs",ha="center",va="center",transform=ax.transAxes)
    ax.set_title(title or ("CPT Project Map — "+metric.replace("_"," ").title()),loc="left",
                 color="#152942",fontweight="bold",fontsize=15)
    ax.set_xlabel("Easting (project coordinate units)")
    ax.set_ylabel("Northing (project coordinate units)")
    ax.set_aspect("equal",adjustable="datalim")
    ax.grid(alpha=.18)
    if uncertain or site_boundary is not None:ax.legend(loc="best",fontsize=8)
    fig.text(.09,.016,crs_label+" | Measured CPT points only — no surface interpolation or inferred values.",
             fontsize=8,color="#64748b")
    fig.subplots_adjust(left=.10,bottom=.12,right=.89,top=.90)
    fig.savefig(p,dpi=160)
    return p


def render_layer_profile(analysis, output_path: str | Path, rolling_window:int=1) -> Path:
    from engineering_layers import from_analysis
    profile=from_analysis(analysis,rolling_window=rolling_window)
    path=Path(output_path);path.parent.mkdir(parents=True,exist_ok=True)
    fig=Figure(figsize=(8,9.5),facecolor="white",dpi=130)
    ax=fig.add_axes([.15,.09,.53,.81])
    depth=np.asarray(analysis.depth,dtype=float)
    ic=np.asarray(analysis.ic,dtype=float)
    good=np.asarray(analysis.valid_sensor,dtype=bool)&np.isfinite(ic)
    ax.plot(np.ma.masked_where(~good,ic),depth,color="#2563eb",linewidth=.9,label="Ic - source")
    ax.axvline(2.60,color="#dc2626",linestyle="--",linewidth=1,label="Project screening 2.60")
    ax.invert_yaxis();ax.set_xlim(0,5);ax.grid(alpha=.15)
    ax.set_xlabel("Soil behavior type index Ic")
    ax.set_ylabel("Corrected depth below ground (m)")
    ax.legend(loc="upper right",fontsize=8)
    strip=fig.add_axes([.72,.09,.15,.81],sharey=ax)
    cmap={"UNKNOWN":"#9ca3af"}
    from matplotlib.patches import Rectangle
    for layer in profile.layers:
        color="#9ca3af" if layer.kind=="UNKNOWN" else "#f2cc65" if layer.mean_ic is not None and layer.mean_ic<2.60 else "#7fa3ba" if layer.mean_ic is not None and layer.mean_ic<3.1 else "#a98ebf"
        strip.add_patch(Rectangle((0,layer.start_m),1,layer.thickness_m,color=color,linewidth=0))
    strip.set_xlim(0,1);strip.set_ylim(ax.get_ylim());strip.set_xticks([])
    strip.set_title("SBT layers",fontsize=9)
    strip.tick_params(axis="y",left=False,labelleft=False)
    fig.suptitle(str(analysis.reference)+" | Observed CPT Layers",x=.12,y=.97,ha="left",
                 fontweight="bold",fontsize=14)
    fig.text(.12,.035,"Silt-like screening is not laboratory USCS. Gray = missing/invalid data.",fontsize=8,color="#475569")
    fig.savefig(path,dpi=160)
    return path

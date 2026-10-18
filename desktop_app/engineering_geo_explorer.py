"""Professional geotechnical spatial explorer.

2D: surveyed plan, all screening-hotspot CPT points, optionally a transparent
linear-in-triangle *interpretive* screening surface bounded by local spacing.
3D: independently observed CPT layers plus cautious interpretive layer wedges
between three neighboring soundings with vertical interval overlap. No volume
outside supported triangles; never confuse screening with design hazard.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import math
import numpy as np
from matplotlib.figure import Figure
from matplotlib.tri import Triangulation


@dataclass(frozen=True)
class SpatialPoint:
    reference: str
    x: float
    y: float
    elevation: float|None
    depth: float|None
    intervals: tuple[tuple[float,float],...]
    maximum_m: float|None
    cumulative_m: float|None
    status: str
    source: str
    recorded_layers: bool


def _num(value):
    try:
        x=float(value)
        return x if math.isfinite(x) else None
    except (ValueError,TypeError):
        return None


def spatial_points(data):
    """Convert numeric CPT analyses or original XLSB cached zone records."""
    from engineering_maps import filter_coordinate_outliers
    prepared=[]
    for item in data:
        if isinstance(item,dict):
            meta=item
            ref=str(item.get("reference",""))
            raw_layers=item.get("all_intervals",[])
            intervals=tuple((float(e["start_raw"]),float(e["end_raw"]))
                             for e in raw_layers
                             if _num(e.get("start_raw")) is not None and
                                _num(e.get("end_raw")) is not None and
                                e["end_raw"]>e["start_raw"])
            maximum=_num(item.get("max_contiguous_silt_screen_m"))
            cumulative=_num(item.get("cumulative_silt_screen_m"))
            depth=_num(item.get("test_depth_m"))
            source="ORIGINAL XLSB CACHED SBT ZONES"
            status=str(item.get("status","REFERENCE-CACHED"))
        else:
            meta=getattr(item,"metadata",{}) or {}
            ref=str(getattr(item,"reference",""))
            status=str(getattr(item,"status","REVIEW"))
            source=str(getattr(item,"source_path","RAW GEF"))
            depth=_num(getattr(item,"test_depth_raw",None))
            intervals=()
            maximum=cumulative=None
            try:
                from engineering_layers import from_analysis
                observed=from_analysis(item)
                intervals=tuple((float(a),float(b)) for a,b in observed.silt_intervals)
                maximum=observed.maximum_silt_m
                cumulative=observed.cumulative_silt_m
            except (ValueError,AttributeError,TypeError,IndexError,KeyError):
                pass
        x=_num(meta.get("easting"));y=_num(meta.get("northing"))
        elev=_num(meta.get("ground_elevation"))
        if x is None or y is None:continue
        # A REVIEW is not a verified no-silt observation; preserve any measured
        # preliminary data but disallow its use in the interpolated surface.
        record=SpatialPoint(ref,x,y,elev,depth,intervals,maximum,cumulative,
                            status,source,bool(intervals))
        prepared.append((ref,x,y,record))
    accepted,discarded=filter_coordinate_outliers(prepared)
    return [row[3] for row in accepted],[row[3] for row in discarded]


def _survey_polygon(boundary):
    if boundary is None:return None
    p=np.asarray(boundary,dtype=float)
    if p.ndim!=2 or p.shape[1]!=2 or len(p)<3 or not np.isfinite(p).all():
        raise ValueError("Site limits must contain at least three finite Easting/Northing coordinates")
    return p


def _triangle_mask(xy, *, max_spacing_m=None, boundary=None):
    """Mask any cross-site bridge across a sparse gap or a site-limit void."""
    from matplotlib.path import Path as PolygonPath
    xy=np.asarray(xy,dtype=float)
    if len(xy)<3:return None,None,None
    # Duplicated spatial points make the triangulation undefined. Site aliases
    # remain visible as distinct markers, but only one of each XY is modeled.
    uniq, indices=np.unique(np.round(xy,5),axis=0,return_index=True)
    indices=np.sort(indices)
    if len(indices)<3:return None,None,None
    xy=xy[indices]
    try:tri=Triangulation(xy[:,0],xy[:,1])
    except (RuntimeError,ValueError):return None,None,None
    faces=tri.triangles
    edge_lengths=np.stack([
        np.linalg.norm(xy[faces[:,0]]-xy[faces[:,1]],axis=1),
        np.linalg.norm(xy[faces[:,1]]-xy[faces[:,2]],axis=1),
        np.linalg.norm(xy[faces[:,2]]-xy[faces[:,0]],axis=1)],axis=1)
    # Automatic local spacing: median of nearest-neighbor distances, then
    # reject spans across unsampled gaps. This is NOT a geology acceptance.
    nearest=[]
    for i in range(len(xy)):
        d=np.linalg.norm(xy-xy[i],axis=1)
        d=d[d>1e-7]
        if len(d):nearest.append(float(np.min(d)))
    if not nearest:return None,None,None
    maxdist=float(max_spacing_m) if max_spacing_m is not None else 2.6*float(np.median(nearest))
    if maxdist<=0:raise ValueError("max spacing must be positive")
    mask=np.max(edge_lengths,axis=1)>maxdist
    polygon=_survey_polygon(boundary)
    if polygon is not None:
        path=PolygonPath(polygon)
        # Check triangle centroid and edge midpoints to reduce drawing across
        # concave boundary indentations.
        centroids=np.mean(xy[faces],axis=1)
        mask|=~path.contains_points(centroids,radius=1e-7)
        for a,b in ((0,1),(1,2),(2,0)):
            mid=(xy[faces[:,a]]+xy[faces[:,b]])*.5
            mask|=~path.contains_points(mid,radius=1e-7)
    tri.set_mask(mask)
    return tri,indices,maxdist


def _kind(point,warning_m,high_m):
    if point.maximum_m is None or point.status=="REVIEW":
        return "REVIEW"
    if point.maximum_m>=high_m-1e-10:return "HIGH"
    if point.maximum_m>=warning_m-1e-10:return "WATCH"
    return "LOW"


def risk_plan(fig:Figure, data, *,boundary=None,warning_m=.10,high_m=.30,
              show_interpretive_surface=True,max_spacing_m=None):
    """Draw 2D plan into the supplied Figure; returns picked artists and all highs.

    Red/amber = soil-screening priority, not 'unsafe foundation' decisions.
    """
    if warning_m<0 or high_m<=warning_m:
        raise ValueError("High thickness limit must exceed nonnegative watch limit")
    points,excluded=spatial_points(data)
    fig.clear();ax=fig.add_subplot(111)
    artists={}
    if boundary is not None:
        p=_survey_polygon(boundary)
        closed=np.vstack([p,p[0]])
        ax.fill(closed[:,0],closed[:,1],color="#e6f0f3",alpha=.6,zorder=0)
        ax.plot(closed[:,0],closed[:,1],color="#33516b",lw=1.8,label="Site boundary")
    valid=[p for p in points if p.maximum_m is not None and p.status!="REVIEW"]
    # CONSTRAINED sparse-data interpolation only, all points remain on top.
    ntri=0
    if show_interpretive_surface and len(valid)>=3:
        xy=np.array([(p.x,p.y) for p in valid])
        tri,idx,spacing=_triangle_mask(xy,max_spacing_m=max_spacing_m,boundary=boundary)
        if tri is not None and np.any(~tri.mask):
            z=np.array([p.maximum_m for p in valid])[idx]
            try:
                contour=ax.tricontourf(tri,z,levels=np.linspace(0,max(float(max(z))*1.03,high_m,.05),13),
                             cmap="YlOrRd",alpha=.33,zorder=1)
                fig.colorbar(contour,ax=ax,fraction=.035,pad=.02,label="Interpreted thickness (m)")
                ntri=int(np.count_nonzero(~tri.mask))
            except (ValueError,RuntimeError):
                pass
    colors={"HIGH":"#c73838","WATCH":"#e39820","LOW":"#298c68","REVIEW":"#8b93a3"}
    classes=[(_kind(p,warning_m,high_m),p) for p in points]
    for kind in ("LOW","WATCH","HIGH","REVIEW"):
        selected=[p for k,p in classes if k==kind]
        if not selected:continue
        artist=ax.scatter([p.x for p in selected],[p.y for p in selected],
                     marker="x" if kind=="REVIEW" else "o",
                     s=65 if kind=="HIGH" else 38,
                     c=colors[kind],edgecolors="#ffffff" if kind!="REVIEW" else None,
                     linewidths=.9,zorder=4 if kind=="HIGH" else 3,
                     label={"LOW":"Below watch threshold","WATCH":"Screening watch",
                     "HIGH":"High screening thickness","REVIEW":"REVIEW / unknown"}[kind],
                     picker=7)
        artists[artist]=selected
    highs=sorted((p for k,p in classes if k=="HIGH"),
                 key=lambda p:(-(p.maximum_m or 0),p.reference))
    # Every high CPT appears in the separate clickable table; no label is
    # silently omitted. Draw all directly only when legible.
    if len(highs)<=30:
        for i,p in enumerate(highs):
            ax.annotate(p.reference,(p.x,p.y),xytext=(5,5+i%3*5),
                        textcoords="offset points",fontsize=7,color="#9e2020",
                        fontweight="bold",zorder=7)
    elif highs:
        ax.text(.01,.015,f"{len(highs)} high-screen CPT points: all listed in the clickable table",
                transform=ax.transAxes,fontsize=8,
                bbox={"facecolor":"white","alpha":.88,"edgecolor":"none","pad":5})
    if not points:
        ax.text(.5,.5,"No valid surveyed CPT coordinates",ha="center",va="center",
                transform=ax.transAxes)
    ax.set_xlabel("Site Easting (m)");ax.set_ylabel("Site Northing (m)")
    ax.set_aspect("equal",adjustable="datalim");ax.grid(alpha=.12)
    ax.set_title("Site soil screening plan | observed CPTs and bounded estimate",
                 fontweight="bold",fontsize=12,loc="left")
    ax.legend(fontsize=8,loc="best")
    fig.text(.055,.012,
        f"Observed points: {len(points)}  •  HIGH: {len(highs)}  •  outliers: {len(excluded)}  •  supported triangles: {ntri}. "
        "Colored fill = inferred only, not design acceptance.",fontsize=8,color="#637083")
    fig.tight_layout(rect=(0,.05,1,.97))
    return {"points":points,"high":highs,"outliers":excluded,"artists":artists,
            "supported_triangles":ntri,"screen_counts":{
                k:sum(1 for kind,_ in classes if kind==k) for k in colors}}


def _vertical_intersections(point):
    """All recorded qualifying intervals as absolute elevation ranges.

    Several separated fine-grained-like layers may exist at one CPT. Do not
    discard them in favor of the longest interval.
    """
    if point.elevation is None:
        return []
    bounds=[]
    for top_depth,base_depth in point.intervals:
        high=point.elevation-float(top_depth)
        low=point.elevation-float(base_depth)
        if math.isfinite(high) and math.isfinite(low) and high>low:
            bounds.append((low,high))
    bounds.sort()
    merged=[]
    for low,high in bounds:
        if merged and low<=merged[-1][1]+1e-9:
            merged[-1]=(merged[-1][0],max(high,merged[-1][1]))
        else:
            merged.append((low,high))
    return merged


def _common_vertical_bands(corners,min_overlap_m):
    """Intersection of all three CPT soil-screen intervals, retaining every band."""
    first=_vertical_intersections(corners[0])
    second=_vertical_intersections(corners[1])
    third=_vertical_intersections(corners[2])
    common=[]
    for a0,a1 in first:
        for b0,b1 in second:
            lower=max(a0,b0);upper=min(a1,b1)
            if upper-lower<min_overlap_m:continue
            for c0,c1 in third:
                lower3=max(lower,c0);upper3=min(upper,c1)
                if upper3-lower3>=min_overlap_m-1e-10:
                    common.append((lower3,upper3))
    return sorted(common)


def interpreted_wedges(points,boundary=None,max_spacing_m=None,min_vertical_overlap_m=.05):
    """Return ALL locally evidenced depth bands as separate 3D prisms.

    A prism is admitted only within a spatially supported CPT triangle AND
    a vertical band classified at all three corner soundings. A band at 2 m
    cannot be connected to another at 6 m. These are uncertain screening
    visualizations, never measured contiguous geological volumes.
    """
    good=[p for p in points if p.elevation is not None and
          p.status!="REVIEW" and _vertical_intersections(p)]
    if len(good)<3:return [],0
    tri,idx,_=_triangle_mask([(p.x,p.y) for p in good],
                          max_spacing_m=max_spacing_m,boundary=boundary)
    if tri is None:return [],0
    aligned=[good[i] for i in idx]
    wedges=[]
    for j,face in enumerate(tri.triangles):
        if tri.mask is not None and tri.mask[j]:continue
        corners=[aligned[int(i)] for i in face]
        for low,high in _common_vertical_bands(corners,min_vertical_overlap_m):
            # Conservative continuous overlap of all 3 observed horizons:
            # flat top/bottom *inside* the data envelope, not guessed contacts.
            wedges.append((corners,[high]*3,[low]*3))
    return wedges,len(good)


def depth_window_records(data,top_m,bottom_m,*,minimum_coverage=.8):
    """Observed screening thickness INSIDE a vertical depth window.

    Invalid/deeper unmeasured portions are REVIEW, not zero. Raw sensor
    validity is checked independently for every window. Original saved
    SBT series use their recorded depth coverage and are marked cached.
    """
    top=float(top_m);bottom=float(bottom_m)
    if not (math.isfinite(top) and math.isfinite(bottom) and 0<=top<bottom):
        raise ValueError("Depth window must have finite bottom > top >= 0")
    if not (0<minimum_coverage<=1):
        raise ValueError("Coverage fraction must be between 0 and 1")
    output=[]
    for item in data:
        if isinstance(item,dict):
            e=item.get("easting");n=item.get("northing")
            meta=item
            intervals=tuple((float(v["start_raw"]),float(v["end_raw"]))
                            for v in item.get("all_intervals",[])
                            if v.get("start_raw") is not None and v.get("end_raw") is not None)
            max_end=_num(item.get("test_depth_m"))
            source_quality=str(item.get("status","REFERENCE-CACHED"))
            cached_depths=item.get("source_classified_depths_m")
            if cached_depths is not None:
                z=np.asarray(cached_depths,dtype=float)
                if len(z)>1 and np.all(np.diff(z)>0):
                    lo=np.maximum(z[:-1],top)
                    hi=np.minimum(z[1:],bottom)
                    eligible=(np.diff(z)<=.025)
                    observed=float(np.maximum(0,hi-lo)[eligible].sum())
                    sufficient=observed>=minimum_coverage*(bottom-top)-1e-8
                else:
                    sufficient=False
            else:
                # External summaries without full classification samples only
                # substantiate a nominal end depth, not guaranteed continuity.
                sufficient=max_end is not None and max_end>=bottom-.02
        else:
            meta=getattr(item,"metadata",{}) or {}
            e=meta.get("easting");n=meta.get("northing")
            source_quality=str(getattr(item,"status","REVIEW"))
            intervals=()
            try:
                from engineering_layers import from_analysis
                intervals=from_analysis(item).silt_intervals
            except (AttributeError,ValueError,TypeError,IndexError):pass
            # One observation at the requested bottom does not imply coverage
            # throughout that interval. Estimate coverage by valid adjacent
            # sample segments; never bridge a missing sensor stretch.
            depth=np.asarray(getattr(item,"depth",[]),float)
            sensor=np.asarray(getattr(item,"valid_sensor",[]),bool)
            ic=np.asarray(getattr(item,"ic",[]),float)
            coverage=0.
            if len(depth)>1 and len(depth)==len(sensor)==len(ic):
                if np.all(np.diff(depth)>0):
                    a=np.maximum(depth[:-1],top)
                    b=np.minimum(depth[1:],bottom)
                    valid=sensor[:-1]&sensor[1:]&np.isfinite(ic[:-1])&np.isfinite(ic[1:])
                    valid&=(np.diff(depth)<=.06)
                    coverage=float(np.maximum(0,b-a)[valid].sum())
            sufficient=coverage>=minimum_coverage*(bottom-top)-1e-8
        if _num(e) is None or _num(n) is None:continue
        observed=max(0.,sum(max(0.,min(b,bottom)-max(a,top)) for a,b in intervals))
        maximum=max((max(0.,min(b,bottom)-max(a,top)) for a,b in intervals),default=0.)
        status="REVIEW" if not sufficient or source_quality.upper().startswith("REVIEW") else source_quality
        output.append({
            "reference":str(item.get("reference","")) if isinstance(item,dict) else str(item.reference),
            "easting":float(e),"northing":float(n),
            "ground_elevation":meta.get("ground_elevation"),
            "test_depth_m":bottom if sufficient else None,
            "status":status,
            "source_window_status":"OBSERVED" if sufficient else "INSUFFICIENT DEPTH/SENSOR COVERAGE",
            "max_contiguous_silt_screen_m":maximum if sufficient else None,
            "cumulative_silt_screen_m":observed if sufficient else None,
            "all_intervals":[{"start_raw":max(a,top),"end_raw":min(b,bottom)}
                             for a,b in intervals if min(b,bottom)>max(a,top)]
        })
    return output


def depth_window_plan(fig,data,*,top_m,bottom_m,boundary=None,warning_m=.10,
                      high_m=.30,show_interpretive_surface=True,max_spacing_m=None):
    """Risk screening PLAN for a user-selected horizontal depth band."""
    rows=depth_window_records(data,top_m,bottom_m)
    result=risk_plan(fig,rows,boundary=boundary,warning_m=warning_m,
                     high_m=high_m,show_interpretive_surface=show_interpretive_surface,
                     max_spacing_m=max_spacing_m)
    ax=fig.axes[0]
    ax.set_title(f"Site depth slice {top_m:.2f}–{bottom_m:.2f} m BGL | observed screening",
                 loc="left",fontweight="bold",fontsize=12)
    result["depth_window"]=(float(top_m),float(bottom_m))
    result["window_records"]=rows
    return result


def fence_section_figure(data,*,bearing="E-W",corridor_m=None):
    """Interactive measured CPT fence section (NO lateral interpolation).

    The fence is a corridor extraction from an actual surveyed plan, not a
    claim that the selected soundings lie exactly on a geological transect.
    All observed qualifying intervals are drawn, including multiple layers.
    """
    import plotly.graph_objects as go
    if bearing not in ("E-W","N-S"):
        raise ValueError("Section bearing must be E-W or N-S")
    points,excluded=spatial_points(data)
    valid=[p for p in points if p.elevation is not None and
           (p.depth is not None or p.intervals)]
    fig=go.Figure()
    if len(valid)<2:
        fig.add_annotation(text="At least two georeferenced CPT profiles are required",
                           showarrow=False)
        return fig,{"points":0,"corridor_m":0,"bearing":bearing}
    perpendicular=np.asarray([p.y if bearing=="E-W" else p.x for p in valid])
    center=float(np.median(perpendicular))
    along=np.asarray([p.x if bearing=="E-W" else p.y for p in valid])
    extent=float(np.ptp(perpendicular))
    width=float(corridor_m) if corridor_m is not None else max(8.,extent*.12)
    if width<=0:raise ValueError("Section corridor width must be positive")
    selected=[p for p in valid if abs(
        (p.y if bearing=="E-W" else p.x)-center)<=width]
    selected.sort(key=lambda p:p.x if bearing=="E-W" else p.y)
    if not selected:
        fig.add_annotation(text="No CPT points within the selected section corridor",
                           showarrow=False)
    elif len(selected)<2:
        fig.add_annotation(text="Only one observed CPT falls inside this corridor",
                           showarrow=False)
    else:
        base=min(p.x if bearing=="E-W" else p.y for p in selected)
        bx=[];by=[];sx=[];sy=[];count=0
        for p in selected:
            station=(p.x if bearing=="E-W" else p.y)-base
            end=p.depth if p.depth is not None else max(b for _,b in p.intervals)
            bx.extend([station,station,None])
            by.extend([p.elevation,p.elevation-end,None])
            for start,finish in p.intervals:
                if finish<=start:continue
                sx.extend([station,station,None])
                sy.extend([p.elevation-start,p.elevation-finish,None])
                count+=1
            if len(selected)<=65:
                fig.add_annotation(x=station,y=p.elevation,showarrow=False,
                                   text=p.reference,textangle=-48,yshift=26,
                                   font={"size":8,"color":"#324b63"})
        fig.add_trace(go.Scatter(x=bx,y=by,mode="lines",
                      line={"color":"#adb8c6","width":2},name="CPT observed sounding",
                      hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=sx,y=sy,mode="lines",
                      line={"color":"#c3483d","width":9},
                      name="Observed Ic-screen interval",hoverinfo="skip"))
        fig.update_layout(hovermode="x unified")
    fig.update_layout(
        title=f"{bearing} CPT fence | surveyed corridor ±{width:.1f} m "
              "(intervals observed at CPTs only)",
        template="plotly_white",height=520,margin={"l":66,"r":20,"t":72,"b":65},
        xaxis_title="Distance along transect (m)",yaxis_title="Elevation RL (m)",
        legend={"orientation":"h","y":-0.22,"x":0.02})
    return fig,{"points":len(selected),"corridor_m":width,"bearing":bearing}


def export_interactive_3d(data,path,*,boundary=None,warning_m=.10,high_m=.30,
                          max_spacing_m=None):
    """Create a standalone fully offline 3D geotechnical explorer HTML.

    Bundles Plotly JS locally in the HTML. No browser server/network needed.
    Camera, layer toggles, hover details, clipping via legend and zoom work.
    """
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
    except ImportError as e:
        raise RuntimeError("The offline 3D visualizer requires plotly; please reinstall the Windows package.") from e
    points,excluded=spatial_points(data)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fig=go.Figure()
    if not points:
        fig.add_annotation(text="No surveyed CPT locations and ground levels",showarrow=False)
    valid=[p for p in points if p.elevation is not None and p.depth is not None]
    if not valid:
        # Reference XLSB profiles may lack recorded sounding termination; use
        # observed interval end as conservative minimum visible depth.
        valid=[p for p in points if p.elevation is not None and p.intervals]
    east0=min((p.x for p in points),default=0.0)
    north0=min((p.y for p in points),default=0.0)
    def tool(p):
        layers="; ".join(f"{a:.2f}-{b:.2f}m" for a,b in p.intervals) or "None observed"
        value=f"{p.maximum_m:.2f} m" if p.maximum_m is not None else "Unavailable"
        return (f"<b>{p.reference}</b><br>Easting {p.x:.3f} / Northing {p.y:.3f}<br>"
                f"Max SBT-screen {value}<br>Intervals {layers}<br>Status {p.status}<br>"
                f"Source {p.source}<extra></extra>")
    for category,color in (("Below watch","#389873"),("Watch","#e5a13e"),
                           ("High","#d54f48"),("Unresolved","#9399a9")):
        subset=[p for p in points if (
            ("Unresolved" if p.maximum_m is None or p.status=="REVIEW" else
             "High" if p.maximum_m>=high_m else "Watch" if p.maximum_m>=warning_m
             else "Below watch"))==category]
        if not subset:continue
        fig.add_trace(go.Scatter3d(x=[p.x-east0 for p in subset],y=[p.y-north0 for p in subset],
             z=[p.elevation if p.elevation is not None else 0 for p in subset],
             mode="markers",name=f"CPT points · {category}",legendgroup="survey",
             marker={"size":3.8,"color":color,"line":{"color":"white","width":.6}},
             hovertemplate=[tool(p) for p in subset]))
    # Crisp dark stem lines and full-depth measured/cached silt intervals.
    stems_x=[];stems_y=[];stems_z=[]
    silt_x=[];silt_y=[];silt_z=[]
    for p in valid:
        top=p.elevation
        depth=p.depth if p.depth is not None else max(b for a,b in p.intervals)
        stems_x.extend([p.x-east0,p.x-east0,None]);stems_y.extend([p.y-north0,p.y-north0,None])
        stems_z.extend([top,top-depth,None])
        for start,end in p.intervals:
            silt_x.extend([p.x-east0,p.x-east0,None])
            silt_y.extend([p.y-north0,p.y-north0,None])
            silt_z.extend([top-end,top-start,None])
    if stems_x:
        fig.add_trace(go.Scatter3d(x=stems_x,y=stems_y,z=stems_z,mode="lines",
                 name="Measured sounding depth",line={"color":"#8f9eab","width":2},
                 hoverinfo="skip",legendgroup="survey"))
    if silt_x:
        fig.add_trace(go.Scatter3d(x=silt_x,y=silt_y,z=silt_z,mode="lines",
                name="Observed SBT-screen layers",line={"color":"#c3423b","width":7},
                hoverinfo="skip",legendgroup="screen"))
    wedges,eligible=interpreted_wedges(points,boundary,max_spacing_m=max_spacing_m)
    if wedges:
        vx=[];vy=[];vz=[];ii=[];jj=[];kk=[]
        faces=((0,1,2),(3,5,4),(0,3,4),(0,4,1),
               (1,4,5),(1,5,2),(2,5,3),(2,3,0))
        for corners,tops,bottoms in wedges:
            base=len(vx)
            for pos,z in list(zip(corners,tops))+list(zip(corners,bottoms)):
                vx.append(pos.x-east0);vy.append(pos.y-north0);vz.append(z)
            for a,b,c in faces:
                ii.append(base+a);jj.append(base+b);kk.append(base+c)
        fig.add_trace(go.Mesh3d(x=vx,y=vy,z=vz,i=ii,j=jj,k=kk,
              color="#cf554b",opacity=.23,flatshading=True,
              name="Interpreted silt-like wedge (uncertain)",
              legendgroup="inferred",hovertemplate="Interpreted 3-CPT overlap, not a measured geology volume<extra></extra>",
              showlegend=True))
    poly=_survey_polygon(boundary) if boundary is not None else None
    if poly is not None:
        zbase=float(np.median([p.elevation for p in valid])) if valid else 0
        closed=np.vstack([poly,poly[:1]])
        fig.add_trace(go.Scatter3d(x=closed[:,0]-east0,y=closed[:,1]-north0,
            z=np.full(len(closed),zbase),mode="lines",name="Site survey boundary",
            line={"color":"#2c465e","width":5},hoverinfo="skip"))
    fig.update_layout(
        title={"text":"CPT Subsurface Explorer · observed columns + evidence-bounded interpreted layers","x":.04},
        template="plotly_white",height=820,
        margin={"l":12,"r":12,"t":68,"b":48},
        legend={"orientation":"h","y":-.07,"x":.02},
        scene={"xaxis_title":f"Easting offset from {east0:.2f} m",
               "yaxis_title":f"Northing offset from {north0:.2f} m",
               "zaxis_title":"Elevation RL (m)","aspectmode":"data",
               "camera":{"eye":{"x":1.65,"y":-1.65,"z":1.18}}},
        updatemenus=[{"type":"buttons","x":.02,"y":1.06,"direction":"right",
                      "buttons":[
                        {"label":"Normal scale","method":"relayout",
                          "args":[{"scene.aspectmode":"data"}]},
                        {"label":"Vertical emphasis","method":"relayout",
                          "args":[{"scene.aspectmode":"manual",
                                   "scene.aspectratio":{"x":1.35,"y":1.25,"z":.65}}]},
                        {"label":"Top / plan","method":"relayout",
                         "args":[{"scene.camera.eye":{"x":0.01,"y":0.01,"z":2.3}}]},
                        {"label":"Isometric","method":"relayout",
                         "args":[{"scene.camera.eye":{"x":1.65,"y":-1.65,"z":1.18}}]},
                      ]}])
    header=(
      f"<div style='font:14px Segoe UI,sans-serif;background:#e8f0f8;color:#18314a;"
      f"padding:12px 20px;border-bottom:1px solid #c6d5e2'>"
      f"<b>{len(points)} surveyed CPT locations</b> &nbsp;·&nbsp; "
      f"<b>{len(wedges)} supported 3-point overlap wedges</b> &nbsp;·&nbsp; "
      f"<b>{len(excluded)} coordinate outliers withheld</b><br>"
      f"<span style='font-size:12px'>Transparent solids show <b>interpreted screening continuity only where"
      f" three neighboring observed intervals overlap.</b> Not certified stratigraphy or foundation risk."
      f" Click a legend label to hide layers. Rotate, pan and scroll to zoom.</span></div>")
    html=pio.to_html(fig,include_plotlyjs=True,full_html=True,
                     config={"responsive":True,"scrollZoom":True,"displaylogo":False,
                             "modeBarButtonsToAdd":["resetCameraDefault3d"]})
    html=html.replace("<body>","<body style='margin:0;background:#f9fbfd'>"+header,1)
    # Two independent E-W / N-S observed cross-sections make the 3D volume
    # interpretable. Each section shows all measured depth bands; never
    # implies that strata continue between separate CPTs.
    sections=[]
    for bearing in ("E-W","N-S"):
        fence,summary=fence_section_figure(data,bearing=bearing)
        sections.append(summary)
        section_html=pio.to_html(fence,include_plotlyjs=False,full_html=False,
            config={"responsive":True,"scrollZoom":True,"displaylogo":False})
        panel=("<section style='margin:18px 18px 28px;background:white;"
               "border:1px solid #cbd5e1;border-radius:12px'>"
               +section_html+"</section>")
        html=html.replace("</body>",panel+"</body>",1)
    path.write_text(html,encoding="utf-8")
    return {"file":path,"points":len(points),"wedges":len(wedges),
            "withheld":len(excluded),"fence_sections":sections}

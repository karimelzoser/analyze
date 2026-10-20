"""CPT-derived ISOLATED footing settlement screening, fully traceable.

Engineering basis: vertical strain integration with a simplified 2:1 stress
distribution under an isolated rectangular footing:

    delta_sigma(z) = q_net * B*L / ((B+z)*(L+z))
    M(z) = alpha_M * qt(z) * 1000 [kPa]     [empirical, MUST BE CALIBRATED]
    s_observed = integral(delta_sigma/M dz) * 1000 [mm]

z is depth below footing base. Measurements are never extrapolated into
unsounded depth. An incomplete depth profile CANNOT claim final settlement.
This simplified screening is NOT an independently validated Schmertmann or
original XLSB/isolated-footing design calculation.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional
import math
import numpy as np


@dataclass(frozen=True)
class IsolatedInputs:
    width_m: float = 3.0
    length_m: float = 3.0
    net_pressure_kpa: float = 150.0
    embedment_m: float = 1.0
    influence_b: float = 1.5
    qc_modulus_factor: float = 5.0
    max_sample_gap_m: float = 0.08
    step_m: float = 0.02
    min_coverage: float = 0.90
    allowable_settlement_mm: Optional[float] = None

    def validate(self):
        for name in ("width_m","length_m","net_pressure_kpa","influence_b",
                     "qc_modulus_factor","max_sample_gap_m","step_m"):
            x=float(getattr(self,name))
            if not math.isfinite(x) or x<=0:
                raise ValueError(name+" must be finite and positive")
        if not 0<=self.embedment_m<40:
            raise ValueError("Invalid footing embedment")
        if not .50<=self.min_coverage<=1.0:
            raise ValueError("min_coverage must be between 0.5 and 1")
        if self.step_m>self.max_sample_gap_m:
            raise ValueError("Integration step cannot exceed maximum sampling gap")
        if (self.allowable_settlement_mm is not None and
            (not math.isfinite(self.allowable_settlement_mm) or self.allowable_settlement_mm<=0)):
            raise ValueError("Allowable settlement must be positive")


@dataclass
class IsolatedResult:
    reference: str
    status: str
    source: str
    observed_settlement_mm: Optional[float]
    calculated_settlement_mm: Optional[float]
    coverage_percent: float
    influence_start_bgl_m: float
    influence_end_bgl_m: float
    last_valid_depth_m: Optional[float]
    source_settlement_mm: Optional[float]
    source_delta_mm: Optional[float]
    criterion_status: str
    warning: str
    inputs: dict
    integration: list[dict]


def _value(obj,name,default=None):
    return obj.get(name,default) if isinstance(obj,dict) else getattr(obj,name,default)


def _finite(value):
    try:
        x=float(value)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):return None


def derive_isolated_settlement(analysis, inputs:IsolatedInputs,
                              *, source_settlement_mm=None):
    inputs.validate()
    ref=str(_value(analysis,"reference","UNKNOWN"))
    source=str(_value(analysis,"source_path","RAW GEF/GFF"))
    depth=np.asarray(_value(analysis,"depth",[]),dtype=float)
    qt=np.asarray(_value(analysis,"qt",[]),dtype=float)
    z0=inputs.embedment_m
    z1=z0+inputs.width_m*inputs.influence_b
    usedsource=_finite(source_settlement_mm)

    def result(status,partial=None,coverage=0.,last=None,rows=None,warning=""):
        complete=partial if status=="ESTIMATE — COVERAGE SUFFICIENT" else None
        delta=(complete-usedsource if complete is not None and usedsource is not None else None)
        # No independent settlement PASS/FAIL until the correlation is approved.
        # Even complete observed coverage establishes only a provisional estimate.
        return IsolatedResult(
            ref,status,source,partial,complete,round(coverage*100,2),
            z0,z1,last,usedsource,delta,"NOT ASSESSED — MODEL NOT APPROVED",
            warning,asdict(inputs),rows or [])

    if len(depth)<2 or len(qt)!=len(depth):
        return result("NOT CALCULABLE — RAW PROFILE UNAVAILABLE",warning=
                      "No compatible numerical qc/qt profile provided. Source summary preserved separately.")
    good=np.isfinite(depth)&np.isfinite(qt)&(qt>0)
    if not np.all(np.diff(depth)>0):
        return result("NOT CALCULABLE — DEPTH ORDER",warning=
                      "Corrected sounding depth must be strictly increasing.")
    if not np.any(good):
        return result("NOT CALCULABLE — QT INVALID",warning="No positive finite qt observations.")
    valid_intervals=(good[:-1]&good[1:]&
                     (np.diff(depth)<=inputs.max_sample_gap_m))
    grid=np.arange(z0+inputs.step_m/2.,z1,inputs.step_m)
    if not len(grid):
        return result("NOT CALCULABLE — INFLUENCE WINDOW")
    ii=np.searchsorted(depth,grid,side="right")-1
    ii=np.clip(ii,0,len(depth)-2)
    within=(grid>=depth[0])&(grid<=depth[-1])
    within &= valid_intervals[ii]
    # Piecewise linear interpolation ONLY between 2 valid measured samples.
    left=depth[ii];right=depth[ii+1]
    qvals=np.full(len(grid),np.nan)
    qvals[within]=qt[ii[within]]+(qt[ii[within]+1]-qt[ii[within]])*(
        (grid[within]-left[within])/(right[within]-left[within]))
    within &= np.isfinite(qvals)&(qvals>0)
    depths=grid[within]
    coverage=float(np.sum(within))/len(grid)
    if not len(depths):
        return result("NOT CALCULABLE — NO OBSERVED INFLUENCE DATA",0.,coverage,
                      warning="Footing influence zone does not overlap reliable CPT measurements.")
    dz=inputs.step_m
    base_depth=depths-z0
    sigma=inputs.net_pressure_kpa*inputs.width_m*inputs.length_m/(
        (inputs.width_m+base_depth)*(inputs.length_m+base_depth))
    modulus=inputs.qc_modulus_factor*qvals[within]*1000
    strains=sigma/modulus
    increments=strains*dz*1000
    subtotal=float(np.sum(increments))
    trace=[{"depth_bgl_m":round(float(z),4),"qt_mpa":round(float(q),6),
            "stress_kpa":round(float(stress),5),"modulus_kpa":round(float(M),3),
            "strain":round(float(strain),9),"incremental_settlement_mm":round(float(d),7)}
           for z,q,stress,M,strain,d in zip(depths,qvals[within],sigma,modulus,strains,increments)]
    status="ESTIMATE — COVERAGE SUFFICIENT" if coverage>=inputs.min_coverage else "INCOMPLETE — DEPTH COVERAGE"
    caution=("PROVISIONAL 2:1 strain integration using empirical M=alpha*qt, "
             "evaluated only to %.1fB below footing base; deeper stress influence "
             "has not been calculated. Not source-XLSB-equivalent, no engineer-approved "
             "modulus factor or design PASS. Unsounded data remain UNKNOWN."%
             inputs.influence_b)
    return result(status,subtotal,coverage,float(depths[-1]),trace,caution)


def attach_isolated_estimates(analyses,source_points,inputs:IsolatedInputs,
                             *,max_xy_error_m=2.0):
    """One physical source point at a time; never fabricate matches by filename."""
    rows=[]
    for p in source_points:
        if p.foundation!="ISOLATED":continue
        candidates=[]
        for a in analyses:
            x=_finite((_value(a,"metadata",{}) or {}).get("easting"))
            y=_finite((_value(a,"metadata",{}) or {}).get("northing"))
            if None in (x,y,p.east,p.north):continue
            offset=math.hypot(x-p.east,y-p.north)
            if offset<=max_xy_error_m and str(_value(a,"reference","")).upper()==p.reference.upper():
                candidates.append((offset,a))
        observed=p.metrics.get("settlement_mm")
        if len(candidates)!=1:
            reason=("missing matching raw CPT and coordinates" if not candidates else
                    "ambiguous duplicate test records")
            rows.append(IsolatedResult(p.reference,"NOT CALCULABLE — "+reason.upper(),
                       str(p.source_sheet),None,None,0.,inputs.embedment_m,
                       inputs.embedment_m+inputs.width_m*inputs.influence_b,
                       None,_finite(observed),None,
                       "NOT ASSESSED — MODEL NOT APPROVED",reason,asdict(inputs),[]))
            continue
        a=candidates[0][1]
        rows.append(derive_isolated_settlement(a,inputs,source_settlement_mm=observed))
    return rows

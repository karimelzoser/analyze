"""Observed depth profile and project screening for CPT soil behavior.

A soil-behavior type estimated from Ic is NOT a laboratory USCS classification.
Never extend an observed interval into invalid sensor readings, and never round
a short observed thickness upward to a fictitious measured thickness.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import math
import numpy as np


@dataclass(frozen=True)
class Layer:
    number: int
    kind: str
    start_m: float
    end_m: float
    thickness_m: float
    mean_ic: Optional[float]
    status: str
    silt_screen: bool
    source: str = "OBSERVED"

    def as_dict(self):
        return dict(number=self.number, kind=self.kind, start=self.start_m,
                    end=self.end_m, thickness=self.thickness_m, mean_ic=self.mean_ic,
                    status=self.status, silt_screen=self.silt_screen, source=self.source)


@dataclass(frozen=True)
class Stratigraphy:
    layers: tuple[Layer, ...]
    silt_intervals: tuple[tuple[float, float], ...]
    brief_exceedances: tuple[tuple[float, float], ...]
    rolling_window: int
    threshold: float
    notes: tuple[str, ...]

    @property
    def cumulative_silt_m(self) -> float:
        return float(sum(end-start for start, end in self.silt_intervals))

    @property
    def maximum_silt_m(self) -> float:
        return float(max((end-start for start, end in self.silt_intervals), default=0))

    @property
    def silt_count(self) -> int:
        return len(self.silt_intervals)

    @property
    def unknown_m(self) -> float:
        return float(sum(l.thickness_m for l in self.layers if l.kind == "UNKNOWN"))


def behavior_label(ic: float) -> str:
    """Workbook-reference-inspired Ic categories. All labels are SBT estimates."""
    if not math.isfinite(ic):
        return "UNKNOWN"
    if ic < 1.31:
        return "GRAVELLY SAND-LIKE"
    if ic < 1.59:
        return "CLEAN SAND-LIKE"
    if ic < 1.83:
        return "SAND WITH SILT-LIKE"
    if ic < 2.276:
        return "SILTY SAND-LIKE"
    if ic < 2.50:
        return "SILTY SAND / SANDY SILT-LIKE"
    if ic < 2.60:
        return "SANDY SILT / SILTY SAND-LIKE"
    if ic < 2.68:
        return "SANDY SILT-LIKE"
    if ic < 2.95:
        return "SILT MIXTURE-LIKE"
    if ic < 3.10:
        return "SILTY CLAY-LIKE"
    if ic < 3.60:
        return "CLAY-LIKE"
    return "ORGANIC SOIL-LIKE"


def _smooth_contiguous(values: np.ndarray, valid: np.ndarray, width: int) -> np.ndarray:
    """Centered rolling mean that NEVER bridges a contiguous invalid-data run."""
    if width < 1:
        raise ValueError("Rolling mean window must be >= 1")
    out = np.full(len(values), np.nan)
    indices = np.flatnonzero(valid)
    if not len(indices):
        return out
    groups = np.split(indices, np.flatnonzero(np.diff(indices) > 1)+1)
    before = (width-1)//2
    after = width-1-before
    for group in groups:
        if not len(group):
            continue
        for j, idx in enumerate(group):
            window = group[max(0,j-before):min(len(group),j+after+1)]
            out[idx] = np.mean(values[window])
    return out


def _intervals_from_indicator(z: np.ndarray, v: np.ndarray, valid: np.ndarray,
                              threshold: float, min_thickness: float):
    """Threshold-crossing interpolation; only interpolate between adjacent valid samples."""
    passed = valid & (v >= threshold)
    runs = []
    i = 0
    while i < len(z):
        if not passed[i]:
            i += 1
            continue
        j = i
        while j+1 < len(z) and passed[j+1]:
            j += 1
        start, end = float(z[i]), float(z[j])
        if i > 0 and valid[i-1] and v[i-1] < threshold and v[i] != v[i-1]:
            start = float(z[i-1] + (threshold-v[i-1])*(z[i]-z[i-1])/(v[i]-v[i-1]))
        if j+1 < len(z) and valid[j+1] and v[j+1] < threshold and v[j+1] != v[j]:
            end = float(z[j] + (threshold-v[j])*(z[j+1]-z[j])/(v[j+1]-v[j]))
        # Do not infer beyond first/last observed point.
        start, end = max(start, float(z[0])), min(end, float(z[-1]))
        if end > start:
            runs.append((start, end))
        i = j+1
    persistent = tuple((a,b) for a,b in runs if b-a+1e-10 >= min_thickness)
    brief = tuple((a,b) for a,b in runs if b-a+1e-10 < min_thickness)
    return persistent, brief


def analyze_stratigraphy(depth, ic, sensor_valid=None, *, rolling_window: int = 1,
                         silt_threshold: float = 2.60, min_silt_m: float = .05,
                         max_depth_step_m: float = .06) -> Stratigraphy:
    """Get full soil-behavior layers and separate project-screening intervals.

    Inputs must be corrected BGL depths in ascending order. Missing data and large
    gaps produce UNKNOWN segments, never interpreted as clean sand/silt/clay.
    """
    z = np.asarray(depth, dtype=float)
    v = np.asarray(ic, dtype=float)
    if z.ndim != 1 or len(z) != len(v) or len(z) < 2:
        raise ValueError("Requires >=2 aligned corrected-depth/Ic samples")
    if not np.all(np.isfinite(z)) or np.any(np.diff(z) <= 0):
        raise ValueError("Depths must be finite and strictly ascending")
    if rolling_window < 1 or min_silt_m <= 0 or max_depth_step_m <= 0:
        raise ValueError("Invalid layer interpretation parameters")
    sensor = np.ones(len(z), dtype=bool) if sensor_valid is None else np.asarray(sensor_valid, dtype=bool)
    if len(sensor) != len(z):
        raise ValueError("Sensor validity length mismatch")
    valid = np.isfinite(v) & sensor
    # Split at large unobserved depth gaps; index following the gap cannot join across it.
    biggap = np.diff(z) > max_depth_step_m
    smooth = _smooth_contiguous(v, valid, int(rolling_window))
    if np.any(biggap):
        # Rebuild rolling mean without averaging across depth discontinuities.
        group_ids = np.cumsum(np.r_[0, biggap.astype(int)])
        smooth = np.full(len(z), np.nan)
        for g in np.unique(group_ids):
            idx = np.flatnonzero(group_ids == g)
            smooth[idx] = _smooth_contiguous(v[idx], valid[idx], int(rolling_window))
    smooth_valid = valid & np.isfinite(smooth)
    # Do not interpolate a threshold crossing across gaps.
    if np.any(biggap):
        for i in np.flatnonzero(biggap):
            if valid[i] and valid[i+1]:
                # Large gap handled as a split below, and no cross-gap threshold geometry.
                pass
    pieces: list[tuple[str,float,float,list[float],str]] = []
    for i in range(len(z)-1):
        a,b = float(z[i]),float(z[i+1])
        if b-a > max_depth_step_m:
            pieces.append(("UNKNOWN",a,b,[],"DEPTH GAP"))
            continue
        if not smooth_valid[i] or not smooth_valid[i+1]:
            pieces.append(("UNKNOWN",a,b,[],"SENSOR/DATA INVALID"))
            continue
        kind=behavior_label(float((smooth[i]+smooth[i+1])/2))
        pieces.append((kind,a,b,[float(smooth[i]),float(smooth[i+1])],"OBSERVED"))
    layers: list[Layer]=[]
    for kind,a,b,vals,reason in pieces:
        if layers and layers[-1].kind==kind and layers[-1].status==reason and abs(layers[-1].end_m-a)<1e-8:
            prev=layers.pop()
            w1=prev.mean_ic
            val=float(np.mean(vals)) if vals else None
            avg=(w1*prev.thickness_m+val*(b-a))/(prev.thickness_m+b-a) if w1 is not None and val is not None else None
            layers.append(Layer(prev.number,kind,prev.start_m,b,b-prev.start_m,avg,reason,kind!="UNKNOWN" and (avg or 0)>=silt_threshold))
        else:
            avg=float(np.mean(vals)) if vals else None
            layers.append(Layer(len(layers)+1,kind,a,b,b-a,avg,reason,kind!="UNKNOWN" and (avg or 0)>=silt_threshold))
    # Segment threshold intervals separately with explicit break at big gaps.
    segments = np.split(np.arange(len(z)), np.flatnonzero(biggap)+1)
    persistent_all=[];brief_all=[]
    for segment in segments:
        if len(segment)<2:
            continue
        persistent, brief = _intervals_from_indicator(z[segment],smooth[segment],smooth_valid[segment],silt_threshold,min_silt_m)
        persistent_all.extend(persistent);brief_all.extend(brief)
    notes=[
        "Ic is CPT soil-behavior index, not a laboratory USCS identification.",
        "Silt-screening indicator includes any valid Ic >= project threshold, including clay-like SBT.",
        "Measured qualifying layers are never extended beyond valid readings or into terminal fs dropout.",
        "The averaging order and 3/10 rolling-mean settings require workbook parity validation.",
    ]
    if not np.all(valid):
        notes.append("Some depth readings are UNKNOWN because sensor measurements or Ic are invalid.")
    if np.any(biggap):
        notes.append("Sounding contains large unsampled depth gaps; those regions remain UNKNOWN.")
    return Stratigraphy(tuple(layers),tuple(persistent_all),tuple(brief_all),
                        int(rolling_window),float(silt_threshold),tuple(notes))


def from_analysis(analysis, rolling_window: int | None = None) -> Stratigraphy:
    if rolling_window is None:
        metadata=getattr(analysis,"metadata",{}) or {}
        rolling_window=int(metadata.get("analysis_smoothing_window_samples",1))
    return analyze_stratigraphy(analysis.depth,analysis.ic,analysis.valid_sensor,
                                rolling_window=rolling_window)

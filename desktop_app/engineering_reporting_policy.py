"""Presentation policy for independently measured CPT silt-screen intervals.

This module does NOT edit cpt_core, the project Ic=2.60 screening threshold,
the PRE/POST smoothing, or the persistence rule that preserves raw evidence.

Operator reporting request (2026-10-31):
- Show every DISTINCT observed Ic-screened interval strictly thicker than 0.10m.
- Smaller/equal intervals are not *reportable layers* and are never presented
  as invented zero-thickness soil.
- Raw samples and original thin-layer evidence remain in expert audit tabs.
- Unknown material below a measured interval is UNKNOWN, not presumed clay.
"""
from __future__ import annotations
from math import isfinite
from typing import NamedTuple

REPORT_MIN_THICKNESS_M = 0.10
REPORT_PRECISION_M = 0.01


class DisplaySiltLayer(NamedTuple):
    start: float
    end: float
    thickness: float


def visible_silt_layers(analysis) -> tuple[DisplaySiltLayer, ...]:
    """Re-use computed depth/Ic arrays; filter already detected observed runs.

    Deliberately no input mutation, threshold replacement, numeric rounding or
    gap interpolation. Keep every separate run; never merge across sand/UNKNOWN.
    """
    try:
        from engineering_layers import from_analysis
        observed=from_analysis(analysis)
        pairs=observed.silt_intervals
    except (AttributeError,ValueError,TypeError,IndexError,KeyError):
        pairs=getattr(analysis,"all_intervals",()) or ()
    found=[]
    for start,end in pairs:
        try:
            a=float(start);b=float(end)
        except (TypeError,ValueError):
            continue
        if isfinite(a) and isfinite(b) and b-a>REPORT_MIN_THICKNESS_M+1e-9:
            found.append(DisplaySiltLayer(a,b,b-a))
    return tuple(sorted(found,key=lambda z:(z.start,z.end)))


def display_silt_summary(analysis):
    """Non-engineering derived display status, separate from analysis.status."""
    layers=visible_silt_layers(analysis)
    if getattr(analysis,"metadata",{}).get("same_point_short_attempt"):
        return "SHORT TEST - INCOMPLETE",layers
    if layers:
        return ("REVIEW - observed silt layers" if analysis.status=="REVIEW"
                else "OBSERVED SILT LAYERS"),layers
    if analysis.status=="REVIEW":
        md=getattr(analysis,"metadata",{}) or {}
        if md.get("thin_interval_unrounded_thickness") is not None:
            return "NO LAYER >0.10m - thin evidence retained",layers
        return "REVIEW - no approved silt layer >0.10m",layers
    return "NO REPORTABLE SILT LAYER >0.10m",layers

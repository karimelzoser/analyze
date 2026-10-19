"""Deterministic, non-destructive triage for CPT source and precision exceptions.

A REVIEW row is not necessarily an unreadable CPT: preserve observable
measurement evidence and distinguish source conflicts from reporting decisions.
Do not automatically promote a REVIEW to VERIFIED.
"""
from __future__ import annotations
from pathlib import Path
from math import isfinite


def _float(value):
    try:
        x=float(value)
        return x if isfinite(x) else None
    except (TypeError,ValueError):
        return None


def triage_review(analysis):
    if str(getattr(analysis,"status",""))!="REVIEW":
        return None
    meta=(getattr(analysis,"metadata",None) or {})
    source=str(getattr(getattr(analysis,"source_path",None),"name",
                       getattr(analysis,"source_path","UNKNOWN")))
    note=str(getattr(analysis,"verification_note","") or "")
    thin=_float(meta.get("thin_interval_unrounded_thickness"))
    start=_float(meta.get("thin_interval_unrounded_start"))
    end=_float(meta.get("thin_interval_unrounded_end"))
    # A real source revision conflict can still have a valid, measured
    # provisional interval. It MUST appear in Review Resolution rather than
    # "NOT RECORDED / UNAVAILABLE". Keep its REVIEW disposition unchanged.
    candidate=getattr(analysis,"final_interval",None)
    if candidate is not None:
        if start is None:
            start=_float(getattr(candidate,"start_raw",None))
            if start is None:start=_float(getattr(candidate,"start",None))
        if end is None:
            end=_float(getattr(candidate,"end_raw",None))
            if end is None:end=_float(getattr(candidate,"end",None))
        if thin is None:
            thin=_float(getattr(candidate,"thickness_raw",None))
            if thin is None:thin=_float(getattr(candidate,"thickness",None))
    if thin is None and start is not None and end is not None:
        thin=max(0.0,end-start)
    conflict_flags=[key for key in (
        "source_revision_conflict","source_spatial_conflict","source_datum_conflict"
    ) if meta.get(key)]
    if conflict_flags or "source revisions conflict" in note.lower():
        category="SOURCE CONFLICT"
        decision="Confirm original field-test IDs, coordinate/elevation, dates and approved revision; reprocess authoritative source"
    elif thin is not None and thin>0:
        category="OBSERVED THIN INTERVAL"
        decision=("Approve a stated measured-thickness reporting precision or supply an approved thin-layer rule; "
                  "never round observed thickness upward merely to suppress REVIEW")
    elif _float(getattr(analysis,"sensor_dropout_depth",None)) is not None or (
            "dropout" in note.lower() or "sensor" in note.lower()):
        category="INCOMPLETE SENSOR MEASUREMENT"
        decision="Check original numerical GEF/GFF and field logs; do not extrapolate soil classification across missing sensor readings"
    elif "pdf" in source.lower():
        category="PDF GRAPHIC AMBIGUITY"
        decision="Obtain original numerical GEF/GFF or an approved vector trace/revised report"
    else:
        category="ENGINEERING INTERPRETATION"
        decision="Verify raw measurements, Ic calculation assumptions, persistence and boundary classification"
    return {
        "reference":str(analysis.reference),
        "category":category,
        "source":source,
        "measured_start_m":start,
        "measured_end_m":end,
        "measured_thickness_m":thin,
        "test_depth_m":_float(getattr(analysis,"test_depth_raw",None)),
        "sensor_dropout_m":_float(getattr(analysis,"sensor_dropout_depth",None)),
        "conflict_fields":", ".join(conflict_flags) if conflict_flags else None,
        "required_action":decision,
        "evidence":note,
        "engineering_disposition":"AWAITING REVIEW — retain source data; do not treat as verified design input",
    }


def review_register(analyses):
    return [row for a in analyses if (row:=triage_review(a)) is not None]


def triage_counts(analyses):
    from collections import Counter
    return dict(sorted(Counter(x["category"] for x in review_register(analyses)).items()))

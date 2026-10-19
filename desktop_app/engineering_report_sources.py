"""Preserve an official reference PDF without sacrificing raw GEF numerical analysis.

Raw measurements take precedence for engineering values. A source PDF may be
reused as the *visual report page* only when the observed point coordinates,
ground elevation and available test date agree. Otherwise the app renders its
reference-like report and flags the mismatch for review.
"""
from __future__ import annotations

from datetime import datetime
from math import hypot,isfinite
from pathlib import Path
import re


def _finite(metadata,key):
    try:
        value=float(metadata.get(key))
        return value if isfinite(value) else None
    except (AttributeError,ValueError,TypeError):
        return None


def _date(metadata, *, explicit_test_only=False):
    # GEF FILEDATE/STARTDATE may mean file export or processing date, not
    # the original field-test date printed on a CPT PDF. Never assume equal
    # semantics when matching source reports.
    value=str(metadata.get("test_date") if explicit_test_only else
              (metadata.get("test_date") or metadata.get("file_date") or "")).strip()
    if not value:return None
    for fmt in ("%d-%b-%Y","%Y-%m-%d","%d/%m/%Y","%Y,%m,%d","%d-%B-%Y"):
        try:return datetime.strptime(value,fmt).date()
        except ValueError:pass
    return None


def choose_official_pdf(raw_analysis,candidates,*,xy_tolerance_m=.50,
                        elevation_tolerance_m=.08):
    """Find a verified matching official PDF page for one RAW CPT.

    Only coordinate-verified original PDF input is allowed. Never select a
    nonmatching report merely because the filename or family resembles it.
    Returns (matching_pdf_analysis, reason) or (None, reason).
    """
    raw_path=Path(raw_analysis.source_path)
    if raw_path.suffix.lower() not in (".gef",".gff"):
        return None,"Source is not GEF/GFF; original PDF handling already applies."
    raw=raw_analysis.metadata or {}
    x0,y0=_finite(raw,"easting"),_finite(raw,"northing")
    if x0 is None or y0 is None:
        return None,"Raw source coordinates missing; official PDF matching disabled."
    from app_pdf_enabled import source_reference_key,source_revision
    family=source_reference_key(raw_path)
    compatible=[];rejected=[]
    for a in candidates:
        pdf_path=Path(a.source_path)
        if pdf_path.suffix.lower()!=".pdf" or source_reference_key(pdf_path)!=family:
            continue
        metadata=a.metadata or {}
        x1,y1=_finite(metadata,"easting"),_finite(metadata,"northing")
        if x1 is None or y1 is None:
            rejected.append(pdf_path.name+": PDF coordinates missing")
            continue
        dist=hypot(x1-x0,y1-y0)
        if dist>xy_tolerance_m:
            rejected.append(pdf_path.name+": coordinates differ by %.2fm"%dist)
            continue
        z0,z1=_finite(raw,"ground_elevation"),_finite(metadata,"ground_elevation")
        if z0 is not None and z1 is not None and abs(z0-z1)>elevation_tolerance_m:
            rejected.append(pdf_path.name+": ground elevations differ by %.3fm"%abs(z0-z1))
            continue
        raw_date,pdf_date=_date(raw,explicit_test_only=True),_date(metadata)
        if raw_date is not None and pdf_date is not None and raw_date!=pdf_date:
            rejected.append(pdf_path.name+": test dates conflict")
            continue
        compatible.append((a,dist,abs(z0-z1) if z0 is not None and z1 is not None else 999))
    if not compatible:
        return None,"No matching official PDF with approved point geometry. "+("; ".join(rejected[:3]) or "None supplied.")
    compatible.sort(key=lambda item:(item[1],item[2],-source_revision(item[0].source_path)))
    chosen=compatible[0][0]
    if len(compatible)>1:
        other=compatible[1]
        if abs(other[1]-compatible[0][1])<1e-4 and abs(other[2]-compatible[0][2])<.001:
            # Identical geometry with distinct revisions may contain different
            # reports. Better preserve newer revision only if difference is just
            # filename; signal to Source Audit for engineering accountability.
            compatible.sort(key=lambda item:(-source_revision(item[0].source_path),item[1]))
            chosen=compatible[0][0]
    return chosen,("Original PDF pages preserved with numerical GEF/GFF calculations; "
                   "coordinates and elevation agree. File export dates are NOT assumed "
                   "to be field-test dates; verify source identity if this is a retest.")


def enrich_from_matched_official_pdf(raw_analysis, official_pdf_analysis):
    """Populate only absent descriptive report fields from a matched PDF.

    Geotechnical inputs, numeric coordinates, test depth, area ratio, qc and
    Ic always remain authoritative from raw GEF/GFF. Provenance for each
    imported field is explicitly retained in metadata for workbook/PDF audit.
    The caller must have verified the physical CPT pairing first.
    """
    raw = getattr(raw_analysis,"metadata",None)
    pdf = getattr(official_pdf_analysis,"metadata",None)
    if not isinstance(raw,dict) or not isinstance(pdf,dict):
        raise ValueError("Both CPTs require source metadata dictionaries")
    descriptive=("client","project_name","location","main_contractor",
                 "cone_id","standard","test_date")
    imported={}
    disagreements={}
    for key in descriptive:
        value=pdf.get(key)
        if value is None or not str(value).strip():
            continue
        current=raw.get(key)
        if current is None or not str(current).strip():
            raw[key]=value
            imported[key]=str(value)
        elif str(current).strip().casefold()!=str(value).strip().casefold():
            # Never quietly replace an existing source field. Even differing
            # contractor names / dates are useful for audit and review.
            disagreements[key]={"raw":str(current),"pdf":str(value)}
    raw["official_pdf_metadata_source"]=str(official_pdf_analysis.source_path.name)
    raw["official_pdf_imported_fields"]=imported
    raw["official_pdf_metadata_disagreements"]=disagreements
    return imported,disagreements

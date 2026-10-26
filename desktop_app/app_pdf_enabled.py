from __future__ import annotations

import os
import math
import re
import zipfile
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tkinter import filedialog, messagebox

import app_modern
import app_modern_v2
import reporting_export_v2
from pdf_analysis_refined import analyze_pdf, append_pdf_analysis


SUPPORTED_EXTENSIONS = {".gef", ".gff", ".pdf"}
RAW_EXTENSIONS = {".gef", ".gff"}
CONCLUSIVE_STATUSES = {"VERIFIED", "NO SILT"}


def _source_stem(value: str | Path) -> str:
    if isinstance(value, Path):
        return value.stem
    text = str(value)
    p = Path(text)
    return p.stem if p.suffix.lower() in SUPPORTED_EXTENSIONS else text


def canonical_reference(value: str | Path) -> str:
    """Return the project CPT family reference, stripping report revision suffixes.

    Project files commonly contain revisions such as ``-1``, ``-2`` or ``(1)``.
    The physical files remain separately auditable, but the project result must
    contain one row per CPT location. The canonical project naming convention
    ends in ``-100``; a legacy ``.100`` spelling is normalized as well.
    """
    stem = _source_stem(value).strip()
    stem = re.sub(r"^P\d+_", "", stem, flags=re.I)
    stem = re.sub(r"[.\s]+$", "", stem)

    # Capture through the project's terminal -100 token and deliberately ignore
    # any following revision/copy suffix.
    m = re.search(r"(CPT-[A-Z0-9]+(?:-[A-Z0-9]+)*?[-.]100)(?=$|[-.(\s])", stem, flags=re.I)
    if m:
        return re.sub(r"[.]100$", "-100", m.group(1), flags=re.I).upper()

    # Conservative fallback for non-project naming. Parenthesized copy suffixes
    # are safe to remove; numeric dash suffixes are removed only after -100.
    stem = re.sub(r"\(\d+\)$", "", stem).strip(" .")
    if re.search(r"[-.]100-\d+$", stem, flags=re.I):
        stem = re.sub(r"-\d+$", "", stem)
    stem = re.sub(r"[.]100$", "-100", stem, flags=re.I)
    return stem.upper()


def source_reference_key(path: str | Path) -> str:
    return canonical_reference(path)


def source_revision(path: str | Path) -> int:
    """Extract the project revision number from a physical source filename."""
    stem = _source_stem(path).strip()
    stem = re.sub(r"^P\d+_", "", stem, flags=re.I)
    m = re.search(r"CPT-[A-Z0-9]+(?:-[A-Z0-9]+)*?[-.]100", stem, flags=re.I)
    tail = stem[m.end():] if m else ""
    tail = tail.strip(" ._")
    if not tail:
        return 0
    mrev = re.search(r"(?:^[-_]?|\()(?P<n>\d+)\)?$", tail)
    return int(mrev.group("n")) if mrev else 0


def collect_candidate_sources(paths) -> list[Path]:
    """Keep all physical revisions for QA; remove only exact duplicate paths."""
    unique: dict[str, Path] = {}
    for value in paths:
        p = Path(value)
        if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            key = str(p.resolve()).lower()
        except Exception:
            key = str(p.absolute()).lower()
        unique[key] = p
    return sorted(
        unique.values(),
        key=lambda p: (app_modern.natural_ref_key(source_reference_key(p)), source_revision(p), p.name.lower()),
    )


def prefer_best_sources(paths) -> tuple[list[Path], list[Path]]:
    """Compatibility helper: retain all revisions so the analyzer can QA them.

    Source selection is now performed *after* analysis. This is essential: an
    older/base PDF may be REVIEW while a later revision is fully verifiable.
    """
    selected = collect_candidate_sources(paths)
    return selected, []


def collect_project_folder(folder: str | Path) -> tuple[list[Path], list[Path]]:
    """Discover sources without re-ingesting previously generated CPT reports.

    Default CPT_Output is deliberately located under the input folder, so a
    recursive unfiltered rglob caused the app to ingest its own previous PDFs
    on the second run, creating artificial duplicate/REVIEW project rows.
    Explicitly selected individual PDFs remain supported.
    """
    import re
    root=Path(folder)
    paths=[]
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        # Inspect subdirectories relative to the requested root, never the
        # root name itself: users may explicitly select a folder named CPT_Output.
        parents=p.relative_to(root).parts[:-1]
        if any(re.match(r"(?i)^cpt[_ -]?output(?:$|[_ -])", part) for part in parents):
            continue
        paths.append(p)
    return prefer_best_sources(paths)


def analyze_source(path: Path, gamma: float, wt: float):
    if path.suffix.lower() == ".pdf":
        return analyze_pdf(path)
    return app_modern.analyze_gef(path, gamma_soil=gamma, water_table_depth=wt)


def _result_signature(a) -> tuple:
    if a.status == "NO SILT":
        return ("NO SILT", None, 0.0)
    if a.final_interval is not None:
        return (a.status, a.final_interval.start, a.final_interval.thickness)
    return (a.status, None, None)


def _candidate_rank(a) -> tuple:
    """Rank within one source type: later revision first, then later file mtime."""
    rev = source_revision(a.source_path)
    try:
        mtime = a.source_path.stat().st_mtime_ns
    except Exception:
        mtime = 0
    return (rev, mtime, a.source_path.name.lower())


def retain_physical_cpt_results(analyses, all_sources=None, analysis_errors=None):
    """Output EVERY numerical sounding independently, without merging calculations.

    Raw GEF/GFF are authoritative for numerical data; an official PDF of the
    same point is a visual reference, not a second CPT measurement. If only
    PDFs are supplied, every physical PDF is retained separately. Each raw
    source gets its own result, raw measurements, PDF, and unique workbook ID.
    A repeated TESTID means *multiple tests at one location*, not a reason to
    discard one. Screening calculations/thresholds/precision are unchanged.
    """
    analyses=list(analyses)
    all_sources=list(all_sources or [a.source_path for a in analyses])
    analysis_errors=dict(analysis_errors or {})
    def key(path):
        try:return str(Path(path).resolve()).lower()
        except Exception:return str(Path(path).absolute()).lower()
    families={}
    for a in analyses:
        families.setdefault(canonical_reference(a.reference),[]).append(a)
    results=[]
    selected_by_path={}
    family_by_path={key(a.source_path):canonical_reference(a.reference) for a in analyses}
    for family,items in families.items():
        raw=[a for a in items if a.source_path.suffix.lower() in RAW_EXTENSIONS]
        pool=raw if raw else items
        ordered=sorted(pool,key=lambda a:(source_revision(a.source_path),a.source_path.name.lower(),key(a.source_path)))
        group_size=len(ordered)
        depths=[]
        for measured in ordered:
            try:
                value=float(measured.test_depth_raw)
                if math.isfinite(value):depths.append(value)
            except (TypeError,ValueError,AttributeError):pass
        deepest=max(depths,default=0.0)
        # Check whether the nominally same TESTID actually shares XY/RL.
        survey=[];levels=[]
        for source in ordered:
            try:
                x=float((source.metadata or {}).get("easting"))
                y=float((source.metadata or {}).get("northing"))
                if math.isfinite(x) and math.isfinite(y):survey.append((x,y))
            except (TypeError,ValueError,AttributeError):pass
            try:
                z=float((source.metadata or {}).get("ground_elevation"))
                if math.isfinite(z):levels.append(z)
            except (TypeError,ValueError,AttributeError):pass
        spatial_delta=max((math.hypot(x-survey[0][0],y-survey[0][1])
                           for x,y in survey[1:]),default=0.0) if survey else 0.0
        level_delta=max((abs(z-levels[0]) for z in levels[1:]),
                        default=0.0) if levels else 0.0
        for seq,a in enumerate(ordered,1):
            md=dict(getattr(a,"metadata",{}) or {})
            source_ref=a.reference
            try:source_depth=float(a.test_depth_raw)
            except (TypeError,ValueError,AttributeError):source_depth=0.0
            short_attempt=(group_size>1 and deepest>=1.0
                           and source_depth < min(1.0,.65*deepest))
            md.update({
                "source_report_reference":source_ref,
                "canonical_reference":family,
                "source_revision":source_revision(a.source_path),
                "source_family_count":group_size,
                "same_point_file_count":group_size,
                "same_point_short_attempt":short_attempt,
                "same_point_file_index":seq,
                "same_point_multiple_files":group_size>1,
                "same_point_survey_conflict":spatial_delta>.50 or level_delta>.08,
                "same_point_max_xy_delta_m":round(spatial_delta,3),
                "same_point_max_level_delta_m":round(level_delta,3),
                "same_point_note":(
                    f"SAME CPT POINT — SOURCE FILE {seq} OF {group_size}; "
                    "independent physical measurements; compare original "
                    "filenames and field-test dates before selecting a design source."
                    + (f" SURVEY CONFLICT: coordinates vary {spatial_delta:.3f}m;"
                       f" ground levels vary {level_delta:.3f}m."
                       " Confirm if these are even the same physical point."
                       if spatial_delta>.50 or level_delta>.08 else "")
                    if group_size>1 else "One analyzed physical source file."),
                "source_selection_reason":(
                    f"Individually reported physical source {seq} of {group_size} "
                    f"for {family}; no numerical merge, no silent supersession."),
            })
            a.metadata=md
            # Make workbook IDs, chart series, PDF filenames and atlas hover
            # labels unique WITHOUT changing any numeric measurement.
            a.reference=(f"{family} (FILE {seq} OF {group_size})"
                         if group_size>1 else family)
            if group_size>1:
                a.verification_note=(
                    (str(getattr(a,"verification_note","") or "")+" ")
                    +md["same_point_note"]
                    + (" SUBSTANTIALLY SHORT / ABORTED CPT: this recorded"
                       " calculation is limited to the observed sounding"
                       " depth and is NOT evidence that the deeper soil"
                       " has NO SILT. Do not use it to replace the later"
                       " complete sounding."
                       if short_attempt else ""))
            results.append(a)
            selected_by_path[key(a.source_path)]=a
    results.sort(key=lambda a:(app_modern.natural_ref_key(
        str(a.metadata.get("canonical_reference") or a.reference)),
        int(a.metadata.get("same_point_file_index",1))))
    audit=[]
    for p in sorted(all_sources,key=lambda q:(
            app_modern.natural_ref_key(family_by_path.get(key(q),source_reference_key(q))),
            source_revision(q),q.name.lower())):
        k=key(p)
        a=next((a for a in analyses if key(a.source_path)==k),None)
        chosen=selected_by_path.get(k)
        family=family_by_path.get(k,source_reference_key(p))
        if a is None:
            status="ERROR";start=thickness=None
            note=analysis_errors.get(k,analysis_errors.get(str(p),"Source could not be analyzed."))
            why="Input source failed; retained for error audit."
        else:
            z=getattr(a,"final_interval",None)
            status=a.status
            start=z.start if z is not None else ("NO SILT" if status=="NO SILT" else None)
            thickness=z.thickness if z is not None else (0.0 if status=="NO SILT" else None)
            note=getattr(a,"verification_note","")
            why=(a.metadata.get("source_selection_reason","")
                 if chosen is not None else
                 "Reference PDF only: corresponding RAW GEF/GFF is the numerical source; PDF kept for traceability.")
        audit.append({
            "family":family,"source_file":p.name,
            "source_type":p.suffix.upper().lstrip("."),
            "revision":source_revision(p),
            "source_quality":str((getattr(a,"metadata",{}) or {}).get("source_quality")
                or ("RAW GEF/GFF" if p.suffix.lower() in RAW_EXTENSIONS else "PDF")),
            "status":status,"silt_start":start,"silt_thickness":thickness,
            "selected":"YES" if chosen is not None else "NO",
            "selection_reason":why,"verification_note":note,
            "result_reference":chosen.reference if chosen is not None else None,
            "same_point_file_count":(
                chosen.metadata.get("same_point_file_count",1)
                if chosen is not None else len(families.get(family,[]))),
        })
    return results,audit


def select_project_results(analyses, all_sources=None, analysis_errors=None):
    """Collapse physical report revisions to one authoritative project CPT row.

    Selection policy:
      1. Raw GEF/GFF has source priority whenever a raw analysis is available.
      2. Within that source class, the highest revision is authoritative when
         it is conclusive (VERIFIED / NO SILT).
      3. If the newest revision is REVIEW, fall back to the highest conclusive
         revision and make that fallback explicit in the Source Audit sheet.
      4. If every revision is REVIEW, retain the newest REVIEW; never guess.

    Returns ``(selected_results, audit_rows)``.
    """
    analyses = list(analyses)
    all_sources = list(all_sources or [a.source_path for a in analyses])
    analysis_errors = dict(analysis_errors or {})

    # The TESTID embedded in the data or official PDF metadata—not an arbitrary
    # descriptive upload filename—is the authoritative physical CPT identifier.
    # Preserve the original source filename separately for exact provenance.
    def key_for_file(path):
        try:return str(Path(path).resolve()).lower()
        except Exception:return str(Path(path).absolute()).lower()
    source_identity={key_for_file(a.source_path):canonical_reference(a.reference)
                     for a in analyses}
    family_sources: dict[str, list[Path]] = {}
    for p in all_sources:
        family=source_identity.get(key_for_file(p),source_reference_key(p))
        family_sources.setdefault(family, []).append(Path(p))

    grouped: dict[str, list] = {}
    for a in analyses:
        grouped.setdefault(canonical_reference(a.reference), []).append(a)

    selected_results = []
    selected_by_family: dict[str, object] = {}

    for family, items in grouped.items():
        raw_items = [a for a in items if a.source_path.suffix.lower() in RAW_EXTENSIONS]
        pool = raw_items if raw_items else items
        source_class = "RAW GEF/GFF" if raw_items else "PDF"
        def _observed_length(a):
            try:
                z=float(a.test_depth_raw)
                return z if math.isfinite(z) and z>0 else None
            except (AttributeError,TypeError,ValueError):
                return None
        depths=[z for a in pool if (z:=_observed_length(a)) is not None]
        longest=max(depths,default=None)
        # A 0.27m failed push followed by a 6.09m full CPT is not a
        # contradictory full-depth interpretation. Keep both in Source
        # Audit, but choose only a substantially complete sounding.
        incomplete=[a for a in pool if longest is not None and longest>=1.0
                    and (z:=_observed_length(a)) is not None
                    and z < min(1.0, .65*longest)]
        incomplete_ids={id(a) for a in incomplete}
        eligible=[a for a in pool if id(a) not in incomplete_ids]
        if not eligible:
            eligible=pool
        newest=max(eligible,key=_candidate_rank)
        conclusive=[a for a in eligible if a.status in CONCLUSIVE_STATUSES]

        if newest.status in CONCLUSIVE_STATUSES:
            selected=newest
            reason=f"Selected highest sufficiently complete {source_class} revision ({source_revision(newest.source_path)})."
        elif conclusive:
            selected=max(conclusive,key=_candidate_rank)
            reason=("Newest sufficiently complete source requires REVIEW; "
                    f"selected conclusive revision {source_revision(selected.source_path)}.")
        else:
            selected=newest
            reason="All sufficiently complete candidate sources require REVIEW."
        if incomplete:
            reason+=(" Excluded %d substantially incomplete/aborted earlier sounding(s)"
                    " from final-layer conflict voting; originals kept in Source Audit."%len(incomplete))

        signatures={_result_signature(a) for a in conclusive}
        # Do not silently fall back to a verified older sounding when a
        # comparable substantial retest is REVIEW. B254 real-field acceptance
        # identified an older 4.87m push marked VERIFIED while a later 5.73m
        # measured retest was REVIEW due thin-layer reporting precision.
        # Both represent substantial physical soundings and require an
        # authoritative field-test decision before project acceptance.
        review_retest_conflict=selected.status in CONCLUSIVE_STATUSES and any(
            a is not selected and a.status=="REVIEW"
            and _observed_length(a) is not None
            and longest is not None
            and _observed_length(a)>=.80*longest
            for a in eligible)
        conflict=(len(signatures)>1 or review_retest_conflict)
        # Different report versions can use the same nominal CPT identifier
        # while referring to different physical tests. These must not be
        # collapsed into a seemingly verified single engineering location.
        points=[]
        levels=[]
        for item in items:
            try:
                x=float(item.metadata.get("easting"))
                y=float(item.metadata.get("northing"))
                if math.isfinite(x) and math.isfinite(y):
                    points.append((x,y,item.source_path.name))
            except (TypeError,ValueError,AttributeError):
                pass
            try:
                level=float(item.metadata.get("ground_elevation"))
                if math.isfinite(level):
                    levels.append((level,item.source_path.name))
            except (TypeError,ValueError,AttributeError):
                pass
        spatial_conflict=any(
            math.hypot(x-points[0][0],y-points[0][1])>.50
            for x,y,_ in points[1:]) if len(points)>1 else False
        datum_conflict=any(
            abs(z-levels[0][0])>.08 for z,_ in levels[1:]) if len(levels)>1 else False
        if conflict or spatial_conflict or datum_conflict:
            reason += (" SOURCE CONFLICT: comparable substantial retests differ"
                       " in verified status, observed engineering classification,"
                       " physical coordinates, or ground elevation."
                       " The selected numeric result is PROVISIONAL, not accepted."
                       " Every retest remains in Source Audit for field adjudication.")
            if review_retest_conflict:
                reason+=(" A substantial competing physical source requires REVIEW;"
                         " an older conclusive result cannot override it automatically.")
            selected.status="REVIEW"
            # Keep original measured candidate interval so the project sheet
            # shows an analyzed number, not an empty cell. Its REVIEW status
            # and SOURCE CONFLICT label remain mandatory until sign-off.
            selected.metadata=dict(selected.metadata)
            selected.metadata["provisional_conflicting_result"]=True
            selected.verification_note=(str(selected.verification_note or "")+
                 " Project full-depth source revisions CONFLICT. The displayed"
                 " start/thickness is preliminary, NOT VERIFIED. Compare"
                 " original field-test identity, depth, qc/fs curves, survey"
                 " datum and accepted retest before engineering use.")

        original_ref = selected.reference
        selected.metadata = dict(selected.metadata)
        selected.metadata.update({
            "source_report_reference": original_ref,
            "canonical_reference": family,
            "source_revision": source_revision(selected.source_path),
            "source_selection_reason": reason,
            "source_family_count": len(family_sources.get(family, items)),
            "source_revision_conflict": conflict,
            "source_retest_review_conflict": review_retest_conflict,
            "source_spatial_conflict": spatial_conflict,
            "source_datum_conflict": datum_conflict,
            "incomplete_source_count":len(incomplete),
            "incomplete_source_filenames":[a.source_path.name for a in incomplete],
        })
        selected.reference = family
        selected_results.append(selected)
        selected_by_family[family] = selected

    selected_results.sort(key=lambda a: app_modern.natural_ref_key(a.reference))

    audit_rows = []
    analyzed_by_path = {}
    for a in analyses:
        try:
            key = str(a.source_path.resolve()).lower()
        except Exception:
            key = str(a.source_path.absolute()).lower()
        analyzed_by_path[key] = a

    for p in sorted(all_sources, key=lambda q: (app_modern.natural_ref_key(source_reference_key(q)), source_revision(q), q.name.lower())):
        family = source_identity.get(key_for_file(p), source_reference_key(p))
        try:
            pkey = str(Path(p).resolve()).lower()
        except Exception:
            pkey = str(Path(p).absolute()).lower()
        a = analyzed_by_path.get(pkey)
        selected = selected_by_family.get(family)
        is_selected = a is not None and selected is a

        if a is None:
            status = "ERROR"
            start = thickness = None
            quality = "RAW GEF/GFF" if p.suffix.lower() in RAW_EXTENSIONS else "PDF"
            note = analysis_errors.get(pkey, analysis_errors.get(str(p), "Analysis failed before a verified result could be produced."))
        else:
            status = a.status
            start = a.final_interval.start if a.final_interval is not None else ("NO SILT" if a.status == "NO SILT" else None)
            thickness = a.final_interval.thickness if a.final_interval is not None else (0.0 if a.status == "NO SILT" else None)
            quality = str(a.metadata.get("source_quality") or ("RAW GEF/GFF" if p.suffix.lower() in RAW_EXTENSIONS else "PDF"))
            note = a.verification_note

        if is_selected:
            selection_reason = str(selected.metadata.get("source_selection_reason") or "Selected project source.")
        elif selected is not None:
            if a is not None and p.name in selected.metadata.get("incomplete_source_filenames",[]):
                selection_reason=(f"ABORTED / SUBSTANTIALLY INCOMPLETE CPT; {selected.source_path.name}"
                                  " is a later full-depth sounding at the same physical point.")
            else:
                selection_reason=f"Superseded by {selected.source_path.name}."
        else:
            selection_reason = "No project source could be selected from this family."

        audit_rows.append({
            "family": family,
            "source_file": p.name,
            "source_type": p.suffix.upper().lstrip("."),
            "revision": source_revision(p),
            "source_quality": quality,
            "status": status,
            "silt_start": start,
            "silt_thickness": thickness,
            "selected": "YES" if is_selected else "NO",
            "selection_reason": selection_reason,
            "verification_note": note,
        })

    return selected_results, audit_rows


class AnalysisCancelled(Exception):
    """User requested safe cancellation at a phase boundary."""


class PDFEnabledCPTApp(app_modern_v2.ProfessionalModernCPTApp):
    """Production desktop shell supporting GEF, GFF and CPT PDF reports."""

    def __init__(self):
        self.skipped_duplicate_sources: list[Path] = []
        self.source_audit: list[dict] = []
        super().__init__()
        self.title("CPT Analyzer Professional - GEF / GFF / PDF")
        self._replace_static_text("GEF / GFF", "GEF / GFF / PDF")
        self.status_var.set("Ready — select GEF/GFF/PDF files or a project folder.")

    def _replace_static_text(self, old: str, new: str):
        def walk(widget):
            for child in widget.winfo_children():
                try:
                    if child.cget("text") == old:
                        child.configure(text=new)
                except Exception:
                    pass
                walk(child)
        walk(self)

    def select_files(self):
        chosen = filedialog.askopenfilenames(
            title="Select CPT GEF/GFF/PDF files",
            filetypes=[
                ("CPT inputs including ZIP", "*.GEF *.gef *.GFF *.gff *.PDF *.pdf *.ZIP *.zip"),
                ("Raw CPT files", "*.GEF *.gef *.GFF *.gff"),
                ("CPT PDF reports", "*.PDF *.pdf"),
                ("All files", "*.*"),
            ],
        )
        if chosen:
            from engineering_zip_inputs import extract_project_zip
            expanded=[]
            try:
                for item in chosen:
                    p=Path(item)
                    if p.suffix.lower()==".zip":
                        _,extracted=extract_project_zip(p)
                        expanded.extend(extracted)
                    else:
                        expanded.append(p)
            except (ValueError,OSError,zipfile.BadZipFile) as exc:
                messagebox.showerror("CPT ZIP input problem",str(exc))
                return
            self.files=collect_candidate_sources(expanded)
            self.skipped_duplicate_sources=[]
            self._after_select()
            self._describe_selection()

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing CPT GEF/GFF/PDF files")
        if folder:
            self.files, self.skipped_duplicate_sources = collect_project_folder(folder)
            self.output_dir = Path(folder) / "CPT_Output"
            self.output_var.set(str(self.output_dir))
            self._after_select(set_output=False)
            self._describe_selection()

    def _describe_selection(self):
        raw = sum(p.suffix.lower() in RAW_EXTENSIONS for p in self.files)
        pdf = sum(p.suffix.lower() == ".pdf" for p in self.files)
        families = len({source_reference_key(p) for p in self.files})
        revisions = max(0, len(self.files) - families)
        self.status_var.set(
            f"Loaded {len(self.files)} physical source(s) across {families} CPT location(s): "
            f"{raw} raw, {pdf} PDF, {revisions} revision/duplicate source(s). "
            "All revisions are checked; one authoritative result is selected per CPT."
        )

    def clear(self):
        self.skipped_duplicate_sources = []
        self.source_audit = []
        super().clear()
        self.status_var.set("Ready — select GEF/GFF/PDF files or a project folder.")

    def _worker(self, out: Path, gamma: float, wt: float, make_pdfs: bool):
        """Never leave the GUI permanently disabled on a failed batch."""
        import traceback
        try:
            return self._work_batch(out,gamma,wt,make_pdfs)
        except AnalysisCancelled:
            # Do not leave partly completed project reports after Cancel.
            # These are run-created unique paths only; existing output files
            # are never deleted.
            for report in getattr(self,"_created_pdf_paths",[]):
                try:Path(report).unlink(missing_ok=True)
                except OSError:pass
            self.messages.put(("cancelled",))
        except Exception as exc:
            diagnostic=traceback.format_exc()
            log_path=Path(out)/"CPT_Processing_Failure.log"
            try:
                Path(out).mkdir(parents=True,exist_ok=True)
                log_path.write_text(diagnostic,encoding="utf-8")
            except OSError:
                log_path=Path("(Could not write processing log)")
            self.messages.put(("fatal",str(exc),str(log_path)))

    def _work_batch(self, out: Path, gamma: float, wt: float, make_pdfs: bool):
        out.mkdir(parents=True, exist_ok=True)
        # A dedicated PDF folder for each analysis prevents stale reports
        # from earlier runs being mistaken for the new same-point retest set.
        pdfs = out / "PDFs" / ("Run_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
        cancel=getattr(self,"cancel_event",None)
        def guard():
            if cancel is not None and cancel.is_set():
                raise AnalysisCancelled()
        generated_pdfs=[]
        self._created_pdf_paths=generated_pdfs
        guard()
        if make_pdfs:
            pdfs.mkdir(parents=True, exist_ok=True)

        candidate_results = []
        errors: list[tuple[str, str]] = []
        error_map: dict[str, str] = {}
        raw_sources = [p for p in self.files if p.suffix.lower() in RAW_EXTENSIONS]
        pdf_sources = [p for p in self.files if p.suffix.lower() == ".pdf"]
        total = len(self.files)
        completed = 0

        # Raw numerical CPT analysis is parallel. PDF parsing remains serial
        # because PyMuPDF does not guarantee thread safety.
        if raw_sources:
            workers = max(1, min(8, os.cpu_count() or 4, len(raw_sources)))
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="cpt-raw") as pool:
                futures = {
                    pool.submit(app_modern.analyze_gef, p, gamma_soil=gamma, water_table_depth=wt,
                                stage=getattr(self,"analysis_stage_value","PRE")): p
                    for p in raw_sources
                }
                for future in as_completed(futures):
                    guard()
                    p = futures[future]
                    completed += 1
                    try:
                        a = future.result()
                        candidate_results.append(a)
                        self.messages.put(("analysis_row", completed, total, a))
                    except Exception as exc:
                        msg = str(exc)
                        errors.append((p.name, msg))
                        try:
                            error_map[str(p.resolve()).lower()] = msg
                        except Exception:
                            error_map[str(p)] = msg
                        self.messages.put(("analysis_error", completed, total, p, msg))

        for p in pdf_sources:
            guard()
            completed += 1
            try:
                a = analyze_pdf(p)
                candidate_results.append(a)
                self.messages.put(("analysis_row", completed, total, a))
            except Exception as exc:
                msg = str(exc)
                errors.append((p.name, msg))
                try:
                    error_map[str(p.resolve()).lower()] = msg
                except Exception:
                    error_map[str(p)] = msg
                self.messages.put(("analysis_error", completed, total, p, msg))

        guard()
        self.messages.put(("batch_stage",60 if make_pdfs else 90,
                           "Verifying sources and duplicate CPT references",
                           f"{len(candidate_results)} analyzed source(s)"))
        # Every independently measured GEF/GFF must produce its own result,
        # even when TESTID and XY match a retest at the same physical point.
        # The numerical analysis engine is unchanged.
        results, audit_rows = retain_physical_cpt_results(candidate_results, self.files, error_map)
        self.source_audit = audit_rows
        if not results:
            detail="; ".join(f"{name}: {problem}" for name,problem in errors[:3])
            raise RuntimeError("No CPT source could be analyzed. Check file formats, sensor data and permissions. "+detail)

        # 2D and 3D project maps are now embedded inside ONE comprehensive XLSX.
        # Explicit Save PNG remains available from the interactive Site Map tab.

        if make_pdfs:
            for idx, a in enumerate(results, 1):
                guard()
                try:
                    output_pdf = app_modern.unique_pdf_path(pdfs, a.reference)
                    if a.source_path.suffix.lower() == ".pdf":
                        append_pdf_analysis(a.source_path, a, output_pdf)
                    else:
                        from engineering_report_sources import choose_official_pdf
                        if (a.metadata or {}).get("same_point_multiple_files"):
                            # A physical PDF cannot be assigned to two retests
                            # on nominal XY alone; keep both raw calculations.
                            official=None
                            reason=("SAME POINT MULTIPLE FILES: generating a"
                                    " source-specific PDF; no ambiguous"
                                    " official chart pairing.")
                        else:
                            official, reason = choose_official_pdf(a, candidate_results)
                        if official is not None:
                            # Calculations remain from raw GEF. The
                            # coordinate-matched original can fill only
                            # missing descriptive PDF labels, with an audit
                            # trail recording each imported/conflicting field.
                            from engineering_report_sources import enrich_from_matched_official_pdf
                            enrich_from_matched_official_pdf(a,official)
                            append_pdf_analysis(official.source_path, a, output_pdf)
                            a.metadata["official_pdf_visual_source"] = official.source_path.name
                            a.metadata["official_pdf_pairing_reason"] = reason
                        else:
                            app_modern.generate_pdf(a, output_pdf)
                            a.metadata["official_pdf_pairing_reason"] = reason
                    generated_pdfs.append(output_pdf)
                    self.messages.put(("pdf_done", idx, len(results), a.reference, output_pdf))
                except Exception as exc:
                    errors.append((a.source_path.name, f"PDF generation: {exc}"))
                    self.messages.put(("pdf_error", idx, len(results), a.reference, str(exc)))

        guard()
        self.messages.put(("batch_stage",95,"Assembling complete engineering Excel",
                           f"{len(results)} physical sounding(s); repeated points clearly labeled"))
        excel_path = app_modern_v2.timestamped_excel_path(out)
        # One deliverable: combine calculated CPTs, all raw points, both
        # georeferenced map views, optional XLSB reference and foundation
        # results, Pre/Post changes, coordinate exceptions and QA.
        original=getattr(self,"original_model_path",None)
        foundation=getattr(self,"foundation_reference_path",None)
        foundation_xlsx=foundation if foundation and Path(foundation).suffix.lower()==".xlsx" else None
        # Atomic publish: never expose a half-written workbook as 'Open Excel'.
        pending=excel_path.with_name(excel_path.stem+".partial.xlsx")
        try:
            reporting_export_v2.export_excel(
                results,pending,errors=errors,source_audit=audit_rows,
                original_xlsb=original,foundation_xlsx=foundation_xlsx,
                site_boundary=getattr(self,"site_boundary",None),
                comparison_result=getattr(self,"compare_result",None),
                isolated_inputs=self.get_isolated_inputs() if hasattr(self,"get_isolated_inputs") else None)
            guard()
            pending.replace(excel_path)
            excel=excel_path
        finally:
            if pending.exists():
                pending.unlink(missing_ok=True)
        # Publish the *same fully interactive* Plotly/SVG soil atlas that is
        # available from Site Map, next to the one consolidated Excel workbook.
        # Do not silently substitute a scatter/PNG for the layer explorer.
        # A separate local HTML is needed: Excel cannot execute an offline
        # interactive WebGL/SVG application inside a worksheet.
        self._latest_atlas_path = None
        try:
            from engineering_geo_atlas import export_geo_atlas
            from engineering_geo_explorer import spatial_points
            observed, excluded = spatial_points(results)
            if observed:
                atlas = out / "CPT_Interactive_2D_3D_Atlas.html"
                export_geo_atlas(results, atlas,
                    boundary=getattr(self,"site_boundary",None),
                    warning_m=float(self.risk_watch.get()) if hasattr(self,"risk_watch") else .10,
                    high_m=float(self.risk_high.get()) if hasattr(self,"risk_high") else .30)
                if atlas.exists() and atlas.stat().st_size > 100000:
                    self._latest_atlas_path=atlas
                    self.messages.put(("batch_stage",99,
                        "Interactive soil atlas ready",
                        f"Measured CPT layers, 2D soil colors, 3D scene: {len(observed)} location(s)"))
                else:
                    errors.append(("Interactive soil atlas","Generated HTML was incomplete"))
        except Exception as exc:
            errors.append(("Interactive soil atlas",str(exc)))
        self.messages.put(("done", out, pdfs if make_pdfs else None, excel, results, errors))


if __name__ == "__main__":
    PDFEnabledCPTApp().mainloop()

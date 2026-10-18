from __future__ import annotations

import os
import math
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tkinter import filedialog

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
    paths = [p for p in Path(folder).rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
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
        newest = max(pool, key=_candidate_rank)
        conclusive = [a for a in pool if a.status in CONCLUSIVE_STATUSES]

        if newest.status in CONCLUSIVE_STATUSES:
            selected = newest
            reason = f"Selected highest {source_class} revision ({source_revision(newest.source_path)}); analysis is conclusive."
        elif conclusive:
            selected = max(conclusive, key=_candidate_rank)
            reason = (
                f"Newest {source_class} revision {source_revision(newest.source_path)} is REVIEW; "
                f"selected highest conclusive revision {source_revision(selected.source_path)}."
            )
        else:
            selected = newest
            reason = f"All available {source_class} revisions require REVIEW; newest revision retained without guessing."

        signatures = {_result_signature(a) for a in conclusive}
        conflict = len(signatures) > 1
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
            reason += (" SOURCE CONFLICT: revisions disagree in final engineering"
                       " classification, measured coordinates, or ground elevation."
                       " No verified project value was selected; manual reconciliation required.")
            selected.status="REVIEW"
            selected.final_interval=None
            selected.verification_note=(str(selected.verification_note or "")+
                 " Project source revisions conflict. Resolve original test identity,"
                 " survey coordinates, ground datum and selected report before approval.")

        original_ref = selected.reference
        selected.metadata = dict(selected.metadata)
        selected.metadata.update({
            "source_report_reference": original_ref,
            "canonical_reference": family,
            "source_revision": source_revision(selected.source_path),
            "source_selection_reason": reason,
            "source_family_count": len(family_sources.get(family, items)),
            "source_revision_conflict": conflict,
            "source_spatial_conflict": spatial_conflict,
            "source_datum_conflict": datum_conflict,
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
            selection_reason = f"Superseded by {selected.source_path.name}."
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
                ("Supported CPT files", "*.GEF *.gef *.GFF *.gff *.PDF *.pdf"),
                ("Raw CPT files", "*.GEF *.gef *.GFF *.gff"),
                ("CPT PDF reports", "*.PDF *.pdf"),
                ("All files", "*.*"),
            ],
        )
        if chosen:
            self.files = collect_candidate_sources(Path(v) for v in chosen)
            self.skipped_duplicate_sources = []
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
        pdfs = out / "PDFs"
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

        # Revision-aware project collapse: one final result per CPT location.
        results, audit_rows = select_project_results(candidate_results, self.files, error_map)
        self.source_audit = audit_rows

        # 2D and 3D project maps are now embedded inside ONE comprehensive XLSX.
        # Explicit Save PNG remains available from the interactive Site Map tab.

        if make_pdfs:
            for idx, a in enumerate(results, 1):
                try:
                    output_pdf = app_modern.unique_pdf_path(pdfs, a.reference)
                    if a.source_path.suffix.lower() == ".pdf":
                        append_pdf_analysis(a.source_path, a, output_pdf)
                    else:
                        from engineering_report_sources import choose_official_pdf
                        official, reason = choose_official_pdf(a, candidate_results)
                        if official is not None:
                            # Use RAW source for every calculation and the verified
                            # official PDF solely for its original reference graphics.
                            append_pdf_analysis(official.source_path, a, output_pdf)
                            a.metadata["official_pdf_visual_source"] = official.source_path.name
                            a.metadata["official_pdf_pairing_reason"] = reason
                        else:
                            app_modern.generate_pdf(a, output_pdf)
                            a.metadata["official_pdf_pairing_reason"] = reason
                    self.messages.put(("pdf_done", idx, len(results), a.reference, output_pdf))
                except Exception as exc:
                    errors.append((a.source_path.name, f"PDF generation: {exc}"))
                    self.messages.put(("pdf_error", idx, len(results), a.reference, str(exc)))

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
                comparison_result=getattr(self,"compare_result",None))
            pending.replace(excel_path)
            excel=excel_path
        finally:
            if pending.exists():
                pending.unlink(missing_ok=True)
        # Preserve ONE workbook per run. The UI already knows the exact
        # completed timestamped path; duplicating it as *_Latest.xlsx
        # created an unnecessary second Excel deliverable.
        self.messages.put(("done", out, pdfs if make_pdfs else None, excel, results, errors))


if __name__ == "__main__":
    PDFEnabledCPTApp().mainloop()

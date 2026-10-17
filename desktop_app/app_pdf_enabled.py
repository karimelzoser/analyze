from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from tkinter import filedialog

import app_modern
import app_modern_v2
from pdf_analysis import analyze_pdf, append_pdf_analysis


SUPPORTED_EXTENSIONS = {".gef", ".gff", ".pdf"}
RAW_EXTENSIONS = {".gef", ".gff"}


def source_reference_key(path: str | Path) -> str:
    p = Path(path)
    stem = re.sub(r"\(\d+\)$", "", p.stem, flags=re.I)
    stem = re.sub(r"^P\d+_", "", stem, flags=re.I)
    match = re.search(r"(CPT-[A-Za-z0-9_.\-]+)", stem, flags=re.I)
    return (match.group(1) if match else stem).upper()


def prefer_best_sources(paths) -> tuple[list[Path], list[Path]]:
    """Prefer raw GEF/GFF over a PDF of the same CPT reference."""
    best: dict[str, Path] = {}
    skipped: list[Path] = []

    def rank(p: Path):
        ext = p.suffix.lower()
        raw_rank = 0 if ext in RAW_EXTENSIONS else 1
        copy_rank = 1 if re.search(r"\(\d+\)$", p.stem) else 0
        return (raw_rank, copy_rank, len(p.name), p.name.lower())

    for p in sorted({Path(x) for x in paths}, key=lambda q: app_modern.natural_ref_key(q.name)):
        key = source_reference_key(p)
        current = best.get(key)
        if current is None:
            best[key] = p
            continue
        if rank(p) < rank(current):
            skipped.append(current)
            best[key] = p
        else:
            skipped.append(p)

    selected = sorted(best.values(), key=lambda q: app_modern.natural_ref_key(q.stem))
    return selected, skipped


def collect_project_folder(folder: str | Path) -> tuple[list[Path], list[Path]]:
    paths = [p for p in Path(folder).rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    return prefer_best_sources(paths)


def analyze_source(path: Path, gamma: float, wt: float):
    if path.suffix.lower() == ".pdf":
        return analyze_pdf(path)
    return app_modern.analyze_gef(path, gamma_soil=gamma, water_table_depth=wt)


class PDFEnabledCPTApp(app_modern_v2.ProfessionalModernCPTApp):
    """Production desktop shell supporting GEF, GFF and CPT PDF reports."""

    def __init__(self):
        self.skipped_duplicate_sources: list[Path] = []
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
            self.files, self.skipped_duplicate_sources = prefer_best_sources(Path(v) for v in chosen)
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
        skipped = len(self.skipped_duplicate_sources)
        suffix = f" • {skipped} duplicate PDF/copy source(s) skipped" if skipped else ""
        self.status_var.set(
            f"Loaded {len(self.files)} CPT source(s): {raw} raw GEF/GFF, {pdf} PDF{suffix}. Raw data is preferred when both exist."
        )

    def clear(self):
        self.skipped_duplicate_sources = []
        super().clear()
        self.status_var.set("Ready — select GEF/GFF/PDF files or a project folder.")

    def _worker(self, out: Path, gamma: float, wt: float, make_pdfs: bool):
        out.mkdir(parents=True, exist_ok=True)
        pdfs = out / "PDFs"
        if make_pdfs:
            pdfs.mkdir(parents=True, exist_ok=True)

        results = []
        errors: list[tuple[str, str]] = []
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
                    pool.submit(app_modern.analyze_gef, p, gamma_soil=gamma, water_table_depth=wt): p
                    for p in raw_sources
                }
                for future in as_completed(futures):
                    p = futures[future]
                    completed += 1
                    try:
                        a = future.result()
                        results.append(a)
                        self.messages.put(("analysis_row", completed, total, a))
                    except Exception as exc:
                        errors.append((p.name, str(exc)))
                        self.messages.put(("analysis_error", completed, total, p, str(exc)))

        for p in pdf_sources:
            completed += 1
            try:
                a = analyze_pdf(p)
                results.append(a)
                self.messages.put(("analysis_row", completed, total, a))
            except Exception as exc:
                errors.append((p.name, str(exc)))
                self.messages.put(("analysis_error", completed, total, p, str(exc)))

        results.sort(key=lambda a: app_modern.natural_ref_key(a.reference))

        if make_pdfs:
            for idx, a in enumerate(results, 1):
                try:
                    output_pdf = app_modern.unique_pdf_path(pdfs, a.reference)
                    if a.source_path.suffix.lower() == ".pdf":
                        append_pdf_analysis(a.source_path, a, output_pdf)
                    else:
                        app_modern.generate_pdf(a, output_pdf)
                    self.messages.put(("pdf_done", idx, len(results), a.reference, output_pdf))
                except Exception as exc:
                    errors.append((a.source_path.name, f"PDF generation: {exc}"))
                    self.messages.put(("pdf_error", idx, len(results), a.reference, str(exc)))

        excel_path = app_modern_v2.timestamped_excel_path(out)
        excel = app_modern.export_excel(results, excel_path, errors=errors)
        app_modern_v2.update_latest_excel_alias(Path(excel), out)
        self.messages.put(("done", out, pdfs if make_pdfs else None, excel, results, errors))


if __name__ == "__main__":
    PDFEnabledCPTApp().mainloop()

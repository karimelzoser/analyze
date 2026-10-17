from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from tkinter import messagebox

import app_modern


SECONDARY_BG = "#E8F0FE"
SECONDARY_FG = "#174EA6"
SECONDARY_BORDER = "#A8C7FA"
SECONDARY_HOVER = "#D2E3FC"
PRIMARY_BG = app_modern.PALETTE["accent"]
PRIMARY_HOVER = app_modern.PALETTE["accent_hover"]
DISABLED_BG = "#EEF2F7"
DISABLED_FG = "#94A3B8"


def latest_excel_path(output_dir: Path | None, preferred: Path | None = None) -> Path | None:
    """Resolve the newest completed CPT workbook in the current output folder.

    The application writes a uniquely named workbook for every run. This avoids
    Excel showing a workbook that was already open from a previous run and also
    preserves a traceable run history. The preferred path is included when it
    exists, but modification time decides which workbook is newest.
    """
    candidates: list[Path] = []
    if preferred is not None:
        p = Path(preferred)
        if p.exists() and p.is_file() and p.suffix.lower() == ".xlsx" and not p.name.startswith("~$"):
            candidates.append(p)

    if output_dir is not None:
        root = Path(output_dir)
        if root.exists():
            for p in root.glob("CPT_Silt_Analysis*.xlsx"):
                if p.is_file() and not p.name.startswith("~$"):
                    candidates.append(p)

    if not candidates:
        return None

    # De-duplicate by resolved path and pick the physically newest workbook.
    unique: dict[str, Path] = {}
    for p in candidates:
        try:
            key = str(p.resolve()).lower()
        except Exception:
            key = str(p.absolute()).lower()
        unique[key] = p
    return max(unique.values(), key=lambda p: p.stat().st_mtime_ns)


def timestamped_excel_path(output_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    return Path(output_dir) / f"CPT_Silt_Analysis_{stamp}.xlsx"


def update_latest_excel_alias(source: Path, output_dir: Path) -> Path | None:
    """Best-effort stable copy for users who prefer a constant filename.

    If the stable workbook is already open in Excel, Windows can lock it. That
    must never invalidate a successful analysis, so failures here are ignored;
    the app always keeps and opens the timestamped source workbook.
    """
    target = Path(output_dir) / "CPT_Silt_Analysis_Latest.xlsx"
    try:
        shutil.copy2(source, target)
        return target
    except Exception:
        return None


class ProfessionalModernCPTApp(app_modern.ModernCPTApp):
    """Modern production shell with clearer actions and reliable run outputs."""

    def __init__(self):
        super().__init__()
        self.title("CPT Analyzer Professional")
        self.after_idle(self._maximize_startup)
        self._polish_action_labels()

    # ---------- button system ----------
    def _btn(self, parent, text, command, *, primary=False, width=None, state="normal"):
        """Create an unmistakably clickable action button.

        Secondary actions intentionally use a filled light-blue surface instead
        of white-on-white so they read as buttons on every tab and monitor.
        """
        bg = PRIMARY_BG if primary else SECONDARY_BG
        fg = "#FFFFFF" if primary else SECONDARY_FG
        hover = PRIMARY_HOVER if primary else SECONDARY_HOVER
        border = PRIMARY_BG if primary else SECONDARY_BORDER

        b = app_modern.tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=hover,
            activeforeground=fg,
            disabledforeground=DISABLED_FG,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Segoe UI Semibold", 9),
            padx=17,
            pady=10,
            highlightthickness=1,
            highlightbackground=border,
            highlightcolor=border,
            takefocus=True,
            state=state,
        )
        if width:
            b.configure(width=width)

        def on_enter(_event):
            if str(b.cget("state")) != "disabled":
                b.configure(bg=hover)

        def on_leave(_event):
            if str(b.cget("state")) != "disabled":
                b.configure(bg=bg)

        b.bind("<Enter>", on_enter)
        b.bind("<Leave>", on_leave)
        b.bind("<FocusIn>", on_enter)
        b.bind("<FocusOut>", on_leave)
        return b

    def _polish_action_labels(self):
        # Short, consistent action wording is easier to scan than mixed labels.
        mapping = [
            (getattr(self, "open_selected_btn", None), "OPEN SELECTED PDF"),
            (getattr(self, "open_pdfs_btn", None), "OPEN PDF FOLDER"),
            (getattr(self, "open_excel_btn", None), "OPEN LATEST EXCEL"),
            (getattr(self, "open_output_btn", None), "OPEN OUTPUT FOLDER"),
        ]
        for button, text in mapping:
            if button is not None:
                button.configure(text=text)

    # ---------- startup window ----------
    def _maximize_startup(self):
        """Open maximized while keeping normal Windows taskbar behaviour."""
        try:
            self.update_idletasks()
            if os.name == "nt":
                self.state("zoomed")
            else:
                self.attributes("-zoomed", True)
        except Exception:
            try:
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                self.geometry(f"{sw}x{sh}+0+0")
            except Exception:
                pass

    # ---------- batch output ----------
    def _worker(self, out: Path, gamma: float, wt: float, make_pdfs: bool):
        out.mkdir(parents=True, exist_ok=True)
        pdfs = out / "PDFs"
        if make_pdfs:
            pdfs.mkdir(parents=True, exist_ok=True)

        results = []
        errors: list[tuple[str, str]] = []
        total = len(self.files)
        workers = max(1, min(8, os.cpu_count() or 4, total))

        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="cpt") as pool:
            futures = {
                pool.submit(app_modern.analyze_gef, p, gamma_soil=gamma, water_table_depth=wt): p
                for p in self.files
            }
            completed = 0
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

        results.sort(key=lambda a: app_modern.natural_ref_key(a.reference))

        if make_pdfs:
            for idx, a in enumerate(results, 1):
                try:
                    pdf = app_modern.unique_pdf_path(pdfs, a.reference)
                    app_modern.generate_pdf(a, pdf)
                    self.messages.put(("pdf_done", idx, len(results), a.reference, pdf))
                except Exception as exc:
                    errors.append((a.source_path.name, f"PDF generation: {exc}"))
                    self.messages.put(("pdf_error", idx, len(results), a.reference, str(exc)))

        # A unique workbook per run guarantees that OPEN LATEST EXCEL opens the
        # just-created workbook, even if a previous workbook is still open.
        excel_path = timestamped_excel_path(out)
        excel = app_modern.export_excel(results, excel_path, errors=errors)
        update_latest_excel_alias(Path(excel), out)
        self.messages.put(("done", out, pdfs if make_pdfs else None, excel, results, errors))

    # ---------- output actions ----------
    def open_excel(self):
        newest = latest_excel_path(self.output_dir, self.excel_path)
        if newest is None:
            messagebox.showwarning("Excel unavailable", "No completed CPT analysis workbook was found in the current output folder.")
            return

        self.excel_path = newest
        if not app_modern.open_external_path(newest):
            messagebox.showwarning(
                "Excel unavailable",
                f"The latest workbook exists but Windows could not open it.\n\n{newest}",
            )
            return
        self.status_var.set(f"Opened latest Excel workbook: {newest.name}")

    def _set_output_buttons(self, enabled: bool):
        # Re-resolve the newest workbook before deciding whether Excel is ready.
        if enabled:
            newest = latest_excel_path(self.output_dir, self.excel_path)
            if newest is not None:
                self.excel_path = newest
        super()._set_output_buttons(enabled)


if __name__ == "__main__":
    ProfessionalModernCPTApp().mainloop()

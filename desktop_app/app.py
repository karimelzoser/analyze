from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import numpy as np
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from cpt_core import analyze_gef, natural_ref_key, summarize_analyses
from reporting import export_excel, generate_pdf


def open_external_path(path: Path) -> bool:
    path = Path(path)
    if not path.exists():
        return False
    try:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True
    except Exception:
        return False


def default_output_for_files(files):
    if not files:
        return None
    parents = {Path(f).parent.resolve() for f in files}
    base = next(iter(parents)) if len(parents) == 1 else Path(files[0]).parent
    return base / "CPT_Output"


class CPTApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CPT Silt Analyzer")
        self.geometry("1280x820")
        self.minsize(1020, 680)
        self.files = []
        self.results = []
        self.messages = queue.Queue()
        self.output_dir: Path | None = None
        self.excel_path: Path | None = None
        self.pdf_dir: Path | None = None
        self._build_ui()
        self.after(100, self._poll_messages)

    def _build_ui(self):
        ttk.Label(self, text="CPT GEF/GFF Analysis", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=20, pady=(16, 2))
        ttk.Label(self, text="Analyze raw CPT files, generate reference-style PDFs, export Excel, and review full-project layer charts.").pack(anchor="w", padx=20, pady=(0, 10))

        select = ttk.Frame(self); select.pack(fill="x", padx=20)
        ttk.Button(select, text="Select Files", command=self.select_files).pack(side="left")
        ttk.Button(select, text="Select Folder", command=self.select_folder).pack(side="left", padx=6)
        ttk.Button(select, text="Clear", command=self.clear).pack(side="left")
        self.file_label = ttk.Label(select, text="0 files selected"); self.file_label.pack(side="left", padx=14)

        output = ttk.Frame(self); output.pack(fill="x", padx=20, pady=(8, 0))
        ttk.Label(output, text="Output:").pack(side="left")
        self.output_var = tk.StringVar(value="")
        ttk.Entry(output, textvariable=self.output_var).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(output, text="Choose Output Folder", command=self.choose_output).pack(side="left")

        settings = ttk.LabelFrame(self, text="Engineering Settings"); settings.pack(fill="x", padx=20, pady=10)
        ttk.Label(settings, text="Soil unit weight (kN/m3)").grid(row=0, column=0, padx=8, pady=8, sticky="w")
        self.gamma_var = tk.StringVar(value="18.0"); ttk.Entry(settings, textvariable=self.gamma_var, width=9).grid(row=0, column=1)
        ttk.Label(settings, text="Groundwater depth BGL (m)").grid(row=0, column=2, padx=(20, 8), pady=8, sticky="w")
        self.wt_var = tk.StringVar(value="0.0"); ttk.Entry(settings, textvariable=self.wt_var, width=9).grid(row=0, column=3)
        ttk.Label(settings, text="Ic 2.60 | interpolated crossing | terminal sensor-dropout protection | double verification", foreground="#555").grid(row=0, column=4, padx=20, sticky="w")

        actions = ttk.Frame(self); actions.pack(fill="x", padx=20, pady=(0, 8))
        self.analyze_btn = ttk.Button(actions, text="START ANALYSIS", command=self.analyze_all); self.analyze_btn.pack(side="left")
        self.open_pdfs_btn = ttk.Button(actions, text="Open PDFs", command=self.open_pdfs, state="disabled"); self.open_pdfs_btn.pack(side="left", padx=(8, 0))
        self.open_excel_btn = ttk.Button(actions, text="Open Excel Sheet", command=self.open_excel, state="disabled"); self.open_excel_btn.pack(side="left", padx=(8, 0))
        self.open_output_btn = ttk.Button(actions, text="Open Output Folder", command=self.open_output, state="disabled"); self.open_output_btn.pack(side="left", padx=(8, 0))
        self.progress = ttk.Progressbar(actions, mode="determinate"); self.progress.pack(side="left", fill="x", expand=True, padx=12)
        self.progress_label = ttk.Label(actions, text="Ready"); self.progress_label.pack(side="right")

        self.summary_var = tk.StringVar(value="Maximum silt thickness: -")
        ttk.Label(self, textvariable=self.summary_var, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20, pady=(0, 6))

        notebook = ttk.Notebook(self); notebook.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        results_tab, chart_tab = ttk.Frame(notebook), ttk.Frame(notebook)
        notebook.add(results_tab, text="Results"); notebook.add(chart_tab, text="Full Analysis Chart")

        cols = ("ref", "sand", "start", "depth", "status")
        self.tree = ttk.Treeview(results_tab, columns=cols, show="headings")
        for key, text, width in [("ref","CPT Reference",280),("sand","Sand Thickness",140),("start","Silt Start",130),("depth","Silt Depth",130),("status","Status",150)]:
            self.tree.heading(key, text=text); self.tree.column(key, width=width, anchor="center" if key != "ref" else "w")
        scroll = ttk.Scrollbar(results_tab, orient="vertical", command=self.tree.yview); self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self._open_selected_pdf)

        controls = ttk.Frame(chart_tab); controls.pack(fill="x", pady=4)
        self.show_silt_thickness = tk.BooleanVar(value=True); self.show_sand_thickness = tk.BooleanVar(value=True); self.show_silt_start = tk.BooleanVar(value=False)
        for text, var in [("Silt thickness", self.show_silt_thickness), ("Sand thickness", self.show_sand_thickness), ("Silt start", self.show_silt_start)]:
            ttk.Checkbutton(controls, text=text, variable=var, command=self._refresh_chart).pack(side="left", padx=8)
        ttk.Label(controls, text="Use the toolbar to zoom/pan large batches.").pack(side="right", padx=8)
        self.chart_fig = Figure(figsize=(10, 5), dpi=100); self.chart_ax = self.chart_fig.add_subplot(111)
        self.chart_canvas = FigureCanvasTkAgg(self.chart_fig, master=chart_tab); self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)
        self.chart_toolbar = NavigationToolbar2Tk(self.chart_canvas, chart_tab, pack_toolbar=False); self.chart_toolbar.update(); self.chart_toolbar.pack(fill="x")
        self._refresh_chart()

        self.status_var = tk.StringVar(value="Select one or more GEF/GFF files, or select a folder.")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w").pack(fill="x", side="bottom")

    def _set_default_output(self):
        out = default_output_for_files(self.files)
        if out:
            self.output_dir = out; self.output_var.set(str(out))

    def select_files(self):
        chosen = filedialog.askopenfilenames(title="Select GEF/GFF files", filetypes=[("GEF/GFF files", "*.GEF *.gef *.GFF *.gff"), ("All files", "*.*")])
        if chosen:
            self.files = sorted({Path(x) for x in chosen}, key=lambda p: natural_ref_key(p.stem)); self._set_default_output(); self._refresh_file_label()

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing GEF/GFF files")
        if folder:
            p = Path(folder); files = [x for x in p.rglob("*") if x.is_file() and x.suffix.lower() in {".gef", ".gff"}]
            self.files = sorted(set(files), key=lambda x: natural_ref_key(x.stem)); self.output_dir = p / "CPT_Output"; self.output_var.set(str(self.output_dir)); self._refresh_file_label()

    def choose_output(self):
        folder = filedialog.askdirectory(title="Choose output folder")
        if folder:
            self.output_dir = Path(folder); self.output_var.set(folder)

    def _refresh_file_label(self):
        self.file_label.config(text=f"{len(self.files)} files selected"); self.status_var.set(f"Loaded {len(self.files)} CPT file(s). Press START ANALYSIS.")

    def clear(self):
        self.files = []; self.results = []; self.output_dir = self.excel_path = self.pdf_dir = None; self.output_var.set("")
        for item in self.tree.get_children(): self.tree.delete(item)
        self.progress["value"] = 0; self.progress_label.config(text="Ready")
        self.open_pdfs_btn.config(state="disabled"); self.open_excel_btn.config(state="disabled"); self.open_output_btn.config(state="disabled")
        self.summary_var.set("Maximum silt thickness: -"); self._refresh_chart(); self._refresh_file_label()

    def analyze_all(self):
        if not self.files:
            messagebox.showwarning("No files", "Select one or more GEF/GFF files, or select a folder first."); return
        out_text = self.output_var.get().strip()
        if not out_text:
            self._set_default_output(); out_text = self.output_var.get().strip()
        try:
            gamma, wt = float(self.gamma_var.get()), float(self.wt_var.get())
        except ValueError:
            messagebox.showerror("Invalid settings", "Unit weight and groundwater depth must be numeric."); return
        out = Path(out_text); self.output_dir = out; self.analyze_btn.config(state="disabled")
        for item in self.tree.get_children(): self.tree.delete(item)
        self.results = []; self.progress["maximum"] = len(self.files); self.progress["value"] = 0
        self.open_pdfs_btn.config(state="disabled"); self.open_excel_btn.config(state="disabled"); self.open_output_btn.config(state="disabled")
        threading.Thread(target=self._worker, args=(out, gamma, wt), daemon=True).start()

    def _worker(self, out: Path, gamma: float, wt: float):
        pdf_dir = out / "PDFs"; pdf_dir.mkdir(parents=True, exist_ok=True); results = []
        for i, path in enumerate(self.files, 1):
            try:
                a = analyze_gef(path, gamma_soil=gamma, water_table_depth=wt); pdf_path = generate_pdf(a, pdf_dir / f"{a.reference}.pdf"); results.append(a)
                self.messages.put(("row", i, len(self.files), a, pdf_path))
            except Exception as exc:
                self.messages.put(("error_row", i, len(self.files), path, str(exc)))
        excel = export_excel(results, out / "CPT_Silt_Analysis.xlsx"); self.messages.put(("done", out, pdf_dir, excel, results))

    def _poll_messages(self):
        try:
            while True:
                msg = self.messages.get_nowait(); kind = msg[0]
                if kind == "row":
                    _, i, total, a, _ = msg
                    sand = "REVIEW" if a.sand_layer_thickness is None else f"{a.sand_layer_thickness:.2f}"
                    start = "NO SILT" if a.status == "NO SILT" else (f"{a.final_interval.start:.2f}" if a.final_interval else "REVIEW")
                    thickness = "0.00" if a.status == "NO SILT" else (f"{a.final_interval.thickness:.2f}" if a.final_interval else "-")
                    self.tree.insert("", "end", values=(a.reference, sand, start, thickness, a.status)); self.progress["value"] = i; self.progress_label.config(text=f"{i} / {total}")
                    self.status_var.set(f"Analyzed {a.reference}: silt {start} / {thickness}")
                elif kind == "error_row":
                    _, i, total, path, err = msg; self.tree.insert("", "end", values=(path.stem, "-", "REVIEW", "-", "ERROR")); self.progress["value"] = i; self.progress_label.config(text=f"{i} / {total}"); self.status_var.set(f"Could not process {path.name}: {err}")
                elif kind == "done":
                    _, out, pdf_dir, excel, results = msg; self.results = sorted(results, key=lambda a: natural_ref_key(a.reference)); self.output_dir, self.pdf_dir, self.excel_path = out, pdf_dir, excel
                    self.analyze_btn.config(state="normal"); self.open_output_btn.config(state="normal" if out.exists() else "disabled"); self.open_pdfs_btn.config(state="normal" if pdf_dir.exists() else "disabled"); self.open_excel_btn.config(state="normal" if excel.exists() else "disabled")
                    s = summarize_analyses(self.results)
                    if s["max_silt_thickness"] is None: self.summary_var.set("Maximum silt thickness: none detected")
                    else: self.summary_var.set(f"Maximum silt thickness: {s['max_silt_thickness']:.2f} m at {', '.join(s['max_silt_refs'])}")
                    self._refresh_chart(); self.status_var.set(f"Finished. {len(results)} CPT(s). Excel: {excel} | PDFs: {pdf_dir}")
                    messagebox.showinfo("Analysis complete", f"Finished {len(results)} CPT file(s).\n\nPDFs:\n{pdf_dir}\n\nExcel:\n{excel}")
        except queue.Empty:
            pass
        self.after(100, self._poll_messages)

    def _refresh_chart(self):
        ax = self.chart_ax; ax.clear()
        if not self.results:
            ax.text(.5,.5,"Run an analysis to display the full-project chart.",ha="center",va="center",transform=ax.transAxes); ax.set_axis_off(); self.chart_canvas.draw_idle(); return
        ax.set_axis_on(); refs=[a.reference for a in self.results]; x=list(range(len(refs)))
        if self.show_silt_thickness.get(): ax.plot(x,[0.0 if a.status=="NO SILT" else (a.final_interval.thickness if a.final_interval else np.nan) for a in self.results],marker=".",ms=3,lw=1,label="Silt thickness")
        if self.show_sand_thickness.get(): ax.plot(x,[a.sand_layer_thickness if a.sand_layer_thickness is not None else np.nan for a in self.results],lw=1,label="Sand thickness")
        if self.show_silt_start.get(): ax.plot(x,[a.final_interval.start if a.final_interval else np.nan for a in self.results],lw=1,label="Silt start")
        step=max(1,len(refs)//18); ticks=x[::step]; ax.set_xticks(ticks); ax.set_xticklabels([refs[i] for i in ticks],rotation=55,ha="right",fontsize=7)
        ax.set_ylabel("Depth / thickness (m)"); ax.set_title("Full CPT Analysis"); ax.grid(True,alpha=.25)
        if ax.lines: ax.legend(loc="best")
        self.chart_fig.tight_layout(); self.chart_canvas.draw_idle()

    def open_pdfs(self):
        if not self.pdf_dir or not open_external_path(self.pdf_dir): messagebox.showwarning("PDF folder unavailable", "Run the analysis first or check the output folder.")

    def open_excel(self):
        if not self.excel_path or not open_external_path(self.excel_path): messagebox.showwarning("Excel unavailable", "Run the analysis first or check the output folder.")

    def open_output(self):
        if not self.output_dir or not open_external_path(self.output_dir): messagebox.showwarning("Output unavailable", "Run the analysis first or check the output folder.")

    def _open_selected_pdf(self, _event=None):
        selected = self.tree.selection()
        if not selected or not self.pdf_dir: return
        values = self.tree.item(selected[0], "values")
        if not values: return
        pdf = self.pdf_dir / f"{values[0]}.pdf"
        if not open_external_path(pdf): messagebox.showwarning("PDF unavailable", f"PDF not found:\n{pdf}")


if __name__ == "__main__":
    CPTApp().mainloop()

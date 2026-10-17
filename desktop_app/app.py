from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from cpt_core import analyze_gef
from reporting import export_excel, generate_pdf


class CPTApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CPT Silt Analyzer")
        self.geometry("1040x690")
        self.minsize(900, 600)
        self.files = []
        self.results = []
        self.messages = queue.Queue()
        self._build_ui()
        self.after(100, self._poll_messages)

    def _build_ui(self):
        title = ttk.Label(self, text="CPT GEF/GFF Analysis", font=("Segoe UI", 18, "bold"))
        title.pack(anchor="w", padx=24, pady=(20, 4))
        ttk.Label(
            self,
            text="Upload raw CPT GEF/GFF files, generate individual PDF reports, and export the 4-column silt analysis Excel sheet.",
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=24, pady=(0, 16))

        top = ttk.Frame(self)
        top.pack(fill="x", padx=24)
        ttk.Button(top, text="Select Files", command=self.select_files).pack(side="left")
        ttk.Button(top, text="Select Folder", command=self.select_folder).pack(side="left", padx=(8, 0))
        ttk.Button(top, text="Clear", command=self.clear).pack(side="left", padx=(8, 0))
        self.file_label = ttk.Label(top, text="0 files selected")
        self.file_label.pack(side="left", padx=18)

        settings = ttk.LabelFrame(self, text="Engineering Settings")
        settings.pack(fill="x", padx=24, pady=14)
        ttk.Label(settings, text="Soil unit weight (kN/m3)").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.gamma_var = tk.StringVar(value="18.0")
        ttk.Entry(settings, textvariable=self.gamma_var, width=10).grid(row=0, column=1, padx=4)
        ttk.Label(settings, text="Groundwater depth BGL (m)").grid(row=0, column=2, padx=(28, 10), pady=10, sticky="w")
        self.wt_var = tk.StringVar(value="0.0")
        ttk.Entry(settings, textvariable=self.wt_var, width=10).grid(row=0, column=3, padx=4)
        ttk.Label(settings, text="Silt rule: deepest sustained Ic >= 2.60; double verification", foreground="#555555").grid(row=0, column=4, padx=28, sticky="w")

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=24, pady=(0, 12))
        self.analyze_btn = ttk.Button(actions, text="ANALYZE ALL", command=self.analyze_all)
        self.analyze_btn.pack(side="left")
        self.progress = ttk.Progressbar(actions, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=16)
        self.progress_label = ttk.Label(actions, text="Ready")
        self.progress_label.pack(side="right")

        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        cols = ("ref", "start", "depth", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.tree.heading("ref", text="CPT Reference")
        self.tree.heading("start", text="Silt Start")
        self.tree.heading("depth", text="Silt Depth")
        self.tree.heading("status", text="Status")
        self.tree.column("ref", width=300)
        self.tree.column("start", width=150, anchor="center")
        self.tree.column("depth", width=150, anchor="center")
        self.tree.column("status", width=160, anchor="center")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.status_var = tk.StringVar(value="Select GEF/GFF files or a folder to begin.")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w").pack(fill="x", side="bottom")

    def select_files(self):
        chosen = filedialog.askopenfilenames(
            title="Select GEF/GFF files",
            filetypes=[("GEF/GFF files", "*.GEF *.gef *.GFF *.gff"), ("All files", "*.*")],
        )
        if chosen:
            self.files = [Path(x) for x in chosen]
            self._refresh_file_label()

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select folder containing GEF/GFF files")
        if folder:
            p = Path(folder)
            files = list(p.rglob("*.GEF")) + list(p.rglob("*.gef")) + list(p.rglob("*.GFF")) + list(p.rglob("*.gff"))
            self.files = sorted(set(files), key=lambda x: x.name.lower())
            self._refresh_file_label()

    def _refresh_file_label(self):
        self.file_label.config(text=f"{len(self.files)} files selected")
        self.status_var.set(f"Loaded {len(self.files)} raw CPT files.")

    def clear(self):
        self.files = []
        self.results = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.progress["value"] = 0
        self.progress_label.config(text="Ready")
        self._refresh_file_label()

    def analyze_all(self):
        if not self.files:
            messagebox.showwarning("No files", "Please select GEF/GFF files first.")
            return
        out = filedialog.askdirectory(title="Choose output folder")
        if not out:
            return
        try:
            gamma = float(self.gamma_var.get())
            wt = float(self.wt_var.get())
        except ValueError:
            messagebox.showerror("Invalid settings", "Unit weight and groundwater depth must be numbers.")
            return

        self.analyze_btn.config(state="disabled")
        self.results = []
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.progress["maximum"] = len(self.files)
        self.progress["value"] = 0
        worker = threading.Thread(target=self._worker, args=(Path(out), gamma, wt), daemon=True)
        worker.start()

    def _worker(self, out: Path, gamma: float, wt: float):
        pdf_dir = out / "PDFs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        results = []
        for i, path in enumerate(self.files, 1):
            try:
                a = analyze_gef(path, gamma_soil=gamma, water_table_depth=wt)
                generate_pdf(a, pdf_dir / f"{a.reference}.pdf")
                results.append(a)
                self.messages.put(("row", i, len(self.files), a, None))
            except Exception as exc:
                self.messages.put(("error_row", i, len(self.files), path, str(exc)))
        export_excel(results, out / "CPT_Silt_Analysis.xlsx")
        self.messages.put(("done", out, results))

    def _poll_messages(self):
        try:
            while True:
                msg = self.messages.get_nowait()
                kind = msg[0]
                if kind == "row":
                    _, i, total, a, _ = msg
                    start = "NO SILT" if a.status == "NO SILT" else (f"{a.final_interval.start:.2f}" if a.final_interval else "REVIEW")
                    thickness = "0.00" if a.status == "NO SILT" else (f"{a.final_interval.thickness:.2f}" if a.final_interval else "-")
                    self.tree.insert("", "end", values=(a.reference, start, thickness, a.status))
                    self.progress["value"] = i
                    self.progress_label.config(text=f"{i} / {total}")
                    self.status_var.set(f"Analyzed {a.reference}: {start} / {thickness}")
                elif kind == "error_row":
                    _, i, total, path, err = msg
                    self.tree.insert("", "end", values=(path.stem, "REVIEW", "-", "ERROR"))
                    self.progress["value"] = i
                    self.progress_label.config(text=f"{i} / {total}")
                    self.status_var.set(f"Could not process {path.name}: {err}")
                elif kind == "done":
                    _, out, results = msg
                    self.results = results
                    self.analyze_btn.config(state="normal")
                    self.status_var.set(f"Finished. Excel and PDFs saved in {out}")
                    messagebox.showinfo("Analysis complete", f"Finished {len(results)} CPT files.\n\nOutput folder:\n{out}")
        except queue.Empty:
            pass
        self.after(100, self._poll_messages)


if __name__ == "__main__":
    CPTApp().mainloop()

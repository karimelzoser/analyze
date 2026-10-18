from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from cpt_core import analyze_gef, natural_ref_key
from reporting_pro import analysis_record, export_excel
from reporting_pdf_ref_v2 import generate_pdf


CHART_TYPES = [
    "Line overview", "Grouped bars", "Layer profile", "Highest silt ranking",
    "Silt histogram", "Silt start vs thickness", "Coordinate map",
]
SORT_TYPES = ["CPT Reference", "Silt Thickness", "Sand Thickness", "Silt Start", "Test Depth"]
STATUS_TYPES = ["All", "VERIFIED", "NO SILT", "REVIEW"]

PALETTE = {
    "bg": "#F4F7FB", "surface": "#FFFFFF", "surface2": "#F8FAFC",
    "nav": "#0B1F33", "nav2": "#102A43", "accent": "#2563EB",
    "accent_hover": "#1D4ED8", "text": "#0F172A", "muted": "#64748B",
    "border": "#D8E1EC", "success": "#15803D", "warning": "#B45309",
    "danger": "#B91C1C", "cyan": "#0891B2", "purple": "#7C3AED",
}


def open_external_path(path: Path) -> bool:
    p = Path(path)
    if not p.exists():
        return False
    try:
        if os.name == "nt":
            os.startfile(str(p))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return True
    except Exception:
        return False


def collect_folder(folder: Path):
    return sorted(
        {p for p in Path(folder).rglob("*") if p.is_file() and p.suffix.lower() in {".gef", ".gff"}},
        key=lambda p: natural_ref_key(p.stem),
    )


def default_output(files):
    if not files:
        return None
    parents = {Path(f).parent.resolve() for f in files}
    base = next(iter(parents)) if len(parents) == 1 else Path(files[0]).parent
    return base / "CPT_Output"


def unique_pdf_path(folder: Path, ref: str) -> Path:
    p = folder / f"{ref}.pdf"
    n = 2
    while p.exists():
        p = folder / f"{ref}__{n}.pdf"
        n += 1
    return p


def sorted_filtered(results, status_filter="All", sort_by="CPT Reference", ascending=True, search=""):
    data = list(results)
    if status_filter != "All":
        data = [a for a in data if a.status == status_filter]
    search = search.strip().lower()
    if search:
        data = [a for a in data if search in a.reference.lower() or search in a.source_path.name.lower()]

    def key(a):
        r = analysis_record(a)
        if sort_by == "Silt Thickness":
            return (-1 if r["thickness"] is None else float(r["thickness"]), natural_ref_key(a.reference))
        if sort_by == "Sand Thickness":
            return (-1 if r["sand"] is None else float(r["sand"]), natural_ref_key(a.reference))
        if sort_by == "Silt Start":
            return (-1 if r["start_num"] is None else float(r["start_num"]), natural_ref_key(a.reference))
        if sort_by == "Test Depth":
            return (float(r["test_depth"]), natural_ref_key(a.reference))
        return natural_ref_key(a.reference)

    return sorted(data, key=key, reverse=not ascending)


class ModernCPTApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CPT Analyzer Professional")
        self.geometry("1380x850")
        # Windows may be 1024x768/125% DPI. Do not require a minimum window
        # larger than the physical screen; content adapts in tab workspaces.
        self.minsize(940, 615)
        self.configure(bg=PALETTE["bg"])

        self.files: list[Path] = []
        self.results = []
        self.errors = []
        self.messages: queue.Queue = queue.Queue()
        self.output_dir: Path | None = None
        self.pdf_dir: Path | None = None
        self.excel_path: Path | None = None
        self.pdf_by_ref: dict[str, list[Path]] = {}
        self.running = False

        self._configure_styles()
        self._build_shell()
        self.after(100, self._poll)

    # ---------- visual system ----------
    def _configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=PALETTE["bg"])
        style.configure("Surface.TFrame", background=PALETTE["surface"])
        style.configure("TLabel", background=PALETTE["bg"], foreground=PALETTE["text"], font=("Segoe UI", 9))
        style.configure("Surface.TLabel", background=PALETTE["surface"], foreground=PALETTE["text"], font=("Segoe UI", 9))
        style.configure("Muted.TLabel", background=PALETTE["surface"], foreground=PALETTE["muted"], font=("Segoe UI", 8))
        style.configure("Title.TLabel", background=PALETTE["bg"], foreground=PALETTE["text"], font=("Segoe UI Semibold", 20))
        style.configure("Subtitle.TLabel", background=PALETTE["bg"], foreground=PALETTE["muted"], font=("Segoe UI", 9))
        style.configure("CardTitle.TLabel", background=PALETTE["surface"], foreground=PALETTE["muted"], font=("Segoe UI Semibold", 8))
        style.configure("CardValue.TLabel", background=PALETTE["surface"], foreground=PALETTE["text"], font=("Segoe UI Semibold", 18))
        style.configure("Section.TLabel", background=PALETTE["surface"], foreground=PALETTE["text"], font=("Segoe UI Semibold", 11))
        style.configure("TEntry", fieldbackground="#FFFFFF", bordercolor=PALETTE["border"], lightcolor=PALETTE["border"], darkcolor=PALETTE["border"], padding=7)
        style.configure("TCombobox", fieldbackground="#FFFFFF", padding=6)
        style.configure("TCheckbutton", background=PALETTE["surface"], foreground=PALETTE["text"])
        style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF", foreground=PALETTE["text"], rowheight=30, borderwidth=0, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background="#EAF0F7", foreground="#334155", font=("Segoe UI Semibold", 8), relief="flat", padding=8)
        style.map("Treeview", background=[("selected", "#DBEAFE")], foreground=[("selected", "#0F172A")])
        style.configure("TNotebook", background=PALETTE["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background="#E7EDF5", foreground="#475569", padding=(18, 9), font=("Segoe UI Semibold", 9))
        style.map("TNotebook.Tab", background=[("selected", "#FFFFFF")], foreground=[("selected", PALETTE["accent"])])
        style.configure("Modern.Horizontal.TProgressbar", troughcolor="#E2E8F0", background=PALETTE["accent"], bordercolor="#E2E8F0", lightcolor=PALETTE["accent"], darkcolor=PALETTE["accent"], thickness=10)

    def _btn(self, parent, text, command, *, primary=False, width=None, state="normal"):
        bg = PALETTE["accent"] if primary else PALETTE["surface"]
        fg = "#FFFFFF" if primary else PALETTE["text"]
        active = PALETTE["accent_hover"] if primary else "#EEF2F7"
        b = tk.Button(
            parent, text=text, command=command, bg=bg, fg=fg, activebackground=active,
            activeforeground=fg, relief="flat", bd=0, cursor="hand2", font=("Segoe UI Semibold", 9),
            padx=15, pady=9, highlightthickness=1, highlightbackground=PALETTE["accent"] if primary else PALETTE["border"],
            disabledforeground="#94A3B8", state=state,
        )
        if width:
            b.configure(width=width)
        return b

    def _card(self, parent, title, variable, accent):
        frame = tk.Frame(parent, bg=PALETTE["surface"], highlightthickness=1, highlightbackground=PALETTE["border"])
        tk.Frame(frame, bg=accent, width=4).pack(side="left", fill="y")
        body = tk.Frame(frame, bg=PALETTE["surface"])
        body.pack(side="left", fill="both", expand=True, padx=13, pady=10)
        ttk.Label(body, text=title.upper(), style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(body, textvariable=variable, style="CardValue.TLabel").pack(anchor="w", pady=(2, 0))
        return frame

    # ---------- shell ----------
    def _build_shell(self):
        sidebar = tk.Frame(self, bg=PALETTE["nav"], width=235)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="CPT", bg=PALETTE["nav"], fg="#FFFFFF", font=("Segoe UI Semibold", 24)).pack(anchor="w", padx=24, pady=(24, 0))
        tk.Label(sidebar, text="ANALYZER PROFESSIONAL", bg=PALETTE["nav"], fg="#93C5FD", font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=25, pady=(0, 25))

        tk.Label(sidebar, text="WORKFLOW", bg=PALETTE["nav"], fg="#6B8AA8", font=("Segoe UI Semibold", 8)).pack(anchor="w", padx=24, pady=(0, 8))
        for n, label in [("01", "Select CPT files"), ("02", "Review settings"), ("03", "Run verified analysis"), ("04", "Export & inspect")]:
            row = tk.Frame(sidebar, bg=PALETTE["nav"])
            row.pack(fill="x", padx=20, pady=4)
            tk.Label(row, text=n, width=3, bg=PALETTE["nav2"], fg="#93C5FD", font=("Segoe UI Semibold", 8), pady=5).pack(side="left")
            tk.Label(row, text=label, bg=PALETTE["nav"], fg="#D9E6F2", font=("Segoe UI", 9)).pack(side="left", padx=10)

        tk.Frame(sidebar, bg="#24455F", height=1).pack(fill="x", padx=20, pady=20)
        self.sidebar_files = tk.StringVar(value="0 files loaded")
        tk.Label(sidebar, textvariable=self.sidebar_files, bg=PALETTE["nav"], fg="#FFFFFF", font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=24)
        tk.Label(sidebar, text="Local processing • no cloud upload", bg=PALETTE["nav"], fg="#7FA0BB", font=("Segoe UI", 8)).pack(anchor="w", padx=24, pady=(3, 0))
        tk.Label(sidebar, text="GEF / GFF", bg=PALETTE["nav"], fg="#7FA0BB", font=("Segoe UI", 8)).pack(anchor="w", padx=24, pady=(1, 0))

        main = tk.Frame(self, bg=PALETTE["bg"])
        main.pack(side="left", fill="both", expand=True)

        header = tk.Frame(main, bg=PALETTE["bg"])
        header.pack(fill="x", padx=24, pady=(20, 10))
        left = tk.Frame(header, bg=PALETTE["bg"])
        left.pack(side="left")
        ttk.Label(left, text="CPT Project Analysis", style="Title.TLabel").pack(anchor="w")
        ttk.Label(left, text="Verified silt interpretation, reporting and project-wide visualization", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))
        self.header_start_btn = self._btn(header, "START ANALYSIS", self.start, primary=True)
        self.header_start_btn.pack(side="right", pady=3)

        cards = tk.Frame(main, bg=PALETTE["bg"])
        cards.pack(fill="x", padx=24, pady=(4, 12))
        self.kpi_files = tk.StringVar(value="0")
        self.kpi_verified = tk.StringVar(value="0")
        self.kpi_no_silt = tk.StringVar(value="0")
        self.kpi_review = tk.StringVar(value="0")
        self.kpi_max = tk.StringVar(value="—")
        specs = [
            ("Files", self.kpi_files, PALETTE["accent"]),
            ("Verified", self.kpi_verified, PALETTE["success"]),
            ("No Silt", self.kpi_no_silt, PALETTE["cyan"]),
            ("Review", self.kpi_review, PALETTE["warning"]),
            ("Max Silt", self.kpi_max, PALETTE["purple"]),
        ]
        for idx, (title, var, color) in enumerate(specs):
            c = self._card(cards, title, var, color)
            c.grid(row=0, column=idx, sticky="nsew", padx=(0 if idx == 0 else 5, 0 if idx == len(specs)-1 else 5))
            cards.grid_columnconfigure(idx, weight=1)

        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill="both", expand=True, padx=24, pady=(0, 14))
        self.dashboard = tk.Frame(self.notebook, bg=PALETTE["surface"])
        self.results_tab = tk.Frame(self.notebook, bg=PALETTE["surface"])
        self.chart_tab = tk.Frame(self.notebook, bg=PALETTE["surface"])
        self.notebook.add(self.dashboard, text="  Setup  ")
        self.notebook.add(self.results_tab, text="  Results  ")
        self.notebook.add(self.chart_tab, text="  Charts  ")
        self._build_dashboard()
        self._build_results()
        self._build_charts()

        self.status_var = tk.StringVar(value="Ready — select GEF/GFF files or a project folder.")
        statusbar = tk.Frame(main, bg="#E7EDF5", height=30)
        statusbar.pack(fill="x", side="bottom")
        statusbar.pack_propagate(False)
        tk.Label(statusbar, textvariable=self.status_var, bg="#E7EDF5", fg="#475569", font=("Segoe UI", 8), anchor="w").pack(fill="both", padx=12)

    def _surface_panel(self, parent, title, subtitle=None):
        panel = tk.Frame(parent, bg=PALETTE["surface"], highlightthickness=1, highlightbackground=PALETTE["border"])
        head = tk.Frame(panel, bg=PALETTE["surface"])
        head.pack(fill="x", padx=16, pady=(14, 8))
        ttk.Label(head, text=title, style="Section.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(head, text=subtitle, style="Muted.TLabel").pack(anchor="w", pady=(2, 0))
        return panel

    def _build_dashboard(self):
        content = tk.Frame(self.dashboard, bg=PALETTE["surface"])
        content.pack(fill="both", expand=True, padx=14, pady=14)
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(1, weight=1)

        input_panel = self._surface_panel(content, "Input files", "Select individual files or recursively scan a folder.")
        input_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 7), pady=(0, 7))
        btns = tk.Frame(input_panel, bg=PALETTE["surface"])
        btns.pack(fill="x", padx=16, pady=(0, 14))
        self._btn(btns, "Select Files", self.select_files, primary=True).pack(side="left")
        self._btn(btns, "Select Folder", self.select_folder).pack(side="left", padx=7)
        self._btn(btns, "Clear", self.clear).pack(side="left")
        # Make the two actual source summary inputs discoverable in Project
        # Setup instead of hiding them inside different analysis tabs.
        reference_bar=tk.Frame(input_panel,bg=PALETTE["surface"])
        reference_bar.pack(fill="x",padx=16,pady=(0,5))
        self._btn(reference_bar,"SOURCE CALCULATION XLSB",
                  lambda: self.select_original_reference() if hasattr(self,"select_original_reference") else None).pack(side="left")
        self._btn(reference_bar,"RAFT / ISOLATED SUMMARY XLSX",
                  lambda: self.load_foundation_summary() if hasattr(self,"load_foundation_summary") else None).pack(side="left",padx=7)
        self._btn(reference_bar,"SITE LIMIT / COORDINATES",
                  lambda: self.load_site_boundary() if hasattr(self,"load_site_boundary") else None).pack(side="left")
        self.reference_status=tk.StringVar(value="Reference sources optional · native GEF/GFF/PDF analysis works independently.")
        tk.Label(input_panel,textvariable=self.reference_status,
                 bg=PALETTE["surface"],fg=PALETTE["muted"],
                 font=("Segoe UI",8),anchor="w").pack(fill="x",padx=16,pady=(0,8))
        self.file_label = tk.StringVar(value="No files selected")
        tk.Label(btns, textvariable=self.file_label, bg=PALETTE["surface"], fg=PALETTE["muted"], font=("Segoe UI", 9)).pack(side="right")

        settings = self._surface_panel(content, "Engineering settings", "Applied consistently to all selected raw CPT files.")
        settings.grid(row=0, column=1, sticky="nsew", padx=(7, 0), pady=(0, 7))
        form = tk.Frame(settings, bg=PALETTE["surface"])
        form.pack(fill="x", padx=16, pady=(0, 14))
        self.gamma = tk.StringVar(value="18.0")
        self.wt = tk.StringVar(value="2.0")
        ttk.Label(form, text="Soil unit weight (kN/m³)", style="Surface.TLabel").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(form, textvariable=self.gamma, width=12).grid(row=0, column=1, sticky="e", padx=(12, 0), pady=5)
        ttk.Label(form, text="Groundwater depth BGL (m)", style="Surface.TLabel").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(form, textvariable=self.wt, width=12).grid(row=1, column=1, sticky="e", padx=(12, 0), pady=5)
        self.cpt_stage=tk.StringVar(value="PRE")
        ttk.Label(form,text="CPT investigation stage",style="Surface.TLabel").grid(
            row=2,column=0,sticky="w",pady=5)
        ttk.Combobox(form,textvariable=self.cpt_stage,values=("PRE","POST"),
                     state="readonly",width=10).grid(
            row=2,column=1,sticky="e",padx=(12,0),pady=5)
        form.grid_columnconfigure(0, weight=1)
        tk.Label(form, text="Ic 2.60 • observed-only intervals • no gap joining\nPRE=3, POST=10 samples; sensitivity checks and dropout QA", bg=PALETTE["surface"], fg=PALETTE["muted"], justify="left", font=("Segoe UI", 8)).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

        files_panel = self._surface_panel(content, "Selected project files", "The queue is naturally sorted by CPT reference.")
        files_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 7), pady=(7, 0))
        qframe = tk.Frame(files_panel, bg=PALETTE["surface"])
        qframe.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.file_tree = ttk.Treeview(qframe, columns=("name", "type", "folder"), show="headings", height=12)
        self.file_tree.heading("name", text="File")
        self.file_tree.heading("type", text="Type")
        self.file_tree.heading("folder", text="Folder")
        self.file_tree.column("name", width=260, anchor="w")
        self.file_tree.column("type", width=70, anchor="center")
        self.file_tree.column("folder", width=340, anchor="w")
        qy = ttk.Scrollbar(qframe, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=qy.set)
        self.file_tree.pack(side="left", fill="both", expand=True)
        qy.pack(side="right", fill="y")

        output = self._surface_panel(content, "Output & performance", "Choose what to generate. Analysis always produces the engineering Excel workbook.")
        output.grid(row=1, column=1, sticky="nsew", padx=(7, 0), pady=(7, 0))
        obody = tk.Frame(output, bg=PALETTE["surface"])
        obody.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        ttk.Label(obody, text="Output folder", style="Surface.TLabel").pack(anchor="w")
        outrow = tk.Frame(obody, bg=PALETTE["surface"])
        outrow.pack(fill="x", pady=(5, 12))
        self.output_var = tk.StringVar()
        ttk.Entry(outrow, textvariable=self.output_var).pack(side="left", fill="x", expand=True)
        self._btn(outrow, "Browse", self.choose_output).pack(side="left", padx=(7, 0))

        self.generate_pdfs = tk.BooleanVar(value=True)
        self.open_when_done = tk.BooleanVar(value=False)
        ttk.Checkbutton(obody, text="Generate individual CPT PDFs", variable=self.generate_pdfs).pack(anchor="w", pady=3)
        ttk.Checkbutton(obody, text="Open output folder when finished", variable=self.open_when_done).pack(anchor="w", pady=3)
        ttk.Label(obody, text="Analysis engine", style="Surface.TLabel").pack(anchor="w", pady=(13, 4))
        self.worker_label = tk.StringVar(value=f"Auto parallel analysis — up to {max(1, min(8, os.cpu_count() or 4))} workers")
        ttk.Label(obody, textvariable=self.worker_label, style="Muted.TLabel").pack(anchor="w")

        self.start_btn = self._btn(obody, "RUN VERIFIED ANALYSIS", self.start, primary=True)
        self.start_btn.pack(fill="x", pady=(18, 8))
        self.stage_var = tk.StringVar(value="Ready")
        tk.Label(obody, textvariable=self.stage_var, bg=PALETTE["surface"], fg=PALETTE["muted"], font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(2, 4))
        self.progress = ttk.Progressbar(obody, style="Modern.Horizontal.TProgressbar", mode="determinate", maximum=100)
        self.progress.pack(fill="x")
        self.progress_text = tk.StringVar(value="0%")
        tk.Label(obody, textvariable=self.progress_text, bg=PALETTE["surface"], fg=PALETTE["muted"], font=("Segoe UI", 8)).pack(anchor="e", pady=(3, 0))

    def _build_results(self):
        top = tk.Frame(self.results_tab, bg=PALETTE["surface"])
        top.pack(fill="x", padx=14, pady=14)
        self.result_search = tk.StringVar()
        search = ttk.Entry(top, textvariable=self.result_search, width=28)
        search.pack(side="left")
        search.bind("<KeyRelease>", lambda e: self.render_results())
        self.result_status = tk.StringVar(value="All")
        sf = ttk.Combobox(top, textvariable=self.result_status, values=STATUS_TYPES, state="readonly", width=12)
        sf.pack(side="left", padx=7)
        sf.bind("<<ComboboxSelected>>", lambda e: self.render_results())
        self.open_selected_btn = self._btn(top, "Open Selected PDF", self.open_selected, state="disabled")
        self.open_selected_btn.pack(side="right")
        self.open_excel_btn = self._btn(top, "Open Excel", self.open_excel, state="disabled")
        self.open_excel_btn.pack(side="right", padx=7)
        self.open_pdfs_btn = self._btn(top, "Open PDFs", self.open_pdfs, state="disabled")
        self.open_pdfs_btn.pack(side="right")
        self.open_output_btn = self._btn(top, "Open Output", self.open_output, state="disabled")
        self.open_output_btn.pack(side="right", padx=7)

        table = tk.Frame(self.results_tab, bg=PALETTE["surface"])
        table.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        cols = ("ref", "sand", "start", "end", "thick", "test", "status")
        self.tree = ttk.Treeview(table, columns=cols, show="headings", selectmode="browse")
        defs = [
            ("ref", "CPT Reference", 250), ("sand", "Sand before Silt (m)", 145),
            ("start", "Silt Start (m)", 115), ("end", "Silt End (m)", 110),
            ("thick", "Silt Thickness (m)", 135), ("test", "Test Depth (m)", 115),
            ("status", "Status", 110),
        ]
        for k, t, w in defs:
            self.tree.heading(k, text=t)
            self.tree.column(k, width=w, anchor="w" if k == "ref" else "center")
        self.tree.tag_configure("verified", foreground=PALETTE["success"])
        self.tree.tag_configure("nosilt", foreground=PALETTE["cyan"])
        self.tree.tag_configure("review", foreground=PALETTE["warning"])
        self.tree.tag_configure("error", foreground=PALETTE["danger"])
        ys = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        xs = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        table.grid_rowconfigure(0, weight=1)
        table.grid_columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", lambda e: self.open_selected())
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._selected_changed())

    def _build_charts(self):
        controls = tk.Frame(self.chart_tab, bg=PALETTE["surface"])
        controls.pack(fill="x", padx=14, pady=(14, 8))
        ttk.Label(controls, text="View", style="Surface.TLabel").pack(side="left")
        self.chart_type = tk.StringVar(value="Line overview")
        cb = ttk.Combobox(controls, textvariable=self.chart_type, values=CHART_TYPES, state="readonly", width=27)
        cb.pack(side="left", padx=(6, 12))
        cb.bind("<<ComboboxSelected>>", lambda e: self.refresh_chart())
        ttk.Label(controls, text="Sort", style="Surface.TLabel").pack(side="left")
        self.sort_by = tk.StringVar(value="CPT Reference")
        sb = ttk.Combobox(controls, textvariable=self.sort_by, values=SORT_TYPES, state="readonly", width=17)
        sb.pack(side="left", padx=(6, 12))
        sb.bind("<<ComboboxSelected>>", lambda e: self.refresh_chart())
        self.asc = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text="Ascending", variable=self.asc, command=self.refresh_chart).pack(side="left")
        ttk.Label(controls, text="Status", style="Surface.TLabel").pack(side="left", padx=(12, 0))
        self.status_filter = tk.StringVar(value="All")
        sc = ttk.Combobox(controls, textvariable=self.status_filter, values=STATUS_TYPES, state="readonly", width=11)
        sc.pack(side="left", padx=6)
        sc.bind("<<ComboboxSelected>>", lambda e: self.refresh_chart())
        self._btn(controls, "Save PNG", self.save_chart).pack(side="right")
        self._btn(controls, "Reset", self._reset_view).pack(side="right", padx=7)

        toggles = tk.Frame(self.chart_tab, bg=PALETTE["surface"])
        toggles.pack(fill="x", padx=14, pady=(0, 8))
        self.show_silt = tk.BooleanVar(value=True)
        self.show_sand = tk.BooleanVar(value=True)
        self.show_start = tk.BooleanVar(value=False)
        self.show_test = tk.BooleanVar(value=False)
        self.highlight_max = tk.BooleanVar(value=True)
        for text, var in [
            ("Silt thickness", self.show_silt), ("Sand before silt", self.show_sand),
            ("Silt start", self.show_start), ("Test depth", self.show_test),
            ("Highlight maximum", self.highlight_max),
        ]:
            ttk.Checkbutton(toggles, text=text, variable=var, command=self.refresh_chart).pack(side="left", padx=(0, 12))

        chart_wrap = tk.Frame(self.chart_tab, bg="#FFFFFF", highlightthickness=1, highlightbackground=PALETTE["border"])
        chart_wrap.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.fig = Figure(figsize=(11, 5.8), dpi=100, facecolor="#FFFFFF")
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_wrap)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=4)
        self.toolbar = NavigationToolbar2Tk(self.canvas, chart_wrap, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(fill="x")
        self.refresh_chart()

    # ---------- selection ----------
    def select_files(self):
        x = filedialog.askopenfilenames(
            title="Select CPT GEF/GFF files",
            filetypes=[("GEF/GFF CPT files", "*.GEF *.gef *.GFF *.gff"), ("All files", "*.*")],
        )
        if x:
            self.files = sorted({Path(v) for v in x}, key=lambda p: natural_ref_key(p.stem))
            self._after_select()

    def select_folder(self):
        x = filedialog.askdirectory(title="Select folder containing GEF/GFF files")
        if x:
            self.files = collect_folder(Path(x))
            self.output_dir = Path(x) / "CPT_Output"
            self.output_var.set(str(self.output_dir))
            self._after_select(set_output=False)

    def _after_select(self, set_output=True):
        if set_output:
            p = default_output(self.files)
            if p:
                self.output_dir = p
                self.output_var.set(str(p))
        self.file_label.set(f"{len(self.files)} file(s) selected")
        self.sidebar_files.set(f"{len(self.files)} files loaded")
        self.kpi_files.set(str(len(self.files)))
        for i in self.file_tree.get_children():
            self.file_tree.delete(i)
        for p in self.files:
            self.file_tree.insert("", "end", values=(p.name, p.suffix.upper().lstrip("."), str(p.parent)))
        self.status_var.set(f"Loaded {len(self.files)} CPT file(s). Review settings, then run analysis.")

    def choose_output(self):
        x = filedialog.askdirectory(title="Choose output folder")
        if x:
            self.output_dir = Path(x)
            self.output_var.set(x)

    def clear(self):
        if self.running:
            return
        self.files = []
        self.results = []
        self.errors = []
        self.pdf_by_ref = {}
        self.output_dir = self.pdf_dir = self.excel_path = None
        self.output_var.set("")
        self.file_label.set("No files selected")
        self.sidebar_files.set("0 files loaded")
        self.kpi_files.set("0")
        self.kpi_verified.set("0")
        self.kpi_no_silt.set("0")
        self.kpi_review.set("0")
        self.kpi_max.set("—")
        for tree in (self.file_tree, self.tree):
            for i in tree.get_children():
                tree.delete(i)
        self.progress["value"] = 0
        self.progress_text.set("0%")
        self.stage_var.set("Ready")
        self._set_output_buttons(False)
        self.refresh_chart()
        self.status_var.set("Ready — select GEF/GFF files or a project folder.")

    # ---------- analysis ----------
    def start(self):
        if self.running:
            return
        if not self.files:
            messagebox.showwarning("No files selected", "Select one or more GEF/GFF files, or a project folder first.")
            return
        out = self.output_var.get().strip()
        if not out:
            p = default_output(self.files)
            if not p:
                return
            out = str(p)
            self.output_var.set(out)
        try:
            gamma = float(self.gamma.get())
            wt = float(self.wt.get())
        except ValueError:
            messagebox.showerror("Invalid engineering settings", "Soil unit weight and groundwater depth must be numeric values.")
            return
        if gamma <= 0 or wt < 0:
            messagebox.showerror("Invalid engineering settings", "Soil unit weight must be positive and groundwater depth cannot be negative.")
            return

        self.analysis_stage_value=self.cpt_stage.get()
        self.running = True
        self.output_dir = Path(out)
        self.results = []
        self.errors = []
        self.pdf_by_ref = {}
        for i in self.tree.get_children():
            self.tree.delete(i)
        self._set_running(True)
        self.progress["value"] = 0
        self.progress_text.set("0%")
        self.stage_var.set("Preparing analysis…")
        self.notebook.select(self.results_tab)
        threading.Thread(
            target=self._worker,
            args=(self.output_dir, gamma, wt, bool(self.generate_pdfs.get())),
            daemon=True,
        ).start()

    def _worker(self, out: Path, gamma: float, wt: float, make_pdfs: bool):
        out.mkdir(parents=True, exist_ok=True)
        pdfs = out / "PDFs"
        if make_pdfs:
            pdfs.mkdir(parents=True, exist_ok=True)
        results = []
        errors: list[tuple[str, str]] = []
        total = len(self.files)
        workers = max(1, min(8, os.cpu_count() or 4, total))

        # Numerical analysis is independent by CPT and can run concurrently.
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="cpt") as pool:
            futures = {pool.submit(analyze_gef, p, gamma_soil=gamma, water_table_depth=wt): p for p in self.files}
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

        results.sort(key=lambda a: natural_ref_key(a.reference))

        # Matplotlib PDF rendering is intentionally serialized for reliability.
        if make_pdfs:
            for idx, a in enumerate(results, 1):
                try:
                    pdf = unique_pdf_path(pdfs, a.reference)
                    generate_pdf(a, pdf)
                    self.messages.put(("pdf_done", idx, len(results), a.reference, pdf))
                except Exception as exc:
                    errors.append((a.source_path.name, f"PDF generation: {exc}"))
                    self.messages.put(("pdf_error", idx, len(results), a.reference, str(exc)))

        excel = export_excel(results, out / "CPT_Silt_Analysis.xlsx", errors=errors)
        self.messages.put(("done", out, pdfs if make_pdfs else None, excel, results, errors))

    def _poll(self):
        try:
            while True:
                m = self.messages.get_nowait()
                kind = m[0]
                if kind == "analysis_row":
                    _, i, total, a = m
                    pct = int((i / max(total, 1)) * (60 if self.generate_pdfs.get() else 90))
                    self._set_progress(pct, f"Analyzing CPTs — {i}/{total}")
                    self._insert_result(a)
                elif kind == "analysis_error":
                    _, i, total, p, err = m
                    pct = int((i / max(total, 1)) * (60 if self.generate_pdfs.get() else 90))
                    self._set_progress(pct, f"Analyzing CPTs — {i}/{total}")
                    self.tree.insert("", "end", values=(p.stem, "—", "REVIEW", "—", "—", "—", "ERROR"), tags=("error",))
                    self.status_var.set(f"Error in {p.name}: {err}")
                elif kind == "pdf_done":
                    _, i, total, ref, pdf = m
                    self.pdf_by_ref.setdefault(ref, []).append(Path(pdf))
                    pct = 60 + int((i / max(total, 1)) * 35)
                    self._set_progress(pct, f"Generating PDFs — {i}/{total}")
                elif kind == "pdf_error":
                    _, i, total, ref, err = m
                    pct = 60 + int((i / max(total, 1)) * 35)
                    self._set_progress(pct, f"Generating PDFs — {i}/{total}")
                    self.status_var.set(f"PDF generation warning for {ref}: {err}")
                elif kind == "done":
                    _, out, pdfs, excel, results, errors = m
                    self.results = results
                    self.errors = errors
                    self.output_dir = out
                    self.pdf_dir = pdfs
                    self.excel_path = excel
                    self.running = False
                    self._set_progress(100, "Complete")
                    self._set_running(False)
                    self._set_output_buttons(True)
                    self.update_kpis()
                    self.render_results()
                    self.refresh_chart()
                    self.status_var.set(f"Finished {len(results)} CPT(s) with {len(errors)} processing warning/error(s).")
                    if self.open_when_done.get():
                        open_external_path(out)
                    messagebox.showinfo(
                        "Analysis complete",
                        f"Processed: {len(results)} CPT(s)\nWarnings/errors: {len(errors)}\n\nExcel:\n{excel}" + (f"\n\nPDFs:\n{pdfs}" if pdfs else ""),
                    )
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _set_progress(self, value: int, stage: str):
        value = max(0, min(100, value))
        self.progress["value"] = value
        self.progress_text.set(f"{value}%")
        self.stage_var.set(stage)

    def _set_running(self, running: bool):
        state = "disabled" if running else "normal"
        self.start_btn.config(state=state)
        self.header_start_btn.config(state=state)
        if running:
            self._set_output_buttons(False)

    def _set_output_buttons(self, enabled: bool):
        out_ok = enabled and self.output_dir is not None and self.output_dir.exists()
        excel_ok = enabled and self.excel_path is not None and self.excel_path.exists()
        pdf_ok = enabled and self.pdf_dir is not None and self.pdf_dir.exists()
        self.open_output_btn.config(state="normal" if out_ok else "disabled")
        self.open_excel_btn.config(state="normal" if excel_ok else "disabled")
        self.open_pdfs_btn.config(state="normal" if pdf_ok else "disabled")
        self._selected_changed()

    # ---------- results ----------
    def _insert_result(self, a):
        r = analysis_record(a)
        start = "NO SILT" if a.status == "NO SILT" else (f"{r['start_num']:.2f}" if r["start_num"] is not None else "REVIEW")
        end = f"{r['end']:.2f}" if isinstance(r["end"], (int, float)) else "—"
        thick = f"{r['thickness']:.2f}" if isinstance(r["thickness"], (int, float)) else "—"
        sand = f"{r['sand']:.2f}" if isinstance(r["sand"], (int, float)) else "REVIEW"
        tag = "verified" if a.status == "VERIFIED" else "nosilt" if a.status == "NO SILT" else "review"
        self.tree.insert("", "end", values=(a.reference, sand, start, end, thick, f"{r['test_depth']:.2f}", a.status), tags=(tag,))

    def render_results(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        search = self.result_search.get() if hasattr(self, "result_search") else ""
        status = self.result_status.get() if hasattr(self, "result_status") else "All"
        data = sorted_filtered(self.results, status_filter=status, search=search)
        for a in data:
            self._insert_result(a)
        self._selected_changed()

    def update_kpis(self):
        self.kpi_files.set(str(len(self.results) + len([e for e in self.errors if not str(e[1]).startswith("PDF generation")])) if self.results or self.errors else str(len(self.files)))
        verified = [a for a in self.results if a.status == "VERIFIED" and a.final_interval]
        nosilt = [a for a in self.results if a.status == "NO SILT"]
        review = [a for a in self.results if a.status == "REVIEW"]
        self.kpi_verified.set(str(len(verified)))
        self.kpi_no_silt.set(str(len(nosilt)))
        self.kpi_review.set(str(len(review)))
        if verified:
            mx = max(a.final_interval.thickness for a in verified)
            refs = [a.reference for a in verified if abs(a.final_interval.thickness - mx) < 1e-9]
            self.kpi_max.set(f"{mx:.2f} m")
            self.status_var.set(f"Maximum silt thickness: {mx:.2f} m at {', '.join(refs)}")
        else:
            self.kpi_max.set("None")

    def _selected_changed(self):
        enabled = bool(self.tree.selection() and self.pdf_dir)
        self.open_selected_btn.config(state="normal" if enabled else "disabled")

    def open_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("No selection", "Select a CPT row first.")
            return
        ref = str(self.tree.item(sel[0], "values")[0])
        paths = self.pdf_by_ref.get(ref, [])
        p = paths[0] if paths else (self.pdf_dir / f"{ref}.pdf" if self.pdf_dir else None)
        if not p or not open_external_path(Path(p)):
            messagebox.showwarning("PDF unavailable", "The selected CPT PDF was not found or PDF generation was disabled.")

    def open_pdfs(self):
        if not self.pdf_dir or not open_external_path(self.pdf_dir):
            messagebox.showwarning("PDFs unavailable", "Generate PDFs during analysis first.")

    def open_excel(self):
        if not self.excel_path or not open_external_path(self.excel_path):
            messagebox.showwarning("Excel unavailable", "Run analysis first.")

    def open_output(self):
        if not self.output_dir or not open_external_path(self.output_dir):
            messagebox.showwarning("Output unavailable", "Run analysis first.")

    # ---------- charts ----------
    def _chart_data(self):
        return sorted_filtered(self.results, self.status_filter.get(), self.sort_by.get(), self.asc.get())

    def _clear_extra_axes(self):
        for extra in list(self.fig.axes):
            if extra is not self.ax:
                self.fig.delaxes(extra)

    def refresh_chart(self):
        if not hasattr(self, "ax"):
            return
        self._clear_extra_axes()
        ax = self.ax
        ax.clear()
        ax.set_facecolor("#FFFFFF")
        data = self._chart_data() if self.results else []
        if not data:
            ax.text(.5, .52, "Project charts will appear here after analysis.", ha="center", va="center", transform=ax.transAxes, fontsize=12, color="#64748B")
            ax.text(.5, .46, "Choose a chart type, filter and visible engineering metrics.", ha="center", va="center", transform=ax.transAxes, fontsize=9, color="#94A3B8")
            ax.set_axis_off()
            self.canvas.draw_idle()
            return
        ax.set_axis_on()
        rec = [analysis_record(a) for a in data]
        refs = [r["reference"] for r in rec]
        x = np.arange(len(rec))
        typ = self.chart_type.get()
        silt = np.array([np.nan if r["thickness"] is None else r["thickness"] for r in rec], float)
        sand = np.array([np.nan if r["sand"] is None else r["sand"] for r in rec], float)
        start = np.array([np.nan if r["start_num"] is None else r["start_num"] for r in rec], float)
        test = np.array([r["test_depth"] for r in rec], float)

        if typ == "Grouped bars":
            width = .36
            if self.show_sand.get(): ax.bar(x-width/2, sand, width, label="Sand before silt", color="#60A5FA")
            if self.show_silt.get(): ax.bar(x+width/2, silt, width, label="Silt thickness", color="#7C3AED")
            if self.show_start.get(): ax.plot(x, start, marker="o", ms=3, lw=1.2, label="Silt start", color="#D97706")
            if self.show_test.get(): ax.plot(x, test, marker=".", lw=1.1, label="Test depth", color="#475569")
        elif typ == "Layer profile":
            ax.bar(x, sand, label="Sand / overlying layer", color="#F2C94C")
            ax.bar(x, np.nan_to_num(silt, nan=0), bottom=sand, label="Terminal silt layer", color="#4F86C6")
            ax.invert_yaxis(); ax.set_ylabel("Depth BGL (m)")
        elif typ == "Highest silt ranking":
            order = np.argsort(np.nan_to_num(silt, nan=-1))[::-1]
            xx = np.arange(len(order)); ax.bar(xx, silt[order], color="#7C3AED")
            refs = [refs[i] for i in order]; x = xx; silt = silt[order]
        elif typ == "Silt histogram":
            vals = silt[np.isfinite(silt)]
            ax.hist(vals, bins=min(20, max(5, int(np.sqrt(max(len(vals), 1))))), color="#7C3AED", alpha=.85)
            ax.set_xlabel("Silt thickness (m)"); ax.set_ylabel("Number of CPTs"); ax.set_title("Distribution of Silt Thickness", loc="left", fontweight="bold")
            self._finish_chart(); return
        elif typ == "Silt start vs thickness":
            m = np.isfinite(start) & np.isfinite(silt)
            ax.scatter(start[m], silt[m], color="#2563EB", alpha=.8)
            ax.set_xlabel("Silt start depth BGL (m)"); ax.set_ylabel("Silt thickness (m)"); ax.set_title("Silt Start vs Thickness", loc="left", fontweight="bold")
            self._finish_chart(); return
        elif typ == "Coordinate map":
            east = np.array([np.nan if not isinstance(r["easting"], (int, float)) else r["easting"] for r in rec], float)
            north = np.array([np.nan if not isinstance(r["northing"], (int, float)) else r["northing"] for r in rec], float)
            m = np.isfinite(east) & np.isfinite(north)
            sizes = 28 + 110*np.nan_to_num(silt[m], nan=0)
            sc = ax.scatter(east[m], north[m], s=sizes, c=np.nan_to_num(silt[m], nan=0), cmap="viridis", alpha=.88, edgecolors="white", linewidths=.5)
            self.fig.colorbar(sc, ax=ax, label="Silt thickness (m)")
            ax.set_xlabel("Easting"); ax.set_ylabel("Northing"); ax.set_title("CPT Coordinate Map", loc="left", fontweight="bold")
            ax.ticklabel_format(style="plain", useOffset=False)
            self._finish_chart(); return
        else:
            if self.show_silt.get(): ax.plot(x, silt, marker="o", ms=3, lw=1.4, label="Silt thickness", color="#7C3AED")
            if self.show_sand.get(): ax.plot(x, sand, lw=1.2, label="Sand before silt", color="#2563EB")
            if self.show_start.get(): ax.plot(x, start, lw=1.2, label="Silt start", color="#D97706")
            if self.show_test.get(): ax.plot(x, test, lw=1.1, label="Test depth", color="#475569")

        if self.highlight_max.get() and np.any(np.isfinite(silt)) and typ != "Layer profile":
            mi = int(np.nanargmax(silt))
            ax.scatter([x[mi]], [silt[mi]], s=100, facecolors="none", edgecolors="#DC2626", linewidths=1.8, zorder=9)
            ax.annotate(f"MAX {silt[mi]:.2f} m\n{refs[mi]}", (x[mi], silt[mi]), xytext=(9, 10), textcoords="offset points", fontsize=8, weight="bold", color="#991B1B")
        step = max(1, len(refs)//20)
        ticks = np.arange(len(refs))[::step]
        ax.set_xticks(ticks)
        ax.set_xticklabels([refs[i] for i in ticks], rotation=55, ha="right", fontsize=7)
        ax.set_title(f"Full CPT Analysis — {typ}", loc="left", fontweight="bold")
        ax.set_ylabel("Depth / thickness (m)")
        if ax.get_legend_handles_labels()[0]:
            ax.legend(loc="best", frameon=False)
        self._finish_chart()

    def _finish_chart(self):
        self.ax.grid(True, alpha=.14, color="#94A3B8")
        self.ax.spines[["top", "right"]].set_visible(False)
        self.fig.tight_layout(pad=1.4)
        self.canvas.draw_idle()

    def _reset_view(self):
        self.toolbar.home()
        self.refresh_chart()

    def save_chart(self):
        if not self.results:
            messagebox.showwarning("No chart", "Run analysis first.")
            return
        p = filedialog.asksaveasfilename(title="Save chart", defaultextension=".png", filetypes=[("PNG image", "*.png")], initialfile="CPT_Project_Chart.png")
        if p:
            self.fig.savefig(p, dpi=200, bbox_inches="tight")
            self.status_var.set(f"Chart saved: {p}")


if __name__ == "__main__":
    ModernCPTApp().mainloop()

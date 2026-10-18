"""Engineering QA workbench: an auditable and accessible desktop control surface.

Designed to add useful professional workflows without changing the validated
underlying calculation, PDF and Excel execution paths.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from engineering_workspace import EngineeringWorkspaceApp
from engineering_reference_audit import audit_to_json
from engineering_pdf_parity import pdf_visual_regression
from engineering_excel_pdf import export_original_excel_pdf


def qa_record(analysis):
    source = Path(analysis.source_path)
    metadata = getattr(analysis, "metadata", {}) or {}
    status = str(getattr(analysis,"status","REVIEW"))
    interval = getattr(analysis,"final_interval",None)
    issues=[]
    if status=="REVIEW":
        issues.append("Unresolved interpretation; do not use as accepted layer thickness")
    if getattr(analysis,"sensor_dropout_depth",None) is not None:
        issues.append("Terminal sensor dropout or missing Ic measurements")
    if source.suffix.lower()==".pdf":
        issues.append("PDF-derived graphical interpretation; raw GEF preferred")
    elif not hasattr(analysis,"depth") or len(analysis.depth)==0:
        issues.append("Raw depth data unavailable")
    note=str(getattr(analysis,"verification_note","") or "")
    if any(term in note.lower() for term in ("uncertain","conflict","nonconver","review","invalid")):
        issues.append("Engineering verification note requires attention")
    return {
        "reference":str(analysis.reference),
        "status":status,
        "source":source.name,
        "source_type":source.suffix.upper().lstrip("."),
        "source_quality":str(metadata.get("source_quality") or ("RAW" if source.suffix.lower() in (".gef",".gff") else "PDF")),
        "silt_start":None if interval is None else float(interval.start),
        "silt_thickness":None if interval is None else float(interval.thickness),
        "test_depth":float(analysis.test_depth_raw) if hasattr(analysis,"test_depth_raw") else None,
        "sensor_dropout":getattr(analysis,"sensor_dropout_depth",None),
        "issues":issues,
        "verification":note,
        "full_path":str(source),
    }


def qa_summary(records):
    rows=list(records)
    return {"CPTs":len(rows),
            "Verified":sum(r["status"]=="VERIFIED" for r in rows),
            "No silt":sum(r["status"]=="NO SILT" for r in rows),
            "Review":sum(r["status"]=="REVIEW" for r in rows),
            "QC flags":sum(bool(r["issues"]) for r in rows)}


def export_qa_csv(rows, destination):
    dest=Path(destination);dest.parent.mkdir(parents=True,exist_ok=True)
    fields=("reference","status","source_type","source_quality","source",
            "silt_start","silt_thickness","test_depth","sensor_dropout",
            "issues","verification","full_path")
    with dest.open("w",encoding="utf-8-sig",newline="") as file:
        writer=csv.DictWriter(file,fieldnames=fields)
        writer.writeheader()
        for row in rows:
            values={k:row.get(k) for k in fields}
            values["issues"]="; ".join(row.get("issues") or [])
            writer.writerow(values)
    return dest


class EngineeringReviewApp(EngineeringWorkspaceApp):
    def __init__(self):
        super().__init__()
        self.title("CPT ENGINEERING STUDIO  |  Project Analysis · Maps · QA")
        self._add_quality_workspace()
        self._add_global_shortcuts()
        self._show_first_run_tip()

    def _add_global_shortcuts(self):
        # Ctrl combinations are conventional Windows shortcuts; never bind to
        # letters alone because editable fields must remain usable.
        self.bind_all("<Control-o>",lambda _e:self.select_files())
        self.bind_all("<Control-Shift-O>",lambda _e:self.select_folder())
        self.bind_all("<Control-r>",lambda _e:self.start() if not self.running else None)
        self.bind_all("<Control-e>",lambda _e:self.open_excel())
        self.bind_all("<Control-m>",lambda _e:self.notebook.select(self.map_tab))
        self.bind_all("<Control-q>",lambda _e:self.notebook.select(self.qa_tab))
        self.bind_all("<F1>",lambda _e:self._show_help())

    def _show_first_run_tip(self):
        if hasattr(self,"qa_status"):
            self.qa_status.set("Ready  •  Load a raw GEF/GFF folder or a compatible PDF batch. Verify REVIEW cases before using results for engineering decisions.")

    def _add_quality_workspace(self):
        from app_modern import PALETTE
        self.qa_tab=tk.Frame(self.notebook,bg="#ffffff")
        self.notebook.add(self.qa_tab,text="  QA & Review  ")
        heading=tk.Frame(self.qa_tab,bg="#ffffff")
        heading.pack(fill="x",padx=18,pady=(14,5))
        tk.Label(heading,text="Engineering verification center",font=("Segoe UI Semibold",15),
                 bg="#ffffff",fg="#12354b").pack(anchor="w")
        tk.Label(heading,text="Source provenance  ·  Convergence and dropout  ·  Failed interpretations  ·  Reference-model audits",
                 font=("Segoe UI",9),bg="#ffffff",fg="#64748b").pack(anchor="w",pady=(3,0))

        actions=tk.Frame(self.qa_tab,bg="#ffffff")
        actions.pack(fill="x",padx=18,pady=(10,6))
        self.qa_filter=tk.StringVar(value="All")
        tk.Label(actions,text="Filter",font=("Segoe UI Semibold",9),bg="#ffffff",
                 fg="#475569").pack(side="left")
        choices=ttk.Combobox(actions,textvariable=self.qa_filter,
              values=["All","REVIEW","VERIFIED","NO SILT","QC flagged"],
              state="readonly",width=14)
        choices.pack(side="left",padx=(8,12))
        choices.bind("<<ComboboxSelected>>",lambda _e:self.refresh_qa())
        self.qa_search=tk.StringVar()
        entry=ttk.Entry(actions,textvariable=self.qa_search,width=24)
        entry.pack(side="left",padx=(0,12))
        self.qa_search.trace_add("write",lambda *_:self.refresh_qa())
        self._btn(actions,"EXPORT QA CSV",self.save_qa_csv).pack(side="right")
        self._btn(actions,"OPEN SOURCE",self.open_selected_qa_source).pack(side="right",padx=7)
        self._btn(actions,"VIEW CPT PROFILE",self.open_selected_qa_profile).pack(side="right",padx=7)

        tools=tk.Frame(self.qa_tab,bg="#ffffff")
        tools.pack(fill="x",padx=18,pady=(0,12))
        self._btn(tools,"AUDIT ORIGINAL XLSB",self.audit_reference_excel).pack(side="left")
        self._btn(tools,"COMPARE PDF LAYOUTS",self.compare_pdf_layout).pack(side="left",padx=8)
        self._btn(tools,"EXPORT ORIGINAL EXCEL PDF",self.print_original_xlsb_pdf).pack(side="left",padx=7)
        self._btn(tools,"ENGINEERING GUIDE  F1",self._show_help).pack(side="right")
        self.qa_status=tk.StringVar()
        self.qa_note=tk.Label(tools,textvariable=self.qa_status,bg="#ffffff",fg="#64748b",
                  font=("Segoe UI",8),anchor="w")
        self.qa_note.pack(side="left",padx=12)
        board=tk.Frame(self.qa_tab,bg="#f1f5f9")
        board.pack(fill="x",padx=18,pady=(4,10))
        self.qa_counts=tk.StringVar(value="NO RESULTS  |  Choose a source folder and run analysis")
        tk.Label(board,textvariable=self.qa_counts,bg="#f1f5f9",fg="#0f3956",
                 font=("Segoe UI Semibold",10),padx=14,pady=12,anchor="w").pack(fill="x")

        detail=tk.Frame(self.qa_tab,bg="#f8fafc",highlightthickness=1,
                        highlightbackground="#dce5ef")
        detail.pack(fill="x",padx=18,pady=(0,8))
        self.qa_details=tk.StringVar(value="Select a CPT to see the original source, interpretation and verification notes.")
        tk.Label(detail,textvariable=self.qa_details,bg="#f8fafc",fg="#334155",
                 justify="left",anchor="w",wraplength=1100,padx=12,pady=11,
                 font=("Segoe UI",9)).pack(fill="x")
        frame=tk.Frame(self.qa_tab,bg="#ffffff")
        frame.pack(fill="both",expand=True,padx=18,pady=(0,6))
        columns=("reference","status","type","thickness","quality","issues")
        self.qa_tree=ttk.Treeview(frame,columns=columns,show="headings",selectmode="browse")
        for col,label,width in [
            ("reference","CPT REFERENCE",185),("status","STATUS",100),
            ("type","SOURCE",78),("thickness","SILT (m)",95),
            ("quality","QUALITY",128),("issues","QA FINDINGS",430)]:
            self.qa_tree.heading(col,text=label)
            self.qa_tree.column(col,width=width,anchor="w" if col in ("reference","issues","quality") else "center",
                                minwidth=72,stretch=col=="issues")
        scrollbar=ttk.Scrollbar(frame,orient="vertical",command=self.qa_tree.yview)
        self.qa_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right",fill="y")
        self.qa_tree.pack(side="left",fill="both",expand=True)
        self.qa_tree.tag_configure("REVIEW",background="#fff3e8",foreground="#923b18")
        self.qa_tree.tag_configure("VERIFIED",background="#effbf5",foreground="#0b6043")
        self.qa_tree.tag_configure("NO SILT",background="#f1f7ff",foreground="#245e9b")
        self.qa_tree.bind("<<TreeviewSelect>>",lambda _e:self._set_qa_details())
        self.qa_tree.bind("<Double-1>",lambda _e:self.open_selected_qa_profile())
        self._qa_source_by_iid={}



        self.refresh_qa()

    def refresh_qa(self):
        if not hasattr(self,"qa_tree"):return
        rows=[qa_record(a) for a in self.results]
        summary=qa_summary(rows)
        self.qa_counts.set("  ·  ".join(f"{label.upper()}: {value}" for label,value in summary.items()))
        query=self.qa_search.get().strip().casefold()
        filtering=self.qa_filter.get()
        self._qa_source_by_iid={}
        for rowid in self.qa_tree.get_children():self.qa_tree.delete(rowid)
        for row in rows:
            if filtering=="QC flagged" and not row["issues"]:continue
            if filtering not in ("All","QC flagged") and row["status"]!=filtering:continue
            if query and query not in (row["reference"]+" "+row["source"]).casefold():continue
            val=("—" if row["silt_thickness"] is None else f'{row["silt_thickness"]:.2f}')
            iid=self.qa_tree.insert("", "end",values=(
                row["reference"],row["status"],row["source_type"],val,
                row["source_quality"],"  |  ".join(row["issues"]) or "No automatic flags"),
                tags=(row["status"],))
            self._qa_source_by_iid[iid]=row
        self._set_qa_details()

    def _get_qa_selection(self):
        selected=self.qa_tree.selection() if hasattr(self,"qa_tree") else []
        return self._qa_source_by_iid.get(selected[0]) if selected else None

    def _set_qa_details(self):
        row=self._get_qa_selection()
        if row is None:
            self.qa_details.set("Select a CPT to inspect its original source and full verification notes.")
            return
        self.qa_details.set("SOURCE: "+row["full_path"]+"\nSTATUS: "+row["status"]+
            "    |    METHOD: "+row["source_quality"]+"\nVERIFICATION: "+(
                row["verification"] or "No recorded verification explanation."))

    def open_selected_qa_source(self):
        from app_modern import open_external_path
        row=self._get_qa_selection()
        if not row:
            messagebox.showinfo("Choose a CPT","Select a source row first.");return
        if not open_external_path(Path(row["full_path"])):
            messagebox.showwarning("Source unavailable","The selected input file could not be opened.")

    def open_selected_qa_profile(self):
        row=self._get_qa_selection()
        if not row:
            messagebox.showinfo("Choose a CPT","Select a source row first.");return
        self.layer_reference.set(row["reference"])
        self.notebook.select(self.layers_tab)
        self.refresh_layers()

    def save_qa_csv(self):
        if not self.results:
            messagebox.showwarning("Nothing to export","Complete an analysis first.")
            return
        file=filedialog.asksaveasfilename(defaultextension=".csv",
             initialfile="CPT_Engineering_QA.csv",filetypes=[("CSV UTF-8","*.csv")])
        if file:
            try:
                export_qa_csv((qa_record(a) for a in self.results),file)
                self.status_var.set("QA audit exported to "+file)
            except Exception as error:messagebox.showerror("QA export failed",str(error))

    def audit_reference_excel(self):
        path=filedialog.askopenfilename(title="Select original CPT calculation XLSB",
                 filetypes=[("Binary Excel workbook","*.xlsb")])
        if not path:return
        output=filedialog.asksaveasfilename(defaultextension=".json",
           initialfile="CPT_Reference_Model_Audit.json",filetypes=[("JSON audit","*.json")])
        if not output:return
        try:
            audit_to_json(path,output)
            messagebox.showinfo("Source-model inventory saved",
                "The read-only XLSB chart/formula reference inventory was exported.\n\n"
                "This does not certify cell formulas or VBA calculations.")
        except Exception as exc:messagebox.showerror("Source-model audit failed",str(exc))

    def print_original_xlsb_pdf(self):
        source=filedialog.askopenfilename(title="Select original CPT calculation XLSB",
                      filetypes=[("Original Excel model","*.xlsb")])
        if not source:return
        from engineering_xlsb_reference import ReferenceWorkbookCache
        try:
            with ReferenceWorkbookCache(source) as book:
                meta=book.summary()
            ref=meta["cached_selected_cpt"]
            if not ref:raise ValueError("Workbook does not expose a current CPT reference")
            proceed=messagebox.askyesno("Export original Excel chart",
                 "The original workbook currently contains cached report charts for:\\n"+
                 str(ref)+"\\n\\nThis prints ONLY the source workbook's current saved CPT using "
                 "locally installed Microsoft Excel. Macros and external links are disabled; "
                 "it will not calculate an arbitrary new GEF.\\n\\nContinue?")
            if not proceed:return
            target=filedialog.asksaveasfilename(defaultextension=".pdf",
                    initialfile=str(ref)+"_Original_Excel_Report.pdf",
                    filetypes=[("PDF report","*.pdf")])
            if not target:return
            result,_=export_original_excel_pdf(source,target,expected_cpt=ref)
            messagebox.showinfo("Original Excel PDF saved",
                    "Printed by Microsoft Excel using the source workbook chart geometry:\\n"+
                    str(result))
        except Exception as exc:
            messagebox.showerror("Original XLSB print not available",str(exc))

    def compare_pdf_layout(self):
        paths=filedialog.askopenfilenames(title="Choose TWO PDFs: reference then generated",
              filetypes=[("PDF reports","*.pdf")])
        if not paths:return
        if len(paths)!=2:
            messagebox.showwarning("Two PDFs required","Choose exactly two reports.")
            return
        folder=filedialog.askdirectory(title="Where should comparison images and JSON be saved?")
        if not folder:return
        try:
            comparison=pdf_visual_regression(paths[0],paths[1],folder,pages=1)
            page=comparison["pages"][0]
            result="NEAR-IDENTICAL" if comparison["exact_layout_near_match"] else "VISUAL DIFFERENCES"
            messagebox.showinfo("PDF fidelity audit",result+
                "\nChanged-pixel fraction: "+str(page["fraction_pixels_changed_over_20"])+
                "\nA difference PNG and JSON report have been saved to:\n"+folder)
        except Exception as exc:messagebox.showerror("PDF audit failed",str(exc))

    def _show_help(self):
        messagebox.showinfo("CPT Engineering Studio — Guide",
            "SETUP: Choose raw GEF/GFF or compatible PDF files; choose output and run.\n"
            "SOIL LAYERS: Inspect observed Ic and all layers; UNKNOWN is never presumed sand or silt.\n"
            "SITE MAP: Map measured point coordinates only; import Site Limit for the boundary.\n"
            "FOUNDATIONS: Imported settlement/FOS values are REFERENCE ONLY until approved formulas and limits are verified.\n"
            "PRE/POST: Match source reports or raw profiles; differences may reflect processing settings.\n"
            "QA & REVIEW: Inspect flags, original files, source-workbook inventory and PDF layout differences.\n\n"
            "Shortcuts: Ctrl+O file · Ctrl+Shift+O folder · Ctrl+R analyze · Ctrl+E latest Excel · Ctrl+M map · Ctrl+Q QA · F1 help.\n\n"
            "Engineering caution: Ic is a behavior indicator, not a laboratory USCS soil classification.")

    def update_kpis(self):
        super().update_kpis()
        self.refresh_qa()

    def clear(self):
        super().clear()
        self.refresh_qa()

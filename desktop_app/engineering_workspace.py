"""Interactive engineering workspaces for the existing professional Tk desktop app.

Charts and measured-coordinate maps are standalone offline features.
Foundation design remains reference-only pending source Excel formula approval.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import math
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from app_pdf_enabled import PDFEnabledCPTApp
from engineering_layers import from_analysis, _smooth_contiguous
from engineering_maps import coordinate_rows,filter_coordinate_outliers
from engineering_3d_map import site_3d_figure
from engineering_geo_explorer import risk_plan, export_interactive_3d, depth_window_plan
from engineering_comparison import read_summary_xlsx, compare_summaries, export_comparison, read_site_boundary_xlsx
from engineering_depth_comparison import compare_depth_profiles, export_depth_change
from engineering_foundations import check_foundation_results, export_foundation_validation
from engineering_xlsb_reference import ReferenceWorkbookCache,reference_foundations


class EngineeringWorkspaceApp(PDFEnabledCPTApp):
    def __init__(self):
        super().__init__()
        self.title("CPT Engineering Studio | Analyses • Layers • Maps • Pre/Post")
        self._add_layer_tab()
        self._add_map_tab()
        self._add_foundation_tab()
        self._add_compare_tab()

    def _tab_top(self,frame,title,subtitle):
        bar=tk.Frame(frame,bg="#ffffff")
        bar.pack(fill="x",padx=16,pady=(16,8))
        tk.Label(bar,text=title,bg="#ffffff",fg="#142a40",
                 font=("Segoe UI Semibold",13)).pack(anchor="w")
        tk.Label(bar,text=subtitle,bg="#ffffff",fg="#64748b",
                 font=("Segoe UI",9)).pack(anchor="w",pady=(2,0))
        return bar

    def _plot(self,parent,fig):
        canvas=FigureCanvasTkAgg(fig,master=parent)
        canvas.get_tk_widget().pack(fill="both",expand=True,padx=12,pady=8)
        toolbar=NavigationToolbar2Tk(canvas,parent,pack_toolbar=False)
        toolbar.update();toolbar.pack(fill="x",padx=12)
        return canvas

    def _add_layer_tab(self):
        self.layers_tab=tk.Frame(self.notebook,bg="#ffffff")
        self.notebook.add(self.layers_tab,text="  Soil Layers  ")
        self._tab_top(self.layers_tab,"Full CPT soil-behavior profile",
            "All observed intervals, Ic screening threshold, sensor-invalid portions and rolling-mean options.")
        ctrl=tk.Frame(self.layers_tab,bg="#ffffff")
        ctrl.pack(fill="x",padx=16,pady=4)
        tk.Label(ctrl,text="CPT point",bg="#ffffff").pack(side="left")
        self.layer_reference=tk.StringVar()
        self.layer_picker=ttk.Combobox(ctrl,textvariable=self.layer_reference,state="readonly",width=30)
        self.layer_picker.pack(side="left",padx=8)
        self.layer_picker.bind("<<ComboboxSelected>>",lambda event:self.refresh_layers())
        tk.Label(ctrl,text="Ic processing",bg="#ffffff").pack(side="left",padx=(10,0))
        self.layer_window=tk.StringVar(value="Raw (1)")
        selector=ttk.Combobox(ctrl,textvariable=self.layer_window,state="readonly",
                 values=["Raw (1)","PRE (3)","POST (10)"],width=13)
        selector.pack(side="left",padx=8)
        selector.bind("<<ComboboxSelected>>",lambda event:self.refresh_layers())
        self._btn(ctrl,"SAVE PROFILE PNG",self.save_layer_image).pack(side="right")
        self.layer_status=tk.StringVar(value="Select a CPT after analysis to view all layers.")
        tk.Label(self.layers_tab,textvariable=self.layer_status,bg="#ffffff",fg="#475569",
                 anchor="w",font=("Segoe UI",9)).pack(fill="x",padx=18,pady=4)
        # An inner view switcher gives the chart its full plotting area on
        # small displays instead of squeezing it under a permanent table.
        self.layer_views=ttk.Notebook(self.layers_tab)
        self.layer_views.pack(fill="both",expand=True,padx=16,pady=(0,8))
        self.layer_chart_view=tk.Frame(self.layer_views,bg="#ffffff")
        self.layer_table_view=tk.Frame(self.layer_views,bg="#ffffff")
        self.layer_views.add(self.layer_chart_view,text="  Ic Profile & Colored Intervals  ")
        self.layer_views.add(self.layer_table_view,text="  All Layer Depths & Thicknesses  ")
        colnames=("number","type","from","to","thickness","ic","quality")
        frame=tk.Frame(self.layer_table_view,bg="#ffffff")
        frame.pack(fill="both",expand=True,padx=8,pady=8)
        self.layer_table=ttk.Treeview(frame,columns=colnames,show="headings",
                                       height=10,selectmode="browse")
        for key,label,width in [
            ("number","LAYER",65),("type","CPT SBT INTERPRETATION",260),
            ("from","START (m)",95),("to","END (m)",95),
            ("thickness","THICKNESS (m)",115),("ic","MEAN Ic",100),
            ("quality","DATA QUALITY",180)]:
            self.layer_table.heading(key,text=label)
            self.layer_table.column(key,width=width,stretch=key in ("type","quality"),
                       anchor="w" if key in ("type","quality") else "center")
        self.layer_table.tag_configure("UNKNOWN",background="#fff4ed",foreground="#92400e")
        self.layer_table.tag_configure("MEASURED",background="#f0f7ff",foreground="#1e3a5f")
        table_scroll=ttk.Scrollbar(frame,orient="vertical",command=self.layer_table.yview)
        self.layer_table.configure(yscrollcommand=table_scroll.set)
        table_scroll.pack(side="right",fill="y")
        self.layer_table.pack(side="left",fill="both",expand=True)
        self.layer_fig=Figure(figsize=(10,6),dpi=100,facecolor="#ffffff")
        self.layer_ax=self.layer_fig.add_subplot(111)
        self.layer_canvas=self._plot(self.layer_chart_view,self.layer_fig)
        self.refresh_layers()

    def _add_map_tab(self):
        self.map_tab=tk.Frame(self.notebook,bg="#ffffff")
        self.notebook.add(self.map_tab,text="  Site Map  ")
        self._tab_top(self.map_tab,"CPT point map — actual surveyed coordinates",
            "Offline Easting/Northing plan. No unverified coordinate conversion or interpolation.")
        self.site_boundary=None
        ctrl=tk.Frame(self.map_tab,bg="#ffffff")
        ctrl.pack(fill="x",padx=16,pady=4)
        tk.Label(ctrl,text="Color points by",bg="#ffffff").pack(side="left")
        self.map_metric=tk.StringVar(value="Maximum observed silt-screen thickness")
        self.map_metric_picker=ttk.Combobox(ctrl,textvariable=self.map_metric,state="readonly",width=42,
            values=["Maximum observed silt-screen thickness","Cumulative observed silt-screen thickness",
                    "First qualifying silt-screen depth","Sounding test depth"])
        self.map_metric_picker.pack(side="left",padx=8)
        self.map_metric_picker.bind("<<ComboboxSelected>>",lambda event:self.refresh_map())
        map_actions=tk.Frame(self.map_tab,bg="#ffffff")
        map_actions.pack(fill="x",padx=16,pady=(1,5))
        tk.Label(map_actions,text="DATASET",fg="#64748b",bg="#ffffff",
                 font=("Segoe UI Semibold",9)).pack(side="left",padx=(0,7))
        self.map_data_source=tk.StringVar(value="Current CPT batch")
        source_picker=ttk.Combobox(map_actions,textvariable=self.map_data_source,
           values=["Current CPT batch","Original XLSB full project"],
           width=23,state="readonly")
        source_picker.pack(side="left",padx=6)
        source_picker.bind("<<ComboboxSelected>>",lambda event:self.refresh_map())
        self._source_cached_analysis=None
        self._source_cached_file=None

        self.map_projection=tk.StringVar(value="Risk screening plan")
        projection=ttk.Combobox(map_actions,textvariable=self.map_projection,
                         values=["Risk screening plan","Depth slice plan","2D measured plan","3D CPT soil columns"],width=23,state="readonly")
        projection.pack(side="left",padx=8)
        projection.bind("<<ComboboxSelected>>",lambda event:self.refresh_map())
        self._btn(map_actions,"MAP OPTIONS",self.show_map_options).pack(side="right",padx=3)
        self._btn(map_actions,"FULL SCREEN PLAN",self.show_fullscreen_plan,
                  primary=True).pack(side="right",padx=4)
        # Keep data selectors and action buttons on separate rows; this is
        # essential on 1024px displays and at 125-150% Windows DPI.
        map_files=tk.Frame(self.map_tab,bg="#ffffff")
        map_files.pack(fill="x",padx=16,pady=(1,3))
        self._btn(map_files,"LOAD SITE LIMIT XLSX",self.load_site_boundary).pack(side="left")
        self._btn(map_files,"SAVE CURRENT PLAN PNG",self.save_map_image).pack(side="left",padx=8)
        riskbar=tk.Frame(self.map_tab,bg="#ffffff")
        riskbar.pack(fill="x",padx=16,pady=(2,4))
        tk.Label(riskbar,text="WATCH from (m)",bg="#ffffff",fg="#475569").pack(side="left")
        self.risk_watch=tk.StringVar(value="0.10")
        ttk.Entry(riskbar,textvariable=self.risk_watch,width=8).pack(side="left",padx=(5,10))
        tk.Label(riskbar,text="HIGH from (m)",bg="#ffffff",fg="#475569").pack(side="left")
        self.risk_high=tk.StringVar(value="0.30")
        ttk.Entry(riskbar,textvariable=self.risk_high,width=8).pack(side="left",padx=(5,10))
        self.show_interpolated=tk.BooleanVar(value=False)
        ttk.Checkbutton(riskbar,text="Bounded indicative shading",
                        variable=self.show_interpolated,
                        command=self.refresh_map).pack(side="left",padx=4)
        self._btn(riskbar,"APPLY",self.refresh_map).pack(side="left",padx=4)
        modelbar=tk.Frame(self.map_tab,bg="#ffffff")
        modelbar.pack(fill="x",padx=16,pady=(1,4))
        self._btn(modelbar,"ALL HIGH CPTs · OPEN LIST",self.show_all_high_points).pack(side="left")
        self._btn(modelbar,"OPEN OFFLINE INTERACTIVE 3D SOIL MODEL",self.open_interactive_3d,
                  primary=True).pack(side="left",padx=8)
        self._btn(modelbar,"SAVE 3D HTML",self.save_interactive_3d).pack(side="left",padx=4)
        self.slice_controls=tk.Frame(self.map_tab,bg="#edf4f9")
        self.slice_top=tk.StringVar(value="4.0")
        self.slice_bottom=tk.StringVar(value="5.0")
        tk.Label(self.slice_controls,text="DEPTH SLICE BGL",fg="#29465d",
                 bg="#edf4f9",font=("Segoe UI Semibold",9)).pack(side="left",padx=(10,14))
        tk.Label(self.slice_controls,text="Top (m)",bg="#edf4f9").pack(side="left")
        ttk.Entry(self.slice_controls,textvariable=self.slice_top,width=9).pack(side="left",padx=6)
        tk.Label(self.slice_controls,text="Bottom (m)",bg="#edf4f9").pack(side="left")
        ttk.Entry(self.slice_controls,textvariable=self.slice_bottom,width=9).pack(side="left",padx=6)
        self._btn(self.slice_controls,"UPDATE DEPTH SLICE",self.refresh_map).pack(side="left",padx=9)
        self.slice_controls.pack_forget()
        # Keep the map as the main canvas. Advanced controls live in MAP
        # OPTIONS instead of consuming half the screen at 1024x697.
        map_files.pack_forget()
        riskbar.pack_forget()
        modelbar.pack_forget()
        self._geo_risk_artists={}
        self._geo_hotspots=[]
        # The previous interactive 3D button lived inside modelbar, which was
        # pack_forget()'d by default. Surface the real rotatable offline 3D
        # model as a visible primary action without opening Map Options.
        visible3d=tk.Frame(self.map_tab,bg="#ffffff")
        visible3d.pack(fill="x",padx=16,pady=(2,3))
        self.map_open_3d_btn=self._btn(visible3d,"EXPLORE INTERACTIVE 3D SOIL MODEL",
                  self.open_interactive_3d,primary=True)
        self.map_open_3d_btn.pack(side="left")
        self._btn(visible3d,"SAVE 3D MODEL HTML",
                  self.save_interactive_3d).pack(side="left",padx=8)
        tk.Label(visible3d,text="3D shows observed CPT intervals; scale is adjustable.",
                 bg="#ffffff",fg="#64748b",font=("Segoe UI",8)).pack(side="right")
        self.map_status=tk.StringVar(value="Project map becomes available after analysis.")
        self.map_status_label=tk.Label(self.map_tab,textvariable=self.map_status,bg="#ffffff",fg="#64748b",
                 anchor="w")
        self.map_status_label.pack(fill="x",padx=18,pady=4)
        self.map_fig=Figure(figsize=(10,6),dpi=100,facecolor="#ffffff")
        self.map_ax=self.map_fig.add_subplot(111)
        self.map_canvas=self._plot(self.map_tab,self.map_fig)
        self._mapped_points=[]
        self.map_canvas.mpl_connect("pick_event",self._pick_map_point)
        self.refresh_map()

    def _add_foundation_tab(self):
        self.foundation_tab=tk.Frame(self.notebook,bg="#ffffff")
        self.notebook.add(self.foundation_tab,text="  Foundations  ")
        self._tab_top(self.foundation_tab,"Raft & isolated foundation reference results",
            "Read approved external summary tables. New settlement/FOS design equations are NOT yet validated.")
        controls=tk.Frame(self.foundation_tab,bg="#ffffff")
        controls.pack(fill="x",padx=16,pady=6)
        self._btn(controls,"LOAD ORIGINAL XLSB / XLSX",self.load_foundation_summary,primary=True).pack(side="left")
        self.foundation_metric=tk.StringVar(value="Settlement (mm)")
        c=ttk.Combobox(controls,textvariable=self.foundation_metric,state="readonly",width=20,
                        values=["Settlement (mm)","Minimum FOS"])
        c.pack(side="left",padx=8)
        c.bind("<<ComboboxSelected>>",lambda e:self.refresh_foundations())
        self._btn(controls,"SAVE FOUNDATION MAP",lambda:self._save_figure(
            self.foundation_fig,"CPT_Foundation_Reference_Map.png")).pack(side="right")
        limits=tk.Frame(self.foundation_tab,bg="#ffffff")
        limits.pack(fill="x",padx=16,pady=(0,8))
        tk.Label(limits,text="Engineer-approved allowable settlement (mm)",bg="#ffffff").pack(side="left")
        self.allowable_settlement=tk.StringVar(value="")
        ttk.Entry(limits,textvariable=self.allowable_settlement,width=10).pack(side="left",padx=(8,15))
        tk.Label(limits,text="Minimum FOS",bg="#ffffff").pack(side="left")
        self.minimum_fos=tk.StringVar(value="")
        ttk.Entry(limits,textvariable=self.minimum_fos,width=9).pack(side="left",padx=8)
        self._btn(limits,"EXPORT CRITERIA QA",self.export_foundation_criteria).pack(side="right")
        self.foundation_note=tk.StringVar(value="REFERENCE ONLY — Load the original raft / isolated summary XLSX.")
        tk.Label(self.foundation_tab,textvariable=self.foundation_note,bg="#ffffff",
                 fg="#9a3412",anchor="w").pack(fill="x",padx=16,pady=5)
        self.foundation_fig=Figure(figsize=(10,6),dpi=100,facecolor="#ffffff")
        self.foundation_ax=self.foundation_fig.add_subplot(111)
        self.foundation_canvas=self._plot(self.foundation_tab,self.foundation_fig)
        self.foundation_points=[]

    def load_foundation_summary(self):
        path=filedialog.askopenfilename(title="Select original calculation XLSB or foundation summary XLSX",
               filetypes=[("Excel workbooks","*.xlsb *.xlsx"),
                          ("Original calculation XLSB","*.xlsb"),
                          ("Foundation summary XLSX","*.xlsx")])
        if not path:return
        try:
            if Path(path).suffix.lower()==".xlsb":
                values=reference_foundations(path)
                with ReferenceWorkbookCache(path) as wb:
                    source=wb.summary()
                detail=("%d original XLSB cached foundation rows | Groundwater %.2f m | "
                        "Cone ratio %.2f | Current source CPT: %s") % (
                        len(values),float(source["water_depth_m"] or 0),
                        float(source["cone_ratio"] or 0),source["cached_selected_cpt"])
                self.foundation_reference_path=Path(path)
                self.original_model_path=Path(path)
                self._source_cached_analysis=None
            else:
                values=read_summary_xlsx(path)
                detail="%d summary reference rows loaded" % len(values)
                self.foundation_reference_path=None
            if hasattr(self,"reference_status"):
                self.reference_status.set("Foundation summary: "+Path(path).name+" · "+str(len(values))+" reference records")
            self.foundation_points=[v for v in values if v.foundation in ("RAFT","ISOLATED")]
            if not self.foundation_points:raise ValueError("No Raft Summary or Isolated Summary results found.")
            self.foundation_note.set(detail+"  •  SAVED SOURCE RESULTS; formula recalculation NOT CERTIFIED.")

            self.refresh_foundations()
        except Exception as exc:messagebox.showerror("Foundation import failed",str(exc))

    def export_foundation_criteria(self):
        if not self.foundation_points:
            messagebox.showwarning("No foundation summary","Import a raft/isolated summary first.")
            return
        try:
            allowable=float(self.allowable_settlement.get()) if self.allowable_settlement.get().strip() else None
            fos=float(self.minimum_fos.get()) if self.minimum_fos.get().strip() else None
            if allowable is None and fos is None:
                messagebox.showwarning("Criteria required","Enter at least one approved engineering limit. No defaults will be assumed.")
                return
            rows=check_foundation_results(self.foundation_points,
                    allowable_settlement_mm=allowable,minimum_fos=fos)
            target=filedialog.asksaveasfilename(defaultextension=".xlsx",
                   initialfile="CPT_Foundation_Criteria_QA.xlsx",filetypes=[("Excel workbook","*.xlsx")])
            if not target:return
            export_foundation_validation(rows,target)
            discrepancies=sum(bool(row.discrepancy) for row in rows)
            self.foundation_note.set("%d reference rows checked; %d source/criterion conflicts; imported settlement/FOS still NOT independently validated." % (len(rows),discrepancies))
            self.status_var.set("Foundation QA exported to "+target)
        except Exception as exc:
            messagebox.showerror("Foundation validation failed",str(exc))

    def refresh_foundations(self):
        if not hasattr(self,"foundation_ax"):return
        self.foundation_fig.clear()
        ax=self.foundation_fig.add_subplot(111);self.foundation_ax=ax
        key="settlement_mm" if self.foundation_metric.get()=="Settlement (mm)" else "fos"
        cases={"RAFT":[v for v in self.foundation_points if v.foundation=="RAFT"],
               "ISOLATED":[v for v in self.foundation_points if v.foundation=="ISOLATED"]}
        marks={"RAFT":"s","ISOLATED":"o"}
        all_vals=[v.metrics.get(key) for v in self.foundation_points if v.metrics.get(key) is not None]
        import matplotlib.colors as colors
        norm=colors.Normalize(vmin=min(all_vals),vmax=max(all_vals)+1e-9) if all_vals else None
        last=None
        for typ,items in cases.items():
            source_rows=[v for v in items if v.east is not None and v.north is not None and v.metrics.get(key) is not None]
            mapped,excluded=filter_coordinate_outliers([(v.reference,v.east,v.north,v) for v in source_rows])
            rows=[t[3] for t in mapped]
            if not rows:continue
            last=ax.scatter([v.east for v in rows],[v.north for v in rows],
                            c=[v.metrics[key] for v in rows],marker=marks[typ],
                            cmap="viridis",norm=norm,edgecolor="white",s=43,label=typ)
        if last:self.foundation_fig.colorbar(last,ax=ax,label=self.foundation_metric.get())
        if all_vals:ax.legend()
        if not self.foundation_points:ax.text(.5,.5,"Load an approved foundation summary",transform=ax.transAxes,ha="center")
        ax.set_xlabel("Easting");ax.set_ylabel("Northing");ax.grid(alpha=.13)
        ax.set_aspect("equal",adjustable="datalim")
        ax.set_title("IMPORTED "+self.foundation_metric.get()+" — REFERENCE ONLY",loc="left",fontsize=11)
        self.foundation_fig.tight_layout()
        self.foundation_canvas.draw_idle()

    def _add_compare_tab(self):
        self.compare_tab=tk.Frame(self.notebook,bg="#ffffff")
        self.notebook.add(self.compare_tab,text="  Pre / Post  ")
        self._tab_top(self.compare_tab,"Pre/Post CPT and foundation-summary comparison",
           "Pair by CPT identity and coordinates. Show unmatched results and signed changes, not assumed improvement.")
        # Two task-focused control pages instead of a single crowded
        # toolbar. Chart stays below, accessible from either workflow.
        self.compare_controls=ttk.Notebook(self.compare_tab)
        self.compare_controls.pack(fill="x",padx=16,pady=(5,4))
        self.compare_summary_controls=tk.Frame(self.compare_controls,bg="#ffffff")
        self.compare_raw_controls=tk.Frame(self.compare_controls,bg="#ffffff")
        self.compare_controls.add(self.compare_summary_controls,text="  Compare Summary Workbooks  ")
        self.compare_controls.add(self.compare_raw_controls,text="  Compare Raw Depth Profiles  ")

        row=tk.Frame(self.compare_summary_controls,bg="#ffffff")
        row.pack(fill="x",padx=8,pady=(6,2))
        self.pre_path=tk.StringVar(value="No PRE summary")
        self.post_path=tk.StringVar(value="No POST summary")
        self._btn(row,"CHOOSE PRE XLSX",lambda:self._select_summary("pre")).pack(side="left")
        tk.Label(row,textvariable=self.pre_path,bg="#ffffff",fg="#475569",
                 width=21,anchor="w").pack(side="left",padx=6)
        self._btn(row,"CHOOSE POST XLSX",lambda:self._select_summary("post")).pack(side="left",padx=(8,0))
        tk.Label(row,textvariable=self.post_path,bg="#ffffff",fg="#475569",
                 width=21,anchor="w").pack(side="left",padx=6)

        actions=tk.Frame(self.compare_summary_controls,bg="#ffffff")
        actions.pack(fill="x",padx=8,pady=3)
        self._btn(actions,"RUN SUMMARY COMPARISON",self.run_summary_comparison,primary=True).pack(side="left")
        self.allow_coordinate_only=tk.BooleanVar(value=False)
        ttk.Checkbutton(actions,text="Match distinct IDs by unique coordinates (needs review)",
                        variable=self.allow_coordinate_only).pack(side="left",padx=10)
        self.comparison_view=tk.StringVar(value="Change bars")
        cv=ttk.Combobox(actions,textvariable=self.comparison_view,state="readonly",
                        width=21,values=["Change bars","Coordinate delta map"])
        cv.pack(side="left",padx=4)
        cv.bind("<<ComboboxSelected>>",
                lambda event:self.run_summary_comparison() if self.compare_result else None)
        summary_exports=tk.Frame(self.compare_summary_controls,bg="#ffffff")
        summary_exports.pack(fill="x",padx=8,pady=(1,7))
        self._btn(summary_exports,"EXPORT CHANGES XLSX",self.export_summary_comparison).pack(side="left")
        self._btn(summary_exports,"SAVE COMPARISON PNG",self.save_comparison_image).pack(side="left",padx=8)

        rawbar=tk.Frame(self.compare_raw_controls,bg="#ffffff")
        rawbar.pack(fill="x",padx=8,pady=(8,3))
        self._btn(rawbar,"CHOOSE PRE GEF/GFF",lambda:self._choose_raw_pair("pre")).pack(side="left")
        self.raw_pre_label=tk.StringVar(value="No PRE source")
        tk.Label(rawbar,textvariable=self.raw_pre_label,bg="#ffffff",fg="#475569",
                 width=20,anchor="w").pack(side="left",padx=6)
        self._btn(rawbar,"CHOOSE POST GEF/GFF",lambda:self._choose_raw_pair("post")).pack(side="left",padx=(8,0))
        self.raw_post_label=tk.StringVar(value="No POST source")
        tk.Label(rawbar,textvariable=self.raw_post_label,bg="#ffffff",fg="#475569",
                 width=20,anchor="w").pack(side="left",padx=6)
        raw_actions=tk.Frame(self.compare_raw_controls,bg="#ffffff")
        raw_actions.pack(fill="x",padx=8,pady=(2,8))
        self.depth_pair={}
        self.raw_compare_mode=tk.StringVar(value="Harmonized (3 / 3)")
        modes=ttk.Combobox(raw_actions,textvariable=self.raw_compare_mode,state="readonly",
              values=["Harmonized (3 / 3)","Workbook reference (3 / 10)"],width=27)
        modes.pack(side="left",padx=(0,9))
        self._btn(raw_actions,"ANALYZE DEPTH CHANGES & EXPORT",self.run_raw_depth_comparison,
                  primary=True).pack(side="left")
        self.comparison_status=tk.StringVar(value="Select both PRE and POST workbooks.")
        tk.Label(self.compare_tab,textvariable=self.comparison_status,bg="#ffffff",fg="#475569",
                 anchor="w").pack(fill="x",padx=16,pady=5)
        self.comparison_fig=Figure(figsize=(10,6),dpi=100,facecolor="#ffffff")
        self.comparison_ax=self.comparison_fig.add_subplot(111)
        self.comparison_canvas=self._plot(self.compare_tab,self.comparison_fig)
        self.compare_result=None
        self._comparison_inputs={}

    def _choose_raw_pair(self,stage):
        f=filedialog.askopenfilename(title="Choose "+stage.upper()+" raw CPT",
                    filetypes=[("Raw CPT sounding","*.GEF *.gef *.GFF *.gff")])
        if f:
            self.depth_pair[stage]=Path(f)
            (self.raw_pre_label if stage=="pre" else self.raw_post_label).set(Path(f).name)

    def run_raw_depth_comparison(self):
        if "pre" not in self.depth_pair or "post" not in self.depth_pair:
            messagebox.showwarning("Missing sounding","Select both PRE and POST raw GEF/GFF soundings.")
            return
        from cpt_core import analyze_gef
        from matplotlib.figure import Figure
        try:
            gamma=float(self.gamma.get());wt=float(self.wt.get())
            pre=analyze_gef(self.depth_pair["pre"],gamma_soil=gamma,water_table_depth=wt)
            post=analyze_gef(self.depth_pair["post"],gamma_soil=gamma,water_table_depth=wt)
            mode="reference" if "Workbook" in self.raw_compare_mode.get() else "harmonized"
            change=compare_depth_profiles(pre,post,mode=mode)
            output=filedialog.askdirectory(title="Save depth comparison files (Excel/PDF/PNG)")
            if not output:
                return
            files=export_depth_change(change,output)
        except Exception as exc:
            messagebox.showerror("Raw depth comparison failed",str(exc))
            return
        ax=self.comparison_ax;self.comparison_fig.clear()
        ax=self.comparison_fig.add_subplot(111)
        ax.plot(change.metrics["qc"]["delta"],change.depth_m,color="#2563eb",linewidth=1.4,label="qc delta (MPa)")
        ax2=ax.twiny()
        ax2.plot(change.metrics["ic"]["delta"],change.depth_m,color="#dc2626",linewidth=1.0,label="Ic delta")
        ax.invert_yaxis();ax.set_xlabel("POST - PRE qc (MPa)")
        ax2.set_xlabel("POST - PRE Ic (-)")
        ax.set_ylabel("Corrected depth BGL (m)")
        ax.grid(alpha=.12)
        ax.set_title("Raw PRE/POST observed profiles — "+mode,loc="left")
        self.comparison_ax=ax
        self.comparison_fig.tight_layout()
        self.comparison_canvas.draw_idle()
        self.comparison_status.set("Raw paired depth comparison: %s vs %s | %d depths | %s" % (
            change.pre_reference,change.post_reference,len(change.depth_m),mode))
        self.status_var.set("Saved comparison to "+str(files["xlsx"]))

    def _select_summary(self,stage):
        path=filedialog.askopenfilename(title="Select "+stage.upper()+" summary",
               filetypes=[("Excel workbook","*.xlsx")])
        if path:
            self._comparison_inputs[stage]=Path(path)
            (self.pre_path if stage=="pre" else self.post_path).set(Path(path).name)

    def _render_original_source_profile(self,reference):
        """Drill from project map to ORIGINAL SAVED SBT zones, never fake Ic."""
        source=getattr(self,"original_model_path",None)
        selected=next((x for x in (self._source_cached_analysis or [])
                       if x["reference"]==reference),None)
        if not source or selected is None:return False
        try:
            if getattr(self,"_source_cached_curves_file",None)!=str(source):
                from engineering_xlsb_reference import ReferenceWorkbookCache
                with ReferenceWorkbookCache(source) as source_book:
                    self._source_cached_curves=source_book.mapped_profiles()
                self._source_cached_curves_file=str(source)
            raw=self._source_cached_curves.get(reference,[])
            ground=float(selected["ground_elevation"])
            values=sorted([(ground-float(rl),int(zone)) for rl,qc,zone in raw
                        if isinstance(zone,(int,float)) and float(rl)<=ground],
                        key=lambda x:x[0])
            self.layer_ax.clear()
            for iid in self.layer_table.get_children():self.layer_table.delete(iid)
            if values:
                depths=np.asarray([x[0] for x in values],float)
                zones=np.asarray([x[1] for x in values],int)
                self.layer_ax.step(zones,depths,where="post",linewidth=1.0,color="#17416e")
                self.layer_ax.axvspan(.5,4.5,color="#ffc2b8",alpha=.25)
                self.layer_ax.set_xlim(.5,9.5)
                self.layer_ax.set_xticks(list(range(1,10)))
                self.layer_ax.set_ylim(float(np.max(depths))+.05,-.05)
            for index,layer in enumerate(selected.get("all_intervals",[]),1):
                self.layer_ax.axhspan(layer["start_raw"],layer["end_raw"],
                                      color="#dd5344",alpha=.19)
                self.layer_table.insert("","end",values=(
                    index,"ORIGINAL SBT ZONES "+",".join(map(str,layer["zone_codes"])),
                    f'{layer["start_raw"]:.3f}',f'{layer["end_raw"]:.3f}',
                    f'{layer["thickness_raw"]:.3f}',"—",
                    "XLSB CACHED; NOT NUMERICAL Ic"),tags=("MEASURED",))
            self.layer_ax.set_xlabel("Original XLSB categorical SBT zone (1–9), NOT Ic")
            self.layer_ax.set_ylabel("Depth BGL (m)")
            self.layer_ax.set_title(reference+" — original saved zone sequence",
                                    loc="left",fontsize=11)
            self.layer_ax.grid(alpha=.12)
            self.layer_status.set(
                f"{reference}: {len(raw)} cached points | {len(selected.get('all_intervals',[]))} "
                "qualifying intervals | original zone classes, not continuous Ic. "
                "See Original SBT Curves sheet in Excel.")
            self.layer_fig.tight_layout()
            self.layer_canvas.draw_idle()
            return True
        except Exception as exc:
            self.layer_status.set("Original source profile unavailable: "+str(exc))
            return False

    def refresh_layers(self):
        if not hasattr(self,"layer_ax"):return
        if (getattr(self,"map_data_source",None) is not None
             and self.map_data_source.get()=="Original XLSB full project"
             and self.layer_reference.get()
             and self._render_original_source_profile(self.layer_reference.get())):
            return
        a=next((v for v in self.results if v.reference==self.layer_reference.get()),None)
        self.layer_ax.clear()
        if hasattr(self,"layer_table"):
            for iid in self.layer_table.get_children():
                self.layer_table.delete(iid)
        if a is None:
            self.layer_ax.text(.5,.5,"Select an analyzed CPT",transform=self.layer_ax.transAxes,
                               ha="center",va="center",color="#64748b")
            self.layer_canvas.draw_idle()
            return
        window={"Raw (1)":1,"PRE (3)":3,"POST (10)":10}[self.layer_window.get()]
        try:
            strat=from_analysis(a,rolling_window=window)
            z=np.asarray(a.depth,dtype=float)
            ic=np.asarray(a.ic,dtype=float)
            valid=np.asarray(a.valid_sensor,dtype=bool)&np.isfinite(ic)
            smooth=_smooth_contiguous(ic,valid,window)
            self.layer_ax.plot(np.ma.masked_where(~valid,ic),z,lw=.8,color="#93c5fd",label="Raw Ic")
            if window>1:self.layer_ax.plot(np.ma.masked_invalid(smooth),z,lw=1.3,color="#2563eb",label="Rolling mean Ic")
            for layer in strat.layers:
                color="#cbd5e1" if layer.kind=="UNKNOWN" else "#f5ca70" if (layer.mean_ic or 0)<2.6 else "#77acc7" if (layer.mean_ic or 0)<3.1 else "#b59dcc"
                self.layer_ax.axhspan(layer.start_m,layer.end_m,color=color,alpha=.25,linewidth=0)
                if hasattr(self,"layer_table"):
                    self.layer_table.insert("","end",values=(
                        layer.number,layer.kind,f"{layer.start_m:.3f}",
                        f"{layer.end_m:.3f}",f"{layer.thickness_m:.3f}",
                        "—" if layer.mean_ic is None else f"{layer.mean_ic:.3f}",
                        layer.status),
                        tags=("UNKNOWN" if layer.kind=="UNKNOWN" else "MEASURED",))
            self.layer_ax.axvline(2.60,color="#dc2626",linestyle="--",lw=1,label="Ic 2.60")
            self.layer_ax.invert_yaxis()
            self.layer_ax.set_xlim(0,5)
            self.layer_ax.set_xlabel("Soil behavior type index Ic")
            self.layer_ax.set_ylabel("Corrected depth BGL (m)")
            self.layer_ax.set_title(a.reference+" — full observed profile",loc="left",fontweight="bold")
            self.layer_ax.legend(fontsize=8)
            self.layer_ax.grid(alpha=.15)
            self.layer_status.set("Observed qualifying layers: %d | Cumulative %.3f m | Max %.3f m | UNKNOWN %.3f m | Brief crossings: %d" %
                 (strat.silt_count,strat.cumulative_silt_m,strat.maximum_silt_m,strat.unknown_m,len(strat.brief_exceedances)))
        except Exception as exc:
            self.layer_status.set("Profile REVIEW: "+str(exc))
            self.layer_ax.text(.5,.5,str(exc),transform=self.layer_ax.transAxes,ha="center")
        self.layer_fig.tight_layout()
        self.layer_canvas.draw_idle()

    def load_site_boundary(self):
        path=filedialog.askopenfilename(title="Select Site Limit workbook",
                        filetypes=[("Excel workbook","*.xlsx")])
        if not path:return
        try:
            self.site_boundary=read_site_boundary_xlsx(path)
            if hasattr(self,"reference_status"):self.reference_status.set("Survey site limits loaded: "+Path(path).name)
            self.refresh_map()
            self.status_var.set("Site limit loaded: "+Path(path).name)
        except Exception as exc:
            messagebox.showerror("Site boundary not available",str(exc))

    def _map_dataset(self):
        analyses=self.results
        if self.map_data_source.get()=="Original XLSB full project":
            source=getattr(self,"original_model_path",None)
            if not source:raise ValueError("Select an original XLSB model in QA & Review first")
            if self._source_cached_analysis is None or self._source_cached_file!=str(source):
                from engineering_reference_project import analyze_original_xlsb
                _,self._source_cached_analysis,_=analyze_original_xlsb(source)
                self._source_cached_file=str(source)
            analyses=self._source_cached_analysis
        return analyses

    def show_map_options(self):
        dlg=tk.Toplevel(self)
        dlg.title("Site Map — Settings & Actions")
        dlg.geometry("620x425")
        dlg.minsize(490,320)
        dlg.transient(self)
        root=tk.Frame(dlg,bg="#f8fafc",padx=17,pady=15)
        root.pack(fill="both",expand=True)
        tk.Label(root,text="Site screening map options",
              font=("Segoe UI Semibold",14),bg="#f8fafc",fg="#17364e").pack(anchor="w")
        tk.Label(root,text="These thresholds prioritize CPT review; they do not define engineering safety.",
              font=("Segoe UI",9),bg="#f8fafc",fg="#64748b").pack(anchor="w",pady=(3,13))
        settings=tk.Frame(root,bg="#f8fafc")
        settings.pack(fill="x",pady=5)
        tk.Label(settings,text="Watch from (m)",bg="#f8fafc").grid(row=0,column=0,sticky="w")
        ttk.Entry(settings,textvariable=self.risk_watch,width=12).grid(row=0,column=1,padx=(7,20))
        tk.Label(settings,text="High from (m)",bg="#f8fafc").grid(row=0,column=2,sticky="w")
        ttk.Entry(settings,textvariable=self.risk_high,width=12).grid(row=0,column=3,padx=7)
        tk.Label(settings,text="Slice top (m BGL)",bg="#f8fafc").grid(row=1,column=0,sticky="w",pady=8)
        ttk.Entry(settings,textvariable=self.slice_top,width=12).grid(row=1,column=1,padx=(7,20),pady=8)
        tk.Label(settings,text="Slice bottom (m BGL)",bg="#f8fafc").grid(row=1,column=2,sticky="w",pady=8)
        ttk.Entry(settings,textvariable=self.slice_bottom,width=12).grid(row=1,column=3,padx=7,pady=8)
        ttk.Checkbutton(root,text="Show locally supported *indicative* interpolated shading",
                        variable=self.show_interpolated).pack(anchor="w",pady=8)
        actions=tk.Frame(root,bg="#f8fafc")
        actions.pack(fill="x",pady=(8,0))
        self._btn(actions,"APPLY AND REFRESH",lambda:(self.refresh_map(),dlg.lift()),
                  primary=True).grid(row=0,column=0,sticky="ew",padx=(0,8),pady=4)
        self._btn(actions,"ALL HIGH CPT POINTS",self.show_all_high_points).grid(
                  row=0,column=1,sticky="ew",pady=4)
        self._btn(actions,"LOAD SITE LIMIT",self.load_site_boundary).grid(
                  row=1,column=0,sticky="ew",padx=(0,8),pady=4)
        self._btn(actions,"SAVE 2D PLAN PNG",self.save_map_image).grid(
                  row=1,column=1,sticky="ew",pady=4)
        self._btn(actions,"OPEN INTERACTIVE 3D",self.open_interactive_3d).grid(
                  row=2,column=0,sticky="ew",padx=(0,8),pady=4)
        self._btn(actions,"EXPORT 3D HTML",self.save_interactive_3d).grid(
                  row=2,column=1,sticky="ew",pady=4)
        actions.grid_columnconfigure(0,weight=1)
        actions.grid_columnconfigure(1,weight=1)
        self._btn(root,"CLOSE",dlg.destroy).pack(anchor="e",pady=(8,0))

    def show_fullscreen_plan(self):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg,NavigationToolbar2Tk
        from matplotlib.figure import Figure
        try:
            dataset=self._map_dataset()
            figure=Figure(figsize=(13,8.5),dpi=110,facecolor="white")
            settings={"boundary":self.site_boundary,
                      "warning_m":float(self.risk_watch.get()),
                      "high_m":float(self.risk_high.get()),
                      "show_interpretive_surface":self.show_interpolated.get()}
            if self.map_projection.get()=="Depth slice plan":
                drawn=depth_window_plan(figure,dataset,
                    top_m=float(self.slice_top.get()),
                    bottom_m=float(self.slice_bottom.get()),**settings)
            else:
                drawn=risk_plan(figure,dataset,**settings)
        except Exception as exc:
            messagebox.showerror("Full-screen plan unavailable",str(exc))
            return
        popup=tk.Toplevel(self)
        popup.title("CPT SITE PLAN — Full-screen Engineering Review")
        try:popup.state("zoomed")
        except tk.TclError:popup.geometry("1360x870")
        bar=tk.Frame(popup,bg="#f0f5fa")
        bar.pack(fill="x",padx=8,pady=5)
        tk.Label(bar,text=f"{len(drawn['points'])} CPT points  |  "
              f"{len(drawn['high'])} HIGH  |  "
              f"{len(drawn['outliers'])} survey exceptions — click CPT pins to inspect",
              bg="#f0f5fa",fg="#18364f",
              font=("Segoe UI Semibold",10)).pack(side="left",padx=8)
        self._btn(bar,"ALL HIGH CPTs",self.show_all_high_points).pack(side="right",padx=5)
        self._btn(bar,"CLOSE FULL SCREEN",popup.destroy).pack(side="right",padx=5)
        canvas=FigureCanvasTkAgg(figure,master=popup)
        canvas.get_tk_widget().pack(fill="both",expand=True)
        toolbar=NavigationToolbar2Tk(canvas,popup,pack_toolbar=False)
        toolbar.update();toolbar.pack(fill="x",padx=9,pady=3)
        def clicked(event):
            found=drawn["artists"].get(getattr(event,"artist",None),[])
            indices=getattr(event,"ind",[])
            if len(indices) and int(indices[0])<len(found):
                self._open_map_reference(found[int(indices[0])].reference)
                popup.destroy()  # reveal the selected full CPT profile
        canvas.mpl_connect("pick_event",clicked)
        canvas.draw_idle()
        # Keep figure+canvas strongly reachable while popup is alive.
        popup._cpt_figure=figure
        popup._cpt_canvas=canvas

    def show_all_high_points(self):
        from tkinter import ttk
        if not self._geo_hotspots:
            messagebox.showinfo("No high screening points",
                "No locations reach the current HIGH screening thickness. "
                "Review the threshold, data source and filter.")
            return
        window=tk.Toplevel(self)
        window.title("All CPT screening hotspots — click to inspect")
        window.geometry("900x500")
        panel=tk.Frame(window,padx=14,pady=12);panel.pack(fill="both",expand=True)
        ttk.Label(panel,text=f"{len(self._geo_hotspots)} CPTs meeting HIGH screening threshold — "
                  "not engineering design failures",font=("Segoe UI Semibold",12)).pack(anchor="w",pady=(0,9))
        cols=("ref","thick","x","y","status")
        grid=ttk.Treeview(panel,columns=cols,show="headings",selectmode="browse")
        for c,t,w in zip(cols,("CPT Reference","Max observed (m)","Easting","Northing",
                               "Classification"),(235,140,150,150,145)):
            grid.heading(c,text=t);grid.column(c,width=w)
        grid.pack(fill="both",expand=True)
        for p in self._geo_hotspots:
            grid.insert("","end",values=(p.reference,
                     "N/A" if p.maximum_m is None else f"{p.maximum_m:.3f}",
                     f"{p.x:.3f}",f"{p.y:.3f}",p.status))
        def open_row(_event=None):
            item=grid.selection()
            if not item:return
            ref=grid.item(item[0],"values")[0]
            self._open_map_reference(ref)
        grid.bind("<Double-1>",open_row)
        self._btn(panel,"OPEN SELECTED CPT",open_row).pack(anchor="e",pady=8)

    def _open_map_reference(self,reference):
        self.layer_reference.set(reference)
        self.notebook.select(self.layers_tab)
        self.refresh_layers()
        self.status_var.set("Opened CPT profile: "+reference)

    def save_interactive_3d(self):
        output=filedialog.asksaveasfilename(
            title="Save portable offline 3D geotechnical model",
            defaultextension=".html",
            initialfile="CPT_Site_3D_Soil_Model.html",
            filetypes=[("Offline interactive HTML","*.html")])
        if not output:return
        try:
            dataset=self._map_dataset()
            result=export_interactive_3d(
                dataset,output,boundary=self.site_boundary,
                warning_m=float(self.risk_watch.get()),
                high_m=float(self.risk_high.get()))
            self.status_var.set("Offline 3D model saved: "+str(result["file"]))
            messagebox.showinfo("Offline 3D model exported",
                f"{result['points']} surveyed CPTs; {result['wedges']} "
                "locally supported interpretive wedges.\n\n"+
                str(result["file"]))
        except Exception as exc:
            messagebox.showerror("3D export unsuccessful",str(exc))

    def open_interactive_3d(self):
        import webbrowser
        import tempfile
        try:
            dataset=self._map_dataset()
            # A standalone HTML document contains Plotly itself; it remains
            # usable offline and can be opened in any modern local browser.
            if not hasattr(self,"_geo_html_dir"):
                from tempfile import TemporaryDirectory
                self._geo_html_dir=TemporaryDirectory(prefix="cpt_3d_explorer_")
            target=Path(self._geo_html_dir.name)/"CPT_Interactive_3D.html"
            result=export_interactive_3d(dataset,target,boundary=self.site_boundary,
                         warning_m=float(self.risk_watch.get()),
                         high_m=float(self.risk_high.get()))
            if not webbrowser.open(target.resolve().as_uri()):
                messagebox.showinfo("3D model created","Open this local HTML in your browser:\n"+str(target))
            self.map_status.set(
                f"Offline 3D explorer: {result['points']} surveyed CPTs | "
                f"{result['wedges']} locally supported interpretation wedges | "
                f"{result['withheld']} survey coordinate exceptions. "
                "Rotate, zoom and toggle layer visibility in the browser.")
        except Exception as exc:
            messagebox.showerror("3D geology model unavailable",str(exc))

    def refresh_map(self):
        if not hasattr(self,"map_ax"):return
        if hasattr(self,"slice_controls"):
            if self.map_projection.get()=="Depth slice plan":
                if not self.slice_controls.winfo_manager():
                    self.slice_controls.pack(fill="x",padx=16,pady=4,
                                             before=self.map_status_label)
            elif self.slice_controls.winfo_manager():
                self.slice_controls.pack_forget()
        map_analyses=self.results
        if self.map_data_source.get()=="Original XLSB full project":
            source=getattr(self,"original_model_path",None)
            if not source:
                self.map_fig.clear()
                ax=self.map_fig.add_subplot(111);self.map_ax=ax
                ax.text(.5,.5,"Set an original XLSB baseline in QA & Review first",
                    transform=ax.transAxes,ha="center",va="center",fontsize=12)
                ax.set_axis_off()
                self.map_status.set("No original XLSB loaded. QA & Review > Original Excel & Reference Tools > Set XLSB baseline")
                self.map_canvas.draw_idle()
                return
            try:
                if self._source_cached_analysis is None or self._source_cached_file!=str(source):
                    from engineering_reference_project import analyze_original_xlsb
                    _,self._source_cached_analysis,_=analyze_original_xlsb(source)
                    self._source_cached_file=str(source)
                map_analyses=self._source_cached_analysis
            except Exception as exc:
                self.map_status.set("Original XLSB project could not be read: "+str(exc))
                return
        if self.map_projection.get() in ("Risk screening plan","Depth slice plan"):
            try:
                watch=float(self.risk_watch.get());high=float(self.risk_high.get())
                if self.map_projection.get()=="Depth slice plan":
                    summary=depth_window_plan(
                        self.map_fig,map_analyses,top_m=float(self.slice_top.get()),
                        bottom_m=float(self.slice_bottom.get()),
                        boundary=self.site_boundary,warning_m=watch,high_m=high,
                        show_interpretive_surface=self.show_interpolated.get())
                else:
                    summary=risk_plan(self.map_fig,map_analyses,boundary=self.site_boundary,
                            warning_m=watch,high_m=high,
                            show_interpretive_surface=self.show_interpolated.get())
            except Exception as exc:
                self.map_status.set("Risk plan cannot be displayed: "+str(exc))
                return
            self.map_ax=self.map_fig.axes[0]
            self._geo_risk_artists=summary["artists"]
            self._geo_hotspots=summary["high"]
            self._mapped_points=[]
            self.map_status.set(
                f"{len(summary['points'])} CPT locations • "
                f"{len(summary['high'])} HIGH screening points (all inspectable) • "
                f"{summary['supported_triangles']} locally supported surface triangles • "
                f"{len(summary['outliers'])} coordinate QA exceptions. "
                "Click a pin for full CPT details; toolbar pan/zoom supported.")
            self.map_canvas.draw_idle()
            return
        if self.map_projection.get()=="3D CPT soil columns":
            fig,summary=site_3d_figure(map_analyses,self.site_boundary,figure=self.map_fig)
            self.map_ax=self.map_fig.axes[0]
            self._mapped_points=[]
            self.map_status.set("%d observed CPT columns | %d source-coordinate exceptions | Drag the model to rotate, mouse wheel to zoom. No interpolated surfaces." %
                                (summary["plotted"],summary["withheld"]))
            self.map_canvas.draw_idle()
            return
        self.map_fig.clear()
        ax=self.map_fig.add_subplot(111);self.map_ax=ax
        option={"Maximum observed silt-screen thickness":"maximum_silt",
                "Cumulative observed silt-screen thickness":"cumulative_silt",
                "First qualifying silt-screen depth":"silt_start",
                "Sounding test depth":"test_depth"}[self.map_metric.get()]
        if self.map_data_source.get()=="Original XLSB full project":
            metric={"maximum_silt":"max_contiguous_silt_screen_m",
                    "cumulative_silt":"cumulative_silt_screen_m",
                    "silt_start":"first_silt_screen_m",
                    "test_depth":"test_depth_m"}[option]
            rawrows=[(r["reference"],float(r["easting"]),float(r["northing"]),
                      float(r[metric]) if r.get(metric) is not None else float("nan"),
                      str(r["status"]))
                     for r in map_analyses if r.get("easting") is not None and
                     r.get("northing") is not None]
        else:
            rawrows=coordinate_rows(map_analyses,option) if map_analyses else []
        rows,coordinate_outliers=filter_coordinate_outliers(rawrows)
        data=[r for r in rows if math.isfinite(r[3]) and r[4]!="REVIEW"]
        review=[r for r in rows if r not in data]
        self._mapped_points=data
        if data:
            scat=ax.scatter([r[1] for r in data],[r[2] for r in data],
                  c=[r[3] for r in data],cmap="viridis",s=43,edgecolors="white",linewidths=.5,
                  picker=8)
            cb=self.map_fig.colorbar(scat,ax=ax,shrink=.8);cb.set_label(option.replace("_"," ")+" (m)")
            if len(data)<75:
                for ref,e,n,v,status in data:ax.annotate(ref,(e,n),xytext=(3,3),textcoords="offset points",fontsize=6)
        if review:ax.scatter([r[1] for r in review],[r[2] for r in review],marker="x",color="#be123c",label="REVIEW / no metric")
        if self.site_boundary:
            poly=np.asarray(self.site_boundary,float)
            poly=np.vstack([poly,poly[0]])
            ax.plot(poly[:,0],poly[:,1],color="#475569",linewidth=1.7,label="Survey boundary")
        if not rows:ax.text(.5,.5,"No CPT locations with valid coordinates",ha="center",va="center",transform=ax.transAxes)
        ax.set_xlabel("Easting (project grid units)");ax.set_ylabel("Northing (project grid units)")
        ax.set_aspect("equal",adjustable="datalim");ax.grid(alpha=.12)
        ax.set_title("CPT Site Map | "+option.replace("_"," ").title(),loc="left",fontweight="bold")
        self.map_status.set("%d plotted coordinate points | %d numeric points | %d uncertain | %d outlier(s) withheld for survey verification. CRS not verified." %
                             (len(rows),len(data),len(review),len(coordinate_outliers)))
        if review:ax.legend()
        self.map_fig.tight_layout()
        self.map_canvas.draw_idle()

    def _pick_map_point(self,event):
        points=getattr(self,"_geo_risk_artists",{}).get(getattr(event,"artist",None))
        if points is not None:
            indices=getattr(event,"ind",[])
            if len(indices) and 0<=int(indices[0])<len(points):
                self._open_map_reference(points[int(indices[0])].reference)
            return
        if not getattr(self,"_mapped_points",None):return
        indices=getattr(event,"ind",[])
        if not len(indices):return
        i=int(indices[0])
        if i<0 or i>=len(self._mapped_points):return
        ref=self._mapped_points[i][0]
        self.layer_reference.set(ref)
        self.notebook.select(self.layers_tab)
        self.refresh_layers()
        self.status_var.set("Opened full measured layer profile for "+ref)

    def _update_analysis_options(self):
        if hasattr(self,"layer_picker"):
            refs=[a.reference for a in self.results]
            self.layer_picker["values"]=refs
            if self.layer_reference.get() not in refs:
                self.layer_reference.set(refs[0] if refs else "")
            self.refresh_layers()
        if hasattr(self,"map_ax"):self.refresh_map()

    def update_kpis(self):
        super().update_kpis()
        self._update_analysis_options()

    def clear(self):
        super().clear()
        self._update_analysis_options()

    def run_summary_comparison(self):
        if "pre" not in self._comparison_inputs or "post" not in self._comparison_inputs:
            messagebox.showwarning("Missing workbook","Select both PRE and POST summary workbooks.")
            return
        try:
            pre=read_summary_xlsx(self._comparison_inputs["pre"])
            post=read_summary_xlsx(self._comparison_inputs["post"])
            self.compare_result=compare_summaries(pre,post,
                allow_coordinate_only=self.allow_coordinate_only.get())
        except Exception as exc:
            messagebox.showerror("Comparison input problem",str(exc));return
        result=self.compare_result
        self.comparison_status.set("Matched %d | PRE unmatched %d | POST unmatched %d | Ambiguous %d" %
          (len(result["matched"]),len(result["unmatched_pre"]),len(result["unmatched_post"]),len(result["ambiguous"])))
        ax=self.comparison_ax;ax.clear()
        if self.comparison_view.get()=="Coordinate delta map":
            for key,label in (("settlement_mm","Settlement delta (mm)"),
                              ("silt_thickness_m","Silt screening thickness delta (m)")):
                places=[m for m in result["matched"] if
                       m["pre"].east is not None and m["pre"].north is not None
                       and m["metrics"].get(key,{}).get("delta") is not None]
                if places:break
            if places:
                sc=ax.scatter([m["pre"].east for m in places],
                              [m["pre"].north for m in places],
                              c=[m["metrics"][key]["delta"] for m in places],
                              cmap="coolwarm",edgecolors="white",s=65)
                self.comparison_fig.colorbar(sc,ax=ax,label=label)
                if len(places)<=60:
                    for m in places:
                        ax.annotate(m["pre"].reference,(m["pre"].east,m["pre"].north),
                                    xytext=(3,3),textcoords="offset points",fontsize=7)
                ax.set_xlabel("Easting");ax.set_ylabel("Northing")
                ax.set_aspect("equal",adjustable="datalim")
            else:ax.text(.5,.5,"Matched points have no shared coordinate-and-metric data",
                         transform=ax.transAxes,ha="center")
            ax.set_title("PRE / POST DELTA MAP — measured locations only",loc="left")
            ax.grid(alpha=.13)
            self.comparison_fig.tight_layout()
            self.comparison_canvas.draw_idle()
            return
        pairs=[x for x in result["matched"] if x["metrics"].get("settlement_mm",{}).get("delta") is not None]
        label="Settlement change (POST - PRE), mm"
        if not pairs:
            pairs=[x for x in result["matched"] if x["metrics"].get("silt_thickness_m",{}).get("delta") is not None]
            label="Silt screening thickness change (POST - PRE), m"
            key="silt_thickness_m"
        else:key="settlement_mm"
        if pairs:
            refs=[p["pre"].reference for p in pairs]
            diff=[p["metrics"][key]["delta"] for p in pairs]
            order=np.argsort(np.abs(diff))[::-1]
            ax.bar(np.arange(len(order)),np.asarray(diff)[order],color=["#c2410c" if diff[k]>0 else "#0f766e" for k in order])
            if len(order)<=40:ax.set_xticks(np.arange(len(order)),[refs[k] for k in order],rotation=80,fontsize=7)
            else:ax.set_xticks([])
            ax.axhline(0,color="#64748b",lw=1)
            ax.set_ylabel(label)
            ax.grid(axis="y",alpha=.2)
        else:
            ax.text(.5,.5,"Matched records have no common numeric metric",transform=ax.transAxes,ha="center")
        ax.set_title("Pre/Post matched comparison — differences are not automatically improvement",loc="left",fontsize=11)
        self.comparison_fig.tight_layout()
        self.comparison_canvas.draw_idle()

    def export_summary_comparison(self):
        if not self.compare_result:
            messagebox.showwarning("No comparison","Run comparison first.");return
        p=filedialog.asksaveasfilename(defaultextension=".xlsx",initialfile="CPT_Pre_Post_Comparison.xlsx",
                                        filetypes=[("Excel workbook","*.xlsx")])
        if p:
            try:
                export_comparison(self.compare_result,p)
                self.status_var.set("Comparison Excel saved: "+p)
            except Exception as exc:messagebox.showerror("Export failed",str(exc))

    def _save_figure(self,fig,filename):
        p=filedialog.asksaveasfilename(defaultextension=".png",initialfile=filename,filetypes=[("PNG image","*.png")])
        if p:fig.savefig(p,dpi=200,bbox_inches="tight");self.status_var.set("Saved chart: "+p)

    def save_layer_image(self):self._save_figure(self.layer_fig,"CPT_Layers.png")
    def save_map_image(self):self._save_figure(self.map_fig,"CPT_Site_Map.png")
    def save_comparison_image(self):self._save_figure(self.comparison_fig,"CPT_Pre_Post_Deltas.png")

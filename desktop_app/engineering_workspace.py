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
from engineering_maps import coordinate_rows
from engineering_comparison import read_summary_xlsx, compare_summaries, export_comparison, read_site_boundary_xlsx


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
        self.layer_fig=Figure(figsize=(10,6),dpi=100,facecolor="#ffffff")
        self.layer_ax=self.layer_fig.add_subplot(111)
        self.layer_canvas=self._plot(self.layers_tab,self.layer_fig)
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
        self._btn(ctrl,"SAVE SITE MAP PNG",self.save_map_image).pack(side="right")
        self._btn(ctrl,"LOAD SITE LIMIT XLSX",self.load_site_boundary).pack(side="right",padx=8)
        self.map_status=tk.StringVar(value="Project map becomes available after analysis.")
        tk.Label(self.map_tab,textvariable=self.map_status,bg="#ffffff",fg="#64748b",
                 anchor="w").pack(fill="x",padx=18,pady=4)
        self.map_fig=Figure(figsize=(10,6),dpi=100,facecolor="#ffffff")
        self.map_ax=self.map_fig.add_subplot(111)
        self.map_canvas=self._plot(self.map_tab,self.map_fig)
        self.refresh_map()

    def _add_foundation_tab(self):
        self.foundation_tab=tk.Frame(self.notebook,bg="#ffffff")
        self.notebook.add(self.foundation_tab,text="  Foundations  ")
        self._tab_top(self.foundation_tab,"Raft & isolated foundation reference results",
            "Read approved external summary tables. New settlement/FOS design equations are NOT yet validated.")
        controls=tk.Frame(self.foundation_tab,bg="#ffffff")
        controls.pack(fill="x",padx=16,pady=6)
        self._btn(controls,"LOAD FOUNDATION SUMMARY",self.load_foundation_summary,primary=True).pack(side="left")
        self.foundation_metric=tk.StringVar(value="Settlement (mm)")
        c=ttk.Combobox(controls,textvariable=self.foundation_metric,state="readonly",width=20,
                        values=["Settlement (mm)","Minimum FOS"])
        c.pack(side="left",padx=8)
        c.bind("<<ComboboxSelected>>",lambda e:self.refresh_foundations())
        self._btn(controls,"SAVE FOUNDATION MAP",lambda:self._save_figure(
            self.foundation_fig,"CPT_Foundation_Reference_Map.png")).pack(side="right")
        self.foundation_note=tk.StringVar(value="REFERENCE ONLY — Load the original raft / isolated summary XLSX.")
        tk.Label(self.foundation_tab,textvariable=self.foundation_note,bg="#ffffff",
                 fg="#9a3412",anchor="w").pack(fill="x",padx=16,pady=5)
        self.foundation_fig=Figure(figsize=(10,6),dpi=100,facecolor="#ffffff")
        self.foundation_ax=self.foundation_fig.add_subplot(111)
        self.foundation_canvas=self._plot(self.foundation_tab,self.foundation_fig)
        self.foundation_points=[]

    def load_foundation_summary(self):
        path=filedialog.askopenfilename(title="Select foundation reference summary",
               filetypes=[("Excel workbook","*.xlsx")])
        if not path:return
        try:
            values=read_summary_xlsx(path)
            self.foundation_points=[v for v in values if v.foundation in ("RAFT","ISOLATED")]
            if not self.foundation_points:raise ValueError("No Raft Summary or Isolated Summary values found.")
            self.foundation_note.set("%d reference values loaded — not independently validated; no new PASS is inferred." %
                                     len(self.foundation_points))
            self.refresh_foundations()
        except Exception as exc:messagebox.showerror("Foundation import failed",str(exc))

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
            rows=[v for v in items if v.east is not None and v.north is not None and v.metrics.get(key) is not None]
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
        row=tk.Frame(self.compare_tab,bg="#ffffff")
        row.pack(fill="x",padx=16,pady=10)
        self.pre_path=tk.StringVar(value="No PRE summary selected")
        self.post_path=tk.StringVar(value="No POST summary selected")
        self._btn(row,"SELECT PRE XLSX",lambda:self._select_summary("pre")).pack(side="left")
        tk.Label(row,textvariable=self.pre_path,bg="#ffffff",fg="#475569",
                 width=36,anchor="w").pack(side="left",padx=8)
        self._btn(row,"SELECT POST XLSX",lambda:self._select_summary("post")).pack(side="left",padx=(12,0))
        tk.Label(row,textvariable=self.post_path,bg="#ffffff",fg="#475569",
                 width=36,anchor="w").pack(side="left",padx=8)
        actions=tk.Frame(self.compare_tab,bg="#ffffff")
        actions.pack(fill="x",padx=16,pady=6)
        self._btn(actions,"RUN COMPARISON",self.run_summary_comparison,primary=True).pack(side="left")
        self.comparison_view=tk.StringVar(value="Change bars")
        cv=ttk.Combobox(actions,textvariable=self.comparison_view,state="readonly",
                        width=22,values=["Change bars","Coordinate delta map"])
        cv.pack(side="left",padx=8)
        cv.bind("<<ComboboxSelected>>",lambda event:self.run_summary_comparison() if self.compare_result else None)
        self._btn(actions,"EXPORT COMPARISON XLSX",self.export_summary_comparison).pack(side="left",padx=8)
        self._btn(actions,"SAVE COMPARISON PNG",self.save_comparison_image).pack(side="left")
        self.comparison_status=tk.StringVar(value="Select both PRE and POST workbooks.")
        tk.Label(self.compare_tab,textvariable=self.comparison_status,bg="#ffffff",fg="#475569",
                 anchor="w").pack(fill="x",padx=16,pady=5)
        self.comparison_fig=Figure(figsize=(10,6),dpi=100,facecolor="#ffffff")
        self.comparison_ax=self.comparison_fig.add_subplot(111)
        self.comparison_canvas=self._plot(self.compare_tab,self.comparison_fig)
        self.compare_result=None
        self._comparison_inputs={}

    def _select_summary(self,stage):
        path=filedialog.askopenfilename(title="Select "+stage.upper()+" summary",
               filetypes=[("Excel workbook","*.xlsx")])
        if path:
            self._comparison_inputs[stage]=Path(path)
            (self.pre_path if stage=="pre" else self.post_path).set(Path(path).name)

    def refresh_layers(self):
        if not hasattr(self,"layer_ax"):return
        a=next((v for v in self.results if v.reference==self.layer_reference.get()),None)
        self.layer_ax.clear()
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
            self.refresh_map()
            self.status_var.set("Site limit loaded: "+Path(path).name)
        except Exception as exc:
            messagebox.showerror("Site boundary not available",str(exc))

    def refresh_map(self):
        if not hasattr(self,"map_ax"):return
        self.map_fig.clear()
        ax=self.map_fig.add_subplot(111);self.map_ax=ax
        option={"Maximum observed silt-screen thickness":"maximum_silt",
                "Cumulative observed silt-screen thickness":"cumulative_silt",
                "First qualifying silt-screen depth":"silt_start",
                "Sounding test depth":"test_depth"}[self.map_metric.get()]
        rows=coordinate_rows(self.results,option) if self.results else []
        data=[r for r in rows if math.isfinite(r[3]) and r[4]!="REVIEW"]
        review=[r for r in rows if r not in data]
        if data:
            scat=ax.scatter([r[1] for r in data],[r[2] for r in data],
                  c=[r[3] for r in data],cmap="viridis",s=43,edgecolors="white",linewidths=.5)
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
        self.map_status.set("%d coordinate points | %d numeric points | %d uncertain. CRS not yet verified; no interpolation." %
                             (len(rows),len(data),len(review)))
        if review:ax.legend()
        self.map_fig.tight_layout()
        self.map_canvas.draw_idle()

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
            self.compare_result=compare_summaries(pre,post)
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

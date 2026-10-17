from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from cpt_core import analyze_gef, natural_ref_key
from reporting_pro import analysis_record, export_excel, generate_pdf

CHART_TYPES = ["Line", "Bar", "Layer Profile", "Highest Silt Ranking", "Histogram", "Scatter: Silt Start vs Thickness", "Coordinate Map"]
SORT_TYPES = ["CPT Reference", "Silt Thickness", "Sand Thickness", "Silt Start", "Test Depth"]
STATUS_TYPES = ["All", "Verified", "No Silt", "Review"]


def open_external_path(path: Path) -> bool:
    p=Path(path)
    if not p.exists(): return False
    try:
        if os.name=="nt": os.startfile(str(p))  # type: ignore[attr-defined]
        elif sys.platform=="darwin": subprocess.Popen(["open",str(p)])
        else: subprocess.Popen(["xdg-open",str(p)])
        return True
    except Exception: return False


def collect_folder(folder: Path):
    return sorted({p for p in Path(folder).rglob("*") if p.is_file() and p.suffix.lower() in {".gef",".gff"}},key=lambda p:natural_ref_key(p.stem))


def default_output(files):
    if not files: return None
    parents={Path(f).parent.resolve() for f in files}; base=next(iter(parents)) if len(parents)==1 else Path(files[0]).parent
    return base/"CPT_Output"


def unique_pdf_path(folder: Path, ref: str) -> Path:
    p=folder/f"{ref}.pdf"; n=2
    while p.exists(): p=folder/f"{ref}__{n}.pdf"; n+=1
    return p


def sorted_filtered(results, status_filter="All", sort_by="CPT Reference", ascending=True):
    data=list(results)
    if status_filter!="All":
        wanted={"Verified":"VERIFIED","No Silt":"NO SILT","Review":"REVIEW"}[status_filter]; data=[a for a in data if a.status==wanted]
    def key(a):
        r=analysis_record(a)
        if sort_by=="Silt Thickness": return (-1 if r["thickness"] is None else float(r["thickness"]),natural_ref_key(a.reference))
        if sort_by=="Sand Thickness": return (-1 if r["sand"] is None else float(r["sand"]),natural_ref_key(a.reference))
        if sort_by=="Silt Start": return (-1 if r["start_num"] is None else float(r["start_num"]),natural_ref_key(a.reference))
        if sort_by=="Test Depth": return (float(r["test_depth"]),natural_ref_key(a.reference))
        return natural_ref_key(a.reference)
    return sorted(data,key=key,reverse=not ascending)


class CPTApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("CPT Silt Analyzer - Professional v3.1"); self.geometry("1420x900"); self.minsize(1100,720)
        self.files=[]; self.results=[]; self.errors=[]; self.messages=queue.Queue(); self.output_dir=None; self.pdf_dir=None; self.excel_path=None; self.pdf_by_ref={}
        self._build(); self.after(100,self._poll)

    def _build(self):
        ttk.Label(self,text="CPT GEF/GFF Professional Analysis",font=("Segoe UI",18,"bold")).pack(anchor="w",padx=18,pady=(14,2))
        ttk.Label(self,text="Raw CPT analysis • reference-style PDFs • complete engineering Excel • interactive project charts").pack(anchor="w",padx=18,pady=(0,10))
        row=ttk.Frame(self); row.pack(fill="x",padx=18)
        ttk.Button(row,text="Select Files",command=self.select_files).pack(side="left"); ttk.Button(row,text="Select Folder",command=self.select_folder).pack(side="left",padx=6); ttk.Button(row,text="Clear",command=self.clear).pack(side="left")
        self.file_label=ttk.Label(row,text="0 files selected"); self.file_label.pack(side="left",padx=14)
        out=ttk.Frame(self); out.pack(fill="x",padx=18,pady=(7,0)); ttk.Label(out,text="Output:").pack(side="left"); self.output_var=tk.StringVar(); ttk.Entry(out,textvariable=self.output_var).pack(side="left",fill="x",expand=True,padx=7); ttk.Button(out,text="Choose Output Folder",command=self.choose_output).pack(side="left")
        cfg=ttk.LabelFrame(self,text="Engineering Settings"); cfg.pack(fill="x",padx=18,pady=9)
        ttk.Label(cfg,text="Soil unit weight (kN/m³)").grid(row=0,column=0,padx=8,pady=7); self.gamma=tk.StringVar(value="18.0"); ttk.Entry(cfg,textvariable=self.gamma,width=9).grid(row=0,column=1)
        ttk.Label(cfg,text="Groundwater depth BGL (m)").grid(row=0,column=2,padx=(24,8)); self.wt=tk.StringVar(value="0.0"); ttk.Entry(cfg,textvariable=self.wt,width=9).grid(row=0,column=3)
        ttk.Label(cfg,text="Ic=2.60 • interpolated crossing • terminal dropout protection • 2-pass verification + rechecks",foreground="#555").grid(row=0,column=4,padx=25,sticky="w")
        act=ttk.Frame(self); act.pack(fill="x",padx=18,pady=(0,7))
        self.start_btn=ttk.Button(act,text="START ANALYSIS",command=self.start); self.start_btn.pack(side="left")
        self.open_selected_btn=ttk.Button(act,text="Open Selected PDF",command=self.open_selected,state="disabled"); self.open_selected_btn.pack(side="left",padx=(7,0))
        self.open_pdfs_btn=ttk.Button(act,text="Open PDFs",command=self.open_pdfs,state="disabled"); self.open_pdfs_btn.pack(side="left",padx=(7,0))
        self.open_excel_btn=ttk.Button(act,text="Open Excel Sheet",command=self.open_excel,state="disabled"); self.open_excel_btn.pack(side="left",padx=(7,0))
        self.open_output_btn=ttk.Button(act,text="Open Output Folder",command=self.open_output,state="disabled"); self.open_output_btn.pack(side="left",padx=(7,0))
        self.progress=ttk.Progressbar(act,mode="determinate"); self.progress.pack(side="left",fill="x",expand=True,padx=12); self.progress_label=ttk.Label(act,text="Ready"); self.progress_label.pack(side="right")
        self.summary=tk.StringVar(value="Maximum silt thickness: -"); ttk.Label(self,textvariable=self.summary,font=("Segoe UI",10,"bold")).pack(anchor="w",padx=18,pady=(0,5))
        nb=ttk.Notebook(self); nb.pack(fill="both",expand=True,padx=18,pady=(0,8)); res=ttk.Frame(nb); chart=ttk.Frame(nb); nb.add(res,text="Results"); nb.add(chart,text="Full Analysis Chart")
        cols=("ref","sand","start","end","thick","test","status"); self.tree=ttk.Treeview(res,columns=cols,show="headings",selectmode="browse")
        defs=[("ref","CPT Reference",250),("sand","Sand Thickness",125),("start","Silt Start",105),("end","Silt End",105),("thick","Silt Thickness",115),("test","Test Depth",105),("status","Status",120)]
        for k,t,w in defs: self.tree.heading(k,text=t); self.tree.column(k,width=w,anchor="w" if k=="ref" else "center")
        ys=ttk.Scrollbar(res,orient="vertical",command=self.tree.yview); xs=ttk.Scrollbar(res,orient="horizontal",command=self.tree.xview); self.tree.configure(yscrollcommand=ys.set,xscrollcommand=xs.set); self.tree.pack(side="left",fill="both",expand=True); ys.pack(side="right",fill="y"); xs.pack(side="bottom",fill="x"); self.tree.bind("<Double-1>",lambda e:self.open_selected()); self.tree.bind("<<TreeviewSelect>>",lambda e:self._selected_changed())
        controls=ttk.Frame(chart); controls.pack(fill="x",padx=6,pady=5)
        ttk.Label(controls,text="View:").pack(side="left"); self.chart_type=tk.StringVar(value="Line"); cb=ttk.Combobox(controls,textvariable=self.chart_type,values=CHART_TYPES,state="readonly",width=29); cb.pack(side="left",padx=4); cb.bind("<<ComboboxSelected>>",lambda e:self.refresh_chart())
        ttk.Label(controls,text="Sort:").pack(side="left",padx=(10,0)); self.sort_by=tk.StringVar(value="CPT Reference"); sb=ttk.Combobox(controls,textvariable=self.sort_by,values=SORT_TYPES,state="readonly",width=17); sb.pack(side="left",padx=4); sb.bind("<<ComboboxSelected>>",lambda e:self.refresh_chart())
        self.asc=tk.BooleanVar(value=True); ttk.Checkbutton(controls,text="Ascending",variable=self.asc,command=self.refresh_chart).pack(side="left")
        ttk.Label(controls,text="Status:").pack(side="left",padx=(10,0)); self.status_filter=tk.StringVar(value="All"); sf=ttk.Combobox(controls,textvariable=self.status_filter,values=STATUS_TYPES,state="readonly",width=10); sf.pack(side="left",padx=4); sf.bind("<<ComboboxSelected>>",lambda e:self.refresh_chart())
        c2=ttk.Frame(chart); c2.pack(fill="x",padx=6,pady=(0,4)); self.show_silt=tk.BooleanVar(value=True); self.show_sand=tk.BooleanVar(value=True); self.show_start=tk.BooleanVar(value=False); self.show_test=tk.BooleanVar(value=False); self.highlight_max=tk.BooleanVar(value=True)
        for t,v in [("Silt thickness",self.show_silt),("Sand thickness",self.show_sand),("Silt start",self.show_start),("Test depth",self.show_test),("Highlight maximum",self.highlight_max)]: ttk.Checkbutton(c2,text=t,variable=v,command=self.refresh_chart).pack(side="left",padx=5)
        ttk.Button(c2,text="Reset View",command=self._reset_view).pack(side="right",padx=4); ttk.Button(c2,text="Save Chart PNG",command=self.save_chart).pack(side="right",padx=4)
        self.fig=Figure(figsize=(11,5.6),dpi=100); self.ax=self.fig.add_subplot(111); self.canvas=FigureCanvasTkAgg(self.fig,master=chart); self.canvas.get_tk_widget().pack(fill="both",expand=True); self.toolbar=NavigationToolbar2Tk(self.canvas,chart,pack_toolbar=False); self.toolbar.update(); self.toolbar.pack(fill="x"); self.refresh_chart()
        self.status=tk.StringVar(value="Select GEF/GFF files or a folder."); ttk.Label(self,textvariable=self.status,relief="sunken",anchor="w").pack(fill="x",side="bottom")

    def select_files(self):
        x=filedialog.askopenfilenames(title="Select GEF/GFF files",filetypes=[("GEF/GFF","*.GEF *.gef *.GFF *.gff"),("All files","*.*")])
        if x: self.files=sorted({Path(v) for v in x},key=lambda p:natural_ref_key(p.stem)); self._after_select()
    def select_folder(self):
        x=filedialog.askdirectory(title="Select folder containing GEF/GFF files")
        if x: self.files=collect_folder(Path(x)); self.output_dir=Path(x)/"CPT_Output"; self.output_var.set(str(self.output_dir)); self._after_select(set_output=False)
    def _after_select(self,set_output=True):
        if set_output:
            p=default_output(self.files)
            if p: self.output_dir=p; self.output_var.set(str(p))
        self.file_label.config(text=f"{len(self.files)} files selected"); self.status.set(f"Loaded {len(self.files)} CPT file(s). Press START ANALYSIS.")
    def choose_output(self):
        x=filedialog.askdirectory(title="Choose output folder")
        if x: self.output_dir=Path(x); self.output_var.set(x)
    def clear(self):
        self.files=[]; self.results=[]; self.errors=[]; self.pdf_by_ref={}; self.output_dir=self.pdf_dir=self.excel_path=None; self.output_var.set(""); self.file_label.config(text="0 files selected"); self.progress["value"]=0; self.progress_label.config(text="Ready"); self.summary.set("Maximum silt thickness: -")
        for i in self.tree.get_children(): self.tree.delete(i)
        for b in [self.open_selected_btn,self.open_pdfs_btn,self.open_excel_btn,self.open_output_btn]: b.config(state="disabled")
        self.refresh_chart(); self.status.set("Select GEF/GFF files or a folder.")
    def start(self):
        if not self.files: messagebox.showwarning("No files","Select one or more GEF/GFF files, or a folder first."); return
        out=self.output_var.get().strip()
        if not out:
            p=default_output(self.files)
            if not p: return
            out=str(p); self.output_var.set(out)
        try: gamma=float(self.gamma.get()); wt=float(self.wt.get())
        except ValueError: messagebox.showerror("Invalid settings","Unit weight and groundwater depth must be numeric."); return
        self.output_dir=Path(out); self.results=[]; self.errors=[]; self.pdf_by_ref={}; [self.tree.delete(i) for i in self.tree.get_children()]; self.progress["maximum"]=len(self.files); self.progress["value"]=0; self.start_btn.config(state="disabled")
        for b in [self.open_selected_btn,self.open_pdfs_btn,self.open_excel_btn,self.open_output_btn]: b.config(state="disabled")
        threading.Thread(target=self._worker,args=(self.output_dir,gamma,wt),daemon=True).start()
    def _worker(self,out,gamma,wt):
        pdfs=out/"PDFs"; pdfs.mkdir(parents=True,exist_ok=True); results=[]; errors=[]
        for i,p in enumerate(self.files,1):
            try:
                a=analyze_gef(p,gamma_soil=gamma,water_table_depth=wt); pdf=unique_pdf_path(pdfs,a.reference); generate_pdf(a,pdf); results.append(a); self.messages.put(("row",i,len(self.files),a,pdf))
            except Exception as e: errors.append((p.name,str(e))); self.messages.put(("error",i,len(self.files),p,str(e)))
        excel=export_excel(results,out/"CPT_Silt_Analysis.xlsx",errors=errors); self.messages.put(("done",out,pdfs,excel,results,errors))
    def _poll(self):
        try:
            while True:
                m=self.messages.get_nowait(); kind=m[0]
                if kind=="row":
                    _,i,total,a,pdf=m; r=analysis_record(a); self.pdf_by_ref.setdefault(a.reference,[]).append(Path(pdf)); start="NO SILT" if a.status=="NO SILT" else (f"{r['start_num']:.2f}" if r["start_num"] is not None else "REVIEW"); end=f"{r['end']:.2f}" if isinstance(r["end"],(int,float)) else "-"; thick=f"{r['thickness']:.2f}" if isinstance(r["thickness"],(int,float)) else "-"; sand=f"{r['sand']:.2f}" if isinstance(r["sand"],(int,float)) else "REVIEW"; self.tree.insert("","end",values=(a.reference,sand,start,end,thick,f"{r['test_depth']:.2f}",a.status)); self.progress["value"]=i; self.progress_label.config(text=f"{i} / {total}"); self.status.set(f"Analyzed {a.reference}: {start} / {thick}")
                elif kind=="error":
                    _,i,total,p,e=m; self.tree.insert("","end",values=(p.stem,"-","REVIEW","-","-","-","ERROR")); self.progress["value"]=i; self.progress_label.config(text=f"{i} / {total}"); self.status.set(f"Error in {p.name}: {e}")
                elif kind=="done":
                    _,out,pdfs,excel,results,errors=m; self.results=sorted(results,key=lambda a:natural_ref_key(a.reference)); self.errors=errors; self.output_dir=out; self.pdf_dir=pdfs; self.excel_path=excel; self.start_btn.config(state="normal"); self.open_pdfs_btn.config(state="normal" if pdfs.exists() else "disabled"); self.open_excel_btn.config(state="normal" if excel.exists() else "disabled"); self.open_output_btn.config(state="normal" if out.exists() else "disabled"); self._update_summary(); self.refresh_chart(); self.status.set(f"Finished {len(results)} CPT(s); {len(errors)} error(s). Excel: {excel}"); messagebox.showinfo("Analysis complete",f"Finished {len(results)} CPT file(s).\nErrors: {len(errors)}\n\nPDFs:\n{pdfs}\n\nExcel:\n{excel}")
        except queue.Empty: pass
        self.after(100,self._poll)
    def _update_summary(self):
        vals=[(a.reference,a.final_interval.thickness) for a in self.results if a.status=="VERIFIED" and a.final_interval]
        if not vals: self.summary.set(f"Maximum silt thickness: none detected | CPTs: {len(self.results)} | NO SILT: {sum(a.status=='NO SILT' for a in self.results)} | REVIEW: {sum(a.status=='REVIEW' for a in self.results)}"); return
        mx=max(v for _,v in vals); refs=[r for r,v in vals if abs(v-mx)<1e-9]; self.summary.set(f"MAXIMUM SILT THICKNESS: {mx:.2f} m at {', '.join(refs)} | CPTs: {len(self.results)} | NO SILT: {sum(a.status=='NO SILT' for a in self.results)} | REVIEW: {sum(a.status=='REVIEW' for a in self.results)}")
    def _selected_changed(self): self.open_selected_btn.config(state="normal" if self.tree.selection() and self.pdf_dir else "disabled")
    def open_selected(self):
        sel=self.tree.selection()
        if not sel: messagebox.showwarning("No selection","Select a CPT row first."); return
        ref=str(self.tree.item(sel[0],"values")[0]); paths=self.pdf_by_ref.get(ref,[]); p=paths[0] if paths else (self.pdf_dir/f"{ref}.pdf" if self.pdf_dir else None)
        if not p or not open_external_path(Path(p)): messagebox.showwarning("PDF unavailable","The selected CPT PDF was not found.")
    def open_pdfs(self):
        if not self.pdf_dir or not open_external_path(self.pdf_dir): messagebox.showwarning("PDFs unavailable","Run analysis first.")
    def open_excel(self):
        if not self.excel_path or not open_external_path(self.excel_path): messagebox.showwarning("Excel unavailable","Run analysis first.")
    def open_output(self):
        if not self.output_dir or not open_external_path(self.output_dir): messagebox.showwarning("Output unavailable","Run analysis first.")
    def _chart_data(self): return sorted_filtered(self.results,self.status_filter.get(),self.sort_by.get(),self.asc.get())
    def refresh_chart(self):
        ax=self.ax; ax.clear(); data=self._chart_data()
        if not data: ax.text(.5,.5,"Run analysis or change filters to display project charts.",ha="center",va="center",transform=ax.transAxes); ax.set_axis_off(); self.canvas.draw_idle(); return
        ax.set_axis_on(); rec=[analysis_record(a) for a in data]; refs=[r["reference"] for r in rec]; x=np.arange(len(rec)); typ=self.chart_type.get()
        silt=np.array([np.nan if r["thickness"] is None else r["thickness"] for r in rec],float); sand=np.array([np.nan if r["sand"] is None else r["sand"] for r in rec],float); start=np.array([np.nan if r["start_num"] is None else r["start_num"] for r in rec],float); test=np.array([r["test_depth"] for r in rec],float)
        if typ=="Bar":
            width=.36
            if self.show_sand.get(): ax.bar(x-width/2,sand,width,label="Sand thickness")
            if self.show_silt.get(): ax.bar(x+width/2,silt,width,label="Silt thickness")
            if self.show_start.get(): ax.plot(x,start,marker="o",lw=1,label="Silt start")
            if self.show_test.get(): ax.plot(x,test,marker=".",lw=1,label="Test depth")
        elif typ=="Layer Profile":
            ax.bar(x,sand,label="Sand / overlying layer"); ax.bar(x,np.nan_to_num(silt,nan=0),bottom=sand,label="Terminal silt layer"); ax.invert_yaxis(); ax.set_ylabel("Depth BGL (m)")
        elif typ=="Highest Silt Ranking":
            order=np.argsort(np.nan_to_num(silt,nan=-1))[::-1]; xx=np.arange(len(order)); ax.bar(xx,silt[order]); refs=[refs[i] for i in order]; x=xx; silt=silt[order]
        elif typ=="Histogram":
            vals=silt[np.isfinite(silt)]; ax.hist(vals,bins=min(20,max(5,int(np.sqrt(max(len(vals),1)))))); ax.set_xlabel("Silt thickness (m)"); ax.set_ylabel("Number of CPTs"); ax.set_title("Distribution of Silt Thickness"); self.fig.tight_layout(); self.canvas.draw_idle(); return
        elif typ=="Scatter: Silt Start vs Thickness":
            m=np.isfinite(start)&np.isfinite(silt); ax.scatter(start[m],silt[m]); ax.set_xlabel("Silt start depth BGL (m)"); ax.set_ylabel("Silt thickness (m)"); ax.set_title("Silt Start vs Thickness"); self.fig.tight_layout(); self.canvas.draw_idle(); return
        elif typ=="Coordinate Map":
            east=np.array([np.nan if not isinstance(r["easting"],(int,float)) else r["easting"] for r in rec],float); north=np.array([np.nan if not isinstance(r["northing"],(int,float)) else r["northing"] for r in rec],float); m=np.isfinite(east)&np.isfinite(north); sizes=25+100*np.nan_to_num(silt[m],nan=0); sc=ax.scatter(east[m],north[m],s=sizes,c=np.nan_to_num(silt[m],nan=0),cmap="viridis",alpha=.85); self.fig.colorbar(sc,ax=ax,label="Silt thickness (m)"); ax.set_xlabel("Easting"); ax.set_ylabel("Northing"); ax.set_title("CPT Coordinate Map - point size/color = silt thickness"); ax.ticklabel_format(style="plain",useOffset=False); self.fig.tight_layout(); self.canvas.draw_idle(); return
        else:
            if self.show_silt.get(): ax.plot(x,silt,marker=".",ms=4,lw=1,label="Silt thickness")
            if self.show_sand.get(): ax.plot(x,sand,lw=1,label="Sand thickness")
            if self.show_start.get(): ax.plot(x,start,lw=1,label="Silt start")
            if self.show_test.get(): ax.plot(x,test,lw=1,label="Test depth")
        if self.highlight_max.get() and np.any(np.isfinite(silt)) and typ not in {"Layer Profile"}:
            mi=int(np.nanargmax(silt)); ax.scatter([x[mi]],[silt[mi]],s=80,facecolors="none",edgecolors="black",linewidths=1.4,zorder=9); ax.annotate(f"MAX {silt[mi]:.2f} m\n{refs[mi]}",(x[mi],silt[mi]),xytext=(8,10),textcoords="offset points",fontsize=7,weight="bold")
        step=max(1,len(refs)//20); ticks=np.arange(len(refs))[::step]; ax.set_xticks(ticks); ax.set_xticklabels([refs[i] for i in ticks],rotation=55,ha="right",fontsize=7); ax.set_title(f"Full CPT Analysis - {typ}"); ax.set_ylabel("Depth / thickness (m)"); ax.grid(True,alpha=.22); ax.legend(loc="best"); self.fig.tight_layout(); self.canvas.draw_idle()
    def _reset_view(self): self.toolbar.home(); self.refresh_chart()
    def save_chart(self):
        if not self.results: messagebox.showwarning("No chart","Run analysis first."); return
        p=filedialog.asksaveasfilename(title="Save chart",defaultextension=".png",filetypes=[("PNG image","*.png")],initialfile="CPT_Full_Analysis_Chart.png")
        if p: self.fig.savefig(p,dpi=180,bbox_inches="tight"); self.status.set(f"Chart saved: {p}")


if __name__=="__main__": CPTApp().mainloop()

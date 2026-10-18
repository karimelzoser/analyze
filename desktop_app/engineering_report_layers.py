"""Complete engineering depth-layer appendix for native and original-PDF CPT reports.

Every listed interval is observed/screened, UNKNOWN or an explicit quality
limitation. Never convert missing sensor data into clean sand or exact USCS.
"""
from __future__ import annotations
from math import isfinite
from matplotlib.figure import Figure
from matplotlib.table import Table


def full_layer_pages(analysis,*,page_size=23):
    try:
        from engineering_layers import from_analysis
        profile=from_analysis(analysis)
        layers=list(profile.layers)
        observed_intervals=list(profile.silt_intervals)
        brief=list(profile.brief_exceedances)
        notes=list(profile.notes)
    except (AttributeError,TypeError,ValueError,IndexError) as exc:
        layers=[];observed_intervals=[];brief=[]
        notes=[f"Depth-layer extraction unavailable: {type(exc).__name__}: {exc}",
               "PDF-only sources may lack an auditable full numeric curve."]
    rows=[]
    for layer in layers:
        rows.append([str(layer.number),layer.kind,
                 f"{layer.start_m:.3f}",f"{layer.end_m:.3f}",
                 f"{layer.thickness_m:.3f}",
                 "Not observed" if layer.mean_ic is None else f"{layer.mean_ic:.3f}",
                 "UNKNOWN / unavailable" if layer.kind=="UNKNOWN" else layer.status])
    if not rows:
        rows=[["—","No full-depth numeric observations","—","—","—","—",
               "Source limitations recorded; see verification note"]]
    pages=[]
    parts=[rows[i:i+page_size] for i in range(0,len(rows),page_size)]
    for idx,part in enumerate(parts,1):
        fig=Figure(figsize=(8.27,11.69),dpi=150,facecolor="white")
        fig.text(.06,.963,"CPT FULL SOIL-BEHAVIOR DEPTH PROFILE",fontsize=14,
                 color="#153851",weight="bold")
        fig.text(.06,.94,f"{analysis.reference} · Page {idx}/{len(parts)}",
                 fontsize=9,color="#475569")
        fig.text(.06,.919,
              "All SBT categories are estimates from CPT Ic, NOT a lab USCS classification.",
              fontsize=8,color="#8b3f31")
        ax=fig.add_axes([.06,.27,.88,.615])
        ax.axis("off")
        headings=["#","SBT interpretation","Start BGL","End BGL",
                  "Thickness","Mean Ic","Data quality"]
        rows_all=[headings]+part
        # A one-row table must not expand to a half-page height. Use a
        # consistent ~0.035 figure-height per row, anchored to the top.
        table_height=min(.61,max(.073,.036*len(rows_all)))
        relative_height=table_height/.615
        tb=Table(ax,bbox=[0,1-relative_height,1,relative_height])
        widths=[.05,.27,.12,.12,.13,.10,.21]
        for i,row in enumerate(rows_all):
            for j,item in enumerate(row):
                shade="#173d59" if i==0 else "#fff3ea" if "UNKNOWN" in str(row[-1]) else "#f2f7fb" if i%2 else "#ffffff"
                cell=tb.add_cell(i,j,width=widths[j],height=1/len(rows_all),
                                 text=item,loc="left",facecolor=shade,edgecolor="#d0dbe6")
                cell.PAD=.02
                cell.get_text().set_fontsize(6.1 if j in (1,6) else 6.7)
                if i==0:
                    cell.get_text().set_color("white")
                    cell.get_text().set_weight("bold")
        ax.add_table(tb)
        fig.text(.06,.245,"OBSERVED SCREENING TOTALS",fontsize=9,weight="bold",color="#153851")
        valid_sum=sum(max(0,b-a) for a,b in observed_intervals)
        largest=max((max(0,b-a) for a,b in observed_intervals),default=0)
        summary=(f"Qualifying observed Ic>=2.60 intervals: {len(observed_intervals)}"
                 f"    |    cumulative: {valid_sum:.3f} m"
                 f"    |    maximum continuous: {largest:.3f} m"
                 f"    |    brief crossings: {len(brief)}")
        fig.text(.06,.224,summary,fontsize=7.7)
        if idx==len(parts):
            note=" | ".join(notes[:3])
            fig.text(.06,.181,"ENGINEERING LIMITATIONS",fontsize=9,
                     weight="bold",color="#153851")
            from textwrap import wrap
            lines=wrap(note or "No numerical quality notes",width=113,break_long_words=False)
            for k,line in enumerate(lines[:5]):
                fig.text(.06,.161-.014*k,line,fontsize=7.3,color="#334155")
            fig.text(.06,.055,"Original source may contain other soil classes; UNKNOWN means not measured, not clean sand.",
                     fontsize=7.3,color="#9a3412")
        pages.append(fig)
    return pages

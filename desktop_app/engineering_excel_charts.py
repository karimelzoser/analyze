"""Restore editable, native Excel engineering charts within ONE output workbook.

These are real xlsxwriter Excel chart objects referencing worksheet cells,
not static PNGs. All CPT values and the chart inputs remain auditable.
"""
from __future__ import annotations

import math


def _number(value):
    try:
        x=float(value)
        return x if math.isfinite(x) else None
    except (TypeError,ValueError):
        return None


def restore_project_charts(book, spatial, analyses, measurement_ranges=()):
    """Add full-project charts plus a representative set of raw CPT curves."""
    styles={
      "title":book.add_format({"font_name":"Aptos Display","font_size":17,
                                "bold":True,"font_color":"#18364f"}),
      "heading":book.add_format({"font_color":"white","bold":True,"bg_color":"#173e59",
                                 "font_name":"Aptos","text_wrap":True}),
      "note":book.add_format({"font_name":"Aptos","font_color":"#5c7083",
                              "font_size":10,"text_wrap":True})
    }
    sheet=book.add_worksheet("Charts")
    sheet.set_tab_color("#3179ad")
    sheet.set_column("A:X",10.4)
    sheet.set_column("AA:AQ",17.5)
    sheet.set_row(0,34)
    sheet.merge_range("A1:X2","CPT ENGINEERING | PROJECT CHARTS",styles["title"])
    sheet.merge_range("A3:X4",
        "Native Excel charts. Every chart is linked to the actual CPT analysis values below. "
        "Review is not a zero-thickness observation; SBT screening is not definitive USCS.",styles["note"])

    pairs={a.reference:a for a in analyses}
    data=[]
    for p in spatial:
        case=pairs.get(p.reference)
        reported=getattr(case,"final_interval",None) if case is not None else None
        sand=getattr(case,"sand_layer_thickness",None) if case is not None else None
        data.append((p.reference,p.maximum_m,p.cumulative_m,sand,p.depth,p.status,
                     p.x,p.y,reported.start if reported is not None else None,
                     reported.thickness if reported is not None else None))
    data.sort(key=lambda r:r[0])
    headers=["CPT reference","Max observed SBT screen (m)","Cumulative observed (m)",
             "Sand layer before silt (m)","CPT depth (m)","Status",
             "Easting","Northing","Silt start (m)","Reported silt thickness (m)"]
    for j,h in enumerate(headers):
        sheet.write(0,26+j,h,styles["heading"])
    for i,row in enumerate(data,1):
        for j,v in enumerate(row):
            if isinstance(v,(int,float)) and _number(v) is not None:
                sheet.write_number(i,26+j,float(v))
            elif v is None:
                sheet.write_blank(i,26+j,None)
            else:
                sheet.write_string(i,26+j,str(v))
    n=len(data)
    ranked=sorted((r for r in data if _number(r[1]) is not None),
                  key=lambda r:(-float(r[1]),r[0]))[:25]
    sheet.write(0,38,"Top 25 CPT",styles["heading"])
    sheet.write(0,39,"Max observed thickness (m)",styles["heading"])
    for i,row in enumerate(ranked,1):
        sheet.write_string(i,38,row[0])
        sheet.write_number(i,39,float(row[1]))
    statuses=["VERIFIED","NO SILT","REVIEW"]
    sheet.write(0,41,"Engineering result",styles["heading"])
    sheet.write(0,42,"Count",styles["heading"])
    for i,status in enumerate(statuses,1):
        sheet.write_string(i,41,status)
        sheet.write_number(i,42,sum(a.status==status for a in analyses))

    def frame(chart,title,xlabel=None,ylabel=None):
        chart.set_title({"name":title})
        chart.set_legend({"position":"bottom"})
        chart.set_style(10)
        chart.set_chartarea({"border":{"none":True},"fill":{"color":"#ffffff"}})
        chart.set_plotarea({"fill":{"color":"#f9fbfe"},"border":{"color":"#dce6ed"}})
        if xlabel:chart.set_x_axis({"name":xlabel,"name_font":{"size":9},"num_font":{"size":8}})
        if ylabel:chart.set_y_axis({"name":ylabel,"name_font":{"size":9},"num_font":{"size":8}})
        chart.set_size({"width":670,"height":380})
        return chart

    top=book.add_chart({"type":"bar"})
    if ranked:
        top.add_series({"name":"Maximum observed qualifying interval",
             "categories":["Charts",1,38,len(ranked),38],
             "values":["Charts",1,39,len(ranked),39],
             "fill":{"color":"#d85a49"},"border":{"none":True}})
    top.set_y_axis({"reverse":True,"name":"CPT reference","num_font":{"size":8}})
    top.set_x_axis({"name":"Observed maximum screening interval (m)"})
    frame(top,"25 largest observed soil-behaviour intervals")
    sheet.insert_chart("A6",top)

    trend=book.add_chart({"type":"line"})
    if n:
        for column,color,name in ((27,"#cd5d48","Max observed"),
                                  (28,"#267c90","Cumulative observed"),
                                  (29,"#b6a14a","Sand before silt")):
            trend.add_series({"name":name,
                  "categories":["Charts",1,26,n,26],
                  "values":["Charts",1,column,n,column],
                  "line":{"color":color,"width":2},
                  "marker":{"type":"none"}})
    frame(trend,"Full-project layer thicknesses","CPT references in natural dataset order","Thickness (m)")
    trend.set_x_axis({"num_font":{"rotation":270,"size":7}})
    sheet.insert_chart("N6",trend)

    donut=book.add_chart({"type":"doughnut"})
    donut.add_series({"name":"Classification status",
                     "categories":["Charts",1,41,3,41],
                     "values":["Charts",1,42,3,42],
                     "points":[{"fill":{"color":"#267e60"}},
                               {"fill":{"color":"#377eb8"}},
                               {"fill":{"color":"#dc7c36"}}]})
    donut.set_hole_size(53)
    frame(donut,"Classification quality / review workload")
    sheet.insert_chart("A28",donut)

    depth=book.add_chart({"type":"scatter","subtype":"straight_with_markers"})
    if n:
        depth.add_series({"name":"Observed max silt-like screening interval",
               "categories":["Charts",1,30,n,30],
               "values":["Charts",1,27,n,27],
               "line":{"none":True},"marker":{"type":"circle","size":5,
                                                "border":{"none":True},
                                                "fill":{"color":"#ca7660"}}})
    frame(depth,"Silt-like interval vs sounding depth","Sounding depth (m)","Maximum interval (m)")
    sheet.insert_chart("N28",depth)
    sheet.freeze_panes(4,0)
    sheet.set_landscape();sheet.fit_to_pages(1,0)

    # Raw CPT curves displayed in a *separate* native Excel chart sheet,
    # sourced directly from the complete depth-by-depth CPT Measurements.
    curves=book.add_worksheet("CPT Curves")
    curves.set_tab_color("#2c8094")
    curves.set_column("A:X",10.5)
    curves.merge_range("A1:X2","CPT DEPTH CURVES | QC · FR · IC · QTN",styles["title"])
    curves.merge_range("A3:X4",
        "These charts draw selected CPT curves directly from CPT Measurements. "
        "The complete records for EVERY CPT remain in that sheet; invalid readings "
        "remain visibly unknown. Further filtering is available in the desktop chart.",styles["note"])
    measurement_ranges=list(measurement_ranges)
    # Select up to four CPTs with most observed thickness, without inventing a
    # value where none was measured. Fall back to first raw sounding if needed.
    thickness=dict((p.reference,p.maximum_m or 0) for p in spatial)
    selected=sorted(measurement_ranges,key=lambda item:
                    (-float(thickness.get(item[0],0)),item[0]))[:4]
    labels=[("qc",2,"qc (MPa)"),("fr",6,"Fr (%)"),
            ("ic",8,"Ic (-)"),("qtn",7,"Qtn (-)")]
    locations=["A6","N6","A28","N28"]
    hues=["#266c91","#c68e43","#be4c55","#64886c"]
    for (code,metric_index,title),cell in zip(labels,locations):
        graph=book.add_chart({"type":"scatter","subtype":"straight"})
        for i,entry in enumerate(selected):
            if len(entry)==4:ref,sheetname,first,last=entry
            else:ref,first,last=entry;sheetname="CPT Measurements"
            graph.add_series({"name":ref,
                     "categories":[sheetname,first,metric_index,last,metric_index],
                     "values":[sheetname,first,1,last,1],
                     "line":{"color":hues[i%len(hues)],"width":1.7}})
        frame(graph,"Observed CPT "+title+" profile",title,"Corrected depth BGL (m)")
        graph.set_y_axis({"reverse":True,"name":"Corrected depth BGL (m)"})
        curves.insert_chart(cell,graph)
    return {"chart_count":8,"source_point_count":n,
            "raw_cpt_curves":[r[0] for r in selected]}

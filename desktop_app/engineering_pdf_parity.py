"""PDF visual regression metrics against approved original report pages.

Measures exact rendered pixel similarity at matched page geometry. It does not
imply that a low error means numerical correctness, nor that a high error alone
identifies calculation disagreement.
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
try:
    import pymupdf
except ImportError:
    import fitz as pymupdf

def pdf_visual_regression(reference:str|Path,generated:str|Path,output_dir:str|Path,
                          dpi:int=110, pages:int=1)->dict:
    if dpi<60 or dpi>250 or pages<1:
        raise ValueError("Invalid rendering settings")
    directory=Path(output_dir);directory.mkdir(parents=True,exist_ok=True)
    ref=pymupdf.open(str(reference));gen=pymupdf.open(str(generated))
    results=[]
    try:
        for n in range(min(pages,ref.page_count,gen.page_count)):
            ra=ref[n];gb=gen[n]
            a=ra.get_pixmap(matrix=pymupdf.Matrix(dpi/72,dpi/72),alpha=False)
            b=gb.get_pixmap(matrix=pymupdf.Matrix(dpi/72,dpi/72),alpha=False)
            geometry_compatible=a.width==b.width and a.height==b.height
            if geometry_compatible:
                p=np.frombuffer(a.samples,dtype=np.uint8).reshape(a.height,a.width,a.n).astype(np.int16)
                q=np.frombuffer(b.samples,dtype=np.uint8).reshape(b.height,b.width,b.n).astype(np.int16)
                delta=np.abs(p-q)
                mean=float(np.mean(delta)/255)
                pixels=float(np.mean(np.any(delta>20,axis=2)))
                hist=(np.minimum(255,delta*4)).astype(np.uint8)
                from PIL import Image
                output=directory/f"page_{n+1}_difference.png"
                Image.fromarray(hist[:,:,:3]).save(output)
            else:
                mean=pixels=None;output=None
            results.append({
                "page":n+1,"reference_dimensions_points":[round(ra.rect.width,2),round(ra.rect.height,2)],
                "generated_dimensions_points":[round(gb.rect.width,2),round(gb.rect.height,2)],
                "geometry_compatible":geometry_compatible,"mean_normalized_absolute_pixel_error":mean,
                "fraction_pixels_changed_over_20":pixels,
                "difference_image":str(output) if output else None
            })
    finally:
        ref.close();gen.close()
    verdict=bool(results) and all(r["geometry_compatible"] and r["mean_normalized_absolute_pixel_error"]<.002
                                  for r in results)
    summary={"reference":str(reference),"generated":str(generated),
             "exact_layout_near_match":verdict,"pages_tested":len(results),
             "pages":results,
             "engineering_note":"Pixel comparison is a fidelity metric, not independent Ic, soil or foundation formula validation. A human must approve any changed print layout."}
    (directory/"pdf_visual_regression.json").write_text(json.dumps(summary,indent=2))
    return summary


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("reference");p.add_argument("generated");p.add_argument("out")
    p.add_argument("--pages",type=int,default=1)
    a=p.parse_args()
    result=pdf_visual_regression(a.reference,a.generated,a.out,pages=a.pages)
    print(json.dumps(result,indent=2))

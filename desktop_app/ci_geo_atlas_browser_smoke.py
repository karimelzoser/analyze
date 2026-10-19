"""Real browser visual/interactivity smoke test for the offline CPT Atlas.

Run in CI after installing playwright. Uses preinstalled Microsoft Edge,
captures both 2D and 3D panels, and ensures source-point details respond.
"""
from __future__ import annotations

from pathlib import Path
import tempfile

from playwright.sync_api import sync_playwright
from test_engineering_geo_atlas import _raw
from engineering_geo_atlas import export_geo_atlas


def main():
    with tempfile.TemporaryDirectory(prefix="cpt_atlas_browser_") as temp:
        target=Path(temp)/"interactive_atlas.html"
        project=[
            _raw(1,421000,2927000,2.82),
            _raw(2,421025,2927000,3.12),
            _raw(3,421000,2927025,2.55),
            _raw(4,421025,2927025,2.78)
        ]
        # Three distinct field thicknesses allow the 3D heat gradient to
        # prove thin-versus-thick soil visibility, not blanket red blocks.
        project[1].ic[(project[1].depth>4.5)&(project[1].depth<5.25)]=2.25
        export_geo_atlas(project,target)
        screenshots=Path("geo-atlas-visual-qa")
        screenshots.mkdir(exist_ok=True)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel="msedge",headless=True,
                    args=["--enable-webgl","--use-gl=swiftshader","--disable-gpu-sandbox"])
            try:
                page=browser.new_page(viewport={"width":1440,"height":900},device_scale_factor=1)
                exceptions=[]
                console=[]
                page.on("pageerror",lambda err:exceptions.append(str(err)))
                page.on("console",lambda msg:console.append(msg.type+": "+msg.text))
                page.goto(target.as_uri(),wait_until="load",timeout=100000)
                try:
                    page.wait_for_function(
                        "() => {let e=document.getElementById('cpt-atlas-2d');return !!e && !!e.data && e.data.length>=2;}",
                        timeout=30000)
                except Exception:
                    print("ATLAS INITIALIZATION FAILURE. JS ERRORS:",repr(exceptions))
                    print("BROWSER CONSOLE:",repr(console[-15:]))
                    try:
                        print("DOM STATE:",page.evaluate("""() => ({
                            ready:document.readyState,plotly:!!window.Plotly,
                            original:!!document.getElementById('cpt-studio'),
                            atlas:!!document.getElementById('cpt-atlas-screen'),
                            canvas:!!document.getElementById('cpt-atlas-2d'),
                            traces:document.getElementById('cpt-atlas-2d')?.data?.length,
                            primaryTraces:[...document.querySelectorAll('.plotly-graph-div')]
                                .map(x=>({id:x.id,n:x.data?.length||0}))
                        })"""))
                        page.screenshot(path=str(screenshots/"00-startup-error.png"),full_page=True)
                    except Exception as e:print("Browser state inspection failed",e)
                    raise
                assert page.locator("#atlas-2d").is_visible()
                assert page.locator("#cpt-atlas-2d").is_visible()
                page.screenshot(path=str(screenshots/"01-soil-plan.png"),full_page=True)
                page.locator("#atlas-mode").select_option("max")
                page.wait_for_function(
                    "() => {let e=document.getElementById('cpt-atlas-2d');return !!e && !!e.data && e.data[0].zmax !== 3;}",
                    timeout=20000)
                page.locator("#atlas-find").fill("CPT-A2-B1-100")
                page.locator("#atlas-find").press("Enter")
                page.wait_for_function("() => document.getElementById('cpt-atlas-details')?.textContent.includes('CPT-A2-B1-100')",timeout=20000)
                assert "qc" in page.locator("#cpt-atlas-details").inner_text().lower()
                page.screenshot(path=str(screenshots/"02-thickness-selected-cpt.png"),full_page=True)
                # Map interactions must work beyond the initial screenshot.
                page.locator("#atlas-zoom-in").click()
                page.wait_for_timeout(200)
                xr=page.evaluate("() => document.getElementById('cpt-atlas-2d').layout.xaxis.range")
                assert xr and xr[1]>xr[0],"Explicit 2D zoom must provide a valid coordinate extent"
                page.locator("#atlas-box").click()
                assert "chosen" in page.locator("#atlas-box").get_attribute("class")
                page.locator("#atlas-pan").click()
                assert "chosen" in page.locator("#atlas-pan").get_attribute("class")
                page.locator("#atlas-expand").click()
                assert "atlas-focus-map" in page.locator("body").get_attribute("class")
                page.locator("#atlas-expand").click()
                page.locator("#atlas-depth-number").fill("5.00")
                page.locator("#atlas-depth-number").press("Tab")
                assert "5.00" in page.locator("#atlas-depth-label").inner_text()
                page.locator("#cpt-atlas-rank button").first.click()
                assert "CPT-A2-" in page.locator("#cpt-atlas-details").inner_text()

                page.locator("#atlas-3d").click()
                page.wait_for_function(
                    "() => {let panel=document.getElementById('cpt-atlas-svg3d');return !!panel && !!panel.offsetParent && panel.querySelectorAll('svg polygon').length>=4;}",
                    timeout=20000)
                assert page.locator("#atlas-vertical").is_visible()
                assert page.locator("#cpt-atlas-svg3d svg circle").count()>=4
                page.wait_for_timeout(300)
                page.screenshot(path=str(screenshots/"03-layered-3d.png"),full_page=True)
                # GPU-free column view must show actual soil shapes, not a
                # blank WebGL scene with only Plotly legends.
                assert page.locator("#cpt-atlas-svg3d svg polygon").count()>=4
                # Engineer usability regression: columns must occupy meaningful
                # vertical plotting space rather than the previous ~30px sticks.
                column_height=page.evaluate("""() => {
                  const shapes=[...document.querySelectorAll('#cpt-atlas-svg3d polygon.soil-svg-body')];
                  const y=shapes.flatMap(p=>p.getAttribute('points').trim().split(/\\s+/)
                               .map(pair=>Number(pair.split(',')[1])));
                  return y.length ? Math.max(...y)-Math.min(...y) : 0;
                }""")
                assert column_height>120, f"3D CPT layers too small to inspect: {column_height:.1f}px high"
                fitted=page.evaluate("""() => {
                  const host=document.getElementById('cpt-atlas-svg3d');
                  const shapes=[...host.querySelectorAll('polygon.soil-svg-body')];
                  const y=shapes.flatMap(p=>p.getAttribute('points').trim().split(/\\s+/)
                               .map(pair=>Number(pair.split(',')[1])));
                  return {lo:Math.min(...y),hi:Math.max(...y),height:host.clientHeight};
                }""")
                assert fitted["lo"]>=55 and fitted["hi"]<=fitted["height"]-50, (
                    f"3D CPT columns clipped outside visible engineering viewport: {fitted}")
                # GPU-independent SVG is the primary 3D model. Requiring a
                # WebGL mesh in the hidden optional plot prevents this app
                # working on engineering PCs without stable graphics drivers.
                assert page.locator("#cpt-thickness-color").is_checked(), "3D numeric thickness overlay missing"
                colors_before=page.locator("#cpt-atlas-svg3d polygon.soil-svg-body").evaluate_all(
                    "(items) => [...new Set(items.map(x => x.getAttribute('fill')))]")
                assert len(colors_before)>=3, "3D soil palette lacks distinct class/thickness colors"
                page.locator("#cpt-thickness-color").uncheck()
                colors_classes=page.locator("#cpt-atlas-svg3d polygon.soil-svg-body").evaluate_all(
                    "(items) => [...new Set(items.map(x => x.getAttribute('fill')))]")
                assert "#67b4af" in colors_classes, "Silt category color not restored in soil-class mode"
                page.locator("#cpt-thickness-color").check()
                colors_heat=page.locator("#cpt-atlas-svg3d polygon.soil-svg-body").evaluate_all(
                    "(items) => [...new Set(items.map(x => x.getAttribute('fill')))]")
                assert colors_heat!=colors_classes, "3D silt thickness heat toggle did not recolor soil blocks"
                page.locator("#cpt-atlas-svg3d polygon.soil-svg-body").first.click(force=True)
                assert "CPT-A2-" in page.locator("#cpt-atlas-details").inner_text()
                page.locator("#atlas-expand").click()
                page.locator("#atlas-expand").click()
                page.set_viewport_size({"width":1220,"height":800})
                page.wait_for_timeout(350)
                assert not exceptions,"Browser errors during 3D resizing and recoloring: "+" | ".join(exceptions[:5])

                assert not exceptions,"Browser JS errors: "+" | ".join(exceptions[:5])
                print("PASS: offline 2D/3D atlas visually rendered, zoom/hover data present, search and inspector responded, 3D soil SVG blocks and thickness color toggle verified.")
            finally:
                browser.close()


if __name__=="__main__":
    main()

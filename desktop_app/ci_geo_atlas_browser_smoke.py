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
        export_geo_atlas(project,target)
        screenshots=Path("geo-atlas-visual-qa")
        screenshots.mkdir(exist_ok=True)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(channel="msedge",headless=True,
                    args=["--enable-webgl","--use-gl=swiftshader","--disable-gpu-sandbox"])
            try:
                page=browser.new_page(viewport={"width":1440,"height":900},device_scale_factor=1)
                exceptions=[]
                page.on("pageerror",lambda err:exceptions.append(str(err)))
                page.goto(target.as_uri(),wait_until="load",timeout=100000)
                page.wait_for_function(
                    "() => {let e=document.getElementById('cpt-atlas-2d');return !!e && !!e.data && e.data.length>=2;}",
                    timeout=100000)
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
                page.wait_for_function("() => !document.getElementById('cpt-atlas-screen')?.classList.contains('atlas-hide') && !document.getElementById('cpt-atlas-2d')?.offsetParent",timeout=20000)
                page.wait_for_timeout(600)
                page.screenshot(path=str(screenshots/"03-layered-3d.png"),full_page=True)
                mesh_count=page.evaluate(
                    "() => Array.from(document.querySelectorAll('.plotly-graph-div')).filter(x=>x.data).flatMap(x=>x.data).filter(t=>t.type==='mesh3d').length")
                assert mesh_count>=1,"Expected actual WebGL 3D soil meshes"
                assert page.locator("#cpt-thickness-color").is_checked(),"3D must support numeric thickness color mode"
                page.locator("#cpt-thickness-color").uncheck()
                page.locator("#cpt-thickness-color").check()
                page.wait_for_timeout(300)
                assert not exceptions,"Browser errors during 3D block recoloring: "+" | ".join(exceptions[:5])

                assert not exceptions,"Browser JS errors: "+" | ".join(exceptions[:5])
                print("PASS: offline 2D/3D atlas visually rendered, zoom/hover data present, search and inspector responded, 3D mesh loaded.")
            finally:
                browser.close()


if __name__=="__main__":
    main()

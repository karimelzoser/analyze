from __future__ import annotations

import math
import re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional, Tuple

import numpy as np

try:
    import pymupdf as fitz
except ImportError:  # compatibility with older PyMuPDF
    import fitz  # type: ignore

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

from cpt_core import CPTAnalysis, SiltInterval, classify_ic, round_01


PDF_IC_THRESHOLD = 2.60
PDF_MIN_LAYER_THICKNESS = 0.05
PDF_MAX_SMALL_GAP = 0.06
PDF_TERMINAL_EXTENSION = 0.15


def _as_float(value: str | None) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except Exception:
        return None


def _clean_lines(text: str) -> list[str]:
    return [x.strip() for x in text.replace("\r", "").split("\n") if x.strip()]


def _block_value(page, label: str) -> str:
    """Read a value next to/below a known report label without OCR."""
    label_l = label.lower()
    blocks = []
    for b in page.get_text("blocks"):
        rect = fitz.Rect(b[:4])
        lines = _clean_lines(str(b[4]))
        if lines:
            blocks.append((rect, lines))

    for rect, lines in blocks:
        hit = None
        for idx, line in enumerate(lines):
            if label_l in line.lower():
                hit = idx
                if ":" in line:
                    rhs = line.split(":", 1)[1].strip()
                    if rhs:
                        return rhs
                if idx + 1 < len(lines):
                    nxt = lines[idx + 1].strip()
                    if nxt and not nxt.endswith(":"):
                        return nxt
                break
        if hit is None:
            continue

        yc = (rect.y0 + rect.y1) / 2.0
        candidates = []
        for r2, l2 in blocks:
            if r2 == rect or r2.x0 <= rect.x0 + 35:
                continue
            yc2 = (r2.y0 + r2.y1) / 2.0
            if abs(yc2 - yc) <= max(8.0, rect.height * 0.75):
                candidates.append((r2.x0, l2[0]))
        if candidates:
            return min(candidates, key=lambda x: x[0])[1].strip()
    return ""


def _parse_pdf_metadata(page, path: Path) -> dict:
    ref = _block_value(page, "Test Location")
    if not ref:
        stem = re.sub(r"^P\d+_", "", path.stem, flags=re.I)
        ref = re.sub(r"\(\d+\)$", "", stem).strip()

    ground = _as_float(_block_value(page, "Ground Elevation"))
    easting = northing = None
    text = page.get_text("text")
    m = re.search(
        r"Coordinates\s*:\s*\n?\s*([-+]?\d+(?:\.\d+)?)\s*\n\s*([-+]?\d+(?:\.\d+)?)",
        text,
        flags=re.I,
    )
    if m:
        easting, northing = float(m.group(1)), float(m.group(2))
    else:
        vals = []
        for w in page.get_text("words"):
            v = _as_float(w[4])
            if v is not None and abs(v) > 1000:
                vals.append(v)
        if len(vals) >= 2:
            easting, northing = vals[-2], vals[-1]

    return {
        "reference": ref,
        "project_id": "",
        "project_name": _block_value(page, "Project"),
        "client": _block_value(page, "Client"),
        "location": "",
        "main_contractor": _block_value(page, "Main Contractor"),
        "cone_id": _block_value(page, "Cone ID"),
        "ground_elevation": ground,
        "easting": easting,
        "northing": northing,
        "test_date": _block_value(page, "Test Date"),
        "file_date": "",  # source PDF reports a test date, not GEF FILEDATE
        "area_ratio": None,
        "standard": "PDF vector report",
        "input_type": "PDF",
        "source_quality": "VECTOR PDF",
        "gamma_soil": None,
        "water_table_depth": None,
    }


def _find_ic_panel_and_trace(page):
    drawings = page.get_drawings()
    page_w = float(page.rect.width)
    panels = []
    for idx, d in enumerate(drawings):
        r = d["rect"]
        color = d.get("color")
        width = float(d.get("width") or 0.0)
        if (
            r.x0 > page_w * 0.60
            and 110.0 < r.width < 190.0
            and 300.0 < r.height < 480.0
            and color is not None
            and max(abs(float(c)) for c in color) < 0.05
            and 0.70 < width < 1.20
        ):
            panels.append((idx, d))

    for _, panel in panels:
        pr = panel["rect"]
        candidates = []
        for idx, d in enumerate(drawings):
            r = d["rect"]
            items = d.get("items", [])
            if not items:
                continue
            if (
                r.x0 >= pr.x0 - 3.0
                and r.x1 <= pr.x1 + 3.0
                and r.y0 >= pr.y0 - 2.0
                and r.y1 <= pr.y1 + 2.0
                and len(items) >= 120
                and r.y1 - r.y0 > 40.0
                and r.x1 - r.x0 > 8.0
                and all(it[0] == "l" for it in items)
            ):
                candidates.append((idx, d))
        if candidates:
            trace = max(candidates, key=lambda pair: len(pair[1]["items"]))[1]
            if len(trace["items"]) >= 200:
                return pr, trace
    raise ValueError("Native vector Ic panel/trace not found")


def _axis_level_limits(page, panel) -> Tuple[float, float]:
    """Infer top/bottom level labels but anchor geometry to panel borders."""
    groups: dict[float, list[Tuple[float, float]]] = {}
    for w in page.get_text("words"):
        x0, y0, x1, y1, txt = w[:5]
        val = _as_float(txt)
        if val is None or not (-100.0 <= val <= 100.0):
            continue
        if panel.x0 - 28.0 <= x1 <= panel.x0 + 3.0 and panel.y0 - 12.0 <= (y0 + y1) / 2.0 <= panel.y1 + 12.0:
            groups.setdefault(round(float(x1), 1), []).append(((y0 + y1) / 2.0, val))

    best = None
    best_score = float("inf")
    for pairs in groups.values():
        if len(pairs) < 5:
            continue
        ys = [p[0] for p in pairs]
        if max(ys) - min(ys) < panel.height * 0.70:
            continue
        score = abs(min(ys) - panel.y0) + abs(max(ys) - panel.y1)
        if score < best_score:
            best_score = score
            top_pair = min(pairs, key=lambda p: p[0])
            bottom_pair = max(pairs, key=lambda p: p[0])
            best = (float(top_pair[1]), float(bottom_pair[1]))

    if best is not None and best[0] > best[1]:
        return best
    return 10.0, -10.0


def _extract_ic_trace(page, ground_elevation: float) -> Tuple[np.ndarray, np.ndarray]:
    panel, trace = _find_ic_panel_and_trace(page)
    level_top, level_bottom = _axis_level_limits(page, panel)

    pts: list[Tuple[float, float]] = []
    for item in trace["items"]:
        if item[0] != "l":
            continue
        if not pts:
            pts.append((float(item[1].x), float(item[1].y)))
        pts.append((float(item[2].x), float(item[2].y)))

    rows = []
    for x, y in pts:
        ic = 5.0 * (x - panel.x0) / max(panel.x1 - panel.x0, 1e-9)
        level = level_top + (level_bottom - level_top) * (y - panel.y0) / max(panel.y1 - panel.y0, 1e-9)
        depth = float(ground_elevation) - float(level)
        if math.isfinite(depth) and math.isfinite(ic) and -0.10 <= depth <= 50.0 and -0.20 <= ic <= 5.30:
            rows.append((depth, ic))

    arr = np.asarray(rows, dtype=float)
    if len(arr) < 100:
        raise ValueError("Insufficient native vector Ic points")

    violations = int(np.count_nonzero(np.diff(arr[:, 0]) < -0.003))
    if violations > max(3, len(arr) // 100):
        arr = arr[np.argsort(arr[:, 0], kind="stable")]

    arr = arr[arr[:, 0] >= -0.02]
    if len(arr) < 50:
        raise ValueError("Insufficient valid Ic trace after depth filtering")
    return arr[:, 0], arr[:, 1]


def _median_filter(values: np.ndarray, width: int) -> np.ndarray:
    if width <= 1:
        return np.asarray(values, dtype=float).copy()
    half = width // 2
    out = np.empty_like(values, dtype=float)
    for i in range(len(values)):
        out[i] = float(np.nanmedian(values[max(0, i-half): min(len(values), i+half+1)]))
    return out


def _round_graph_01m(value: float) -> float:
    """Snap PDF-derived depth to the graph's meaningful 0.01 m resolution."""
    return float(Decimal(str(float(value))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _make_interval(start_raw: float, end_raw: float, source_end_raw: float) -> SiltInterval:
    # Otherwise identical PDF exports can shift vector coordinates by fractions
    # of a millimetre. The source graph is sampled at about 0.01 m, so suppress
    # sub-centimetre export jitter before applying the project's 0.10 m rule.
    start = round_01(_round_graph_01m(start_raw))
    end = round_01(_round_graph_01m(end_raw))
    return SiltInterval(
        start=start,
        end=end,
        thickness=round_01(max(0.0, end - start)),
        start_raw=float(start_raw),
        end_raw=float(end_raw),
        thickness_raw=float(max(0.0, end_raw - start_raw)),
        source_end_raw=float(source_end_raw),
    )


def _detect_pdf_interval(
    depth: np.ndarray,
    ic: np.ndarray,
    threshold: float,
    smooth_width: int,
    max_gap: float,
) -> Tuple[Optional[SiltInterval], list[Tuple[float, float]]]:
    work = _median_filter(ic, smooth_width)
    state = np.isfinite(work) & (work >= threshold)

    i = 0
    while i < len(state):
        if state[i]:
            i += 1
            continue
        j = i
        while j < len(state) and not state[j]:
            j += 1
        if i > 0 and j < len(state) and float(depth[j] - depth[i-1]) <= max_gap:
            state[i:j] = True
        i = j

    runs: list[Tuple[int, int]] = []
    i = 0
    while i < len(state):
        if not state[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(state) and state[j+1]:
            j += 1
        if float(depth[j] - depth[i]) >= PDF_MIN_LAYER_THICKNESS:
            runs.append((i, j))
        i = j + 1

    all_intervals = [(float(depth[a]), float(depth[b])) for a, b in runs]
    if not runs:
        return None, all_intervals

    a, b = runs[-1]
    start_raw = float(depth[a])
    source_end = float(depth[b])
    test_end = float(depth[-1])
    end_raw = test_end if (test_end - source_end) <= PDF_TERMINAL_EXTENSION else source_end
    return _make_interval(start_raw, end_raw, source_end), all_intervals


def _same_interval(a: Optional[SiltInterval], b: Optional[SiltInterval]) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return (a.start, a.end, a.thickness) == (b.start, b.end, b.thickness)


def _review_analysis(path: Path, metadata: dict, note: str) -> CPTAnalysis:
    depth = np.asarray([0.0], dtype=float)
    nan = np.asarray([np.nan], dtype=float)
    metadata = dict(metadata)
    metadata.update({"records": 0, "end_depth_header": 0.0, "source_quality": "UNSUPPORTED/SCANNED PDF"})
    return CPTAnalysis(
        path,
        str(metadata.get("reference") or path.stem),
        metadata,
        depth,
        nan.copy(), nan.copy(), nan.copy(), nan.copy(), nan.copy(), nan.copy(), nan.copy(),
        np.asarray([False]),
        ["Unknown"],
        None,
        None,
        None,
        "REVIEW",
        note,
        [],
        None,
    )


def analyze_pdf(path: str | Path) -> CPTAnalysis:
    """Analyze a project CPT PDF locally from its native vector Ic trace.

    No OCR or cloud service is used. Scanned/unsupported PDFs become REVIEW;
    the engine never estimates a silt layer from an unverified image.
    """
    path = Path(path)
    doc = fitz.open(path)
    if doc.page_count < 1:
        raise ValueError("Empty PDF")

    first_metadata = _parse_pdf_metadata(doc[0], path)
    selected = None
    last_error = ""
    for page in doc:
        text = page.get_text("text")
        if "Soil Behaviour Type Index" not in text and "Soil behavior type index" not in text:
            continue
        metadata = _parse_pdf_metadata(page, path)
        ground = metadata.get("ground_elevation")
        if not isinstance(ground, (int, float)):
            last_error = "Ground elevation could not be read from native PDF text."
            continue
        try:
            depth, ic = _extract_ic_trace(page, float(ground))
            selected = (metadata, depth, ic)
            break
        except Exception as exc:
            last_error = str(exc)

    if selected is None:
        note = (
            "PDF input could not be verified from the native vector Soil Behaviour Type Index (Ic) chart. "
            "This can occur with scanned/image-only PDFs or an unsupported report template. "
            "No interval was guessed; manual review or the original GEF/GFF is required."
        )
        if last_error:
            note += f" Parser detail: {last_error}"
        return _review_analysis(path, first_metadata, note)

    metadata, depth, ic = selected
    metadata = dict(metadata)
    metadata.update({"records": int(len(depth)), "end_depth_header": float(depth[-1])})

    p1, intervals = _detect_pdf_interval(depth, ic, PDF_IC_THRESHOLD, 1, 0.05)
    p2, _ = _detect_pdf_interval(depth, ic, PDF_IC_THRESHOLD, 3, PDF_MAX_SMALL_GAP)

    if p1 is None and p2 is None:
        final, status = None, "NO SILT"
        note = "PDF vector verification: two independent Ic-trace passes found no sustained qualifying Ic >= 2.60 interval."
    elif _same_interval(p1, p2):
        final, status = p1, "VERIFIED"
        note = "PDF vector verification: the native Ic trace was reconstructed from vector geometry and two independent passes agree at 0.10 m reporting resolution."
    else:
        specs = [
            (2.60, 1, .05), (2.60, 3, .06), (2.58, 3, .07), (2.62, 3, .07),
            (2.60, 5, .06), (2.59, 5, .07), (2.61, 5, .07), (2.60, 7, .08),
        ]
        candidates = []
        for threshold, smooth, gap in specs:
            z, _ = _detect_pdf_interval(depth, ic, threshold, smooth, gap)
            candidates.append(("NO SILT", None) if z is None else (f"{z.start:.1f}/{z.end:.1f}/{z.thickness:.1f}", z))
        counts: dict[str, int] = {}
        for label, _ in candidates:
            counts[label] = counts.get(label, 0) + 1
        best_label, best_count = max(counts.items(), key=lambda item: item[1])
        if best_count >= 5:
            if best_label == "NO SILT":
                final, status = None, "NO SILT"
            else:
                final = next(z for label, z in candidates if label == best_label and z is not None)
                status = "VERIFIED"
            note = f"PDF vector verification: primary passes differed; {best_count}/8 sensitivity checks converged on {best_label}."
        else:
            final, status = None, "REVIEW"
            note = "PDF vector trace was extracted, but independent interpretation passes did not converge. Manual review is required."

    note += " PDF-derived interpretation has lower source confidence than raw GEF/GFF and is used only when raw numerical data is unavailable."

    nan = np.full(len(depth), np.nan, dtype=float)
    labels = [classify_ic(float(v)) for v in ic]
    return CPTAnalysis(
        path,
        str(metadata.get("reference") or path.stem),
        metadata,
        np.asarray(depth, dtype=float),
        nan.copy(), nan.copy(), nan.copy(), nan.copy(), nan.copy(), nan.copy(),
        np.asarray(ic, dtype=float),
        np.isfinite(ic),
        labels,
        p1,
        p2,
        final,
        status,
        note,
        intervals,
        None,
    )


def _fmt(value, digits=2, suffix="") -> str:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return f"{float(value):.{digits}f}{suffix}"
    return "-"


def _pdf_analysis_figure(a: CPTAnalysis) -> Figure:
    fig = Figure(figsize=(8.27, 11.69), dpi=150, facecolor="white")
    ax = fig.add_subplot(111)
    ax.axis("off")
    md = a.metadata
    z = a.final_interval
    ground = md.get("ground_elevation") if isinstance(md.get("ground_elevation"), (int, float)) else None
    start_rl = float(ground) - z.start if z and ground is not None else None
    end_rl = float(ground) - z.end if z and ground is not None else None

    fig.text(.07, .955, "CPT PDF ANALYSIS SUMMARY", fontsize=16, weight="bold", color="#0B1F33")
    fig.text(.07, .927, a.reference, fontsize=11, weight="bold", color="#334155")
    fig.text(.93, .949, "PDF VECTOR INPUT", ha="right", fontsize=8.5, weight="bold", color="#2563EB")

    rows = [
        ["Verification status", a.status],
        ["Source quality", str(md.get("source_quality") or "PDF")],
        ["Ground elevation", _fmt(ground, 2, " m")],
        ["Reconstructed sounding depth", _fmt(a.test_depth_raw, 3, " m")],
        ["Silt start - reported", "NO SILT" if a.status == "NO SILT" else (_fmt(z.start, 2, " m") if z else "REVIEW")],
        ["Silt start RL - reported", _fmt(start_rl, 2, " m")],
        ["Silt end - reported", _fmt(z.end if z else None, 2, " m")],
        ["Silt end RL - reported", _fmt(end_rl, 2, " m")],
        ["Silt thickness - reported", _fmt(z.thickness if z else (0.0 if a.status == "NO SILT" else None), 2, " m")],
        ["Sand layer thickness before silt", _fmt(a.sand_layer_thickness, 2, " m")],
        ["Raw plotted silt start", _fmt(z.start_raw if z else None, 3, " m")],
        ["Raw analysis end", _fmt(z.end_raw if z else None, 3, " m")],
        ["Raw interval thickness", _fmt(z.thickness_raw if z else None, 3, " m")],
        ["Maximum reconstructed Ic", _fmt(float(np.nanmax(a.ic)) if np.any(np.isfinite(a.ic)) else None, 3)],
        ["Detected qualifying intervals", str(len(a.all_intervals))],
        ["Pass 1", f"{a.pass1.start:.2f} / {a.pass1.thickness:.2f}" if a.pass1 else "NO SILT"],
        ["Pass 2", f"{a.pass2.start:.2f} / {a.pass2.thickness:.2f}" if a.pass2 else "NO SILT"],
    ]
    tbl = ax.table(cellText=rows, colWidths=[.40, .54], cellLoc="left", bbox=[.07, .42, .86, .43])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7.8)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("#CBD5E1")
        cell.set_linewidth(.65)
        if c == 0:
            cell.set_facecolor("#EAF0F7")
            cell.set_text_props(weight="bold", color="#0F172A")
        else:
            cell.set_facecolor("#FFFFFF")

    ax.text(.07, .365, "Verification note", transform=ax.transAxes, fontsize=9.5, weight="bold", color="#0F172A")
    ax.text(.07, .335, a.verification_note, transform=ax.transAxes, fontsize=7.7, wrap=True, va="top", color="#334155")
    ax.text(.07, .255, "PDF calculation basis", transform=ax.transAxes, fontsize=9.5, weight="bold", color="#0F172A")
    ax.text(
        .07, .225,
        "The original PDF pages are preserved unchanged. The application reads native PDF vector geometry from the Soil Behaviour Type Index (Ic) panel, maps the plotted trace to depth using the report level axis and ground elevation, suppresses sub-centimetre PDF-export jitter at the graph's 0.01 m resolution, detects sustained Ic >= 2.60 intervals, and verifies the selected deepest interval with two passes plus sensitivity rechecks when required. Graphical PDF reconstruction is not treated as equivalent to raw GEF/GFF numerical data; unsupported or scanned PDFs are returned as REVIEW rather than guessed.",
        transform=ax.transAxes, fontsize=7.6, wrap=True, va="top", color="#334155",
    )
    ax.text(.07, .105, "Source file", transform=ax.transAxes, fontsize=8.5, weight="bold", color="#0F172A")
    ax.text(.24, .105, a.source_path.name, transform=ax.transAxes, fontsize=8.2, color="#475569")
    return fig


def append_pdf_analysis(source_pdf: str | Path, analysis: CPTAnalysis, output_path: str | Path) -> Path:
    """Preserve every source PDF page and append one analysis summary page."""
    source_pdf = Path(source_pdf)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        with PdfPages(tmp_path) as pdf:
            fig = _pdf_analysis_figure(analysis)
            pdf.savefig(fig, bbox_inches="tight")
            fig.clear()

        src = fitz.open(source_pdf)
        extra = fitz.open(tmp_path)
        out = fitz.open()
        out.insert_pdf(src)
        out.insert_pdf(extra)
        out.save(output_path, garbage=4, deflate=True)
        out.close(); extra.close(); src.close()
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
    return output_path

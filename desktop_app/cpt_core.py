from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

PA_KPA = 100.0
GAMMA_W = 9.81
DEFAULT_GAMMA = 18.0
DEFAULT_WATER_TABLE = 2.0
SILT_IC_THRESHOLD = 2.60
MIN_LAYER_THICKNESS = 0.05
MAX_SMALL_GAP = 0.025  # preserve >=3cm Ic reversals as distinct layers
IGNORE_TOP_DEPTH = 0.20
TERMINAL_DROPOUT_MAX = 0.20
SENSOR_EPS = 1e-8


def round_01(value: float) -> float:
    return float(Decimal(str(float(value))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def natural_ref_key(ref: str):
    parts = re.split(r"(\d+)", ref or "")
    return tuple(int(p) if p.isdigit() else p.lower() for p in parts)


@dataclass
class GEFData:
    source_path: Path
    headers: Dict[str, List[str]]
    metadata: Dict[str, object]
    columns: Dict[str, np.ndarray]


@dataclass
class SiltInterval:
    start: float
    end: float
    thickness: float
    start_raw: float
    end_raw: float
    thickness_raw: float
    source_end_raw: float


@dataclass
class CPTAnalysis:
    source_path: Path
    reference: str
    metadata: Dict[str, object]
    depth: np.ndarray
    qc: np.ndarray
    fs: np.ndarray
    u2: np.ndarray
    qt: np.ndarray
    fr: np.ndarray
    qtn: np.ndarray
    ic: np.ndarray
    valid_sensor: np.ndarray
    sbt_labels: List[str]
    pass1: Optional[SiltInterval]
    pass2: Optional[SiltInterval]
    final_interval: Optional[SiltInterval]
    status: str
    verification_note: str
    all_intervals: List[Tuple[float, float]] = field(default_factory=list)
    sensor_dropout_depth: Optional[float] = None

    @property
    def test_depth_raw(self) -> float:
        header = self.metadata.get("end_depth_header")
        measured = float(self.depth[-1]) if len(self.depth) else float("nan")
        if isinstance(header, (int, float)) and math.isfinite(float(header)):
            return min(float(header), measured + 0.02) if measured <= float(header) + 0.05 else measured
        return measured

    @property
    def test_depth(self) -> float:
        return round_01(self.test_depth_raw)

    @property
    def sand_layer_thickness(self) -> Optional[float]:
        # REVIEW may have an observed quantitative interval that is not yet
        # approved because two genuinely full-depth test revisions conflict.
        # Preserve the numeric evidence, but never relabel it VERIFIED.
        if self.final_interval is not None:
            return self.final_interval.start
        if self.status == "REVIEW":
            return None
        if self.status == "NO SILT":
            return self.test_depth
        return None

    @property
    def silt_start_display(self):
        if self.status == "NO SILT":
            return "NO SILT"
        if self.final_interval is None:
            return "REVIEW"
        return self.final_interval.start

    @property
    def silt_depth_display(self):
        if self.status == "NO SILT":
            return 0.0
        if self.final_interval is None:
            return None
        return self.final_interval.thickness


def summarize_analyses(analyses: List[CPTAnalysis]) -> Dict[str, object]:
    verified = [a for a in analyses if a.status == "VERIFIED" and a.final_interval is not None]
    no_silt = [a for a in analyses if a.status == "NO SILT"]
    review = [a for a in analyses if a.status == "REVIEW"]
    max_value = None
    max_refs: List[str] = []
    if verified:
        max_value = max(a.final_interval.thickness for a in verified)
        max_refs = [a.reference for a in verified if abs(a.final_interval.thickness - max_value) < 1e-9]
    return {
        "total": len(analyses),
        "verified": len(verified),
        "no_silt": len(no_silt),
        "review": len(review),
        "max_silt_thickness": max_value,
        "max_silt_refs": max_refs,
        "avg_silt_thickness": float(np.mean([a.final_interval.thickness for a in verified])) if verified else None,
    }


def _split_header_value(line: str) -> Tuple[str, str]:
    if "=" not in line:
        return line.strip().upper(), ""
    key, value = line.split("=", 1)
    return key.strip().lstrip("#").upper(), value.strip()


def _parse_float(value: str, default: Optional[float] = None) -> Optional[float]:
    try:
        return float(value.strip().replace(",", "."))
    except Exception:
        return default


def parse_gef(path: str | Path) -> GEFData:
    path = Path(path)
    text = path.read_bytes().decode("latin-1", errors="replace")
    if "#EOH=" not in text.upper():
        raise ValueError("Not a supported ASCII GEF/GFF file: #EOH marker not found")
    marker = re.search(r"(?im)^#EOH\s*=.*$", text)
    if not marker:
        raise ValueError("GEF header termination marker not found")
    header_text, data_text = text[: marker.start()], text[marker.end() :]

    headers: Dict[str, List[str]] = {}
    for line in header_text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            key, value = _split_header_value(line)
            headers.setdefault(key, []).append(value)

    col_defs: Dict[int, Tuple[str, str, Optional[int]]] = {}
    for value in headers.get("COLUMNINFO", []):
        parts = [p.strip() for p in value.split(",")]
        if len(parts) < 3:
            continue
        try:
            idx = int(parts[0])
        except ValueError:
            continue
        try:
            code = int(parts[3]) if len(parts) > 3 else None
        except ValueError:
            code = None
        col_defs[idx] = (parts[1] if len(parts) > 1 else "", parts[2], code)

    ncols = int(float(headers.get("COLUMN", [str(len(col_defs) or 0)])[0] or 0))
    if ncols <= 0:
        raise ValueError("No columns declared in GEF header")

    rows = []
    for line in data_text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.replace(";", " ").split()
        if len(parts) < ncols:
            continue
        try:
            rows.append([float(x.replace(",", ".")) for x in parts[:ncols]])
        except ValueError:
            continue
    if not rows:
        raise ValueError("No numerical GEF/GFF records could be parsed")
    arr = np.asarray(rows, dtype=float)

    def find_col(*codes: int, descriptions: Tuple[str, ...] = ()) -> Optional[int]:
        for idx, (_, _, code) in col_defs.items():
            if code in codes:
                return idx - 1
        for idx, (_, desc, _) in col_defs.items():
            if any(term in desc.lower() for term in descriptions):
                return idx - 1
        return None

    idx_pen = find_col(1, descriptions=("penetration length", "depth"))
    idx_qc = find_col(2, descriptions=("tip resistance", "cone resistance"))
    idx_fs = find_col(3, descriptions=("sleeve friction", "local sleeve"))
    idx_u2 = find_col(6, descriptions=("pore pressure", "u2"))
    idx_corr = find_col(11, descriptions=("corrected depth",))
    if idx_qc is None or idx_fs is None:
        raise ValueError("GEF/GFF must contain cone resistance qc and sleeve friction fs")

    depth = arr[:, idx_corr] if idx_corr is not None else (arr[:, idx_pen] if idx_pen is not None else None)
    if depth is None:
        raise ValueError("GEF/GFF must contain penetration length or corrected depth")
    qc, fs = arr[:, idx_qc], arr[:, idx_fs]
    u2 = arr[:, idx_u2] if idx_u2 is not None else np.zeros(len(arr), dtype=float)

    mask = np.isfinite(depth) & np.isfinite(qc) & np.isfinite(fs) & np.isfinite(u2)
    depth, qc, fs, u2 = depth[mask], qc[mask], fs[mask], u2[mask]
    order = np.argsort(depth, kind="stable")
    depth, qc, fs, u2 = depth[order], qc[order], fs[order], u2[order]
    _, unique_idx = np.unique(np.round(depth, 6), return_index=True)
    unique_idx = np.sort(unique_idx)
    depth, qc, fs, u2 = depth[unique_idx], qc[unique_idx], fs[unique_idx], u2[unique_idx]

    def first(key: str, default: str = "") -> str:
        vals = headers.get(key, [])
        return vals[0].strip() if vals else default

    xy = [x.strip() for x in first("XYID").split(",")] if first("XYID") else []
    zid = [x.strip() for x in first("ZID").split(",")] if first("ZID") else []
    mtext, mvar = {}, {}
    for val in headers.get("MEASUREMENTTEXT", []):
        parts = [p.strip() for p in val.split(",")]
        if len(parts) >= 2:
            try:
                mtext[int(parts[0])] = parts[1]
            except ValueError:
                pass
    for val in headers.get("MEASUREMENTVAR", []):
        parts = [p.strip() for p in val.split(",")]
        if len(parts) >= 2:
            try:
                mvar[int(parts[0])] = float(parts[1].replace(",", "."))
            except ValueError:
                pass

    client = mtext.get(1, "")
    metadata = {
        "reference": first("TESTID") or path.stem,
        "project_id": first("PROJECTID"),
        "project_name": first("PROJECTNAME") or mtext.get(2, ""),
        "client": client,
        "location": mtext.get(3, ""),
        "main_contractor": "CTS GULF" if "SAUDI GLOBAL PORTS" in str(client).upper() else "",
        "cone_id": mtext.get(4, ""),
        "ground_elevation": _parse_float(zid[1]) if len(zid) > 1 else None,
        "easting": _parse_float(xy[1]) if len(xy) > 1 else None,
        "northing": _parse_float(xy[2]) if len(xy) > 2 else None,
        "file_date": first("STARTDATE") or first("FILEDATE"),
        "end_depth_header": mvar.get(16),
        "area_ratio": mvar.get(3, 0.75),
        "standard": mtext.get(6, ""),
        "records": int(len(depth)),
        # Preserve every original source header line, including manufacturer
        # fields not mapped by the current report template. This allows a
        # complete engineering provenance sheet without guessing metadata.
        "source_header_entries": [
            (key, item) for key, values in headers.items() for item in values
        ],
        "pore_pressure_source": ("MEASURED" if idx_u2 is not None
                                  else "NOT PROVIDED — assumed u2=0 for qt; engineering validation required"),
        "pore_pressure_measured": idx_u2 is not None,
        # GEF STARTDATE is the recorded start of the physical penetration
        # test and is distinct from FILEDATE (source-file generation date).
        # Prefer an explicit test date when supplied.
        "test_date": first("TESTDATE") or first("TEST_DATE") or first("STARTDATE") or "",
        "test_time": first("STARTTIME") or "",
    }
    return GEFData(path, headers, metadata, {"depth": depth, "qc": qc, "fs": fs, "u2": u2})


def _terminal_sensor_valid(depth: np.ndarray, qc: np.ndarray, fs: np.ndarray) -> Tuple[np.ndarray, Optional[float]]:
    valid = np.isfinite(depth) & np.isfinite(qc) & np.isfinite(fs) & (qc > SENSOR_EPS)
    zero_fs = np.isfinite(fs) & (np.abs(fs) <= SENSOR_EPS)
    dropout_start = None
    if len(fs) >= 4:
        i = len(fs) - 1
        while i >= 0 and zero_fs[i]:
            i -= 1
        first_zero = i + 1
        if first_zero < len(fs) and first_zero > 0:
            terminal_len = float(depth[-1] - depth[first_zero])
            prev = fs[max(0, first_zero - 8): first_zero]
            if terminal_len <= TERMINAL_DROPOUT_MAX and np.count_nonzero(prev > SENSOR_EPS) >= min(3, len(prev)):
                valid[first_zero:] = False
                dropout_start = float(depth[first_zero])
    return valid, dropout_start


def compute_robertson(gef: GEFData, gamma_soil: float = DEFAULT_GAMMA, water_table_depth: float = DEFAULT_WATER_TABLE) -> Dict[str, np.ndarray]:
    z = np.asarray(gef.columns["depth"], dtype=float)
    qc = np.asarray(gef.columns["qc"], dtype=float)
    fs = np.asarray(gef.columns["fs"], dtype=float)
    u2 = np.asarray(gef.columns["u2"], dtype=float)
    area_ratio = float(gef.metadata.get("area_ratio") or 0.75)
    sensor_valid, dropout_start = _terminal_sensor_valid(z, qc, fs)
    qt = qc + (1.0 - area_ratio) * u2
    sigma_v0 = np.maximum(gamma_soil * z, 0.0)
    u0 = np.where(z > water_table_depth, GAMMA_W * (z - water_table_depth), 0.0)
    sigma_v0_eff = np.maximum(sigma_v0 - u0, 1.0)
    qnet = qt * 1000.0 - sigma_v0
    fr = np.full_like(z, np.nan)
    calc_valid = sensor_valid & np.isfinite(qnet) & (qnet > 1e-6) & (fs > SENSOR_EPS)
    fr[calc_valid] = fs[calc_valid] * 1000.0 / qnet[calc_valid] * 100.0
    n = np.full_like(z, 0.5)
    ic = np.full_like(z, np.nan)
    qtn = np.full_like(z, np.nan)
    if np.any(calc_valid):
        for _ in range(30):
            qtn_calc = np.maximum(qnet[calc_valid] / PA_KPA * (PA_KPA / sigma_v0_eff[calc_valid]) ** n[calc_valid], 1e-12)
            fr_calc = np.maximum(fr[calc_valid], 1e-12)
            ic_new = np.sqrt((3.47 - np.log10(qtn_calc)) ** 2 + (np.log10(fr_calc) + 1.22) ** 2)
            n_new = np.clip(0.381 * ic_new + 0.05 * (sigma_v0_eff[calc_valid] / PA_KPA) - 0.15, 0.0, 1.0)
            delta = np.nanmax(np.abs(n_new - n[calc_valid]))
            n[calc_valid] = n_new
            qtn[calc_valid] = qtn_calc
            ic[calc_valid] = ic_new
            if delta < 1e-6:
                break
    labels = np.array([classify_ic(v) for v in ic], dtype=object)
    return {"depth": z, "qc": qc, "fs": fs, "u2": u2, "qt": qt, "fr": fr, "qtn": qtn, "ic": ic, "labels": labels, "sensor_valid": sensor_valid, "dropout_start": dropout_start}


def classify_ic(ic: float) -> str:
    if not np.isfinite(ic):
        return "Unknown"
    if ic < 1.31:
        return "Gravelly sand to dense sand"
    if ic < 2.05:
        return "Clean to silty sand"
    if ic < 2.60:
        return "Silty sand to sandy silt"
    if ic < 2.95:
        return "Clayey silt to silty clay"
    if ic < 3.60:
        return "Silty clay to clay"
    return "Organic soil - clay"


def _median_filter(values: np.ndarray, width: int) -> np.ndarray:
    if width <= 1:
        return values.copy()
    half = width // 2
    out = np.full_like(values, np.nan, dtype=float)
    for i in range(len(values)):
        w = values[max(0, i - half): min(len(values), i + half + 1)]
        if np.any(np.isfinite(w)):
            out[i] = np.nanmedian(w)
    return out


def _close_small_gaps(state: np.ndarray, depth: np.ndarray, valid: np.ndarray, max_gap: float) -> np.ndarray:
    state = np.asarray(state, dtype=bool).copy()
    i = 0
    while i < len(state):
        if state[i]:
            i += 1
            continue
        j = i
        while j < len(state) and not state[j]:
            j += 1
        if i > 0 and j < len(state) and np.all(valid[i:j]) and depth[j] - depth[i - 1] <= max_gap:
            state[i:j] = True
        i = j
    return state


def _find_runs(state: np.ndarray, depth: np.ndarray, min_thickness: float) -> List[Tuple[int, int]]:
    runs = []
    i = 0
    while i < len(state):
        if not state[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(state) and state[j + 1]:
            j += 1
        if depth[j] - depth[i] >= min_thickness:
            runs.append((i, j))
        i = j + 1
    return runs


def _interpolate_crossing(depth: np.ndarray, ic: np.ndarray, idx: int, threshold: float) -> float:
    if idx <= 0:
        return float(depth[idx])
    prev = idx - 1
    while prev >= 0 and not np.isfinite(ic[prev]):
        prev -= 1
    if prev < 0 or not np.isfinite(ic[idx]):
        return float(depth[idx])
    x0, x1, y0, y1 = float(depth[prev]), float(depth[idx]), float(ic[prev]), float(ic[idx])
    if y1 == y0 or not (min(y0, y1) <= threshold <= max(y0, y1)):
        return x1
    return x0 + (threshold - y0) / (y1 - y0) * (x1 - x0)


def _make_interval(start_raw: float, end_raw: float, source_end_raw: float) -> SiltInterval:
    start_report, end_report = round_01(start_raw), round_01(end_raw)
    return SiltInterval(start_report, end_report, round_01(max(0.0, end_report - start_report)), float(start_raw), float(end_raw), float(max(0.0, end_raw - start_raw)), float(source_end_raw))


def _detect_interval(depth, ic, sensor_valid, test_end, dropout_start, threshold, smooth_width, max_gap, min_thickness):
    work_ic = _median_filter(ic, smooth_width)
    valid = np.isfinite(work_ic) & np.isfinite(depth) & sensor_valid & (depth >= IGNORE_TOP_DEPTH)
    state = _close_small_gaps(valid & (work_ic >= threshold), depth, valid, max_gap)
    raw_runs = _find_runs(state, depth, 0.0)
    runs = []
    for a, b in raw_runs:
        observed = float(depth[b] - depth[a])
        # Require sustained thickness on valid, observed measurements.
        # Terminal zero-fs dropout is UNKNOWN; never infer silt to sounding end.
        if observed >= min_thickness:
            runs.append((a, b))
    all_intervals = [(float(depth[a]), float(depth[b])) for a, b in runs]
    if not runs:
        return None, all_intervals
    a, b = runs[-1]
    start_raw = _interpolate_crossing(depth, work_ic, a, threshold)
    source_end = float(depth[b])
    # Interpolate BOTH boundaries when the adjacent observation exists:
    # for falling Ic this can shift the engineering report end from 4.5
    # to 4.6 at HALF_UP precision. Never cross a dropout or invalid gap.
    end_raw = source_end
    nxt=b+1
    if (nxt<len(depth) and valid[nxt] and work_ic[nxt]<threshold and
        float(depth[nxt]-depth[b])<=.035 and work_ic[b]!=work_ic[nxt]):
        fraction=(threshold-float(work_ic[b]))/(float(work_ic[nxt])-float(work_ic[b]))
        if 0<=fraction<=1:
            end_raw=source_end+fraction*(float(depth[nxt])-source_end)
    return _make_interval(start_raw, end_raw, source_end), all_intervals


def _same(a: Optional[SiltInterval], b: Optional[SiltInterval]) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return a.start == b.start and a.end == b.end and a.thickness == b.thickness


def _profile_screening_interval(depth, ic, sensor_valid, window):
    """Observed-only Ic >= project threshold: never join intervening sand zones.

    All persistent intervals are retained. The project quick sheet chooses the
    deepest qualifying interval; detailed Excel charts preserve every layer.
    """
    from engineering_layers import analyze_stratigraphy
    p = analyze_stratigraphy(
        depth, ic, sensor_valid, rolling_window=window,
        silt_threshold=SILT_IC_THRESHOLD, min_silt_m=MIN_LAYER_THICKNESS)
    intervals=list(p.silt_intervals)
    if not intervals:
        return None, intervals, p
    start,end=intervals[-1]
    return _make_interval(start,end,end),intervals,p


def analyze_gef(path: str | Path, gamma_soil: float = DEFAULT_GAMMA,
                water_table_depth: float = DEFAULT_WATER_TABLE,
                stage: str = "PRE") -> CPTAnalysis:
    gef = parse_gef(path)
    gef.metadata["analysis_gamma_soil_kn_m3"] = float(gamma_soil)
    gef.metadata["analysis_water_table_bgl_m"] = float(water_table_depth)
    gef.metadata["ic_screening_threshold"] = float(SILT_IC_THRESHOLD)
    gef.metadata["minimum_qualifying_layer_m"] = float(MIN_LAYER_THICKNESS)
    phase = str(stage).strip().upper()
    if phase not in ("PRE","POST"):
        raise ValueError("CPT stage must be PRE or POST")
    primary_width=3 if phase=="PRE" else 10
    secondary_widths=(1,5,7) if phase=="PRE" else (7,9,11)
    gef.metadata["cpt_stage"]=phase
    gef.metadata["analysis_smoothing_window_samples"]=primary_width
    gef.metadata["analysis_interval_gap_joining"]=False
    gef.metadata["analysis_method"]=(
        f"Observed-only Ic screening, {phase} mean of {primary_width} samples;"
        f" sensitivity windows {secondary_widths}")
    calc=compute_robertson(gef, gamma_soil, water_table_depth)
    depth,ic,sensor_valid=calc["depth"],calc["ic"],calc["sensor_valid"]
    dropout_start=calc["dropout_start"]
    by_width={}
    for width in (primary_width,)+secondary_widths:
        by_width[width]=_profile_screening_interval(
            depth,ic,sensor_valid,width)
    p2,intervals1,selected_profile=by_width[primary_width]
    p1=by_width[secondary_widths[0]][0]
    # The primary project-stage window is authoritative for reporting,
    # while three different windows independently test stability.
    candidates={k:v[0] for k,v in by_width.items()}
    label=lambda z: "NONE" if z is None else f"{z.start:.1f}/{z.end:.1f}/{z.thickness:.1f}"
    primary=label(p2)
    support=sum(label(x)==primary for x in candidates.values())
    # Reference-build reporting policy: at least three of four windows
    # must agree with the PRE/POST primary interval at 0.10 m resolution.
    # Alternative windows are sensitivity checks, not replacement soundings.
    # A disagreement is explicitly REVIEW; do not publish a guessed interval.
    gef.metadata["calculation_policy"]="REFERENCE_CONSENSUS_3_OF_4_V1"
    if p2 is not None:
        gef.metadata["primary_candidate_raw_start_m"]=float(p2.start_raw)
        gef.metadata["primary_candidate_raw_end_m"]=float(p2.end_raw)
        gef.metadata["primary_candidate_raw_thickness_m"]=float(p2.thickness_raw)
    if support>=3:
        final,status=(p2,"VERIFIED") if p2 is not None else (None,"NO SILT")
    else:
        final,status=None,"REVIEW"
    gef.metadata["processing_sensitivity_support"]=support
    gef.metadata["processing_sensitivity_total"]=len(candidates)
    gef.metadata["processing_sensitivity_warning"]=support<3
    gef.metadata["sensitivity_disagreement_review"]=support<3
    report="; ".join(f"window {k}: {label(v)}" for k,v in candidates.items())
    note=(f"Observed-only {phase} Ic screening ({primary_width}-sample rolling mean);"
          f" {support}/4 sensitivity windows agree with {primary} at 0.10m"
          f" reporting resolution. {report}. No gap-joining.")
    if status=="NO SILT":
        note+=" No qualifying *observed* Ic interval, not confirmed absence of silt."
    if support<3:
        note+=(" REVIEW: fewer than three smoothing windows agree with the"
               " declared primary result. Its raw candidate is retained"
               " as evidence, not a reportable final interval. Check the"
               " source model and profile before engineering approval.")
    if selected_profile.brief_exceedances:
        note+=f" {len(selected_profile.brief_exceedances)} brief threshold crossing(s) retained separately in the layer audit."

    # Censored terminal crossing: a thin observed above-threshold tail may
    # continue beyond the last valid sensor record, but its extent is UNKNOWN.
    # Do not turn this into NO SILT or measured full-terminal silt.
    if status == "NO SILT" and dropout_start is not None:
        good_idx = np.flatnonzero(sensor_valid & np.isfinite(ic))
        if len(good_idx):
            i_last = int(good_idx[-1])
            if float(ic[i_last])>=SILT_IC_THRESHOLD:
                # This is a valid distinction: no sustained qualifying OBSERVED
                # interval, but the terminal sensor tail remains unclassified.
                # It must not be labelled a measured 0.10m silt layer or
                # silently converted into REVIEW with all numeric fields empty.
                note += (" Last valid Ic crosses the screening limit for less"
                         " than the required observed persistence. No sustained"
                         " measured silt found; terminal sensor data remain UNKNOWN."
                         " This does not exclude unobserved fine-grained soil.")
    # A positive thin interval that rounds to zero at 0.10 m is REVIEW.
    # Store exact observations for the Review Evidence sheet, instead of
    # silently changing precision or inventing a minimum layer thickness.
    if status=="VERIFIED" and final is not None and final.thickness_raw>0 and final.thickness==0:
        gef.metadata["thin_interval_unrounded_start"]=float(final.start_raw)
        gef.metadata["thin_interval_unrounded_end"]=float(final.end_raw)
        gef.metadata["thin_interval_unrounded_thickness"]=float(final.thickness_raw)
        status="REVIEW"
        final=None
        note+=(" REVIEW: measured positive interval rounds to zero at the"
               " declared 0.10m resolution. Unrounded observations are"
               " retained for engineer-approved reporting; no 0.01m"
               " VERIFIED result is substituted.")
    if dropout_start is not None:
        note += f" Terminal sleeve-friction dropout detected from {dropout_start:.3f} m; this UNKNOWN tail is NOT counted as measured silt."

    return CPTAnalysis(Path(path), str(gef.metadata.get("reference") or Path(path).stem), gef.metadata, calc["depth"], calc["qc"], calc["fs"], calc["u2"], calc["qt"], calc["fr"], calc["qtn"], calc["ic"], sensor_valid, list(calc["labels"]), p1, p2, final, status, note, intervals1, dropout_start)

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
DEFAULT_WATER_TABLE = 0.0
SILT_IC_THRESHOLD = 2.60
MIN_LAYER_THICKNESS = 0.05
MAX_SMALL_GAP = 0.06
IGNORE_TOP_DEPTH = 0.20


def round_01(value: float) -> float:
    return float(Decimal(str(float(value))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


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
    sbt_labels: List[str]
    pass1: Optional[SiltInterval]
    pass2: Optional[SiltInterval]
    final_interval: Optional[SiltInterval]
    status: str
    verification_note: str
    all_intervals: List[Tuple[float, float]] = field(default_factory=list)

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
    raw = path.read_bytes()
    text = raw.decode("latin-1", errors="replace")
    if "#EOH=" not in text.upper():
        raise ValueError("Not a supported ASCII GEF file: #EOH marker not found")

    marker = re.search(r"(?im)^#EOH\s*=.*$", text)
    if not marker:
        raise ValueError("GEF header termination marker not found")
    header_text = text[: marker.start()]
    data_text = text[marker.end() :]

    headers: Dict[str, List[str]] = {}
    for line in header_text.splitlines():
        line = line.strip()
        if not line.startswith("#"):
            continue
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
        unit = parts[1] if len(parts) > 1 else ""
        desc = parts[2] if len(parts) > 2 else f"column_{idx}"
        try:
            code = int(parts[3]) if len(parts) > 3 else None
        except ValueError:
            code = None
        col_defs[idx] = (unit, desc, code)

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
            row = [float(x.replace(",", ".")) for x in parts[:ncols]]
        except ValueError:
            continue
        rows.append(row)

    if not rows:
        raise ValueError("No numerical GEF records could be parsed")
    arr = np.asarray(rows, dtype=float)

    def find_col(*codes: int, descriptions: Tuple[str, ...] = ()) -> Optional[int]:
        for idx, (_, desc, code) in col_defs.items():
            if code in codes:
                return idx - 1
        for idx, (_, desc, code) in col_defs.items():
            dl = desc.lower()
            if any(term in dl for term in descriptions):
                return idx - 1
        return None

    idx_pen = find_col(1, descriptions=("penetration length", "depth"))
    idx_qc = find_col(2, descriptions=("tip resistance", "cone resistance"))
    idx_fs = find_col(3, descriptions=("sleeve friction", "local sleeve"))
    idx_u2 = find_col(6, descriptions=("pore pressure", "u2"))
    idx_corr = find_col(11, descriptions=("corrected depth",))

    if idx_qc is None or idx_fs is None:
        raise ValueError("GEF must contain cone resistance qc and sleeve friction fs")

    depth = arr[:, idx_corr] if idx_corr is not None else (arr[:, idx_pen] if idx_pen is not None else None)
    if depth is None:
        raise ValueError("GEF must contain penetration length or corrected depth")

    u2 = arr[:, idx_u2] if idx_u2 is not None else np.zeros(len(arr), dtype=float)
    qc = arr[:, idx_qc]
    fs = arr[:, idx_fs]

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

    test_id = first("TESTID") or path.stem
    project_id = first("PROJECTID")
    project_name = first("PROJECTNAME")
    file_date = first("FILEDATE")

    xy = [x.strip() for x in first("XYID").split(",")] if first("XYID") else []
    zid = [x.strip() for x in first("ZID").split(",")] if first("ZID") else []

    mtext = {}
    for val in headers.get("MEASUREMENTTEXT", []):
        parts = [p.strip() for p in val.split(",")]
        if len(parts) >= 2:
            try:
                mtext[int(parts[0])] = parts[1]
            except ValueError:
                pass

    mvar = {}
    for val in headers.get("MEASUREMENTVAR", []):
        parts = [p.strip() for p in val.split(",")]
        if len(parts) >= 2:
            try:
                mvar[int(parts[0])] = float(parts[1].replace(",", "."))
            except ValueError:
                pass

    metadata = {
        "reference": test_id,
        "project_id": project_id,
        "project_name": project_name or mtext.get(2, ""),
        "client": mtext.get(1, ""),
        "location": mtext.get(3, ""),
        "cone_id": mtext.get(4, ""),
        "ground_elevation": _parse_float(zid[1]) if len(zid) > 1 else None,
        "easting": _parse_float(xy[1]) if len(xy) > 1 else None,
        "northing": _parse_float(xy[2]) if len(xy) > 2 else None,
        "file_date": file_date,
        "end_depth_header": mvar.get(16),
        "area_ratio": mvar.get(3, 0.75),
        "standard": mtext.get(6, ""),
        "records": int(len(depth)),
    }

    return GEFData(
        source_path=path,
        headers=headers,
        metadata=metadata,
        columns={"depth": depth, "qc": qc, "fs": fs, "u2": u2},
    )


def compute_robertson(
    gef: GEFData,
    gamma_soil: float = DEFAULT_GAMMA,
    water_table_depth: float = DEFAULT_WATER_TABLE,
) -> Dict[str, np.ndarray]:
    z = np.asarray(gef.columns["depth"], dtype=float)
    qc = np.asarray(gef.columns["qc"], dtype=float)
    fs = np.asarray(gef.columns["fs"], dtype=float)
    u2 = np.asarray(gef.columns["u2"], dtype=float)
    area_ratio = float(gef.metadata.get("area_ratio") or 0.75)

    qt = qc + (1.0 - area_ratio) * u2

    sigma_v0 = np.maximum(gamma_soil * z, 0.0)
    u0 = np.where(z > water_table_depth, GAMMA_W * (z - water_table_depth), 0.0)
    sigma_v0_eff = np.maximum(sigma_v0 - u0, 1.0)
    qnet = np.maximum(qt * 1000.0 - sigma_v0, 1e-6)

    fr = np.maximum(fs * 1000.0 / qnet * 100.0, 1e-6)

    n = np.full_like(z, 0.5)
    ic = np.full_like(z, np.nan)
    qtn = np.full_like(z, np.nan)
    for _ in range(30):
        qtn = np.maximum(qnet / PA_KPA * (PA_KPA / sigma_v0_eff) ** n, 1e-12)
        ic_new = np.sqrt((3.47 - np.log10(qtn)) ** 2 + (np.log10(fr) + 1.22) ** 2)
        n_new = np.clip(0.381 * ic_new + 0.05 * (sigma_v0_eff / PA_KPA) - 0.15, 0.0, 1.0)
        if np.nanmax(np.abs(n_new - n)) < 1e-6:
            ic = ic_new
            n = n_new
            break
        ic, n = ic_new, n_new

    labels = np.array([classify_ic(v) for v in ic], dtype=object)
    return {
        "depth": z,
        "qc": qc,
        "fs": fs,
        "u2": u2,
        "qt": qt,
        "sigma_v0": sigma_v0,
        "sigma_v0_eff": sigma_v0_eff,
        "fr": fr,
        "qtn": qtn,
        "ic": ic,
        "labels": labels,
    }


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
    return np.asarray([
        np.nanmedian(values[max(0, i - half): min(len(values), i + half + 1)])
        for i in range(len(values))
    ])


def _close_small_gaps(state: np.ndarray, depth: np.ndarray, max_gap: float) -> np.ndarray:
    state = np.asarray(state, dtype=bool).copy()
    i = 0
    while i < len(state):
        if state[i]:
            i += 1
            continue
        j = i
        while j < len(state) and not state[j]:
            j += 1
        if i > 0 and j < len(state):
            if depth[j] - depth[i - 1] <= max_gap:
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


def _detect_interval(
    depth: np.ndarray,
    ic: np.ndarray,
    threshold: float,
    smooth_width: int,
    max_gap: float,
    min_thickness: float,
) -> Tuple[Optional[SiltInterval], List[Tuple[float, float]]]:
    work_ic = _median_filter(ic, smooth_width)
    valid = np.isfinite(work_ic) & np.isfinite(depth) & (depth >= IGNORE_TOP_DEPTH)
    state = valid & (work_ic >= threshold)
    state = _close_small_gaps(state, depth, max_gap)
    runs = _find_runs(state, depth, min_thickness)
    all_intervals = [(float(depth[a]), float(depth[b])) for a, b in runs]
    if not runs:
        return None, all_intervals

    a, b = runs[-1]
    start_raw = float(depth[a])
    end_raw = float(depth[b])
    test_end = float(depth[-1])
    if test_end - end_raw <= 0.08:
        end_raw = test_end
    thickness_raw = max(0.0, end_raw - start_raw)
    return SiltInterval(
        start=round_01(start_raw),
        end=round_01(end_raw),
        thickness=round_01(thickness_raw),
        start_raw=start_raw,
        end_raw=end_raw,
        thickness_raw=thickness_raw,
    ), all_intervals


def _same(a: Optional[SiltInterval], b: Optional[SiltInterval]) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return a.start == b.start and a.thickness == b.thickness


def analyze_gef(
    path: str | Path,
    gamma_soil: float = DEFAULT_GAMMA,
    water_table_depth: float = DEFAULT_WATER_TABLE,
) -> CPTAnalysis:
    gef = parse_gef(path)
    calc = compute_robertson(gef, gamma_soil=gamma_soil, water_table_depth=water_table_depth)
    depth = calc["depth"]
    ic = calc["ic"]

    p1, intervals1 = _detect_interval(depth, ic, SILT_IC_THRESHOLD, 1, MAX_SMALL_GAP, MIN_LAYER_THICKNESS)
    p2, intervals2 = _detect_interval(depth, ic, SILT_IC_THRESHOLD, 3, MAX_SMALL_GAP, MIN_LAYER_THICKNESS)

    if p1 is None and p2 is None:
        final = None
        status = "NO SILT"
        note = "Two independent passes found no sustained Ic >= 2.60 interval."
    elif _same(p1, p2):
        final = p1
        status = "VERIFIED"
        note = "Two independent passes agree after 0.10 m reporting rounding."
    else:
        candidates = []
        specs = [
            (2.60, 1, 0.05),
            (2.60, 3, 0.06),
            (2.58, 3, 0.07),
            (2.62, 3, 0.07),
            (2.60, 5, 0.06),
            (2.59, 5, 0.07),
            (2.61, 5, 0.07),
            (2.60, 7, 0.08),
        ]
        for threshold, smooth, gap in specs:
            z, _ = _detect_interval(depth, ic, threshold, smooth, gap, MIN_LAYER_THICKNESS)
            if z is None:
                candidates.append(("NO SILT", None))
            else:
                candidates.append((f"{z.start:.1f}/{z.thickness:.1f}", z))
        counts: Dict[str, int] = {}
        for label, _ in candidates:
            counts[label] = counts.get(label, 0) + 1
        best_label, best_count = max(counts.items(), key=lambda x: x[1])
        if best_count >= 5:
            if best_label == "NO SILT":
                final = None
                status = "NO SILT"
            else:
                final = next(z for label, z in candidates if label == best_label and z is not None)
                status = "VERIFIED"
            note = f"Primary passes differed; {best_count}/8 detailed rechecks converged on {best_label}."
        else:
            silt_candidates = [z for _, z in candidates if z is not None]
            if len(silt_candidates) >= 5:
                starts = [z.start for z in silt_candidates]
                thick = [z.thickness for z in silt_candidates]
                if max(starts) - min(starts) <= 0.1 + 1e-9 and max(thick) - min(thick) <= 0.1 + 1e-9:
                    sr = float(np.median([z.start_raw for z in silt_candidates]))
                    tr = float(np.median([z.thickness_raw for z in silt_candidates]))
                    final = SiltInterval(round_01(sr), round_01(sr + tr), round_01(tr), sr, sr + tr, tr)
                    status = "VERIFIED"
                    note = "Detailed checks were within one 0.10 m increment; geometric median used."
                else:
                    final = None
                    status = "REVIEW"
                    note = "Independent analyses did not converge. Manual review required."
            else:
                final = None
                status = "REVIEW"
                note = "Independent analyses did not converge. Manual review required."

    return CPTAnalysis(
        source_path=Path(path),
        reference=str(gef.metadata.get("reference") or Path(path).stem),
        metadata=gef.metadata,
        depth=calc["depth"],
        qc=calc["qc"],
        fs=calc["fs"],
        u2=calc["u2"],
        qt=calc["qt"],
        fr=calc["fr"],
        qtn=calc["qtn"],
        ic=calc["ic"],
        sbt_labels=list(calc["labels"]),
        pass1=p1,
        pass2=p2,
        final_interval=final,
        status=status,
        verification_note=note,
        all_intervals=intervals1,
    )

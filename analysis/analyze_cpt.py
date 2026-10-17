import csv
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import fitz
import numpy as np

IC_VALUES = np.array([0.00, 1.31, 2.05, 2.60, 2.95, 3.60, 5.00], dtype=float)
IC_THRESHOLD = 2.60
DEPTH_STEP = 0.01
MAX_GAP_SAMPLES_P1 = 7
MAX_GAP_SAMPLES_P2 = 5
MIN_RUN_SAMPLES_P1 = 10
MIN_RUN_SAMPLES_P2 = 8
TERMINAL_TOL = 0.15

# Values visible in the user's supplied project spreadsheet screenshot.
REFERENCE = {
    "CPT-A1-B328-100": (6.00, 0.40),
    "CPT-A1-B340-100": (6.00, 0.40),
    "CPT-A1-B341-100": (6.00, 0.30),
    "CPT-A1-B342-100": (6.20, 0.40),
    "CPT-A1-B377-100": (6.50, 0.30),
    "CPT-A1-B378-100": (6.40, 0.30),
}


def round_tenth(v):
    if v is None:
        return None
    return float(Decimal(str(float(v))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def parse_date(text):
    m = re.search(r"Test\s*Date\s*:?\s*(\d{1,2}-[A-Za-z]{3}-\d{4})", text, flags=re.I)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%d-%b-%Y").date().isoformat()
    except Exception:
        return m.group(1)


def parse_cpt_reference(text, filename):
    m = re.search(r"Test\s*Location\s*:?\s*(CPT-[A-Za-z0-9-]+)", text, flags=re.I)
    if m:
        return m.group(1).strip().upper()
    stem = Path(filename).stem.strip()
    stem = re.sub(r"^P\d+_", "", stem, flags=re.I)
    m = re.search(r"(CPT-[A-Za-z0-9-]+?-100)(?:-\d+)?$", stem, flags=re.I)
    if m:
        return m.group(1).upper()
    m = re.search(r"(CPT-[A-Za-z0-9-]+)", stem, flags=re.I)
    return m.group(1).upper() if m else stem.upper()


def revision_rank(filename):
    stem = Path(filename).stem.strip()
    m = re.search(r"-100-(\d+)\.?$", stem, flags=re.I)
    return int(m.group(1)) if m else 0


def line_points(drawing):
    pts = []
    for item in drawing.get("items", []):
        if item[0] != "l":
            continue
        p1, p2 = item[1], item[2]
        if not pts:
            pts.append((float(p1.x), float(p1.y)))
        pts.append((float(p2.x), float(p2.y)))
    return np.asarray(pts, dtype=float)


def find_ic_curve_candidates(page):
    cands = []
    for i, d in enumerate(page.get_drawings()):
        r = d["rect"]
        color = d.get("color")
        width = float(d.get("width") or 0)
        items = d.get("items") or []
        if (
            color == (0.0, 0.0, 0.0)
            and width >= 0.7
            and len(items) >= 100
            and r.x0 > 405
            and r.x1 < 535
            and 180 < r.y0 < 310
            and 300 < r.y1 < 430
        ):
            pts = line_points(d)
            if len(pts) >= 101:
                cands.append((int(d.get("seqno", i)), i, d, pts))
    cands.sort(key=lambda x: x[0])
    return cands


def find_ic_tick_sets(page):
    ticks = []
    for i, d in enumerate(page.get_drawings()):
        items = d.get("items") or []
        if len(items) != 1 or items[0][0] != "l":
            continue
        p1, p2 = items[0][1], items[0][2]
        height = abs(float(p2.y - p1.y))
        if (
            abs(float(p1.x - p2.x)) < 0.02
            and 405 < p1.x < 565
            and 96 < min(p1.y, p2.y) < 103
            and 4.0 < height < 8.0
            and d.get("color") == (0.0, 0.0, 0.0)
        ):
            ticks.append((int(d.get("seqno", i)), float(p1.x)))
    ticks.sort(key=lambda x: x[0])
    if len(ticks) < 7:
        return []
    sets = []
    if len(ticks) >= 14:
        sets.append(sorted([x for _, x in ticks[:7]]))
        sets.append(sorted([x for _, x in ticks[-7:]]))
    else:
        sets.append(sorted([x for _, x in ticks[:7]]))
    return [s for s in sets if len(s) == 7 and all(s[j] < s[j+1] for j in range(6))]


def rolling_median(values, window=5):
    values = np.asarray(values, dtype=float)
    if window <= 1:
        return values
    n = len(values)
    half = window // 2
    out = np.empty(n, dtype=float)
    for i in range(n):
        lo, hi = max(0, i-half), min(n, i+half+1)
        out[i] = float(np.median(values[lo:hi]))
    return out


def close_small_gaps(state, max_gap_samples):
    s = np.asarray(state, dtype=bool).copy()
    n = len(s)
    i = 0
    while i < n:
        if s[i]:
            i += 1
            continue
        j = i
        while j < n and not s[j]:
            j += 1
        if i > 0 and j < n and (j-i) <= max_gap_samples:
            s[i:j] = True
        i = j
    return s


def true_runs(state, min_samples):
    s = np.asarray(state, dtype=bool)
    runs = []
    i = 0
    n = len(s)
    while i < n:
        if not s[i]:
            i += 1
            continue
        j = i
        while j < n and s[j]:
            j += 1
        if (j-i) >= min_samples:
            runs.append((i, j-1))
        i = j
    return runs


def choose_layer(state, end_index, max_gap_samples, min_run_samples):
    s = close_small_gaps(state, max_gap_samples)
    runs = true_runs(s, min_run_samples)
    if not runs:
        return None
    start_i, run_end_i = max(runs, key=lambda r: (r[1], r[0]))
    end_depth = end_index * DEPTH_STEP
    run_end_depth = run_end_i * DEPTH_STEP
    is_terminal = (end_depth-run_end_depth) <= TERMINAL_TOL
    selected_end_i = end_index if is_terminal else run_end_i
    return {
        "start_i": start_i,
        "run_end_i": run_end_i,
        "selected_end_i": selected_end_i,
        "is_terminal": is_terminal,
        "all_runs": runs,
    }


def pass_analysis(curve_pts, tick_xs, mode):
    n_segments = len(curve_pts)-1
    if n_segments < 1:
        return None
    end_depth_raw = n_segments * DEPTH_STEP
    if mode == "fit_raw":
        coef = np.polyfit(np.asarray(tick_xs), IC_VALUES, 1)
        ic = np.polyval(coef, curve_pts[:, 0])
        state = ic >= IC_THRESHOLD
        layer = choose_layer(state, n_segments, MAX_GAP_SAMPLES_P1, MIN_RUN_SAMPLES_P1)
    elif mode == "tick_median":
        threshold_x = tick_xs[3]
        xsm = rolling_median(curve_pts[:, 0], 5)
        state = xsm >= threshold_x
        layer = choose_layer(state, n_segments, MAX_GAP_SAMPLES_P2, MIN_RUN_SAMPLES_P2)
    else:
        raise ValueError(mode)
    if layer is None:
        return None
    start_raw = layer["start_i"] * DEPTH_STEP
    selected_end_raw = layer["selected_end_i"] * DEPTH_STEP
    start_round = round_tenth(start_raw)
    end_round = round_tenth(selected_end_raw)
    thickness = round(max(0.0, end_round-start_round), 2)
    return {
        "start_raw": start_raw,
        "end_raw": selected_end_raw,
        "test_end_raw": end_depth_raw,
        "start": start_round,
        "end": end_round,
        "thickness": thickness,
        "terminal": layer["is_terminal"],
        "run_end_raw": layer["run_end_i"] * DEPTH_STEP,
        "run_count": len(layer["all_runs"]),
    }


def analyze_pdf(path):
    out = {"filename": Path(path).name, "path": str(path), "status": "UNRESOLVED", "reason": ""}
    try:
        doc = fitz.open(path)
        if len(doc) < 1:
            out["reason"] = "empty PDF"
            return out
        page = doc[0]
        text = page.get_text("text") or ""
        out["cpt_reference"] = parse_cpt_reference(text, path)
        out["test_date"] = parse_date(text) or ""
        out["revision_rank"] = revision_rank(path)
        curves = find_ic_curve_candidates(page)
        tick_sets = find_ic_tick_sets(page)
        out["curve_candidates"] = len(curves)
        out["tick_sets"] = len(tick_sets)
        if not curves:
            out["reason"] = "Ic curve not found"
            return out
        if not tick_sets:
            out["reason"] = "Ic axis ticks not found"
            return out

        low_curve, high_curve = curves[0][3], curves[-1][3]
        low_ticks, high_ticks = tick_sets[0], tick_sets[-1]
        p1 = pass_analysis(low_curve, low_ticks, "fit_raw")
        p2 = pass_analysis(high_curve, high_ticks, "tick_median")
        out["segments_p1"] = len(low_curve)-1
        out["segments_p2"] = len(high_curve)-1
        if p1:
            out.update({f"p1_{k}": v for k,v in p1.items()})
        if p2:
            out.update({f"p2_{k}": v for k,v in p2.items()})

        if p1 and p2 and p1["start"] == p2["start"] and p1["thickness"] == p2["thickness"]:
            out["status"] = "VERIFIED_2PASS"
            out["final_start"] = p1["start"]
            out["final_thickness"] = p1["thickness"]
            return out

        candidates = []
        variants = [
            (low_curve, low_ticks, "fit_raw"),
            (low_curve, low_ticks, "tick_median"),
            (high_curve, high_ticks, "fit_raw"),
            (high_curve, high_ticks, "tick_median"),
        ]
        for c,t,m in variants:
            r = pass_analysis(c,t,m)
            if r:
                candidates.append((r["start"], r["thickness"]))
        out["third_candidates"] = ";".join(f"{a:.2f}/{b:.2f}" for a,b in candidates)
        if candidates:
            counts = Counter(candidates)
            (best_start,best_thick), votes = counts.most_common(1)[0]
            if votes >= 3:
                out["status"] = "VERIFIED_CONSENSUS"
                out["final_start"] = best_start
                out["final_thickness"] = best_thick
                out["reason"] = f"2-pass mismatch resolved by {votes}/{len(candidates)} deterministic consensus"
                return out
        out["reason"] = "independent passes did not converge"
        return out
    except Exception as e:
        out["reason"] = f"{type(e).__name__}: {e}"
        return out


def choose_unique(group):
    verified = [r for r in group if r.get("status", "").startswith("VERIFIED")]
    if not verified:
        return None, "no verified physical file"
    def key(r):
        date = r.get("test_date") or "0000-00-00"
        rev = int(r.get("revision_rank") or 0)
        seg = max(int(r.get("segments_p1") or 0), int(r.get("segments_p2") or 0))
        return (date, rev, seg, r.get("filename", ""))
    selected = sorted(verified, key=key)[-1]
    vals = Counter((r.get("final_start"), r.get("final_thickness")) for r in verified)
    note = ""
    if len(vals) > 1:
        note = "duplicate versions disagree: " + "; ".join(f"{k[0]:.2f}/{k[1]:.2f} x{v}" for k,v in vals.items())
    return selected, note


def main(root="pdfs/pdf_Single", output="analysis_output"):
    root = Path(root)
    outdir = Path(output)
    outdir.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(root.rglob("*.pdf"), key=lambda p: p.name.lower())
    physical = []
    for i,p in enumerate(pdfs,1):
        r = analyze_pdf(p)
        r["physical_index"] = i
        physical.append(r)
        print(f"[{i}/{len(pdfs)}] {p.name}: {r.get('status')} {r.get('final_start','')}/{r.get('final_thickness','')} {r.get('reason','')}")

    preferred = [
        "physical_index","filename","cpt_reference","test_date","revision_rank","status","reason",
        "curve_candidates","tick_sets","segments_p1","segments_p2",
        "p1_start_raw","p1_start","p1_end_raw","p1_end","p1_thickness","p1_terminal","p1_run_end_raw","p1_run_count","p1_test_end_raw",
        "p2_start_raw","p2_start","p2_end_raw","p2_end","p2_thickness","p2_terminal","p2_run_end_raw","p2_run_count","p2_test_end_raw",
        "third_candidates","final_start","final_thickness","path"
    ]
    extra = sorted(set().union(*(r.keys() for r in physical)) - set(preferred)) if physical else []
    fields = preferred + extra
    with open(outdir/"physical_results.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(physical)

    groups=defaultdict(list)
    for r in physical:
        groups[r.get("cpt_reference") or r.get("filename")].append(r)
    unique_rows=[]; conflicts=[]
    def natural_key(ref):
        return [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", ref or "")]
    for ref in sorted(groups,key=natural_key):
        selected,note=choose_unique(groups[ref])
        if selected is None:
            unique_rows.append({"cpt_reference":ref,"silt_start":"","silt_depth":"","source_file":"","status":"UNRESOLVED","note":note})
            continue
        row={
            "cpt_reference":ref,
            "silt_start":f"{float(selected['final_start']):.2f}",
            "silt_depth":f"{float(selected['final_thickness']):.2f}",
            "source_file":selected["filename"],
            "status":selected["status"],
            "note":note,
        }
        unique_rows.append(row)
        if note:
            conflicts.append({"cpt_reference":ref,"selected":selected["filename"],"selected_value":f"{selected['final_start']:.2f}/{selected['final_thickness']:.2f}","detail":note})

    with open(outdir/"unique_provisional.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["cpt_reference","silt_start","silt_depth","source_file","status","note"]); w.writeheader(); w.writerows(unique_rows)
    with open(outdir/"duplicate_conflicts.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["cpt_reference","selected","selected_value","detail"]); w.writeheader(); w.writerows(conflicts)

    validation=[]; by_ref={r["cpt_reference"]:r for r in unique_rows}
    for ref,(es,et) in REFERENCE.items():
        r=by_ref.get(ref)
        ds=float(r["silt_start"]) if r and r["silt_start"] else None
        dt=float(r["silt_depth"]) if r and r["silt_depth"] else None
        validation.append({"cpt_reference":ref,"expected_start":es,"detected_start":ds,"expected_depth":et,"detected_depth":dt,"pass":ds==es and dt==et})
    with open(outdir/"validation.csv","w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["cpt_reference","expected_start","detected_start","expected_depth","detected_depth","pass"]); w.writeheader(); w.writerows(validation)

    counts=Counter(r["status"] for r in physical)
    summary=[
        f"physical_pdfs={len(pdfs)}",
        f"unique_cpt_references={len(unique_rows)}",
        f"verified_2pass={counts.get('VERIFIED_2PASS',0)}",
        f"verified_consensus={counts.get('VERIFIED_CONSENSUS',0)}",
        f"unresolved={counts.get('UNRESOLVED',0)}",
        f"duplicate_conflict_groups={len(conflicts)}",
        f"validation_pass={sum(1 for v in validation if v['pass'])}/{len(validation)}",
    ]
    for v in validation:
        summary.append(f"validation {v['cpt_reference']}: expected={v['expected_start']:.2f}/{v['expected_depth']:.2f}, detected={v['detected_start']}/{v['detected_depth']}, pass={v['pass']}")
    (outdir/"summary.txt").write_text("\n".join(summary)+"\n",encoding="utf-8")
    print("\n"+"\n".join(summary))

if __name__ == "__main__":
    main(os.environ.get("CPT_ROOT","pdfs/pdf_Single"), os.environ.get("CPT_OUTPUT","analysis_output"))

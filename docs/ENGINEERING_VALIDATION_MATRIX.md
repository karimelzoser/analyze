# QA / Engineering signoff matrix
| Test case | Expected behavior |
|---|---|
| Zero fs at terminal tail | Unclassifiable segment; not automatically measured silt |
| Brief Ic>=2.60 threshold spike | Retain spike for audit but do not label a sustained layer |
| Alternating SBT strata | Every valid interval included, cumulative and maximum thickness separately |
| Thin observed 0.06m layer | Preserve 0.06 raw; document 0.1 display precision without inflating measurement |
| All unknown below 4.5m | No inferred sand layer 4.5-end; unknown retained |
| PRE=3, POST=10 smoothing | Compare only with clear processing flags and common-window option |
| Same CPT revised PDF + raw GEF | Source precedence plus conflict disclosure; no silent auto merge |
| B292 vs 292 different name same coordinates | Candidate match flagged as alias requiring evidence, not guess |
| No coordinates / invalid CRS | Project point map warns or excludes row |
| PRE baseline zero | Percent change undefined; show NA rather than divide by zero |
| Unmatched or >tolerance coordinates | Separate exception, not fabricated delta |
| PDF raster input | Review instead of unverified Ic |
| Raft/isolated FOS/settlement | No derived PASS until Excel equations and design criteria signed off |
| Workbook formula regression | Named inputs, unit conversions, depth profile, output values within approved tolerances |
| Full project PDF parity | Page-by-page numeric + graphical checks before exact-match claim |

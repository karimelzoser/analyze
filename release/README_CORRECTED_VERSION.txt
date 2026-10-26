CPT SILT ANALYZER — CORRECTED WINDOWS ENGINEERING PREVIEW
Date: 2026-10-26
Source: karimelzoser/analyze
Fix review: https://github.com/karimelzoser/analyze/pull/10
Windows validation: https://github.com/karimelzoser/analyze/actions/runs/40385229269

HOW TO USE
1. Extract this ZIP into a local folder on your Windows PC.
2. Double-click CPT_Silt_Analyzer.exe.
3. Select GEF, GFF, or supported vector-PDF CPT sources and run analysis.
4. Inspect CPT Analysis (quick 5-column results), Full Analysis, Source Audit,
   Review Evidence and engineering QA for any REVIEW cases.

CORRECTIONS
- Restores reference-release 3-of-4 agreement for primary PRE (3-sample)
  and POST (10-sample) Ic screening at 0.10 m reporting precision.
- Disagreements and positive unreportable thin layers remain REVIEW with
  raw evidence saved, not silently accepted as VERIFIED.
- Provisional conflicting full-depth source revisions are not published as
  accepted numerical values in the primary five-column workbook.
- Retains newer 2D/3D soil atlas, source-revision QA and foundation UI.

VERIFICATION
- GitHub Windows automated tests + GUI integration: PASS.
- Packaged executable built and startup smoke-tested: PASS.
- 448 actual source PDF audit workflow: PASS on separate branch workflow.
- SHA256 of this executable: fea4d518b5ed560ba897e5edfafed847b66a65fd9223eb2e507fccbe01aa2de3

IMPORTANT ENGINEERING LIMITATION
This software remains an ENGINEERING PREVIEW. The private real GEF/GFF
side-by-side validation against BOTH old binaries, XLSB/VBA formula parity,
and engineering signoff are not complete. Ground-classification Ic-screening
is not a laboratory USCS determination. Provisional foundation estimates
are not certified design/acceptance calculations. Review all REVIEW cases.

Do not replace a previously accepted project result without comparing the
same raw source, stage, cone area ratio, groundwater and source revision.

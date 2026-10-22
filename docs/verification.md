# Verification record — 22 October 2026

- **41 automated tests passed**, including the preserved 22 tests and 19 additions covering calibration validity, uncertainty propagation, ambiguous consensus, alarm hold/recovery, stale data, timestamps, intentional blind spots and the new HTTP endpoint. Actual output: `test-results.txt`.
- **320 new synthetic runs**: 16 scenarios × 20 withheld seeds; plus **3,000 calibration-validation readings**. Full evidence: `examples/study/`.
- Re-ran the benchmark and verified identical SHA-256 hashes for **20 evidence files**. Runtime and hashes: `study-reproducibility.json`.
- Re-ran the existing **50-run legacy benchmark** successfully. These remain distinct experiments with distinct metric definitions.
- Headless Microsoft Edge: exercised bias, common_mode, dual_fault, all_missing and high_noise; verified a 241-row JSON download, invalid-seed error, root-page link, no JavaScript errors and no horizontal overflow at 390px. Records: `study-ui-verification.json`; images: `study-desktop.png`, `study-mobile.png`.
- **15-page PDF**: rendered every page and visually reviewed the contact sheet, calibration mathematics and result pages. No clipping or orphaned table continuations observed.
- Existing `ui-verification.json`, `demo.mp4`, `demo-script.md` and older screenshots describe the prior single-channel demonstration. They are retained as legacy evidence, not proof of the new redundancy study. Live hardware and remote GitHub Actions were not tested.

The elevated-noise, dual-fault and common-mode failure results are retained. All numerical resume claims trace to `examples/study/summary.json`.

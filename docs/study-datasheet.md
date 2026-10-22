# Three-channel simulated calibration datasheet

Educational design artifact; no physical traceability or calibration certificate.

| Quantity | Assumption |
|---|---|
| Channel identifiers | A, B, C; same generic process quantity |
| Reference span | 0–100 engineering units |
| Nominal current intercepts (mA) | 4.10, 4.04, 3.98 |
| Nominal sensitivities (mA/unit) | 0.158, 0.159, 0.160 |
| Calibration design | Six levels × five repeats per channel |
| Calibration current-noise SD | 0.032 mA |
| Shared reference standard uncertainty | 0.05 units, assumed allowance |
| Fit | Current versus reference OLS; inverse for measurement |
| Fitted coefficients and residual SD | examples/study/drift-1001.json, calibrations |
| Raw calibration observations | examples/study/calibration-readings.json |
| Independent validation | 1,000 readings per channel at withheld levels |
| Agreement | max(0.5 units, 4 × combined independent standard uncertainty) |
| Isolation | Three consecutive disagreements |
| Stale threshold | Reported age >2 seconds |
| Recovery | Two consecutive usable batches |
| High / clear | Lower interval bound ≥80 / upper bound ≤77 |
| Low / clear | Upper interval bound ≤20 / lower bound ≥23 |
| Unknown-quality action | Withhold estimate; hold prior process alarms |

Synthetic sensor independence, affine response and representative calibration noise are assumptions. Common errors and noise mismatch are explicitly tested, not automatically corrected.

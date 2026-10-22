# Decision before implementation: instrument measurement validation

Date: 22 October 2026. This decision follows inspection of the current engine, calibration, benchmark, dashboard, server, live client, Modbus parser, tests, recorded results, README and report source.

## Audit of the current path

CSV/generated/Modbus current -> fixed five-point affine conversion -> temporal diagnostic flags -> quality gate -> held hysteretic process alarms -> event log/dashboard/export. The engine is isolated from HTTP and UI code. The live interface tracks heartbeat age and retains bounded history.

The calibration points are exactly collinear constructed values. The fit has no noisy repeats, independent validation or uncertainty budget. The returned reference RMSE is a monitoring-trace error calculated only on accepted samples, not an independent calibration certificate. Rejecting difficult samples can make that metric optimistic unless availability is also reported.

Single-signal spike/noise/stuck rules lack information to distinguish some real process changes from sensor faults. Synthetic reference-assisted drift works only when a reference is supplied; CSV and live input do not provide one. The benchmark exposes this: healthy steps produce false positives, isolated spikes have 9.1% sample precision because diagnostic windows/quality holds extend beyond the pulse, and unreferenced drift is not detected within its injected interval.

The quality/alarm separation, hysteresis, two-sample recovery, missing-data handling, deterministic experiments, parsing and protocol checks are meaningful engineering work worth retaining. Short code is not the problem. Weak observability and incomplete evaluation are the problem.

## Evaluate the five suggestions

| Suggestion | Decision | Reason |
|---|---|---|
| Calibration residuals and uncertainty | Accept with a new purpose | Fit noisy repeated calibration readings, validate on withheld levels, and use propagated uncertainty to normalize sensor disagreement. Residual charts alone would not fix diagnosis. |
| More fault injection | Modify | The current suite already has ten scenarios. Add faults that test redundancy assumptions, healthy transients, correlated/common faults and asynchronous measurements; use withheld seeds and magnitudes. |
| Delay/false alarms/misses | Accept and correct | Separate sensor-level diagnosis, false-isolation episodes, detected-event delay, output error and availability. Do not treat every recovery-hold sample as an independent false alarm. |
| Unknown-quality handling | Keep and extend | Already implemented and tested. Reuse the principle; add uncertainty-aware alarm decisions and unknown output when consensus is unavailable. |
| Noisy/changing conditions | Accept as validation | Use nominal and challenged noise, model mismatch and timing. Report failure envelopes instead of tuning until every demo looks successful. |

## Alternatives considered before coding

| Alternative | Technical value | Cost / limitation | Decision |
|---|---|---|---|
| Calibration analytics only | Makes measurement error visible | Does not distinguish process changes from sensor faults | Supporting component |
| Better single-channel temporal thresholds/CUSUM | Small implementation; useful when a stable reference model exists | Slow process drift and sensor drift remain confounded without additional information | Retain legacy baseline; not the new central contribution |
| Tank-model observer and residual diagnosis | Strong analytical-redundancy story | Requires trustworthy flow inputs, identified dynamics and a defensible model-error budget; currently risks classifying model mismatch as sensor failure | Deferred |
| Three-channel uncertainty-aware consistency checking | Separates common process motion from one disagreeing instrument; directly testable | Adds two hypothetical independent instruments; cannot resolve common-mode or agreeing dual faults | Selected |
| Machine learning/cloud/more protocol features | Adds infrastructure | Does not address the information gap | Excluded |

## Chosen engineering problem

For three independently calibrated, approximately synchronized instruments measuring the same quantity, determine whether a consistent pair exists; identify a persistently disagreeing channel; produce a usable estimate with a stated uncertainty; and preserve process-alarm state when evidence is insufficient.

Calibration becomes the foundation of instrument-health assessment rather than the headline feature. The primary claim will be explicitly conditional on independent redundancy and a predominantly single-fault model. A consistent majority is not proof of physical truth.

## Planned implementation and evaluation contract

- Retain the legacy engine, CSV mode, local Modbus mode and existing tests. Add a compact calibration module, consistency/quality state machine and deterministic three-channel test bench.
- Fit forward current-versus-reference calibration with noisy repeats; invert for measurements; propagate fit covariance and repeatability. Include a shared reference term that does not shrink when sensors are averaged.
- Compare against two explicit baselines: the old temporal method on channel A without oracle reference, and an unqualified three-channel median using the same additional sensor inputs as the new method.
- Never pass process truth or injected fault labels to the detector. Keep them in the evaluator only.
- Freeze engineering thresholds before withheld evaluation. Retain calibration, development and test seed lists. Publish scenario-level results and settings, including failures.
- Score channel isolation precision/recall, event detection and delay, nuisance episodes, measurement RMSE on common valid samples, output availability and uncertainty-band coverage. Report common-mode, dual-fault and timing failures separately.
- Keep the existing one-channel Modbus path distinct. Do not imply that six existing registers represent three independent physical instruments.

No physical hardware, safety certification, model-based observer, ML or deployment expansion is included. The dashboard will expose this study and its evidence rather than add unrelated features.

## Supporting sources

- [NIST: calibration of future measurements](https://www.itl.nist.gov/div898/handbook/mpc/section3/mpc366.htm): inversion of a fitted calibration relation.
- [NIST: calibration intervals](https://www.itl.nist.gov/div898/handbook/pmd/section5/pmd521.htm): uncertainty in inverse prediction.
- [NASA sensor validation report](https://ntrs.nasa.gov/api/citations/20205000446/downloads/TM-20205000446.pdf): redundancy as additional information for sensor validation. This project is not a reproduction or certification of that system.

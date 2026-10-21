# Simulated transmitter and calibration datasheet

Educational design artifact, not a calibration certificate.

| Item | Defined value |
|---|---|
| Instrument tag | LT-101 / CAL-101 |
| Input | 4–20 mA current-loop representation |
| Example calibrated span | 4.1–19.9 mA = 0–100 units |
| Calibration points | 4.1, 8.05, 12, 15.95, 19.9 mA / 0,25,50,75,100 units |
| Fit | Least-squares line, slope 6.32911, intercept -25.94937 |
| Physical reference traceability | None; synthetic pairs |
| Expected sample interval | Approximately 1 second |
| Bad-quality gap / stale threshold | Greater than 2 seconds |
| Recovery | Two consecutive valid samples |

Live tank signal maps 0–1.5 m level to 0–100 display units. Uncertainty, temperature drift and hardware calibration have not been measured. Reference-assisted drift is evaluated only where an independent synthetic reference is supplied to the engine.

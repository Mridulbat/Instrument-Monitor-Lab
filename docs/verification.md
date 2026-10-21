# Verification record

Date: 21 October 2026. Runtime: Python 3.12.14.
All 9 model tests passed. See test-results.txt for exact names.
Browser: headless installed Microsoft Edge driven by Playwright; desktop 1440x1100 and mobile 390x844.
Initial load, parameter/error interactions, CSV export and responsive width checked; monitor CSV import checked.
UI details: ui-verification.json. The browser test runner is not a runtime dependency.

Run `python -m unittest discover -s tests -v` and `python evaluate.py` from the project root.
Default measured metrics: {"Samples": 301, "Valid samples (%)": 82.72, "Alarm raises": 5, "Reference RMSE": 0.259, "Calibration slope": 6.32911, "Calibration intercept": -25.94937}

No hardware, cloud service, clean-OS installation, or formal safety validation was performed.
Python 3.10+ is the intended compatibility target; only the recorded runtime was exercised.
PDF visual inspection and final transport checks are recorded in final-verification.json.

Final: 14 model + HTTP tests passed on Python 3.14.7. Early Content-Length rejection tested before sending the body; direct oversized clients may observe a connection reset. The dashboard checks size before upload. PDF has 10 pages and 8 internal TOC links.

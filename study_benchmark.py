"""Reproduce the held-out study and raw evidence; no third-party dependencies."""
import csv
import json
from pathlib import Path
import sys
from statistics import mean
from math import sqrt
from random import Random
sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))
from study import SCENARIOS, TEST_SEEDS, CALIBRATION_SEEDS, DEVELOPMENT_SEEDS, PARAMETERS, calibrations, run, score


def main():
    root = Path(__file__).resolve().parent
    folder = root / 'examples' / 'study'
    folder.mkdir(exist_ok=True)
    scores = [score(run(kind, seed)) for kind in SCENARIOS for seed in TEST_SEEDS]
    summary = []
    for kind in SCENARIOS:
        group = [s for s in scores if s['scenario'] == kind]
        total = lambda key: sum(s[key] for s in group)
        avg = lambda key: mean(s[key] for s in group if s[key] is not None)
        tp, fp, fn = total('tp'), total('fp'), total('fn')
        delays = [d for s in group for d in s['delays']]
        summary.append(dict(scenario=kind, runs=len(group), precision=tp/(tp+fp) if tp+fp else None,
            recall=tp/(tp+fn) if tp+fn else None, false_episodes=total('false_episodes'),
            false_isolation_episodes=total('false_isolation_episodes'),
            events=total('events'), detected=total('detected'), mean_delay=mean(delays) if delays else None,
            availability=total('available')/total('samples'), coverage=total('covered')/total('available') if total('available') else None,
            rmse=avg('rmse'), median_rmse=avg('median_rmse'), common_rmse=avg('common_rmse'),
            common_median_rmse=avg('common_median_rmse'), legacy_rmse=avg('legacy_rmse'),
            legacy_availability=total('legacy_available')/total('samples'), legacy_flagged=total('legacy_flagged'),
            tp=tp, fp=fp, fn=fn))
    cals, readings = calibrations()
    calibration_validation = []
    for i, (cal, (a, b)) in enumerate(zip(cals, PARAMETERS)):
        rng = Random(9001+i)
        errors, covered = [], 0
        for level in range(5, 100, 10):
            for _ in range(100):
                raw = a+b*level+rng.gauss(0, .032)
                value, variance = cal.measure(raw)
                errors.append(value-level)
                covered += abs(value-level) <= 2*sqrt(variance+cal.reference_u**2)
        calibration_validation.append(dict(channel=i, samples=len(errors), rmse=sqrt(mean(e*e for e in errors)),
            max_abs_error=max(map(abs, errors)), bias=mean(errors), coverage=covered/len(errors)))
    result = dict(test_seeds=TEST_SEEDS, calibration_seeds=CALIBRATION_SEEDS,
                  development_seeds=DEVELOPMENT_SEEDS, run_count=len(scores), summary=summary,
                  calibration_validation=calibration_validation,
                  thresholds=dict(pair_sigma=4, pair_floor=.5, isolation_samples=3, recovery_samples=2, stale_seconds=2),
                  metrics_note='RMSE is mean of per-run RMSE; availability/coverage are pooled sample fractions. Delay is conditional on detection. Diagnosis combines explicit invalidity and persistent isolation.')
    (folder/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    (folder/'run-scores.json').write_text(json.dumps(scores, indent=2, allow_nan=False), encoding='utf-8')
    (folder/'calibration-readings.json').write_text(json.dumps(readings, indent=2), encoding='utf-8')
    with (folder/'summary.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0])); writer.writeheader(); writer.writerows(summary)
    for scenario in SCENARIOS:
        (folder/f'{scenario}-1001.json').write_text(json.dumps(run(scenario, 1001), indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()

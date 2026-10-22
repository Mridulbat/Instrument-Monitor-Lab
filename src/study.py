"""Deterministic synthetic test bench. Truth stays outside Validator.update."""
from dataclasses import asdict
from math import sin, sqrt
from random import Random
from statistics import median
from calibration import fit
from validation import Validator
from engine import analyze

CALIBRATION_SEEDS = (101, 102, 103)
DEVELOPMENT_SEEDS = (7, 11)
TEST_SEEDS = tuple(range(1001, 1021))
SCENARIOS = ('healthy', 'step', 'plateau', 'drift', 'bias', 'spikes', 'noise',
             'frozen', 'dropout', 'irregular', 'stale', 'all_missing',
             'common_mode', 'dual_fault', 'misaligned', 'high_noise')
PARAMETERS = ((4.10, .158), (4.04, .159), (3.98, .160))


def calibrations():
    result, readings = [], []
    for seed, (a, b) in zip(CALIBRATION_SEEDS, PARAMETERS):
        rng = Random(seed)
        reference = [float(level) for level in range(0, 101, 20) for _ in range(5)]
        current = [a + b * x + rng.gauss(0, .032) for x in reference]
        result.append(fit(reference, current))
        readings.append([dict(reference=x, current=y) for x, y in zip(reference, current)])
    return result, readings


def generate(scenario, seed):
    if scenario not in SCENARIOS: raise ValueError('Unknown study scenario.')
    rng = Random(seed)
    magnitude = rng.uniform(5, 10)
    faulty_channel = seed % 3
    def process(t):
        if scenario == 'plateau': return 50.0
        if scenario in ('step', 'all_missing'): return 85.0 if 70 <= t < 160 else 50.0
        return 50 + 8 * sin(t / 22)
    rows = []
    for t in range(241):
        if scenario == 'irregular' and 90 <= t < 150 and t % 10 in (1, 2, 3): continue
        truth = process(t)
        currents = [a + b * truth + rng.gauss(0, .032) for a, b in PARAMETERS]
        ages, faults = [0.0] * 3, [False] * 3
        active = 80 <= t < 180
        i = faulty_channel
        if active:
            if scenario == 'drift': currents[i] += PARAMETERS[i][1] * magnitude * (t - 80) / 100; faults[i] = True
            elif scenario == 'bias': currents[i] += PARAMETERS[i][1] * magnitude; faults[i] = True
            elif scenario == 'spikes' and t in (90, 120, 150): currents[i] += 3; faults[i] = True
            elif scenario == 'noise': currents[i] += rng.gauss(0, 1); faults[i] = True
            elif scenario == 'frozen': currents[i] = PARAMETERS[i][0] + PARAMETERS[i][1] * process(79); faults[i] = True
            elif scenario == 'dropout' and t % 20 < 5: currents[i] = None; faults[i] = True
            elif scenario == 'stale': ages[i] = 5; faults[i] = True
            elif scenario == 'all_missing': currents = [None] * 3; faults = [True] * 3
            elif scenario in ('common_mode', 'dual_fault'):
                for j in (range(3) if scenario == 'common_mode' else (0, 1)):
                    currents[j] += PARAMETERS[j][1] * magnitude; faults[j] = True
            elif scenario == 'misaligned':
                # Unreported timestamp skew: receiver cannot infer this hidden age.
                currents[i] = PARAMETERS[i][0] + PARAMETERS[i][1] * process(t - 8) + rng.gauss(0, .032)
                faults[i] = True
            elif scenario == 'high_noise':
                currents = [v + rng.gauss(0, .16) for v in currents]
        rows.append(dict(time_s=t, currents=currents, ages=ages, truth=truth, faults=faults))
    return rows


def run(scenario='drift', seed=1001):
    if not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed <= 1000000:
        raise ValueError('Seed must be an integer from 0 to 1000000.')
    cals, readings = calibrations()
    detector = Validator(cals)
    inputs = generate(scenario, seed)
    output = [detector.update(r['time_s'], r['currents'], r['ages']) for r in inputs]
    # Same calibration for legacy channel A; convert back to its nominal current convention.
    legacy_input = []
    for r in inputs:
        try: value = cals[0].measure(r['currents'][0])[0]
        except (ValueError, TypeError): value = None
        legacy_input.append(dict(time_s=r['time_s'], raw_mA=None if value is None else 4.1 + .158 * value, age_s=r['ages'][0]))
    legacy = analyze(legacy_input)['rows']
    for source, target, old in zip(inputs, output, legacy):
        # Median baseline uses electrically/calibration-valid currents but no age or agreement gate.
        baseline = []
        for c, raw in zip(cals, source['currents']):
            try: baseline.append(c.measure(raw)[0])
            except (ValueError, TypeError): pass
        target.update(truth=source['truth'], faults=source['faults'], currents=source['currents'], ages=source['ages'],
                      median=median(baseline) if baseline else None,
                      legacy_value=old.get('value') if old['valid'] else None,
                      legacy_flags=old['flags'].split('|') if old['flags'] else [])
    return dict(scenario=scenario, seed=seed, rows=output,
                calibrations=[asdict(c) for c in cals], calibration_readings=readings,
                note='Synthetic three-sensor study. Truth is evaluation-only. Common-mode/dual faults can defeat consensus.')


def score(result):
    rows = result['rows']
    tp = fp = fn = episodes = events = detected = 0
    delays = []
    false_isolation_episodes = 0
    for channel in range(3):
        previous_false = False
        previous_false_isolation = False
        event_start = None
        hit = None
        for row in rows + [dict(faults=[False]*3, isolated=[], invalid=[], time_s=rows[-1]['time_s']+1)]:
            fault = row['faults'][channel]
            # Electrical/age invalidity is explicit diagnosis; disagreement requires persistence.
            diagnosed = channel in row['isolated'] or channel in row['invalid']
            tp += int(fault and diagnosed); fp += int(not fault and diagnosed); fn += int(fault and not diagnosed)
            false = diagnosed and not fault
            episodes += int(false and not previous_false); previous_false = false
            false_isolation = channel in row['isolated'] and not fault
            false_isolation_episodes += int(false_isolation and not previous_false_isolation)
            previous_false_isolation = false_isolation
            if fault and event_start is None: event_start = row['time_s']; hit = None
            if fault and diagnosed and hit is None: hit = row['time_s']
            if not fault and event_start is not None:
                events += 1
                if hit is not None: detected += 1; delays.append(hit-event_start)
                event_start = None
    common = [r for r in rows if r['value'] is not None and r['median'] is not None]
    def rmse(key, subset):
        values = [(r[key]-r['truth'])**2 for r in subset if r[key] is not None]
        return sqrt(sum(values)/len(values)) if values else None
    valid = [r for r in rows if r['value'] is not None]
    return dict(scenario=result['scenario'], seed=result['seed'], tp=tp, fp=fp, fn=fn,
                false_episodes=episodes, false_isolation_episodes=false_isolation_episodes,
                events=events, detected=detected, delays=delays,
                samples=len(rows), available=len(valid), common_samples=len(common),
                rmse=rmse('value', valid), median_rmse=rmse('median', rows),
                common_rmse=rmse('value', common), common_median_rmse=rmse('median', common),
                legacy_rmse=rmse('legacy_value', rows),
                legacy_available=sum(r['legacy_value'] is not None for r in rows),
                legacy_flagged=sum(bool(set(r['legacy_flags'])-{'HIGH','LOW'}) for r in rows),
                covered=sum(abs(r['value']-r['truth'])<=r['expanded_u'] for r in valid))

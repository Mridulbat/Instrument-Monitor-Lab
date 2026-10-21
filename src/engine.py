"""Calibration, deterministic signal generation and stateful diagnostic rules."""
import csv
import io
import math
import random
import statistics


def calibrate(raw, reference):
    if len(raw) != len(reference) or len(raw) < 2:
        raise ValueError('At least two paired calibration points are required.')
    if not all(math.isfinite(v) for v in raw + reference):
        raise ValueError('Calibration values must be finite.')
    xbar, ybar = sum(raw) / len(raw), sum(reference) / len(reference)
    denominator = sum((x - xbar) ** 2 for x in raw)
    if denominator == 0:
        raise ValueError('Calibration readings must span more than one value.')
    slope = sum((x-xbar)*(y-ybar) for x,y in zip(raw,reference)) / denominator
    return slope, ybar - slope*xbar


def parse_csv(text):
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not {'time_s', 'raw_mA'} <= set(reader.fieldnames):
        raise ValueError('CSV requires time_s and raw_mA columns; blank raw_mA means missing.')
    rows = []
    for row in reader:
        if len(rows) >= 10000:
            raise ValueError('CSV limit is 10,000 rows.')
        t = float(row['time_s'])
        raw_text = row.get('raw_mA')
        if raw_text is None: raise ValueError('CSV row is missing a field.')
        raw = None if not raw_text.strip() else float(raw_text)
        if not math.isfinite(t) or t < 0 or (raw is not None and not math.isfinite(raw)):
            raise ValueError('CSV values must be finite and time nonnegative.')
        if rows and t <= rows[-1]['time_s']:
            raise ValueError('Timestamps must increase strictly.')
        rows.append({'time_s': t, 'raw_mA': raw})
    if not rows:
        raise ValueError('CSV contains no samples.')
    return rows


def demo_data(seed=11):
    rng = random.Random(seed)
    rows = []
    frozen = None
    for t in range(301):
        truth = 50 + 8 * math.sin(t / 25)
        if 60 <= t < 90: truth = 90
        if 210 <= t < 240: truth = 10
        raw = 4.1 + truth * 0.158 + rng.gauss(0, 0.015)
        label = 'normal'
        if 110 <= t < 125: raw, label = None, 'missing'
        if 150 <= t < 180:
            if frozen is None: frozen = raw
            raw, label = frozen, 'stuck'
        if 250 <= t < 265: raw, label = 22.0, 'range'
        rows.append({'time_s': t, 'raw_mA': raw, 'reference': truth, 'fault': label})
    return rows


def analyze(samples=None, low=20.0, high=80.0, hysteresis=3.0, stuck_seconds=8.0):
    if not all(math.isfinite(x) for x in (low, high, hysteresis, stuck_seconds)):
        raise ValueError('Settings must be finite.')
    if not (0 <= low < high <= 100 and 0 < hysteresis < (high-low)/2 and 1 <= stuck_seconds <= 60):
        raise ValueError('Require 0 <= low < high <= 100, positive hysteresis below half the gap, and a 1-60 s stuck window.')
    samples = demo_data() if samples is None else samples
    if not samples: raise ValueError('At least one sample is required.')
    slope, intercept = calibrate([4.1, 8.05, 12.0, 15.95, 19.9], [0, 25, 50, 75, 100])
    active, events, rows = set(), [], []
    anchor = start = previous_time = None
    errors = []
    recent = []
    drift_count = 0
    good_count = 2
    for sample in samples:
        t, raw = sample['time_s'], sample['raw_mA']
        if not math.isfinite(t) or t < 0 or (previous_time is not None and t <= previous_time):
            raise ValueError('Timestamps must be finite, nonnegative and strictly increasing.')
        if raw is not None and not math.isfinite(raw): raise ValueError('Nonfinite raw signal.')
        gap = previous_time is not None and t - previous_time > 2
        flags = {'GAP'} if gap else set()
        value = None if raw is None else slope * raw + intercept
        if sample.get('age_s', 0) > 2: flags.add('STALE')
        if raw is None:
            flags.add('MISSING'); anchor = start = None
        elif raw < 4 or raw > 20:
            flags.add('RANGE'); anchor = start = None
        else:
            if gap or anchor is None or abs(raw-anchor) > 0.002:
                anchor, start = raw, t
            if t-start >= stuck_seconds: flags.add('STUCK')
            if len(recent) >= 5 and abs(value-statistics.median(recent[-5:])) > 12:
                flags.add('SPIKE')
            if len(recent) >= 9:
                window = recent[-9:] + [value]
                differences = [b-a for a,b in zip(window,window[1:])]
                if statistics.pstdev(differences) > 3: flags.add('NOISY')
            if 'reference' in sample and abs(value-sample['reference']) > 3:
                drift_count += 1
            else: drift_count = 0
            if drift_count >= 5: flags.add('DRIFT')
            recent.append(value)
            recent = recent[-10:]
        if raw is None or 'RANGE' in flags or gap or 'STALE' in flags:
            recent = []; drift_count = 0
        bad = bool(flags.intersection({'MISSING','RANGE','GAP','STUCK','STALE','SPIKE','NOISY','DRIFT'}))
        if bad:
            good_count = 0
        else:
            good_count += 1
        if good_count < 2:
            flags.add('QUALITY_UNKNOWN')
            flags.update(active.intersection({'HIGH','LOW'}))
            quality = 'BAD' if bad else 'RECOVERING'
        else:
            quality = 'GOOD'
            if value >= high or ('HIGH' in active and value > high-hysteresis): flags.add('HIGH')
            if value <= low or ('LOW' in active and value < low+hysteresis): flags.add('LOW')
        for flag in sorted(flags-active): events.append({'time_s': t, 'event': flag, 'state': 'RAISED'})
        for flag in sorted(active-flags): events.append({'time_s': t, 'event': flag, 'state': 'CLEARED'})
        valid = quality == 'GOOD'
        if valid and 'reference' in sample: errors.append((value-sample['reference'])**2)
        rows.append({**sample, 'value': value, 'flags': '|'.join(sorted(flags)), 'valid': valid, 'quality': quality})
        active, previous_time = flags, t
    metrics = {'Samples': len(rows), 'Valid samples (%)': round(100*sum(r['valid'] for r in rows)/len(rows), 2),
               'Alarm raises': sum(e['state']=='RAISED' for e in events),
               'Reference RMSE': round(math.sqrt(sum(errors)/len(errors)), 3) if errors else None,
               'Calibration slope': round(slope, 5), 'Calibration intercept': round(intercept, 5)}
    return {'rows': rows, 'events': events, 'metrics': metrics,
            'note': 'Educational 4-20 mA simulation, mapped to 0-100 units. Bad quality holds active process alarms; 2 good samples establish recovery. Drift detection requires a reference. Gap/stale threshold: 2 s. Rules are advisory.'}

def RUN(p):
    p = dict(p)
    if 'csv' in p:
        p['samples'] = parse_csv(p.pop('csv'))
    return analyze(**p)

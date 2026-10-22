"""Three-channel consistency: independent inputs only, no truth or fault labels."""
from itertools import combinations
from math import isfinite, sqrt


class Validator:
    """Fixed thresholds chosen before held-out evaluation; one persistent outlier assumed."""
    def __init__(self, calibrations):
        if len(calibrations) != 3:
            raise ValueError('Exactly three calibrations required.')
        self.calibrations = calibrations
        self.counts = [0, 0, 0]
        self.good = 0
        self.previous_time = None
        self.high = self.low = False

    def update(self, time_s, currents, ages=None):
        if not isfinite(time_s) or time_s < 0 or (self.previous_time is not None and time_s <= self.previous_time):
            raise ValueError('Finite, nonnegative, strictly increasing timestamps required.')
        if len(currents) != 3 or (ages is not None and len(ages) != 3):
            raise ValueError('Exactly three currents and ages required.')
        ages = [0.0] * 3 if ages is None else ages
        gap = self.previous_time is not None and time_s - self.previous_time > 2
        self.previous_time = time_s
        values, variances, invalid = [None] * 3, [None] * 3, []
        for i, (cal, raw, age) in enumerate(zip(self.calibrations, currents, ages)):
            try:
                if not isfinite(age) or age < 0 or age > 2 or gap:
                    raise ValueError('Stale or discontinuous data.')
                values[i], variances[i] = cal.measure(raw)
            except (ValueError, TypeError):
                invalid.append(i)
        available = [i for i in range(3) if i not in invalid]
        pairs = [(i, j) for i, j in combinations(available, 2)
                 if abs(values[i] - values[j]) <= max(0.5, 4 * sqrt(variances[i] + variances[j]))]
        selected, suspects = [], []
        if len(pairs) == 3:
            selected = available
        elif len(pairs) == 1:
            selected = list(pairs[0])
            suspects = [i for i in available if i not in selected]
        # Two agreeing edges but not the third are ambiguous: do not choose a convenient pair.
        for i in range(3):
            self.counts[i] = self.counts[i] + 1 if i in suspects else 0
        isolated = [i for i in range(3) if self.counts[i] >= 3]
        self.good = self.good + 1 if selected else 0
        value = uncertainty = None
        quality = 'UNKNOWN'
        if selected:
            if self.good < 2:
                quality = 'RECOVERING'
            else:
                quality = 'CONSISTENT' if len(selected) == 3 else 'DEGRADED'
                value = sum(values[i] for i in selected) / len(selected)
                # Shared calibration-reference contribution must NOT average down.
                shared_u = max(self.calibrations[i].reference_u for i in selected)
                uncertainty = 2 * sqrt(sum(variances[i] for i in selected) / len(selected) ** 2 + shared_u ** 2)
                lower, upper = value - uncertainty, value + uncertainty
                if lower >= 80: self.high = True
                elif upper <= 77: self.high = False
                if upper <= 20: self.low = True
                elif lower >= 23: self.low = False
        return dict(time_s=time_s, values=values, selected=selected, invalid=invalid,
                    suspects=suspects, isolated=isolated, value=value, expanded_u=uncertainty,
                    quality=quality, high=self.high, low=self.low)

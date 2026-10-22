"""Forward affine calibration and first-order inverse uncertainty (standard library)."""
from dataclasses import dataclass
from math import isfinite, sqrt


@dataclass(frozen=True)
class Calibration:
    intercept: float
    slope: float
    residual_sd: float
    n: int
    mean_reference: float
    sxx: float
    minimum: float
    maximum: float
    reference_u: float = 0.05

    def measure(self, raw):
        if raw is None or not isfinite(raw) or not 3.8 <= raw <= 20.5:
            raise ValueError('Missing, non-finite or electrically out-of-range current.')
        value = (raw - self.intercept) / self.slope
        # A small edge allowance accommodates repeatability at calibration endpoints.
        if not self.minimum - 1 <= value <= self.maximum + 1:
            raise ValueError('Measurement outside validated calibration span.')
        fit_variance = self.residual_sd ** 2 * (1 / self.n +
                       (value - self.mean_reference) ** 2 / self.sxx)
        independent_variance = (self.residual_sd ** 2 + fit_variance) / self.slope ** 2
        return value, independent_variance


def fit(reference, current, reference_u=0.05):
    x, y = list(reference), list(current)
    if len(x) != len(y) or len(x) < 4 or not all(isfinite(v) for v in x + y):
        raise ValueError('At least four finite paired calibration readings required.')
    if not isfinite(reference_u) or reference_u < 0:
        raise ValueError('Reference uncertainty must be finite and nonnegative.')
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((v - mx) ** 2 for v in x)
    if sxx <= 0:
        raise ValueError('Calibration reference span must be nonzero.')
    slope = sum((a - mx) * (b - my) for a, b in zip(x, y)) / sxx
    if slope <= 1e-9:
        raise ValueError('Positive, non-degenerate transmitter slope required.')
    intercept = my - slope * mx
    residual_sd = sqrt(sum((b - intercept - slope * a) ** 2 for a, b in zip(x, y)) / (n - 2))
    if residual_sd < 1e-9:
        raise ValueError('Zero residual variance cannot support this empirical uncertainty model.')
    return Calibration(intercept, slope, residual_sd, n, mx, sxx, min(x), max(x), reference_u)

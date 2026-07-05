import math
import numpy as np

try:
    from scipy.optimize import curve_fit
except ImportError:  # pragma: no cover - fallback for environments without SciPy
    curve_fit = None


def _four_parameter_logistic(x, bottom, top, hill_slope, log_ic50):
    return bottom + (top - bottom) / (1 + 10 ** ((x - log_ic50) * hill_slope))


def fit_four_parameter_logistic(concentrations, responses):
    """Fit a 4-parameter logistic curve to dose-response data.

    The model is fitted in log10-space and returns the fitted IC10, IC50 and IC90.
    """
    conc = np.asarray(concentrations, dtype=float)
    resp = np.asarray(responses, dtype=float)

    valid = np.isfinite(conc) & np.isfinite(resp) & (conc > 0)
    conc = conc[valid]
    resp = resp[valid]

    if conc.size < 4:
        return None

    x = np.log10(conc)
    y = resp

    if np.ptp(y) < 1e-8:
        return None

    bottom_guess = float(np.min(y))
    top_guess = float(np.max(y))

    if curve_fit is not None:
        try:
            p0 = (bottom_guess, top_guess, -1.0, float(np.median(x)))
            bounds = ([-1e6, -1e6, -20, np.min(x) - 10], [1e6, 1e6, 20, np.max(x) + 10])
            params, _ = curve_fit(_four_parameter_logistic, x, y, p0=p0, bounds=bounds, maxfev=200000)
            bottom, top, hill_slope, log_ic50 = params
        except Exception:
            bottom, top, hill_slope, log_ic50 = bottom_guess, top_guess, -1.0, float(np.median(x))
    else:
        candidate_slopes = np.linspace(-3, 3, 121)
        candidate_log_ic50 = np.linspace(np.min(x), np.max(x), 121)
        best_error = None
        best_params = (bottom_guess, top_guess, -1.0, float(np.median(x)))
        for slope in candidate_slopes:
            for log_ic50 in candidate_log_ic50:
                prediction = _four_parameter_logistic(x, bottom_guess, top_guess, slope, log_ic50)
                error = float(np.sum((prediction - y) ** 2))
                if best_error is None or error < best_error:
                    best_error = error
                    best_params = (bottom_guess, top_guess, float(slope), float(log_ic50))
        bottom, top, hill_slope, log_ic50 = best_params

    if not np.isfinite(hill_slope) or not np.isfinite(log_ic50):
        return None

    ic50 = 10 ** log_ic50
    if hill_slope == 0:
        ic10 = None
        ic90 = None
    else:
        ic10 = 10 ** (log_ic50 + math.log10(9) / hill_slope)
        ic90 = 10 ** (log_ic50 - math.log10(9) / hill_slope)

    return {
        "bottom": float(bottom),
        "top": float(top),
        "hill_slope": float(hill_slope),
        "log_ic50": float(log_ic50),
        "ic50": float(ic50),
        "ic10": float(ic10) if ic10 is not None else None,
        "ic90": float(ic90) if ic90 is not None else None,
    }

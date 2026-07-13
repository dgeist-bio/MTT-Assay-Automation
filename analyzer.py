import math
import pandas as pd

from dose_response import fit_four_parameter_logistic


def parse_well_coordinates(well_string):
    """Hilfsfunktion: Konvertiert 'E2' in (row_idx, col_idx)."""
    row_char = well_string[0]
    col_idx = int(well_string[1:])
    row_idx = ord(row_char) - ord('A')
    return row_idx, col_idx


def describe_well_set(df, wells, blank):
    """Berechnet Statistik für eine Gruppe von Wells."""
    values = []
    for well in wells:
        r, c = parse_well_coordinates(well)
        try:
            values.append(float(df.iloc[r, c]))
        except Exception:
            continue

    if not values:
        return None

    series = pd.Series(values)
    mean_raw = series.mean()
    std_raw = series.std(ddof=1)
    rel_std = (std_raw / mean_raw * 100) if mean_raw else 0.0
    return {
        "count": int(len(values)),
        "mean": float(mean_raw),
        "std": float(std_raw),
        "rel_std": float(rel_std),
        "blank_corrected_mean": float(mean_raw - blank),
        "values": [float(v) for v in values],
        "e_min": float(min(values)),
        "e_max": float(max(values)),
    }


def parse_well_sort_key(well_string):
    row_char = well_string[0]
    col_idx = int(well_string[1:])
    return ord(row_char), col_idx


def build_dose_response_from_start_triplet(df, start_triplet, blank, start_concentration, reference_value=None):
    """
    Builds dose-response groups starting from a vertical triplet.
    """
    if not start_triplet or start_concentration is None:
        return None

    try:
        coords = [parse_well_coordinates(w) for w in start_triplet]
    except Exception:
        return None

    cols = [c for r, c in coords]
    rows = [r for r, c in coords]
    if len(set(cols)) != 1:
        return None

    start_col = int(cols[0])
    start_row = min(rows)
    sorted_rows = sorted(rows)
    if not (sorted_rows[1] == sorted_rows[0] + 1 and sorted_rows[2] == sorted_rows[1] + 1):
        return None

    try:
        current_conc = float(start_concentration)
    except Exception:
        return None

    dose_response = []
    max_col = 11
    max_row_idx = 7

    block_start = start_row
    while block_start <= max_row_idx - 2:
        for col in range(start_col, max_col + 1):
            group_wells = []
            for r in range(block_start, block_start + 3):
                well = f"{chr(ord('A') + r)}{col}"
                group_wells.append(well)

            summary = describe_well_set(df, group_wells, blank)
            if summary is None:
                continue

            summary["concentration"] = float(current_conc)
            summary["group_index"] = len(dose_response) + 1
            summary["wells"] = group_wells
            if reference_value is not None:
                try:
                    summary["viability"] = float((summary["blank_corrected_mean"] / reference_value) * 100) if reference_value else None
                except Exception:
                    summary["viability"] = None
            dose_response.append(summary)
            current_conc = current_conc / 2

        block_start += 3

    return dose_response if dose_response else None


def calculate_auc_log10(concentrations, values):
    """Compute the area under the curve on a log10-scaled concentration axis."""
    conc = sorted([float(c) for c in concentrations if c is not None and float(c) > 0], reverse=False)
    vals = [float(v) for c, v in sorted(zip(concentrations, values), key=lambda item: float(item[0])) if float(c) > 0]

    if len(conc) < 2:
        return None

    log_conc = [math.log10(c) for c in conc]
    auc = 0.0
    for i in range(1, len(log_conc)):
        x0, x1 = log_conc[i - 1], log_conc[i]
        y0, y1 = vals[i - 1], vals[i]
        auc += (x1 - x0) * (y0 + y1) / 2.0
    return float(auc)


def collect_raw_plate_data(df):
    """Return a JSON-serializable mapping of all raw OD values for all wells."""
    rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    plate = {}
    for row_idx, row_label in enumerate(rows):
        row_data = {}
        for col_idx in range(1, 13):
            well_name = f"{row_label}{col_idx}"
            value = df.iloc[row_idx, col_idx]
            row_data[str(col_idx)] = float(value) if pd.notna(value) else None
        plate[row_label] = row_data
    return plate


def calculate_viability(df, puro_wells, dmso_wells=None, blank_wells=None, start_concentration=None, start_triplet=None, include_summary=False):
    dmso_wells = dmso_wells or set()
    blank_wells = blank_wells or set()

    if blank_wells:
        blank_values = []
        for well in blank_wells:
            r, c = parse_well_coordinates(well)
            blank_values.append(df.iloc[r, c])
        blank = pd.Series(blank_values).mean()
    else:
        blank = pd.concat([df.iloc[:, 1], df.iloc[:, 12]]).mean()

    puro_summary = describe_well_set(df, puro_wells, blank)
    dmso_summary = describe_well_set(df, dmso_wells, blank)

    reference_name = "blank"
    reference_val = 1.0
    if dmso_summary:
        reference_val = dmso_summary["blank_corrected_mean"] or 1.0
        reference_name = "dmso"
        dmso_summary["viability"] = 100.0

    puro_viability = None
    if puro_summary and reference_val:
        puro_viability = (puro_summary["blank_corrected_mean"] / reference_val) * 100
        puro_summary["viability"] = float(puro_viability)

    mean_diff = None
    viability_diff = None
    if puro_summary and dmso_summary:
        mean_diff = dmso_summary["blank_corrected_mean"] - puro_summary["blank_corrected_mean"]
        if puro_summary.get("viability") is not None and dmso_summary.get("viability") is not None:
            viability_diff = dmso_summary["viability"] - puro_summary["viability"]

    dose_response = build_dose_response_from_start_triplet(
        df,
        start_triplet or [],
        blank,
        start_concentration,
        reference_value=reference_val,
    )

    z_prime = None
    z_prime_valid = False
    if puro_summary and dmso_summary:
        pos_mean = float(dmso_summary.get("blank_corrected_mean", 0.0) or 0.0)
        neg_mean = float(puro_summary.get("blank_corrected_mean", 0.0) or 0.0)
        pos_std = float(dmso_summary.get("std") or 0.0)
        neg_std = float(puro_summary.get("std") or 0.0)
        denominator = abs(pos_mean - neg_mean)
        if denominator:
            z_prime = 1 - ((3 * pos_std + 3 * neg_std) / denominator)
            z_prime_valid = z_prime >= 0.5

    signal_to_background = None
    if dmso_summary and blank:
        signal_to_background = float(dmso_summary.get("mean", 0.0) / blank) if blank else None

    dose_response_fit = None
    if dose_response:
        concentrations = [group["concentration"] for group in dose_response]
        viabilities = [group.get("viability") for group in dose_response if group.get("viability") is not None]
        if len(viabilities) >= 4:
            dose_response_fit = fit_four_parameter_logistic(concentrations, viabilities)

    e_min = None
    e_max = None
    if dose_response_fit:
        e_min = dose_response_fit.get("bottom")
        e_max = dose_response_fit.get("top")
    elif dose_response:
        viabilities = [group.get("viability") for group in dose_response if group.get("viability") is not None]
        if viabilities:
            e_min = min(viabilities)
            e_max = max(viabilities)

    auc_log10 = None
    if dose_response:
        concentrations = [group.get("concentration") for group in dose_response]
        values = [group.get("viability") for group in dose_response]
        auc_log10 = calculate_auc_log10(concentrations, values)

    raw_plate_data = collect_raw_plate_data(df)

    summary = {
        "blank": float(blank),
        "reference_name": reference_name,
        "reference_value": float(reference_val),
        "puro": puro_summary,
        "dmso": dmso_summary,
        "mean_difference_blank_corrected": float(mean_diff) if mean_diff is not None else None,
        "viability_difference": float(viability_diff) if viability_diff is not None else None,
        "dose_response": dose_response,
        "z_prime": float(z_prime) if z_prime is not None else None,
        "z_prime_valid": bool(z_prime_valid),
        "signal_to_background": float(signal_to_background) if signal_to_background is not None else None,
        "dose_response_fit": dose_response_fit,
        "e_min": float(e_min) if e_min is not None else None,
        "e_max": float(e_max) if e_max is not None else None,
        "E_min": float(e_min) if e_min is not None else None,
        "E_max": float(e_max) if e_max is not None else None,
        "ic10": dose_response_fit["ic10"] if dose_response_fit else None,
        "ic50": dose_response_fit["ic50"] if dose_response_fit else None,
        "ic50_absolute": dose_response_fit["ic50_absolute"] if dose_response_fit else None,
        "ic50_relative": dose_response_fit["ic50_relative"] if dose_response_fit else None,
        "ic90": dose_response_fit["ic90"] if dose_response_fit else None,
        "hill_slope": dose_response_fit["hill_slope"] if dose_response_fit else None,
        "auc_log10": float(auc_log10) if auc_log10 is not None else None,
        "raw_plate_data": raw_plate_data,
    }

    full_plate_viability = ((df.iloc[0:8, 1:13] - blank) / reference_val) * 100

    status = "OK"
    if puro_summary and puro_viability is not None and puro_viability > 30:
        status = f"WARNUNG: Puromycin-Kontrolle fehlgeschlagen ({puro_viability:.1f}% Viabilität)!"

    if dmso_summary:
        status += f" DMSO-Referenz basierend auf Blank-korrigiertem Mittelwert."

    if include_summary:
        return full_plate_viability, status, summary
    return full_plate_viability, status
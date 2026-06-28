import pandas as pd

def parse_well_coordinates(well_string):
    """Hilfsfunktion: Konvertiert 'E2' in (row_idx, col_idx)"""
    row_char = well_string[0] # z.B. 'E'
    col_idx = int(well_string[1:]) # z.B. '2' -> 1
    row_idx = ord(row_char) - ord('A') # 'A'=0, 'B'=1
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
        "values": [float(v) for v in values]
    }

def parse_well_sort_key(well_string):
    row_char = well_string[0]
    col_idx = int(well_string[1:])
    return ord(row_char), col_idx


def build_dose_response_from_start_triplet(df, start_triplet, blank, start_concentration):
    """
    Builds dose-response groups starting from a vertical triplet (e.g. ['B3','C3','D3']).
    Pattern: iterate columns from start column to column 11, for the same three rows (triplicate),
    then move to the next block of three rows below and repeat (e.g. B/C/D -> E/F/G -> ...).
    """
    if not start_triplet or start_concentration is None:
        return None

    # Validate and parse start_triplet
    try:
        coords = [parse_well_coordinates(w) for w in start_triplet]
    except Exception:
        return None

    # all columns should be equal for a vertical triplet
    cols = [c for r, c in coords]
    rows = [r for r, c in coords]
    if len(set(cols)) != 1:
        return None

    start_col = int(cols[0])
    start_row = min(rows)
    # ensure rows are consecutive and form a block of 3
    sorted_rows = sorted(rows)
    if not (sorted_rows[1] == sorted_rows[0] + 1 and sorted_rows[2] == sorted_rows[1] + 1):
        return None

    try:
        current_conc = float(start_concentration)
    except Exception:
        return None

    dose_response = []
    max_col = 11
    max_row_idx = 7  # rows A-H -> 0-7

    block_start = start_row
    while block_start <= max_row_idx - 2:
        # for each column from start_col to max_col
        for col in range(start_col, max_col + 1):
            group_wells = []
            for r in range(block_start, block_start + 3):
                well = f"{chr(ord('A') + r)}{col}"
                group_wells.append(well)

            summary = describe_well_set(df, group_wells, blank)
            if summary is None:
                # still append structure so indexing remains predictable
                block_start += 0
                continue

            summary["concentration"] = float(current_conc)
            summary["group_index"] = len(dose_response) + 1
            summary["wells"] = group_wells
            dose_response.append(summary)
            current_conc = current_conc / 2

        block_start += 3

    return dose_response if dose_response else None


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

    summary = {
        "blank": float(blank),
        "reference_name": reference_name,
        "reference_value": float(reference_val),
        "puro": puro_summary,
        "dmso": dmso_summary,
        "mean_difference_blank_corrected": float(mean_diff) if mean_diff is not None else None,
        "viability_difference": float(viability_diff) if viability_diff is not None else None,
        "dose_response": build_dose_response_from_start_triplet(df, start_triplet or [], blank, start_concentration)
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
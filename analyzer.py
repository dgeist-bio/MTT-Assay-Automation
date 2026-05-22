import pandas as pd

def parse_well_coordinates(well_string):
    """Hilfsfunktion: Konvertiert 'E2' in (row_idx, col_idx)"""
    row_char = well_string[0] # z.B. 'E'
    col_idx = int(well_string[1:]) # z.B. '2' -> 1
    row_idx = ord(row_char) - ord('A') # 'A'=0, 'B'=1
    return row_idx, col_idx

def calculate_viability(df, puro_wells, control_wells, dmso_wells=None):
    dmso_wells = dmso_wells or set()

    # 1. Blank berechnen (Spalte 2 und Spalte 12 standardmäßig)
    blank = pd.concat([df.iloc[:, 1], df.iloc[:, 12]]).mean()

    # 2. Dynamische Kontroll-Berechnung (Medium)
    if control_wells:
        control_values = []
        for well in control_wells:
            r, c = parse_well_coordinates(well)
            control_values.append(df.iloc[r, c])
        control_raw = pd.Series(control_values).mean()
    else:
        # Fallback auf dein altes Standard-Medium, falls nichts ausgewählt wurde
        control_raw = df.iloc[1:4, 2].mean()
        
    control_val = control_raw - blank

    # 3. Dynamische PURO-Berechnung
    if puro_wells:
        puro_values = []
        for well in puro_wells:
            r, c = parse_well_coordinates(well)
            puro_values.append(df.iloc[r, c])
        puro_raw = pd.Series(puro_values).mean()
        puro_viability = ((puro_raw - blank) / control_val) * 100
    else:
        puro_viability = 0 # Keine Überprüfung möglich

    dmso_status = ""
    if dmso_wells:
        dmso_values = []
        for well in dmso_wells:
            r, c = parse_well_coordinates(well)
            dmso_values.append(df.iloc[r, c])
        dmso_raw = pd.Series(dmso_values).mean()
        dmso_viability = ((dmso_raw - blank) / control_val) * 100
        dmso_status = f" DMSO-Kontrolle: {dmso_viability:.1f}% Viabilität."

    # 4. Gesamte Platte berechnen (Auswertung Spalten 2 bis 12)
    full_plate_viability = ((df.iloc[0:8, 1:13] - blank) / control_val) * 100

    status = "OK"
    if puro_wells and puro_viability > 30: 
        status = f"WARNUNG: Puromycin-Kontrolle fehlgeschlagen ({puro_viability:.1f}% Viabilität)!"

    status += dmso_status
                
    return full_plate_viability, status
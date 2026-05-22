import pandas as pd

def calculate_viability(df, puro_wells):
    # 1. Blank berechnen
    blank = pd.concat([df.iloc[:, 1], df.iloc[:, 12]]).mean()

    # 2. Kontrolle (Medium) - bleibt vorerst fest, da es meist Standard ist
    control_raw = df.iloc[1:4, 2].mean()
    control_val = control_raw - blank

    # 3. Dynamische PURO-Berechnung
    puro_values = []
    for well in puro_wells:
        # Konvertiere "E2" zu Zeilen/Spalten-Index
        row_char = well[0] # z.B. 'E'
        col_idx = int(well[1:]) - 1 # z.B. '2' -> 1
        row_idx = ord(row_char) - ord('A') # 'A'=0, 'B'=1 ... 'E'=4
        puro_values.append(df.iloc[row_idx, col_idx])
    
    puro_raw = pd.Series(puro_values).mean()
    puro_viability = ((puro_raw - blank) / control_val) * 100

    # 4. Gesamte Platte berechnen
    full_plate_viability = ((df.iloc[0:8, 1:13] - blank) / control_val) * 100

    status = "OK"
    if puro_viability > 30: 
        status = f"WARNUNG: Puromycin-Kontrolle fehlgeschlagen ({puro_viability:.1f}% Viabilität)!"
                
    return full_plate_viability, status
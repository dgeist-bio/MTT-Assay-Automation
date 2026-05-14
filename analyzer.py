import pandas as pd

def calculate_viability(df):
    # 1. Blank berechnen (A1 und H12)
    blank = pd.concat([df.iloc[:, 1], df.iloc[:, 12]]).mean()

    # 2. Kontrolle (Medium): B2, C2, D2 
    control_raw = df.iloc[1:4, 2].mean()
    control_val = control_raw - blank

    # 3. PURO (Zelltod-Kontrolle): E2, F2, G2
    puro_raw = df.iloc[4:7, 2].mean()
    puro_viability = ((puro_raw - blank) / control_val) * 100

    # 4. Gesamte Platte berechnen
    full_plate_viability = ((df.iloc[0:8, 1:13] - blank) / control_val) * 100

    # Debug-Prints
    print(f"Check: Kontrolle (Medium) Mittelwert: {control_raw:.4f}")
    print(f"Check: PURO (Zelltod) Mittelwert: {puro_raw:.4f}")
    print(f"Check: PURO Viabilität: {puro_viability:.2f}%")

    # 5. Status-Logik
    status = "OK"
    if puro_viability > 30: 
        status = f"WARNUNG: Puromycin-Kontrolle fehlgeschlagen ({puro_viability:.1f}% Viabilität)!"
                
    # WICHTIG: Nur das hier zurückgeben
    return full_plate_viability, status
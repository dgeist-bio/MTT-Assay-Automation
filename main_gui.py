import sys
import matplotlib.pyplot as plt
import seaborn as sns
import os
import tkinter as tk
from tkinter import filedialog, messagebox

from analyzer import calculate_viability
from data_loader import load_data

def select_and_run():
    # 1. Liste der ausgewählten Dateien wird ausgewählt
    ausgewaehlte_dateien = filedialog.askopenfilenames(
        title="Wähle die Textdateien aus",
        filetypes=[("Softmax Pro Dateien", "*.txt *.tsv *.asc *.csv"), ("Alle Dateien", "*.*")]
    )
    
    # 2. Nur weitermachen, wenn der User nicht "Abbrechen" geklickt hat
    if ausgewaehlte_dateien:
        # Die ganze Liste wird an die Analyse-Funktion übergeben
        run_full_analysis_flexible(ausgewaehlte_dateien)

def run_full_analysis_flexible(dateiliste):
    # Output-Ordner auf dem Desktop definieren
    output_folder = os.path.join(os.path.expanduser("~"), "Desktop", "MTT_Ergebnisse")
    if not os.path.exists(output_folder): 
        os.makedirs(output_folder)

    erfolgreich_verarbeitet = 0
    
    # WICHTIG: Die Liste der Pfade wird in dieser Schleife durchgegangen
    for pfad in dateiliste:
        # Jetzt wird der korrekte, volle Pfad an den Loader gegeben
        df = load_data(pfad)
        
        if df is None: 
            continue
        
        # Berechnung über analyzer.py
        res, status_msg = calculate_viability(df)
        
        # Dateinamen für den Titel und das Speichern extrahieren
        basis_name = os.path.basename(pfad).split('.')[0]

        # Heatmap erstellen
        plt.figure(figsize=(10, 6))
        sns.heatmap(res, annot=True, fmt=".1f", cmap='RdYlGn', center=100, vmin=0, vmax=120, xticklabels=range(1, 13), yticklabels=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])
        
        # Titel setzen (mit Qualitätscheck aus analyzer.py)
        if "WARNUNG" in status_msg:
            plt.title(f"MTT: {basis_name}\n{status_msg}", color='red', fontweight='bold')
        else:
            plt.title(f"MTT: {basis_name}\nStatus: OK (Puro-Check bestanden)")

        plt.xlabel('Spalte (Tecan)')
        plt.ylabel('Zeile (Tecan)')
    
        # Bild speichern
        save_path = os.path.join(output_folder, f"{basis_name}.png")
        plt.savefig(save_path)
        plt.close() # Ganz wichtig, sonst bleiben 100 Fenster im Hintergrund offen
        erfolgreich_verarbeitet += 1

    messagebox.showinfo("Erfolg", f"Analyse fertig!\n{erfolgreich_verarbeitet} Heatmaps wurden gespeichert unter:\n{output_folder}")

# --- GUI SETUP ---
def start_app():
    root = tk.Tk()
    root.title("MTT Auto-Analyzer v1.1")
    root.geometry("400x250")

    # Überschrift
    tk.Label(root, text="MTT-Daten Analyse", font=("Arial", 14, "bold"), pady=20).pack()

    # GUI mit grünem Button zum Auswählen der Dateien
    btn = tk.Button(root, 
                    text="ORDNER AUSWÄHLEN & STARTEN", 
                    command=select_and_run, 
                    bg="#2ecc71", 
                    fg="white", 
                    font=("Arial", 10, "bold"), 
                    padx=20, 
                    pady=10)
    btn.pack(pady=20)

    # Infotext unten
    info = tk.Label(root, text="Output: Desktop/MTT_Ergebnisse", font=("Arial", 8, "italic"))
    info.pack(side="bottom", pady=10)

    root.mainloop()

if __name__ == "__main__":
    start_app()
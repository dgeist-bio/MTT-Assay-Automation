import sys
import matplotlib.pyplot as plt
import seaborn as sns
import os
import customtkinter as ctk #
from tkinter import filedialog, messagebox

# Deine vorhandenen Module
from analyzer import calculate_viability
from data_loader import load_data

# Erscheinungsbild-Einstellungen
ctk.set_appearance_mode("dark")  
ctk.set_default_color_theme("blue") 

class MTTAnalyzerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Fenster-Konfiguration
        self.title("MTT Auto-Analyzer v1.1 - Professional Edition")
        self.geometry("600x600")

        # Layout-Struktur
        self.label = ctk.CTkLabel(self, text="MTT-Daten Analyse", font=("Arial", 20, "bold"))
        self.label.pack(pady=(30, 10))

        self.puro_wells = set()
        self.create_plate_grid()

        self.sub_label = ctk.CTkLabel(self, text="Automatisierte Heatmap-Generierung (300dpi)", font=("Arial", 12))
        self.sub_label.pack(pady=(0, 20))

        # Moderner Button
        self.btn = ctk.CTkButton(self, 
                                text="DATEIEN AUSWÄHLEN & STARTEN", 
                                command=self.select_and_run,
                                font=("Arial", 12, "bold"),
                                height=45,
                                corner_radius=10)
        self.btn.pack(pady=20)

        # Fortschrittsbalken für den "Showroom"-Effekt
        self.progress = ctk.CTkProgressBar(self, width=300)
        self.progress.pack(pady=10)
        self.progress.set(0)

    def create_plate_grid(self):
        self.grid_frame = ctk.CTkFrame(self)
        self.grid_frame.pack(pady=10, padx=10)

        self.default_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
        self.accent_color = "red"
        
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        for r_idx, row_label in enumerate(rows):
            for c_idx in range(1, 13):
                well_name = f"{row_label}{c_idx}"
                btn = ctk.CTkButton(self.grid_frame, 
                                    text=well_name, 
                                    width=30, height=25, 
                                    corner_radius=3)
                
                # Standardzustand (dein Theme-Blau)
                btn.configure(fg_color=self.default_color)
                btn.configure(command=lambda b=btn, name=well_name: self.toggle_well(b, name))
                btn.grid(row=r_idx, column=c_idx, padx=1, pady=1)

    def toggle_well(self, btn, name):
        if name in self.puro_wells:
            self.puro_wells.remove(name)
            btn.configure(fg_color=self.default_color) # Zurück zum UI-Standard
        else:
            self.puro_wells.add(name)
            btn.configure(fg_color="#E74C3C")
        print(f"Puromycin-Wells aktuell: {self.puro_wells}")

        # Infotext unten
        self.info = ctk.CTkLabel(self, text="Speicherort: Desktop/MTT_Ergebnisse", font=("Arial", 10, "italic"))
        self.info.pack(side="bottom", pady=20)

    def select_and_run(self):
        # Dateiauswahl
        ausgewaehlte_dateien = filedialog.askopenfilenames(
            title="Wähle die Textdateien aus",
            filetypes=[("Softmax Pro Dateien", "*.txt *.tsv *.asc *.csv"), ("Alle Dateien", "*.*")]
        )
        
        if ausgewaehlte_dateien:
            self.run_full_analysis_flexible(ausgewaehlte_dateien)

    def run_full_analysis_flexible(self, dateiliste):
        output_folder = os.path.join(os.path.expanduser("~"), "Desktop", "MTT_Ergebnisse")
        if not os.path.exists(output_folder): 
            os.makedirs(output_folder)

        anzahl = len(dateiliste)
        erfolgreich_verarbeitet = 0
        
        for i, pfad in enumerate(dateiliste):
            # Fortschrittsbalken aktualisieren
            self.progress.set((i + 1) / anzahl)
            self.update_idletasks()

            df = load_data(pfad)
            if df is None: continue
            
            res, status_msg = calculate_viability(df, self.puro_wells)
            basis_name = os.path.basename(pfad).split('.')[0]

            # Heatmap mit viridis
            plt.figure(figsize=(10, 6))
            sns.heatmap(res, annot=True, fmt=".1f", cmap='viridis', center=100, 
                        xticklabels=range(1, 13), yticklabels=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])
            
            if "WARNUNG" in status_msg:
                plt.title(f"MTT: {basis_name}\n{status_msg}", color='red', fontweight='bold')
            else:
                plt.title(f"MTT: {basis_name}\nStatus: OK (Puro-Check bestanden)")

            plt.xlabel('Spalte (1-12)')
            plt.ylabel('Zeile (A-H)')

            # Speichern in hoher Auflösung
            save_path = os.path.join(output_folder, f"{basis_name}.png")
            plt.savefig(save_path, dpi=300) # 300dpi für die Publikationsqualität
            plt.close() 
            erfolgreich_verarbeitet += 1

        messagebox.showinfo("Erfolg", f"Analyse fertig!\n{erfolgreich_verarbeitet} Heatmaps wurden gespeichert.")
        self.progress.set(0) # Reset nach Fertigstellung

if __name__ == "__main__":
    app = MTTAnalyzerApp()
    app.mainloop()
import sys
import matplotlib.pyplot as plt
import seaborn as sns
import os
import customtkinter as ctk 
from tkinter import filedialog, messagebox

from analyzer import calculate_viability
from data_loader import load_data

ctk.set_appearance_mode("dark")  
ctk.set_default_color_theme("blue") 

class MTTAnalyzerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MTT Auto-Analyzer v1.2 - Professional Edition")
        self.geometry("800x800")

        self.label = ctk.CTkLabel(self, text="MTT-Daten Analyse", font=("Arial", 20, "bold"))
        self.label.pack(pady=(20, 10))

        # Well-Speicher
        self.puro_wells = set()
        self.control_wells = set()
        self.dmso_wells = set()

        # --- NEU: Modus-Auswahl für das Klicken ---
        self.mode_frame = ctk.CTkFrame(self)
        self.mode_frame.pack(pady=10)
        
        self.selection_mode = ctk.StringVar(value="puro")
        
        self.r_puro = ctk.CTkRadioButton(self.mode_frame, text="Puromycin markieren (Rot)", 
                                         variable=self.selection_mode, value="puro", fg_color="#E74C3C")
        self.r_puro.grid(row=0, column=0, padx=15, pady=5)
        
        self.r_control = ctk.CTkRadioButton(self.mode_frame, text="Medium/Kontrolle markieren (Grün)", 
                                            variable=self.selection_mode, value="control", fg_color="#2ECC71")
        self.r_control.grid(row=0, column=1, padx=15, pady=5)

        self.r_dmso = ctk.CTkRadioButton(self.mode_frame, text="DMSO markieren (Blau)", 
                                            variable=self.selection_mode, value="dmso", fg_color="#3498DB")
        self.r_dmso.grid(row=0, column=2, padx=15, pady=5)

        # ------------------------------------------

        self.create_plate_grid()

        self.sub_label = ctk.CTkLabel(self, text="Automatisierte Heatmap-Generierung (300dpi)", font=("Arial", 12))
        self.sub_label.pack(pady=(15, 5))

        self.btn = ctk.CTkButton(self, 
                                text="DATEIEN AUSWÄHLEN & STARTEN", 
                                command=self.select_and_run,
                                font=("Arial", 12, "bold"),
                                height=45,
                                corner_radius=10)
        self.btn.pack(pady=15)

        self.progress = ctk.CTkProgressBar(self, width=300)
        self.progress.pack(pady=10)
        self.progress.set(0)

        self.info = ctk.CTkLabel(self, text="Speicherort: Desktop/MTT_Ergebnisse", font=("Arial", 10, "italic"))
        self.info.pack(side="bottom", pady=15)

    def create_plate_grid(self):
        self.grid_frame = ctk.CTkFrame(self)
        self.grid_frame.pack(pady=10, padx=10)

        self.default_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
        
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        for r_idx, row_label in enumerate(rows):
            for c_idx in range(1, 13):
                well_name = f"{row_label}{c_idx}"
                btn = ctk.CTkButton(self.grid_frame, 
                                    text=well_name, 
                                    width=35, height=30, 
                                    corner_radius=3)
                
                btn.configure(fg_color=self.default_color)
                btn.configure(command=lambda b=btn, name=well_name: self.toggle_well(b, name))
                btn.grid(row=r_idx, column=c_idx, padx=1, pady=1)

    def toggle_well(self, btn, name):
        current_mode = self.selection_mode.get()

        if current_mode == "puro":
            # Falls es in der anderen Gruppe war, dort entfernen
            if name in self.control_wells: self.control_wells.remove(name)
            
            if name in self.puro_wells:
                self.puro_wells.remove(name)
                btn.configure(fg_color=self.default_color)
            else:
                self.puro_wells.add(name)
                btn.configure(fg_color="#E74C3C") # Rot für Puro

        elif current_mode == "control":
            self.puro_wells.discard(name)
            self.dmso_wells.discard(name)
            
            if name in self.control_wells:
                self.control_wells.remove(name)
                btn.configure(fg_color=self.default_color)
            else:
                self.control_wells.add(name)
                btn.configure(fg_color="#2ECC71") # Grün für Kontrolle/Medium

        elif current_mode == "dmso":
            self.puro_wells.discard(name)
            self.control_wells.discard(name)
            
            if name in self.dmso_wells:
                self.dmso_wells.remove(name)
                btn.configure(fg_color=self.default_color)
            else:
                self.dmso_wells.add(name)
                btn.configure(fg_color="#3498DB") # Blau für DMSO

        print(f"Puro-Wells: {self.puro_wells} | Control-Wells: {self.control_wells} | DMSO-Wells: {self.dmso_wells}")

    def select_and_run(self):
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
            self.progress.set((i + 1) / anzahl)
            self.update_idletasks()

            df = load_data(pfad)
            if df is None: continue
            
            # ÜBERGABE AN RECHNER: Jetzt mit allen Well-Listen
            res, status_msg = calculate_viability(df, self.puro_wells, self.control_wells, self.dmso_wells)
            basis_name = os.path.basename(pfad).split('.')[0]

            plt.figure(figsize=(10, 6.5))
            sns.heatmap(res, annot=True, fmt=".1f", cmap='cividis', center=100, 
                        xticklabels=range(1, 13), yticklabels=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])
            
 # Zerlegen des Status-Strings für die zweizeilige Darstellung
            if "WARNUNG" in status_msg:
                # Teilt den String beim Ausrufezeichen oder am DMSO-Start
                if "DMSO-Kontrolle:" in status_msg:
                    puro_part, dmso_part = status_msg.split("! ")
                    titel_text = f"MTT: {basis_name}\n{puro_part}!\n{dmso_part}"
                else:
                    titel_text = f"MTT: {basis_name}\n{status_msg}"
                
                plt.title(titel_text, color='red', fontweight='bold', fontsize=12, pad=15)
            else:
                # Falls alles OK ist, aber DMSO-Werte da sind
                status_clean = status_msg.replace("OK", "Status: OK (Puro-Check bestanden)")
                status_clean = status_clean.replace(" DMSO-Kontrolle:", "\nDMSO-Kontrolle:")
                plt.title(f"MTT: {basis_name}\n{status_clean}", fontsize=12, pad=15)

            plt.xlabel('Spalte (1-12)')
            plt.ylabel('Zeile (A-H)')

            # WICHTIG: Verhindert das Abschneiden von mehrzeiligem Text
            plt.tight_layout()

            save_path = os.path.join(output_folder, f"{basis_name}.png")
            plt.savefig(save_path, dpi=300)
            plt.close()
            erfolgreich_verarbeitet += 1

        messagebox.showinfo("Erfolg", f"Analyse fertig!\n{erfolgreich_verarbeitet} Heatmaps wurden gespeichert.")
        self.progress.set(0)

if __name__ == "__main__":
    app = MTTAnalyzerApp()
    app.mainloop()
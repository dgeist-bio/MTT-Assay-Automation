import sys
import matplotlib.pyplot as plt
import seaborn as sns
import os
import customtkinter as ctk 
from tkinter import filedialog, messagebox

from analyzer import calculate_viability
from data_loader import load_data
import json
from fpdf import FPDF

ctk.set_appearance_mode("dark")  
ctk.set_default_color_theme("blue") 

class MTTAnalyzerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MTT Auto-Analyzer v1.3.0 - Professional Edition")
        self.geometry("900x900")

        self.label = ctk.CTkLabel(self, text="MTT-Daten Analyse", font=("Arial", 20, "bold"))
        self.label.pack(pady=(20, 10))

        # Well-Speicher
        self.puro_wells = set()
        self.blank_wells = set()
        self.dmso_wells = set()
        self.start_triplet = []

        # --- Modus-Auswahl für das Klicken ---
        self.mode_frame = ctk.CTkFrame(self)
        self.mode_frame.pack(pady=10)
        
        self.selection_mode = ctk.StringVar(value="puro")
        
        self.r_puro = ctk.CTkRadioButton(self.mode_frame, text="Puromycin (Brown)", 
                                         variable=self.selection_mode, value="puro", fg_color="#D87320")
        self.r_puro.grid(row=0, column=0, padx=15, pady=5)
        
        self.r_blank = ctk.CTkRadioButton(self.mode_frame, text="Blank (Blue)", 
                                           variable=self.selection_mode, value="blank", fg_color="#CFCCFF")
        self.r_blank.grid(row=0, column=1, padx=15, pady=5)

        self.r_dmso = ctk.CTkRadioButton(self.mode_frame, text="DMSO (Red)", 
                            variable=self.selection_mode, value="dmso", fg_color="#CC2E2E")
        self.r_dmso.grid(row=0, column=2, padx=15, pady=5)

        self.r_start = ctk.CTkRadioButton(self.mode_frame, text="Start-Triplet (Lila)", 
                           variable=self.selection_mode, value="start", fg_color="#9B59B6")
        self.r_start.grid(row=0, column=3, padx=15, pady=5)

        # ------------------------------------------

        self.create_plate_grid()

        self.conc_frame = ctk.CTkFrame(self)
        self.conc_frame.pack(pady=10)

        self.conc_label = ctk.CTkLabel(self.conc_frame, text="Startkonzentration (µM):", font=("Arial", 12))
        self.conc_label.grid(row=0, column=0, padx=5, pady=5)

        self.start_conc = ctk.CTkEntry(self.conc_frame, width=120)
        self.start_conc.insert(0, "10")
        self.start_conc.grid(row=0, column=1, padx=5, pady=5)

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

        self.export_frame = ctk.CTkFrame(self)
        self.export_frame.pack(pady=10)

        self.json_button = ctk.CTkButton(self.export_frame,
                                        text="JSON Export speichern",
                                        command=self.save_template_json,
                                        font=("Arial", 12),
                                        height=35,
                                        corner_radius=8)
        self.json_button.grid(row=0, column=0, padx=10)

        self.pdf_button = ctk.CTkButton(self.export_frame,
                                       text="PDF Summary speichern",
                                       command=self.save_pdf_summary,
                                       font=("Arial", 12),
                                       height=35,
                                       corner_radius=8)
        self.pdf_button.grid(row=0, column=1, padx=10)

        self.load_json_button = ctk.CTkButton(self.export_frame,
                                           text="JSON Vorlage laden",
                                           command=self.load_template_json,
                                           font=("Arial", 12),
                                           height=35,
                                           corner_radius=8)
        self.load_json_button.grid(row=0, column=2, padx=10)

        self.analysis_summary = None
        self.template_data = None

    def create_plate_grid(self):
        self.grid_frame = ctk.CTkFrame(self)
        self.grid_frame.pack(pady=10, padx=10)

        self.default_color = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
        self.well_buttons = {}
        
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
                self.well_buttons[well_name] = btn
                btn.grid(row=r_idx, column=c_idx, padx=1, pady=1)

    def toggle_well(self, btn, name):
        current_mode = self.selection_mode.get()

        if current_mode == "puro":
            self.blank_wells.discard(name)
            self.dmso_wells.discard(name)
            
            if name in self.puro_wells:
                self.puro_wells.remove(name)
                btn.configure(fg_color=self.default_color)
            else:
                self.puro_wells.add(name)
                btn.configure(fg_color="#8C4C18")

        elif current_mode == "blank":
            self.puro_wells.discard(name)
            self.dmso_wells.discard(name)
            
            if name in self.blank_wells:
                self.blank_wells.remove(name)
                btn.configure(fg_color=self.default_color)
            else:
                self.blank_wells.add(name)
                btn.configure(fg_color="#CFCCFF")

        elif current_mode == "dmso":
            self.puro_wells.discard(name)
            self.blank_wells.discard(name)
            
            if name in self.dmso_wells:
                self.dmso_wells.remove(name)
                btn.configure(fg_color=self.default_color)
            else:
                self.dmso_wells.add(name)
                btn.configure(fg_color="#CC2E2E")
        elif current_mode == "start":
            # Selecting start triplet wells (max 3)
            self.puro_wells.discard(name)
            self.blank_wells.discard(name)
            self.dmso_wells.discard(name)
            
            if name in self.start_triplet:
                try:
                    self.start_triplet.remove(name)
                except ValueError:
                    pass
                btn.configure(fg_color=self.default_color)
            else:
                if len(self.start_triplet) >= 3:
                    messagebox.showinfo("Start-Triplet", "Es können maximal 3 Wells für das Start-Triplet ausgewählt werden.")
                else:
                    self.start_triplet.append(name)
                    btn.configure(fg_color="#9B59B6")
        print(f"Puro-Wells: {self.puro_wells} | Blank-Wells: {self.blank_wells} | DMSO-Wells: {self.dmso_wells} | Start-Triplet: {self.start_triplet}")

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
            res, status_msg, summary = calculate_viability(
                df,
                self.puro_wells,
                dmso_wells=self.dmso_wells,
                blank_wells=self.blank_wells,
                start_concentration=self.start_conc.get(),
                start_triplet=self.start_triplet,
                include_summary=True
            )
            self.analysis_summary = summary
            self.template_data = {
                "puro": sorted(list(self.puro_wells)),
                "blank": sorted(list(self.blank_wells)),
                "dmso": sorted(list(self.dmso_wells)),
                "start_triplet": list(self.start_triplet),
                "start_concentration": self.start_conc.get(),
                "active_file": os.path.basename(pfad),
                "summary": summary
            }
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

    def save_template_json(self):
        if not self.template_data:
            messagebox.showwarning("Keine Vorlage", "Bitte zuerst eine Analyse durchführen, damit die JSON-Vorlage erzeugt werden kann.")
            return

        output_folder = os.path.join(os.path.expanduser("~"), "Desktop", "MTT_Ergebnisse")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        json_path = os.path.join(output_folder, "mttexport_template.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.template_data, f, indent=2, ensure_ascii=False)

        messagebox.showinfo("JSON gespeichert", f"Die JSON-Vorlage wurde gespeichert: {json_path}")

    def load_template_json(self):
        json_path = filedialog.askopenfilename(
            title="JSON Vorlage laden",
            filetypes=[("JSON Dateien", "*.json"), ("Alle Dateien", "*.*")]
        )
        if not json_path:
            return

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.puro_wells = set(data.get("puro", []))
        self.blank_wells = set(data.get("blank", []))
        self.dmso_wells = set(data.get("dmso", []))
        self.template_data = data
        self.analysis_summary = data.get("summary")
        self.start_conc.delete(0, ctk.END)
        self.start_conc.insert(0, str(data.get("start_concentration", "10")))
        self.start_triplet = list(data.get("start_triplet", []))
        # refresh button colors to reflect loaded template
        try:
            self.refresh_button_colors()
        except Exception:
            pass

    def refresh_button_colors(self):
        for name, btn in getattr(self, 'well_buttons', {}).items():
            if name in self.puro_wells:
                btn.configure(fg_color="#E74C3C")
            elif name in self.blank_wells:
                btn.configure(fg_color="#F1C40F")
            elif name in self.dmso_wells:
                btn.configure(fg_color="#2ECC71")
            elif name in self.start_triplet:
                btn.configure(fg_color="#9B59B6")
            else:
                btn.configure(fg_color=self.default_color)

        messagebox.showinfo("JSON geladen", f"JSON-Vorlage erfolgreich geladen: {json_path}")

    def save_pdf_summary(self):
        if not self.analysis_summary:
            messagebox.showwarning("Keine Analyse", "Bitte zuerst eine Analyse durchführen.")
            return

        output_folder = os.path.join(os.path.expanduser("~"), "Desktop", "MTT_Ergebnisse")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        pdf_path = os.path.join(output_folder, "mttexport_summary.pdf")
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "MTT Analyse Zusammenfassung", ln=True)
        pdf.ln(4)

        pdf.set_font("Arial", size=12)
        def add_stat_block(name, stats):
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, f"{name}", ln=True)
            pdf.set_font("Arial", size=11)
            if not stats:
                pdf.cell(0, 7, "Keine Wells ausgewählt.", ln=True)
                pdf.ln(2)
                return
            pdf.cell(0, 7, f"Anzahl Wells: {stats['count']}", ln=True)
            pdf.cell(0, 7, f"Mittelwert: {stats['mean']:.3f}", ln=True)
            pdf.cell(0, 7, f"Standardabweichung: {stats['std']:.3f}", ln=True)
            pdf.cell(0, 7, f"Relative Standardabweichung: {stats['rel_std']:.2f}%", ln=True)
            pdf.cell(0, 7, f"Blank-korrigierter Mittelwert: {stats['blank_corrected_mean']:.3f}", ln=True)
            if stats.get('viability') is not None:
                pdf.cell(0, 7, f"Viabilität: {stats['viability']:.2f}%", ln=True)
            pdf.ln(2)

        add_stat_block("Puromycin", self.analysis_summary.get("puro"))
        add_stat_block("DMSO", self.analysis_summary.get("dmso"))

        dose_response = self.analysis_summary.get("dose_response")
        if dose_response:
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, "Dose Response (Puromycin)", ln=True)
            pdf.set_font("Arial", size=11)
            for group in dose_response:
                pdf.cell(0, 7, f"{group['concentration']:.3f} µM - Wells: {', '.join(group['wells'])}", ln=True)
                pdf.cell(0, 7, f"  Mittelwert: {group['mean']:.3f}, Std: {group['std']:.3f}, RSD: {group['rel_std']:.2f}%", ln=True)
            pdf.ln(2)

            # prepare IC50 plot
            try:
                xs = [g['concentration'] for g in dose_response]
                reference_val = self.analysis_summary.get('reference_value', 1.0) or 1.0
                ys = [(g['blank_corrected_mean'] / reference_val) * 100 for g in dose_response]
                # compute IC50 by linear interpolation on log10 concentrations
                import math
                ic50 = None
                for i in range(len(xs) - 1):
                    y1, y2 = ys[i], ys[i+1]
                    if (y1 >= 50 >= y2) or (y2 >= 50 >= y1):
                        x1_log = math.log10(xs[i]) if xs[i] > 0 else None
                        x2_log = math.log10(xs[i+1]) if xs[i+1] > 0 else None
                        if x1_log is not None and x2_log is not None and y2 != y1:
                            log_ic50 = x1_log + (50 - y1) * (x2_log - x1_log) / (y2 - y1)
                            ic50 = 10 ** (log_ic50)
                        break

                # plot
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.plot(xs, ys, marker='o')
                ax.set_xscale('log')
                ax.set_xlabel('Konzentration (µM)')
                ax.set_ylabel('Viabilität (%)')
                ax.set_title('Dose-Response')
                ax.grid(True, which='both', ls='--', lw=0.5)
                plot_path = os.path.join(output_folder, 'mttexport_ic50_plot.png')
                fig.tight_layout()
                fig.savefig(plot_path, dpi=150)
                plt.close(fig)

                # embed plot into PDF
                try:
                    pdf.add_page()
                except Exception:
                    pass
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 8, "Dose-Response Plot & IC50", ln=True)
                pdf.ln(2)
                pdf.image(plot_path, x=15, w=180)
                pdf.ln(4)
                if ic50:
                    pdf.set_font("Arial", size=12)
                    pdf.cell(0, 7, f"Geschätzte IC50: {ic50:.4g} µM", ln=True)
                else:
                    pdf.set_font("Arial", size=12)
                    pdf.cell(0, 7, "IC50 konnte nicht interpoliert werden (kein 50% Schnittpunkt).", ln=True)
                pdf.ln(4)
            except Exception:
                pass

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Berechnete Differenzen", ln=True)
        pdf.set_font("Arial", size=11)
        if self.analysis_summary.get("mean_difference_blank_corrected") is not None:
            pdf.cell(0, 7, f"Mittelwert DMSO - Mittelwert Puro (blank-korrigiert): {self.analysis_summary['mean_difference_blank_corrected']:.3f}", ln=True)
            pdf.cell(0, 7, f"Viabilitätsdifferenz: {self.analysis_summary['viability_difference']:.2f}%", ln=True)
        else:
            pdf.cell(0, 7, "Nicht genügend Daten für Differenzberechnung.", ln=True)

        pdf.output(pdf_path)
        messagebox.showinfo("PDF gespeichert", f"Die PDF-Zusammenfassung wurde gespeichert: {pdf_path}")

if __name__ == "__main__":
    app = MTTAnalyzerApp()
    app.mainloop()
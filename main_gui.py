import sys
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json
import customtkinter as ctk 
from tkinter import filedialog, messagebox

from analyzer import calculate_viability
from data_loader import load_data
import json
from fpdf import FPDF

def load_config(filename="config.json"):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)
    

ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("blue") 

class MTTAnalyzerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.config = load_config()
        cfg = self.config["ui_defaults"]
        fonts = self.config["fonts"]

        self.title(cfg["title"])
        self.geometry(cfg["geometry"])

        self.label = ctk.CTkLabel(self, text=cfg["label_text"], font=(fonts["font_family"], fonts["font_size"]))
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

        # 2. Extract grid settings once
        g = self.config["grid"]

        # 3. Create buttons in a loop
        for i, btn in enumerate(self.config["buttons_confic"]):

            color_key = btn["color_key"]
            actual_color = self.config["buttons"][color_key]
            
            rb = ctk.CTkRadioButton(
                self.mode_frame, 
                text=btn["text"], 
                variable=self.selection_mode, 
                value=btn["value"], 
                fg_color=actual_color
            )
    
            # Using 'i' for column index to position them side-by-side
            rb.grid(row=g["grid_row"], column=i, padx=g["grid_cell_xpadding"], pady=g["grid_cell_ypadding"])

        # ------------------------------------------

        self.create_plate_grid()

        self.conc_frame = ctk.CTkFrame(self)
        self.conc_frame.pack(pady=10)


        self.conc_label = ctk.CTkLabel(self.conc_frame, text=cfg["start_conc_text"], font=tuple(cfg["font_main"]))
        self.conc_label.grid(row=0, column=0, padx=5, pady=5)

        self.start_conc = ctk.CTkEntry(self.conc_frame, width=120)
        self.start_conc.insert(0, cfg["start_concentration"])
        self.start_conc.grid(row=0, column=1, padx=5, pady=5)

        self.sub_label = ctk.CTkLabel(self, text=cfg["heatmap_text"], font=tuple(cfg["font_main"]))
        self.sub_label.pack(pady=(15, 5))

        self.btn = ctk.CTkButton(self, 
                                text=self.config["buttons"]["button_file_text"], 
                                command=self.select_and_run,
                                font=("Arial", 12, "bold"),
                                height=45,
                                corner_radius=10)
        self.btn.pack(pady=15)

        self.progress = ctk.CTkProgressBar(self, width=300)
        self.progress.pack(pady=10)
        self.progress.set(0)

        self.info = ctk.CTkLabel(self, text=cfg["save_path_text"], font=("Arial", 10, "italic"))
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

        self.raw_json_button = ctk.CTkButton(self.export_frame,
                                           text="Rohdaten JSON speichern",
                                           command=self.save_raw_plate_json,
                                           font=("Arial", 12),
                                           height=35,
                                           corner_radius=8)
        self.raw_json_button.grid(row=0, column=3, padx=10)

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
                btn.configure(fg_color=self.config["buttons"]["button_puro"])

        elif current_mode == "blank":
            self.puro_wells.discard(name)
            self.dmso_wells.discard(name)
            
            if name in self.blank_wells:
                self.blank_wells.remove(name)
                btn.configure(fg_color=self.default_color)
            else:
                self.blank_wells.add(name)
                btn.configure(fg_color=self.config["buttons"]["button_blank"])

        elif current_mode == "dmso":
            self.puro_wells.discard(name)
            self.blank_wells.discard(name)
            
            if name in self.dmso_wells:
                self.dmso_wells.remove(name)
                btn.configure(fg_color=self.default_color)
            else:
                self.dmso_wells.add(name)
                btn.configure(fg_color=self.config["buttons"]["button_dmso"])
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
                "summary": summary,
                "raw_plate_data": summary.get("raw_plate_data"),
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

    def save_raw_plate_json(self):
        if not self.analysis_summary:
            messagebox.showwarning("Keine Analyse", "Bitte zuerst eine Analyse durchführen, damit die Rohdaten gespeichert werden können.")
            return

        output_folder = os.path.join(os.path.expanduser("~"), "Desktop", "MTT_Ergebnisse")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        base_name = self.template_data.get("active_file", "mtt_plate").split('.')[0] if self.template_data else "mtt_plate"
        json_path = os.path.join(output_folder, f"{base_name}_raw_plate_data.json")
        raw_plate_data = self.analysis_summary.get("raw_plate_data")
        if not raw_plate_data:
            messagebox.showwarning("Keine Rohdaten", "Für die aktuelle Analyse sind keine Rohdaten verfügbar.")
            return

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(raw_plate_data, f, indent=2, ensure_ascii=False)

        messagebox.showinfo("Rohdaten JSON gespeichert", f"Die Rohdaten wurden gespeichert: {json_path}")

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
        self.last_loaded_json_path = json_path
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

        messagebox.showinfo("JSON geladen", f"JSON-Vorlage erfolgreich geladen: {getattr(self, 'last_loaded_json_path', 'unbekannt')}")

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

        def pdf_table(headers, rows, widths, aligns=None, header_fill=(230, 230, 230)):
            if aligns is None:
                aligns = ['L'] * len(headers)
            pdf.set_font("Arial", "B", 11)
            pdf.set_fill_color(*header_fill)
            for header, width, align in zip(headers, widths, aligns):
                pdf.cell(width, 8, header, border=1, align=align, fill=True)
            pdf.ln()

            pdf.set_font("Arial", size=10)
            for row in rows:
                for datum, width, align in zip(row, widths, aligns):
                    pdf.cell(width, 7, str(datum), border=1, align=align)
                pdf.ln()

        add_stat_block("Puromycin", self.analysis_summary.get("puro"))
        add_stat_block("DMSO", self.analysis_summary.get("dmso"))

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Qualitätskontrolle", ln=True)
        pdf.set_font("Arial", size=11)
        z_prime = self.analysis_summary.get("z_prime")
        z_prime_valid = self.analysis_summary.get("z_prime_valid", False)
        if z_prime is not None:
            pdf.cell(0, 7, f"Z'-Prime: {z_prime:.3f} ({'gültig' if z_prime_valid else 'nicht gültig'})", ln=True)
        else:
            pdf.cell(0, 7, "Z'-Prime konnte nicht berechnet werden.", ln=True)
        signal_to_background = self.analysis_summary.get("signal_to_background")
        if signal_to_background is not None:
            pdf.cell(0, 7, f"Signal-to-Background: {signal_to_background:.3f}", ln=True)
        else:
            pdf.cell(0, 7, "Signal-to-Background konnte nicht berechnet werden.", ln=True)
        pdf.ln(2)

        dose_response = self.analysis_summary.get("dose_response")
        if dose_response:
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, "Dose Response (Puromycin)", ln=True)
            pdf.ln(1)

            headers = ["Konzentration (µM)", "Wells", "SD", "RSD (%)", "Viabilität (%)"]
            widths = [35, 55, 30, 30, 40]
            aligns = ['C', 'L', 'R', 'R', 'R']
            rows = []
            for group in dose_response:
                wells_text = ", ".join(group.get('wells', []))
                rows.append([
                    f"{group.get('concentration', 0):.3f}",
                    wells_text,
                    f"{group.get('std', 0.0):.3f}",
                    f"{group.get('rel_std', 0.0):.2f}",
                    f"{group.get('viability', 0.0):.2f}"
                ])

            pdf_table(headers, rows, widths, aligns)
            pdf.ln(2)

            try:
                import numpy as np
                
                # Datenstrukturen für das Plotten vorbereiten
                xs = []
                ys = []
                yerrs = []
                ref_val = self.analysis_summary.get("reference_value", 1.0) or 1.0
                
                for group in dose_response:
                    if group.get('viability') is not None:
                        xs.append(group['concentration'])
                        ys.append(group['viability'])
                        # Roh-Standardabweichung auf die Prozent-Skala der Viabilität normieren
                        yerrs.append((group['std'] / ref_val) * 100)
                
                if len(ys) >= 4:
                    # Professionelle Design-Richtlinien für wissenschaftliche Arbeiten anwenden
                    plt.rcParams['font.family'] = 'sans-serif'
                    plt.rcParams['font.sans-serif'] = ['Arial', 'Liberation Sans', 'DejaVu Sans']
                    plt.rcParams['axes.edgecolor'] = '#333333'
                    plt.rcParams['axes.linewidth'] = 1.2
                    
                    fig, ax = plt.subplots(figsize=(6.5, 4.5))
                    
                    # 1. Reale Messpunkte mit präzisen Fehlerbalken darstellen (ohne Zickzack-Linie)
                    ax.errorbar(xs, ys, yerr=yerrs, fmt='o', color='#1A365D', elinewidth=1.5, 
                                capsize=3, capthick=1.2, ms=6, label='Messdaten (Triplikate)')
                    
                    # 2. Mathematisch exakte Regressionskurve auf Basis der Fit-Ergebnisse berechnen
                    fit_summary = self.analysis_summary.get("dose_response_fit")
                    if fit_summary:
                        bottom = fit_summary.get("bottom")
                        top = fit_summary.get("top")
                        hill_slope = fit_summary.get("hill_slope")
                        log_ic50 = fit_summary.get("log_ic50")
                        
                        # Generierung einer hochauflösenden logarithmischen Achsenskalierung für die Kurve
                        x_smooth = np.logspace(np.log10(min(xs)), np.log10(max(xs)), 300)
                        # Spiegelt exakt die log10-basierte 4PL-Funktion aus dose_response.py
                        y_smooth = bottom + (top - bottom) / (1 + 10 ** ((np.log10(x_smooth) - log_ic50) * hill_slope))
                        
                        ax.plot(x_smooth, y_smooth, color='#E74C3C', lw=2, label='4PL-Regressionskurve')
                        
                        # Kennwerte sauber formatiert als Box in die Grafik einbetten
                        textstr = '\n'.join((
                            r'$IC_{10}: %.4g\ \mu\mathrm{M}$' % (fit_summary.get('ic10', 0),),
                            r'$IC_{50}: %.4g\ \mu\mathrm{M}$' % (fit_summary.get('ic50', 0),),
                            r'$IC_{90}: %.4g\ \mu\mathrm{M}$' % (fit_summary.get('ic90', 0),),
                            r'$\mathrm{Hill-Slope}: %.2f$' % (fit_summary.get('hill_slope', 0),)
                        ))
                        props = dict(boxstyle='round,pad=0.5', facecolor='#F8F9FA', edgecolor='#E2E8F0', alpha=0.9)
                        ax.text(0.05, 0.05, textstr, transform=ax.transAxes, fontsize=10, verticalalignment='bottom', bbox=props)
                    else:
                        # Fallback-Option falls die Regression fehlschlägt
                        ax.plot(xs, ys, color='#E74C3C', ls='--', alpha=0.4, label='Trendlinie (unvollständiger Fit)')
                    
                    # Achsen-Kosmetik für den echten GraphPad Prism-Look
                    ax.set_xscale('log')
                    ax.set_xlabel('Konzentration (µM)', fontsize=11, fontweight='bold', labelpad=8)
                    ax.set_ylabel('Zellviabilität (%)', fontsize=11, fontweight='bold', labelpad=8)
                    
                    # Äußeren Kasten aufbrechen (Top und Right Spines entfernen)
                    ax.spines['top'].set_visible(False)
                    ax.spines['right'].set_visible(False)
                    
                    # GraphPad Prism Charakteristika: 
                    ax.grid(False) # <--- Hier wird das gestrichelte Raster komplett abgeschaltet!
                    
                    # Ticks nach außen zeigen lassen und Achsenlinien stärken
                    ax.tick_params(direction='out', which='both', length=5, width=1.2, colors='#333333', labelsize=10)
                    ax.tick_params(which='minor', length=3) # Auch kleine Zwischen-Ticks für Log-Skala
                    
                    ax.legend(loc='upper right', frameon=False, fontsize=10)
                    
                    plot_path = os.path.join(output_folder, 'mttexport_ic50_plot.png')
                    fig.tight_layout()
                    fig.savefig(plot_path, dpi=300)  # Gestochen scharfe 300 DPI für den PDF-Druck
                    plt.close(fig)

                    try:
                        pdf.add_page()
                    except Exception:
                        pass
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 8, "Dose-Response Plot & IC-Kennwerte", ln=True)
                    pdf.ln(2)
                    pdf.image(plot_path, x=15, w=180)
                    pdf.ln(4)
                    pdf.set_font("Arial", size=12)
                    
                    if fit_summary:
                        pdf.cell(0, 7, f"IC10: {fit_summary.get('ic10'):.4g} µM", ln=True)
                        pdf.cell(0, 7, f"IC50: {fit_summary.get('ic50'):.4g} µM", ln=True)
                        pdf.cell(0, 7, f"IC90: {fit_summary.get('ic90'):.4g} µM", ln=True)
                        pdf.cell(0, 7, f"Hill-Slope: {fit_summary.get('hill_slope'):.3f}", ln=True)
                    else:
                        pdf.cell(0, 7, "IC10/IC50/IC90 konnte nicht durch ein 4-Parameter-Logistik-Modell geschätzt werden.", ln=True)
                    pdf.ln(4)
            except Exception as e:
                print(f"Fehler bei der Generierung des Publikationsplots: {e}")

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Berechnete Differenzen", ln=True)
        pdf.set_font("Arial", size=11)
        if self.analysis_summary.get("mean_difference_blank_corrected") is not None:
            pdf.cell(0, 7, f"Mittelwert DMSO - Mittelwert Puro (blank-korrigiert): {self.analysis_summary['mean_difference_blank_corrected']:.3f}", ln=True)
            pdf.cell(0, 7, f"Viabilitätsdifferenz: {self.analysis_summary['viability_difference']:.2f}%", ln=True)
        else:
            pdf.cell(0, 7, "Nicht genügend Daten für Differenzberechnung.", ln=True)

        auc_log10 = self.analysis_summary.get("auc_log10")
        if auc_log10 is not None:
            pdf.cell(0, 7, f"AUC (log10-skaliert): {auc_log10:.3f}", ln=True)
        else:
            pdf.cell(0, 7, "AUC konnte nicht berechnet werden.", ln=True)

        pdf.output(pdf_path)
        messagebox.showinfo("PDF gespeichert", f"Die PDF-Zusammenfassung wurde gespeichert: {pdf_path}")

if __name__ == "__main__":
    app = MTTAnalyzerApp()
    app.mainloop()
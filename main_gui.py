import sys
import tempfile
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json
from datetime import datetime
import customtkinter as ctk 
from tkinter import filedialog, messagebox

from analyzer import calculate_viability
from data_loader import load_data
import json
from fpdf import FPDF

class PdfWithFooter(FPDF):
    def __init__(self, generated_at, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generated_at = generated_at

    def footer(self):
        self.set_y(-12)
        self.set_font("Arial", "I", 8)
        footer_text = f"{self.generated_at.strftime('%d.%m.%Y %H:%M:%S')} | Seite {self.page_no()}/{{nb}}"
        self.cell(0, 10, footer_text, align='C')

def load_config(filename="config.json"):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)
    

ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
ctk.set_default_color_theme("dark-blue") 

class MTTAnalyzerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        #Extracting configuration settings from the config.json file
        self.config = load_config()
        cfg = self.config["ui_defaults"]
        fonts = self.config["fonts"]
        g = self.config["grid"]
        btns = self.config["buttons"]

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

        # 3. Create buttons in a loop
        for i, btn in enumerate(self.config["buttons_confic"]):

           # color_key = btn["color_key"]
           # actual_color = self.config["buttons"][color_key]
            
            rb = ctk.CTkRadioButton(
                self.mode_frame, 
                text=btn["text"], 
                variable=self.selection_mode, 
                value=btn["value"], 
                fg_color=btns["button_puro"]
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
                                text=btns["button_file_text"], 
                                command=self.select_and_run,
                                font=(btns["button_font_family"], btns["button_font_size"], btns["button_font_weight"]),
                                height=btns["button_height"],
                                corner_radius=btns["button_corner_radius"])
        self.btn.pack(pady=15)

        self.progress = ctk.CTkProgressBar(self, width=300)
        self.progress.pack(pady=10)
        self.progress.set(0)

        self.info = ctk.CTkLabel(self, text=cfg["save_path_text"], font=("Arial", 10, "italic"))
        self.info.pack(side="bottom", pady=15)

        self.export_frame = ctk.CTkFrame(self)
        self.export_frame.pack(pady=10)

        self.save_json_button = ctk.CTkButton(self.export_frame,
                                             text="JSON Vorlage speichern",
                                             command=self.save_template_json,
                                             font=("Arial", 12),
                                             height=35,
                                             corner_radius=btns["button_corner_radius"])
        self.save_json_button.grid(row=0, column=0, padx=5)

        self.load_json_button = ctk.CTkButton(self.export_frame,
                                           text="JSON Vorlage laden",
                                           command=self.load_template_json,
                                           font=("Arial", 12),
                                           height=35,
                                           corner_radius=btns["button_corner_radius"])
        self.load_json_button.grid(row=0, column=1, padx=5)

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

    def build_output_folder(self):
        output_folder = os.path.join(os.path.expanduser("~"), "Desktop", "MTT_Ergebnisse")
        os.makedirs(output_folder, exist_ok=True)
        return output_folder

    def build_template_payload(self):
        return {
            "puro": sorted(list(self.puro_wells)),
            "blank": sorted(list(self.blank_wells)),
            "dmso": sorted(list(self.dmso_wells)),
            "start_triplet": list(self.start_triplet),
            "start_concentration": self.start_conc.get(),
        }

    def select_and_run(self):
        ausgewaehlte_dateien = filedialog.askopenfilenames(
            title="Wähle die Textdateien aus",
            filetypes=[("Softmax Pro Dateien", "*.txt *.tsv *.asc *.csv"), ("Alle Dateien", "*.*")]
        )
        if ausgewaehlte_dateien:
            self.run_full_analysis_flexible(ausgewaehlte_dateien)

    def run_full_analysis_flexible(self, dateiliste):
        output_folder = self.build_output_folder()

        anzahl = len(dateiliste)
        erfolgreich_verarbeitet = 0
        
        for i, pfad in enumerate(dateiliste):
            self.progress.set((i + 1) / anzahl)
            self.update_idletasks()

            df = load_data(pfad)
            if df is None:
                continue
            
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
            self.template_data = self.build_template_payload()
            self.template_data["active_file"] = os.path.basename(pfad)
            self.last_analysis_file_name = os.path.basename(pfad).split('.')[0]
            basis_name = self.last_analysis_file_name

            self.save_raw_plate_json(summary=summary, base_name=basis_name, output_folder=output_folder)
            self.save_pdf_summary(
                summary=summary,
                base_name=basis_name,
                output_folder=output_folder,
                heatmap_matrix=res,
                status_msg=status_msg,
            )
            erfolgreich_verarbeitet += 1

        messagebox.showinfo("Erfolg", f"Analyse fertig!\n{erfolgreich_verarbeitet} PDFs wurden erstellt.")
        self.progress.set(0)

    def save_template_json(self):
        payload = self.build_template_payload()
        output_folder = self.build_output_folder()

        json_path = os.path.join(output_folder, "mttexport_template.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        messagebox.showinfo("JSON gespeichert", f"Die JSON-Vorlage wurde gespeichert: {json_path}")

    def save_raw_plate_json(self, summary=None, base_name=None, output_folder=None):
        summary = summary or self.analysis_summary
        if not summary:
            messagebox.showwarning("Keine Analyse", "Bitte zuerst eine Analyse durchführen, damit die Rohdaten gespeichert werden können.")
            return None

        output_folder = output_folder or self.build_output_folder()
        base_name = base_name or self.last_analysis_file_name or "mtt_plate"
        json_path = os.path.join(output_folder, f"{base_name}_raw_plate_data.json")
        raw_plate_data = summary.get("raw_plate_data")
        if not raw_plate_data:
            messagebox.showwarning("Keine Rohdaten", "Für die aktuelle Analyse sind keine Rohdaten verfügbar.")
            return None

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(raw_plate_data, f, indent=2, ensure_ascii=False)

        return json_path

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

### Output PDF Summary Generation

    def save_pdf_summary(self, summary=None, base_name=None, output_folder=None, heatmap_matrix=None, status_msg=None):
        summary = summary or self.analysis_summary
        if not summary:
            messagebox.showwarning("Keine Analyse", "Bitte zuerst eine Analyse durchführen.")
            return None

        output_folder = output_folder or os.path.join(os.path.expanduser("~"), "Desktop", "MTT_Ergebnisse")
        os.makedirs(output_folder, exist_ok=True)
        pdf_path = os.path.join(output_folder, f"{base_name or self.last_analysis_file_name or 'mtt_plate'}_summary.pdf")

        generated_at = datetime.now()
        pdf = PdfWithFooter(generated_at)
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"MTT Analyse Zusammenfassung - {base_name or self.last_analysis_file_name or 'mtt_plate'}", ln=True)
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
            pdf.cell(0, 7, f"Minimaler Effekt: {stats['e_min']:.3f}", ln=True)
            pdf.cell(0, 7, f"Maximaler Effekt: {stats['e_max']:.3f}", ln=True)
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

            fit_summary = summary.get("dose_response_fit")
            if fit_summary:
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 8, "Fit-Metriken", ln=True)
                pdf.set_font("Arial", size=11)
                pdf.cell(0, 7, f"E_min (curve): {fit_summary.get('e_min', 0.0):.3f}", ln=True)
                pdf.cell(0, 7, f"E_max (curve): {fit_summary.get('e_max', 0.0):.3f}", ln=True)
                pdf.cell(0, 7, f"Absolute IC50: {fit_summary.get('ic50_absolute', 0.0):.4g} µM", ln=True)
                pdf.cell(0, 7, f"Relative IC50: {fit_summary.get('ic50_relative', 0.0):.4g} µM", ln=True)
                if fit_summary.get('ic10') is not None:
                    pdf.cell(0, 7, f"IC10: {fit_summary.get('ic10'):.4g} µM", ln=True)
                if fit_summary.get('ic90') is not None:
                    pdf.cell(0, 7, f"IC90: {fit_summary.get('ic90'):.4g} µM", ln=True)
                pdf.ln(2)

        raw_plate_data = summary.get("raw_plate_data") or {}
        if raw_plate_data:
            pdf.add_page()
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, "Rohdaten der Platte", ln=True)
            pdf.set_font("Arial", size=7)
            column_headers = ["Row\\Col"] + [str(col) for col in range(1, 13)]
            widths = [14] + [10] * 12
            for header, width in zip(column_headers, widths):
                pdf.cell(width, 6, header, border=1, align="C", fill=True)
            pdf.ln()
            for row in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
                pdf.cell(widths[0], 6, row, border=1, align="C")
                row_values = raw_plate_data.get(row, {})
                for col in range(1, 13):
                    value = row_values.get(str(col), row_values.get(col, ""))
                    if isinstance(value, (int, float)):
                        text = f"{value:.4f}"
                    else:
                        text = str(value)
                    pdf.cell(widths[col], 6, text, border=1, align="C")
                pdf.ln()
            pdf.ln(2)

        fit_summary = summary.get("dose_response_fit")
        if dose_response and fit_summary:
            try:
                import numpy as np

                xs = [group.get("concentration") for group in dose_response if group.get("viability") is not None]
                ys = [group.get("viability") for group in dose_response if group.get("viability") is not None]
                yerrs = []
                ref_val = summary.get("reference_value", 1.0) or 1.0
                for group in dose_response:
                    if group.get("viability") is not None:
                        yerrs.append((group.get("std", 0.0) / ref_val) * 100)

                if len(xs) >= 4:
                    plt.rcParams['font.family'] = 'sans-serif'
                    plt.rcParams['font.sans-serif'] = ['Arial', 'Liberation Sans', 'DejaVu Sans']
                    fig, ax = plt.subplots(figsize=(6.8, 4.5))
                    ax.errorbar(xs, ys, yerr=yerrs, fmt='o', color='#1A365D', elinewidth=1.4, capsize=3, capthick=1.2, ms=6, label='Messdaten')

                    bottom = fit_summary.get("bottom")
                    top = fit_summary.get("top")
                    hill_slope = fit_summary.get("hill_slope")
                    log_ic50 = fit_summary.get("log_ic50")
                    x_smooth = np.logspace(np.log10(min(xs)), np.log10(max(xs)), 300)
                    y_smooth = bottom + (top - bottom) / (1 + 10 ** ((np.log10(x_smooth) - log_ic50) * hill_slope))
                    ax.plot(x_smooth, y_smooth, color='#E74C3C', lw=2, label='4PL-Fit')

                    ax.set_xscale('log')
                    ax.set_xlabel('Konzentration (µM)')
                    ax.set_ylabel('Zellviabilität (%)')
                    ax.set_title('Dose-Response / 4-Parameter-Logistic Fit')
                    ax.spines['top'].set_visible(False)
                    ax.spines['right'].set_visible(False)
                    ax.grid(False)
                    ax.legend(loc='best')
                    textstr = '\n'.join([
                        f"IC10: {fit_summary.get('ic10'):.4g} µM",
                        f"IC50: {fit_summary.get('ic50'):.4g} µM",
                        f"IC90: {fit_summary.get('ic90'):.4g} µM",
                        f"Hill-Slope: {fit_summary.get('hill_slope'):.3f}",
                    ])
                    props = dict(boxstyle='round,pad=0.35', facecolor='#F8F9FA', edgecolor='#D0D7DE', alpha=0.95)
                    ax.text(0.05, 0.05, textstr, transform=ax.transAxes, fontsize=9, verticalalignment='bottom', bbox=props)

                    fig.tight_layout()
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        plot_path = tmp.name
                    fig.savefig(plot_path, dpi=300)
                    plt.close(fig)

                    pdf.add_page()
                    pdf.set_font("Arial", "B", 12)
                    pdf.cell(0, 8, "Graphical Abstract", ln=True)
                    pdf.image(plot_path, x=12, y=20, w=186)
                    os.remove(plot_path)
            except Exception as exc:
                print(f"Fehler bei der Graphik-Erzeugung: {exc}")

        if heatmap_matrix is not None:
            try:
                import numpy as np

                plt.rcParams['font.family'] = 'sans-serif'
                plt.rcParams['font.sans-serif'] = ['Arial', 'Liberation Sans', 'DejaVu Sans']
                fig, ax = plt.subplots(figsize=(7.2, 5.2))
                sns.heatmap(
                    np.array(heatmap_matrix, dtype=float),
                    ax=ax,
                    cmap='viridis',
                    cbar=True,
                    cbar_kws={'label': 'Zellviabilität (%)'},
                    annot=True,
                    fmt='.2f',
                    annot_kws={'size': 7},
                    xticklabels=[str(i) for i in range(1, 13)],
                    yticklabels=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
                )
                ax.set_title('Heatmap der Zellviabilität')
                ax.set_xlabel('Spalte (1-12)')
                ax.set_ylabel('Zeile (A-H)')
                fig.tight_layout()
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    plot_path = tmp.name
                fig.savefig(plot_path, dpi=300)
                plt.close(fig)

                pdf.add_page()
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 8, "Heatmap der Zellviabilität", ln=True)
                pdf.image(plot_path, x=15, y=24, w=180)
                os.remove(plot_path)
            except Exception as exc:
                print(f"Fehler bei der Heatmap-Erzeugung: {exc}")

        pdf.output(pdf_path)
        return pdf_path

if __name__ == "__main__":
    app = MTTAnalyzerApp()
    app.mainloop()
import sys
import tempfile
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json
from datetime import datetime
import customtkinter as ctk 
from tkinter import filedialog, messagebox
from pdf_summary import generate_pdf_summary

from analyzer import calculate_viability
from data_loader import load_data
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
        self.error_msg = self.config["messages"]

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

        self.use_puro_baseline = ctk.BooleanVar(value=False)
        self.puro_baseline_checkbox = ctk.CTkCheckBox(
            self.conc_frame,
            text="Puromycin-basierte Zellviabilität",
            variable=self.use_puro_baseline,
            onvalue=True,
            offvalue=False,
            font=("Arial", 10)
        )
        self.puro_baseline_checkbox.grid(row=1, column=0, columnspan=2, padx=5, pady=(5, 0), sticky="w")

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
                                             text=cfg["save_json_text"],
                                             command=self.save_template_json,
                                             font=("Arial", 12),
                                             height=35,
                                             corner_radius=btns["button_corner_radius"])
        self.save_json_button.grid(row=0, column=0, padx=5)

        self.load_json_button = ctk.CTkButton(self.export_frame,
                                           text=cfg["load_json_text"],
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
                    messagebox.showinfo("Fehler", self.error_msg["error_number_triplet"])
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
            "use_puro_baseline": self.use_puro_baseline.get(),
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

            # 1. Daten sicher einlesen
            df = load_data(pfad)
            if df is None:
                continue
            
            # 2. Analyse durchführen
            analysis_result = calculate_viability(
                df,
                self.puro_wells,
                dmso_wells=self.dmso_wells,
                blank_wells=self.blank_wells,
                start_concentration=self.start_conc.get(),
                start_triplet=self.start_triplet,
                include_summary=True,
                use_puro_baseline=self.use_puro_baseline.get()
            )

            # 3. Rückgabewerte sicher aufteilen (ob 2 oder 3 Werte)
            if isinstance(analysis_result, tuple) and len(analysis_result) == 3:
                res, status_msg, summary = analysis_result
            elif isinstance(analysis_result, tuple) and len(analysis_result) == 2:
                res, status_msg = analysis_result
                summary = None
            else:
                res = analysis_result
                status_msg = "Analyse abgeschlossen"
                summary = None

            self.analysis_summary = summary
            self.template_data = self.build_template_payload()
            self.template_data["active_file"] = os.path.basename(pfad)
            self.last_analysis_file_name = os.path.basename(pfad).split('.')[0]
            basis_name = self.last_analysis_file_name

            # 4. JSON-Rohdaten und PDF-Report erzeugen
            if summary:
                self.save_raw_plate_json(summary=summary, base_name=basis_name, output_folder=output_folder)
                generate_pdf_summary(
                    summary=summary,
                    base_name=basis_name,
                    output_folder=output_folder,
                    heatmap_matrix=res,
                    status_msg=status_msg,
                    operator_info="Labor / Standard"
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
        self.use_puro_baseline.set(bool(data.get("use_puro_baseline", False)))
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

if __name__ == "__main__":
    app = MTTAnalyzerApp()
    app.mainloop()
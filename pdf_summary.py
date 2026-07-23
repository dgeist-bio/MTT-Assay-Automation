import os
import tempfile
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import json
import numpy as np
from fpdf import FPDF

class PdfWithFooter(FPDF):
    def __init__(self, generated_at, script_version="v1.7.0", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generated_at = generated_at
        self.script_version = script_version

    def footer(self):
        self.set_y(-12)
        self.set_font("Arial", "I", 8)
        self.set_text_color(120, 120, 120)
        footer_text = f"MTT Auto-Analyzer {self.script_version}  |  Seite {self.page_no()}/{{nb}}"
        self.cell(0, 10, footer_text, align='C')


def load_config(filename="config.json"):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_pdf_summary(summary, base_name, output_folder, heatmap_matrix=None, status_msg=None, operator_info=None):
    if not summary:
        return None

    os.makedirs(output_folder, exist_ok=True)
    pdf_path = os.path.join(output_folder, f"{base_name}_summary.pdf")

    json_config = load_config()
    messages = json_config.get("messages", {})
    cfg = json_config.get("ui_defaults", {})

    # Version aus Titel extrahieren oder Standard
    app_title = cfg.get("title", "v1.7.0")
    script_version = "v1.7.0"
    for part in app_title.split():
        if part.startswith("v") and "." in part:
            script_version = part
            break

    generated_at = datetime.now()
    pdf = PdfWithFooter(generated_at, script_version=script_version)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- TITEL & HEADER ---
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(26, 54, 93)  # Dunkles Corporate-Blau
    pdf.cell(0, 10, messages["title_message"], align='C', ln=True)
    pdf.ln(1)

    # --- METADATEN-BOX (Sauberes 2-Spalten-Layout ohne Überlappungen) ---
    box_y = 22
    box_h = 30
    total_width = 190
    col_width = (total_width - 4) / 2
    left_x = 10
    right_x = left_x + col_width + 4

    fill_bg = (245, 247, 250)
    border_col = (208, 215, 222)

    pdf.set_fill_color(*fill_bg)
    pdf.set_draw_color(*border_col)

    # 1. Linke Box (Unterschriften / GMP Rollen)
    pdf.rect(left_x, box_y, col_width, box_h, style='DF')
    pdf.set_font("Arial", "B", 9)
    pdf.set_text_color(80, 80, 80)
    
    pdf.set_xy(left_x + 3, box_y + 6)
    pdf.cell(col_width - 6, 5, "Bearbeiter: ________________ (Visum)", ln=1)
    
    pdf.set_xy(left_x + 3, box_y + 18)
    pdf.set_font("Arial", "", 9)
    pdf.cell(col_width - 6, 5, "Reviewer: ___________________ (Visum)", ln=1)

    # 2. Rechte Box (Metadaten & Gerät - feste, saubere Y-Abstände)
    pdf.rect(right_x, box_y, col_width, box_h, style='DF')
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(60, 60, 60)

    pdf.set_xy(right_x + 3, box_y + 3)
    pdf.cell(col_width - 6, 4, f"Datei: {base_name}", ln=0)

    pdf.set_font("Arial", "", 8)
    pdf.set_xy(right_x + 3, box_y + 8)
    pdf.cell(col_width - 6, 4, f"Datum: {generated_at.strftime('%d.%m.%Y %H:%M')}", ln=0)

    pdf.set_xy(right_x + 3, box_y + 13)
    pdf.cell(col_width - 6, 4, "Geräte-ID: Molecular Devices (Plate#1)", ln=0)

    pdf.set_xy(right_x + 3, box_y + 18)
    pdf.cell(col_width - 6, 4, "Zelllinie: ___________________", ln=0)

    pdf.set_xy(right_x + 3, box_y + 23)
    pdf.cell(col_width - 6, 4, "Target: _____________________", ln=0)

    pdf.set_text_color(0, 0, 0)
    pdf.set_y(box_y + box_h + 8)

    # --- 3 KPI-KACHELN ---
    card_y = 58
    card_h = 28
    card_w = 60
    spacing = 5
    start_x = 10

    z_prime = summary.get("z_prime")
    z_valid = summary.get("z_prime_valid", False)
    fit_summary = summary.get("dose_response_fit") or {}
    ic50_val = fit_summary.get("ic50_relative", fit_summary.get("ic50_absolute", 0.0))
    s2b = summary.get("signal_to_background", 0.0)

    # Kachel 1: Z'-Prime
    box_color = (212, 237, 218) if z_valid else (248, 215, 218)
    border_color = (40, 167, 69) if z_valid else (220, 53, 69)
    pdf.set_fill_color(*box_color)
    pdf.set_draw_color(*border_color)
    pdf.rect(start_x, card_y, card_w, card_h, style='DF')
    
    pdf.set_xy(start_x + 2, card_y + 3)
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(card_w - 4, 5, "Z'-PRIME (QUALITÄT)", align="C", ln=1)
    pdf.set_xy(start_x + 2, card_y + 11)
    pdf.set_font("Arial", "B", 14)
    z_text = f"{z_prime:.3f}" if z_prime is not None else "N/A"
    pdf.cell(card_w - 4, 8, z_text, align="C", ln=1)
    pdf.set_xy(start_x + 2, card_y + 20)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(card_w - 4, 4, "Gültig (SST OK)" if z_valid else "Ungültig", align="C", ln=1)

    # Kachel 2: IC50
    x2 = start_x + card_w + spacing
    pdf.set_fill_color(240, 244, 248)
    pdf.set_draw_color(180, 200, 220)
    pdf.rect(x2, card_y, card_w, card_h, style='DF')

    pdf.set_xy(x2 + 2, card_y + 3)
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(card_w - 4, 5, "IC50 (POTENZ)", align="C", ln=1)
    pdf.set_xy(x2 + 2, card_y + 11)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(card_w - 4, 8, f"{ic50_val:.4g} µM", align="C", ln=1)
    pdf.set_xy(x2 + 2, card_y + 20)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(card_w - 4, 4, "4PL-Fit Modell", align="C", ln=1)

    # Kachel 3: Signal-to-Background
    x3 = x2 + card_w + spacing
    pdf.set_fill_color(240, 244, 248)
    pdf.set_draw_color(180, 200, 220)
    pdf.rect(x3, card_y, card_w, card_h, style='DF')

    pdf.set_xy(x3 + 2, card_y + 3)
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(card_w - 4, 5, "SIGNAL-TO-BACKGR.", align="C", ln=1)
    pdf.set_xy(x3 + 2, card_y + 11)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(card_w - 4, 8, f"{s2b:.1f}x", align="C", ln=1)
    pdf.set_xy(x3 + 2, card_y + 20)
    pdf.set_font("Arial", "I", 8)
    pdf.cell(card_w - 4, 4, "Dynamikbereich", align="C", ln=1)

    pdf.set_text_color(0, 0, 0)
    pdf.set_y(card_y + card_h + 10)

    # --- SAUBERE KONTROLL-STATISTIKEN ---
    def add_clean_stat_block(name, stats):
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(26, 54, 93)
        pdf.cell(0, 6, f"Kontrolle / Referenz: {name}", ln=True)
        
        pdf.set_font("Arial", size=9)
        pdf.set_text_color(70, 70, 70)
        if not stats:
            pdf.cell(0, 5, "   Keine Daten verfügbar.", ln=True)
            pdf.ln(2)
            return
        
        pdf.cell(0, 5, f"   - Anzahl Wells: {stats['count']}   |   Mittelwert (OD): {stats['mean']:.4f}   |   Standardabweichung (SD): {stats['std']:.4f}", ln=True)
        pdf.cell(0, 5, f"   - Relative Standardabweichung (RSD): {stats['rel_std']:.2f}%   |   Relative Viabilität: {stats.get('viability', 0):.2f}%", ln=True)
        pdf.ln(3)

    add_clean_stat_block("Puromycin (Positivkontrolle / Maximale Inhibition)", summary.get("puro"))
    add_clean_stat_block("DMSO (Negativkontrolle / 100% Viabilität)", summary.get("dmso"))
    pdf.ln(2)

    if summary.get("use_puro_baseline"):
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(26, 54, 93)
        pdf.cell(0, 6, "Berechnung: DMSO-Mittelwert minus Puromycin-Mittelwert", ln=True)
        pdf.set_font("Arial", size=9)
        pdf.set_text_color(70, 70, 70)
        pdf.cell(0, 5, "   Die Zellviabilität wird auf Basis der Differenz zwischen DMSO- und Puromycin-Werten berechnet.", ln=True)
        pdf.ln(3)

    if fit_summary:
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(26, 54, 93)
        pdf.cell(0, 6, "Dose-Response Fit Metriken (4PL-Modell)", ln=True)
        pdf.set_font("Arial", size=9)
        pdf.set_text_color(70, 70, 70)
        pdf.cell(0, 5, f"   - Absolute IC50: {fit_summary.get('ic50_absolute', 0.0):.4g} µM   |   Relative IC50: {fit_summary.get('ic50_relative', 0.0):.4g} µM", ln=True)
        pdf.cell(0, 5, f"   - IC10: {fit_summary.get('ic10', 0):.4g} µM   |   IC90: {fit_summary.get('ic90', 0):.4g} µM   |   Hill-Slope: {fit_summary.get('hill_slope', 0):.3f}", ln=True)
        pdf.ln(3)

    # --- DOSIS-WIRKUNGS-TABELLE ---
    dose_response = summary.get("dose_response")
    if dose_response:
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(26, 54, 93)
        pdf.cell(0, 6, "Dose-Response Übersicht", ln=True)
        pdf.ln(1)
        
        headers = ["Konzentration (µM)", "Wells", "Mittelwert", "SD", "RSD (%)", "Viabilität (%)"]
        widths = [36, 42, 35, 25, 30, 30]
        aligns = ['R', 'L', 'R', 'R', 'R', 'R']
        
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(230, 238, 248)
        pdf.set_text_color(26, 54, 93)
        pdf.set_draw_color(180, 190, 200)
        for h, w, a in zip(headers, widths, aligns):
            pdf.cell(w, 6, h, border=1, align=a, fill=True)
        pdf.ln()

        pdf.set_font("Arial", size=9)
        pdf.set_text_color(50, 50, 50)
        for idx, group in enumerate(dose_response):
            is_even = (idx % 2 == 0)
            pdf.set_fill_color(255, 255, 255) if is_even else pdf.set_fill_color(248, 250, 252)
            
            wells_text = ", ".join(group.get('wells', []))
            mean_display = group.get('baseline_corrected_mean') if group.get('baseline_corrected_mean') is not None else group.get('blank_corrected_mean', 0.0)
            row_data = [
                f"{group.get('concentration', 0):.4f}",
                wells_text,
                f"{mean_display:.4f}",
                f"{group.get('std', 0.0):.4f}",
                f"{group.get('rel_std', 0.0):.2f}",
                f"{group.get('viability', 0.0):.2f}"
            ]
            for val, w, a in zip(row_data, widths, aligns):
                pdf.cell(w, 5.5, str(val), border=1, align=a, fill=True)
            pdf.ln()
        pdf.ln(6)

    # --- ROHDATEN TABELLE ---
    raw_plate_data = summary.get("raw_plate_data") or {}
    if raw_plate_data:
        pdf.add_page()
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(26, 54, 93)
        pdf.cell(0, 8, "Rohdaten der Platte (Optische Dichte / Absorbance)", ln=True)
        pdf.ln(1)
        
        pdf.set_font("Arial", "B", 8)
        column_headers = ["Reihe\\Spalte"] + [str(col) for col in range(1, 13)]
        raw_widths = [18] + [14] * 12
        
        pdf.set_fill_color(230, 238, 248)
        pdf.set_text_color(26, 54, 93)
        for header, width in zip(column_headers, raw_widths):
            pdf.cell(width, 6, header, border=1, align="C", fill=True)
        pdf.ln()
        
        pdf.set_font("Arial", size=8)
        pdf.set_text_color(60, 60, 60)
        for row_idx, row in enumerate(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']):
            is_even = (row_idx % 2 == 0)
            pdf.set_fill_color(255, 255, 255) if is_even else pdf.set_fill_color(248, 250, 252)
            
            pdf.cell(18, 5.5, row, border=1, align="C", fill=True)
            row_values = raw_plate_data.get(row, {})
            for col in range(1, 13):
                val = row_values.get(str(col), row_values.get(col, ""))
                text = f"{val:.4f}" if isinstance(val, (int, float)) else str(val)
                pdf.cell(14, 5.5, text, border=1, align="C", fill=True)
            pdf.ln()
        pdf.ln(6)

    # --- ANALYTISCHES DASHBOARD ---
    if (dose_response and fit_summary) or heatmap_matrix is not None:
        try:
            plt.rcParams['font.family'] = 'sans-serif'
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.0, 8.2), gridspec_kw={'height_ratios': [1, 1.1]})
            
            if dose_response and fit_summary:
                xs = [g.get("concentration") for g in dose_response if g.get("viability") is not None]
                ys = [g.get("viability") for g in dose_response if g.get("viability") is not None]
                yerrs = []
                ref_val = summary.get("reference_value", 1.0) or 1.0
                for g in dose_response:
                    if g.get("viability") is not None:
                        yerrs.append((g.get("std", 0.0) / ref_val) * 100)

                if len(xs) >= 4:
                    ax1.errorbar(xs, ys, yerr=yerrs, fmt='o', color='#1A365D', elinewidth=1.4, capsize=3, ms=5, label='Messdaten')

                    bottom = fit_summary.get("bottom", 0)
                    top = fit_summary.get("top", 100)
                    hill_slope = fit_summary.get("hill_slope", 1)
                    log_ic50 = fit_summary.get("log_ic50", 0)
                    x_smooth = np.logspace(np.log10(min(xs)), np.log10(max(xs)), 300)
                    y_smooth = bottom + (top - bottom) / (1 + 10 ** ((np.log10(x_smooth) - log_ic50) * hill_slope))
                    
                    ax1.plot(x_smooth, y_smooth, color='#E74C3C', lw=2, label='4PL-Fit')
                    ax1.set_xscale('log')
                    ax1.set_xlabel('Konzentration (µM)', fontsize=8)
                    ax1.set_ylabel('Zellviabilität (%)', fontsize=8)
                    ax1.set_title('Dose-Response / 4-Parameter-Logistic Fit', fontsize=9, fontweight='bold', color='#1A365D')
                    ax1.spines['top'].set_visible(False)
                    ax1.spines['right'].set_visible(False)
                    ax1.grid(True, linestyle="--", alpha=0.4)
                    ax1.legend(loc='best', fontsize=7)

            if heatmap_matrix is not None:
                clean_matrix = np.clip(np.array(heatmap_matrix, dtype=float), 0.0, None)
                sns.heatmap(
                    clean_matrix,
                    ax=ax2,
                    cmap='viridis',
                    cbar=True,
                    cbar_kws={'label': 'Zellviabilität (%)'},
                    annot=True,
                    fmt='.2f',
                    annot_kws={'size': 6},
                    xticklabels=[str(i) for i in range(1, 13)],
                    yticklabels=['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
                )
                ax2.set_title('Heatmap der Zellviabilität (Plate Layout)', fontsize=9, fontweight='bold', color='#1A365D')
                ax2.set_xlabel('Spalte (1-12)', fontsize=8)
                ax2.set_ylabel('Reihe (A-H)', fontsize=8)

            fig.tight_layout()
            
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                plot_path = tmp.name
            fig.savefig(plot_path, dpi=300)
            plt.close(fig)

            pdf.add_page()
            pdf.set_font("Arial", "B", 11)
            pdf.set_text_color(26, 54, 93)
            pdf.cell(0, 8, "Analytisches Dashboard (Dose-Response & Rohdaten-Heatmap)", ln=True)
            pdf.image(plot_path, x=15, y=22, w=180)
            os.remove(plot_path)
            
        except Exception as exc:
            print(f"Fehler bei Dashboard-Erzeugung: {exc}")

    pdf.output(pdf_path)
    return pdf_path
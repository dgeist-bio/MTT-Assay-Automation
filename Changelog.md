### Date 2026-07-23 - v1.7.0 ###

- Added a checkbox for puromycin-based cell viability. The checkbox changes the calculation of the cell viability: Substracting the mean puro values from the values of the wells of DMSO (=living cells). It then calculates the cellviability of the mean values of the triplicates to a puromycin-based viability, where the value of the living cells is substracted from the triplicates.
- Added mean values of the wells in the pdf executive summary
- Added an explanation when puromycin baseline correction is active
- Changed the layout of the generated pdf executive summary

Updated files:

- main_gui.py
- pdf_summary.py
- analyzer.py
- config.json
- Changelog.md

The main_gui was splitted to main_gui.py and pdf_summary.py for the output of the generated pdf file. The file analyzer.py computes the calculation of DMSO minus Puromycin baseline when checkbox is enabled, as well calculating the dose-response group means and viabilities from corrected values.
The file pdf_summary.py displays an explanation when puromycin baseline correction is active and shows corrected mean values in the dose-response overview table.


### Date: 13.07.2026 - v1.6.0 ###

- Added IC50 absolute & relative, as well E_min and E_max to the 4PL fit output.
- Added Date & Time, as well page count in the PDF footer.
- Added a fit metrics block to the PDF containing E_min, E_max, absolute IC50, relative IC50, and IC10/IC90.


Updated files:

- dose_response.py
- analyzer.py
- main_gui.py

### Date: 12.07.2026 v1.5.0 ###

- Changed the output from a PNG file to a complete PDF summary per file with the embedded heatmap.
- Removed the separate manual "PDF Summary speichern" and "Rohdaten JSON speichern" buttons, since in the workflow it is no longer needed, because those files are produced during analysis.
- Gives the minimal and maximal Values. Needs to be changed for E_min and E_max
- "JSON Export speichern" now writes only the selected well layout and start concentration, so it can be reloaded with "JSON Vorlage laden".
- Further re-factoring of the values to config.json

Updated files:
- main_gui.py
- analyzer.py
- test-dose-response
- config.json
- Changelog.md

### Date: 08.07.2026 v1.4.1 ###

- Bugfix: JSON self.config changed in main.gui

### Date: 05.07.2026 v1.4.0 ###

- Added calculations for IC10, IC50, IC90 and Area under curve (AUC) in the generated PDF summary
- Cell Viabilty values are written in the generated PDF summary
- Quality Control: Z'-Prime from DMSO vs. Puromycin is calculated, where values ≥ 0.5 are treated as valid.
- Signal-to-backround (S/B) based on DMSO mean vs. blank mean
- A 4-parameter logistic fit for the dose-response curve, including the Hill slope in the PDF
- Export of raw data in JSON (for Blender): Full raw OD values for every well in the exported JSON payload
- Area under the curve (AUC) on a log10-scaled concentration.
- A new button in the GUI: JSON export for raw data added, which saves a separate JSON file named like [example]_raw_plate_data.json (contains full raw OD values for every well from the processed plate).
- Added a formatted dose-response table to the exported PDF, where save_pdf_summary() now renders a table with columns, like Konzentration (µM), Wells, SD, RSD (%), Viablität (%). The table uses a header row with fill color and bordered cells for better readability.

### Changes in the Python files v1.3.0 ###
- Added the new fitting logic in dose_response.py
- Estended the analysis summary in analyzer.py
- Updated the PDF export in main_gui.py
- Added AUC calculation in anaylzer.py
- Added raw plate export logic in analyzer.py
- Included the AUC in the PDF summary and attached the raw plate data to the JSON export in main_gui.py
- A dedictated export button in main_gui.py
- A handler that writes the raw plate values to a standalone JSON file
- Updating main_gui.py to save the loaded JSON path as self.last_loaded_json_path
- Updated the success message to use that stored value instead of the undefined local variable
- Added a regression test in test_dose_response.py

- analyzer.py
    - Added describe_well_set() for mean, std, relative std, and blank-corrected mean.
    - Extended calculate_viability() to return:
        - Puromycin summary
        - DMSO summary
        - calculated DMSO–Puromycin mean difference
        - viability difference
- main_gui.py
    - Added buttons for:
        - JSON Export speichern
        - PDF Summary speichern
        - JSON Vorlage laden
    - Added JSON export/load support for Puromycin, DMSO, control templates
    - Added PDF summary export with:
        - mean
        - std
        - relative std
        - blank-corrected mean
        - DMSO–Puromycin difference
- requirements.txt
    - Added fpdf

- main_gui.py
    - Removed control/medium selection
    - Added Blank selection mode
    - Added start concentration input
    - Updated analysis call to pass:
        - blank_wells
        - dmso_wells
        - start_concentration
    - Updated JSON export template with:
        - blank
        - start_concentration
    - PDF now includes Puromycin dose-response triplicate summaries
- analyzer.py
    - Added blank-specific selection
    - Added dose-response grouping from start concentration
    - Added per-triplicate mean/std/RSD output

### Export behaviour in JSON v1.2.0 ###

The JSON export now contains:
- the selected well annotations
- the full analysis summary
- the raw OD values for all wells under the key raw_plate_daata

### **Results** v1.1.0###

- GUI now supports only:
    - Puromycin
    - Blank
    - DMSO
    - Start-Triplet
- Start concentration is read from the GUI and used to compute half-dilution triplicates
- The PDF summary includes dose-response statistics for the Puromycin groups
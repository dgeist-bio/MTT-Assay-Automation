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

## **What changed**

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

## **Result**

- GUI now supports only:
    - Puromycin
    - Blank
    - DMSO
- Start concentration is read from the GUI and used to compute half-dilution triplicates
- The PDF summary includes dose-response statistics for the Puromycin groups
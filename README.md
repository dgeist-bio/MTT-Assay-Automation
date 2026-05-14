# MTT-Assay-Automation

This tool **automates** the analysis of MTT assays exported from **Molecular Devices SpectraMax 250** readers (SoftMax Pro 3.0).

## How to Use
1. Run the `main_gui.py` script.
2. Select your raw data files (`.txt`).
3. The analyzed results will be automatically saved to a folder on your **Desktop**.

## Highlights
- **Automated Visualization:** Transforms messy raw data into clear, publication-ready heatmaps.
- **Quality Control:** Integrated validation of the Puromycin control (triggers a warning if cell viability is >30%).
- **Consistent Scaling:** Implemented fixed color scaling (0-120%) for reliable comparison between different plates.

## Future Roadmap
- **Enhanced Data Normalization:** Refinement of mathematical models for advanced inter-plate normalization.
- **Customizable Well Mapping:** Implementation of a GUI feature to define custom positions for controls and blanks, allowing for flexible pipetting schemes.

## Tech-Stack
- **Python 3.14**
- **Pandas** for data processing
- **Seaborn & Matplotlib** for data visualization
- **Tkinter** for the graphical user interface

## Installation for Mac Users:

- Open Terminal.
- Install dependencies: pip3 install pandas seaborn matplotlib
- Run the app: python3 main_gui.py

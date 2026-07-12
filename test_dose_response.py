import math
import os
import tempfile
import unittest
from unittest.mock import patch

from analyzer import calculate_auc_log10
from dose_response import fit_four_parameter_logistic
import main_gui


class DoseResponseTest(unittest.TestCase):
    def test_fit_four_parameter_logistic_recovers_ic50(self):
        concentrations = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]

        def model(x, top, bottom, hill_slope, ic50):
            return bottom + (top - bottom) / (1 + 10 ** ((math.log10(x) - math.log10(ic50)) * hill_slope))

        expected_top = 100.0
        expected_bottom = 0.0
        expected_hill_slope = -1.2
        expected_ic50 = 1.0

        values = [
            model(c, expected_top, expected_bottom, expected_hill_slope, expected_ic50)
            for c in concentrations
        ]

        fit = fit_four_parameter_logistic(concentrations, values)

        self.assertIsNotNone(fit)
        self.assertTrue(abs(fit["ic50"] - expected_ic50) < 0.3)
        self.assertTrue(abs(fit["hill_slope"] - expected_hill_slope) < 0.3)
        self.assertTrue(fit["ic10"] > 0)
        self.assertTrue(fit["ic90"] > fit["ic10"])

    def test_auc_log10_matches_trapezoid_rule(self):
        concentrations = [1.0, 10.0, 100.0]
        values = [0.0, 50.0, 100.0]
        auc = calculate_auc_log10(concentrations, values)
        self.assertAlmostEqual(auc, 100.0, places=6)

    def test_build_template_payload_contains_only_selection(self):
        app = main_gui.MTTAnalyzerApp.__new__(main_gui.MTTAnalyzerApp)
        app.puro_wells = {"A1"}
        app.blank_wells = {"B1"}
        app.dmso_wells = {"C1"}
        app.start_triplet = ["D1"]
        app.start_conc = type("Entry", (), {"get": lambda self: "10"})()

        payload = app.build_template_payload()

        self.assertEqual(payload["puro"], ["A1"])
        self.assertEqual(payload["blank"], ["B1"])
        self.assertEqual(payload["dmso"], ["C1"])
        self.assertEqual(payload["start_triplet"], ["D1"])
        self.assertEqual(payload["start_concentration"], "10")
        self.assertNotIn("summary", payload)
        self.assertNotIn("raw_plate_data", payload)

    def test_save_pdf_summary_creates_file(self):
        app = main_gui.MTTAnalyzerApp.__new__(main_gui.MTTAnalyzerApp)
        app.puro_wells = {"A1"}
        app.blank_wells = {"B1"}
        app.dmso_wells = {"C1"}
        app.start_triplet = ["D1"]
        app.analysis_summary = {
            "blank": 0.1,
            "reference_name": "dmso",
            "reference_value": 1.0,
            "mean_difference_blank_corrected": 0.5,
            "viability_difference": 10.0,
            "z_prime": 0.7,
            "signal_to_background": 2.0,
            "dose_response": [{
                "group_index": 1,
                "concentration": 1.0,
                "viability": 80.0,
                "std": 2.0,
                "rel_std": 2.5,
                "wells": ["A1", "B1", "C1"],
            }],
            "dose_response_fit": {
                "bottom": 10.0,
                "top": 90.0,
                "hill_slope": -1.2,
                "log_ic50": 0.0,
                "ic10": 0.1,
                "ic50": 1.0,
                "ic90": 10.0,
            },
            "e_min": 10.0,
            "e_max": 90.0,
            "raw_plate_data": {"A": {"1": 1.0}},
        }
        app.last_analysis_file_name = "demo"

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = app.save_pdf_summary(
                summary=app.analysis_summary,
                base_name="demo",
                output_folder=tmpdir,
                heatmap_matrix=[[100, 90], [80, 70]],
                status_msg="OK",
            )
            self.assertTrue(os.path.exists(pdf_path))
            self.assertTrue(pdf_path.endswith("demo_summary.pdf"))

    def test_refresh_button_colors_uses_loaded_json_path(self):
        class DummyApp:
            def __init__(self):
                self.well_buttons = {}
                self.default_color = "#000000"
                self.puro_wells = set()
                self.blank_wells = set()
                self.dmso_wells = set()
                self.start_triplet = []
                self.last_loaded_json_path = "/tmp/template.json"

        app = DummyApp()
        captured = {}

        def fake_showinfo(title, message):
            captured["title"] = title
            captured["message"] = message

        with patch.object(main_gui.messagebox, "showinfo", side_effect=fake_showinfo):
            main_gui.MTTAnalyzerApp.refresh_button_colors(app)

        self.assertEqual(captured["title"], "JSON geladen")
        self.assertIn("template.json", captured["message"])


if __name__ == "__main__":
    unittest.main()

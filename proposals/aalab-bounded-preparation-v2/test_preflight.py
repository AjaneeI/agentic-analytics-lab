"""Offline bootstrap controls: no dependencies execute before exact preflight."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
try:
    import offline_loader as loader
except ModuleNotFoundError:
    # Explicit permissive baseline; missing refusal must fail before implementation.
    from types import SimpleNamespace
    loader = SimpleNamespace(preflight=lambda path: ({}, {}))

HERE=Path(__file__).resolve().parent

class PreflightControls(unittest.TestCase):
    def test_active_live_wrong_approval_or_attempt_configuration_refused(self):
        cases=[{}, {"version":"aalab-bounded-preparation-v2","activation":True},
               {"version":"aalab-bounded-preparation-v2","authorized_treatment_a_attempts":1},
               {"version":"aalab-bounded-preparation-v2","approved_package_sha256":"0"*64}]
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"config.json"
            for config in cases:
                with self.subTest(config=config):
                    p.write_text(json.dumps(config))
                    with self.assertRaises(ValueError): loader.preflight(p)

    def test_complete_pins_verify_and_retained_sources_execute(self):
        config,retained=loader.preflight(HERE/"synthetic-config.json")
        self.assertEqual(config["authorized_treatment_a_attempts"],0)
        self.assertEqual(len(retained),len(config["source_sha256"])+len(config["dependency_sha256"]))
        self.assertIn(str((HERE/"integrated_capture.py").resolve()),retained)

    def test_each_missing_candidate_pin_rejected(self):
        original=json.loads((HERE/"synthetic-config.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"config.json"
            for key in original["source_sha256"]:
                config=copy.deepcopy(original);del config["source_sha256"][key]
                p.write_text(json.dumps(config))
                with self.subTest(key=key), self.assertRaises(ValueError): loader.preflight(p)

    def test_each_wrong_dependency_and_candidate_hash_rejected(self):
        original=json.loads((HERE/"synthetic-config.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"config.json"
            for group in ("source_sha256","dependency_sha256"):
                for key in original[group]:
                    config=copy.deepcopy(original);config[group][key]="0"*64
                    p.write_text(json.dumps(config))
                    with self.subTest(group=group,key=key), self.assertRaises(ValueError): loader.preflight(p)

if __name__=="__main__":unittest.main()

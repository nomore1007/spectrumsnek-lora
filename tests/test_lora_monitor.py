import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "__init__.py"
SPEC = importlib.util.spec_from_file_location("lora_monitor", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RtlPowerParserTests(unittest.TestCase):
    def test_parses_frequency_bins(self):
        row = "2026-10-20, 12:00:00, 902000000, 902100000, 25000, 4, -40.0, -30.0, -50.0, -45.0\n"
        samples = MODULE._parse_rtl_power(row)
        self.assertEqual(len(samples), 4)
        self.assertEqual(samples[0], (902012500.0, -40.0))
        self.assertEqual(samples[1], (902037500.0, -30.0))

    def test_skips_headers_and_invalid_rows(self):
        text = "date,time, hz low, hz high, hz step, samples, dbm\nnot,a,valid,row\n"
        self.assertEqual(MODULE._parse_rtl_power(text), [])

    def test_ignores_non_finite_values(self):
        row = "2026-10-20, 12:00:00, 902000000, 902100000, 25000, 4, -40.0, nan, inf, -45.0\n"
        samples = MODULE._parse_rtl_power(row)
        self.assertEqual([power for _, power in samples], [-40.0, -45.0])


class FrequencyParserTests(unittest.TestCase):
    def test_frequency_suffixes(self):
        self.assertEqual(MODULE._frequency_hz("902M"), 902_000_000)
        self.assertEqual(MODULE._frequency_hz("125k"), 125_000)
        self.assertEqual(MODULE._frequency_hz("915000000"), 915_000_000)
        self.assertEqual(MODULE._frequency_hz("0.9G"), 900_000_000)

    def test_invalid_frequency_raises(self):
        with self.assertRaises(ValueError):
            MODULE._frequency_hz("not-a-frequency")


if __name__ == "__main__":
    unittest.main()

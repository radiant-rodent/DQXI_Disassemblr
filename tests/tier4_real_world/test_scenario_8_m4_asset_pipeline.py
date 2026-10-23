"""Tier 4: Scenario 8 - Milestone 4 Universal Asset Decompilation & Re-encoders.
Features Exercised: F1 through F14 (Asset extraction, decoding, standard conversion, and bit-matching rebuild).
Runs tests/test_m4_assets.py suite covering Textures, 3D Models, UI Layouts, Audio, Scripts & Tables.
"""

import unittest
from tests.test_m4_assets import (
    TestAudioTool,
    TestLayoutTool,
    TestModelTool,
    TestScriptTool,
    TestTableTool,
    TestTextureTool,
)


class TestScenario8M4AssetPipeline(unittest.TestCase):
    """Scenario 8: Milestone 4 Universal Asset Pipelines."""

    def test_scenario_8_textures_roundtrip(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(TestTextureTool)
        res = unittest.TextTestRunner(verbosity=0).run(suite)
        self.assertTrue(res.wasSuccessful(), f"Texture tests failed: {res.errors + res.failures}")

    def test_scenario_8_models_gltf_obj(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(TestModelTool)
        res = unittest.TextTestRunner(verbosity=0).run(suite)
        self.assertTrue(res.wasSuccessful(), f"Model tests failed: {res.errors + res.failures}")

    def test_scenario_8_layouts_roundtrip(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(TestLayoutTool)
        res = unittest.TextTestRunner(verbosity=0).run(suite)
        self.assertTrue(res.wasSuccessful(), f"Layout tests failed: {res.errors + res.failures}")

    def test_scenario_8_audio_bcstm_bcsar(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(TestAudioTool)
        res = unittest.TextTestRunner(verbosity=0).run(suite)
        self.assertTrue(res.wasSuccessful(), f"Audio tests failed: {res.errors + res.failures}")

    def test_scenario_8_scripts_sqbin(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(TestScriptTool)
        res = unittest.TextTestRunner(verbosity=0).run(suite)
        self.assertTrue(res.wasSuccessful(), f"Script tests failed: {res.errors + res.failures}")

    def test_scenario_8_tables_bxon(self):
        suite = unittest.TestLoader().loadTestsFromTestCase(TestTableTool)
        res = unittest.TextTestRunner(verbosity=0).run(suite)
        self.assertTrue(res.wasSuccessful(), f"Table tests failed: {res.errors + res.failures}")


if __name__ == "__main__":
    unittest.main()

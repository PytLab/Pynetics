import unittest
import sys
import logging

from kynetix.model import KineticModel
from kynetix.parsers import *


class TestKineticModel(unittest.TestCase):

    def setUp(self):
        # Test case setting.
        self.maxDiff = None

    def test_mkm_construction_query(self):
        " Test micro kinetic model can be constructed with parser. "
        # Test construction.
        model = KineticModel(setup_file="input_files/setup.mkm",
                             verbosity=logging.WARNING)

        # Test member data query.
        self.assertEqual(model.h(), 4.135667662e-15)
        self.assertEqual(model.kB(), 8.6173324e-5)

        # Load data in setup file.
        glob, loc = {}, {}
        execfile("input_files/setup.mkm", glob, loc)
        self.assertEqual(model.tools(), loc["tools"])
        self.assertEqual(model.solver(), loc["solver"])
        self.assertEqual(model.corrector(), loc["corrector"])
        self.assertEqual(model.plotter(), loc["plotter"])
        self.assertEqual(model.rxn_expressions(), loc["rxn_expressions"])
        self.assertEqual(model.temperature(), loc["temperature"])
        self.assertEqual(model.ref_species(), loc["ref_species"])
        self.assertEqual(model.surface_name(), loc["surface_name"])
        self.assertEqual(model.verbosity(), logging.WARNING)
        self.assertEqual(model.decimal_precision(), 100)

        self.assertTrue(isinstance(model.parser(), RelativeEnergyParser))

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestKineticModel)
    unittest.TextTestRunner(verbosity=2).run(suite)

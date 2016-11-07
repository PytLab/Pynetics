#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import unittest

from kynetix.model import KineticModel
from kynetix.solvers import *

from unit_test import *


class KMCRedistributionTest(unittest.TestCase):

    def setUp(self):
        # Test case setting.
        self.maxDiff = None
        self.setup = kmc_path + "/kmc_redistribution.mkm"

    def test_run_with_redistribution(self):
        " Make sure the model can run with redistribution operation. "
        model = KineticModel(setup_file=self.setup, verbosity=logging.WARNING)
        parser = model.parser()
        parser.parse_data(filename=kmc_energy, relative=True)

        # Run the model with redistribution.
        model.run_kmc(processes_file=kmc_processes,
                      configuration_file=kmc_config,
                      sitesmap_file=kmc_sites)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(KMCRedistributionTest)
    unittest.TextTestRunner(verbosity=2).run(suite)


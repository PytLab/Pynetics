import logging
from math import exp, pi, sqrt

from kynetix import ModelShell
from kynetix.database.thermo_data import kB_J, kB_eV, h_eV
from kynetix.functions import *
from kynetix.parsers.rxn_parser import *
from kynetix.parsers.parser_base import ParserBase


class SolverBase(ModelShell):
    """
    Abstract base class to be herited by other solver classes.
    """

    def __init__(self, owner):
        super(SolverBase, self).__init__(owner)

        # Set logger.
        self.__logger = logging.getLogger("model.solver.SolverBase")

    @staticmethod
    def get_kTST(Ga, T):
        """
        Static function to get rate constants according to Transition State Theory.

        Parameters:
        -----------
        Ga: free energy barrier, float.

        T: thermodynamics constants, floats.
        """

        kTST = kB_eV*T/h_eV*exp(-Ga/(kB_eV*T))

        return kTST

    @staticmethod
    def get_kCT(Ea, Auc, act_ratio, p, m, T, f=1.0):
        """
        Static function to get rate constant/collision rate
        according to Collision Theory.

        Parameters:
        -----------
        Ea: energy barrier( NOT free energy barrier), float.

        Auc: area of unitcell (m^-2), float.

        act_ratio: area of active sites/area of unitcell, float(<= 1.0).

        p: partial pressure of gas, float.

        m: absolute mass of molecule (kg), float.

        f: factor accounts for a further reduction in the sticking probability,
           if particle with certain initial states are not efficiently steered
           along the MEP, and reflected by a higher barrier, float(<= 1.0).

        T: temperature (K), float.
        """
        # Check parameters.
        if act_ratio > 1.0:
            msg = "active area ratio must be less than 1.0"
            raise ParameterError(msg)

        if f > 1.0:
            msg = "factor f must be less than 1.0"
            raise ParameterError(msg)

        # Sticking coefficient.
        S = f*act_ratio*exp(-Ea/(kB_eV*T))

        # Rate constant.
        kCT = S*(p*Auc)/(sqrt(2*pi*m*kB_J*T))

        return kCT

    def get_rxn_rates_TST(self, rxn_expression, relative_energies):
        """
        Function to get rate constants for an elementary reaction
        using Transition State Theory.

        Parameters:
        -----------
        rxn_expression: The expression of an elementary reaction, str.
        relative_energies: The relative energies for all elementary reactions.
        """
        Gaf, Gar, dG = self._get_relative_energies(rxn_expression, relative_energies)
        T = self._owner.temperature
        kf, kr = [self._mpf(self.get_kTST(Ga, T)) for Ga in [Gaf, Gar]]

        return kf, kr

    def get_rxn_rates_CT(self, rxn_expression, relative_energies):
        """
        Function to get rate constants for an elementary reaction
        using Collision Theory wrt adsorption process.

        Parameters:
        -----------
        rxn_expression: The expression of an elementary reaction, str.
        relative_energies: The relative energies for all elementary reactions.
        """
        # {{{
        # Get raw relative energies.
        Gaf, Gar, dG = self._get_relative_energies(rxn_expression, relative_energies)
        if self._owner.log_allowed:
            self.__logger.info("{} (Gaf={}, Gar={}, dG={})".format(rxn_expression, Gaf, Gar, dG))

        # Get reactants and product types.
        rxn_equation = RxnEquation(rxn_expression)
        formula_list = rxn_equation.to_formula_list()
        istate, fstate = formula_list[0], formula_list[-1]
        is_types = [formula.type() for formula in istate]
        fs_types = [formula.type() for formula in fstate]
        if self._owner.log_allowed:
            self.__logger.info("species type: {} -> {}".format(is_types, fs_types))

        # Get rate constant.
        T = self._owner.temperature
        Auc = self._owner.unitcell_area
        act_ratio = self._owner.active_ratio

        # Get model corrector.
        corrector = self._owner.corrector
        # Check.
        if type(corrector) == str:
            msg = "No instantialized corrector, try to modify '{}'"
            msg = msg.format(self._owner.setup_file)
            raise SetupError(msg)

        # Forward rate.

        # Gas participating.
        if "gas" in is_types:
            # Get gas pressure.
            idx = is_types.index("gas")
            formula = istate[idx]
            gas_name = formula.formula()
            p = self._owner.species_definitions[gas_name]["pressure"]

            # Use Collision Theory.
            Ea = Gaf
            m = ParserBase.get_molecular_mass(formula.species(), absolute=True)
            rf = SolverBase.get_kCT(Ea, Auc, act_ratio, p, m, T)
            if self._owner.log_allowed:
                self.__logger.info("R(forward) = {} s^-1 (Collision Theory)".format(rf))
        # No gas participating.
        else:
            # ThermoEquilibrium and gas species in final state.
            if "gas" in fs_types and Gar < 1e-10:
                # Correction energy.
                idx = fs_types.index("gas")
                formula = fstate[idx]
                gas_name = formula.species_site()
                p = self._owner.species_definitions[gas_name]["pressure"]
                m = ParserBase.get_molecular_mass(formula.species(), absolute=True)
                correction_energy = corrector.entropy_correction(gas_name, m, p, T)
                stoichiometry = formula.stoichiometry()
                Gaf += stoichiometry*correction_energy

                # Info output.
                msg = "Correct forward barrier: {} -> {}".format(Gaf-correction_energy, Gaf)
                if self._owner.log_allowed:
                    self.__logger.info(msg)

            rf = SolverBase.get_kTST(Gaf, T)
            if self._owner.log_allowed:
                self.__logger.info("R(forward) = {} s^-1 (Transition State Theory)".format(rf))

        # Reverse rate.

        # Gas participating.
        if "gas" in fs_types:
            # Get gas pressure.
            idx = fs_types.index("gas")
            formula = fstate[idx]
            gas_name = formula.formula()
            p = self._owner.species_definitions[gas_name]["pressure"]

            # Use Collision Theory.
            Ea = Gar
            m = ParserBase.get_molecular_mass(formula.species(), absolute=True)
            rr = SolverBase.get_kCT(Ea, Auc, act_ratio, p, m, T)
            if self._owner.log_allowed:
                self.__logger.info("R(reverse) = {} s^-1 (Collision Theory)".format(rr))
        # No gas participating.
        else:
            # Check if it is an adsorption process.
            if "gas" in is_types and Gaf < 1e-10:
                # Correction energy.
                idx = is_types.index("gas")
                formula = istate[idx]
                gas_name = formula.species_site()
                p = self._owner.species_definitions[gas_name]["pressure"]
                m = ParserBase.get_molecular_mass(formula.species(), absolute=True)
                correction_energy = corrector.entropy_correction(gas_name, m, p, T)
                stoichiometry = formula.stoichiometry()
                dG -= stoichiometry*correction_energy

                # Info output.
                if self._owner.log_allowed:
                    msg = "Correct dG: {} -> {}".format(dG+correction_energy, dG)
                    self.__logger.info(msg)

                # Use Equilibrium condition to get reverse rate.
                K = exp(-dG/(kB_eV*T))
                rr = rf/K
                if self._owner.log_allowed:
                    self.__logger.info("R(reverse) = {} s^-1 (Equilibrium Condition)".format(rr))
            else:
                # Use Transition State Theory.
                rr = SolverBase.get_kTST(Gar, T)
                if self._owner.log_allowed:
                    self.__logger.info("R(reverse) = {} s^-1 (Transition State Theory)".format(rr))

        return rf, rr
        # }}}

    def _get_relative_energies(self, rxn_expression, relative_energies):
        """
        Private helper function to get relative energies for an elementary reaction.
        """
        # Get raw relative energies.
        rxn_expressions = self._owner.rxn_expressions
        idx = rxn_expressions.index(rxn_expression)

        Gaf = relative_energies["Gaf"][idx]
        Gar = relative_energies["Gar"][idx]
        dG = relative_energies["dG"][idx]

        return Gaf, Gar, dG


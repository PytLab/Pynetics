import copy
import logging

import mpmath as mp
import numpy as np
import gmpy2
import sympy as sym
#import sympy.mpmath as symp
try:
    import matplotlib.pyplot as plt
except ImportError:
    print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    print "!!!                                                   !!!"
    print "!!!       WARNING: Matplotlib is not installed        !!!"
    print "!!!       Any plot functions will be disabled         !!!"
    print "!!!                                                   !!!"
    print "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

from kynetix import KineticCoreComponent
from kynetix.functions import *
from kynetix.parsers.rxn_parser import *


class SolverBase(KineticCoreComponent):
    def __init__(self, owner):
        '''
        A class acts as a base class to be inherited by other
        solver classes, it is not functional on its own.
        '''
        super(SolverBase, self).__init__(owner)

        # Set logger.
        self.__logger = logging.getLogger("model.solvers.SolverBase")

        # Update default parameter dict
        defaults = dict(perturbation_size=0.01,
                        perturbation_direction='right',
                        numerical_representation='mpmath',
                        archived_variables=['steady_state_coverage', 'rates'])
        defaults = self.update_defaults(defaults)

        # Set varibles in defaults protected attributes of solver.
        protected_defaults = {"_{}".format(key): value
                              for key, value in defaults.iteritems()}
        self.__dict__.update(protected_defaults)

        # Set numerical representation.
        self.__set_numerical_representation()

        # Set flags.
        self._has_absolute_energy = False
        self._has_relative_energy = False
        self._has_energy_correction = False
        self._has_symbols = False

        # Set essential attrs for solver
        self._rxns_list = self._owner.elementary_rxns_list()
        self._rxns_num = len(self._rxns_list)

        # set constants symbol dict
        self._kB_sym, self._h_sym, self._T_sym = sym.symbols('kB, h, T', is_real=True)

        # Constant symbols substitution dict.
        self._constants_subs_dict = {
            self._kB_sym: self._mpf(self._owner.kB()),
            self._h_sym: self._mpf(self._owner.h()),
            self._T_sym: self._mpf(self._owner.temperature()),
        }

        # classify adsorbates according to site type
        self._classified_adsorbates = self.__classify_adsorbates()

    def __set_numerical_representation(self):
        # {{{
        """
        Private helper function to set numerical representation.
        """
        # Mpmath.
        if self._numerical_representation == 'mpmath':
            mp.mp.dps = self._owner.decimal_precision()
            self._math = mp  # to do math operations
            self._linalg = mp
            self._mpf = mp.mpf
            self._matrix = mp.matrix
            self._Axb_solver = mp.lu_solve
            self._norm = lambda x: mp.norm(x, p=2)
        # Gmpy2.
        elif self._numerical_representation == 'gmpy':
            gmpy2.get_context().precision = 3*self._owner.decimal_precision()
            self._math = gmpy2
            self._linalg = np
            self._mpf = gmpy2.mpfr

            def cus_matrix(*args):
                if len(args) == 1:
                    mat = np.matrix(args[0])
                    mat_shape = mat.shape
                    if mat_shape[0] == 1 and mat_shape[1] > 1:
                        mat.shape = (-1, 1)
                    return mat
                elif len(args) == 2:
                    return np.matrix(np.empty(args, object))

            self._matrix = cus_matrix
            self._Axb_solver = np.linalg.solve
            self._norm = lambda x: gmpy2.sqrt(np.sum(np.square(x)))  # x is a column vector
        # Sympy.
        elif self._numerical_representation == 'sympy':
            self._math = sym
            self._linalg = sym
            precision = self._owner.decimal_precision()
            self._mpf = lambda x: \
                sym.N(sym.RealNumber(str(x), precision), precision)

            def cus_matrix(*args):
                if len(args) == 1:
                    return sym.Matrix(args[0])
                elif len(args) == 2:
                    return sym.zeros(*args)

            self._matrix = cus_matrix
            self._Axb_solver = lambda A, b: A.LUsolve(b)
            self._norm = lambda x: sym.sqrt((x.transpose()*x)[0])  # x is a column vector
        # }}}

    def log_latex(self, latex_tup):
        "Append latex strings to 'formulas.tex'."
        latex_str = ''.join(latex_tup)
        latex_str += '\n'

        self.write2file('formulas.tex', latex_str)
        return latex_str

    def __classify_adsorbates(self):
        """
        Private helper function to classify coverages according to type of site.
        """
        classified_adsorbates = {}
        for site_name in self._owner.site_names():
            classified_adsorbates.setdefault(site_name, [])

        species_definitions = self._owner.species_definitions()
        for adsorbate_name in self._owner.adsorbate_names():
            formula = ChemFormula(adsorbate_name)
            site_name = formula.site()
            classified_adsorbates[site_name].append(adsorbate_name)

        return classified_adsorbates

    def _cvg_tuple2dict(self, cvgs_tuple):
        """
        Protected function to convert coverages list to corresponding coverages dict.
        """

        # NOTE: there are some small errors when convert tuple to dict
        #       which is so small that we can ignore it

        # Create cvgs_dict containing adsorbates
        cvgs_dict = {}
        adsorbate_names = self._owner.adsorbate_names()
        for adsorbate_name in adsorbate_names:
            idx = adsorbate_names.index(adsorbate_name)
            cvgs_dict.setdefault(adsorbate_name, cvgs_tuple[idx])

        # Add free site coverages
        species_definitions = self._owner.species_definitions()
        for site_name in self._owner.site_names():
            total_cvg = species_definitions[site_name]['total']
            sum_cvg = 0.0
            for sp in self._classified_adsorbates[site_name]:
                sum_cvg += cvgs_dict[sp]
            free_site_cvg = total_cvg - sum_cvg
            cvgs_dict.setdefault('*_' + site_name, free_site_cvg)

        return cvgs_dict

    def _cvg_dict2tuple(self, cvgs_dict):
        """
        Protected function to convert coverages dict to coverages tuple.
        """
        cvgs_list = []
        for adsorbate_name in self._owner.adsorbate_names():
            cvgs_list.append(cvgs_dict[adsorbate_name])
        return tuple(cvgs_list)

    def get_data(self):
        """
        Function to get data from model.
        """
        species_definitions = self._owner.species_definitions()

        # Get gas pressure dict.
        p_dict = {}
        for gas_name in self._owner.gas_names():
            pressure = species_definitions[gas_name]['pressure']
            p_dict.setdefault(gas_name, self._mpf(pressure))
        self._p = p_dict

        # Get concentration dict.
        c_dict = {}
        for liquid_name in self._owner.liquid_names():
            concentration = species_definitions[liquid_name]['concentration']
            c_dict.setdefault(liquid_name, self._mpf(concentration))
        self._c = c_dict

        # Get energy data(relative or absolute)
        if self._owner.has_relative_energy():
            self._relative_energies = self._owner.relative_energies()
            # Set flag.
            self._has_relative_energy = True
        else:
            raise IOError('No relative energies was read, try parser.parse_data() ' +
                          'or add data in data table.')

        # get energy for each species
        if self._owner.has_absolute_energy():
            G_dict = {}
            for species in species_definitions:
                if ("type" in species_definitions[species] and
                        species_definitions[species]["type"] == "site"):
                    key = '*_' + species
                else:
                    key = species
                energy = self._mpf(species_definitions[species]['formation_energy'])
                G_dict.setdefault(key, energy)
            self._G = G_dict

            # Set flags.
            self._has_energy_correction = False
            self._has_absolute_energy = True

    def get_rate_constants(self, relative_energies=None):
        """
        Function to get rate constants for all elementary reactions.

        Parameters:
        -----------
        relative_energies: A dict of relative eneriges of elementary reactions.
            NOTE: keys "Gaf" and "Gar" must be in relative energies dict.

        Returns:
        --------
        Forward rate constants, Reverse rate constants
        """
        # Get relative energies.
        if not relative_energies:
            if self._has_relative_energy:
                relative_energies = self._relative_energies
            else:
                msg = "Solver must have relative energies to get rate constants."
                raise AttributeError(msg)

        # Check input parameter.
        if "Gaf" and "Gar" not in relative_energies:
            msg = "'Gaf' and 'Gar' must be in relative_energies."
            raise ParameterError(msg)

        # Calculate rate constants.
        kB, h, T = [self._mpf(constant) for constant in
                    [self._owner.kB(), self._owner.h(), self._owner.temperature()]]
        prefactor = kB*T/h
        kfs, krs = [], []
        Gafs, Gars = relative_energies["Gaf"], relative_energies["Gar"]

        for Gaf, Gar in zip(Gafs, Gars):
            kf = prefactor*self._math.exp(-Gaf/(kB*T))
            kr = prefactor*self._math.exp(-Gar/(kB*T))
            kfs.append(kf)
            krs.append(kr)

        return tuple(kfs), tuple(krs)

    def boltzmann_coverages(self, include_empty_site=True):
        """
        Function to get boltzmann coverages according to the formation energy of each adsorbate.

        Parameters:
        -----------
        include_empty_site: If the empty sites are included in bolztmann sum, bool.
                            Default value is True.

        Returns:
        --------
        cvgs: A tuple of coverages in order of adsorbates names.
        """
        free_site_names = tuple(['*_' + site for site in self._owner.site_names()])
        self._cvg_types = self._owner.adsorbate_names() + free_site_names
        kB, h, T = [self._mpf(constant) for constant in
                    [self._owner.kB(), self._owner.h(), self._owner.temperature()]]

        # Check whether solver has load data from species_definition
        if not self._has_absolute_energy:
            self.get_data()
        if not self._has_absolute_energy:  # if no absolute again, raise exception
            raise IOError('No absolute energies read, could not get Boltzmann coverages.')

        if include_empty_site:
            boltz_sum = sum([mp.exp(-self._G[adsorbate]/(kB*T))
                             for adsorbate in self._cvg_types])
        else:
            boltz_sum = sum([self._math.exp(-self._G[adsorbate]/(kB*T))
                             for adsorbate in self._owner.adsorbate_names()])

        # Get coverages list
        cvgs = []
        for adsorbate in self._owner.adsorbate_names():
            cvg = self._math.exp(-self._G[adsorbate]/(kB*T))/boltz_sum
            cvgs.append(cvg)

        return tuple(cvgs)

    def get_elementary_rate_expression(self, rxn_expression):
        """
        Function to get the rate calculation expression for an elementary reaction.

        Parameters:
        -----------
        elementary_rxn_list: An elementary reaction (in list).

        Returns:
        --------
        f_expr, r_expr: A tuple of forward and reverse reaction rate expressions.

        Example:
        --------
        >>> rxn_list = [['O2_g', '2*_s'], ['2O_s']]
        >>> solver.get_elementary_rate_expression(rxn_list)
        >>> ("kf[1]*p['O2_g']*theta['*_s']**2", "kr[1]*theta['O_s']**2")
        """
        idx = self._owner.rxn_expressions().index(rxn_expression)

        # Local function.
        def list2string(formula_list, direction):
            if direction == 'f':
                rate_str = 'kf[' + str(idx) + ']'
            if direction == 'r':
                rate_str = 'kr[' + str(idx) + ']'

            for formula in formula_list:
                stoichiometry = formula.stoichiometry()
                species_name = formula.species_site()
                #get type of species
                if '*' in species_name:
                    if stoichiometry == 1:
                        sp_expr = "*theta['" + species_name + "']"
                    else:
                        sp_expr = "*theta['" + species_name + "']**" + str(stoichiometry)
                else:
                    sp_type = formula.type()
                    if sp_type == 'adsorbate':
                        if stoichiometry == 1:
                            sp_expr = "*theta['" + species_name + "']"
                        else:
                            sp_expr = "*theta['" + species_name + "']**" + str(stoichiometry)
                    elif sp_type == 'gas':
                        if stoichiometry == 1:
                            sp_expr = "*p['" + species_name + "']"
                        else:
                            sp_expr = "*p['" + species_name + "']**" + str(stoichiometry)
                    elif sp_type == 'liquid':
                        if stoichiometry == 1:
                            sp_expr = "*c['" + species_name + "']"
                        else:
                            sp_expr = "*c['" + species_name + "']**" + str(stoichiometry)
                rate_str += sp_expr
            return rate_str

        elementary_rxn_list = self._rxns_list[idx]

        f_expr, r_expr = (list2string(elementary_rxn_list[0], direction='f'),
                          list2string(elementary_rxn_list[-1], direction='r'))

        return f_expr, r_expr

    def get_rate_expressions(self):
        """
        Function to get rate expression for all elementary reactions in model.
        """
        f_rate_expressions, r_rate_expressions = [], []
        rxn_expressions = self._owner.rxn_expressions()

        # Loop over all rxn expressions to get all rate expressions.
        for idx, rxn_expression in enumerate(rxn_expressions):
            f_expr, r_expr = self.get_elementary_rate_expression(rxn_expression)
            f_rate_expressions.append('rfs[' + str(idx) + '] = ' + f_expr)
            r_rate_expressions.append('rrs[' + str(idx) + '] = ' + r_expr)

        return f_rate_expressions, r_rate_expressions

    def get_rates(self, cvgs_tuple, archive=False):
        """
        Function to get forward and reverse rates list.

        Parameters:
        -----------
        cvgs_tuple: coverage tuple, tuple of floats.
        archive: archive data or not, bool.

        Returns:
        --------
        rfs, rrs: forward rates and reverse rates, tuple of float.
        """
        # Coverages(theta).
        theta = self._cvg_tuple2dict(cvgs_tuple)

        # Rate constants(kf, kr).
        kf, kr = self.get_rate_constants()

        # Pressure.
        p = self._p

        # Concentration.
        c = self._c

        # Rate list.
        rfs, rrs = [0]*self._rxns_num, [0]*self._rxns_num

        # Rate expressions.
        rate_expressions = self.get_rate_expressions()

        # Calculate rates.
        for exprs_list in rate_expressions:
            exprs_str = '\n'.join(exprs_list)
            exec exprs_str in locals()

        rfs, rrs = map(tuple, (rfs, rrs))

        # Archive.
        if archive:
            self.archive_data('rates', (rfs, rrs))

        return rfs, rrs

    def get_net_rates(self, cvgs_tuple, archive=False):
        """
        Function to get forward and reverse rates list.

        Parameters:
        -----------
        cvgs_tuple: coverage tuple, tuple of floats.
        archive: archive data or not, bool.

        Returns:
        --------
        net_rates: net rates for all elementary reactions, tuple of float.
        """
        # Get forward and reverse rates.
        rfs, rrs = self.get_rates(cvgs_tuple, archive=False)

        # Get net rates.
        net_rates = tuple([rf - rr for rf, rr in zip(rfs, rrs)])

        # Archive.
        if archive:
            self.archive_data('net_rates', net_rates)

        return net_rates

    def get_reversibilities(self, rfs, rrs):
        """
        Function to get reversibilities of given rates.

        Parameters:
        -----------
        rfs: forward rates, list of float.
        rrs: reverse rates, list of float.

        Returns:
        --------
        reversibilities: list of float.
        """
        if len(rfs) != len(rrs):
            raise ValueError('Different rates number is detected.')

        reversibilities = [float(rr/rf) for rf, rr in zip(rfs, rrs)]

        # Archive.
        self.archive_data('reversibilities', reversibilities)

        return reversibilities

    def get_tof(self, cvgs):
        """
        Function to get the turnover frequencies(TOF) wrt all gas species.

        Parameters:
        -----------
        cvgs: coverages of adsorbates on surface, tuple of float.

        Returns:
        --------
        tof_list: List of TOF.
        """
        # Get net rates wrt the coverages c.
        net_rates = self.get_net_rates(cvgs)

        # Get turnover frequencies.
        _, reapro_matrix = self._owner.parser().get_stoichiometry_matrices()
        reapro_matrix *= -1
        rate_vector = np.matrix(net_rates)  # get rate vector
        tof_list = (rate_vector*reapro_matrix).tolist()[0]

        # log TOFs
        self.__log_tof(tof_list, self._owner.gas_names())

        # Archive.
        self.archive_data('tofs', tof_list)

        return tof_list

    def __log_tof(self, tof_list, gas_names):
        """
        Private helper function to log TOF of every gas species.
        """
        head_str = "\n\n {:<5s}     {:<20s}     {:<30s}\n".format("index", "gas name", "TOF")
        line_str = '-'*60 + '\n'

        all_data = ''
        all_data += head_str + line_str
        for idx, (gas_name, tof) in enumerate(zip(gas_names, tof_list)):
            idx = str(idx).zfill(2)
            data = " {:<5s}     {:<20s}     {:<30.16e}\n".format(idx, gas_name, float(tof))
            all_data += data
        all_data += line_str

        self.__logger.info(all_data)

        return all_data

    def classified_numerical_jacobian(self, f, x, h=1e-10):
        """
        Calculate the Jacobian matrix of a function at the point x0.
        Modified from numerial_jacobian() in 'functions.py'.

        Not a general-purpose method, just used for given model

        Use differences in opposite directions according to the type
        of G(intermediate or transition state) to avoid stagnated or
        diverging residual.
        """
        x = self._matrix(x)
        x = self._matrix(x).reshape(-1, 1)
        fx = self._matrix(f(x))
        m = len(fx)
        n = len(x)
        J = self._matrix(m, n)
        inter_num = len(self._owner.adsorbate_names())

        for j in xrange(n):
            print j
            xj = x.copy()
            #using delta proportional to xj is more stable
            delta = abs(h*xj[j])
            delta = max(delta, h)

            #differences with different direction
            if j <= inter_num - 1:
                xj[j] += delta
                Jj = (self._matrix(f(xj)) - fx)/(delta)
            else:
                xj[j] -= delta
                Jj = (self._matrix(f(xj)) - fx)/(-delta)

            for i in xrange(m):
                J[i, j] = Jj[i]
        return J

    def correct_energies(self):
        "Correct energies of solver"
        #corrections for gas
        if self._owner.gas_thermo_mode() == 'shomate_gas':
            correction_dict = self._owner.corrector.shomate_gas()
        for gas_name in correction_dict:
            self.E[gas_name] += correction_dict[gas_name]
        setattr(self, 'energy_correction', True)

        return self.E

    ######################################################
    ######                                          ######
    ###### calculate micro kinetic model with Sympy ######
    ######                                          ######
    ######################################################

    def get_data_symbols(self):
        # {{{
        """
        Get Sympy Symbol objects tuple for P, G, coverage.
        """
        # Pressure symbols objects.
        self._p_sym = tuple([sym.Symbol('p_' + gas_name, real=True, positive=True)
                             for gas_name in self._owner.gas_names()])

        # Concentration symbols objects.
        self._c_sym = tuple([sym.Symbol('c_' + liquid_name, real=True, positive=True)
                             for liquid_name in self._owner.liquid_names()])

        # Coverage symnols objects.
        # Adsorbates.
        self._ads_theta_sym = tuple([sym.Symbol(r'theta_' + ads_name, real=True, positive=True)
                                     for ads_name in self._owner.adsorbate_names()])

        # Free sites.
        fsite_theta_sym = []
        for site_name in self._owner.site_names():
            total = self._owner.species_definitions()[site_name]['total']
            #free_site_cvg = sym.Symbol(str(total), is_real=True)
            free_site_cvg = total
            for ads_name in self._classified_adsorbates[site_name]:
                free_site_cvg -= self._extract_symbol(sp_name=ads_name,
                                                      symbol_type='ads_cvg')
            fsite_theta_sym.append(free_site_cvg)
        self._fsite_theta_sym = tuple(fsite_theta_sym)

        # Free energies symbols for each species.
        sp_list = self._owner.species_definitions().keys()
        G_sym_list = []
        for idx, sp_name in enumerate(sp_list):
            # Add star symbol.
            if sp_name in self._owner.site_names():
                sp_name = '*_' + sp_name
                sp_list[idx] = sp_name

            G_sym_list.append(sym.Symbol('G_' + sp_name, real=True, positive=True))
        self._G_sym = tuple(G_sym_list)

        # Equilibrium constants(K) symbols for each elementary rxn.
        K_sym_list = []
        for i in xrange(self._rxns_num):
            #subscript = i + 1
            K_sym = sym.Symbol('K_' + str(i), real=True, positive=True)
            K_sym_list.append(K_sym)
        self._K_sym = tuple(K_sym_list)

        self._has_symbols = True

        return
        # }}}

    def _extract_symbol(self, sp_name, symbol_type):
        # {{{
        """
        Protected helper function to get species symbol.

        Parameters:
        -----------
        sp_name: species name, str.

        symbol_type: ['pressure', 'concentration',
                      'ads_cvg', 'free_site_cvg',
                      'free_energy'],

        Returns:
        --------
        Symbol of species.
        """
        # Set species list and symbols tuple.
        if symbol_type == 'pressure':
            sp_list = self._owner.gas_names()
            symbol_tup = self._p_sym
        elif symbol_type == 'concentration':
            sp_list = self._owner.liquid_names()
            symbol_tup = self._c_sym
        elif symbol_type == 'ads_cvg':
            sp_list = self._owner.adsorbate_names()
            symbol_tup = self._ads_theta_sym
        elif symbol_type == 'free_site_cvg':
            sp_list = self._owner.site_names()
            symbol_tup = self._fsite_theta_sym
        elif symbol_type == 'free_energy':
            sp_list = self._owner.species_definitions().keys()
            symbol_tup = self._G_sym
        else:
            msg_template = ("illegal symbol_type. symbol_type must be in {}")
            type_list = ['pressure', 'concentration', 'ads_cvg', 'free_site_cvg', 'free_energy']
            msg = msg_template.format(type_list)
            raise ValueError(msg)

        # Extract corresponding symbol from symbol tuple
        try:
            idx = sp_list.index(sp_name)
        except ValueError:
            msg_template = "species '{}' is not in list '{}'"
            msg = msg_template.format(sp_name, sp_list)
            raise ParameterError(msg)

        return symbol_tup[idx]
        # }}}

    def get_single_barrier_symbols(self, rxn_expression):
        # {{{
        """
        Function to get forward and reverse barrier expression symbols
        for an elementary reaction expression.

        Paramters:
        ----------
        rxn_expression: An elementary reaction expression, str.

        Returns:
        --------
        Barrier expression symbols, tuple of Add objects of Sympy.

        Example:
        --------
        >>> rxn_expression = 'CO_s + O_s <-> CO-O_2s -> CO2_g + 2*_s'
        >>> solver.get_single_barrier_symbols(rxn_expression)
        """
        if not self._has_symbols:
            msg = "Solver has no data symbol, try get_data_symbols() first."
            raise AttributeError(msg)

        # Get formula list.
        rxn_equation = RxnEquation(rxn_expression)
        elementary_rxn_list = rxn_equation.to_formula_list()

        # Get symbols of state energy.
        state_energy_sym_list = []  # list to gather state energy symbols

        for formula_list in elementary_rxn_list:
            state_energy_sym = sym.Symbol('0', is_real=True)
            for formula in formula_list:
                # Split.
                stoichiometry = formula.stoichiometry()
                species = formula.species_site()

                # Empty site.
                if "*" in species:
                    species = formula.site()

                sp_sym = self._extract_symbol(sp_name=species, symbol_type='free_energy')
                if stoichiometry == 1:
                    sp_energy_sym = sp_sym
                else:
                    sp_energy_sym = stoichiometry*sp_sym

                state_energy_sym += sp_energy_sym

            state_energy_sym_list.append(state_energy_sym)

        # Get relative energy expressions.
        is_energy_sym = state_energy_sym_list[0]
        fs_energy_sym = state_energy_sym_list[-1]

        if len(state_energy_sym_list) == 3:
            ts_energy_sym = state_energy_sym_list[1]
        elif len(state_energy_sym_list) == 2:
            # Get TS symbol.
            rxn_idx = self._owner.rxn_expressions().index(rxn_expression)
            dG = self._relative_energies['dG'][rxn_idx]
            ts_idx = 0 if dG < 0 else -1
            ts_energy_sym = state_energy_sym_list[ts_idx]

        Gaf_sym = ts_energy_sym - is_energy_sym
        Gar_sym = ts_energy_sym - fs_energy_sym

        return Gaf_sym, Gar_sym
        # }}}

    @staticmethod
    def get_latex_strs(part1, part2, symbols):
        """
        part1 and part2 are parts of left string in equation string,
        symbols is a iterable object e.g. list or tuple.
        """
        latex_strs = []
        for i, symbol in enumerate(symbols):
            left = part1 + str(i+1) + part2
            right = sym.latex(symbol)
            latex_str = left + ' = ' + right + r'\\' + '\n'
            latex_strs.append(latex_str)

        return tuple(latex_strs)

    def get_barrier_symbols(self, log_latex=False):
        """
        Function to get all barrier expression symbols.
        """
        # Go through all reaction expressions to get symbols of barriers.
        Gaf_syms, Gar_syms = [], []
        for rxn_expression in self._owner.rxn_expressions():
            Gaf_sym, Gar_sym = self.get_single_barrier_symbols(rxn_expression)
            Gaf_syms.append(Gaf_sym)
            Gar_syms.append(Gar_sym)

        # latex strings.
        f_latexs = self.get_latex_strs(part1=r'\Delta G_{', part2=r'+}',
                                       symbols=Gaf_syms)
        r_latexs = self.get_latex_strs(part1=r'\Delta G_{', part2=r'-}',
                                       symbols=Gar_syms)

        if log_latex:
            # Log it.
            self.log_latex(f_latexs)
            self.log_latex(r_latexs)

        return Gaf_syms, Gar_syms

    def get_equilibrium_constant_syms(self):
        """
        Function to get symbols of equilibrium constant.
        """
        # Get rate constant symbols
        kf_syms, kr_syms = self.get_rate_constant_syms()
        K_syms = []

        for kf_sym, kr_sym in zip(kf_syms, kr_syms):
            K_sym = kf_sym/kr_sym
            K_syms.append(K_sym)

        K_syms = tuple(K_syms)

        return K_syms

    def get_rate_constant_syms(self):
        """
        Fucntion to get rate constant expression symbols.
        """
        # Go through rxn expressions to get symbols of rate constants.
        kB, h, T = self._kB_sym, self._h_sym, self._T_sym
        kf_syms, kr_syms = [], []

        for idx, rxn_expression in enumerate(self._owner.rxn_expressions()):
            Gaf_syms, Gar_syms = self.get_barrier_symbols()

            Gaf = Gaf_syms[idx]
            kf_sym = kB*T/h*sym.E**(-Gaf/(kB*T))
            kf_syms.append(kf_sym)

            Gar = Gar_syms[idx]
            kr_sym = kB*T/h*sym.E**(-Gar/(kB*T))
            kr_syms.append(kr_sym)

        return kf_syms, kr_syms

    def get_single_rate_sym(self, rxn_expression):
        """
        Expect a elementary_rxn_list e.g.
        [['HCOOH_s', '*_s'], ['HCO-OH_s', '*_s'], ['HCO_s', 'OH_s']]

        return corresponding forward rate and reverse rate symbols.
        e.g. [T*kB*theta_HCOOH_s*(1 - theta_CO_s - theta_H2O_s - theta_HCOOH_s -
              theta_HCO_s - theta_H_s - theta_OH_s)*
              exp((-G_HCO-OH_s + G_HCOOH_s)/(T*kB))/h,

              T*kB*theta_HCO_s*theta_OH_s*
              exp((-G_*_s - G_HCO-OH_s + G_HCO_s + G_OH_s)/(T*kB))/h]
        """
        # Get expression index.
        rxn_idx = self._owner.rxn_expressions().index(rxn_expression)

        # Get rate constant symbols.
        kf_syms, kr_syms = self.get_rate_constant_syms()
        k_syms = (kf_syms[rxn_idx], kr_syms[rxn_idx])

        # Get formula list.
        rxn_equation = RxnEquation(rxn_expression)
        elementary_rxn_list = rxn_equation.to_formula_list()

        rate_syms = []

        # IS and FS.
        for i in [0, -1]:
            rate_sym = k_syms[i]

            # Each formula in state.
            for formula in elementary_rxn_list[i]:
                # Split.
                stoichiometry = formula.stoichiometry()
                species_site = formula.species_site()

                # Get species name and type.
                if '*' in species_site:
                    species_name = formula.site()
                    sp_type = 'site'
                else:
                    species_name = species_site
                    sp_type = formula.type()

                # Set symbol_type.
                if sp_type == 'gas':
                    symbol_type = 'pressure'
                elif sp_type == 'liquid':
                    symbol_type = 'concentration'
                elif sp_type == 'site':
                    symbol_type = 'free_site_cvg'
                else:
                    symbol_type = 'ads_cvg'

                sp_data_sym = self._extract_symbol(species_name, symbol_type)
                rate_sym *= sp_data_sym**stoichiometry
            rate_syms.append(rate_sym)

        return tuple(rate_syms)

    def get_rate_syms(self, log_latex=False):
        rf_syms, rr_syms = [], []
        for elementary_rxn_list in self._owner.elementary_rxns_list():
            rf_sym, rr_sym = self.get_single_rate_sym(elementary_rxn_list)
            rf_syms.append(rf_sym)
            rr_syms.append(rr_sym)

        self.rf_syms = rf_syms
        self.rr_syms = rr_syms

        #latex strings
        rf_latexs = self.get_latex_strs(part1=r'r_{f', part2=r'^{+}}',
                                        symbols=rf_syms)
        rr_latexs = self.get_latex_strs(part1=r'r_{r', part2=r'^{-}}',
                                        symbols=rf_syms)
        self.r_latex = (tuple(rf_latexs), tuple(rr_latexs))

        if log_latex:
            #log it
            self.log_latex(rf_latexs)
            self.log_latex(rr_latexs)

        return rf_syms, rr_syms

    def get_subs_dict(self, **kwargs):
        "get substitution dict(e.g. G, theta, p, constants dicts)."
        #free energy substitution dict
        G_subs_dict = self.get_G_subs_dict()
        #coverage substitution dict
        if 'cvgs_tuple' in kwargs:
            theta_subs_dict = self.get_theta_subs_dict(kwargs['cvgs_tuple'])
        #pressure substitution dict
        p_subs_dict = self.get_p_subs_dict()
        #concentration substution dict
        c_subs_dict = self.get_c_subs_dict()
        #constants substitution dict
        constants_subs_dict = self._constants_subs_dict
        #get dicts list
        if 'cvgs_tuple' in kwargs:
            dicts_list = [G_subs_dict, theta_subs_dict, constants_subs_dict,
                          p_subs_dict, c_subs_dict]
        else:
            dicts_list = [G_subs_dict, constants_subs_dict,
                          p_subs_dict, c_subs_dict]

        #merge dicts
        subs_dict = {}
        for dic in dicts_list:
            subs_dict = dict(subs_dict, **dic)

        return subs_dict

    def get_rate_constants_by_sym(self):
        """
        Calculate rate constants values
        by back substitution to symbol expressions.
        """
        if not hasattr(self, 'kf_syms') or not hasattr(self, 'kr_syms'):
            self.get_rate_constant_syms()
        #get substitution dict(need G_dict and constants dict)
        subs_dict = self.get_subs_dict()

        kfs, krs = [], []
        #calculate kfs
        for kf_sym in self.kf_syms:
            kf = self._mpf(kf_sym.evalf(subs=subs_dict))
            kfs.append(kf)
        #krs
        for kr_sym in self.kr_syms:
            kr = self._mpf(kr_sym.evalf(subs=subs_dict))
            krs.append(kr)

        self.kfs, self.krs = tuple(kfs), tuple(krs)

        return kfs, krs

    def get_rates_by_sym(self, cvgs_tuple):
        """
        Expect a coverages tuple, and then calculate rates values
        by back substitution to symbol expressions,
        return rfs, rrs
        """
        if not hasattr(self, 'rf_syms') or not hasattr(self, 'rr_syms'):
            self.get_rate_syms()
        #get substitution dict(need G, theta, p, constants dicts)
        subs_dict = self.get_subs_dict(cvgs_tuple=cvgs_tuple)
        #calculate rfs
        rfs, rrs = [], []
        for rf_sym in self.rf_syms:
            rf = self._mpf(float(rf_sym.evalf(subs=subs_dict)))
            rfs.append(rf)
        #cal rrs
        for rr_sym in self.rr_syms:
            rr = self._mpf(float(rr_sym.evalf(subs=subs_dict)))
            rrs.append(rr)

        self.rfs, self.rrs = tuple(rfs), tuple(rrs)

        self.archive_data('rates', (self.rfs, self.rrs))

        return tuple(rfs), tuple(rrs)

    def get_G_subs_dict(self):
        "Get values from solver's data dict."
        #get value dict for solver
        if not self._has_absolute_energy:
            self.get_data()
        if not self._has_absolute_energy:
            raise IOError('No absolute energies read, ' +
                          'could not get substitution dictionary for G symbol.')
        #free energy value dict
        G_dict = {}
        for idx, sp_name in enumerate(self.sp_list):
            G_dict.setdefault(self._G_sym[idx], self.E[sp_name])

        return G_dict

    def get_theta_subs_dict(self, cvgs_tuple):
        theta_dict = {}
        for idx, ads_name in enumerate(self._owner.adsorbate_names()):
            theta_dict.setdefault(self._ads_theta_sym[idx], cvgs_tuple[idx])

        return theta_dict

    def get_p_subs_dict(self):
        "Get values from solver's data dict."
        p_dict = {}
        for idx, gas_name in enumerate(self._owner.gas_names()):
            p_dict.setdefault(self._p_sym[idx], self.p[gas_name])

        return p_dict

    def get_c_subs_dict(self):
        "Get values from solver's data dict."
        c_dict = {}
        for idx, liquid_name in enumerate(self._owner.liquid_names()):
            c_dict.setdefault(self._c_sym[idx], self.c[liquid_name])

        return c_dict

    def get_net_rate_syms(self):
        "Go through rfs and rrs, to get net rate symbolic expressions."
        if not hasattr(self, 'rfs_syms') or not hasattr(self, 'rrs_syms'):
            self.get_rate_syms()
        net_rate_syms = []
        for rf_sym, rr_sym in zip(self.rf_syms, self.rr_syms):
            net_rate_sym = rf_sym - rr_sym
            net_rate_syms.append(net_rate_sym)

        self.net_rate_syms = tuple(net_rate_syms)

        return tuple(net_rate_syms)

    def get_net_rates_by_sym(self, cvgs_tuple):
        if not hasattr(self, 'net_rate_syms'):
            self.get_net_rate_syms()
        #get substitution dict
        subs_dict = self.get_subs_dict(cvgs_tuple=cvgs_tuple)
        net_rate_syms_vect = sym.Matrix(self.net_rate_syms)  # col vect
        #back substitution
        net_rates_vect = net_rate_syms_vect.evalf(subs=subs_dict)
        #keep precision
        net_rates_vect = [self._mpf(float(net_rate))
                          for net_rate in net_rates_vect]

        net_rates_tup = tuple(net_rates_vect)
        #archive
        self.archive_data('net_rates', net_rates_tup)

        return net_rates_tup

    def get_tof_syms(self):
        "Return a tuple containing turnover frequencies of gases."
        #get gas coefficients matrix
        if hasattr(self._owner, 'gas_matrix'):
            gas_matrix = self._owner.gas_matrix
        else:
            gas_matrix = \
                self._owner.parser().get_stoichiometry_matrices()[1]
        gas_matrix = -sym.Matrix(gas_matrix)
        #get net rates symbolic expressions vector
        if not hasattr(self, 'net_rate_syms'):
            self.get_net_rate_syms()
        rate_syms_vect = \
            sym.Matrix(self.get_net_rate_syms()).transpose()  # row vector
        #get tof symbolic expression vector(row vector)
        tof_vect = rate_syms_vect*gas_matrix

        tof_tup = tuple(tof_vect)

        return tof_tup

    def get_tof_by_sym(self, cvgs_tuple):
        "Expect a coverage tuple, return a tuple of TOFs."
        tof_syms_vect = sym.Matrix(self.get_tof_syms())
        subs_dict = self.get_subs_dict(cvgs_tuple=cvgs_tuple)
        tof_vect = tof_syms_vect.evalf(subs=subs_dict)
        #keep precision
        tof_vect = [self._mpf(float(tof)) for tof in tof_vect]

        # log TOFs
        self.log_tof(tof_vect, self._owner.gas_names())

        return tuple(tof_vect)

    ###### calculate micro kinetic model with Sympy END ######

    def has_absolute_energy(self):
        """
        Query function for has_absolute_energy flag.
        """
        return self._has_absolute_energy

    def has_relative_energy(self):
        """
        Query function for has_relative_energy flag.
        """
        return self._has_relative_energy

    def has_energy_correction(self):
        """
        Query function for has energy correction flag.
        """
        return self._has_energy_correction

    def has_symbols(self):
        """
        Query function for has symbol flag.
        """
        return self._has_symbols

    @return_deepcopy
    def classified_adsorbates(self):
        """
        Query function for classified adsorbates.
        """
        return self._classified_adsorbates

    @return_deepcopy
    def pressures(self):
        """
        Query function for gas pressures.
        """
        return self._p

    @return_deepcopy
    def concentrations(self):
        """
        Query function for liquid concentrations.
        """
        return self._c

    @return_deepcopy
    def formation_energies(self):
        """
        Query function for formation energies.
        """
        return self._G

    @return_deepcopy
    def relative_energies(self):
        """
        Query function for relative energies.
        """
        return self._relative_energies

    def rate_expressions(self):
        """
        Query functions for rate expressions for all elementary reactions.
        """
        return self._rate_expressions


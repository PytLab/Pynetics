from solver_base import *
import sympy as sym
import copy


class QuasiEquilibriumSolver(SolverBase):
    def __init__(self, owner):
        SolverBase.__init__(self, owner)

        #set default parameter dict
        defaults = dict(
            RDS=2,  # rate determining step number
            )
        defaults = self.update_defaults(defaults)
        self.__dict__.update(defaults)

        #update quasi_equilibrium_solver's own logger template
        self.logger_template_dict = {}
        self.logger._templates_dict.update(self.logger_template_dict)

        #species names that has been represented by theta*
        self.represented_species = []

    def get_tof_sym(self):
        """
        Return complete analytical expression of rate of RDS.
        """
        #refresh self.represented_species
        self.represented_species = []
        #operate copy later
        rxns_list_copy = copy.copy(self.rxns_list)
        Ks_list_copy = list(copy.copy(self.K_sym))
        #remove rate determinating step
        RDS_rxn_list = rxns_list_copy[self.RDS]
        rxns_list_copy.remove(RDS_rxn_list)
        #remove rate determinating step's K
        RDS_K = Ks_list_copy[self.RDS]
        Ks_list_copy.remove(RDS_K)
        #create a free site theta symbol used in all rxns
        theta_f = sym.Symbol('theta_f', positive=True, real=True)
        syms_sum = 0  # sum expression of all adsorbates' thetas
        self.eq_dict = {}  # substitution dict for symbols
        rxns_num = len(self.rxns_list)

        loop_counter = 0
        while rxns_list_copy:
            loop_counter += 1
#            print rxns_list_copy
            origin_num = len(rxns_list_copy)  # number of rxns

            for K_sym, rxn_list in zip(Ks_list_copy, rxns_list_copy):
#                print Ks_list_copy
                #get adsorbate name that will be represented
                target_adsorbate = self.check_repr(rxn_list)

                if target_adsorbate and target_adsorbate != 'all_represented':
                    #get target adsorbate theta symbol
                    theta_target = self.extract_symbol(target_adsorbate, 'ads_cvg')
                    #represented by theta_f
                    theta_target_subs = self.represent(rxn_list, target_adsorbate,
                                                       theta_f, K_sym)
#                    print theta_target_subs
                    theta_target_subs = theta_target_subs.subs(self.eq_dict)
#                    print theta_target_subs

                    #add it to self.eq_dict
                    if theta_target in self.eq_dict:
                        self.eq_dict[theta_target] = theta_target_subs
                    else:
                        self.eq_dict.setdefault(theta_target, theta_target_subs)

                    rxns_list_copy.remove(rxn_list)
                    Ks_list_copy.remove(K_sym)
                    #add this good species name to self.represented_species
                    self.represented_species.append(target_adsorbate)
                    #add theta to sym_sum
                    syms_sum += theta_target_subs
                elif target_adsorbate and target_adsorbate == 'all_represented':
                    #just remove it
                    rxns_list_copy.remove(rxn_list)
                    Ks_list_copy.remove(K_sym)
                else:
                    #move the rxn_list to the end of rxns_list_copy
                    rxns_list_copy.remove(rxn_list)  # remove it
                    rxns_list_copy.append(rxn_list)  # insert to the end
                    #move the K_sym to the end of Ks_list_copy
                    Ks_list_copy.remove(K_sym)  # remove it
                    Ks_list_copy.append(K_sym)  # insert to the end

            remaining_num = len(rxns_list_copy)  # number of rxn remaining in list

            if remaining_num == origin_num and loop_counter > rxns_num:
                #insert K for merged rxn list to head of Ks_list_copy
                merged_K = self.get_merged_K(rxns_list_copy)
                Ks_list_copy.insert(0, merged_K)
                #merge all remaining elementary_rxn lists
                merged_rxn_list = \
                    self._owner.parser.merge_elementary_rxn_list(*rxns_list_copy)
                #insert new merged list to the head of rxns_list_copy
                rxns_list_copy.insert(0, merged_rxn_list)

        #get theta_f expression
#        print syms_sum
        normalization_expr = syms_sum + theta_f - 1
        theta_f_expr = sym.solve(normalization_expr, theta_f, check=0)[0]
#        print theta_f_expr

        #get complete equivalent dict
        complete_eq_dict = self.get_complete_eq_dict(theta_f, theta_f_expr)
#        print complete_eq_dict
        #get net rate of rate determinating step
        if not hasattr(self, 'net_rate_syms'):
            self.get_net_rate_syms()
        tof_sym = self.net_rate_syms[self.RDS]
        #substitute thetas of adsorbates
        complete_tof_sym = tof_sym.subs(complete_eq_dict)
        #substitute again to subs Ks in complete_eq_dict itself!
        #e.g. complete_eq_dict[theta_H_s]
        complete_tof_sym = complete_tof_sym.subs(complete_eq_dict)

        return complete_tof_sym

    def get_merged_K(self, rxns_list):
        merged_K = 1
        for rxn_list in rxns_list:
            #get index
            idx = self.rxns_list.index(rxn_list)
            #get corresponding K
            K = self.K_sym[idx]
            merged_K *= K
        return merged_K

    def get_complete_eq_dict(self, theta_f, theta_f_expr):
        "substitute theta_f and K, to get complete equivalent dict."
        #check number of elements in eq_dict
        ads_num = len(self._owner.adsorbate_names)
        if len(self.eq_dict) != ads_num:
            raise ValueError('eq_dict is illegal.')
        for ads_sym in self.eq_dict:
            self.eq_dict[ads_sym] = \
                self.eq_dict[ads_sym].subs({theta_f: theta_f_expr})
        #get equilibrium constant subs dict
        if not hasattr(self, 'K_expr_syms'):
            self.get_K_syms()
        K_subs_dict = {}
        for i, K_sym in enumerate(self.K_sym):
            K_subs_dict.setdefault(K_sym, self.K_expr_syms[i])

        #merge two dicts
        self.eq_dict = dict(self.eq_dict, **K_subs_dict)

        return self.eq_dict  # Note: K still in it!

    def represent(self, rxn_list, target_adsorbate, theta_f, K):
        """
        Expect a rxn_list which can be represented by theta_f,
        return the symbol expression of theta_target_adsorbate.

        Parameters
        ----------
        rxn_list : list of states
            e.g. [['*_s', 'HCOOH_g'], ['HCOOH_s']]
        target_adsorbate : str
            adsorbate_name which will be represented
        theta_f : sympy.core.symbol.Symbol
            coverage of free sites
        """
        left_syms, right_syms = [], []  # syms to be multipled later

        #go thtough rxn_list's head and tail
        ends_list = [rxn_list[0], rxn_list[-1]]
        for state_idx, state_list in enumerate(ends_list):
            #go through sp_list to locate theta
            for sp_str in state_list:
                stoichiometry, species_name = self.split_species(sp_str)
                #free site
                if '*' in species_name:
                    # get location of theta_f
                    if state_idx == 0:
                        theta_f_loc = 'left'
                    else:
                        theta_f_loc = 'right'
                    #add exponential
                    theta_f_term = theta_f**stoichiometry
                #target species theta
                elif species_name == target_adsorbate:
                    # get location of theta_target_ads
                    if state_idx == 0:
                        theta_t_loc = 'left'
                    else:
                        theta_t_loc = 'right'
                    #get theta_t term exponential
                    theta_t_exp = stoichiometry
                #represented adsorbate
                elif species_name in self._owner.adsorbate_names:
                    #extract symbol of the adsorbate
                    theta_sym = self.extract_symbol(species_name, 'ads_cvg')
                    #add exponential
                    theta_sym_term = theta_sym**stoichiometry
                    #get location of theta represented already
                    if state_idx == 0:
                        left_syms.append(theta_sym_term)
                    else:
                        right_syms.append(theta_sym_term)
                #gas pressure
                elif species_name in self._owner.gas_names:
                    p_sym = self.extract_symbol(species_name, 'pressure')
                    #add exponential
                    p_sym_term = p_sym**stoichiometry
                    if state_idx == 0:
                        left_syms.append(p_sym_term)
                    else:
                        right_syms.append(p_sym_term)

        #use theta_f to represent theta_target_adsorbate
        '''
        --------------------------------------------------------------------------
        |theta_* location | theta_t_loc | theta_t expression without exponential |
        --------------------------------------------------------------------------
        |    left         |    left     |            R/(K*L*theta_f_term)        |
        --------------------------------------------------------------------------
        |    left         |    right    |            K*L*theta_f_term/R          |
        --------------------------------------------------------------------------
        |    right        |    left     |            R*theta_f_term/(L*K)        |
        --------------------------------------------------------------------------
        |    right        |    right    |            K*L/(R*theta_f_term)        |
        --------------------------------------------------------------------------
        '''
        def get_multi_sym_list(syms_list):
            multi_sym = 1
            for symbol in syms_list:
                multi_sym *= symbol
            return multi_sym

        L = get_multi_sym_list(left_syms)  # left multipled symbols
        R = get_multi_sym_list(right_syms)  # right multipled symbols
        total_exp = 1.0/theta_t_exp

        if theta_f_loc == 'left' and theta_t_loc == 'left':
            theta_t = (R/(K*L*theta_f_term))**total_exp
        elif theta_f_loc == 'left' and theta_t_loc == 'right':
            theta_t = (K*L*theta_f_term/R)**total_exp
        elif theta_f_loc == 'right' and theta_t_loc == 'left':
            theta_t = (R*theta_f_term/(L*K))**total_exp
        elif theta_f_loc == 'right' and theta_t_loc == 'right':
            theta_t = (K*L/(R*theta_f_term))**total_exp

        return theta_t

    def check_repr(self, rxn_list):
        """
        Expect a rxn_list, e.g. [['*_s', 'HCOOH_g'], ['HCOOH_s']].
        Check if there is only one adsorbate cvg
        that can be represented by cvg of free site theta_f.

        e.g. [['*_s', 'HCOOH_g'], ['HCOOH_s']] is good, return 'HCOOH_s'
        [['HCOOH_s', '*_s'], ['H-COOH_s', '*_s'], ['COOH_s', 'H_s']] not,
        return None.
        """
        #merge IS and FS sp_list
        merged_list = rxn_list[0] + rxn_list[-1]
        #initial number of theta that hasn't been represented by theta_*
        free_num = 0
        #adsorbate name that will be archived in loop
        archived_ads = ''
        for sp_str in merged_list:
            stoichiometry, species_name = self.split_species(sp_str)
            if (species_name in self._owner.adsorbate_names and
                    species_name not in self.represented_species):
                free_num += 1
                archived_ads = species_name

        if free_num == 1:
            return archived_ads
        elif free_num == 0:
            return 'all_represented'
        else:
            return

    def get_XTRC(self, intermediate_name):
        r = self.get_tof_sym()  # tof symbol expression
        G = self.extract_symbol(intermediate_name, 'free_energy')  # free energy symbol
        k_B, T = self.k_B_sym, self.T_sym
        XTRC = -k_B*T/r*(sym.Derivative(r, G).doit())

        subs_dict = self.get_subs_dict()
        XTRC_value = XTRC.evalf(subs=subs_dict)

        return XTRC_value

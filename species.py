#!/usr/bin/env python3

import cantera as ct
import copy
import math
from typing import List, Optional, Tuple

class OldSpecies:
    def __init__(self):
        pass

class OldMixture:
    def __init__(self):
        pass

class LatentHeat:
    """
    Latent heat required for a phase change. Typically melting or boiling.
    """

    def __init__(self, T: float, latent_heat: float):
        """
        Args:
            T (float): Temperature that the phase change occurs [K]
            latent_heat (float): Latent heat [J/mol]
        """
        self._T = T
        self._latent_heat = latent_heat

    def __repr__(self):
        return f"LatentHeat({self._T} K, {self._latent_heat} J/mol)"

    @property
    def T(self) -> float:
        """
        Temperature [K]
        """
        return self._T

    @property
    def latent_heat(self) -> float:
        """
        Latent heat [J/mol]
        """
        return self._latent_heat


class Species:
    """
    The Species class represents an amount of a substance / solution.
    It stores the thermodynamic phase data and the amount of a substance.
    As implemented right now, it is essentially a wrapper class around the
    Cantera.Quantity class, but with optionally additional latent heat and
    heat of formation data option.
    """

    gas_data = {s.name: s for s in ct.Species.list_from_file('nasa_gas.yaml')}
    condensed_data = {s.name: s for s in ct.Species.list_from_file('nasa_condensed.yaml')}

    def __init__(self, name: str, quantity: ct.Quantity, latent_heats: Optional[List[LatentHeat]]=None,
                 delta_h_formation: Optional[float]=None):
        """
        Args:
            name: The name of the species, typically the chemical formula
            quantity: The cantera quantity containing phase data and the amount of the species
            latent_heats: The latent heat of any phase changes between the temperature that the
                species exists and 298.15 K, assuming atmospheric pressure. Only include this
                 if the Cp data does not extend to 298.15 [J/mol]
            delta_h_formation: The enthalpy of formation at standard conditions 298.15 K, one
                atmospheric pressure. [J/mol]
        """
        self._name = name
        self._quantity = quantity
        self._latent_heats = [] if latent_heats is None else latent_heats
        self._delta_h_formation = delta_h_formation

    def __repr__(self):
        return f"Species({self._name} K, {self._quantity.mass} kg)"

    def quantity_from_database_name(name: str, mass: Optional[float] = None,
                                    moles: Optional[float] = None) -> ct.Quantity:
        """
        Attempts to find a phase with the given name in the available databases (nasa_gas.yaml
        and nasa_condensed.yaml). Creates the ct.Quantity object if it exists.

        Args:
            name: The name of the phase, as it appears in the database
            mass: The mass of the quantity [kg]
            moles: The moles of the quantity [moles]

        Raises:
            ValueError: if the name of the species does not exist in the known databases, or
                        if neither mass nor moles are given.
        """

        if name in Species.gas_data:
            solution_data = ct.Solution(thermo='ideal-gas', species=[Species.gas_data[name]])
            solution_data.TPX = 298.15, ct.one_atm, f'{name}:1.0'
        elif name in Species.condensed_data:
            solution_data = ct.Solution(thermo='fixed-stoichiometry', species=[Species.condensed_data[name]])
            solution_data.TPX = 298.15, ct.one_atm, f'{name}:1.0'
        else:
            raise ValueError(f'No such species {name} in available databases.')

        if moles is not None:
            quantity = ct.Quantity(solution_data, moles=moles)
        elif mass is not None:
            quantity = ct.Quantity(solution_data, mass=mass)
        else:
            raise ValueError(f'No mass or mole value provided for {name}')

        return quantity

    @property
    def T(self) -> float:
        """
        Temperature [K]
        """
        return self._quantity.T

    @T.setter
    def T(self, val: float):
        self._quantity.TP = val, self.P

    @property
    def P(self) -> float:
        """
        Pressure [Pa]
        """
        return self._quantity.P

    @property
    def TP(self) -> Tuple[float, float]:
        return self._quantity.TP

    @TP.setter
    def TP(self, tp: Tuple[float, float]):
        self._quantity.TP = tp

    @property
    def H(self) -> float:
        """
        Enthalpy change relative to standard conditions (298K, 1 bar) [J]
        """
        return self._quantity.H

    @property
    def mm(self) -> float:
        """
        The molecular mass [kg / mol]
        """
        return self._quantity.mean_molecular_weight * 0.001

    def cp(self, molar_cp:bool =True) -> float:
        """
        The molar heat capacity.

        Args:
            molar_cp: When true returns molar heat capacity [J / mol K]
                When false, returns specific heat capacity [J / kg K]
        """
        return self._quantity.cp_mole * 0.001 if molar_cp else self._quantity.cp_mass


class Mixture:
    """
    The Mixture class stores one or more Species objects. Should always use
    a Mixture in the mass and energy flow simulation, even when transporting
    a simple Species.
    """
    def __init__(self, name: str, species: Optional[List[Species]] = None):
        self._name = name
        self._species = [] if species is None else species

    def __repr__(self):
            s = f"Mixture({self._name} K"
            for species in self._species:
                s += f", {species}"
            s += ")"
            return s

    @property
    def T(self) -> float:
        """
        Temperature [K]

        raises:
            Exception: If no species are in the mixture, or if not all the temperatures
                of the individual species are the same.
        """
        num_species = len(self._species)
        if num_species == 0:
            raise Exception('Could not retrieve temperature. Empty Mixture')
        elif num_species == 1:
            return self._species[0].T

        temps = [s.T for s in self._species]
        for i in range(num_species - 1):
            if not math.isclose(self._species[i].T, self._species[i+1].T):
                raise Exception('Could not retrieve temperature. Species in the Mixture have different temperatures')
        return temps[0]

    @T.setter
    def T(self, val: float):
        for species in self._species:
            species.T = val

    @property
    def mm(self) -> float:
        """
        The molecular mass [kg / mol]

        raises:
            Exception: There is more or less than exactly one species in the mixture.
        """
        if len(self._species) != 1:
            raise Exception(f'Could not retrieve molar mass. Expected 1 species, not {len(self._species)}.')

        return self._species[0].mm

    def cp(self, molar_cp:bool =True) -> float:
        """
        The molar heat capacity.

        Args:
            molar_cp: When true returns molar heat capacity [J / mol K]
                When false, returns specific heat capacity [J / kg K]
        raises:
            Exception: There is more or less than exactly one species in the mixture.
        """
        if len(self._species) != 1:
            raise Exception(f'Could not retrieve heat capacity. Expected 1 species, not {len(self._species)}.')

        return self._species[0].cp(molar_cp)



# Species - Master copies
# Unless otherwise stated, thermodynamic data is obtained from the following sources:
# Heat capacity data is provided by the nasa gas and nasa condensed databases, provided through cantera
# Latent Heat Data is from the CRC Handbook of Chemistry and Physics, Enthalpy of Fusion, 6-146
# Enthalpy of Formation data is from the CRC Handbook of Chemistry and Physics, Enthalpy of Formation, 5-1,
# and checked against the NIST webbook.
def create_dummy_mixture(name):
    return Mixture(name)

def create_h2_mixture():
    name = 'H2'
    quantity = Species.quantity_from_database_name(name, moles=0.0)
    species = Species(name,
                      quantity,
                      delta_h_formation=0.0)
    return Mixture(name, [species])

def create_o2_mixture():
    name = 'O2'
    quantity = Species.quantity_from_database_name(name, moles=0.0)
    species = Species(name,
                      quantity,
                      delta_h_formation=0.0)
    return Mixture(name, [species])

def create_h2o_g_mixture():
    name = 'H2O'
    quantity = Species.quantity_from_database_name(name, moles=0.0)
    species = Species(name,
                     quantity,
                     delta_h_formation=-241.83e3)
    return Mixture(name, [species])

def create_h2o_l_mixture():
    name = 'H2O(L)'
    quantity = Species.quantity_from_database_name(name, moles=0.0)
    species = Species(name,
                     quantity,
                     delta_h_formation=-285.83e3)
    return Mixture(name, [species])

def create_n2_species():
    heat_capacities = [ShomateEquation(100.0, 500.0,
                                            (28.98641, 1.853978, -9.647459,
                                             16.63537, 0.000117, -8.671914, 226.4168, 0.0)), 
                            ShomateEquation(500.0, 2000.0,
                                            (19.50583, 19.88705, -8.598535, 
                                             1.369784, 0.527601, -4.935202, 212.3900, 0.0)),
                            ShomateEquation(2000.0, 6000.0,
                                            (35.51872, 1.128728, -0.196103, 
                                             0.014662, -4.553760, -18.97091, 224.9810, 0.0))]
    thermo_data = ThermoData(heat_capacities)
    species = OldSpecies('N2',
                         0.0280134,
                         thermo_data)
    return species

def create_ar_species():
    heat_capacities = [SimpleHeatCapacity(273.15, 6000, 20.786)]
    thermo_data = ThermoData(heat_capacities)
    species = OldSpecies('Ar',
                         0.039948,
                         thermo_data)
    return species

def create_fe_species():
    # NIST data is very conflicting for iron. 
    # Using simplified data
    heat_capacities = [SimpleHeatCapacity(273.15, 298.0, 25.09),
                        ShomateEquation(298.0, 1809.0,
                                       (23.97449, 8.367750, 0.000277,
                                        -0.000086, -0.000005, 0.268027, 62.06336, 7.788015)),
                       SimpleHeatCapacity(1809.0, 3133.345, 46.02400)]
    latent_heats = [LatentHeat(1811.15, 13810.0)]
    thermo_data = ThermoData(heat_capacities, latent_heats)
    species = OldSpecies('Fe',
                         0.055845,
                         thermo_data,
                         0.0)
    return species

def create_feo_species():
    fe = create_fe_species()
    o2 = create_o2_species()

    heat_capacities = [SimpleHeatCapacity(273.15, 298.0, 49.93),
                        ShomateEquation(298.0, 1650.0, 
                                        (45.75120, 18.78553, -5.952201,
                                         0.852779, -0.081265, -286.7429, 110.3120, -272.0441)),
                        ShomateEquation(1650, 5000, 
                                           (68.19920, 0.0, 0.0, 0.0, 0.0, 
                                            -281.4326, 137.8377, -249.5321))
    ]
    latent_heats = [LatentHeat(1650.15, 24100.0)]
    thermo_data = ThermoData(heat_capacities, latent_heats)
    species = OldSpecies('FeO',
                         fe.mm + o2.mm * 0.5,
                         thermo_data,
                         -272.0e3)
    return species

def create_fe3o4_species():
    fe = create_fe_species()
    o2 = create_o2_species()

    # Plot of the ShomateEquations seems weird, but will run with it.
    heat_capacities = [SimpleHeatCapacity(273.15, 298.0, 147.183),
                        ShomateEquation(298, 900.0, 
                                        (104.2096, 178.5108, 10.61510,
                                         1.132534, -0.994202, -1163.336, 
                                         212.0585, -1120.894)),
                        SimpleHeatCapacity(900.0, 3000.1, 200.823)
    ]
    latent_heats = [LatentHeat(1870.15, 138000)]
    thermo_data = ThermoData(heat_capacities, latent_heats)
    species = OldSpecies('Fe3O4',
                         fe.mm * 3 + o2.mm * 2.0,
                         thermo_data,
                         -1118.4e3)
    return species

def create_fe2o3_species():
    fe = create_fe_species()
    o2 = create_o2_species()

    heat_capacities = [SimpleHeatCapacity(273.15, 298.0, 103.7443),
                        ShomateEquation(298.0, 950.0, 
                                        (93.43834, 108.3577, -50.86447,
                                         25.58683, -1.611330, -863.2094, 
                                         161.0719, -825.5032)),
                        SimpleHeatCapacity(950.0, 1050, 150.6240),
                        ShomateEquation(1050.0, 3000.1, # max was 2500, but extending to 3000k
                                        (110.9362, 32.04714, -9.192333,
                                         0.901506, 5.433677, -843.1471, 
                                         228.3548, -825.5032))
    ]
    latent_heats = [LatentHeat(1838.15, 87000)]
    thermo_data = ThermoData(heat_capacities, latent_heats)
    species = OldSpecies('Fe2O3',
                         fe.mm * 2 + o2.mm * 1.5,
                         thermo_data,
                         -824.2e3)
    return species

def create_c_species():
    heat_capacities = [SimpleHeatCapacity(273.15, 3000.1, 10.68)] # simplified, but not a large input material
    thermo_data = ThermoData(heat_capacities)
    species = OldSpecies('C',
                         0.012011,
                         thermo_data,
                         0.0) # graphite enthalpy of formation
    return species

def create_co_species():
    c = create_c_species()
    o2 = create_o2_species()

    heat_capacities = [SimpleHeatCapacity(273.15, 298.0, 29.15),
                        ShomateEquation(298.0, 1300.0,
                                        (25.56759, 6.096130, 4.054656,
                                        -2.671301, 0.131021, -118.0089,
                                        227.3665, -110.5271)),
                        ShomateEquation(1300.0, 6000.0,
                                        (35.15070, 1.300095, -0.205921,
                                        0.013550, -3.282780, -127.8375,
                                        231.7120, -110.5271))]
    thermo_data = ThermoData(heat_capacities)
    species = OldSpecies('CO',
                         c.mm + o2.mm * 0.5,
                         thermo_data,
                         -110.53e3)
    return species

def create_co2_species():
    c = create_c_species()
    o2 = create_o2_species()

    heat_capacities = [ShomateEquation(273.15, 1200.0, 
                                       (24.99735, 55.18696, 55.18696,
                                        -33.69137, 7.948387, -0.136638,
                                        -403.6075, 228.2431)),
                        ShomateEquation(1200.0, 6000.0,
                                        (58.16639, 2.720074, -0.492289,
                                            0.038844, -6.447293, -425.9186,
                                            263.6125, -393.5224))]
    thermo_data = ThermoData(heat_capacities)
    species = OldSpecies('CO2',
                         c.mm + o2.mm,
                         thermo_data,
                         -393.51e3)
    return species

def create_al2o3_species():
    heat_capacities = [SimpleHeatCapacity(273.15, 298.0, 81.0885),
                        ShomateEquation(298.0, 2327.0, 
                                        (106.9180, 36.62190, -13.97590,
                                         2.157990, -3.157761, -1710.500,
                                         151.7920, -1666.490)),
                        SimpleHeatCapacity(2327.0, 4000.0, 
                                           (192.4640, 0.0, 0.0, 0.0, 0.0,
                                            -1773.50, 177.1008, -1620.568))]
    # Adding flux should reduce the melting point. Possibly effect
    # the latent heat value as well?
    latent_heats = [LatentHeat(2345.15, 111100)]
    thermo_data = ThermoData(heat_capacities, latent_heats)
    species = OldSpecies('Al2O3',
                         0.101961,
                         thermo_data)
    return species

def create_si_species():
    heat_capacities = [SimpleHeatCapacity(273.15, 298.0, 44.57),
                        ShomateEquation(298.0, 1685.0,
                                        (22.81719, 3.899510, -0.082885,
                                        0.042111, -0.354063, -8.163946,
                                        43.27846, 0.000000)),
                        SimpleHeatCapacity(1685.0, 3504.616, 27.19604)

    ]
    latent_heats = [LatentHeat(1414.0, 50210)]
    thermo_data = ThermoData(heat_capacities, latent_heats)
    species = OldSpecies('Si',
                         0.0280855,
                         thermo_data,
                         0)
    return species

def create_sio2_species():
    heat_capacities = [SimpleHeatCapacity(273.15, 298.0, 44.57),
                        ShomateEquation(298.0, 847.0,
                                        (-6.076591, 251.6755, -324.7964,
                                            168.5604, 0.002548, -917.6893,
                                            -27.96962, -910.8568)),
                        ShomateEquation(847.0, 1996.0,
                                        (58.75340, 10.27925, -0.131384,
                                            0.025210, 0.025601, -929.3292,
                                            105.8092, -910.8568)),
                        SimpleHeatCapacity(1996.0, 3000.1, 77.99) # NIST data didn't go higher, guessing
    ]
    # Adding flux should reduce the melting point. Possibly effect
    # the latent heat value as well?
    latent_heats = [LatentHeat(1983.15, 9600)]
    thermo_data = ThermoData(heat_capacities, latent_heats)
    species = OldSpecies('SiO2',
                         0.060084,
                         thermo_data,
                         -910.7e3)
    return species

def create_cao_species():
    heat_capacities = [SimpleHeatCapacity(273.15, 298.0, 42.09),
                       ShomateEquation(298.0, 3200.0, # solid phase
                                       (49.95403, 4.887916, -0.352056,
                                        0.046187, -0.825097, -652.9718,
                                        92.56096, -635.0894)),
                        SimpleHeatCapacity(3200.0, 4500.0, 62.76000) # liquid phase
                        ]
    latent_heats = [LatentHeat(2845.15, 80000)]
    thermo_data = ThermoData(heat_capacities, latent_heats)
    species = OldSpecies('CaO',
                         0.0560774,
                         thermo_data)
    return species

def create_mgo_species():
    heat_capacities = [SimpleHeatCapacity(273.15, 298.0, 37.01),
                       ShomateEquation(298.0, 3105.0, # solid phase
                                       (47.25995, 5.681621, -0.872665,
                                        0.104300, -1.053955, -619.1316,
                                        76.46176, -601.2408)),
                        SimpleHeatCapacity(3105.0, 5000.0, 66.944) # liquid phase
    ]
    latent_heats = [LatentHeat(3098.15, 77000)]
    thermo_data = ThermoData(heat_capacities, latent_heats)
    species = OldSpecies('MgO',
                         0.0403044,
                         thermo_data)
    return species

def create_ch4_species():
    c = create_c_species()
    h2 = create_h2_species()

    heat_capacities = [ShomateEquation(273.15, 1300.0,
                                        (-0.703029, 108.4773, -42.52157,
                                        5.862788, 0.678565, -76.84376,
                                        158.7163, -74.87310)),
                        ShomateEquation(1300.0, 6000.0,
                                        (85.81217, 11.26467, -2.114146,
                                        0.138190, -26.42221, -153.5327,
                                        224.4143, -95.74984))]
    thermo_data = ThermoData(heat_capacities)
    species = OldSpecies('CH4',
                         c.mm + 2.0 * h2.mm,
                         thermo_data,
                         -74.6e3)
    return species

def create_scrap_species():
    # TODO. should get data for steel scrap
    species = create_fe_species()
    species.name = 'Scrap'
    return species

def create_air_mixture(mass_kg):
    n2 = create_n2_species()
    n2.mass = mass_kg * 0.7812
    o2 = create_o2_species()
    o2.mass = mass_kg * 0.2095
    ar = create_ar_species()
    ar.mass = mass_kg * 0.0093
    mixture = OldMixture('Air', [n2, o2, ar])
    return mixture


# Chemical reaction master copies
def compute_reaction_enthalpy(reactants, products, temp_kelvin):
    standard_temp = 298.15
    for species in reactants + products:
        species.temp_kelvin = standard_temp
    reactant_enthalpy = 0.0
    for reactant in reactants:
        reactant_enthalpy += reactant.mols * reactant.delta_h_formation
        reactant_enthalpy += reactant.heat_energy(temp_kelvin)
    product_enthalpy = 0.0
    for product in products:
        product_enthalpy += product.mols * product.delta_h_formation
        product_enthalpy += product.heat_energy(temp_kelvin)
    return product_enthalpy - reactant_enthalpy

def delta_h_2fe_o2_2feo(temp_kelvin: float = 298.15) -> float:
    """
    2Fe + O2 -> 2FeO
    """
    fe = create_fe_species()
    fe.mols = 2
    o2 = create_o2_species()
    o2.mols = 1
    reactants = [fe, o2]
    feo = create_feo_species()
    feo.mols = 2
    products = [feo]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)

def delta_h_c_o2_co2(temp_kelvin: float = 298.15) -> float:
    """
    C + O2 -> CO2
    """
    c = create_c_species()
    c.mols = 1
    o2 = create_o2_species()
    o2.mols = 1
    reactants = [c, o2]
    co2 = create_co2_species()
    co2.mols = 1
    products = [co2]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)

def delta_h_2c_o2_2co(temp_kelvin: float = 298.15) -> float:
    """
    2C + O2 -> 2CO
    """
    c = create_c_species()
    c.mols = 2
    o2 = create_o2_species()
    o2.mols = 1
    reactants = [c, o2]
    co = create_co_species()
    co.mols = 2
    products = [co]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)

def delta_h_c_2h2_ch4(temp_kelvin: float = 298.15) -> float:
    """
    C + 2H2 -> CH4
    """
    c = create_c_species()
    c.mols = 1
    h2 = create_h2_species()
    h2.mols = 2
    reactants = [c, h2]
    ch4 = create_ch4_species()
    ch4.mols = 1
    products = [ch4]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)

def delta_h_si_o2_sio2(temp_kelvin: float = 298.15) -> float:
    """
    Si + O2 -> SiO2
    """
    si = create_si_species()
    si.mols = 1
    o2 = create_o2_species()
    o2.mols = 1
    reactants = [si, o2]
    sio2 = create_sio2_species()
    sio2.mols = 1
    products = [sio2]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)

def delta_h_sio2_h2_si_h2o(temp_kelvin: float = 298.15) -> float:
    """
    SiO2 + 2H2 -> Si + 2H2O
    """
    sio2 = create_sio2_species()
    sio2.mols = 1
    h2 = create_h2_species()
    h2.mols = 2
    reactants = [sio2, h2]
    si = create_si_species()
    si.mols = 1
    h2o = create_h2o_species()
    h2o.mols = 2
    products = [si, h2o]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)

def delta_h_2fe_o2_2feo(temp_kelvin: float = 298.15) -> float:
    """
    2Fe + O2 -> 2FeO
    """
    fe = create_fe_species()
    fe.mols = 2
    o2 = create_o2_species()
    o2.mols = 1
    reactants = [fe, o2]
    feo = create_feo_species()
    feo.mols = 2
    products = [feo]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)

def delta_h_feo_c_fe_co(temp_kelvin: float = 298.15) -> float: # Check delta h this gives to a source
    """
    FeO + C -> Fe + CO
    """
    feo = create_feo_species()
    feo.mols = 1
    c = create_c_species()
    c.mols = 1
    reactants = [feo, c]
    fe = create_fe_species()
    fe.mols = 1
    co = create_co_species()
    co.mols = 1
    products = [fe, co]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)

def delta_h_3fe2o3_h2_2fe3o4_h2o(temp_kelvin: float = 298.15) -> float: # TODO! Check with another source. Seems wrong
    """
    3 Fe2O3 + H2 -> 2 Fe3O4 + H2O
    """
    fe2o3 = create_fe2o3_species()
    fe2o3.mols = 3
    h2 = create_h2_species()
    h2.mols = 1
    reactants = [fe2o3, h2]
    fe3o4 = create_fe3o4_species()
    fe3o4.mols = 2
    h2o = create_h2o_species()
    h2o.mols = 1
    products = [fe3o4, h2o]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)

def delta_h_fe3o4_h2_3feo_h2o(temp_kelvin: float = 298.15) -> float: # TODO! Check with another source. Seems wrong
    """
    Fe3O4 + H2 -> 3 FeO + H2O
    """
    fe3o4 = create_fe3o4_species()
    fe3o4.mols = 1
    h2 = create_h2_species()
    h2.mols = 1
    reactants = [fe3o4, h2]
    feo = create_feo_species()
    feo.mols = 3
    h2o = create_h2o_species()
    h2o.mols = 1
    products = [feo, h2o]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)

def delta_h_feo_h2_fe_h2o(temp_kelvin: float = 298.15) -> float: # TODO! Check with another source. Seems wrong
    """
    FeO + H2 -> Fe + H2O
    """
    feo = create_feo_species()
    feo.mols = 1
    h2 = create_h2_species()
    h2.mols = 1
    reactants = [feo, h2]
    fe = create_fe_species()
    fe.mols = 1
    h2o = create_h2o_species()
    h2o.mols = 1
    products = [fe, h2o]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)

def delta_h_3fe2o3_2h_2fe3o4_h2o(temp_kelvin: float = 298.15) -> float: # TODO! Check with another source. Seems wrong
    """
    3 Fe2O3 + 2 H -> 2 Fe3O4 + H2O
    Note: Monatomic hydrogen reduction.
    """
    fe2o3 = create_fe2o3_species()
    fe2o3.mols = 3
    h = create_h_species()
    h.mols = 2
    reactants = [fe2o3, h]
    fe3o4 = create_fe3o4_species()
    fe3o4.mols = 2
    h2o = create_h2o_species()
    h2o.mols = 1
    products = [fe3o4, h2o]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)

def delta_h_fe3o4_2h_3feo_h2o(temp_kelvin: float = 298.15) -> float: # TODO! Check with another source. Seems wrong
    """
    Fe3O4 + 2 H -> 3 FeO + H2O
    Note: Monatomic hydrogen reduction.
    """
    fe3o4 = create_fe3o4_species()
    fe3o4.mols = 1
    h = create_h_species()
    h.mols = 2
    reactants = [fe3o4, h]
    feo = create_feo_species()
    feo.mols = 3
    h2o = create_h2o_species()
    h2o.mols = 1
    products = [feo, h2o]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)

def delta_h_feo_2h_fe_h2o(temp_kelvin: float = 298.15) -> float: # TODO! Check with another source. Seems wrong
    """
    FeO + 2 H -> Fe + H2O
    Note: Monatomic hydrogen reduction.
    """
    feo = create_feo_species()
    feo.mols = 1
    h = create_h_species()
    h.mols = 2
    reactants = [feo, h]
    fe = create_fe_species()
    fe.mols = 1
    h2o = create_h2o_species()
    h2o.mols = 1
    products = [fe, h2o]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)


def delta_h_fe2o3_3h2_3fe_3h2o(temp_kelvin: float = 298.15) -> float:
    """
    Fe2O3 + 3 H2 -> 2 Fe + 3 H2O
    """
    fe2o3 = create_fe2o3_species()
    fe2o3.mols = 1
    h2 = create_h2_species()
    h2.mols = 3
    reactants = [fe2o3, h2]
    fe = create_fe_species()
    fe.mols = 2
    h2o = create_h2o_species()
    h2o.mols = 3
    products = [fe, h2o]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)

def delta_h_2h2o_2h2_o2(temp_kelvin: float = 298.15) -> float:
    """
    2 H2O + 474.2 kJ/mol electricity + 97.2 kJ/mol heat -> 2 H2 + O2
    """
    h2o = create_h2o_species()
    h2o.mols = 2
    reactants = [h2o]
    h2 = create_h2_species()
    h2.mols = 2
    o2 = create_o2_species()
    o2.mols = 1
    products = [h2, o2]
    return compute_reaction_enthalpy(reactants, products, temp_kelvin)
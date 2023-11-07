#!/usr/bin/env python3

import sys
import os
import math
from typing import Dict

try:
    from technoeconomics.system import System
except ImportError:
    # If the technoeconomics package is not installed via pip,
    # add the package directory to the system path.
    examples_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    package_dir = os.path.dirname(examples_dir)
    sys.path.insert(0, package_dir)

    from technoeconomics.system import System


# Levelised Cost of Production Helpers
def operating_cost_per_tonne(inputs: Dict[str, float], spot_electricity_hours: float = 8.0) -> Dict[str, float]:
    # TODO! Update the electrcity prices based on the location of the plant

    # Electricity cost USD / MWh
    expensive_spot_electricity_cpmwh = 93.1
    cheap_spot_electricity_cpmwh = 54.5
    base_electricity_cpmwh = (spot_electricity_hours * cheap_spot_electricity_cpmwh + (24.0-spot_electricity_hours) * expensive_spot_electricity_cpmwh) / 24.0

    # cpt = cost per tonne (USD), cpk = cost per kg (USD)
    ore_cpt = 100.0 # big difference between my price and the slides
    scrap_cpt = 250.0 # check this
    cao_cpk = 0.08 
    mgo_cpk = 0.49 
    h2_cpk = 3.0 # should be adjutable based on an input file
    o2_cpk = 0.0 # free, since it's a byproduct of electrolysis
    h2o_cpk = 0.0 # assumption that water should be close to zero cost, especially since it's a byproduct of reduction?
    carbon_cpt = 130.0

    # usd per hour. Kind of a guess so that it comes out 
    # at 60 USD / tonne of steel. 
    labour_cph = 40.0

    cost = {
        'Base Electricity' : inputs['base electricity'] * base_electricity_cpmwh / 3.6e+9,
        'Cheap Spot Electricity': inputs.get('cheap electricity', 0.0) * cheap_spot_electricity_cpmwh / 3.6e+9,
        'Scrap' : inputs['scrap'] * scrap_cpt / 1000,
        'Ore' : inputs['ore'] * ore_cpt / 1000,
        'CaO' : inputs['CaO'] * cao_cpk,
        'MgO' : inputs['MgO'] * mgo_cpk,
        'Carbon' : inputs['C'] * carbon_cpt / 1000,
        'H2' : inputs.get('H2', 0.0) * h2_cpk,
        'Oxygen' : inputs['O2'] * o2_cpk,
        'Water' : inputs.get('H2O', 0.0) * h2o_cpk,
        'Labour' : 1.5 * labour_cph,
    }

    return cost 


def capex_direct_and_indirect(direct_capex: float) -> float:
    r_contg = 0.1 # contingency cost coefficient
    r_cons = 0.09 # construction cost coefficient
    c_direct = (1 + r_contg) * direct_capex
    c_indirect = r_cons * c_direct
    return c_direct + c_indirect


def annuity_factor(years: float) -> float:
    r_nom = 0.07 # the constant nominal discount rate
    r_i = 0.025 # inflation rate
    r_real = (1+r_nom)/(1+r_i)-1 # the constant real discount rate
    n = years 

    # TODO: verify this formula.
    f = (r_real*(1+r_real**n))/((1+r_real)**n - 1) 
    return f


def lcop_capex_only(capex, annual_production, plant_lifetime_years):
    return annuity_factor(plant_lifetime_years)*capex / annual_production


def lcop_opex_only(annual_operating_cost, annual_production):
    return annual_operating_cost / annual_production


def lcop_total(capex, annual_operating_cost, annual_production, plant_lifetime_years):
    # TODO! levelised cost of production will depend on the capacity factor of the plant
    return lcop_capex_only(capex, annual_production, plant_lifetime_years) + \
           lcop_opex_only(annual_operating_cost, annual_production)


def add_steel_plant_capex(system: System):
    # TODO! Need to unify the ways of defining the steel plant capex.
    if 'h2 storage' in system.devices:
        add_h2_storage_capex(system)


def add_h2_storage_capex(system: System):
    if 'h2 storage method' not in system.system_vars or \
        'h2 storage hours of operation' not in system.system_vars:
        raise ValueError('h2 storage method or h2 storage hours of operation not defined')

    h2_storage_method = system.system_vars['h2 storage method']
    h2_storage_hours_of_operation = system.system_vars['h2 storage hours of operation']

    mass_h2_per_tonne_steel = system.devices['water electrolysis'].first_output_containing_name('h2').mass
    tonnes_steel_per_hour = system.annual_capacity / (365.25 * 24)
    h2_storage_required = tonnes_steel_per_hour * mass_h2_per_tonne_steel * h2_storage_hours_of_operation
    system.devices['h2 storage'].device_vars['h2 storage size [kg]'] = h2_storage_required
    system.devices['h2 storage'].device_vars['h2 storage type'] = h2_storage_method
    
    if h2_storage_method.lower() == 'salt caverns':
        system.devices['h2 storage'].capex = h2_storage_required * salt_cavern_capex_lord2014()
        # required h2 storage is less than a typical salt canvern. Would need to share with some
        # other applications.
    elif h2_storage_method.lower() == 'compressed gas vessels':
        system.devices['h2 storage'].capex = h2_storage_required * compressed_h2_gas_vessel_elberry2021()
        system.devices['h2 storage'].device_vars['num h2 storage vessels'] = int(math.ceil(h2_storage_required / 300.0))
    else:
        raise ValueError('h2 storage method not recognised')

# lord2014
# A. S. Lord, P. H. Kobos, and D. J. Borns, “Geologic storage of hydrogen: 
# Scaling up to meet city transportation demands,” International Journal of Hydrogen Energy, 
# vol. 39, no. 28, pp. 15570–15582, 2014, doi: https://doi.org/10.1016/j.ijhydene.2014.07.121.
def salt_cavern_capex_lord2014():
    """
    Returns the cost per kilo of usable hydrogen stored in a salt cavern. (excludes cushion gas)
    It is up to the function caller to ensure the size of the salt cavern is appropriate for the application.
    """
    # cpk = cost per kilo
    # refers to the usable h2 (so excludes the cushion gas)
    inflation_2014_2023 = 1.29
    stored_h2_cpk_2014 = 1.61 
    stored_h2_cpk_2023 = stored_h2_cpk_2014 * inflation_2014_2023
    return stored_h2_cpk_2023

# elberry2021
# A. M. Elberry, J. Thakur, A. Santasalo-Aarnio, and M. Larmi, “Large-scale compressed
# hydrogen storage as part of renewable electricity storage systems,” International 
# Journal of Hydrogen Energy, vol. 46, no. 29, pp. 15671–15690, 2021, 
# doi: https://doi.org/10.1016/j.ijhydene.2021.02.080.
# TODO: Verify this cost with a few other sources. Quick scan, seems optimistic
def compressed_h2_gas_vessel_elberry2021():
    # Using multifunctional steel layered hydrogen storage vessel (MSLV)
    # Target 160 bar, 25m^3, lower end of the pressure range for MSLV vessels.
    # ~300 kg / vessel
    # Less energy required for compression, cheaper vessels, cheaper compressors.
    # But requires more space, more vessels, possibly more leakage of hydrogen.
    inflation_2016_2023 = 1.27
    stored_h2_cpk_2016 = 350.0
    stored_h2_cpk_2023 = stored_h2_cpk_2016 * inflation_2016_2023
    return stored_h2_cpk_2023
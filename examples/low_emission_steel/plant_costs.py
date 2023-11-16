#!/usr/bin/env python3

import csv
from enum import Enum
import math
import os
import sys
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


class PriceUnits(Enum):
    PerKilo = 1
    PerTonne = 2
    PerMegaWattHour = 3
    PerDevice = 4
    PerTonneOfAnnualCapacity = 5
    PerTonneOfProduct = 6


class PriceEntry:
    def __init__(self, name: str, price_usd: float, units: PriceUnits):
        self.name: str = name
        self.price_usd: float = price_usd
        self.units: PriceUnits = units
    
    def __repr__(self):
        return f'PriceEntry({self.name}: ${self.price_usd} {self.units})'


def load_prices_from_csv(filename: str) -> Dict[str, PriceEntry]:
    with open(filename, newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # skip the title row
        prices = {}
        for row in reader:
            name = row[0]
            price_usd = float(row[1])
            units = PriceUnits[row[2]]
            prices[name] = PriceEntry(name, price_usd, units)
        return prices


def add_steel_plant_lcop(system: System, prices: Dict[str, PriceEntry]):
    lcop_itemised = {
        'capex': lcop_capex_only(system.capex(), system.annual_capacity, system.lifetime_years)
    }

    inputs = system.system_inputs(ignore_flows_named=['infiltrated air'], separate_mixtures_named=['flux', 'h2 rich gas'], mass_flow_only=False)
    operating_costs = operating_cost_per_tonne(inputs, prices, system.system_vars['cheap electricity hours'])
    for opex_name, opex_per_tonne in operating_costs.items():
        lcop_itemised[opex_name] = opex_per_tonne

    system.lcop_breakdown = lcop_itemised


def operating_cost_per_tonne(inputs: Dict[str, float], prices: Dict[str, PriceEntry], spot_electricity_hours: float = 8.0) -> Dict[str, float]:
    # TODO! Update the electrcity prices based on the location of the plant

    # Electricity cost USD / MWh
    expensive_spot_electricity_cpmwh = 93.1
    cheap_spot_electricity_cpmwh = 54.5
    base_electricity_cpmwh = (spot_electricity_hours * cheap_spot_electricity_cpmwh + (24.0-spot_electricity_hours) * expensive_spot_electricity_cpmwh) / 24.0
    prices['Base Electricity'] = PriceEntry('Base Electricity', base_electricity_cpmwh, PriceUnits.PerMegaWattHour)

    inputs_lower = {k.lower(): v for k, v in inputs.items()}
    if len(inputs_lower) != len(inputs):
        raise Exception("Key clash detected after converting keys to lower case.")
    
    prices_lower = {k.lower(): v for k, v in prices.items()}
    if len(prices_lower) != len(prices):
        raise Exception("Key clash detected after converting keys to lower case.")

    operating_costs = {}
    for input_name, input_amount in inputs_lower.items():

        if input_name in prices_lower:
            price = prices_lower[input_name]
            if price.units == PriceUnits.PerKilo:
                operating_costs[input_name] = input_amount * price.price_usd
            elif price.units == PriceUnits.PerTonne:
                operating_costs[input_name] = input_amount * price.price_usd / 1000.0
            elif price.units == PriceUnits.PerMegaWattHour:
                operating_costs[input_name] = input_amount * price.price_usd / 3.6e+9
            elif price.units == PriceUnits.PerTonneOfProduct:
                operating_costs[input_name] = input_amount * price.price_usd
            else:
                raise ValueError(f'Price units not recognised or invalid for consumables: {price.units}')
        else:
            print(f'Warning: Price not found for {input_name}')

    return operating_costs 


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
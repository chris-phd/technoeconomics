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
    PerKiloOfCapacity = 7
    PerKiloJouleOfCapacity = 8


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
    add_steel_plant_capex(system, prices)

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

    inputs_lower = {k.lower(): v for k, v in inputs.items()}
    if len(inputs_lower) != len(inputs):
        raise Exception("Key clash detected after converting keys to lower case.")
    
    prices_lower = {k.lower(): v for k, v in prices.items()}
    if len(prices_lower) != len(prices):
        raise Exception("Key clash detected after converting keys to lower case.")

    if 'cheap spot electricity' in prices_lower and 'expensive spot electricity' in prices_lower:
        expensive_spot_electricity_cpmwh = prices_lower['expensive spot electricity'].price_usd
        cheap_spot_electricity_cpmwh = prices_lower['cheap spot electricity'].price_usd
        base_electricity_cpmwh = (spot_electricity_hours * cheap_spot_electricity_cpmwh + (24.0-spot_electricity_hours) * expensive_spot_electricity_cpmwh) / 24.0
        prices['Base Electricity'] = PriceEntry('Base Electricity', base_electricity_cpmwh, PriceUnits.PerMegaWattHour)
        prices_lower['base electricity'] = PriceEntry('base electricity', base_electricity_cpmwh, PriceUnits.PerMegaWattHour)
    elif 'base electricity' in prices_lower:
        prices['Cheap Spot Electricity'] = PriceEntry('Cheap Spot Electricity', base_electricity_cpmwh, PriceUnits.PerMegaWattHour)
        prices_lower['cheap spot clectricity'] = PriceEntry('cheap spot clectricity', base_electricity_cpmwh, PriceUnits.PerMegaWattHour)
    else:
        raise Exception("No electricity prices set. Need either a 'Base Electricity' entry or both a 'Cheap Spot Electricity' and 'Expensive Spot Electricity' entry")


    operating_costs = {}
    for k, price in prices_lower.items():
        # Primaily used for labour, which we have assumed to be constant.
        if price.units == PriceUnits.PerTonneOfProduct:
            operating_costs[k] = price.price_usd

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


def add_steel_plant_capex(system: System, prices: Dict[str, PriceEntry]):
    prices_lower = {k.lower(): v for k, v in prices.items()}
    if len(prices_lower) != len(prices):
        raise Exception("Key clash detected after converting keys to lower case.")

    if 'h2 storage' in system.devices:
        add_h2_storage_capex(system, prices_lower)

    for device_name, device in system.devices.items():
        if device.capex_label is None:
            continue # capex price already set

        capex_label = device.capex_label.lower()
        if capex_label not in prices_lower:
            raise Exception(f"No entry in price csv with label {device.capex_label}. Expected for device {device_name} in system {system.name}")

        price = prices_lower[capex_label]
        
        if price.units == PriceUnits.PerDevice:
            device.capex = price.price_usd
        if price.units == PriceUnits.PerTonneOfAnnualCapacity:
            device.capex = price.price_usd * system.annual_capacity


def add_h2_storage_capex(system: System, prices: Dict[str, PriceEntry]):
    if 'h2 storage method' not in system.system_vars or \
        'h2 storage hours of operation' not in system.system_vars:
        raise ValueError('h2 storage method or h2 storage hours of operation not defined')

    h2_storage_method = system.system_vars['h2 storage method']
    h2_storage_hours_of_operation = system.system_vars['h2 storage hours of operation']

    price = prices[system.devices['h2 storage'].capex_label.lower()]
    if price.units != PriceUnits.PerKiloOfCapacity: 
        raise ValueError(f"Only PriceUnits of {PriceUnits.PerKiloOfCapacity} are supported for H2 storage.")

    mass_h2_per_tonne_steel = system.devices['water electrolysis'].first_output_containing_name('h2').mass
    tonnes_steel_per_hour = system.annual_capacity / (365.25 * 24)
    h2_storage_required = tonnes_steel_per_hour * mass_h2_per_tonne_steel * h2_storage_hours_of_operation
    system.devices['h2 storage'].device_vars['h2 storage size [kg]'] = h2_storage_required
    system.devices['h2 storage'].device_vars['h2 storage type'] = h2_storage_method
    
    if h2_storage_method.lower() == 'salt caverns':
        system.devices['h2 storage'].capex = h2_storage_required * price.price_usd
        # required h2 storage is less than a typical salt canvern. Would need to share with some
        # other applications.
    elif h2_storage_method.lower() == 'compressed gas vessels':
        system.devices['h2 storage'].capex = h2_storage_required * price.price_usd
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

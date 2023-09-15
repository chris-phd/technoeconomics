#!/usr/bin/env python3

import sys
import os
from typing import Optional

try:
    from technoeconomics.species import create_dummy_species, create_dummy_mixture
    from technoeconomics.system import System, Device, EnergyFlow
    from technoeconomics.utils import celsius_to_kelvin
except ImportError:
    # If the technoeconomics package is not installed via pip,
    # add the package directory to the system path.
    examples_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    package_dir = os.path.dirname(examples_dir)
    sys.path.insert(0, package_dir)

    from technoeconomics.species import create_dummy_species, create_dummy_mixture
    from technoeconomics.system import System, Device, EnergyFlow
    from technoeconomics.utils import celsius_to_kelvin


def main():
    # TODO: Add transferred and non-transferred arc system.
    plasma_system = create_plasma_system()
    dri_eaf_system = create_dri_eaf_system()
    hybrid33_system = create_hybrid_system("hybrid33 steelmaking", 33.33)
    hybrid95_system = create_hybrid_system("hybrid95 steelmaking", 95.0)

    plasma_system.render(output_directory="/home/chris/Desktop/")
    dri_eaf_system.render(output_directory="/home/chris/Desktop/")
    hybrid33_system.render(output_directory="/home/chris/Desktop/")
    hybrid95_system.render(output_directory="/home/chris/Desktop/")


# System Creators
def create_plasma_system(system_name='plasma steelmaking', h2_storage_method: Optional[str] = 'salt caverns',
                         annual_capacity_tls=1.5e6, plant_lifetime_years=20.0) -> System:
    plasma_system = System(system_name, annual_capacity_tls, plant_lifetime_years)

    water_electrolysis = Device('water electrolysis', electrolyser_capex_desantis2021() * annual_capacity_tls)
    plasma_system.add_device(water_electrolysis)
    if h2_storage_method is not None:
        h2_storage = Device('h2 storage')
        plasma_system.add_device(h2_storage)
    h2_heat_exchanger = Device('h2 heat exchanger')
    plasma_system.add_device(h2_heat_exchanger)
    condenser = Device('condenser and scrubber')
    plasma_system.add_device(condenser)
    ore_heater = Device('ore heater')
    plasma_system.add_device(ore_heater)
    plasma_torch = Device('plasma torch')
    plasma_system.add_device(plasma_torch)
    plasma_smelter = Device('plasma smelter', plasma_capex_desantis2021() * annual_capacity_tls)
    plasma_system.add_device(plasma_smelter)
    join_1 = Device('join 1')
    plasma_system.add_device(join_1)

    # System variables defaults. Can be overwritten by user before mass and energy flows.
    plasma_system.system_vars['cheap electricity hours'] = 8.0
    plasma_system.system_vars['h2 storage hours of operation'] = 24.0 - plasma_system.system_vars['cheap electricity hours']
    plasma_system.system_vars['steelmaking device name'] = plasma_smelter.name
    plasma_system.system_vars['feo soluble in slag percent'] = 27.0
    plasma_system.system_vars['plasma temp K'] = 2500 
    plasma_system.system_vars['plasma reduction percent'] = 95.0
    plasma_system.system_vars['final reduction percent'] = plasma_system.system_vars['plasma reduction percent']
    plasma_system.system_vars['plasma h2 excess ratio'] = 1.5
    plasma_system.system_vars['o2 injection kg'] = 0.0
    plasma_system.system_vars['plasma torch electro-thermal eff pecent'] = 55.0
    plasma_system.system_vars['steel exit temp K'] = celsius_to_kelvin(1650)
    plasma_system.system_vars['steelmaking bath temp K'] = plasma_system.system_vars['steel exit temp K']
    plasma_system.system_vars['b2 basicity'] = 2.0
    plasma_system.system_vars['b4 basicity'] = 2.1
    plasma_system.system_vars['ore heater device name'] = ore_heater.name
    plasma_system.system_vars['ore heater temp K'] = celsius_to_kelvin(1450)
    plasma_system.system_vars['ironmaking device names'] = [plasma_smelter.name]
    plasma_system.system_vars['electrolysis lhv efficiency percent'] = 70.0
    plasma_system.system_vars['hydrogen loops'] = [plasma_system.system_vars['ironmaking device names']]
    plasma_system.system_vars['h2 consuming device names'] = plasma_system.system_vars['ironmaking device names']
    plasma_system.system_vars['scrap perc'] = 0.0
    plasma_system.system_vars['steel carbon perc'] = 1.0
    plasma_system.system_vars['max heat exchanger temp K'] = celsius_to_kelvin(1400)
    if h2_storage_method is not None:
        plasma_system.system_vars['h2 storage method'] = h2_storage_method

    # electrolysis flows
    plasma_system.add_input(water_electrolysis.name, create_dummy_species('h2o'))
    plasma_system.add_output(water_electrolysis.name, create_dummy_species('o2'))
    if h2_storage_method is not None:
        electricity_type = 'cheap electricity'
    else:
        electricity_type = 'base electricity'
    plasma_system.add_input(water_electrolysis.name, EnergyFlow(electricity_type))
    plasma_system.add_output(water_electrolysis.name, EnergyFlow('losses'))
    plasma_system.add_output(water_electrolysis.name, EnergyFlow('chemical'))

    # h2 storage
    if h2_storage_method is not None:
        plasma_system.add_flow(water_electrolysis.name, h2_storage.name, create_dummy_species('h2 rich gas'))
        plasma_system.add_input(h2_storage.name, EnergyFlow('cheap electricity'))
        plasma_system.add_output(h2_storage.name, EnergyFlow('losses'))

    # condenser
    plasma_system.add_output(condenser.name, create_dummy_species('h2o'))
    plasma_system.add_output(condenser.name, EnergyFlow('losses'))
    plasma_system.add_output(condenser.name, create_dummy_mixture('carbon gas'))
    plasma_system.add_flow(h2_heat_exchanger.name, condenser.name, create_dummy_mixture('recycled h2 rich gas'))

    # join
    plasma_system.add_flow(condenser.name, join_1.name, create_dummy_species('recycled h2 rich gas'))
    if h2_storage_method is not None:
        plasma_system.add_flow(h2_storage.name, join_1.name, create_dummy_species('h2 rich gas'))
    else:
        plasma_system.add_flow(water_electrolysis.name, join_1.name, create_dummy_species('h2 rich gas'))

    # heat exchanger
    plasma_system.add_flow(join_1.name, h2_heat_exchanger.name, create_dummy_species('h2 rich gas'))
    plasma_system.add_flow(plasma_smelter.name, h2_heat_exchanger.name, create_dummy_mixture('recycled h2 rich gas'))
    plasma_system.add_output(h2_heat_exchanger.name, EnergyFlow('losses'))

    # ore heater
    plasma_system.add_input(ore_heater.name, create_dummy_mixture('ore'))
    plasma_system.add_input(ore_heater.name, EnergyFlow('base electricity'))
    plasma_system.add_output(ore_heater.name, EnergyFlow('losses'))

    # plasma torch
    plasma_system.add_flow(h2_heat_exchanger.name, plasma_torch.name, create_dummy_species('h2 rich gas'))
    plasma_system.add_input(plasma_torch.name, EnergyFlow('base electricity'))
    plasma_system.add_output(plasma_torch.name, EnergyFlow('losses'))

    # plasma smelter
    plasma_system.add_flow(ore_heater.name, plasma_smelter.name, create_dummy_mixture('ore'))
    plasma_system.add_flow(plasma_torch.name, plasma_smelter.name, create_dummy_species('plasma h2 rich gas'))
    plasma_system.add_output(plasma_smelter.name, EnergyFlow('losses'))
    plasma_system.add_input(plasma_smelter.name, EnergyFlow('chemical'))
    plasma_system.add_input(plasma_smelter.name, create_dummy_species('carbon'))
    plasma_system.add_input(plasma_smelter.name, create_dummy_mixture('flux'))
    plasma_system.add_input(plasma_smelter.name, create_dummy_species('o2'))
    plasma_system.add_input(plasma_smelter.name, create_dummy_species('scrap'))
    plasma_system.add_output(plasma_smelter.name, create_dummy_mixture('slag'))
    plasma_system.add_output(plasma_smelter.name, create_dummy_mixture('steel'))

    return plasma_system


def create_dri_eaf_system(system_name='dri eaf steelmaking', h2_storage_method: Optional[str] = 'salt caverns',
                          annual_capacity_tls=1.5e6, plant_lifetime_years=20.0) -> System:
    dri_eaf_system = System(system_name, annual_capacity_tls, plant_lifetime_years)

    water_electrolysis = Device('water electrolysis', electrolyser_capex_desantis2021() * annual_capacity_tls)
    dri_eaf_system.add_device(water_electrolysis)
    if h2_storage_method is not None:
        h2_storage = Device('h2 storage')
        dri_eaf_system.add_device(h2_storage)
    h2_heat_exchanger = Device('h2 heat exchanger')
    dri_eaf_system.add_device(h2_heat_exchanger)
    join_1 = Device('join 1')
    dri_eaf_system.add_device(join_1)
    h2_heater_1 = Device('h2 heater 1')
    dri_eaf_system.add_device(h2_heater_1)
    h2_heater_2 = Device('h2 heater 2')
    dri_eaf_system.add_device(h2_heater_2)
    condenser = Device('condenser and scrubber')
    dri_eaf_system.add_device(condenser)
    ore_heater = Device('ore heater')
    dri_eaf_system.add_device(ore_heater)
    fluidized_bed_1 = Device('fluidized bed 1', dri_capex_wortler2013() / 3 * annual_capacity_tls)
    dri_eaf_system.add_device(fluidized_bed_1)
    fluidized_bed_2 = Device('fluidized bed 2', dri_capex_wortler2013() / 3 * annual_capacity_tls)
    dri_eaf_system.add_device(fluidized_bed_2)
    fluidized_bed_3 = Device('fluidized bed 3', dri_capex_wortler2013() / 3 * annual_capacity_tls)
    dri_eaf_system.add_device(fluidized_bed_3)
    briquetting = Device('briquetting')
    dri_eaf_system.add_device(briquetting)
    eaf = Device('eaf', eaf_capex_wortler2013() * annual_capacity_tls)
    dri_eaf_system.add_device(eaf)

    # System variables defaults. Can be overwritten by user before mass and energy flows.
    dri_eaf_system.system_vars['cheap electricity hours'] = 8.0
    dri_eaf_system.system_vars['h2 storage hours of operation'] = 24.0 - dri_eaf_system.system_vars['cheap electricity hours']
    dri_eaf_system.system_vars['fluidized beds reduction percent'] = 95
    dri_eaf_system.system_vars['final reduction percent'] = dri_eaf_system.system_vars['fluidized beds reduction percent']
    dri_eaf_system.system_vars['steelmaking device name'] = eaf.name
    dri_eaf_system.system_vars['feo soluble in slag percent'] = 27.0
    dri_eaf_system.system_vars['eaf reaction temp K'] = celsius_to_kelvin(1650) 
    dri_eaf_system.system_vars['steel exit temp K'] = celsius_to_kelvin(1650)
    dri_eaf_system.system_vars['b2 basicity'] = 2.0
    dri_eaf_system.system_vars['b4 basicity'] = 1.8
    dri_eaf_system.system_vars['ore heater device name'] = ore_heater.name
    dri_eaf_system.system_vars['ore heater temp K'] = celsius_to_kelvin(800)
    dri_eaf_system.system_vars['ironmaking device names'] = [fluidized_bed_1.name, fluidized_bed_2.name, fluidized_bed_3.name]
    dri_eaf_system.system_vars['fluidized beds h2 excess ratio'] = 4.0
    dri_eaf_system.system_vars['o2 injection kg'] = 35.0
    dri_eaf_system.system_vars['electrolysis lhv efficiency percent'] = 70.0
    dri_eaf_system.system_vars['hydrogen loops'] = [dri_eaf_system.system_vars['ironmaking device names']]
    dri_eaf_system.system_vars['h2 consuming device names'] = dri_eaf_system.system_vars['ironmaking device names']
    dri_eaf_system.system_vars['scrap perc'] = 0.0
    dri_eaf_system.system_vars['steel carbon perc'] = 1.0
    dri_eaf_system.system_vars['max heat exchanger temp K'] = celsius_to_kelvin(1400)
    if h2_storage_method is not None:
        dri_eaf_system.system_vars['h2 storage method'] = h2_storage_method

    # electrolysis flows
    dri_eaf_system.add_input(water_electrolysis.name, create_dummy_species('h2o'))
    dri_eaf_system.add_output(water_electrolysis.name, create_dummy_species('o2'))
    if h2_storage_method is not None:
        electricity_type = 'cheap electricity'
    else:
        electricity_type = 'base electricity'
    dri_eaf_system.add_input(water_electrolysis.name, EnergyFlow(electricity_type))
    dri_eaf_system.add_output(water_electrolysis.name, EnergyFlow('losses'))
    dri_eaf_system.add_output(water_electrolysis.name, EnergyFlow('chemical'))

    # h2 storage
    if h2_storage_method is not None:
        dri_eaf_system.add_flow(water_electrolysis.name, h2_storage.name, create_dummy_species('h2 rich gas'))
        dri_eaf_system.add_input(h2_storage.name, EnergyFlow('cheap electricity'))
        dri_eaf_system.add_output(h2_storage.name, EnergyFlow('losses'))

    # condenser
    dri_eaf_system.add_output(condenser.name, create_dummy_species('h2o'))
    dri_eaf_system.add_output(condenser.name, EnergyFlow('losses'))
    dri_eaf_system.add_flow(h2_heat_exchanger.name, condenser.name, create_dummy_mixture('recycled h2 rich gas'))

    # join
    dri_eaf_system.add_flow(condenser.name, join_1.name, create_dummy_species('recycled h2 rich gas'))
    if h2_storage_method is not None:
        dri_eaf_system.add_flow(h2_storage.name, join_1.name, create_dummy_species('h2 rich gas'))
    else:
        dri_eaf_system.add_flow(water_electrolysis.name, join_1.name, create_dummy_species('h2 rich gas'))

    # heat exchanger
    dri_eaf_system.add_flow(join_1.name, h2_heat_exchanger.name, create_dummy_species('h2 rich gas'))
    dri_eaf_system.add_flow(fluidized_bed_1.name, h2_heat_exchanger.name, create_dummy_mixture('recycled h2 rich gas'))
    dri_eaf_system.add_output(h2_heat_exchanger.name, EnergyFlow('losses'))

    # ore heater
    dri_eaf_system.add_input(ore_heater.name, create_dummy_mixture('ore'))
    dri_eaf_system.add_input(ore_heater.name, EnergyFlow('base electricity'))
    dri_eaf_system.add_output(ore_heater.name, EnergyFlow('losses'))

    # fluidized bed 1
    dri_eaf_system.add_flow(ore_heater.name, fluidized_bed_1.name, create_dummy_mixture('ore'))
    dri_eaf_system.add_flow(fluidized_bed_2.name, fluidized_bed_1.name, create_dummy_mixture('h2 rich gas'))
    dri_eaf_system.add_input(fluidized_bed_1.name, EnergyFlow('chemical'))
    dri_eaf_system.add_output(fluidized_bed_1.name, EnergyFlow('losses'))

    # fluidized bed 2
    dri_eaf_system.add_flow(fluidized_bed_1.name, fluidized_bed_2.name, create_dummy_mixture('dri'))
    dri_eaf_system.add_flow(h2_heater_1.name, fluidized_bed_2.name, create_dummy_mixture('h2 rich gas'))
    dri_eaf_system.add_input(fluidized_bed_2.name, EnergyFlow('chemical'))    
    dri_eaf_system.add_output(fluidized_bed_2.name, EnergyFlow('losses'))

    # heater 1
    dri_eaf_system.add_flow(fluidized_bed_3.name, h2_heater_1.name, create_dummy_mixture('h2 rich gas'))
    dri_eaf_system.add_input(h2_heater_1.name, EnergyFlow('base electricity'))
    dri_eaf_system.add_output(h2_heater_1.name, EnergyFlow('losses'))

    # fluidized bed 3
    dri_eaf_system.add_flow(fluidized_bed_2.name, fluidized_bed_3.name, create_dummy_mixture('dri'))
    dri_eaf_system.add_flow(h2_heater_2.name, fluidized_bed_3.name, create_dummy_mixture('h2 rich gas'))
    dri_eaf_system.add_input(fluidized_bed_3.name, EnergyFlow('chemical'))
    dri_eaf_system.add_output(fluidized_bed_3.name, EnergyFlow('losses'))

    # heater 2
    dri_eaf_system.add_flow(h2_heat_exchanger.name, h2_heater_2.name, create_dummy_species('h2 rich gas'))
    dri_eaf_system.add_input(h2_heater_2.name, EnergyFlow('base electricity'))
    dri_eaf_system.add_output(h2_heater_2.name, EnergyFlow('losses'))

    # briquetting
    dri_eaf_system.add_flow(fluidized_bed_3.name, briquetting.name, create_dummy_mixture('dri'))

    # eaf
    dri_eaf_system.add_flow(briquetting.name, eaf.name, create_dummy_mixture('hbi'))
    dri_eaf_system.add_input(eaf.name, EnergyFlow('base electricity'))
    dri_eaf_system.add_output(eaf.name, EnergyFlow('losses'))
    dri_eaf_system.add_input(eaf.name, create_dummy_species('electrode'))
    dri_eaf_system.add_input(eaf.name, EnergyFlow('chemical'))
    dri_eaf_system.add_input(eaf.name, create_dummy_species('carbon'))
    dri_eaf_system.add_input(eaf.name, create_dummy_mixture('flux'))
    dri_eaf_system.add_input(eaf.name, create_dummy_species('o2'))
    dri_eaf_system.add_input(eaf.name, create_dummy_mixture('infiltrated air'))
    dri_eaf_system.add_input(eaf.name, create_dummy_species('scrap'))
    dri_eaf_system.add_output(eaf.name, create_dummy_mixture('infiltrated air'))
    dri_eaf_system.add_output(eaf.name, create_dummy_mixture('carbon gas'))
    dri_eaf_system.add_output(eaf.name, create_dummy_mixture('slag'))
    dri_eaf_system.add_output(eaf.name, create_dummy_mixture('steel'))

    return dri_eaf_system


def create_hybrid_system(system_name='hybrid steelmaking',  h2_storage_method: Optional[str] = 'salt caverns', 
                         prereduction_perc=33.33, annual_capacity_tls=1.5e6, plant_lifetime_years=20.0) -> System:
    hybrid_system = System(system_name, annual_capacity_tls, plant_lifetime_years)

    water_electrolysis = Device('water electrolysis', electrolyser_capex_desantis2021() * annual_capacity_tls)
    hybrid_system.add_device(water_electrolysis)
    if h2_storage_method is not None:
        h2_storage = Device('h2 storage')
        hybrid_system.add_device(h2_storage)
    h2_heat_exchanger = Device('h2 heat exchanger')
    hybrid_system.add_device(h2_heat_exchanger)
    h2_heater_1 = Device('h2 heater 1')
    hybrid_system.add_device(h2_heater_1)
    condenser = Device('condenser and scrubber')
    hybrid_system.add_device(condenser)
    ore_heater = Device('ore heater')
    hybrid_system.add_device(ore_heater)
    fluidized_bed_1 = Device('fluidized bed 1', dri_capex_wortler2013() / 3 * annual_capacity_tls)
    hybrid_system.add_device(fluidized_bed_1)
    fluidized_bed_2 = Device('fluidized bed 2', dri_capex_wortler2013() / 3 * annual_capacity_tls)
    hybrid_system.add_device(fluidized_bed_2)
    briquetting = Device('briquetting')
    hybrid_system.add_device(briquetting)
    plasma_torch = Device('plasma torch')
    hybrid_system.add_device(plasma_torch)
    plasma_smelter = Device('plasma smelter', plasma_capex_desantis2021() * annual_capacity_tls)
    hybrid_system.add_device(plasma_smelter)
    join_1 = Device('join 1')
    hybrid_system.add_device(join_1)
    join_2 = Device('join 2')
    hybrid_system.add_device(join_2)
    join_3 = Device('join 3')
    hybrid_system.add_device(join_3)

    ironmaking_device_names = [fluidized_bed_1.name, fluidized_bed_2.name]
    if prereduction_perc > 33.3333334:
        # More reduction takes place in the fluidized beds, so need 
        # additional devices. This is why the prereduction percent variable 
        # must be set here.
        h2_heater_2 = Device('h2 heater 2')
        hybrid_system.add_device(h2_heater_2)
        fluidized_bed_3 = Device('fluidized bed 3', dri_capex_wortler2013() / 3 * annual_capacity_tls)
        hybrid_system.add_device(fluidized_bed_3)
        ironmaking_device_names += [fluidized_bed_3.name]

    # System variables defaults. Can be overwritten by user before mass and energy flows.
    hybrid_system.system_vars['cheap electricity hours'] = 8.0
    hybrid_system.system_vars['h2 storage hours of operation'] = 24.0 - hybrid_system.system_vars['cheap electricity hours']
    hybrid_system.system_vars['fluidized beds reduction percent'] = prereduction_perc
    hybrid_system.system_vars['steelmaking device name'] = plasma_smelter.name
    hybrid_system.system_vars['feo soluble in slag percent'] = 27.0
    hybrid_system.system_vars['plasma temp K'] = 2500 
    hybrid_system.system_vars['plasma reduction percent'] = 95.0
    hybrid_system.system_vars['final reduction percent'] = hybrid_system.system_vars['plasma reduction percent']
    hybrid_system.system_vars['plasma torch electro-thermal eff pecent'] = 55.0
    hybrid_system.system_vars['steel exit temp K'] = celsius_to_kelvin(1650)
    hybrid_system.system_vars['o2 injection kg'] = 0.0
    hybrid_system.system_vars['plasma h2 excess ratio'] = 1.5
    hybrid_system.system_vars['steelmaking bath temp K'] = hybrid_system.system_vars['steel exit temp K']
    hybrid_system.system_vars['b2 basicity'] = 2.0
    hybrid_system.system_vars['b4 basicity'] = 2.1
    hybrid_system.system_vars['ore heater device name'] = ore_heater.name
    hybrid_system.system_vars['ore heater temp K'] = celsius_to_kelvin(800)
    hybrid_system.system_vars['ironmaking device names'] = ironmaking_device_names
    hybrid_system.system_vars['fluidized beds h2 excess ratio'] = 4.0
    hybrid_system.system_vars['electrolysis lhv efficiency percent'] = 70.0
    hybrid_system.system_vars['hydrogen loops'] = [ironmaking_device_names, [plasma_smelter.name]]
    hybrid_system.system_vars['h2 consuming device names'] = ironmaking_device_names + [plasma_smelter.name]
    hybrid_system.system_vars['scrap perc'] = 0.0
    hybrid_system.system_vars['steel carbon perc'] = 1.0
    hybrid_system.system_vars['max heat exchanger temp K'] = celsius_to_kelvin(1400)
    if h2_storage_method is not None:
        hybrid_system.system_vars['h2 storage method'] = h2_storage_method

    # electrolysis flows
    hybrid_system.add_input(water_electrolysis.name, create_dummy_species('h2o'))
    hybrid_system.add_output(water_electrolysis.name, create_dummy_species('o2'))
    if h2_storage_method is not None:
        electricity_type = 'cheap electricity'
    else:
        electricity_type = 'base electricity'
    hybrid_system.add_input(water_electrolysis.name, EnergyFlow(electricity_type))
    hybrid_system.add_output(water_electrolysis.name, EnergyFlow('losses'))
    hybrid_system.add_output(water_electrolysis.name, EnergyFlow('chemical'))

    # h2 storage
    if h2_storage_method is not None:
        hybrid_system.add_flow(water_electrolysis.name, h2_storage.name, create_dummy_species('h2 rich gas'))
        hybrid_system.add_input(h2_storage.name, EnergyFlow('cheap electricity'))
        hybrid_system.add_output(h2_storage.name, EnergyFlow('losses'))

    # condenser
    hybrid_system.add_output(condenser.name, create_dummy_species('h2o'))
    hybrid_system.add_output(condenser.name, EnergyFlow('losses'))
    hybrid_system.add_output(condenser.name, create_dummy_mixture('carbon gas'))
    hybrid_system.add_flow(h2_heat_exchanger.name, condenser.name, create_dummy_mixture('recycled h2 rich gas'))

    # join 1
    hybrid_system.add_flow(condenser.name, join_1.name, create_dummy_species('recycled h2 rich gas'))
    if h2_storage_method is not None:
        hybrid_system.add_flow(h2_storage.name, join_1.name, create_dummy_species('h2 rich gas'))
    else:
        hybrid_system.add_flow(water_electrolysis.name, join_1.name, create_dummy_species('h2 rich gas'))

    # heat exchanger
    hybrid_system.add_flow(join_1.name, h2_heat_exchanger.name, create_dummy_species('h2 rich gas'))
    hybrid_system.add_flow(join_3.name, h2_heat_exchanger.name, create_dummy_mixture('recycled h2 rich gas'))
    hybrid_system.add_output(h2_heat_exchanger.name, EnergyFlow('losses'))

    # join 3
    hybrid_system.add_flow(plasma_smelter.name, join_3.name, create_dummy_mixture('waste plasma h2 rich gas'))
    hybrid_system.add_flow(fluidized_bed_1.name, join_3.name, create_dummy_mixture('waste dri h2 rich gas'))

    # ore heater
    hybrid_system.add_input(ore_heater.name, create_dummy_mixture('ore'))
    hybrid_system.add_input(ore_heater.name, EnergyFlow('base electricity'))
    hybrid_system.add_output(ore_heater.name, EnergyFlow('losses'))

    # fluidized bed 1
    hybrid_system.add_flow(ore_heater.name, fluidized_bed_1.name, create_dummy_mixture('ore'))
    hybrid_system.add_flow(fluidized_bed_2.name, fluidized_bed_1.name, create_dummy_mixture('h2 rich gas'))
    hybrid_system.add_input(fluidized_bed_1.name, EnergyFlow('chemical'))
    hybrid_system.add_output(fluidized_bed_1.name, EnergyFlow('losses'))

    # fluidized bed 2
    hybrid_system.add_flow(fluidized_bed_1.name, fluidized_bed_2.name, create_dummy_mixture('dri'))
    hybrid_system.add_flow(h2_heater_1.name, fluidized_bed_2.name, create_dummy_mixture('h2 rich gas'))
    hybrid_system.add_input(fluidized_bed_2.name, EnergyFlow('chemical'))
    hybrid_system.add_output(fluidized_bed_2.name, EnergyFlow('losses'))

    # heater 1
    hybrid_system.add_input(h2_heater_1.name, EnergyFlow('base electricity'))
    hybrid_system.add_output(h2_heater_1.name, EnergyFlow('losses'))

    if 'fluidized bed 3' in hybrid_system.devices:
        # fluidized bed 3
        hybrid_system.add_flow(fluidized_bed_2.name, fluidized_bed_3.name, create_dummy_mixture('dri'))
        hybrid_system.add_flow(h2_heater_2.name, fluidized_bed_3.name, create_dummy_mixture('h2 rich gas'))
        hybrid_system.add_input(fluidized_bed_3.name, EnergyFlow('chemical'))
        hybrid_system.add_output(fluidized_bed_3.name, EnergyFlow('losses'))

        # heater 2
        hybrid_system.add_flow(join_2.name, h2_heater_2.name, create_dummy_species('h2 rich gas'))
        hybrid_system.add_input(h2_heater_2.name, EnergyFlow('base electricity'))
        hybrid_system.add_output(h2_heater_2.name, EnergyFlow('losses'))

        # heater 1
        hybrid_system.add_flow(fluidized_bed_3.name, h2_heater_1.name, create_dummy_mixture('h2 rich gas'))
    else:
        # heater 1
        hybrid_system.add_flow(join_2.name, h2_heater_1.name, create_dummy_species('h2 rich gas'))

    # join 2
    hybrid_system.add_flow(h2_heat_exchanger.name, join_2.name, create_dummy_species('h2 rich gas'))

    # briquetting
    hybrid_system.add_flow(ironmaking_device_names[-1], briquetting.name, create_dummy_mixture('dri'))

    # plasma torch
    hybrid_system.add_flow(join_2.name, plasma_torch.name, create_dummy_species('pre plasma h2 rich gas'))
    hybrid_system.add_input(plasma_torch.name, EnergyFlow('base electricity'))
    hybrid_system.add_output(plasma_torch.name, EnergyFlow('losses'))

    # plasma smelter
    hybrid_system.add_flow(briquetting.name, plasma_smelter.name, create_dummy_mixture('hbi'))
    hybrid_system.add_flow(plasma_torch.name, plasma_smelter.name, create_dummy_species('plasma h2 rich gas'))
    hybrid_system.add_input(plasma_smelter.name, EnergyFlow('chemical'))
    hybrid_system.add_output(plasma_smelter.name, EnergyFlow('losses'))
    hybrid_system.add_input(plasma_smelter.name, create_dummy_species('carbon'))
    hybrid_system.add_input(plasma_smelter.name, create_dummy_mixture('flux'))
    hybrid_system.add_input(plasma_smelter.name, create_dummy_species('o2'))
    hybrid_system.add_input(plasma_smelter.name, create_dummy_species('scrap'))
    hybrid_system.add_output(plasma_smelter.name, create_dummy_mixture('slag'))
    hybrid_system.add_output(plasma_smelter.name, create_dummy_mixture('steel'))

    return hybrid_system

# Capex helpers
# Capex data is derived form the literature
# Biag2016
# 2015 reference yea. 
def dri_capex_biag2018():
    # Midrex DRI Shaft furnace.
    inflation_2015_2023 = 1.28
    dri_shaft_furnace_reference_cpt = 199.9 * inflation_2015_2023 # $ / tonne
    return dri_shaft_furnace_reference_cpt

def eaf_capex_biag2018():
    inflation_2015_2023 = 1.28
    eaf_reference_cpt = 111.43 * inflation_2015_2023 # $ / tonne
    return eaf_reference_cpt

# Vogl2018
# Inflation never explicity stated. Using 2018
# Uses Wortler2013 for the capital cost of the DRI and EAF plant.
def electrolyser_capex_vogl2018():
    inflation_2018_2023 = 1.21
    usd_per_euro_2018 = 1.180
    electrolyser_reference_cpt = 160 * inflation_2018_2023 * usd_per_euro_2018 # $ / tonne
    return electrolyser_reference_cpt

# Fischedick2014
# Reference year not explicitly statedn for Capex data. Using 2014. 
# Uses Wortler2013 for the capital cost of the DRI and EAF plant.
def electrolyser_capex_fischedick2014():
    inflation_2014_2023 = 1.28
    usd_per_euro_2014 = 1.38
    electrolyser_reference_cpt = 450 * inflation_2014_2023 * usd_per_euro_2014 # $ / tonne
    return electrolyser_reference_cpt

# Wortler2013
# Reference year for the capex data is 2010, so adjust by inflation to 2023.
# Methods return the capex in USD / tonne of CS
def dri_capex_wortler2013():
    inflation_2010_2023 = 1.39
    usd_per_euro_2010 = 1.33
    dri_reference_cpt = 230 * inflation_2010_2023 * usd_per_euro_2010 
    return dri_reference_cpt

def eaf_capex_wortler2013():
    inflation_2010_2023 = 1.39
    usd_per_euro_2010 = 1.33
    eaf_reference_cpt = 184 * inflation_2010_2023 * usd_per_euro_2010 
    return eaf_reference_cpt

def smelter_capex_wortler2013():
    inflation_2010_2023 = 1.39
    usd_per_euro_2010 = 1.33
    smelter_reference_cpt = 265 * inflation_2010_2023 * usd_per_euro_2010
    return smelter_reference_cpt

def bof_capex_wortler2013():
    inflation_2010_2023 = 1.39
    usd_per_euro_2010 = 1.33
    bof_reference_cpt = 128 * inflation_2010_2023 * usd_per_euro_2010
    return bof_reference_cpt

def bf_capex_wortler2013():
    inflation_2010_2023 = 1.39
    usd_per_euro_2010 = 1.33
    bf_reference_cpt = 149 * inflation_2010_2023 * usd_per_euro_2010
    return bf_reference_cpt

def sinter_capex_wortler2013():
    inflation_2010_2023 = 1.39
    usd_per_euro_2010 = 1.33
    sinter_reference_cpt = 51 * inflation_2010_2023 * usd_per_euro_2010
    return sinter_reference_cpt

def coke_capex_wortler2013():
    inflation_2010_2023 = 1.39
    usd_per_euro_2010 = 1.33
    coke_reference_cpt = 114 * inflation_2010_2023 * usd_per_euro_2010
    return coke_reference_cpt

# DeSantis2021
# No specific reference year specified, and inflation never mentioned. Using 2021.
# Uses Wortler2013 for the capital cost of the DRI and EAF plant.
def electrolyser_capex_desantis2021():
    inflation_2021_2023 = 1.12
    usd_per_euro_2021 = 1.183 
    electrolyser_reference_cpt = 90 * inflation_2021_2023 * usd_per_euro_2021 # $ / tonne
    return electrolyser_reference_cpt

def plasma_capex_desantis2021():
    # Assumes a plama reactor itself will be 10% more expensive than a state of the art EAF plant.
    # Uses Wortler2013 as the reference price of the EAF. 
    # Although DeSantis then notes that the rest of the plant will require more expensive equipment,
    # which will 2x the cost again. Little justification but says it is inline with industry consultation.
    plasma_reference_cpt = eaf_capex_wortler2013() * 1.1 * 2 # $ / tonne
    return plasma_reference_cpt

# Gielan2020
# Gielen takes this table directly from Mayer2019 and converts to USD. 
# IN general, much more expensive than other sources. Highlights the large error bars in these estimates. 
def plasma_capex_gielen2020():
    inflation_2020_2023 = 1.18
    plasma_reference_cpt = 1179 * inflation_2020_2023 # $ / tonne
    return plasma_reference_cpt

def dri_eaf_capex_gielen2020(): # This doesn't include the electrolyser cost. Why is it so much higher?
    inflation_2020_2023 = 1.18
    dri_eaf_reference_cpt = 1258 * inflation_2020_2023 # $ / tonne
    return dri_eaf_reference_cpt


if __name__ == "__main__":
    main()
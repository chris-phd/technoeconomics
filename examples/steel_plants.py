#!/usr/bin/env python3

import sys
import os

try:
    from technoeconomics.species import create_dummy_species, create_dummy_mixture
    from technoeconomics.system import System, Device, EnergyFlow
    from technoeconomics.utils import celsius_to_kelvin
except ImportError:
    # If the technoeconomics package is not installed via pip,
    # add the package directory to the system path.
    examples_dir = os.path.dirname(os.path.abspath(__file__))
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
def create_plasma_system(system_name='plasma steelmaking') -> System:
    plasma_system = System(system_name)

    water_electrolysis = Device('water electrolysis')
    plasma_system.add_device(water_electrolysis)
    # h2_storage = Device('h2 storage')
    # plasma_system.add_device(h2_storage)
    h2_heat_exchanger = Device('h2 heat exchanger')
    plasma_system.add_device(h2_heat_exchanger)
    condenser = Device('condenser and scrubber')
    plasma_system.add_device(condenser)
    ore_heater = Device('ore heater')
    plasma_system.add_device(ore_heater)
    plasma_smelter = Device('plasma smelter')
    plasma_system.add_device(plasma_smelter)
    join_1 = Device('join 1')
    plasma_system.add_device(join_1)

    # System variables defaults. Can be overwritten by user before mass and energy flows.
    plasma_system.system_vars['steelmaking device name'] = plasma_smelter.name
    plasma_system.system_vars['feo soluble in slag percent'] = 27.0
    plasma_system.system_vars['plasma reaction temp K'] = 2500 
    plasma_system.system_vars['plasma reduction percent'] = 95.0
    plasma_system.system_vars['final reduction percent'] = plasma_system.system_vars['plasma reduction percent']
    plasma_system.system_vars['plasma h2 excess ratio'] = 1.5
    plasma_system.system_vars['o2 injection kg'] = 0.0
    plasma_system.system_vars['plasma torch eff pecent'] = 55.0
    plasma_system.system_vars['steel exit temp K'] = celsius_to_kelvin(1650)
    plasma_system.system_vars['steelmaking bath temp K'] = plasma_system.system_vars['steel exit temp K']
    plasma_system.system_vars['b2 basicity'] = 2.0
    plasma_system.system_vars['b4 basicity'] = 2.1
    plasma_system.system_vars['ore heater device name'] = ore_heater.name
    plasma_system.system_vars['ore heater temp K'] = celsius_to_kelvin(1450)
    plasma_system.system_vars['ironmaking device names'] = [plasma_smelter.name]
    plasma_system.system_vars['electrolysis lhv efficiency percent'] = 70.0
    plasma_system.system_vars['h2 consuming device names'] = plasma_system.system_vars['ironmaking device names']

    # electrolysis flows
    plasma_system.add_input(water_electrolysis.name, create_dummy_species('h2o'))
    plasma_system.add_output(water_electrolysis.name, create_dummy_species('o2'))
    plasma_system.add_input(water_electrolysis.name, EnergyFlow('electricity'))
    plasma_system.add_output(water_electrolysis.name, EnergyFlow('losses'))
    plasma_system.add_output(water_electrolysis.name, EnergyFlow('chemical'))


    # condenser
    plasma_system.add_output(condenser.name, create_dummy_species('h2o'))
    plasma_system.add_output(condenser.name, EnergyFlow('losses'))
    plasma_system.add_output(condenser.name, create_dummy_mixture('co co2'))
    plasma_system.add_flow(h2_heat_exchanger.name, condenser.name, create_dummy_mixture('h2 rich gas'))

    # h2 joiner
    plasma_system.add_flow(condenser.name, join_1.name, create_dummy_species('h2 rich gas'))
    plasma_system.add_flow(water_electrolysis.name, join_1.name, create_dummy_species('h2 rich gas'))

    # heat exchanger
    plasma_system.add_flow(join_1.name, h2_heat_exchanger.name, create_dummy_species('h2 rich gas'))
    plasma_system.add_flow(plasma_smelter.name, h2_heat_exchanger.name, create_dummy_mixture('h2 rich gas'))
    plasma_system.add_output(h2_heat_exchanger.name, EnergyFlow('losses'))

    # ore heater
    plasma_system.add_input(ore_heater.name, create_dummy_mixture('ore'))
    plasma_system.add_input(ore_heater.name, EnergyFlow('electricity'))
    plasma_system.add_output(ore_heater.name, EnergyFlow('losses'))

    # plasma smelter
    plasma_system.add_flow(ore_heater.name, plasma_smelter.name, create_dummy_mixture('ore'))
    plasma_system.add_flow(h2_heat_exchanger.name, plasma_smelter.name, create_dummy_species('h2 rich gas'))
    plasma_system.add_input(plasma_smelter.name, EnergyFlow('electricity'))
    plasma_system.add_output(plasma_smelter.name, EnergyFlow('losses'))
    plasma_system.add_input(plasma_smelter.name, EnergyFlow('chemical'))
    plasma_system.add_input(plasma_smelter.name, create_dummy_species('carbon'))
    plasma_system.add_input(plasma_smelter.name, create_dummy_mixture('flux'))
    plasma_system.add_input(plasma_smelter.name, create_dummy_species('o2'))
    plasma_system.add_output(plasma_smelter.name, create_dummy_mixture('slag'))
    plasma_system.add_output(plasma_smelter.name, create_dummy_mixture('steel'))

    return plasma_system


def create_dri_eaf_system(system_name='dri eaf steelmaking') -> System:
    dri_eaf_system = System(system_name)

    water_electrolysis = Device('water electrolysis')
    dri_eaf_system.add_device(water_electrolysis)
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
    fluidized_bed_1 = Device('fluidized bed 1')
    dri_eaf_system.add_device(fluidized_bed_1)
    fluidized_bed_2 = Device('fluidized bed 2')
    dri_eaf_system.add_device(fluidized_bed_2)
    fluidized_bed_3 = Device('fluidized bed 3')
    dri_eaf_system.add_device(fluidized_bed_3)
    briquetting = Device('briquetting')
    dri_eaf_system.add_device(briquetting)
    eaf = Device('eaf')
    dri_eaf_system.add_device(eaf)

    # System variables defaults. Can be overwritten by user before mass and energy flows.
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
    dri_eaf_system.system_vars['h2 consuming device names'] = dri_eaf_system.system_vars['ironmaking device names']

    # electrolysis flows
    dri_eaf_system.add_input(water_electrolysis.name, create_dummy_species('h2o'))
    dri_eaf_system.add_output(water_electrolysis.name, create_dummy_species('o2'))
    dri_eaf_system.add_input(water_electrolysis.name, EnergyFlow('electricity'))
    dri_eaf_system.add_output(water_electrolysis.name, EnergyFlow('losses'))
    dri_eaf_system.add_output(water_electrolysis.name, EnergyFlow('chemical'))

    # condenser
    dri_eaf_system.add_output(condenser.name, create_dummy_species('h2o'))
    dri_eaf_system.add_output(condenser.name, EnergyFlow('losses'))
    dri_eaf_system.add_flow(h2_heat_exchanger.name, condenser.name, create_dummy_mixture('h2 rich gas'))

    # h2 joiner
    dri_eaf_system.add_flow(condenser.name, join_1.name, create_dummy_species('h2 rich gas'))
    dri_eaf_system.add_flow(water_electrolysis.name, join_1.name, create_dummy_species('h2 rich gas'))

    # heat exchanger
    dri_eaf_system.add_flow(join_1.name, h2_heat_exchanger.name, create_dummy_species('h2 rich gas'))
    dri_eaf_system.add_flow(fluidized_bed_1.name, h2_heat_exchanger.name, create_dummy_mixture('h2 rich gas'))
    dri_eaf_system.add_output(h2_heat_exchanger.name, EnergyFlow('losses'))

    # ore heater
    dri_eaf_system.add_input(ore_heater.name, create_dummy_mixture('ore'))
    dri_eaf_system.add_input(ore_heater.name, EnergyFlow('electricity'))
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
    dri_eaf_system.add_input(h2_heater_1.name, EnergyFlow('electricity'))
    dri_eaf_system.add_output(h2_heater_1.name, EnergyFlow('losses'))

    # fluidized bed 3
    dri_eaf_system.add_flow(fluidized_bed_2.name, fluidized_bed_3.name, create_dummy_mixture('dri'))
    dri_eaf_system.add_flow(h2_heater_2.name, fluidized_bed_3.name, create_dummy_mixture('h2 rich gas'))
    dri_eaf_system.add_input(fluidized_bed_3.name, EnergyFlow('chemical'))
    dri_eaf_system.add_output(fluidized_bed_3.name, EnergyFlow('losses'))

    # heater 2
    dri_eaf_system.add_flow(h2_heat_exchanger.name, h2_heater_2.name, create_dummy_species('h2 rich gas'))
    dri_eaf_system.add_input(h2_heater_2.name, EnergyFlow('electricity'))
    dri_eaf_system.add_output(h2_heater_2.name, EnergyFlow('losses'))

    # briquetting
    dri_eaf_system.add_flow(fluidized_bed_3.name, briquetting.name, create_dummy_mixture('dri'))

    # eaf
    dri_eaf_system.add_flow(briquetting.name, eaf.name, create_dummy_mixture('hbi'))
    dri_eaf_system.add_input(eaf.name, EnergyFlow('electricity'))
    dri_eaf_system.add_output(eaf.name, EnergyFlow('losses'))
    dri_eaf_system.add_input(eaf.name, create_dummy_species('electrode'))
    dri_eaf_system.add_input(eaf.name, EnergyFlow('chemical'))
    dri_eaf_system.add_input(eaf.name, create_dummy_species('carbon'))
    dri_eaf_system.add_input(eaf.name, create_dummy_mixture('flux'))
    dri_eaf_system.add_input(eaf.name, create_dummy_species('o2'))
    dri_eaf_system.add_input(eaf.name, create_dummy_mixture('infiltrated air'))
    dri_eaf_system.add_output(eaf.name, create_dummy_mixture('infiltrated air'))
    dri_eaf_system.add_output(eaf.name, create_dummy_mixture('carbon gas'))
    dri_eaf_system.add_output(eaf.name, create_dummy_mixture('slag'))
    dri_eaf_system.add_output(eaf.name, create_dummy_mixture('steel'))

    return dri_eaf_system


def create_hybrid_system(system_name='hybrid steelmaking', prereduction_perc=33.33) -> System:
    hybrid_system = System(system_name)

    water_electrolysis = Device('water electrolysis')
    hybrid_system.add_device(water_electrolysis)
    h2_heat_exchanger = Device('h2 heat exchanger')
    hybrid_system.add_device(h2_heat_exchanger)
    h2_heater_1 = Device('h2 heater 1')
    hybrid_system.add_device(h2_heater_1)
    condenser = Device('condenser and scrubber')
    hybrid_system.add_device(condenser)
    ore_heater = Device('ore heater')
    hybrid_system.add_device(ore_heater)
    fluidized_bed_1 = Device('fluidized bed 1')
    hybrid_system.add_device(fluidized_bed_1)
    fluidized_bed_2 = Device('fluidized bed 2')
    hybrid_system.add_device(fluidized_bed_2)
    briquetting = Device('briquetting')
    hybrid_system.add_device(briquetting)
    plasma_smelter = Device('plasma smelter')
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
        fluidized_bed_3 = Device('fluidized bed 3')
        hybrid_system.add_device(fluidized_bed_3)
        ironmaking_device_names += [fluidized_bed_3.name]

    # System variables defaults. Can be overwritten by user before mass and energy flows.
    hybrid_system.system_vars['fluidized beds reduction percent'] = prereduction_perc
    hybrid_system.system_vars['steelmaking device name'] = plasma_smelter.name
    hybrid_system.system_vars['feo soluble in slag percent'] = 27.0
    hybrid_system.system_vars['plasma reaction temp K'] = 2500 
    hybrid_system.system_vars['plasma reduction percent'] = 95.0
    hybrid_system.system_vars['final reduction percent'] = hybrid_system.system_vars['plasma reduction percent']
    hybrid_system.system_vars['plasma torch eff pecent'] = 55.0
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
    hybrid_system.system_vars['h2 consuming device names'] = ironmaking_device_names + [plasma_smelter.name]

    # electrolysis flows
    hybrid_system.add_input(water_electrolysis.name, create_dummy_species('h2o'))
    hybrid_system.add_output(water_electrolysis.name, create_dummy_species('o2'))
    hybrid_system.add_input(water_electrolysis.name, EnergyFlow('electricity'))
    hybrid_system.add_output(water_electrolysis.name, EnergyFlow('losses'))
    hybrid_system.add_output(water_electrolysis.name, EnergyFlow('chemical'))


    # condenser
    hybrid_system.add_output(condenser.name, create_dummy_species('h2o'))
    hybrid_system.add_output(condenser.name, EnergyFlow('losses'))
    hybrid_system.add_output(condenser.name, create_dummy_mixture('co co2'))
    hybrid_system.add_flow(h2_heat_exchanger.name, condenser.name, create_dummy_mixture('h2 rich gas'))

    # h2 joiner 1
    hybrid_system.add_flow(condenser.name, join_1.name, create_dummy_species('h2 rich gas'))
    hybrid_system.add_flow(water_electrolysis.name, join_1.name, create_dummy_species('h2 rich gas'))

    # heat exchanger
    hybrid_system.add_flow(join_1.name, h2_heat_exchanger.name, create_dummy_species('h2 rich gas'))
    hybrid_system.add_flow(join_3.name, h2_heat_exchanger.name, create_dummy_mixture('h2 rich gas'))
    hybrid_system.add_output(h2_heat_exchanger.name, EnergyFlow('losses'))

    # join 3
    hybrid_system.add_flow(plasma_smelter.name, join_3.name, create_dummy_mixture('h2 rich gas'))
    hybrid_system.add_flow(fluidized_bed_1.name, join_3.name, create_dummy_mixture('h2 rich gas'))

    # ore heater
    hybrid_system.add_input(ore_heater.name, create_dummy_mixture('ore'))
    hybrid_system.add_input(ore_heater.name, EnergyFlow('electricity'))
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
    hybrid_system.add_input(h2_heater_1.name, EnergyFlow('electricity'))
    hybrid_system.add_output(h2_heater_1.name, EnergyFlow('losses'))

    if 'fluidized bed 3' in hybrid_system.devices:
        # fluidized bed 3
        hybrid_system.add_flow(fluidized_bed_2.name, fluidized_bed_3.name, create_dummy_mixture('dri'))
        hybrid_system.add_flow(h2_heater_2.name, fluidized_bed_3.name, create_dummy_mixture('h2 rich gas'))
        hybrid_system.add_input(fluidized_bed_3.name, EnergyFlow('chemical'))
        hybrid_system.add_output(fluidized_bed_3.name, EnergyFlow('losses'))

        # heater 2
        hybrid_system.add_flow(join_2.name, h2_heater_2.name, create_dummy_species('h2 rich gas'))
        hybrid_system.add_input(h2_heater_2.name, EnergyFlow('electricity'))
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

    # plasma smelter
    hybrid_system.add_flow(briquetting.name, plasma_smelter.name, create_dummy_mixture('hbi'))
    hybrid_system.add_flow(join_2.name, plasma_smelter.name, create_dummy_species('h2 rich gas'))
    hybrid_system.add_input(plasma_smelter.name, EnergyFlow('electricity'))
    hybrid_system.add_input(plasma_smelter.name, EnergyFlow('chemical'))
    hybrid_system.add_output(plasma_smelter.name, EnergyFlow('losses'))
    hybrid_system.add_input(plasma_smelter.name, create_dummy_species('carbon'))
    hybrid_system.add_input(plasma_smelter.name, create_dummy_mixture('flux'))
    hybrid_system.add_input(plasma_smelter.name, create_dummy_species('o2'))
    hybrid_system.add_output(plasma_smelter.name, create_dummy_mixture('slag'))
    hybrid_system.add_output(plasma_smelter.name, create_dummy_mixture('steel'))

    return hybrid_system

if __name__ == "__main__":
    main()
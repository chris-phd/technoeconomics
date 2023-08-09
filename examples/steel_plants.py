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

    plasma_system.render()
    dri_eaf_system.render()
    hybrid33_system.render()
    hybrid95_system.render()


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
    plasma_system.system_vars['feo percent in slag'] = 27.0
    plasma_system.system_vars['steel exit temp K'] = celsius_to_kelvin(1650)
    plasma_system.system_vars['b2 basicity'] = 2.0
    plasma_system.system_vars['b4 basicity'] = 2.1

    # electrolysis flows
    electrolyser_water = create_dummy_species('h2o')
    plasma_system.add_input(water_electrolysis.name, electrolyser_water)
    electrolyser_o2 = create_dummy_species('o2')
    plasma_system.add_output(water_electrolysis.name, electrolyser_o2)
    electrolyser_electricity = EnergyFlow('electricity')
    plasma_system.add_input(water_electrolysis.name, electrolyser_electricity)
    electrolyser_losses = EnergyFlow('losses')
    plasma_system.add_output(water_electrolysis.name, electrolyser_losses)

    # condenser
    condenser_h2o = create_dummy_species('h2o')
    plasma_system.add_output(condenser.name, condenser_h2o)
    condenser_losses = EnergyFlow('losses')
    plasma_system.add_output(condenser.name, condenser_losses)
    condenser_out_gas = create_dummy_mixture('co co2')
    plasma_system.add_output(condenser.name, condenser_out_gas)
    hot_h2o_h2_out = create_dummy_mixture('h2 h2o co co2')
    plasma_system.add_flow(h2_heat_exchanger.name, condenser.name, hot_h2o_h2_out)

    # h2 joiner
    recycled_h2 = create_dummy_species('h2')
    plasma_system.add_flow(condenser.name, join_1.name, recycled_h2)
    new_h2 = create_dummy_species('h2')
    plasma_system.add_flow(water_electrolysis.name, join_1.name, new_h2)

    # heat exchanger
    cold_h2_in = create_dummy_species('h2')
    plasma_system.add_flow(join_1.name, h2_heat_exchanger.name, cold_h2_in)
    plasma_off_gas = create_dummy_mixture('h2 h2o co co2')
    plasma_system.add_flow(plasma_smelter.name, h2_heat_exchanger.name, plasma_off_gas)
    heat_exchanger_losses = EnergyFlow('losses')
    plasma_system.add_output(h2_heat_exchanger.name, heat_exchanger_losses)

    # ore heater
    ore_in = create_dummy_mixture('ore')
    plasma_system.add_input(ore_heater.name, ore_in)
    ore_heater_electricity = EnergyFlow('electricity')
    plasma_system.add_input(ore_heater.name, ore_heater_electricity)
    ore_heater_losses = EnergyFlow('losses')
    plasma_system.add_output(ore_heater.name, ore_heater_losses)

    # plasma smelter
    plasma_ore = create_dummy_mixture('ore')
    plasma_system.add_flow(ore_heater.name, plasma_smelter.name, plasma_ore)
    plasma_h2 = create_dummy_species('h2')
    plasma_system.add_flow(h2_heat_exchanger.name, plasma_smelter.name, plasma_h2)
    plasma_smelter_electricity = EnergyFlow('electricity')
    plasma_system.add_input(plasma_smelter.name, plasma_smelter_electricity)
    plasma_smelter_losses = EnergyFlow('losses')
    plasma_system.add_output(plasma_smelter.name, plasma_smelter_losses)
    plasma_carbon = create_dummy_species('carbon')
    plasma_system.add_input(plasma_smelter.name, plasma_carbon)
    plasma_flux = create_dummy_mixture('flux')
    plasma_system.add_input(plasma_smelter.name, plasma_flux)
    plasma_o2 = create_dummy_species('o2')
    plasma_system.add_input(plasma_smelter.name, plasma_o2)
    plasma_slag = create_dummy_mixture('slag')
    plasma_system.add_output(plasma_smelter.name, plasma_slag)
    steel_out = create_dummy_mixture('steel')
    plasma_system.add_output(plasma_smelter.name, steel_out)

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
    dri_eaf_system.system_vars['steelmaking device name'] = eaf.name
    dri_eaf_system.system_vars['feo percent in slag'] = 27.0
    dri_eaf_system.system_vars['steel exit temp K'] = celsius_to_kelvin(1650)
    dri_eaf_system.system_vars['b2 basicity'] = 2.0
    dri_eaf_system.system_vars['b4 basicity'] = 1.8

    # electrolysis flows
    electrolyser_water = create_dummy_species('h2o')
    dri_eaf_system.add_input(water_electrolysis.name, electrolyser_water)
    electrolyser_o2 = create_dummy_species('o2')
    dri_eaf_system.add_output(water_electrolysis.name, electrolyser_o2)
    electrolyser_electricity = EnergyFlow('electricity')
    dri_eaf_system.add_input(water_electrolysis.name, electrolyser_electricity)
    electrolyser_losses = EnergyFlow('losses')
    dri_eaf_system.add_output(water_electrolysis.name, electrolyser_losses)

    # condenser
    condenser_h2o = create_dummy_species('h2o')
    dri_eaf_system.add_output(condenser.name, condenser_h2o)
    condenser_losses = EnergyFlow('losses')
    dri_eaf_system.add_output(condenser.name, condenser_losses)
    hot_h2o_h2_out = create_dummy_mixture('h2 h2o')
    dri_eaf_system.add_flow(h2_heat_exchanger.name, condenser.name, hot_h2o_h2_out)

    # h2 joiner
    recycled_h2 = create_dummy_species('h2')
    dri_eaf_system.add_flow(condenser.name, join_1.name, recycled_h2)
    new_h2 = create_dummy_species('h2')
    dri_eaf_system.add_flow(water_electrolysis.name, join_1.name, new_h2)

    # heat exchanger
    cold_h2_in = create_dummy_species('h2')
    dri_eaf_system.add_flow(join_1.name, h2_heat_exchanger.name, cold_h2_in)
    hot_h2o_h2_in = create_dummy_mixture('h2 h2o')
    dri_eaf_system.add_flow(fluidized_bed_1.name, h2_heat_exchanger.name, hot_h2o_h2_in)
    heat_exchanger_losses = EnergyFlow('losses')
    dri_eaf_system.add_output(h2_heat_exchanger.name, heat_exchanger_losses)

    # ore heater
    ore_in = create_dummy_mixture('ore')
    dri_eaf_system.add_input(ore_heater.name, ore_in)
    ore_heater_electricity = EnergyFlow('electricity')
    dri_eaf_system.add_input(ore_heater.name, ore_heater_electricity)
    ore_heater_losses = EnergyFlow('losses')
    dri_eaf_system.add_output(ore_heater.name, ore_heater_losses)

    # fluidized bed 1
    fluidized_bed_1_ore = create_dummy_mixture('ore')
    dri_eaf_system.add_flow(ore_heater.name, fluidized_bed_1.name, fluidized_bed_1_ore)
    fluidized_bed_1_h2 = create_dummy_mixture('h2 h2o')
    dri_eaf_system.add_flow(fluidized_bed_2.name, fluidized_bed_1.name, fluidized_bed_1_h2)
    fluidized_bed_1_losses = EnergyFlow('losses')
    dri_eaf_system.add_output(fluidized_bed_1.name, fluidized_bed_1_losses)

    # fluidized bed 2
    fluidized_bed_2_ore = create_dummy_mixture('ore')
    dri_eaf_system.add_flow(fluidized_bed_1.name, fluidized_bed_2.name, fluidized_bed_2_ore)
    fluidized_bed_2_h2 = create_dummy_mixture('h2 h2o')
    dri_eaf_system.add_flow(h2_heater_1.name, fluidized_bed_2.name, fluidized_bed_2_h2)
    fluidized_bed_2_losses = EnergyFlow('losses')
    dri_eaf_system.add_output(fluidized_bed_2.name, fluidized_bed_2_losses)

    # heater 1
    h2_heater_1_gas = create_dummy_mixture('h2 h2o')
    dri_eaf_system.add_flow(fluidized_bed_3.name, h2_heater_1.name, h2_heater_1_gas)
    h2_heater_1_electricity = EnergyFlow('electricity')
    dri_eaf_system.add_input(h2_heater_1.name, h2_heater_1_electricity)
    h2_heater_1_losses = EnergyFlow('losses')
    dri_eaf_system.add_output(h2_heater_1.name, h2_heater_1_losses)

    # fluidized bed 3
    fluidized_bed_3_ore = create_dummy_mixture('ore')
    dri_eaf_system.add_flow(fluidized_bed_2.name, fluidized_bed_3.name, fluidized_bed_3_ore)
    fluidized_bed_3_h2 = create_dummy_species('h2')
    dri_eaf_system.add_flow(h2_heater_2.name, fluidized_bed_3.name, fluidized_bed_3_h2)
    fluidized_bed_3_losses = EnergyFlow('losses')
    dri_eaf_system.add_output(fluidized_bed_3.name, fluidized_bed_3_losses)

    # heater 2
    h2_heater_2_gas = create_dummy_species('h2')
    dri_eaf_system.add_flow(h2_heat_exchanger.name, h2_heater_2.name, h2_heater_2_gas)
    h2_heater_2_electricity = EnergyFlow('electricity')
    dri_eaf_system.add_input(h2_heater_2.name, h2_heater_2_electricity)
    h2_heater_2_losses = EnergyFlow('losses')
    dri_eaf_system.add_output(h2_heater_2.name, h2_heater_2_losses)

    # briquetting
    briquetting_dri = create_dummy_mixture('dri')
    dri_eaf_system.add_flow(fluidized_bed_3.name, briquetting.name, briquetting_dri)

    # eaf
    eaf_hbi = create_dummy_mixture('hbi')
    dri_eaf_system.add_flow(briquetting.name, eaf.name, eaf_hbi)
    eaf_smelter_electricity = EnergyFlow('electricity')
    dri_eaf_system.add_input(eaf.name, eaf_smelter_electricity)
    eaf_smelter_losses = EnergyFlow('losses')
    dri_eaf_system.add_output(eaf.name, eaf_smelter_losses)
    eaf_electrode = create_dummy_species('electrode')
    dri_eaf_system.add_input(eaf.name, eaf_electrode)
    eaf_carbon = create_dummy_species('carbon')
    dri_eaf_system.add_input(eaf.name, eaf_carbon)
    eaf_flux = create_dummy_mixture('flux')
    dri_eaf_system.add_input(eaf.name, eaf_flux)
    eaf_o2 = create_dummy_species('o2')
    dri_eaf_system.add_input(eaf.name, eaf_o2)
    eaf_slag = create_dummy_mixture('slag')
    dri_eaf_system.add_output(eaf.name, eaf_slag)
    eaf_steel = create_dummy_mixture('steel')
    dri_eaf_system.add_output(eaf.name, eaf_steel)

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
    if prereduction_perc > 33.3333334:
        # More reduction takes place in the fluidized beds, so need 
        # additional devices. This is why the prereduction percent variable 
        # must be set here.
        h2_heater_2 = Device('h2 heater 2')
        hybrid_system.add_device(h2_heater_2)
        fluidized_bed_3 = Device('fluidized bed 3')
        hybrid_system.add_device(fluidized_bed_3)

    # System variables defaults. Can be overwritten by user before mass and energy flows.
    hybrid_system.system_vars['prereduction percent'] = prereduction_perc
    hybrid_system.system_vars['steelmaking device name'] = plasma_smelter.name
    hybrid_system.system_vars['feo percent in slag'] = 27.0
    hybrid_system.system_vars['steel exit temp K'] = celsius_to_kelvin(1650)
    hybrid_system.system_vars['b2 basicity'] = 2.0
    hybrid_system.system_vars['b4 basicity'] = 2.1

    # electrolysis flows
    electrolyser_water = create_dummy_species('h2o')
    hybrid_system.add_input(water_electrolysis.name, electrolyser_water)
    electrolyser_o2 = create_dummy_species('o2')
    hybrid_system.add_output(water_electrolysis.name, electrolyser_o2)
    electrolyser_electricity = EnergyFlow('electricity')
    hybrid_system.add_input(water_electrolysis.name, electrolyser_electricity)
    electrolyser_losses = EnergyFlow('losses')
    hybrid_system.add_output(water_electrolysis.name, electrolyser_losses)

    # condenser
    condenser_h2o = create_dummy_species('h2o')
    hybrid_system.add_output(condenser.name, condenser_h2o)
    condenser_losses = EnergyFlow('losses')
    hybrid_system.add_output(condenser.name, condenser_losses)
    carbon_off_gas = create_dummy_mixture('co co2')
    hybrid_system.add_output(condenser.name, carbon_off_gas)
    hot_h2o_h2_out = create_dummy_mixture('h2 h2o co co2')
    hybrid_system.add_flow(h2_heat_exchanger.name, condenser.name, hot_h2o_h2_out)

    # h2 joiner 1
    recycled_h2 = create_dummy_species('h2')
    hybrid_system.add_flow(condenser.name, join_1.name, recycled_h2)
    new_h2 = create_dummy_species('h2')
    hybrid_system.add_flow(water_electrolysis.name, join_1.name, new_h2)

    # heat exchanger
    cold_h2_in = create_dummy_species('h2')
    hybrid_system.add_flow(join_1.name, h2_heat_exchanger.name, cold_h2_in)
    hot_h2o_h2_in = create_dummy_species('h2 h2o co co2')
    hybrid_system.add_flow(join_3.name, h2_heat_exchanger.name, hot_h2o_h2_in)
    heat_exchanger_losses = EnergyFlow('losses')
    hybrid_system.add_output(h2_heat_exchanger.name, heat_exchanger_losses)

    # join 3
    plasma_off_gas = create_dummy_mixture('h2 h2o co co2')
    hybrid_system.add_flow(plasma_smelter.name, join_3.name, plasma_off_gas)
    fluidized_bed_off_gas = create_dummy_mixture('h2 h2o')
    hybrid_system.add_flow(fluidized_bed_1.name, join_3.name, fluidized_bed_off_gas)

    # ore heater
    ore_in = create_dummy_mixture('ore')
    hybrid_system.add_input(ore_heater.name, ore_in)
    ore_heater_electricity = EnergyFlow('electricity')
    hybrid_system.add_input(ore_heater.name, ore_heater_electricity)
    ore_heater_losses = EnergyFlow('losses')
    hybrid_system.add_output(ore_heater.name, ore_heater_losses)

    # fluidized bed 1
    fluidized_bed_1_ore = create_dummy_mixture('ore')
    hybrid_system.add_flow(ore_heater.name, fluidized_bed_1.name, fluidized_bed_1_ore)
    fluidized_bed_1_h2 = create_dummy_mixture('h2 h2o')
    hybrid_system.add_flow(fluidized_bed_2.name, fluidized_bed_1.name, fluidized_bed_1_h2)
    fluidized_bed_1_losses = EnergyFlow('losses')
    hybrid_system.add_output(fluidized_bed_1.name, fluidized_bed_1_losses)

    # fluidized bed 2
    fluidized_bed_2_ore = create_dummy_mixture('ore')
    hybrid_system.add_flow(fluidized_bed_1.name, fluidized_bed_2.name, fluidized_bed_2_ore)
    fluidized_bed_2_h2 = create_dummy_mixture('h2 h2o')
    hybrid_system.add_flow(h2_heater_1.name, fluidized_bed_2.name, fluidized_bed_2_h2)
    fluidized_bed_2_losses = EnergyFlow('losses')
    hybrid_system.add_output(fluidized_bed_2.name, fluidized_bed_2_losses)

    # heater 1
    h2_heater_1_electricity = EnergyFlow('electricity')
    hybrid_system.add_input(h2_heater_1.name, h2_heater_1_electricity)
    h2_heater_1_losses = EnergyFlow('losses')
    hybrid_system.add_output(h2_heater_1.name, h2_heater_1_losses)

    if 'fluidized bed 3' in hybrid_system.devices:
        # fluidized bed 3
        fluidized_bed_3_ore = create_dummy_mixture('ore')
        hybrid_system.add_flow(fluidized_bed_2.name, fluidized_bed_3.name, fluidized_bed_3_ore)
        fluidized_bed_3_h2 = create_dummy_species('h2')
        hybrid_system.add_flow(h2_heater_2.name, fluidized_bed_3.name, fluidized_bed_3_h2)
        fluidized_bed_3_losses = EnergyFlow('losses')
        hybrid_system.add_output(fluidized_bed_3.name, fluidized_bed_3_losses)

        # heater 2
        h2_heater_2_gas = create_dummy_species('h2')
        hybrid_system.add_flow(join_2.name, h2_heater_2.name, h2_heater_2_gas)
        h2_heater_2_electricity = EnergyFlow('electricity')
        hybrid_system.add_input(h2_heater_2.name, h2_heater_2_electricity)
        h2_heater_2_losses = EnergyFlow('losses')
        hybrid_system.add_output(h2_heater_2.name, h2_heater_2_losses)

        # heater 1
        h2_heater_1_gas = create_dummy_mixture('h2 h2o')
        hybrid_system.add_flow(fluidized_bed_3.name, h2_heater_1.name, h2_heater_1_gas)

        final_fluidized_bed_name = fluidized_bed_3.name
    else:
        # heater 1
        h2_heater_1_gas = create_dummy_species('h2')
        hybrid_system.add_flow(join_2.name, h2_heater_1.name, h2_heater_1_gas)

        final_fluidized_bed_name = fluidized_bed_2.name

    # join 2
    h2_join_2 = create_dummy_species('h2')
    hybrid_system.add_flow(h2_heat_exchanger.name, join_2.name, h2_join_2)

    # briquetting
    briquetting_dri = create_dummy_mixture('dri')
    hybrid_system.add_flow(final_fluidized_bed_name, briquetting.name, briquetting_dri)

    # plasma smelter
    eaf_hbi = create_dummy_mixture('hbi')
    hybrid_system.add_flow(briquetting.name, plasma_smelter.name, eaf_hbi)
    plasma_h2 = create_dummy_species('h2')
    hybrid_system.add_flow(join_2.name, plasma_smelter.name, plasma_h2)
    plasma_smelter_electricity = EnergyFlow('electricity')
    hybrid_system.add_input(plasma_smelter.name, plasma_smelter_electricity)
    plasma_smelter_losses = EnergyFlow('losses')
    hybrid_system.add_output(plasma_smelter.name, plasma_smelter_losses)
    plasma_carbon = create_dummy_species('carbon')
    hybrid_system.add_input(plasma_smelter.name, plasma_carbon)
    plasma_flux = create_dummy_mixture('flux')
    hybrid_system.add_input(plasma_smelter.name, plasma_flux)
    plasma_o2 = create_dummy_species('o2')
    hybrid_system.add_input(plasma_smelter.name, plasma_o2)
    plasma_slag = create_dummy_mixture('slag')
    hybrid_system.add_output(plasma_smelter.name, plasma_slag)
    steel_out = create_dummy_mixture('steel')
    hybrid_system.add_output(plasma_smelter.name, steel_out)

    return hybrid_system

if __name__ == "__main__":
    main()
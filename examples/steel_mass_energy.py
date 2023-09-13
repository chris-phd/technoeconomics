#!/usr/bin/env python3

import copy
import sys
import os
import numpy as np
import math
import matplotlib.pyplot as plt
from typing import List, Dict
from steel_plants import create_plasma_system, create_dri_eaf_system, create_hybrid_system
from steel_plant_capex import add_steel_plant_capex

try:
    import technoeconomics.species as species 
    from technoeconomics.system import System, EnergyFlow
    from technoeconomics.utils import celsius_to_kelvin
except ImportError:
    # If the technoeconomics package is not installed via pip,
    # add the package directory to the system path.
    examples_dir = os.path.dirname(os.path.abspath(__file__))
    package_dir = os.path.dirname(examples_dir)
    sys.path.insert(0, package_dir)

    import technoeconomics.species as species 
    from technoeconomics.system import System, EnergyFlow
    from technoeconomics.utils import celsius_to_kelvin


def main():
    # TODO: Add transferred and non-transferred arc system.
    annual_steel_production_tonnes = 1.5e6 # tonnes / year
    plant_lifetime_years = 20.0
    plasma_system = create_plasma_system("Plasma SC", annual_steel_production_tonnes, plant_lifetime_years)
    dri_eaf_system = create_dri_eaf_system("DRI-EAF", annual_steel_production_tonnes, plant_lifetime_years)
    hybrid33_system = create_hybrid_system("Hybrid 33", 33.33, annual_steel_production_tonnes, plant_lifetime_years)
    hybrid95_system = create_hybrid_system("Hybrid 95", 95.0, annual_steel_production_tonnes, plant_lifetime_years)

    # Overwrite system vars here to modify behaviour
    plasma_system.system_vars['ore name'] = 'IOB'
    dri_eaf_system.system_vars['h2 storage method'] = 'compressed gas vessels'

    ## Calculate The Mass and Energy Flow
    add_plasma_mass_and_energy(plasma_system)
    add_dri_eaf_mass_and_energy(dri_eaf_system)
    add_hybrid_mass_and_energy(hybrid33_system)
    add_hybrid_mass_and_energy(hybrid95_system)

    ##
    add_steel_plant_capex(plasma_system)
    add_steel_plant_capex(dri_eaf_system)
    add_steel_plant_capex(hybrid33_system)
    add_steel_plant_capex(hybrid95_system)

    ## Energy and Mass Flow Plots
    systems = [plasma_system, dri_eaf_system, hybrid33_system, hybrid95_system]
    system_names = [s.name for s in systems]

    # Plot the energy flow
    electricity_for_systems = [electricity_demand_per_major_device(s) for s in systems]
    electricity_labels = histogram_labels_from_datasets(electricity_for_systems)
    _, energy_ax = plt.subplots()
    add_stacked_histogram_data_to_axis(energy_ax, system_names, electricity_labels, electricity_for_systems)
    add_titles_to_axis(energy_ax, 'Electricity Demand / Tonne Liquid Steel', 'Energy (GJ)')

    # Plot the mass flows
    inputs_per_tonne_for_systems = [s.system_inputs(ignore_flows_named=['infiltrated air'], mass_flow_only=True) for s in systems]
    input_mass_labels = histogram_labels_from_datasets(inputs_per_tonne_for_systems)
    _, input_mass_ax = plt.subplots()
    add_stacked_histogram_data_to_axis(input_mass_ax, system_names, input_mass_labels, inputs_per_tonne_for_systems)
    add_titles_to_axis(input_mass_ax, 'Input Mass Flow / Tonne Liquid Steel', 'Mass (kg)')

    outputs_for_systems = [s.system_outputs(ignore_flows_named=['infiltrated air'], mass_flow_only=True) for s in systems]
    output_mass_labels = histogram_labels_from_datasets(outputs_for_systems)
    _, output_mass_ax = plt.subplots()
    add_stacked_histogram_data_to_axis(output_mass_ax, system_names, output_mass_labels, outputs_for_systems)
    add_titles_to_axis(output_mass_ax, 'Output Mass Flow / Tonne Liquid Steel', 'Mass (kg)')

    # change the subplot configuration setting 'right' to 0.78
    

    plt.show()

    ## Calculate the levelised cost of production
    inputs_per_tonne_for_systems = [s.system_inputs(separate_mixtures_named=['flux'], mass_flow_only=False) for s in systems]

    total_direct_indirect_capex = [capex_direct_and_indirect(s.capex()) for s in systems]
    operating_costs_per_tonne_itemised = [operating_cost_per_tonne(inputs) for inputs in inputs_per_tonne_for_systems]
    annual_opex = [sum(cpt.values()) * system.annual_capacity for cpt, system in zip(operating_costs_per_tonne_itemised, systems)]

    lcop_for_systems = []
    for system, capex, operating_cost in zip(systems, total_direct_indirect_capex, annual_opex):
        cost_of_production = lcop(capex, operating_cost, system.annual_capacity, system.lifetime_years)
        print(f"{system.name} lcop = {cost_of_production:.2f}")
        lcop_for_systems.append(cost_of_production)


# Mass and Energy Flows - System Level
def add_plasma_mass_and_energy(system: System):
    verify_system_vars(system)
    add_ore_composition(system)
    add_steel_out(system)
    add_plasma_flows_initial(system)
    add_ore(system)
    add_plasma_flows_final(system)
    add_electrolysis_flows(system)
    add_h2_storage_flows(system)
    merge_join_flows(system, 'join 1')
    add_heat_exchanger_flows_initial(system)
    add_condenser_and_scrubber_flows_initial(system)
    merge_join_flows(system, 'join 1')
    add_heat_exchanger_flows_final(system)
    add_condenser_and_scrubber_flows_final(system)
    merge_join_flows(system, 'join 1')
    adjust_plasma_energy_flows(system)


def add_dri_eaf_mass_and_energy(system: System):
    verify_system_vars(system)
    add_ore_composition(system)
    add_steel_out(system)
    add_eaf_flows_initial(system)
    add_ore(system)
    add_fluidized_bed_flows(system)
    add_briquetting_flows(system)
    add_eaf_flows_final(system)
    add_electrolysis_flows(system)
    add_h2_storage_flows(system)
    merge_join_flows(system, 'join 1')
    add_heat_exchanger_flows_initial(system)
    add_condenser_and_scrubber_flows_initial(system)
    merge_join_flows(system, 'join 1')
    add_heat_exchanger_flows_final(system)
    add_condenser_and_scrubber_flows_final(system)
    merge_join_flows(system, 'join 1')
    add_h2_heater_flows(system)


def add_hybrid_mass_and_energy(system: System):
    verify_system_vars(system)
    add_ore_composition(system)
    add_steel_out(system)
    add_plasma_flows_initial(system)
    add_ore(system)
    add_fluidized_bed_flows(system)
    add_briquetting_flows(system)
    add_plasma_flows_final(system)
    add_electrolysis_flows(system)
    add_h2_storage_flows(system)
    merge_join_flows(system, 'join 1')
    merge_join_flows(system, 'join 3')
    add_heat_exchanger_flows_initial(system)
    add_condenser_and_scrubber_flows_initial(system)
    merge_join_flows(system, 'join 1')
    merge_join_flows(system, 'join 3')
    add_heat_exchanger_flows_final(system)
    add_condenser_and_scrubber_flows_final(system)
    merge_join_flows(system, 'join 1')
    merge_join_flows(system, 'join 3')
    balance_join2_flows(system)
    adjust_plasma_energy_flows(system)
    add_h2_heater_flows(system)


def verify_system_vars(system: System):
    # TODO.
    # Raise exception if the system variables necessary
    # for calculating the mass and energy flow are not set
    # correctly.
    pass


# Mass and Energy Flows - Device Level
def add_steel_out(system: System):
    # settings
    steel_target_mass = 1000.0 # kg
    steel_carbon_mass_perc = 1.0 # %
    scrap_perc = 0.0 # %

    # create the species
    fe = species.create_fe_species()
    c = species.create_c_species()
    scrap = species.create_scrap_species()
    fe.mass = steel_target_mass * (1 - steel_carbon_mass_perc*0.01) * (1 - scrap_perc*0.01)
    c.mass = steel_target_mass * (1 - scrap_perc*0.01) * steel_carbon_mass_perc * 0.01 # kg
    scrap.mass = steel_target_mass * scrap_perc * 0.01 # kg

    steel = species.Mixture('steel', [fe, c, scrap])
    steel.temp_kelvin = system.system_vars['steel exit temp K']

    steelmaking_device_name = system.system_vars['steelmaking device name']
    system.get_output(steelmaking_device_name, 'steel').set(steel)


def hematite_normalise(ore_comp: Dict[str, float]):
    """
    Changes the Fe% so that all the iron is in hematite.
    Necessary for the code, which assumes pure hematite.
    """
    fe = species.create_fe_species()
    fe2o3 = species.create_fe2o3_species()
    iron_to_hematite_ratio = fe.mm / (0.5 * fe2o3.mm)

    hematite_perc = 100.0 - ore_comp['gangue'] - ore_comp.get('LOI', 0.0)
    iron_perc = hematite_perc * iron_to_hematite_ratio
    if abs(ore_comp['Fe'] - iron_perc) > 1.0:
        raise Exception('Ore composition may not be pure hematite! Cannot safetly normalise')
    ore_comp['Fe'] = iron_perc

    return ore_comp


def add_ore_composition(system: System):
    """
    Add 'ore composition' and 'ore composition simple' to the system variables.
    Ore composition simple is the hematite ore with only SiO2, Al2O3, CaO and MgO
    impurities.
    """

    ore_name = system.system_vars.get('ore name', 'default')
    


    # Mass percent of dry ore.
    # Remaining mass percent is oxygen in the iron oxide.
    # Values are in mass / weight percent.
    if ore_name.upper() == 'IOA':
        ore_composition_complex = {'Fe': 66.31,
                                 'TiO2': 0.15,
                                 'Al2O3': 2.5,
                                 'SiO2': 2.5,
                                 'CaO': 0.0,
                                 'MgO': 0.0,
                                 'S': 0.01,
                                 'P2O5': 0.03}
    elif ore_name.upper() == 'IOB':
        ore_composition_complex = {'Fe': 65.47,
                                 'NiO': 0.04,
                                 'TiO2': 1.07,
                                 'V2O5': 0.68,
                                 'Al2O3': 0.3,
                                 'SiO2': 1.94,
                                 'MgO': 2.17,
                                 'CaO': 0.12,
                                 'S': 0.06,
                                 'P2O5': 0.02}
    elif ore_name.upper() == 'IOC':
        ore_composition_complex = {'Fe': 58.42,
                                    'Al2O3': 2.57,
                                    'SiO2': 5.97,
                                    'MgO': 0.0,
                                    'CaO': 0.0,
                                    'S': 0.03,
                                    'P2O5': 0.19,
                                    'Mn': 0.51,
                                    'LOI': 7.2}
    elif ore_name.upper() == 'IOD':
        ore_composition_complex = {'Fe': 56.71,
                                    'Al2O3': 3.28,
                                    'SiO2': 6.56,
                                    'MgO': 0.0,
                                    'CaO': 0.0,
                                    'S': 0.03,
                                    'P2O5': 0.14,
                                    'Mn': 0.72,
                                    'LOI': 8.2}
    elif ore_name.upper() == 'IOE':
        ore_composition_complex = {'Fe': 56.41,
                                    'Al2O3': 3.01,
                                    'SiO2': 6.71,
                                    'MgO': 0.0,
                                    'CaO': 0.04,
                                    'S': 0.04,
                                    'P2O5': 0.06,
                                    'Mn': 0.40,
                                    'LOI': 8.8}
    else:
        ore_composition_complex = {'Fe': 65.263,
                                    'SiO2': 3.814,
                                    'Al2O3': 2.437,
                                    'TiO2': 0.095,
                                    'Mn': 0.148,
                                    'CaO': 0.032,
                                    'MgO': 0.085,
                                    'Na2O': 0.012,
                                    'K2O': 0.011,
                                    'P': 0.109,
                                    'S': 0.024}


    ore_composition_complex['gangue'] = sum(ore_composition_complex.values()) - ore_composition_complex['Fe'] - ore_composition_complex.get('LOI', 0.0)
    ore_composition_complex['hematite'] = 100 - ore_composition_complex['gangue'] -  - ore_composition_complex.get('LOI', 0.0)
    ore_composition_complex = hematite_normalise(ore_composition_complex)

    # Neglecting the gangue elements other than SiO2, Al2O3, CaO and MgO. Adding the mass of 
    # ignored elements to the remaining impurities equally. Simplification for the mass flow
    # calculations. Values are in mass / weight percent.
    mass_of_neglected_species = sum(ore_composition_complex.values()) \
                               - ore_composition_complex['gangue'] \
                               - ore_composition_complex['hematite'] \
                                 - ore_composition_complex['Fe'] \
                                - ore_composition_complex['SiO2'] \
                                - ore_composition_complex['Al2O3'] \
                                - ore_composition_complex['CaO'] \
                                - ore_composition_complex['MgO'] \
                                - ore_composition_complex.get('LOI', 0.0)
    ore_composition_simple = {'Fe': ore_composition_complex['Fe'],
                                'SiO2': ore_composition_complex['SiO2'] + mass_of_neglected_species * 0.25,
                                'Al2O3': ore_composition_complex['Al2O3'] + mass_of_neglected_species * 0.25,
                                'CaO': ore_composition_complex['CaO'] + mass_of_neglected_species * 0.25,
                                'MgO': ore_composition_complex['MgO'] + mass_of_neglected_species * 0.25}
    if 'LOI' in ore_composition_complex:
        ore_composition_simple['LOI'] = ore_composition_complex['LOI']

    ore_composition_simple['gangue'] = sum(ore_composition_simple.values()) - ore_composition_simple['Fe'] - ore_composition_complex.get('LOI', 0.0)
    ore_composition_simple['hematite'] = 100 - ore_composition_simple['gangue'] - ore_composition_complex.get('LOI', 0.0)
    ore_composition_simple = hematite_normalise(ore_composition_simple)

    system.system_vars['ore composition'] = ore_composition_complex
    system.system_vars['ore composition simple'] = ore_composition_simple


def add_slag_and_flux_mass(system: System):
    steelmaking_device_name = system.system_vars['steelmaking device name']
    b2_basicity = system.system_vars['b2 basicity']
    b4_basicity = system.system_vars['b4 basicity']
    ore_composition_simple = system.system_vars['ore composition simple']
    final_reduction_degree = system.system_vars['final reduction percent'] * 0.01
    o2_injection_mols = system.system_vars['o2 injection kg'] / species.create_o2_species().mm
    max_feo_in_slag_perc = system.system_vars['feo soluble in slag percent']

    feo_slag = species.create_feo_species()
    sio2_gangue = species.create_sio2_species()
    al2o3_gangue = species.create_al2o3_species()
    cao_gangue = species.create_cao_species()
    mgo_gangue = species.create_mgo_species()
    cao_flux = species.create_cao_species()
    mgo_flux = species.create_mgo_species()

    steelmaking_device = system.devices[steelmaking_device_name]
    fe = steelmaking_device.outputs['steel'].species('Fe')

    # iterative solve for the ore and slag mass
    ore_mass = 1666.0 # kg, initial guess
    for _ in range(10):
        _, feo_after_reduction, _, _ = iron_species_from_reduction_degree(final_reduction_degree, ore_mass, ore_composition_simple)
        feo_slag.mass = feo_after_reduction.mass + feo_slag.mm * 2 * o2_injection_mols
        
        sio2_gangue.mass = ore_mass * ore_composition_simple['SiO2'] * 0.01
        al2o3_gangue.mass = ore_mass * ore_composition_simple['Al2O3'] * 0.01
        cao_gangue.mass = ore_mass * ore_composition_simple['CaO'] * 0.01
        mgo_gangue.mass = ore_mass * ore_composition_simple['MgO'] * 0.01

        cao_flux_mass = b2_basicity * sio2_gangue.mass - cao_gangue.mass
        cao_flux.mass = max(cao_flux_mass, 0.0)
        mgo_flux_mass = b4_basicity * (al2o3_gangue.mass + sio2_gangue.mass) - cao_gangue.mass - cao_flux.mass - mgo_gangue.mass
        mgo_flux.mass = max(mgo_flux_mass, 0.0)

        for _ in range(10):
            slag_mass = sio2_gangue.mass + al2o3_gangue.mass \
                        + cao_gangue.mass + cao_flux.mass + mgo_gangue.mass + mgo_flux.mass \
                        + feo_slag.mass

            if feo_slag.mass > max_feo_in_slag_perc * slag_mass * 0.01:
                # Need another interation to get the correct slag mass, since feo saturates
                feo_slag.mass = max_feo_in_slag_perc * slag_mass * 0.01
            else:
                break

        fe_total_mass = fe.mass + feo_slag.mass * fe.mm / feo_slag.mm
        ore_mass = fe_total_mass / (ore_composition_simple['Fe'] * 0.01)

    flux = species.Mixture('flux', [cao_flux, mgo_flux])
    flux.temp_kelvin = system.system_vars['steel exit temp K']
    steelmaking_device.inputs['flux'].set(flux)

    sio2_slag = copy.deepcopy(sio2_gangue)
    al2o3_slag = copy.deepcopy(al2o3_gangue)
    cao_slag = copy.deepcopy(cao_gangue)
    mgo_slag = copy.deepcopy(mgo_gangue)
    cao_slag.mass += cao_flux.mass
    mgo_slag.mass += mgo_flux.mass
    slag = species.Mixture('slag', [feo_slag, sio2_slag, al2o3_slag, cao_slag, mgo_slag])
    slag.temp_kelvin = system.system_vars['steel exit temp K']
    steelmaking_device.outputs['slag'].set(slag)


def add_eaf_flows_initial(system: System):
    """
    Begin adding EAF mass and energy flow to the system.
    Primarily responsible for determining the slag / flux requirements.
    """
    add_slag_and_flux_mass(system)

    steelmaking_device_name = system.system_vars['steelmaking device name']
    electrode_consumption = species.create_c_species()
    electrode_consumption.mass = 5.5 # kg / tonne steel, from sujay kumar dutta, pg 409
    electrode_consumption.temp_kelvin = celsius_to_kelvin(1750)
    system.devices[steelmaking_device_name].inputs['electrode'].set(electrode_consumption)


def add_plasma_flows_initial(system: System):
    """
    Begin adding Plasma Smelter mass and energy flow to the system.
    Primarily responsible for determining the slag / flux requirements.
    """
    add_slag_and_flux_mass(system)
    # TODO: If using a DC arc plasma, add electrode consumption here


def add_ore(system: System):
    """
    Add the ore to the mass flow. Determine based on the yeild
    of the output slag / steel and the ore composition.
    """
    ore_initial_temp = celsius_to_kelvin(25)
    ore_preheating_temp = system.system_vars['ore heater temp K']
    steelmaking_device_name = system.system_vars['steelmaking device name']
    ore_composition_simple = system.system_vars['ore composition simple']
    ore_heater_device_name = system.system_vars['ore heater device name']
    first_ironmaking_device_name = system.system_vars['ironmaking device names'][0]

    # Calculate the mass of the ore required.
    # Note that this is the input ore at the very start of the process.     
    steelmaking_device = system.devices[steelmaking_device_name]
    slag_mixture = steelmaking_device.outputs['slag']
    flux_mixtures = steelmaking_device.inputs['flux']

    cao_gangue = species.create_cao_species()
    cao_gangue.mass = slag_mixture.species('CaO').mass - flux_mixtures.species('CaO').mass
    mgo_gangue = species.create_mgo_species()
    mgo_gangue.mass = slag_mixture.species('MgO').mass - flux_mixtures.species('MgO').mass
    sio2_gangue = copy.deepcopy(slag_mixture.species('SiO2'))
    al2o3_gangue = copy.deepcopy(slag_mixture.species('Al2O3'))

    gangue_mass = sio2_gangue.mass + al2o3_gangue.mass + cao_gangue.mass + mgo_gangue.mass
    ore_mass = gangue_mass / (ore_composition_simple['gangue'] * 0.01)

    fe2o3_ore = species.create_fe2o3_species()
    fe2o3_ore.mass = ore_mass * ore_composition_simple['hematite'] * 0.01
    fe3o4 = species.create_fe3o4_species()
    feo = species.create_feo_species()
    fe = species.create_fe_species()

    water_loi = species.create_h2o_species()
    water_loi.mass = ore_mass * ore_composition_simple.get('LOI', 0.0) * 0.01

    ore = species.Mixture('ore', [fe2o3_ore, fe3o4, feo, fe,
                          cao_gangue, mgo_gangue, sio2_gangue, al2o3_gangue,
                          water_loi])
    ore.temp_kelvin = ore_initial_temp

    if ore_heater_device_name is not None:
        ore_preheating_device = system.devices[ore_heater_device_name]
        ore_preheating_device.inputs['ore'].set(ore)
        ore.temp_kelvin = ore_preheating_temp
        ore_preheating_device.outputs['ore'].set(ore)


        # Add electrical energy to heat the ore
        # Assume no thermal losses for now.
        electrical_heat_eff = 0.98
        electrical_energy = EnergyFlow('electricity', ore_preheating_device.energy_balance() / electrical_heat_eff)
        ore_preheating_device.inputs['electricity'].set(electrical_energy)
        electrical_losses = EnergyFlow('losses', electrical_energy.energy * (1 - electrical_heat_eff))
        ore_preheating_device.outputs['losses'].set(electrical_losses)
    
    iron_making_device = system.devices[first_ironmaking_device_name]
    iron_making_device.inputs['ore'].set(ore)


def iron_species_from_reduction_degree(reduction_degree: float, initial_ore_mass: float, hematite_composition: Dict[str, float]):
    """
    Returns the iron species at a given reduction degree.
    reduction_degree: The degree of reduction of the ore. 0 is no reduction, 1 is complete reduction.
    initial_ore_mass: The mass of the ore at the start of the process. Iron in the ore is assumed 
        to be completely hematite. 
    hematite_composition: The composition of the hematite ore as a percent. Must contain 'Fe' and 'hematite'.
    """
    # The DRI will contain a mix of Fe, FeO, Fe2O3, and Fe3O4
    fe2o3 = species.create_fe2o3_species()
    fe3o4 = species.create_fe3o4_species()
    feo = species.create_feo_species()
    fe = species.create_fe_species()

    n_hem_i = initial_ore_mass * hematite_composition['hematite'] * 0.01 / fe2o3.mm
    n_fe_t = (initial_ore_mass * hematite_composition['Fe'] * 0.01) / fe.mm

    # The main assumption is that hematite completely reduces to magnetite
    # before any wustite forms, and magnetite completely reduces to wustite
    # before any metallic Fe forms.
    if (1/3) <= reduction_degree <= 1:
        # Mix of wustite and metallic Fe
        feo.mols = 3 * n_hem_i * (1 - reduction_degree)
        fe.mols = n_fe_t - feo.mols
    elif (1/9) <= reduction_degree < (1/3):
        # Mix of magnetite and wustite
        fe3o4.mols = 3 * n_hem_i * (1 - reduction_degree) - n_fe_t
        feo.mols = 3 * n_hem_i * (1 - reduction_degree) - 4 * fe3o4.mols
    elif 0 <= reduction_degree < (1/9):
        # Mix of hematite and magnetite
        fe2o3.mols = 9 * n_hem_i * (1 - reduction_degree) - 4*n_fe_t
        fe3o4.mols = (3*n_hem_i * (1 - reduction_degree) - 3 * fe2o3.mols) / 4
    
    return fe, feo, fe3o4, fe2o3


def add_fluidized_bed_flows(system: System):
    # TODO: FIXING THIS TO PROPERLY USTILISE ALL THE IRONMAKING DEVICES
    # IS THE MAIN PRIORITY AFTER THE FIRST ITERATION OF THE MODEL IS COMPLETE
    ironmaking_device_names = system.system_vars['ironmaking device names']
    excess_h2_ratio = system.system_vars['fluidized beds h2 excess ratio']
    reduction_degree = system.system_vars['fluidized beds reduction percent'] * 0.01

    assert len(ironmaking_device_names) > 0, 'Must have at least one iron making device'
    assert excess_h2_ratio >= 1.0

    in_gas_temp = celsius_to_kelvin(900)
    reaction_temp = celsius_to_kelvin(700)

    ironmaking_device = system.devices[ironmaking_device_names[0]]
    ore = ironmaking_device.inputs['ore']

    hematite_composition = system.system_vars['ore composition simple']
    fe_dri, feo_dri, fe3o4_dri, fe2o3_dri = iron_species_from_reduction_degree(reduction_degree, ore.mass, hematite_composition)

    dri = species.Mixture('dri fines', [fe_dri, feo_dri, fe3o4_dri, fe2o3_dri,
                                copy.deepcopy(ore.species('CaO')),
                                copy.deepcopy(ore.species('MgO')),
                                copy.deepcopy(ore.species('SiO2')),
                                copy.deepcopy(ore.species('Al2O3'))])
    dri.temp_kelvin = in_gas_temp - 50 # Assumption
    ironmaking_device.outputs['dri'].set(dri)

    # TODO: Reduce repeition with the same logic in the plasma smelter. 
    delta_fe = fe_dri.mols - ore.species('Fe').mols
    delta_feo = feo_dri.mols - ore.species('FeO').mols
    delta_fe3o4 = fe3o4_dri.mols - ore.species('Fe3O4').mols

    num_fe_formations = delta_fe
    num_feo_formations = (num_fe_formations + delta_feo) / 3
    num_fe3o4_formations = (num_feo_formations + delta_fe3o4) / 2

    chemical_energy = EnergyFlow('chemical energy', - num_fe_formations * species.delta_h_feo_h2_fe_h2o(reaction_temp) \
                                              - num_feo_formations * species.delta_h_fe3o4_h2_3feo_h2o(reaction_temp) \
                                              - num_fe3o4_formations * species.delta_h_3fe2o3_h2_2fe3o4_h2o(reaction_temp))
    ironmaking_device.inputs['chemical'].set(chemical_energy)

    h2_consumed = species.create_h2_species()
    h2_consumed.mols = 1.5 * fe_dri.mols + 0.5 * feo_dri.mols + 0.5 * fe3o4_dri.mols

    h2o = species.create_h2o_species()
    h2o.mols = h2_consumed.mols

    try: 
        h2o.mols += ore.species('H2O').mols # the LOI (loss on ignition) species in the ore
    except:
        pass # no LOI species in the ore

    h2_excess = copy.deepcopy(h2_consumed)
    h2_excess.mols = (excess_h2_ratio - 1) * h2_consumed.mols

    h2_total = species.create_h2_species()
    h2_total.mols = h2_consumed.mols + h2_excess.mols

    hydrogen = species.Mixture('H2', [h2_total])
    hydrogen.temp_kelvin = in_gas_temp 
    ironmaking_device.first_input_containing_name('h2 rich gas').set(hydrogen)
    # Set initial guess for the out gas temp
    # Then iteratively solve fo the temp that balances the energy balance

    out_gas_temp = in_gas_temp

    off_gas = species.Mixture('H2 H2O', [h2o, h2_excess])
    off_gas.temp_kelvin = out_gas_temp
    ironmaking_device.first_output_containing_name('h2 rich gas').set(off_gas)
    
    # Convection and conduction losses are 4% of input heat. 
    # TODO! Find a better justification for this 4%. Currently reusing the EAF loss recommended 
    # by Sujay Kumar Dutta pg 425
    thermal_losses_frac = 0.04
    thermal_losses = -thermal_losses_frac * ironmaking_device.thermal_energy_balance()

    max_iter = 100
    i = 0
    while True:
        if abs(ironmaking_device.energy_balance() + thermal_losses) < 1e-6:
            break
        if i > max_iter:
            raise Exception("Failed to converge on the out gas temp. Reached max interation")

        energy_balance = ironmaking_device.energy_balance() + thermal_losses
        specific_enthalpy = ironmaking_device.first_output_containing_name('h2 rich gas').cp()
        ironmaking_device.first_output_containing_name('h2 rich gas').temp_kelvin -= energy_balance / specific_enthalpy
        thermal_losses = -thermal_losses_frac * ironmaking_device.thermal_energy_balance()

        i += 1

    # add the calculated thermal losses
    ironmaking_device.outputs['losses'].set(EnergyFlow('thermal losses', thermal_losses))

    for device_name in ironmaking_device_names[1:]:
        # Currently just a dummy reactors, since the calculation 
        # above assunmes all the reduction happens in the first reactor.
        # Eventually we want to split this up between the different reactors
        # TODO! Account for these properly, likely has a difference on the
        # heat balance. 
        second_iron_making_device = system.devices[device_name]
        second_iron_making_device.inputs['dri'].set(dri)
        second_iron_making_device.outputs['dri'].set(dri)
        second_iron_making_device.first_input_containing_name('h2 rich gas').set(hydrogen)
        
        second_iron_making_device.first_output_containing_name('h2 rich gas').set(hydrogen)
        second_iron_making_device.outputs['losses'].energy = 0.0
        second_iron_making_device.inputs['chemical'].energy = 0.0


def add_briquetting_flows(system: System):
    """
    Basically a dummy stage. Since for the moment we don't assune any
    heating takes place. 
    """
    if 'briquetting' not in system.devices:
        return
    final_ironmaking_device_name = system.system_vars['ironmaking device names'][-1]
    hbi = copy.deepcopy(system.devices[final_ironmaking_device_name].outputs['dri'])
    hbi.name = 'hbi'
    system.devices['briquetting'].outputs['hbi'].set(hbi)


def steelsurface_radiation_losses(A, Ts, Tr, capacity_tonnes=180, tap_to_tap_secs=3600):
    """
    Returns the radiation losses per tonne of liquid steel.
    A = Surface area of the steel surface [m2]
    Ts = Temperature of the steel surface [K]
    Tr = Temperature of the surrounding refractory [K] (Sujay et al. recommend 25C, but this seems too low?) 
    source: From Sujay Kumar Dutta, pg 425
    """
    emissivity = 0.28 # emissivity of liquid steel
    boltzmann_constant = 5.67e-8 # W / m^2 K^4
    q_watts = emissivity * boltzmann_constant * A * (Ts**4 - Tr**4)

    return q_watts * tap_to_tap_secs / capacity_tonnes


def hydrogen_plasma_radiation_losses(total_input_energy_less_radiation_losses):
    # Radiation from the plasma contributes to losses. 
    # Different mechanisms will dominate, depending on the state of the plasma (density, 
    # temperature, geometry, external magnetic fields, etc.)
    # Blackbody radiation, bremsstrahlung, cyclotron radiation, etc.
    # for now, use an empirical value for the energy loss due to radiation, as measured by dudnik2020
    # Y. D. Dudnik, V. Kovshechnikov, A. Safronov, V. Kuznetsov, V. Shiryaev, and O. Vasilieva, 
    # “Radiation energy losses in a single chamber three phase plasma torch with rod electrodes,” 
    #  in Journal of Physics: Conference Series, IOP Publishing, 2020, p. 012086.

    # Energy loss from radiation to plasma walls is ~10% of input power at atmospheric pressure
    energy_loss_frac_total_energy = 0.1
    return energy_loss_frac_total_energy * total_input_energy_less_radiation_losses / (1 - energy_loss_frac_total_energy)


def add_eaf_flows_final(system: System):
    # TODO: May be underestimating he energy requirement for the EAF. 
    # According to Sujay Kumar Dutta, it should be around 825 kWh / tonne steel. 
    # and Vogl2018 recommends 667 kWh / tonne steel. 704 kWh / tonne recommended by hornby2021. 
    # We are only getting 455 kWh / tonne steel. Seems to be due to us keeping the hbi hot
    steelmaking_device_name = system.system_vars['steelmaking device name']
    steelmaking_device = system.devices[steelmaking_device_name]
    reaction_temp = system.system_vars['eaf reaction temp K']

    if steelmaking_device.inputs['hbi'].species('Fe3O4').mols > 0 or \
        steelmaking_device.inputs['hbi'].species('Fe2O3').mols > 0:
        # could potentially just add the unreduced hematite and magnetite to the slag?
        raise Exception("add_eaf_mass_flow_final: HBI contains Fe3O4 or Fe2O3, which EAF cannot reduce.")

    # Add the carbon required for the alloy
    c_alloy = copy.deepcopy(steelmaking_device.outputs['steel'].species('C'))

    # Add carbon / oxygen needed for reduction / oxidation of FeO / Fe
    feo_slag = steelmaking_device.outputs['slag'].species('FeO')
    feo_dri = steelmaking_device.inputs['hbi'].species('FeO')

    o2_oxidation = species.create_o2_species()
    c_reduction = species.create_c_species()

    steelmaking_device.inputs['chemical'].energy = 0.0
    if feo_slag.mols > feo_dri.mols:
        # metallic fe is oxidised by injected O2
        o2_oxidation.mols = 0.5 * (feo_slag.mols - feo_dri.mols)
        num_feo_formation_reactions = o2_oxidation.mols
        steelmaking_device.inputs['chemical'].energy += -num_feo_formation_reactions * species.delta_h_2fe_o2_2feo(reaction_temp)

    else:
        # feo is reduced by the injected carbon.
        # we assume all reduction is by pure carbon, non is by CO gas. 
        c_reduction.mols = (feo_dri.mols - feo_slag.mols)
        num_feo_c_reduction_reactions = c_reduction.mols
        steelmaking_device.inputs['chemical'].energy +=  -num_feo_c_reduction_reactions * species.delta_h_feo_c_fe_co(reaction_temp)

    # Add the target amount of O2 and calculate the required
    # Carbon for combustion. The target O2 consumption
    # is based on literature data, from kirschen2021 and sujay kumar dutta, pg 434
    # we know this is what is roughly used. 
    # We also assume all the injected o2 is used in combustion / oxidation. No O2 
    # gas escapes. 
    total_o2_injected_mass = system.system_vars['o2 injection kg']
    assert total_o2_injected_mass >= o2_oxidation.mass

    # Assume a mix of CO and CO2 is produced. We know from hornby2021, that
    # approx 10% of energy comes from CO formation and 24% of energy comes from
    # CO2 formation, so use this as a guide. Main simplification is that we
    # don't include the CO formed from the reduction of FeO by C.
    o2_combustion = species.create_o2_species()
    o2_combustion.mass = total_o2_injected_mass - o2_oxidation.mass # some o2 may already be used in fe oxidation
    n_reactions = o2_combustion.mols
    num_co_reactions = n_reactions / 2.348
    num_co2_reactions = n_reactions - num_co_reactions

    steelmaking_device.inputs['chemical'].energy += -num_co_reactions * species.delta_h_2c_o2_2co(reaction_temp) \
                                                    -num_co2_reactions * species.delta_h_c_o2_co2(reaction_temp)

    c_combustion = species.create_c_species()
    c_combustion.mols = 2*num_co_reactions + num_co2_reactions

    c_injected = species.create_c_species()
    c_injected.mols = c_combustion.mols + c_reduction.mols + c_alloy.mols - steelmaking_device.inputs['electrode'].mols
    c_injected.temp_kelvin = celsius_to_kelvin(25) # assume room temp
    steelmaking_device.inputs['carbon'].set(c_injected)

    o2_injected = species.create_o2_species()
    o2_injected.mols = o2_combustion.mols + o2_oxidation.mols
    o2_injected.temp_kelvin = celsius_to_kelvin(25) # assume room temp
    steelmaking_device.inputs['o2'].set(o2_injected)

    co = species.create_co_species()
    co.mols = 2 * num_co_reactions + c_reduction.mols
    co2 = species.create_co2_species()
    co2.mols = num_co2_reactions
    off_gas = species.Mixture('carbon gas', [co, co2])
    off_gas.temp_kelvin = reaction_temp
    steelmaking_device.outputs['carbon gas'].set(off_gas)

    # losses due to infiltrated air
    infiltrated_air_mass = 200.0 # from pfeifer 2022 (TODO read the original paper)
    infiltrated_air = species.create_air_mixture(infiltrated_air_mass)
    infiltrated_air.name = 'infiltrated air'
    infiltrated_air.temp_kelvin = celsius_to_kelvin(25)
    steelmaking_device.inputs['infiltrated air'].set(infiltrated_air)

    infiltrated_air.temp_kelvin = reaction_temp - 200.0 # guess
    steelmaking_device.outputs['infiltrated air'].set(infiltrated_air)

    # TODO: reduce repetition with the plasma steelmaking
    electric_arc_eff = 0.8 # Makarov2022
    electrical_energy = steelmaking_device.energy_balance() / electric_arc_eff
    steelmaking_device.inputs['electricity'].energy = electrical_energy
    steelmaking_device.outputs['losses'].energy = electrical_energy * (1 - electric_arc_eff)

    # Add the radiation and conduction losses 
    # Conduction losses are 4% of input heat. From sujay kumar dutta pg 425 
    conduction_losses = 0.04 * steelmaking_device.thermal_energy_balance()
    eaf_surface_radius = 3.8
    capacity_tonnes = 180
    tap_to_tap_secs = 60*60
    radiation_losses = steelsurface_radiation_losses(np.pi*(eaf_surface_radius)**2, reaction_temp, celsius_to_kelvin(25),
                                                     capacity_tonnes, tap_to_tap_secs)
    steelmaking_device.outputs['losses'].energy += radiation_losses + conduction_losses

    # Increase the electrical energy to balance the thermal losses 
    steelmaking_device.inputs['electricity'].energy += radiation_losses + conduction_losses

    # print(f"Total energy = {steelmaking_device.inputs['electricity'].energy*2.77778e-7:.2e} kWh")


def add_plasma_flows_final(system: System):
    """
    For the single stage plasma smelter, these functions could be merged, but easier to separate 
    and reuse between Hybrid and Plasma.
    """
    # reduction_degree: The degree of reduction achieved by the hydrogen plasma. Based on the mass of oxygen 
    # remaining in iron oxide, compared to the mass of oxygen in the iron oxide at the very start of the process.
    reduction_degree = system.system_vars['plasma reduction percent'] * 0.01
    reaction_temp = system.system_vars['plasma reaction temp K']
    excess_h2_ratio = system.system_vars['plasma h2 excess ratio']
    steelmaking_device_name = system.system_vars['steelmaking device name']
    steelmaking_device = system.devices[steelmaking_device_name]
    first_ironmaking_device_name = system.system_vars['ironmaking device names'][0]
    ore_composition_simple = system.system_vars['ore composition simple']
    steel_bath_temp = system.system_vars['steel exit temp K']


    # the plasma smelter can use hbi or ore fines.
    ironbearing_material = steelmaking_device.inputs.get('hbi')
    if ironbearing_material is None:
        ironbearing_material = steelmaking_device.inputs.get('ore')

    if ironbearing_material is None:
        raise ValueError('No iron bearing material found in the input mass of the plasma smelter')

    iron_making_device = system.devices[first_ironmaking_device_name]
    ore_mass = iron_making_device.inputs['ore'].mass
    fe_target, feo_target, fe3o4_target, fe2o3_target = iron_species_from_reduction_degree(reduction_degree, ore_mass, ore_composition_simple)

    if not math.isclose(fe3o4_target.mols, 0, abs_tol=1e-12) or not math.isclose(fe2o3_target.mols, 0, abs_tol=1e-12):
        raise Exception("Error: Expect plasma hydrogen reduction to completly reduce magnetite and hematite")

    # TODO! Reduce repetition with the same logic dri function
    delta_fe = fe_target.mols - ironbearing_material.species('Fe').mols
    delta_feo = feo_target.mols - ironbearing_material.species('FeO').mols
    delta_fe3o4 = fe3o4_target.mols - ironbearing_material.species('Fe3O4').mols

    # assert delta_fe >= 0 and delta_feo >= 0 and delta_fe3o4 >= 0, "Error: Plasma reduction degree should be higher than prereduction during ironmaking"

    # The net reactions involved in the Hydrogen Plasma reduction stage of this device
    # TODO: Double check this. the div 3 and div 2 confuse me
    num_fe_formations = delta_fe
    num_feo_formations = (num_fe_formations + delta_feo) / 3
    num_fe3o4_formations = (num_feo_formations + delta_fe3o4) / 2

    print("add_plasma_flows_final: Need to calculate the reaction enthalpy from monotomic H reduction. The fraction of H reduction will depend on temp")
    steelmaking_device.inputs['chemical'].energy = -num_fe_formations * species.delta_h_feo_h2_fe_h2o(reaction_temp) \
                                              -num_feo_formations * species.delta_h_fe3o4_h2_3feo_h2o(reaction_temp) \
                                              -num_fe3o4_formations * species.delta_h_3fe2o3_h2_2fe3o4_h2o(reaction_temp)

    # determine the mass of h2o in the off gas
    h2o = species.create_h2o_species()
    h2o.mols = num_fe_formations + num_feo_formations + num_fe3o4_formations
    h2o.temp_kelvin = reaction_temp - 200 # guess

    # the amount of h2 in the in gas
    h2_consumed = species.create_h2_species()
    h2_consumed.mols = h2o.mols
    h2_consumed.temp_kelvin = celsius_to_kelvin(25)

    assert excess_h2_ratio >= 1
    h2_excess = copy.deepcopy(h2_consumed)
    h2_excess.mols = h2_consumed.mols * (excess_h2_ratio - 1)

    h2_total = species.create_h2_species()
    h2_total.mols = h2_consumed.mols + h2_excess.mols
    h2_total.temp_kelvin = celsius_to_kelvin(25)
    steelmaking_device.first_input_containing_name('h2 rich gas').set(h2_total)

    # Add the carbon required for the alloy
    c_alloy = copy.deepcopy(steelmaking_device.outputs['steel'].species('C'))

    # Add carbon / oxygen needed for reduction / oxidation of FeO / Fe
    feo_slag = steelmaking_device.outputs['slag'].species('FeO')

    o2_oxidation = species.create_o2_species()
    c_reduction = species.create_c_species()

    if math.isclose(feo_slag.mols - feo_target.mols, 0.0, abs_tol=1e-9):
        # no oxidation or reduction of feo required
        pass
    elif feo_slag.mols > feo_target.mols:
        # metallic fe is oxidised by injected O2
        o2_oxidation.mols = 0.5 * (feo_slag.mols - feo_target.mols)
        num_feo_formation_reactions = o2_oxidation.mols
        steelmaking_device.inputs['chemical'].energy += -num_feo_formation_reactions * species.delta_h_2fe_o2_2feo(reaction_temp)
    else:
        # feo is reduced by the injected carbon
        c_reduction.mols = (feo_target.mols - feo_slag.mols)
        num_feo_c_reduction_reactions = c_reduction.mols
        steelmaking_device.inputs['chemical'].energy += -num_feo_c_reduction_reactions * species.delta_h_feo_c_fe_co(reaction_temp)

    total_o2_injected_mass = system.system_vars['o2 injection kg']
    assert total_o2_injected_mass >= o2_oxidation.mass

    # We assume oxygen always oxidises Fe to max FeO solubility in the slag before
    # it begins combusting with the carbon. 

    # Assume a mix of CO and CO2 is produced. We know from hornby2021, that
    # approx 10% of energy comes from CO formation and 24% of energy comes from
    # CO2 formation, so use this as a guide. Main simplification is that we
    # don't include the CO formed from the reduction of FeO by C.
    o2_combustion = species.create_o2_species()
    o2_combustion.mass = total_o2_injected_mass - o2_oxidation.mass # some o2 may already be used in fe oxidation
    n_reactions = o2_combustion.mols
    num_co_reactions = n_reactions / 2.348
    num_co2_reactions = n_reactions - num_co_reactions

    # This reaction may occur at a lower temp, since it is not at the plasma steel interface?
    steelmaking_device.inputs['chemical'].energy += -num_co_reactions * species.delta_h_2c_o2_2co(reaction_temp) \
                                              -num_co2_reactions * species.delta_h_c_o2_co2(reaction_temp)

    c_combustion = species.create_c_species()
    c_combustion.mols = 2*num_co_reactions + num_co2_reactions

    c_injected = species.create_c_species()
    c_injected.mols = c_combustion.mols + c_reduction.mols + c_alloy.mols
    c_injected.temp_kelvin = celsius_to_kelvin(25) # assume room temp
    steelmaking_device.inputs['carbon'].set(c_injected)

    o2_injected = species.create_o2_species()
    o2_injected.mols = o2_combustion.mols + o2_oxidation.mols
    o2_injected.temp_kelvin = celsius_to_kelvin(25) # assume room temp
    steelmaking_device.inputs['o2'].set(o2_injected)

    try: # does this do something weird to the heat balance??
        h2o.mols += ironbearing_material.species('H2O').mols # the LOI (loss on ignition) species in the ore
    except:
        pass # no LOI species in the ore / dri

    co = species.create_co_species()
    co.mols = 2 * num_co_reactions + c_reduction.mols
    co2 = species.create_co2_species()
    co2.mols = num_co2_reactions
    off_gas = species.Mixture('off gas', [co, co2, h2o, h2_excess])
    off_gas.temp_kelvin = reaction_temp
    steelmaking_device.first_output_containing_name('h2 rich gas').set(off_gas)

    # IGNORE LOSSES FROM INFILTRATED AIR, BECAUSE WE NEED TO HEAT RECOVER THE OFF GAS
    # OPTIMISTICALLY ASSUME THE PLASMA SMELTER IS PRETTY MUCH AIR TIGHT / CONTROLLED ATMOSPHERE. 

    # TODO: Reduce repetition with the EAF?
    # Need to add the required electrical energy to balance the 
    # required thermal energy, accounting for the energy already. provided
    # by the chemical reactions (oxidation, reduction, combustion etc.)
    # Assume high efficiency RF ICP plasma gun.
    plasma_torch_eff = system.system_vars['plasma torch eff pecent'] * 0.01
    electrical_energy = steelmaking_device.energy_balance() / plasma_torch_eff
    steelmaking_device.inputs['electricity'].energy = electrical_energy
    steelmaking_device.outputs['losses'].energy = electrical_energy * (1 - plasma_torch_eff)

    # Add the thermal losses 
    # Assume same as an EAF. Convection and conduction losses are 4% of input heat. 
    # From sujay kumar dutta pg 425 
    # assume the plasma smelter is smaller than the EAF due to superior kinetics
    conduction_losses = 0.04 * steelmaking_device.thermal_energy_balance()
    plasma_surface_radius = 3.8 * 0.5 
    capacity_tonnes = 180*0.5 
    tap_to_tap_secs = 60*60*0.5
    radiation_losses = steelsurface_radiation_losses(np.pi*(plasma_surface_radius)**2, 
                                                     steel_bath_temp, celsius_to_kelvin(25),
                                                     capacity_tonnes, tap_to_tap_secs)
    radiation_losses += hydrogen_plasma_radiation_losses(steelmaking_device.inputs['electricity'].energy + conduction_losses)
    steelmaking_device.outputs['losses'].energy += radiation_losses + conduction_losses

    # Increase the electrical energy to balance the thermal losses 
    steelmaking_device.inputs['electricity'].energy += radiation_losses + conduction_losses
    # print(f"Total energy = {steelmaking_device.inputs['electricity'].energy*2.77778e-7:.2e} kWh")


def add_electrolysis_flows(system: System):
    water_input_temp = celsius_to_kelvin(25)
    gas_output_temp = celsius_to_kelvin(70)
    hydrogen_consuming_device_names = system.system_vars['h2 consuming device names']

    electrolyser = system.devices['water electrolysis']

    h2 = species.create_h2_species()
    h2.temp_kelvin = gas_output_temp
    for device_name in hydrogen_consuming_device_names:
        device = system.devices[device_name]
        if isinstance(device.first_input_containing_name('h2 rich gas'), species.Species):
            input_h2_mols = device.first_input_containing_name('h2 rich gas').mols
        elif isinstance(device.first_input_containing_name('h2 rich gas'), species.Mixture):
            input_h2_mols = device.first_input_containing_name('h2 rich gas').species('H2').mols
        else:
            raise TypeError("Error: Unknown type for h2 rich gas input")
        
        if isinstance(device.first_output_containing_name('h2 rich gas'), species.Species):
            output_h2_mols = device.first_output_containing_name('h2 rich gas').mols
        elif isinstance(device.first_output_containing_name('h2 rich gas'), species.Mixture):
            output_h2_mols = device.first_output_containing_name('h2 rich gas').species('H2').mols
        else:
            raise TypeError("Error: Unknown type for h2 rich gas input")
        
        h2_consumed = input_h2_mols - output_h2_mols
        assert h2_consumed >= 0
        h2.mols += h2_consumed
    electrolyser.outputs['h2 rich gas'].set(h2)
    assert 50.0 < h2.mass < 60.0 # we know roughly how much H2 to expect from stoichiometry
    
    o2 = species.create_o2_species()
    o2.mols = h2.mols * 0.5
    o2.temp_kelvin = gas_output_temp
    electrolyser.outputs['o2'].set(o2)

    h2o = species.create_h2o_species()
    h2o.mols = h2.mols
    h2o.temp_kelvin = water_input_temp
    electrolyser.inputs['h2o'].set(h2o)

    # determine the electrical energy required.
    lhv_efficiency = system.system_vars['electrolysis lhv efficiency percent'] * 0.01
    h2_lhv = 120e6 # J/kg
    electrical_energy = h2.mass * h2_lhv / lhv_efficiency
    electrolyser.inputs['electricity'].energy = electrical_energy
    electrolyser.outputs['losses'].energy = electrical_energy * (1-lhv_efficiency)

    # Should really calculate the chemical energy out from the delta_h function
    # as an extra step of verification, but delta_h_2h2o_2h2_o2() gives the hhv
    # for some reason.
    electrolyser.outputs['chemical'].energy = h2.mass * h2_lhv

    # Note that the energy above is just the energy to perform electrolysis at
    # 25 deg. There is also the energy required to heat the species to the
    # specified output temp. For simplicity, we assume no losses here.
    electrolyser.inputs['electricity'].energy += (electrolyser.thermal_energy_balance())


def add_h2_storage_flows(system: System):
    """
    Adds the mass flows so that the correct masses are ready for condenser and scrubber intial
    """

    # Assume no H2 leakage.
    # Neglect the temperature difference from the output of the electrolyser (~70C)
    # to the output of the storage device (~25C). 
    system.devices['h2 storage'].outputs['h2 rich gas'].set(system.devices['h2 storage'].inputs['h2 rich gas'])

    # Not all of the hydrogen flowing into the H2 storage device goes into storage.
    # Some passes straight to the next device. Only the excess is stored.
    # This is to make the flows / wiring of the system as a whole a little simpler.
    # Calculate the fraction of hydrogen that ends up in storage.
    stored_h2_frac = system.system_vars['h2 storage hours of operation'] / 24.0
    stored_h2_mass = stored_h2_frac * system.devices['h2 storage'].inputs['h2 rich gas'].mass
    h2_hhv = 142.0e6 # J/kg

    if system.system_vars['h2 storage method'].lower() == 'salt caverns':
        # Pressure around ~100 bar (but could be in range of 50-160). 
        # Assume mixed isothermal, adiabatic compression. Figure 6 in elberry2021
        # Compress requires 6% of HHV energy
        compressor_energy = 0.06 * stored_h2_mass * h2_hhv
    elif system.system_vars['h2 storage method'].lower() == 'compressed gas vessels':
        # Pressure is ~160 bar. Assume mixed isothermal, adiabatic compression. Figure 6 in elberry2021
        # Compress requires 7% of HHV energy
        compressor_energy = 0.07 * stored_h2_mass * h2_hhv
    else:
        raise ValueError("Error: Unknown h2 storage device")
    
    system.devices['h2 storage'].inputs['electricity'].energy = compressor_energy
    system.devices['h2 storage'].outputs['losses'].energy = compressor_energy


def merge_join_flows(system: System, join_device_name: str):
    """
    Call once the input flows have been calculated. SO ANNOYING! THIS NEW CODE SHOULD BE BETTER!!
    CALLBAK SYSTEM? ANYTIME AN INPUT CHANGES, RECAlC THE OUTPUTS?? PROBABLY. COULD DO THIS FOR EVERY
    DEVICE, THEN THE CALL ORDER DOESN'T NEED TO BE SO STRICT, CAN DO A CONVERGENCE THING.
    MIGHT BE A LITTLE COMPLICATED.
    THIS FUNCTION IS GROSS!!! 
    Also only really handles merges, not divigers.
    """
    device = system.devices[join_device_name]
    assert len(device.outputs) == 1
    output_flow_name = list(device.outputs.keys())[0]

    if isinstance(device.outputs[output_flow_name], species.Species):

        # pretty disgusting here. 
        tmp_mixture = species.Mixture("temp", [])
        device.outputs[output_flow_name].mols = 0
        for flow in device.inputs.values():
            assert isinstance(flow, species.Species)
            tmp_mixture.merge(flow)
        assert tmp_mixture.num_species() == 1
        device.outputs[output_flow_name].set(tmp_mixture._species[0])
            
    elif isinstance(device.outputs[output_flow_name], species.Mixture):
        device.outputs[output_flow_name]._species = [] # clear the ouput
        for flow in device.inputs.values():
            device.outputs[output_flow_name].merge(flow)
    else:
        raise Exception(f"unsupported type {type(device.outputs[0])}")


def balance_join2_flows(system: System):
    """
    Function specific to the join 2 device in the hybrid system. Not ideal
    """
    device = system.devices['join 2']

    input_mass = device.inputs['h2 rich gas'].mass
    plasma_mass = device.outputs['plasma h2 rich gas'].mass
    h2_fluidized_beds = species.create_h2_species()
    h2_fluidized_beds.mass = input_mass - plasma_mass
    device.outputs['h2 rich gas'].set(h2_fluidized_beds)

    device.outputs['plasma h2 rich gas'].temp_kelvin = device.inputs['h2 rich gas'].temp_kelvin
    device.outputs['h2 rich gas'].temp_kelvin = device.inputs['h2 rich gas'].temp_kelvin

def add_heat_exchanger_flows_initial(system: System):
    """
    Adds the mass flows so that the correct masses are ready for condenser and scrubber intial
    """
    heat_exchanger_device_name = 'h2 heat exchanger'
    system.devices[heat_exchanger_device_name].outputs['recycled h2 rich gas'].set(system.devices[heat_exchanger_device_name].inputs['recycled h2 rich gas'])
    system.devices[heat_exchanger_device_name].inputs['h2 rich gas'].set(system.devices[heat_exchanger_device_name].inputs['h2 rich gas'])


def add_condenser_and_scrubber_flows_initial(system: System):
    """
    Add the mass flows so that the correct masses are ready for the heat exchanger energy balance
    """
    condenser_device_name = 'condenser and scrubber'
    system.devices[condenser_device_name].outputs['recycled h2 rich gas'].set(system.devices[condenser_device_name].inputs['recycled h2 rich gas'].species('H2'))


def add_heat_exchanger_flows_final(system: System):
    """
    TODO: Should be able to simplify this function alot.
          start by using the .cp() built in method. 

    May need to use two heat exchangers. It is unclear if the top gas from
    the plasma reactor in the hybrid system can be used as a reducing gas
    for the fluidized bed section. 
    Seems a little unlikely, if the gas is too hot, will sinter and ruin the fluidized beds.
    May need two heat exchangers, or if the off gas is too hot, heat some input scrap.
    The same goes for the top has of the EAF in the fluidized bed, but this
    is not assumed to be the case. (so a bit of asymmetry here)
    """
    heat_exchanger_device_name = 'h2 heat exchanger'
    heat_exchanger = system.devices[heat_exchanger_device_name]

    # The maximum possible efficiency. Actual efficiency can be lower,
    # if required cold gas exit temp is higher than the inlet hot gas temp.
    heat_exchanger_eff = 0.9

    # temp from electrolysis and condenser
    initial_cold_gas_temp = celsius_to_kelvin(70)
    heat_exchanger.inputs['h2 rich gas'].temp_kelvin = initial_cold_gas_temp

    # We should be able to simplify this??
    # Since the system has shared objects now, we can just get the gas flows from the heat exchanger
    hot_gas_in = copy.deepcopy(heat_exchanger.inputs['recycled h2 rich gas'])
    cold_gas_in = copy.deepcopy(heat_exchanger.inputs['h2 rich gas'])
    initial_hot_gas_temp = hot_gas_in.temp_kelvin

    # temp before the condenser. MIGHT BE ABLE TO GO LOWER, BUT NEED TO CHANGE THE 
    # PHASE CHANGE TEMPERATURE OF THE WATER
    final_hot_gas_temp = celsius_to_kelvin(101.0)
    if final_hot_gas_temp > initial_hot_gas_temp:
        raise ValueError("Heat exchanger hot gas exit temp is higher than the inlet temp")
    heat_exchanged = -hot_gas_in.heat_energy(final_hot_gas_temp) * heat_exchanger_eff
    hot_gas_in.temp_kelvin = final_hot_gas_temp
    heat_exchanger.outputs['recycled h2 rich gas'].set(hot_gas_in)

    # Get the initial estimate of the exit temp of the cold gas. This initial estimate assumes
    # that the heat capacity is constant over the temp range, which is in general not the case,
    # so we need to do some iterative calculations. replace this with cp()
    mols_times_molar_heat_capacity = cold_gas_in.heat_energy(cold_gas_in.temp_kelvin + 1)
    final_cold_gas_temp = cold_gas_in.temp_kelvin + heat_exchanged / (mols_times_molar_heat_capacity)
    cold_gas_in.temp_kelvin = final_cold_gas_temp 

    # adjust the final cold gas temp iterativly to reduce error caused by assuming the
    # molar heat capcity is constant.
    # TODO reduce repetition with the Mixture::merge function.
    i = 0
    max_iter = 100
    while True:
        mols_times_molar_heat_capacity = cold_gas_in.heat_energy(cold_gas_in.temp_kelvin + 1)

        energy_gained_by_cold_gas = -cold_gas_in.heat_energy(initial_cold_gas_temp)
        energy_lost_by_hot_gas = heat_exchanged
        assert energy_gained_by_cold_gas >= 0 and energy_lost_by_hot_gas >= 0
        
        if abs((energy_gained_by_cold_gas - energy_lost_by_hot_gas) / energy_gained_by_cold_gas) < 1e-12:
            break

        dH = energy_lost_by_hot_gas - energy_gained_by_cold_gas
        dT = dH / mols_times_molar_heat_capacity
        cold_gas_in.temp_kelvin += dT
        i += 1
        if i > max_iter:
            raise Exception(f'Heat exchanger cold gas exit temp calc did not converge after {max_iter} iterations')

    # assert cold_gas_in.num_species() == 1, "Just a hack, since the line below assumes all the gas is H2." + \
    #                                        "Need to improve interoperability between Species and Mixture"
    heat_exchanger.outputs['h2 rich gas'].set(cold_gas_in)

    # Cold gas cannot exceed the temp of the hot gas
    if cold_gas_in.temp_kelvin  > initial_hot_gas_temp:
        cold_gas_in.temp_kelvin = initial_hot_gas_temp

    
    energy_gained_by_cold_gas = -cold_gas_in.heat_energy(initial_cold_gas_temp)
    energy_lost_by_hot_gas = hot_gas_in.heat_energy(initial_hot_gas_temp)
    # print(f"System = {system.name}")
    # print(f"  Target Efficiency = {heat_exchanger_eff * 100}")
    # print(f"  Actual Efficiency = {100 + (energy_gained_by_cold_gas - energy_lost_by_hot_gas)/energy_lost_by_hot_gas * 100}")
    
    hot_gas_in = heat_exchanger.inputs['recycled h2 rich gas']
    cold_gas_in = heat_exchanger.inputs['h2 rich gas']

    thermal_losses = EnergyFlow('losses', -heat_exchanger.thermal_energy_balance())
    heat_exchanger.outputs['losses'].set(thermal_losses)


def add_condenser_and_scrubber_flows_final(system: System):
    condenser_device_name: str = 'condenser and scrubber'
    condenser = system.devices[condenser_device_name]

    system.devices[condenser_device_name].outputs['recycled h2 rich gas'].set(system.devices[condenser_device_name].inputs['recycled h2 rich gas'].species('H2'))


    condenser_in_gas = system.devices[condenser_device_name].inputs['recycled h2 rich gas']
    condenser_temp = celsius_to_kelvin(70)

    system.devices[condenser_device_name].outputs['recycled h2 rich gas'].temp_kelvin = condenser_temp
    h2o_out = copy.deepcopy(condenser_in_gas.species('H2O'))
    h2o_out.temp_kelvin = condenser_temp
    condenser.outputs['h2o'].set(h2o_out)

    try:
        co_out = copy.deepcopy(condenser_in_gas.species('CO'))
        co2_out = copy.deepcopy(condenser_in_gas.species('CO2'))
        carbon_mixture = species.Mixture('carbon gas', [co_out, co2_out])
        carbon_mixture.temp_kelvin = condenser_temp
        condenser.outputs['carbon gas'].set(carbon_mixture)
    except:
        # no carbon species in the iron making off gas
        pass

    # We imagine that we don't recover useful energy from the
    # condenser, and everything is thermal loss
    thermal_losses = EnergyFlow('losses', -condenser.thermal_energy_balance())
    condenser.outputs['losses'].set(thermal_losses)


def adjust_plasma_energy_flows(system: System):
    """
    Can reduce the energy requirements after the heat exchanger energy has been calculated.
    """
    device_name = system.system_vars['steelmaking device name']

    energy_balance = system.devices[device_name].energy_balance()
    if energy_balance > 1e-5:
        # unexpected, would expect inputs to be greater than inputs after recovering some heat from
        # the heat exchanger
        raise Exception('Expected negative or zero energy balance in the plasma smelter before adjustment')

    system.devices[device_name].inputs['electricity'].energy += energy_balance
    assert system.devices[device_name].inputs['electricity'], "electricity draw must be positive"


# H2 heater energy requirements!!
def add_h2_heater_flows(system: System):
    h2_heaters = system.devices_containing_name('h2 heater')
    if len(h2_heaters) == 0:
        return
    
    for heater_name in h2_heaters:
        if not math.isclose(system.devices[heater_name].mass_balance(), 0.0, abs_tol=1e-9):
            # adjust the mass balance
            output_gas = system.devices[heater_name].first_output_containing_name('h2 rich gas')
            input_gas = system.devices[heater_name].first_input_containing_name('h2 rich gas')
            if math.isclose(output_gas.mass, input_gas.mass):
                continue
            elif output_gas.mass > input_gas.mass:
                system.devices[heater_name].first_input_containing_name('h2 rich gas').mass = output_gas.mass
            else:
                if isinstance(system.devices[heater_name].first_output_containing_name('h2 rich gas'), species.Mixture):
                    system.devices[heater_name].first_output_containing_name('h2 rich gas').species('H2').mass = input_gas.mass
                else: # probs an instance of the Species class
                    system.devices[heater_name].first_output_containing_name('h2 rich gas').mass = input_gas.mass

        if not math.isclose(system.devices[heater_name].energy_balance(), 0.0, abs_tol=1e-9):
            efficiency = 0.98
            required_thermal_energy = system.devices[heater_name].thermal_energy_balance()
            if required_thermal_energy >= 0:
                system.devices[heater_name].inputs['electricity'].energy += required_thermal_energy / efficiency
                system.devices[heater_name].outputs['losses'].energy += required_thermal_energy * (1 - efficiency) / efficiency
            else:
                # the heat exchanger has given all the necessary heat
                # cooling needs to take place. Add all as thermal losses
                system.devices[heater_name].outputs['losses'].energy -= required_thermal_energy


# Plot Helpers
def electricity_demand_per_major_device(system: System) -> Dict[str, float]:
    electricity = {
        '1. water electrolysis': system.devices['water electrolysis'].inputs.get('electricity', EnergyFlow(0.0)).energy,
        '2. h2 storage': system.devices['h2 storage'].inputs.get('electricity', EnergyFlow(0.0)).energy,
        '3. h2 heater': 0.0,
        '4. ore heater': system.devices['ore heater'].inputs.get('electricity', EnergyFlow(0.0)).energy,
        '5. plasma or eaf': 0.0,
    }

    h2_heaters = system.devices_containing_name('h2 heater')
    for device_name in h2_heaters:
        electricity['3. h2 heater'] += system.devices[device_name].inputs.get('electricity', EnergyFlow(0.0)).energy

    if 'plasma smelter' in system.devices:
        electricity['5. plasma or eaf'] += system.devices['plasma smelter'].inputs.get('electricity', EnergyFlow(0.0)).energy
    elif 'eaf' in system.devices:
        electricity['5. plasma or eaf'] += system.devices['eaf'].inputs.get('electricity', EnergyFlow(0.0)).energy
    else:
        raise Exception("Expected a device called 'plasma smelter' or 'eaf' in the steel making system")

    return electricity


def histogram_labels_from_datasets(dataset_dicts: List[Dict[str, float]]) -> List[str]:
    labels = []
    for dataset_dict in dataset_dicts:
        labels += list(dataset_dict.keys())
    return sorted(set(labels))


def add_stacked_histogram_data_to_axis(ax: plt.Axes, histogram_column_names: List[str], stacked_data_labels: List[str], 
                                       dataset_dicts: List[Dict[str, float]], scale_data=1.0):
    bottom = np.array([0.0] * len(histogram_column_names))
    for label in stacked_data_labels:
        data_for_this_label = np.array([d[label] * scale_data for d in dataset_dicts])
        ax.bar(histogram_column_names, data_for_this_label, bottom=bottom, label=label)
        bottom = bottom + data_for_this_label


def add_titles_to_axis(ax: plt.Axes, title: str, y_label: str):
    ax.set_title(title)
    ax.set_ylabel(y_label)
    ax.legend(bbox_to_anchor = (1.0, 1.0), loc='upper left')
    plt.subplots_adjust(right=0.8)
    ax.grid(axis='y', linestyle='--')


# Levelised Cost of Production Helpers
def operating_cost_per_tonne(inputs: Dict[str, float]) -> Dict[str, float]:
    # Electricity cost USD / MWh
    # TODO! This will vary a lot based on hydrogen storage and plant capacity factor.
    electricity_cpmwh = 93.1
    
    # cpt = cost per tonne (USD), cpk = cost per kg (USD)
    ore_cpt = 100.0 # big difference between my price and the slides
    cao_cpk = 0.08 # cost per kg
    mgo_cpk = 0.49 
    o2_cpk = 0.0 # could make this free, since it's a byproduct of electrolysis?
    h2o_cpk = 0.0 # assumption that water should be close to zero cost, especially since it's a byproduct of reduction?
    carbon_cpt = 130.0
    
    # usd per hour. Kind of a guess so that it comes out 
    # at 60 USD / tonne of steel. 
    labour_cph = 40.0

    cost = {
        'Electricity' : inputs['electricity'] * electricity_cpmwh / 3.6e+9,
        'Ore' : inputs['ore'] * ore_cpt / 1000,
        'CaO' : inputs['CaO'] * cao_cpk,
        'MgO' : inputs['MgO'] * mgo_cpk,
        'Carbon' : inputs['C'] * carbon_cpt / 1000,
        'Oxygen' : inputs['O2'] * o2_cpk,
        'Water' : inputs['H2O'] * h2o_cpk,
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


def lcop(capex, annual_operating_cost, annual_production, plant_lifetime_years):
    return (annuity_factor(plant_lifetime_years)*capex + annual_operating_cost) / annual_production


if __name__ == '__main__':
    main()
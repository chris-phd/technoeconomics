#!/usr/bin/env python3

import copy
import sys
import os
import numpy as np
import math
from typing import Type, List, Union, Dict
from steel_plants import create_plasma_system, create_dri_eaf_system, create_hybrid_system

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
    plasma_system = create_plasma_system()
    dri_eaf_system = create_dri_eaf_system()
    hybrid33_system = create_hybrid_system("hybrid33 steelmaking", 33.33)
    hybrid95_system = create_hybrid_system("hybrid95 steelmaking", 95.0)

    # Overwrite system vars here to modify behaviour

    # Add mass and energy flow
    add_plasma_mass_and_energy(plasma_system)
    add_dri_eaf_mass_and_energy(dri_eaf_system)
    # add_hybrid_mass_and_energy(hybrid33_system)
    # print(f"plasma ore mass = {hybrid33_system.devices['ore heater'].inputs['ore'].mass}")
    # add_hybrid_mass_and_energy(hybrid95_system)
    # print(f"plasma ore mass = {hybrid95_system.devices['ore heater'].inputs['ore'].mass}")

    # print(plasma_system)
    # print(dri_eaf_system)
    # print(hybrid33_system)
    # print(hybrid95_system)


# Mass and Energy Flows - System Level
def add_plasma_mass_and_energy(system: System):
    verify_system_vars(system)
    add_ore_composition(system)
    add_steel_out(system)
    add_plasma_flows_initial(system)
    add_ore(system)
    # add_plasma_flows_final(system)


def add_dri_eaf_mass_and_energy(system: System):
    verify_system_vars(system)
    add_ore_composition(system)
    add_steel_out(system)
    add_eaf_flows_initial(system)
    add_ore(system)
    add_fluidized_bed_flows(system)
    add_briquetting_flows(system)
    add_eaf_flows_final(system)


def add_hybrid_mass_and_energy(system: System):
    verify_system_vars(system)
    add_ore_composition(system)
    add_steel_out(system)
    add_plasma_flows_initial(system)
    add_ore(system)
    add_fluidized_bed_flows(system)
    add_briquetting_flows(system)
    # add_plasma_flows_final(system)


def verify_system_vars(system: System):
    # TODO.
    # Raise exception if the system variables necessary
    # for calculating the mass and energy flow are not set
    # correctly.
    print("steel_mass_energy.verify_system_vars: Implement me after the req system vars are known!")
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

    hematite_perc = 100.0 - ore_comp['gangue']
    iron_perc = hematite_perc * iron_to_hematite_ratio
    ore_comp['Fe'] = iron_perc

    return ore_comp


def add_ore_composition(system: System):
    """
    Add 'ore composition' and 'ore composition simple' to the system variables.
    Ore composition simple is the hematite ore with only SiO2, Al2O3, CaO and MgO
    impurities.
    """

    # Mass percent of dry ore.
    # Remaining mass percent is oxygen in the iron oxide.
    # Values are in mass / weight percent.
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

    ore_composition_complex['gangue'] = sum(ore_composition_complex.values()) - ore_composition_complex['Fe']
    ore_composition_complex['hematite'] = 100 - ore_composition_complex['gangue']
    ore_composition_complex = hematite_normalise(ore_composition_complex)

    # Neglecting the trace gangue elements. Adding the mass of the trace elements
    # to the remaining impurities equally. Simplification for the mass flow calculations.
    # Values are in mass / weight percent.
    ore_composition_simple = {'Fe': 65.263,
                                'SiO2': 3.91375,
                                'Al2O3': 2.53675,
                                'CaO': 0.13175,
                                'MgO': 0.18475}

    ore_composition_simple['gangue'] = sum(ore_composition_simple.values()) - ore_composition_simple['Fe']
    ore_composition_simple['hematite'] = 100 - ore_composition_simple['gangue']
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

        cao_flux.mass = b2_basicity * sio2_gangue.mass - cao_gangue.mass
        mgo_flux.mass = b4_basicity * (al2o3_gangue.mass + sio2_gangue.mass) - cao_gangue.mass - cao_flux.mass - mgo_gangue.mass

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

    ore = species.Mixture('ore', [fe2o3_ore, fe3o4, feo, fe,
                          cao_gangue, mgo_gangue, sio2_gangue, al2o3_gangue])
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

    h2_excess = copy.deepcopy(h2_consumed)
    h2_excess.mols = (excess_h2_ratio - 1) * h2_consumed.mols

    h2_total = species.create_h2_species()
    h2_total.mols = h2_consumed.mols + h2_excess.mols

    hydrogen = species.Mixture('h2', [h2_total])
    hydrogen.temp_kelvin = in_gas_temp 
    try:
        ironmaking_device.inputs['h2'].set(hydrogen)
    except KeyError:
        ironmaking_device.inputs['h2 h2o'].set(hydrogen)
    # Set initial guess for the out gas temp
    # Then iteratively solve fo the temp that balances the energy balance

    out_gas_temp = in_gas_temp

    off_gas = species.Mixture('h2 h2o', [h2o, h2_excess])
    off_gas.temp_kelvin = out_gas_temp
    ironmaking_device.outputs['h2 h2o'].set(off_gas)
    
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
        specific_enthalpy = ironmaking_device.outputs['h2 h2o'].cp()
        ironmaking_device.outputs['h2 h2o'].temp_kelvin -= energy_balance / specific_enthalpy
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
        try:
            second_iron_making_device.inputs['h2'].set(hydrogen)
        except KeyError:
            second_iron_making_device.inputs['h2 h2o'].set(hydrogen)
        
        try:
            second_iron_making_device.outputs['h2'].set(hydrogen)
        except KeyError:
            second_iron_making_device.outputs['h2 h2o'].set(hydrogen)
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


def hydrogen_plasma_radiation_losses():
    print("hydrogen_plasma_radiation_losses: Implement me!")
    return 0.0


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
    target_o2_consumption_kg = system.system_vars['o2 injection kg']
    assert target_o2_consumption_kg > o2_oxidation.mass

    # Assume a mix of CO and CO2 is produced. We know from hornby2021, that
    # approx 10% of energy comes from CO formation and 24% of energy comes from
    # CO2 formation, so use this as a guide. Main simplification is that we
    # don't include the CO formed from the reduction of FeO by C.
    o2_combustion = species.create_o2_species()
    o2_combustion.mass = target_o2_consumption_kg - o2_oxidation.mass # some o2 may already be used in fe oxidation
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
    infiltrated_air
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
    excess_h2_ratio = system.system_vars['plasma reduction percent']
    steelmaking_device_name = system.system_vars['steelmaking device name']
    steelmaking_device = system.devices[steelmaking_device_name]
    first_ironmaking_device_name = system.system_vars['ironmaking device names'][0]

    # the plasma smelter can use hbi or ore fines.
    ironbearing_material = steelmaking_device.inputs.get('hbi')
    if ironbearing_material is None:
        ironbearing_material = steelmaking_device.mass_in.get('ore')

    if ironbearing_material is None:
        raise ValueError('No iron bearing material found in the input mass of the plasma smelter')

    iron_making_device = system.devices[first_ironmaking_device_name]
    ore_mass = iron_making_device.inputs['ore'].mass
    fe_target, feo_target, fe3o4_target, fe2o3_target = iron_species_from_reduction_degree(reduction_degree, ore_mass)

    if not math.isclose(fe3o4_target.mols, 0) or not math.isclose(fe2o3_target.mols, 0):
        raise Exception("Error: Expect plasma hydrogen reduction to completly reduce magnetite and hematite")

    # TODO! Reduce repetition with the same logic dri function
    delta_fe = fe_target.mols - ironbearing_material.species('Fe').mols
    delta_feo = feo_target.mols - ironbearing_material.species('FeO').mols
    delta_fe3o4 = fe3o4_target.mols - ironbearing_material.species('Fe3O4').mols

    assert delta_fe >= 0 and delta_feo >= 0 and delta_fe3o4 >= 0, "Error: Plasma reduction degree should be higher than prereduction during ironmaking"

    # The net reactions involved in the Hydrogen Plasma reduction stage of this device
    num_fe_formations = delta_fe
    num_feo_formations = (num_fe_formations + delta_feo) / 3
    num_fe3o4_formations = (num_feo_formations + delta_fe3o4) / 2

    print("FIX ME! Need to calculate the reaction enthalpy from monotomic H reduction. The fraction of H reduction will depend on temp")
    steelmaking_device.add_chemical_energy_in(-num_fe_formations * species.delta_h_feo_h2_fe_h2o(reaction_temp) \
                                              -num_feo_formations * species.delta_h_fe3o4_h2_3feo_h2o(reaction_temp) \
                                              -num_fe3o4_formations * species.delta_h_3fe2o3_h2_2fe3o4_h2o(reaction_temp))

    # determine the mass of h2o in the off gas
    h2o = species.create_h2o_species()
    h2o.mols = num_fe_formations + num_feo_formations + num_fe3o4_formations
    h2o.temp_kelvin = celsius_to_kelvin(1750) 

    # the amount of h2 in the in gas
    h2_consumed = species.create_h2_species()
    h2_consumed.mols = h2o.mols
    h2_consumed.temp_kelvin = celsius_to_kelvin(25)

    assert excess_h2_ratio >= 1
    h2_excess = copy.deepcopy(h2_consumed)
    h2_excess.mols = h2_consumed.mols * (excess_h2_ratio - 1)

    h2_total = species.create_h2_species()
    h2_total.mols = h2_consumed.mols + h2_excess.mols

    hydrogen = species.Mixture('gas in', [h2_total])
    hydrogen.temp_kelvin = celsius_to_kelvin(25)
    steelmaking_device.inputs['h2'].set(hydrogen)

    # Add the carbon required for the alloy
    c_alloy = copy.deepcopy(steelmaking_device.mass_out['steel'].species('C'))

    # Add carbon / oxygen needed for reduction / oxidation of FeO / Fe
    feo_slag = steelmaking_device.mass_out['slag'].species('FeO')

    # Not sure if we want to inject o2 yet. We want to for refining the steel
    target_o2_consumption_kg = system.system_vars['o2 injection kg']

    o2_oxidation = species.create_o2_species()
    c_reduction = species.create_c_species()
    if feo_slag.mols > feo_target.mols:
        # metallic fe is oxidised by injected O2
        o2_oxidation.mols = 0.5 * (feo_slag.mols - feo_target.mols)
        num_feo_formation_reactions = o2_oxidation.mols
        steelmaking_device.add_chemical_energy_in(-num_feo_formation_reactions * species.delta_h_2fe_o2_2feo(reaction_temp))
    else:
        # feo is reduced by the injected carbon
        c_reduction.mols = (feo_target.mols - feo_slag.mols)
        num_feo_c_reduction_reactions = c_reduction.mols
        steelmaking_device.add_chemical_energy_in(-num_feo_c_reduction_reactions * delta_h_feo_c_fe_co(reaction_temp))

    assert target_o2_consumption_kg > o2_oxidation.mass

    # We assume oxygen always oxidises Fe to max FeO solubility in the slag before
    # it begins combusting with the carbon. 

    # Assume a mix of CO and CO2 is produced. We know from hornby2021, that
    # approx 10% of energy comes from CO formation and 24% of energy comes from
    # CO2 formation, so use this as a guide. Main simplification is that we
    # don't include the CO formed from the reduction of FeO by C.
    o2_combustion = create_o2_species()
    o2_combustion.mass = target_o2_consumption_kg - o2_oxidation.mass # some o2 may already be used in fe oxidation
    n_reactions = o2_combustion.mols
    num_co_reactions = n_reactions / 2.348
    num_co2_reactions = n_reactions - num_co_reactions

    # This reaction may occur at a lower temp, since it is not at the plasma steel interface?
    steelmaking_device.add_chemical_energy_in(-num_co_reactions * delta_h_2c_o2_2co(reaction_temp) \
                                              -num_co2_reactions * delta_h_c_o2_co2(reaction_temp))

    c_combustion = create_c_species()
    c_combustion.mols = 2*num_co_reactions + num_co2_reactions

    c_injected = create_c_species()
    c_injected.mols = c_combustion.mols + c_reduction.mols + c_alloy.mols
    c_injected.temp_kelvin = celsius_to_kelvin(25) # assume room temp
    steelmaking_device.add_mass_in(c_injected)

    o2_injected = create_o2_species()
    o2_injected.mols = o2_combustion.mols + o2_oxidation.mols
    o2_injected.temp_kelvin = celsius_to_kelvin(25) # assume room temp
    steelmaking_device.add_mass_in(o2_injected)

    co = create_co_species()
    co.mols = 2 * num_co_reactions + c_reduction.mols
    co2 = create_co2_species()
    co2.mols = num_co2_reactions
    off_gas = Mixture('gas out', [co, co2, h2o, h2_excess])
    off_gas.temp_kelvin = reaction_temp
    steelmaking_device.add_mass_out(off_gas)

    # IGNORE LOSSES FROM INFILTRATED AIR, BECAUSE WE NEED TO HEAT RECOVER THE OFF GAS
    # OPTIMISTICALLY ASSUME THE PLASMA SMELTER IS PRETTY MUCH AIR TIGHT / CONTROLLED ATMOSPHERE. 

    # TODO: Reduce repetition with the EAF?
    # Need to add the required electrical energy to balance the 
    # required thermal energy, accounting for the energy already. provided
    # by the chemical reactions (oxidation, reduction, combustion etc.)
    # Assume high efficiency RF ICP plasma gun.
    plasma_torch_eff = system.system_vars['plasma torch eff pecent'] * 0.01
    electrical_energy = steelmaking_device.total_energy_balance() / plasma_torch_eff
    steelmaking_device.add_electrical_energy_in(electrical_energy)
    steelmaking_device.add_electrical_losses(electrical_energy * (1 - plasma_torch_eff))

    # Add the thermal losses 
    # Assume same as an EAF. Convection and conduction losses are 4% of input heat. 
    # From sujay kumar dutta pg 425 
    convection_conduction_losses = 0.04 * steelmaking_device.thermal_energy_balance()
    plasma_surface_radius = 3.8 * 0.6667 # assume a smaller radius than the EAF due to superior kinetics
    capacity_tonnes = 180*0.6667 # assumption. Smaller than an EAF due to superior kinetics
    tap_to_tap_secs = 60*60*0.6667 # assumption. Less than an EAF due to superior kinetics
    radiation_losses = steelsurface_radiation_losses(np.pi*(plasma_surface_radius)**2, 
                                                     reaction_temp, celsius_to_kelvin(25),
                                                     capacity_tonnes, tap_to_tap_secs)
    radiation_losses += hydrogen_plasma_radiation_losses()
    total_thermal_losses = radiation_losses + convection_conduction_losses
    steelmaking_device.add_thermal_losses(total_thermal_losses)
    # Increase the electrical energy to balance the thermal losses 
    steelmaking_device.add_electrical_energy_in(total_thermal_losses)



    print(f"Total energy = {sum(steelmaking_device.energy_in.values())*2.77778e-7:.2e} kWh")

if __name__ == '__main__':
    main()
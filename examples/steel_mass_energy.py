#!/usr/bin/env python3

import copy
import sys
import os
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
    add_hybrid_mass_and_energy(hybrid33_system)
    add_hybrid_mass_and_energy(hybrid95_system)

    print(plasma_system)
    print(dri_eaf_system)
    print(hybrid33_system)
    print(hybrid95_system)


# Mass and Energy Flows - System Level
def add_plasma_mass_and_energy(system: System):
    verify_system_vars(system)
    add_ore_composition(system)
    add_steel_out(system)
    add_plasma_flows_initial(system)
    add_ore(system)


def add_dri_eaf_mass_and_energy(system: System):
    verify_system_vars(system)
    add_ore_composition(system)
    add_steel_out(system)
    add_eaf_flows_initial(system)
    add_ore(system)
    add_fluidized_bed_flows(system)
    add_briquetting_flows(system)


def add_hybrid_mass_and_energy(system: System):
    verify_system_vars(system)
    add_ore_composition(system)
    add_steel_out(system)
    add_plasma_flows_initial(system)
    add_ore(system)
    add_fluidized_bed_flows(system)
    add_briquetting_flows(system)


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

    #TODO! This should be a maximum rather than a target. It should depend 
    # on the oxygen in the FeO if no O2 is injected.
    slag_feo_mass_perc = system.system_vars['feo percent in slag']

    feo_slag = species.create_feo_species()
    sio2_gangue = species.create_sio2_species()
    al2o3_gangue = species.create_al2o3_species()
    cao_gangue = species.create_cao_species()
    mgo_gangue = species.create_mgo_species()
    cao_flux = species.create_cao_species()
    mgo_flux = species.create_mgo_species()

    steelmaking_device = system.devices[steelmaking_device_name]
    fe = steelmaking_device.outputs['steel'].species('Fe')
    
    ore_composition_simple = system.system_vars['ore composition simple']

    # iterative solve for the slag mass
    slag_mass = 0.4 * fe.mass
    for _ in range(10):
        feo_slag.mass = slag_mass * slag_feo_mass_perc * 0.01

        fe_total_mass = fe.mass + feo_slag.mass * fe.mm / feo_slag.mm
        ore_mass = fe_total_mass / (ore_composition_simple['Fe'] * 0.01)

        sio2_gangue.mass = ore_mass * ore_composition_simple['SiO2'] * 0.01
        al2o3_gangue.mass = ore_mass * ore_composition_simple['Al2O3'] * 0.01
        cao_gangue.mass = ore_mass * ore_composition_simple['CaO'] * 0.01
        mgo_gangue.mass = ore_mass * ore_composition_simple['MgO'] * 0.01

        cao_flux.mass = b2_basicity * sio2_gangue.mass - cao_gangue.mass
        mgo_flux.mass = b4_basicity * (al2o3_gangue.mass + sio2_gangue.mass) - cao_flux.mass- mgo_gangue.mass

        slag_mass = sio2_gangue.mass + al2o3_gangue.mass \
                    + cao_gangue.mass + cao_flux.mass + mgo_gangue.mass + mgo_flux.mass \
                    + feo_slag.mass

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
            print(f"Converged on the out gas temp after {i} iterations")
            print(f"Out gas temp: {ironmaking_device.outputs['h2 h2o'].temp_kelvin}")
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

if __name__ == '__main__':
    main()
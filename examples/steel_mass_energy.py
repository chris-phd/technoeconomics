#!/usr/bin/env python3

import copy
import sys
import os
from typing import Type, List, Union, Dict
from steel_plants import create_plasma_system, create_dri_eaf_system, create_hybrid_system

try:
    import technoeconomics.species as species 
    from technoeconomics.system import System, Device, Flow
    from technoeconomics.utils import celsius_to_kelvin, kelvin_to_celsius
except ImportError:
    # If the technoeconomics package is not installed via pip,
    # add the package directory to the system path.
    examples_dir = os.path.dirname(os.path.abspath(__file__))
    package_dir = os.path.dirname(examples_dir)
    sys.path.insert(0, package_dir)

    import technoeconomics.species as species 
    from technoeconomics.system import System, Device, Flow
    from technoeconomics.utils import celsius_to_kelvin, kelvin_to_celsius


def main():
    # TODO: Add transferred and non-transferred arc system.
    plasma_system = create_plasma_system()
    dri_eaf_system = create_dri_eaf_system()
    hybrid33_system = create_hybrid_system("hybrid33 steelmaking", 33.33)
    hybrid95_system = create_hybrid_system("hybrid95 steelmaking", 95.0)

    # Overwrite system vars to modify behaviour

    # Add mass and energy flow
    add_plasma_mass_and_energy(plasma_system)
    add_dri_eaf_mass_and_energy(dri_eaf_system)
    add_hybrid_mass_and_energy(hybrid33_system)
    add_hybrid_mass_and_energy(hybrid95_system)

    print(plasma_system)


# Mass and Energy Flows - System Level
def add_plasma_mass_and_energy(system: System):

    verify_system_vars(system)

    add_ore_composition(system)
    add_steel_out(system)
    add_plasma_flows_initial(system)


def add_dri_eaf_mass_and_energy(system: System):
    add_ore_composition(system)
    add_steel_out(system)
    add_eaf_flows_initial(system)


def add_hybrid_mass_and_energy(system: System):
    verify_system_vars(system)
    add_ore_composition(system)
    add_steel_out(system)
    add_plasma_flows_initial(system)


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
    system.get_output(steelmaking_device_name, 'steel').mass = steel


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
    fe = steelmaking_device.outputs['steel'].mass.species('Fe')
    
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
    steelmaking_device.inputs['flux'].mass = (flux)

    sio2_slag = copy.deepcopy(sio2_gangue)
    al2o3_slag = copy.deepcopy(al2o3_gangue)
    cao_slag = copy.deepcopy(cao_gangue)
    mgo_slag = copy.deepcopy(mgo_gangue)
    cao_slag.mass += cao_flux.mass
    mgo_slag.mass += mgo_flux.mass
    slag = species.Mixture('slag', [feo_slag, sio2_slag, al2o3_slag, cao_slag, mgo_slag])
    slag.temp_kelvin = system.system_vars['steel exit temp K']
    steelmaking_device.outputs['slag'] = slag


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
    system.devices[steelmaking_device_name].inputs['electrode'] = electrode_consumption


def add_plasma_flows_initial(system: System):
    """
    Begin adding Plasma Smelter mass and energy flow to the system.
    Primarily responsible for determining the slag / flux requirements.
    """
    add_slag_and_flux_mass(system)
    # TODO: If using a DC arc plasma, add electrode consumption here


if __name__ == '__main__':
    main()
#!/usr/bin/env python3

import argparse
import csv
import os
import sys
from typing import List, Dict, Any
import matplotlib.pyplot as plt
from create_plants import create_dri_eaf_system, create_hybrid_system, create_plasma_system
from mass_energy_flow import solve_mass_energy_flow, add_dri_eaf_mass_and_energy, add_hybrid_mass_and_energy,\
                             add_plasma_mass_and_energy, electricity_demand_per_major_device, report_slag_composition
from plant_costs import load_prices_from_csv, add_steel_plant_lcop
from plot_helpers import histogram_labels_from_datasets, add_stacked_histogram_data_to_axis, add_titles_to_axis

try:
    from technoeconomics.system import System
except ImportError:
    # If the technoeconomics package is not installed via pip,
    # add the package directory to the system path.
    examples_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    package_dir = os.path.dirname(examples_dir)
    sys.path.insert(0, package_dir)

    from technoeconomics.system import System

def main():
    ## Setup
    args = parse_args()
    systems = create_systems()
    system_names = [s.name for s in systems]
    prices = load_prices_from_csv(args.price_file)
    config = load_config_from_csv(args.config_file)

    if args.render:
        render_systems(systems, args.render)

    ## Solve
    print("Solving mass and energy flow and calculating cost...")
    for s in systems:
        solve_mass_energy_flow(s, s.add_mass_energy_flow_func, args.verbose)
        add_steel_plant_lcop(s, prices, args.verbose)
    print("Done.")
    
    ## Report
    for s in systems:
        print(f"{s.name} total lcop [USD] = {sum(s.lcop_breakdown.values()):.2f}")
        for k, v in s.lcop_breakdown.items():
            print(f"    {k} = {v:.2f}")
        
        if args.verbose:
            report_slag_composition(s)

    ## Plots
    if args.mass_flow:
        inputs_for_systems = [s.system_inputs(ignore_flows_named=['infiltrated air'], separate_mixtures_named=['h2 rich gas'], mass_flow_only=True) for s in systems]
        input_mass_labels = histogram_labels_from_datasets(inputs_for_systems)
        _, input_mass_ax = plt.subplots()
        add_stacked_histogram_data_to_axis(input_mass_ax, system_names, input_mass_labels, inputs_for_systems)
        add_titles_to_axis(input_mass_ax, 'Input Mass Flow / Tonne Liquid Steel', 'Mass (kg)')

        outputs_for_systems = [s.system_outputs(ignore_flows_named=['infiltrated air'], mass_flow_only=True) for s in systems]
        output_mass_labels = histogram_labels_from_datasets(outputs_for_systems)
        _, output_mass_ax = plt.subplots()
        add_stacked_histogram_data_to_axis(output_mass_ax, system_names, output_mass_labels, outputs_for_systems)
        add_titles_to_axis(output_mass_ax, 'Output Mass Flow / Tonne Liquid Steel', 'Mass (kg)')

    if args.energy_flow:
        electricity_for_systems = [electricity_demand_per_major_device(s) for s in systems]
        electricity_labels = histogram_labels_from_datasets(electricity_for_systems)
        _, energy_ax = plt.subplots()
        add_stacked_histogram_data_to_axis(energy_ax, system_names, electricity_labels, electricity_for_systems)
        add_titles_to_axis(energy_ax, 'Electricity Demand / Tonne Liquid Steel', 'Energy (GJ)')

    lcop_itemised_for_systems = [s.lcop_breakdown for s in systems]
    lcop_labels = histogram_labels_from_datasets(lcop_itemised_for_systems)
    _, lcop_ax = plt.subplots()
    add_stacked_histogram_data_to_axis(lcop_ax, system_names, lcop_labels, lcop_itemised_for_systems)
    add_titles_to_axis(lcop_ax, 'Levelised Cost of Liquid Steel', '$USD / tonne liquid steel')

    plt.show()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='perform the technoeconomic analysis on hydrogen plasma based low emission steel plants and calculates the levelised cost of liquid steel.')
    parser.add_argument('-p', '--price_file', help='path to the csv file containing capex and commondity prices.', required=False, default='prices_default.csv')
    parser.add_argument('-c', '--config_file', help='path to the csv file containing the system configuration.', required=False, default='config_default.csv')
    parser.add_argument('-r', '--render', help='render the steelplant system diagrams. "<system name>" or "ALL"', required=False, default=None)
    parser.add_argument('-s', '--sensitivity_analysis', help='perform sensitivity analysis boolean flag.', required=False, action='store_true')
    parser.add_argument('-m', '--mass_flow', help='show the mass flow bar chart boolean flag.', required=False, action='store_true')
    parser.add_argument('-e', '--energy_flow', help='show the enery flow bar chart boolean flag.', required=False, action='store_true')
    parser.add_argument('-v', '--verbose', help='when enabled, print / log debug messages.', required=False, action='store_true')
    args = parser.parse_args()
    return args


def create_systems() -> List[System]:
    annual_steel_production_tonnes = 1.5e6
    plant_lifetime_years = 20.0
    # capacity_factor = 0.9 # TODO! Need to add this.
    on_premises_h2_production = False
    h2_storage_type = "salt caverns"

    plasma_system = create_plasma_system("Plasma", on_premises_h2_production, h2_storage_type, annual_steel_production_tonnes, plant_lifetime_years)
    plasma_ar_h2_system = create_plasma_system("Plasma Ar-H2", on_premises_h2_production, h2_storage_type, annual_steel_production_tonnes, plant_lifetime_years)
    plasma_bof_system = create_plasma_system("Plasma BOF", on_premises_h2_production, h2_storage_type, annual_steel_production_tonnes, plant_lifetime_years, bof_steelmaking=True)
    dri_eaf_system = create_dri_eaf_system("DRI-EAF", on_premises_h2_production, h2_storage_type, annual_steel_production_tonnes, plant_lifetime_years)
    hybrid33_system = create_hybrid_system("Hybrid 33", on_premises_h2_production, h2_storage_type, 33.33, annual_steel_production_tonnes, plant_lifetime_years)
    hybrid33_ar_h2_system = create_hybrid_system("Hybrid 33 Ar-H2", on_premises_h2_production, h2_storage_type, 33.33, annual_steel_production_tonnes, plant_lifetime_years)
    hybrid33_bof_system = create_hybrid_system("Hybrid 33 BOF", on_premises_h2_production, h2_storage_type, 33.33, annual_steel_production_tonnes, plant_lifetime_years, bof_steelmaking=True)
    hybrid55_system = create_hybrid_system("Hybrid 55", on_premises_h2_production, h2_storage_type, 55.0, annual_steel_production_tonnes, plant_lifetime_years)
    hybrid95_system = create_hybrid_system("Hybrid 90", on_premises_h2_production, h2_storage_type, 90.0, annual_steel_production_tonnes, plant_lifetime_years)

    plasma_system.add_mass_energy_flow_func = add_plasma_mass_and_energy
    plasma_ar_h2_system.add_mass_energy_flow_func = add_plasma_mass_and_energy
    plasma_bof_system.add_mass_energy_flow_func = add_plasma_mass_and_energy
    dri_eaf_system.add_mass_energy_flow_func = add_dri_eaf_mass_and_energy
    hybrid33_system.add_mass_energy_flow_func = add_hybrid_mass_and_energy
    hybrid33_ar_h2_system.add_mass_energy_flow_func = add_hybrid_mass_and_energy
    hybrid33_bof_system.add_mass_energy_flow_func = add_hybrid_mass_and_energy
    hybrid55_system.add_mass_energy_flow_func = add_hybrid_mass_and_energy
    hybrid95_system.add_mass_energy_flow_func = add_hybrid_mass_and_energy

    systems = [plasma_system,
               plasma_ar_h2_system,
               plasma_bof_system,
               dri_eaf_system,
               hybrid33_system,
               hybrid33_ar_h2_system,
               hybrid33_bof_system,
               hybrid55_system,
               hybrid95_system]

    # Overwrite system vars here to modify behaviour
    for system in systems:
        system.system_vars['scrap perc'] = 0.0
        system.system_vars['ore name'] = 'IOA'
        system.system_vars['use mgo slag weight perc'] = True

    plasma_ar_h2_system.system_vars['argon molar percent in h2 plasma'] = 10.0
    hybrid33_ar_h2_system.system_vars['argon molar percent in h2 plasma'] = 10.0

    # For systems where hydrogen is the carrier of thermal energy as well as the reducing
    # agent, you excess h2 ratio may need to be adjusted to ensure there is anough thermal
    # energy to melt the steel and maintain the heat balance. Values listed here is only the initial guess.
    plasma_system.system_vars['plasma h2 excess ratio'] = 2.5 # 1.75 too low, anticipate 40-50% utilisation
    plasma_ar_h2_system.system_vars['plasma h2 excess ratio'] = 1.0
    plasma_bof_system.system_vars['plasma h2 excess ratio'] = 2.5 # 1.75 too low, as above
    hybrid33_system.system_vars['plasma h2 excess ratio'] = 4.0
    hybrid33_ar_h2_system.system_vars['plasma h2 excess ratio'] = 3.5
    hybrid55_system.system_vars['plasma h2 excess ratio'] = 5.5
    hybrid95_system.system_vars['plasma h2 excess ratio'] = 30.0

    return systems


def render_systems(systems: List[System], render_name: str):
    if render_name.upper() == "ALL":
        for s in systems:
            s.render_system()
    else:
        for s in systems:
            if s.name == render_name:
                s.render_system()
                break


def load_config_from_csv(filename: str) -> Dict[str, Dict[str, Any]]:
    config = {}
    with open(filename, newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # skip the title row
        for row in reader:
            system_name = row[0].strip().lower()
            variable_name = row[1].strip().lower()
            variable_type = row[3].strip().lower()
            variable_value = row[2].strip()
            if variable_type.lower() == "string":
                pass
            elif variable_type.lower() == "number":
                variable_value = float(variable_value)
            elif variable_type.lower() == "boolean":
                variable_value = bool(variable_value)
            else:
                raise ValueError(f"Unrecognised variable type {variable_type} in config file {filename}.")

            if system_name in config:
                config[system_name][variable_name] = variable_value
            else:
                config[system_name] = {variable_name: variable_value}
    
    return config

if __name__ == '__main__':
    main()

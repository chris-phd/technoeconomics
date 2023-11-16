#!/usr/bin/env python3

import argparse
import os
import sys
from typing import List
import matplotlib.pyplot as plt
from create_plants import create_dri_eaf_system
from mass_energy_flow import solve_mass_energy_flow, add_dri_eaf_mass_and_energy, electricity_demand_per_major_device
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
    args = parse_args()
    systems = create_systems()
    system_names = [s.name for s in systems]

    if args.render:
        render_systems(systems, args.render)

    for s in systems:
        solve_mass_energy_flow(s, s.add_mass_energy_flow_func)
        print(s)

    ## Prices
    prices = load_prices_from_csv(args.price_file)
    
    for s in systems:
        add_steel_plant_lcop(s, prices)

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
    parser.add_argument('-r', '--render', help='render the steelplant system diagrams. "<system name>" or "ALL"', required=False, default=None)
    parser.add_argument('-s', '--sensitivity_analysis', help='perform sensitivity analysis boolean flag.', required=False, action='store_true')
    parser.add_argument('-m', '--mass_flow', help='show the mass flow bar chart boolean flag.', required=False, action='store_true')
    parser.add_argument('-e', '--energy_flow', help='show the enery flow bar chart boolean flag.', required=False, action='store_true')
    args = parser.parse_args()
    return args


def create_systems() -> List[System]:
    annual_steel_production_tonnes = 1.5e6
    plant_lifetime_years = 20.0
    # capacity_factor = 0.9 # TODO! Need to add this.
    on_premises_h2_production = False
    h2_storage_type = "salt caverns"

    dri_eaf_system = create_dri_eaf_system("DRI-EAF", on_premises_h2_production, h2_storage_type, annual_steel_production_tonnes, plant_lifetime_years)

    dri_eaf_system.add_mass_energy_flow_func = add_dri_eaf_mass_and_energy

    systems = [dri_eaf_system]
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


if __name__ == '__main__':
    main()

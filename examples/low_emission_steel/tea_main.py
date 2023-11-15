#!/usr/bin/env python3

import argparse

from plant_costs import load_prices_from_csv

def main():
    args = parse_args()
    print(args.price_file)
    print(args.sensitivity_analysis)


    # Load the prices
    prices = load_prices_from_csv(args.price_file)
    print(prices)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='perform the technoeconomic analysis on hydrogen plasma based low emission steel plants and calculates the levelised cost of liquid steel.')
    parser.add_argument('-p', '--price_file', help='path to the csv file containing capex and commondity prices.', required=False, default='prices_default.csv')
    parser.add_argument('-r', '--render', help='render the steelplant system diagrams. "<system name>" or "ALL"', required=False, default=None)
    parser.add_argument('-s', '--sensitivity_analysis', help='perform sensitivity analysis boolean flag.', required=False, action='store_true')
    parser.add_argument('-m', '--mass_flow', help='show the mass flow bar chart boolean flag.', required=False, action='store_true')
    parser.add_argument('-e', '--energy_flow', help='show the enery flow bar chart boolean flag.', required=False, action='store_true')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    main()

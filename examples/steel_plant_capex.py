#!/usr/bin/env python3

import sys
import os
import math

try:
    from technoeconomics.system import System
except ImportError:
    # If the technoeconomics package is not installed via pip,
    # add the package directory to the system path.
    examples_dir = os.path.dirname(os.path.abspath(__file__))
    package_dir = os.path.dirname(examples_dir)
    sys.path.insert(0, package_dir)

    from technoeconomics.system import System


def add_steel_plant_capex(system: System, h2_storage_hours_of_operation: float = 12):
    # system.
    h2_storage_method = 'salt cavern'
    if 'h2 storage method' in system.system_vars:
        h2_storage_method = system.system_vars['h2 storage method']

    mass_h2_per_tonne_steel = system.devices['water electrolysis'].first_output_containing_name('h2').mass
    tonnes_steel_per_hour = system.annual_capacity / (365.25 * 24)
    h2_storage_required = tonnes_steel_per_hour * mass_h2_per_tonne_steel * h2_storage_hours_of_operation
    system.devices['h2 storage'].device_vars['h2 storage size [kg]'] = h2_storage_required
    system.devices['h2 storage'].device_vars['h2 storage type'] = h2_storage_method
    
    if h2_storage_method.lower() == 'salt cavern':
        system.devices['h2 storage'].capex = h2_storage_required * salt_cavern_capex_lord2014()
    elif h2_storage_method.lower() == 'compressed gas vessel':
        system.devices['h2 storage'].capex = h2_storage_required * compressed_h2_gas_vessel_elberry2021()
        system.devices['h2 storage'].device_vars['num h2 storage vessels'] = int(math.ceil(h2_storage_required / 300.0))
    else:
        raise ValueError('h2 storage method not recognised')

    # So the H2 required is alot smaller than a typical salt cavern.
    # So ideally need to share with some other storage application.. or use lots of storage vessels. 


# lord2014
# A. S. Lord, P. H. Kobos, and D. J. Borns, “Geologic storage of hydrogen: 
# Scaling up to meet city transportation demands,” International Journal of Hydrogen Energy, 
# vol. 39, no. 28, pp. 15570–15582, 2014, doi: https://doi.org/10.1016/j.ijhydene.2014.07.121.
def salt_cavern_capex_lord2014():
    """
    Returns the cost per kilo of usable hydrogen stored in a salt cavern. (excludes cushion gas)
    It is up to the function caller to ensure the size of the salt cavern is appropriate for the application.
    """
    # cpk = cost per kilo
    # refers to the usable h2 (so excludes the cushion gas)
    inflation_2014_2023 = 1.29
    stored_h2_cpk_2014 = 1.61 
    stored_h2_cpk_2023 = stored_h2_cpk_2014 * inflation_2014_2023
    return stored_h2_cpk_2023

# elberry2021
# A. M. Elberry, J. Thakur, A. Santasalo-Aarnio, and M. Larmi, “Large-scale compressed
# hydrogen storage as part of renewable electricity storage systems,” International 
# Journal of Hydrogen Energy, vol. 46, no. 29, pp. 15671–15690, 2021, 
# doi: https://doi.org/10.1016/j.ijhydene.2021.02.080.
# TODO: Verify this cost with a few other sources. Quick scan, seems optimistic
def compressed_h2_gas_vessel_elberry2021():
    # Using multifunctional steel layered hydrogen storage vessel (MSLV)
    # Target 160 bar, 25m^3, lower end of the pressure range for MSLV vessels.
    # ~300 kg / vessel
    # Less energy required for compression, cheaper vessels, cheaper compressors.
    # But requires more space, more vessels, possibly more leakage of hydrogen.
    inflation_2016_2023 = 1.27
    stored_h2_cpk_2016 = 350.0
    stored_h2_cpk_2023 = stored_h2_cpk_2016 * inflation_2016_2023
    return stored_h2_cpk_2023
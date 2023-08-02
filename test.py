#!/usr/bin/env python3

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
import os

import technoeconomics.species as species
import technoeconomics.system as system
import technoeconomics.thermo as thermo
import technoeconomics.utils as utils

class UtilsTest(TestCase):
    def test_temp_conversion(self):
        self.assertEqual(utils.celsius_to_kelvin(0), 273.15)
        self.assertEqual(utils.kelvin_to_celsius(3000), 2726.85)


class SystemTest(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.temp_dir_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_system_render(self):
        my_system = system.System("Test System")

        device_a = system.Device("Device A")
        device_b = system.Device("Device B")
        device_c = system.Device("Device C")
        my_system.add_device(device_a)
        my_system.add_device(device_b)
        my_system.add_device(device_c)

        flow_ab = system.Flow("mass_flow_1", 1.0)
        flow_ac = system.Flow("mass_flow_2", 2.0)
        flow_bc = system.Flow("mass_flow_3", 3.0)
        energy_a = system.Flow("energy_flow_1", 4.0)
        my_system.add_flow(device_a.name, device_b.name, flow_ab)
        my_system.add_flow(device_a.name, device_c.name, flow_ac)
        my_system.add_flow(device_b.name, device_c.name, flow_bc)
        my_system.add_system_input(device_a.name, energy_a)

        intial_num_files_in_temp_dir = len(os.listdir(str(self.temp_dir_path)))
        my_system.render(False, str(self.temp_dir_path))
        final_num_files_in_temp_dir = len(os.listdir(str(self.temp_dir_path)))
        graph_render_successful = final_num_files_in_temp_dir == intial_num_files_in_temp_dir + 2
        self.assertTrue(graph_render_successful)


class SpeciesThermoTest(TestCase):
    def test_h2o_heat_capacity(self):
        h2o = species.create_h2o_species()
        h2o.temp_kelvin = utils.celsius_to_kelvin(25)
        molar_cp = h2o.cp()
        specific_cp = h2o.cp(False)
        self.assertAlmostEqual(molar_cp, 75.4, places=1)
        self.assertAlmostEqual(specific_cp, 4.18, places=1)

    def test_air_energy_to_heat(self):
        mass = 1.0 # kg
        air = species.create_air_mixture(mass)
        air.temp_kelvin = utils.celsius_to_kelvin(100)
        heat_energy = air.heat_energy(air.temp_kelvin + 1)
        self.assertAlmostEqual(heat_energy, 1015.4, places=1)
        heat_energy = air.heat_energy(air.temp_kelvin + 700)
        print(f'heat_energy: {heat_energy}')
        self.assertAlmostEqual(heat_energy, 732417.1, places=1)

    def test_iron_heat_energy(self): 
        fe = species.create_fe_species()
        fe.mass = 0.001 # kg
        fe.temp_kelvin = utils.celsius_to_kelvin(1000)
        heat_energy = fe.heat_energy(fe.temp_kelvin + 1)
        print(f'heat_energy: {heat_energy}')
        self.assertAlmostEqual(heat_energy, 0.62, places=1)



if __name__ == '__main__':
    main()
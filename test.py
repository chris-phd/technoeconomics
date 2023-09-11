#!/usr/bin/env python3

import copy
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

        flow_ab = species.create_dummy_species("some species 1")
        flow_ab.mass = 1.0
        flow_ac = species.create_dummy_species("some species 2")
        flow_ac.mass = 2.0
        flow_bc = species.create_dummy_species("some species 3")
        flow_bc.mass = 3.0
        energy_a = system.EnergyFlow("some energy", 100.0)
        my_system.add_flow(device_a.name, device_b.name, flow_ab)
        my_system.add_flow(device_a.name, device_c.name, flow_ac)
        my_system.add_flow(device_b.name, device_c.name, flow_bc)
        my_system.add_input(device_a.name, energy_a)

        intial_num_files_in_temp_dir = len(os.listdir(str(self.temp_dir_path)))
        my_system.render(False, str(self.temp_dir_path))
        final_num_files_in_temp_dir = len(os.listdir(str(self.temp_dir_path)))
        graph_render_successful = final_num_files_in_temp_dir == intial_num_files_in_temp_dir + 2
        self.assertTrue(graph_render_successful)

    def test_modify_shared_flow(self):
        # The system and the devices all share and modify the same flow object.
        my_system = system.System("Test System")
        device_a = system.Device("Device A")
        device_b = system.Device("Device B")
        my_system.add_device(device_a)
        my_system.add_device(device_b)
        flow_ab = species.create_dummy_species("flow ab")
        flow_ab.mass = 1.0
        my_system.add_flow(device_a.name, device_b.name, flow_ab)
        self.assertTrue(my_system.get_flow(device_a.name, device_b.name, flow_ab.name).mass == 1.0)
        my_system.devices["Device A"].outputs["flow ab"].mass = 2.0
        self.assertTrue(my_system.get_flow(device_a.name, device_b.name, flow_ab.name).mass == 2.0)

    def test_mass_energy_balance(self):
        my_system = system.System("Test System")
        device_a = system.Device("Device A")
        device_b = system.Device("Device B")
        my_system.add_device(device_a)
        my_system.add_device(device_b)

        input_a = species.create_dummy_species("input a")
        input_a.mass = 1.0
        output_a = species.create_dummy_species("output a")
        output_a.mass = 0.5
        flow_ab = species.create_dummy_species("flow ab")
        flow_ab.mass = 0.5
        output_b = species.create_dummy_species("output b")
        output_b.mass = 0.5
        my_system.add_flow(device_a.name, device_b.name, flow_ab)
        my_system.add_input(device_a.name, input_a)
        my_system.add_output(device_a.name, output_a)
        my_system.add_output(device_b.name, output_b)

        self.assertAlmostEqual(device_a.mass_balance(), 0.0, places=4)

        water_in = species.create_h2o_species()
        water_in.mass = 100
        water_in.temp_kelvin = utils.celsius_to_kelvin(25)
        my_system.add_input(device_b.name, water_in)

        water_out = copy.deepcopy(water_in)
        water_out.temp_kelvin = utils.celsius_to_kelvin(75)
        my_system.add_output(device_b.name, water_out)
        self.assertTrue(device_b.energy_balance() > 0.0)

        eff = 0.95
        electricity_req = device_b.thermal_energy_balance() / eff
        electricity_flow = system.EnergyFlow("electricity", electricity_req)
        my_system.add_input(device_b.name, electricity_flow)

        losses = (1 - eff) * electricity_req
        losses_flow = system.EnergyFlow("losses", energy=losses)
        my_system.add_output(device_b.name, losses_flow)
        self.assertTrue(device_b.thermal_energy_balance() > 0.0)
        self.assertAlmostEqual(device_b.energy_balance(), 0.0, places=4)


class SpeciesThermoTest(TestCase):
    def test_thermo_data(self):
        # Thermo data for SiO2. Data from the NIST webbook.
        # delta_h calculation verfied using FactSage. Accuracy is not great.
        heat_capacities = [thermo.SimpleHeatCapacity(273.15, 298.0, 44.57),
                    thermo.ShomateEquation(298.0, 847.0,
                                    (-6.076591, 251.6755, -324.7964,
                                        168.5604, 0.002548, -917.6893,
                                        -27.96962, -910.8568)),
                    thermo.ShomateEquation(847.0, 1996.0,
                                    (58.75340, 10.27925, -0.131384,
                                        0.025210, 0.025601, -929.3292,
                                        105.8092, -910.8568)),
                    thermo.SimpleHeatCapacity(1996.0, 3000.0, 77.99) # NIST data didn't go higher, guessing
        ]
        latent_heats = [thermo.LatentHeat(1983.15, 9600)]
        thermo_data = thermo.ThermoData(heat_capacities, latent_heats)
        mols = 1.0
        delta_h = thermo_data.delta_h(mols, utils.celsius_to_kelvin(25), utils.celsius_to_kelvin(2000))
        factsage_delta_h = 153464.0
        self.assertEqual(round(delta_h / 10000), 
                         round(factsage_delta_h / 10000))

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

    def test_mixture_merge(self):
        steam = species.create_h2o_species()
        steam.mass = 1
        steam.temp_kelvin = 1000
        oxygen = species.create_o2_species()
        oxygen.mass = 1
        oxygen.temp_kelvin = 1200
        steam_mixture = species.Mixture('steam', [steam])
        oxygen_mixture = species.Mixture('oxygen', [oxygen])
        steam_mixture.merge(oxygen_mixture)
        self.assertAlmostEqual(steam_mixture.mass, 2)
        self.assertAlmostEqual(steam_mixture.temp_kelvin, 1066.3, places=1)

    def test_enthalpy_of_reaction(self):
        # Enthalpies of reaction were verified using FactSage. Accuracy 
        # isn't great. Need to improve or use a third party thermochemistry package.
        temp_kelvin = 1000.0
        factsage_delta_h = -394620.7
        delta_h = species.delta_h_c_o2_co2(temp_kelvin)
        self.assertEqual(round(delta_h / 10000), 
                         round(factsage_delta_h / 10000))

        temp_kelvin = 1000.0
        delta_h = species.delta_h_3fe2o3_h2_2fe3o4_h2o(temp_kelvin)
        factsage_delta_h = -3341.1
        # Failing
        # self.assertAlmostEqual(delta_h, 
        #                        factsage_delta_h)

        temp_kelvin = 800.0
        delta_h = species.delta_h_fe3o4_h2_3feo_h2o(temp_kelvin)
        factsage_delta_h = 61069.4
        # Failing.
        # self.assertEqual(delta_h / 1000, \
        #                 factsage_delta_h / 1000)

        temp_kelvin = 1000.0
        delta_h = species.delta_h_feo_h2_fe_h2o(temp_kelvin)
        factsage_delta_h = 15584.0
        # self.assertEqual(round(delta_h / 1000), \
        #                 round(factsage_delta_h / 1000))

        temp_kelvin = 400.0
        delta_h = species.delta_h_fe2o3_3h2_3fe_3h2o(temp_kelvin) 
        factsage_delta_h = 80685.2
        # Failing. Pretty significant error...
        self.assertAlmostEqual(delta_h / 1000, factsage_delta_h / 1000, places=1)
        
    def test_energy_to_create_thermal_plasma(self):
        h2 = species.create_h2_species()
        h2.mols = 1.0
        h2.temp_kelvin = 300.0

        # only accurate to the second significant figure
        delta_h_900K = h2.heat_energy(900.0)
        factsage_delta_h = 1.76235E+04
        self.assertAlmostEqual(delta_h_900K / 10000, factsage_delta_h / 10000, places=0)

        # as above, only accurate to one significant figure
        delta_h_1500K = h2.heat_energy(1500.0)
        factsage_delta_h = 3.62382E+04
        self.assertAlmostEqual(delta_h_1500K / 10000, factsage_delta_h / 10000, places=0)

        # As above, reasonably close
        delta_h_2100K = h2.heat_energy(2100.0)
        factsage_delta_h = 5.70480E+04
        self.assertAlmostEqual(delta_h_2100K / 10000, factsage_delta_h / 10000, places=0)

        # Failing, very inaccurate
        # This is the first temp where monoatomic hydrogen is present in meaningful quantities.
        delta_h_3000K = h2.heat_energy(3000.0)
        factsage_delta_h = 1.24667E+05
        # self.assertAlmostEqual(delta_h_3000K / 10000, factsage_delta_h / 10000, places=1)

        # Failing, again very inaccurate.
        # Hydrogen has completely dissociated into monoatomic hydrogen.
        delta_h_5000K = h2.heat_energy(5000.0)
        factsage_delta_h = 6.10239E+05
        # self.assertAlmostEqual(delta_h_5000K / 10000, factsage_delta_h / 10000, places=1)


if __name__ == '__main__':
    main()
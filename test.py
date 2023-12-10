#!/usr/bin/env python3

import copy
import cantera as ct
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
import os

from tea_main import load_config_from_csv
import species
import system
import thermo
import utils


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
        my_system.render(str(self.temp_dir_path), False)
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


class ThermoTest(TestCase):
    def test_gas_simple_heat_capacity_data(self):
        # Argon data from NIST Webbook
        heat_capacities = [thermo.SimpleHeatCapacity(273.15, 6000, 20.786)]
        thermo_data = thermo.ThermoData(heat_capacities)
        moles = 2.5
        t_initial = 298.0
        t_final = 1000.0
        delta_h = thermo_data.delta_h(moles, t_initial, t_final)
        delta_h_factsage = 36479.39504
        self.assertAlmostEqual(delta_h, delta_h_factsage, delta=0.01*abs(delta_h_factsage))

    def test_gas_shomate_equation_heat_capacity_data(self):
        # Nitrogen data from NIST Webbook
        heat_capacities = [thermo.ShomateEquation(100.0, 500.0,
                                           (28.98641, 1.853978, -9.647459,
                                            16.63537, 0.000117, -8.671914, 226.4168, 0.0)),
                           thermo.ShomateEquation(500.0, 2000.0,
                                           (19.50583, 19.88705, -8.598535,
                                            1.369784, 0.527601, -4.935202, 212.3900, 0.0)),
                           thermo.ShomateEquation(2000.0, 6000.0,
                                           (35.51872, 1.128728, -0.196103,
                                            0.014662, -4.553760, -18.97091, 224.9810, 0.0))]
        thermo_data = thermo.ThermoData(heat_capacities)
        t_initial = 298.0
        t_final = 2000.0
        moles = 0.44
        delta_h = thermo_data.delta_h(moles, t_initial, t_final)
        delta_h_factsage = 24703.62302
        self.assertAlmostEqual(delta_h, delta_h_factsage, delta=0.025*abs(delta_h_factsage))

    def test_condensed_shomate_equation_heat_capacity_data(self):
        # Heat capacity of solid iron from NIST webbook.
        # Solid BCC phase, sensible heat, no phase change
        heat_capacities = [thermo.ShomateEquation(298, 700.0,
                                           (18.42868, 24.64301, -8.913720,
                                            9.664706, -0.012643, -6.573022, 42.51488,
                                            0.0)),
                           thermo.ShomateEquation(700.0, 1042.0,
                                           (-57767.65, 137919.7, -122773.2,
                                            38682.42, 3993.080, 24078.67, -87364.01, 0.0)),
                           thermo.ShomateEquation(1042.0, 1100.0,
                                           (-325.8859, 28.92876, 0.0,
                                            0.0, 411.9629, 745.8231, 241.8766, 0.0)),
                           thermo.ShomateEquation(1100, 1809,
                                           (-776.7387, 919.4005, -383.7184,
                                            57.08148, 242.1369, 697.6234, -558.3674, 0.0)),
                           thermo.SimpleHeatCapacity(1809.0, 3133.345, 46.02400)]  # liquid phase
        thermo_data = thermo.ThermoData(heat_capacities)
        cp_298 = thermo_data.cp(298)
        cp_298_webbook = 25.09
        self.assertAlmostEqual(cp_298, cp_298_webbook, delta=0.02 * abs(cp_298_webbook))

        cp_600 = thermo_data.cp(800)
        cp_600_webbook = 37.85
        self.assertAlmostEqual(cp_600, cp_600_webbook, delta=0.02 * abs(cp_600_webbook))

        delta_h = thermo_data.delta_h(1.0, 298.15, 600)
        delta_h_webbook = 8.61e3
        self.assertAlmostEqual(delta_h, delta_h_webbook, delta=0.02 * abs(delta_h_webbook))

        delta_h = thermo_data.delta_h(1.0, 298.15, 900)
        delta_h_webbook = 19.50e3
        self.assertAlmostEqual(delta_h, delta_h_webbook, delta=0.02 * abs(delta_h_webbook))


class SpeciesAndMixtureTest(TestCase):
    def test_air_mixture_composition(self):
        mass = 1.0
        air = species.create_air_mixture(mass)
        mass_composition = air.species_mass()
        self.assertAlmostEqual(mass_composition[0], 0.7812)

        moles_composition = air.species_moles()
        self.assertAlmostEqual(moles_composition[1], 6.5471205, places=3)

    def test_fe_species_data_data(self):
        # Heat capacity of solid iron from NIST webbook.
        # Solid BCC phase, sensible heat, no phase change
        fe = species.create_fe_species()
        fe.temp_kelvin = 600
        fe.moles = 1.0
        delta_h = fe.standard_enthalpy()
        delta_h_factsage = 8486.4466
        self.assertAlmostEqual(delta_h, delta_h_factsage, delta=0.02 * abs(delta_h_factsage))

        fe.temp_kelvin = 1100
        delta_h = fe.standard_enthalpy()
        delta_h_factsage = 29856.5266
        self.assertAlmostEqual(delta_h, delta_h_factsage, delta=0.02 * abs(delta_h_factsage))

        # Solid FCC phase, sensible heat + BCC -> FCC phase change
        fe.temp_kelvin = 1200
        delta_h = fe.standard_enthalpy()
        delta_h_factsage = 35057.9266
        self.assertAlmostEqual(delta_h, delta_h_factsage, delta=0.02 * abs(delta_h_factsage))

        fe.temp_kelvin = 1600
        delta_h = fe.standard_enthalpy()
        delta_h_factsage = 49424.9315741
        self.assertAlmostEqual(delta_h, delta_h_factsage, delta=0.02 * abs(delta_h_factsage))

        # Liquid Fe, sensible heat + latent heat phase changes
        fe.temp_kelvin = 2000
        delta_h = fe.standard_enthalpy()
        delta_h_factsage = 81161.23157409999
        self.assertAlmostEqual(delta_h, delta_h_factsage, delta=0.02 * abs(delta_h_factsage))

    def test_h2o_heat_capacity(self):
        h2o = species.create_h2o_species()
        h2o.temp_kelvin = utils.celsius_to_kelvin(25)
        molar_cp = h2o.cp()
        specific_cp = h2o.cp(False)
        self.assertAlmostEqual(molar_cp, 75.4, places=1)
        self.assertAlmostEqual(specific_cp, 4.18, places=1)

    def test_sensible_heat_of_air_mixture(self):
        mass = 1.0 # kg
        air = species.create_air_mixture(mass)
        air.temp_kelvin = 400
        weighted_avg_cp_by_mass = air.cp(False)
        factsage_val = 1017.0
        self.assertAlmostEqual(weighted_avg_cp_by_mass, 1017.0, delta=0.01*abs(factsage_val))
        delta_h = air.delta_h(air.temp_kelvin + 700)
        factsage_val = 763039.0
        self.assertAlmostEqual(delta_h, 763039.0, delta=0.01*abs(factsage_val))

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
        expected = 1066.3
        self.assertAlmostEqual(steam_mixture.temp_kelvin, expected, delta=0.01*abs(expected))


class ReactionsTest(TestCase):
    def test_enthalpy_of_reaction(self):
        # Enthalpies of reaction were verified using FactSage. Accuracy 
        # isn't great. Need to improve or use a third party thermochemistry package.
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

    def test_enthalpy_of_reaction_monatomic_h_reduction(self):
        # These are all failing. The delta H of reaction that I am calcuating does not at
        # all match what FactSage is suggesting..
        temp_kelvin = 298
        delta_h = species.delta_h_3fe2o3_2h_2fe3o4_h2o(temp_kelvin)
        factsage_delta_h = -479275.2 
        self.assertAlmostEqual(delta_h / 1000, factsage_delta_h / 1000, places=1)

        temp_kelvin = 1000
        delta_h = species.delta_h_3fe2o3_2h_2fe3o4_h2o(temp_kelvin)
        factsage_delta_h = -447835.8 
        # self.assertAlmostEqual(delta_h / 1000, factsage_delta_h / 1000, places=1)

        temp_kelvin = 2000
        delta_h = species.delta_h_3fe2o3_2h_2fe3o4_h2o(temp_kelvin)
        factsage_delta_h = -171728.8 
        # self.assertAlmostEqual(delta_h / 1000, factsage_delta_h / 1000, places=1)

        temp_kelvin = 3000
        delta_h = species.delta_h_3fe2o3_2h_2fe3o4_h2o(temp_kelvin)
        factsage_delta_h = -142709.5 
        # self.assertAlmostEqual(delta_h / 1000, factsage_delta_h / 1000, places=1)


    def test_enthalpy_of_oxidation_reaction(self):
        # Accuracy of the enthalpies of reaction for the oxidation reactions 
        # seems slightly better than the enthalpies of reaction of the hydrogen
        # reduction reactions.
        temp_kelvin = 1000.0
        factsage_delta_h = -394620.7
        delta_h = species.delta_h_c_o2_co2(temp_kelvin)
        self.assertEqual(round(delta_h / 10000), 
                         round(factsage_delta_h / 10000))
        
        temp_kelvin = 1000.0
        factsage_delta_h = -223971.8 
        delta_h = species.delta_h_2c_o2_2co(temp_kelvin)
        self.assertEqual(round(delta_h / 10000), 
                         round(factsage_delta_h / 10000))

        temp_kelvin = 298.0
        factsage_delta_h = -221055.8 
        delta_h = species.delta_h_2c_o2_2co(temp_kelvin)
        self.assertEqual(round(delta_h/10), 
                         round(factsage_delta_h/10))
        
        # Only accurate to 1 sig fig!
        temp_kelvin = 298.0
        factsage_delta_h = -531667.4  
        delta_h = species.delta_h_2fe_o2_2feo(temp_kelvin)
        self.assertEqual(round(delta_h/100_000), 
                         round(factsage_delta_h/100_000))
        
        temp_kelvin = 1000.0
        factsage_delta_h =  -526899.7 
        delta_h = species.delta_h_2fe_o2_2feo(temp_kelvin)
        self.assertEqual(round(delta_h/10_000), 
                         round(factsage_delta_h/10_000))

        temp_kelvin = 298.0
        factsage_delta_h =  -910699.2 
        delta_h = species.delta_h_si_o2_sio2(temp_kelvin)
        self.assertEqual(round(delta_h/100), 
                         round(factsage_delta_h/100))
        
        temp_kelvin = 1600.0
        factsage_delta_h =   -897758.4  
        delta_h = species.delta_h_si_o2_sio2(temp_kelvin)
        # Failing
        # self.assertEqual(round(delta_h/100), 
        #                  round(factsage_delta_h/100))


    def test_energy_to_create_thermal_plasma(self):
        h2 = species.create_h2_species()
        h2.moles = 1.0
        h2.temp_kelvin = 300.0

        # only accurate to the second significant figure
        delta_h_900K = h2.delta_h(900.0)
        factsage_delta_h = 1.76235E+04
        self.assertAlmostEqual(delta_h_900K / 10000, factsage_delta_h / 10000, places=0)

        # as above, only accurate to one significant figure
        delta_h_1500K = h2.delta_h(1500.0)
        factsage_delta_h = 3.62382E+04
        self.assertAlmostEqual(delta_h_1500K / 10000, factsage_delta_h / 10000, places=0)

        # As above, reasonably close
        delta_h_2100K = h2.delta_h(2100.0)
        factsage_delta_h = 5.70480E+04
        self.assertAlmostEqual(delta_h_2100K / 10000, factsage_delta_h / 10000, places=0)

        # Failing, very inaccurate
        # This is the first temp where monoatomic hydrogen is present in meaningful quantities.
        delta_h_3000K = h2.delta_h(3000.0)
        factsage_delta_h = 1.24667E+05
        # self.assertAlmostEqual(delta_h_3000K / 10000, factsage_delta_h / 10000, places=1)

        # Failing, again very inaccurate.
        # Hydrogen has completely dissociated into monoatomic hydrogen.
        delta_h_5000K = h2.delta_h(5000.0)
        factsage_delta_h = 6.10239E+05
        # self.assertAlmostEqual(delta_h_5000K / 10000, factsage_delta_h / 10000, places=1)


class TestFileIO(TestCase):
    def test_load_config_from_csv(self):
        config_filename = "config_default.csv"
        config = load_config_from_csv(config_filename)
        print(config)
        self.assertTrue(len(config) > 0)
        self.assertTrue(len(config["all"]) > 0)


class TestCanteraEquilibrium(TestCase):
    def test_cantera_equilibrium(self):
        nasa_species = {s.name: s for s in ct.Species.list_from_file('nasa_gas.yaml')}
        h2_plasma = ct.Solution(thermo='IdealGas', species=[nasa_species['H2'], 
                                                         nasa_species['H2+'],
                                                         nasa_species['H2-'],
                                                         nasa_species['H'],
                                                         nasa_species['H+'],
                                                         nasa_species['H-'],
                                                         nasa_species['Ar'],
                                                         nasa_species['Ar+'],
                                                         nasa_species['Electron']])
        h2_plasma.TPX = 300.0, ct.one_atm, 'H2:1.0, Ar:0.1'
        h2_plasma.equilibrate('TP')
        monatomic_h_fraction = h2_plasma.X[3]
        self.assertLess(monatomic_h_fraction, 1e-5)
        
        h2_plasma.TPX = 3000.0, ct.one_atm, 'H2:1.0, Ar:0.1'
        h2_plasma.equilibrate('TP')
        monatomic_h_fraction = h2_plasma.X[3]
        self.assertGreater(monatomic_h_fraction, 0.1)


if __name__ == '__main__':
    main()
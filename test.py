#!/usr/bin/env python3

from unittest import TestCase, main

import technoeconomics.utils

class UtilsTest(TestCase):
    def test_temp_conversion(self):
        self.assertEqual(technoeconomics.utils.celsius_to_kelvin(0), 273.15)
        self.assertEqual(technoeconomics.utils.kelvin_to_celsius(3000), 2726.85)

if __name__ == '__main__':
    main()
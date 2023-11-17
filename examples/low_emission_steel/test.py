#!/usr/bin/env python3

from unittest import TestCase, main

from tea_main import load_config_from_csv


class TestFileIO(TestCase):
    def test_load_config_from_csv(self):
        config_filename = "config_default.csv"
        config = load_config_from_csv(config_filename)
        print(config)
        self.assertTrue(len(config) > 0)
        self.assertTrue(len(config["all"]) > 0)
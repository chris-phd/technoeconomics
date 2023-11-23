#!/usr/bin/env python3

import copy
import csv
from enum import Enum
import numpy as np 
import os
import sys
from typing import Type, Dict, List, Optional, Callable
from mass_energy_flow import solve_mass_energy_flow
from plant_costs import PriceEntry


try:
    from technoeconomics.system import System
except ImportError:
    # If the technoeconomics package is not installed via pip,
    # add the package directory to the system path.
    examples_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    package_dir = os.path.dirname(examples_dir)
    sys.path.insert(0, package_dir)

    from technoeconomics.system import System


class ParameterType(Enum):
    Price = 1
    SystemVar = 2


class SensitivityIndicator:
    def __init__(self, indicator_name: str, system_name: str, parameter_name: str, parameter_type: ParameterType):
        """
        indicator_name: Name of the indicator: Elasticity, MinMax, SpiderPlot, etc.
        system_name: Name of the system that the indicator was calculated for
        parameter_name: Name of the parameter the indicator was calculated for
        """
        self.indiator_name: str = indicator_name
        self.system_name: str = system_name
        self.parameter_name: str = parameter_name
        self.parameter_type: ParameterType = parameter_type
        self._parameter_vals: np.ndarray = np.array([])
        self._result_vals: np.ndarray = np.array([])
        self._calculate: Optional[Callable] = None

    @property
    def parameter_vals(self) -> np.ndarray:
        return self._parameter_vals

    @parameter_vals.setter
    def parameter_vals(self, value: np.ndarray):
        self._parameter_vals = value

    @property
    def result_vals(self) -> np.ndarray:
        return self._result_vals

    @result_vals.setter
    def result_vals(self, value: np.ndarray):
        self._result_vals = value

    @property
    def calculate(self) -> Optional[Callable]:
        return self._calculate

    @calculate.setter
    def calculate(self, value: Optional[Callable]):
        self._calculate = value


def calculate_min_max_si(parameter_vals: np.ndarray, result_vals: np.ndarray) -> float:
    if len(parameter_vals) != 2 or len(result_vals) != 2:
        raise ValueError("MinMax sensitivity indicator requires two parameter values and two result values.")

    return (result_vals[1] - result_vals[0]) / result_vals[0]


def calculate_elasticity_si(parameter_vals: np.ndarray, result_vals: np.ndarray) -> float:
    if len(parameter_vals) != 2 or len(result_vals) != 2:
        raise ValueError("Elasticity sensitivity indicator requires two parameter values and two result values.")

    X = (parameter_vals[0] + parameter_vals[1]) * 0.5
    Y = (result_vals[0] + result_vals[1]) * 0.5

    return (result_vals[1] - result_vals[0]) / (parameter_vals[1] - parameter_vals[0]) * (X / Y)


def calculate_spider_plot_si(parameter_vals: np.ndarray, result_vals: np.ndarray) -> np.ndarray:
    if len(parameter_vals) != len(result_vals):
        raise ValueError("SpiderPlot sensitivity indicator requires the same number of parameter values and result values.")
    return result_vals
    


class SensitivityCase:
    def __init__(self, parameter_name: str, parameter_type: ParameterType):
        self.parameter_name = parameter_name
        self.parameter_type = parameter_type
        self._X_max = 0.0
        self._X_min = 0.0
        self._max_perc_change = 30.0
        self._num_perc_increments = 11
        self._elasticity_perc_change = 3.0
    
    @property
    def X_max(self) -> float:
        return self._X_max

    @X_max.setter
    def X_max(self, value: float):
        self._X_max = value

    @property
    def X_min(self) -> float:
        return self._X_min

    @X_min.setter
    def X_min(self, value: float):
        self._X_min = value

    @property
    def max_perc_change(self) -> float:
        return self._max_perc_change

    @max_perc_change.setter
    def max_perc_change(self, value: float):
        self._max_perc_change = value

    @property
    def num_perc_increments(self) -> int:
        return self._num_perc_increments

    @num_perc_increments.setter
    def num_perc_increments(self, value: int):
        self._num_perc_increments = value

    @property
    def elasticity_perc_change(self) -> float:
        return self._elasticity_perc_change

    @elasticity_perc_change.setter
    def elasticity_perc_change(self, value: float):
        self._elasticity_perc_change = value

    def create_sensitivity_indicators(self, system: System, prices: Dict[str, float]) -> List[SensitivityIndicator]:
        if self.parameter_type == ParameterType.Price:
            base_case_val = system.prices
        elif self.parameter_type == ParameterType.SystemVar:
            base_case_val = system.__dict__[self.parameter_name]
        else:
            raise ValueError("Parameter type not recognized. Cannot setup sensitivity analysis.")

        minMax = SensitivityIndicator("MinMax", system.name, self.parameter_name)
        minMax.parameter_vals = np.array([self.X_min, self.X_max])
        minMax.calculate = calculate_min_max_si

        elasticity = SensitivityIndicator("Elasticity", system.name, self.parameter_name)
        elasticity.parameter_vals = np.linspace(base_case_val * (100 - 0.5 * self.elasticity_perc_change) * 0.01, 
                                                base_case_val * (100 + 0.5 * self.elasticity_perc_change) * 0.01)
        elasticity.calculate = calculate_elasticity_si

        spiderPlot = SensitivityIndicator("SpiderPlot", system.name, self.parameter_name)
        spiderPlot.parameter_vals = np.linspace(base_case_val * (100 - self.max_perc_change) * 0.01, 
                                                base_case_val * (100 + self.max_perc_change) * 0.01, 
                                                self.num_perc_increments)
        spiderPlot.calculate = calculate_spider_plot_si


class SensitivityAnalysisRunner:
    def __init__(self, sensitivity_cases: List[Type[SensitivityCase]]):
        self.cases = sensitivity_cases

    @property
    def cases(self) -> List[Type[SensitivityCase]]:
        return self._cases
    
    def run(self, systems: List[System], prices: Dict[str, PriceEntry]):
        for case in self._cases:
            for s in systems:
                pass


def sensitivity_analysis_runner_from_csv(filename: str) -> Optional[Type[SensitivityAnalysisRunner]]:
    sensitivity_cases = []
    with open(filename, 'r') as file:
        try:
            csv_reader = csv.reader(file)
        except:
            return None
        next(csv_reader) # Skip the header row

        for row in csv_reader:
            parameter_name = row[0]
            parameter_type = ParameterType[row[1]]
            sensitivity_case = SensitivityCase(parameter_name, parameter_type)
            sensitivity_case.X_max = float(row[2])
            sensitivity_case.X_min = float(row[3])
            sensitivity_case.max_perc_change = float(row[4])
            sensitivity_case.num_perc_increments = int(row[5])
            sensitivity_case.elasticity_perc_change = float(row[6])
            sensitivity_cases.append(sensitivity_case)

    runner = SensitivityAnalysisRunner(sensitivity_cases)
    return runner
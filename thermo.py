#!/usr/bin/env python3

import cantera as ct
import copy
import math
from typing import List, Optional, Union


class ShomateEquation:
    """
    The Shomate equation.
    Used to calculate the molar heat capacity, enthalpy and entropy.
    Units follow the convention of the NIST database.
    """
    def __init__(self, min_kelvin: float, max_kelvin: float, coeffs: tuple):
        assert min_kelvin < max_kelvin
        assert len(coeffs) == 8 # coeffs: (a, b, c, d, e, f, g, h)
        self.min_kelvin = min_kelvin
        self.max_kelvin = max_kelvin
        self.coeffs = coeffs

    def __repr__(self):
        return f"ShomateEquation({self.min_kelvin}-{self.max_kelvin}K, A={self.coeffs[0]}, B={self.coeffs[1]}, " \
               f"C={self.coeffs[2]}, D={self.coeffs[3]}, E={self.coeffs[4]}, F={self.coeffs[5]} "\
               f"G={self.coeffs[6]}, H={self.coeffs[7]})"

    def delta_h(self, moles: float, t_initial: float, t_final: float) -> float:
        """
        The change in enthalpy [J]
        """
        if not (self.min_kelvin <= t_initial <= self.max_kelvin) or \
            not (self.min_kelvin <= t_final <= self.max_kelvin):
            raise Exception("ShomateEquation::delta_h: temperatures must be within the range of the heat capacity")
        t_initial /= 1000
        t_final /= 1000
        energy_kJ = moles * (self.coeffs[0] * (t_final - t_initial)
                       + self.coeffs[1] / 2 * (t_final**2 - t_initial**2)
                       + self.coeffs[2] / 3 * (t_final**3 - t_initial**3)
                       + self.coeffs[3] / 4 * (t_final**4 - t_initial**4)
                       - self.coeffs[4] * (t_final**-1 - t_initial**-1))
        return energy_kJ * 1000

    def cp(self, t):
        """
        The heat capacity [J / mol K]
        """
        if not (self.min_kelvin <= t <= self.max_kelvin):
            raise Exception("ShomateEquation::cp: temperatures must be within the range of the heat capacity")
        t /= 1000
        val = self.coeffs[0]  + self.coeffs[1]*t  + self.coeffs[2]*t**2 + self.coeffs[3]*t**3 + self.coeffs[4]*t**(-2)
        return val


class SimpleHeatCapacity:
    """
    Heat capacity at constant pressure stored as a constant value.
    """
    def __init__(self, min_kelvin: float, max_kelvin: float, cp: float):
        """
        cp: heat capacity at constant pressure in J/mol K
        """
        assert min_kelvin < max_kelvin
        self.min_kelvin = min_kelvin
        self.max_kelvin = max_kelvin
        self._cp = cp

    def __repr__(self):
        return f"SimpleHeatCapacity({self.min_kelvin}-{self.max_kelvin}K, cp={self.cp((self.min_kelvin + self.min_kelvin*0.5))})"
    
    def delta_h(self, moles: float, t_initial: float, t_final: float) -> float:
        """
        The change in enthalpy [J]
        """
        if not (self.min_kelvin <= t_initial <= self.max_kelvin) or \
            not (self.min_kelvin <= t_final <= self.max_kelvin):
            raise Exception("SimpleHeatCapacity::delta_h: temperatures must be within the range of the heat capacity")
        return moles * self._cp * (t_final - t_initial)

    def cp(self, t):
        """
        The heat capacity [J / mol K]
        """
        if not (self.min_kelvin <= t <= self.max_kelvin):
            raise Exception("SimpleHeatCapacity::cp: temperatures must be within the range of the heat capacity")
        return self._cp


class CanteraSolution:
    """
    Heat capacity data provided by cantera.
    """
    def __init__(self, solution: ct.Solution):
        solution.TP = 300, ct.one_atm
        self._quantity = ct.Quantity(solution, moles=1.0)
        self.min_kelvin = self._quantity.min_temp
        self.max_kelvin = self._quantity.max_temp

    def __repr__(self):
        return f"CanteraSolution({self._solution.species_names}, {self.min_kelvin}-{self.max_kelvin}K)"

    def delta_h(self, moles: float, t_initial: float, t_final: float) -> float:
        """
        The change in enthalpy [J]
        """
        if not (self.min_kelvin <= t_initial <= self.max_kelvin) or \
                not (self.min_kelvin <= t_final <= self.max_kelvin):
            if 298 < t_initial <= 300.0 and 298 < self.min_kelvin <= 300.0:
                # Special case for h2 plasma, check if the requested temp is close enough to the allowable range
                t_initial = self.min_kelvin
            elif 298 < t_final <= 300.0 and 298 < self.min_kelvin <= 300.0:
                # As above, special case
                t_final = self.min_kelvin
            else:
                raise Exception("CanteraSolution::delta_h: temperatures must be within the range of the heat capacity")

        self._quantity.TP = t_final, ct.one_atm
        self._quantity.equilibrate('TP')
        h_final = moles * self._quantity.moles * self._quantity.enthalpy_mole * 0.001

        self._quantity.TP = t_initial, ct.one_atm
        self._quantity.equilibrate('TP')
        h_initial = moles * self._quantity.moles * self._quantity.enthalpy_mole * 0.001

        return h_final - h_initial

    def cp(self, t) -> float:
        """
        The heat capacity [J / mol K]
        """
        if not (self.min_kelvin <= t <= self.max_kelvin):
            if 298 < t <= 300.0 and 298 < self.min_kelvin <= 300.0:
                # Special case for h2 plasma, check if the requested temp is close enough to the minimum
                t = self.min_kelvin
            else:
                raise Exception("CanteraSolution::cp: temperatures must be within the range of the heat capacity")
        self._quantity.TP = t, ct.one_atm
        self._quantity.equilibrate('TP')
        return self._quantity.cp_mole * self._quantity.moles * 0.001


class LatentHeat:
    """
    Latent heat required for a phase change. Typically melting (latent heat of fusion)
    or boiling (latent heat of vaporisation).
    """
    def __init__(self, temp_kelvin: float, latent_heat: float):
        """
        Latent heat in J/mol
        """
        self.temp_kelvin = temp_kelvin
        self.latent_heat = latent_heat

    def __repr__(self):
        return f"LatentHeat({self.temp_kelvin} K, latent_heat={self.latent_heat} J/mol)"
    
    def delta_h(self, moles: float):
        return moles * self.latent_heat


class ThermoData:
    """
    Contains a list HeatCapacity instances. Each must cover a different range,
    and be continuous (no gaps between the thermo data ranges).
    """
    def __init__(self, heat_capacities: List[Union[ShomateEquation, SimpleHeatCapacity, CanteraSolution]],
                 latent_heats: Optional[List[LatentHeat]] = None):
        """
        Args:
            heat_capacities: a list of heat capacity classes with non-overlapping temperature ranges.
                The provided list is NOT copied.
            latent_heats: a list of latent heat data for phase changes. Must be within the temperature range
                of the heat capacities. The provided list is NOT copied.
        """

        # Validate the input types
        for heat_capacity in heat_capacities:
            if not isinstance(heat_capacity, (ShomateEquation, SimpleHeatCapacity, CanteraSolution)):
                raise Exception("ThermoData must be initialised with a list of ShomateEquation, SimpleHeatCapacity or CanteraSolution instances")

        if latent_heats:
            for latent_heat in latent_heats:
                if not isinstance(latent_heat, LatentHeat):
                    raise Exception("ThermoData must be initialised with a list of LatentHeat instances")

        # Ensure non-overlapping continous heat capacity range
        self.heat_capacities = heat_capacities
        self.heat_capacities.sort(key=lambda x: x.min_kelvin)
        for i in range(len(self.heat_capacities) - 1):
            if not math.isclose(self.heat_capacities[i].max_kelvin,
                                 self.heat_capacities[i + 1].min_kelvin):
                raise Exception("Non-continuous temperature ranges in ThermoData (gap or overlap detected)")
            
        self.min_kelvin = self.heat_capacities[0].min_kelvin
        self.max_kelvin = self.heat_capacities[-1].max_kelvin

        if latent_heats:
            # Ensure the latent heat values lie within the heat capacity range
            self.latent_heats = latent_heats
            self.latent_heats.sort(key=lambda x: x.temp_kelvin)
            for latent_heat in self.latent_heats:
                if not (self.min_kelvin <= latent_heat.temp_kelvin <= self.max_kelvin):
                    raise Exception("Latent heat temperature out of range")
        else:
            self.latent_heats = []
            
    def __repr__(self):
        return f"ThermoData({self.heat_capacities}, {self.latent_heats})"
    
    def delta_h(self, moles: float, t_initial: float, t_final: float) -> float:
        """
        The change in enthalpy [J]
        """
        if not (self.min_kelvin <= t_initial <= self.max_kelvin) or \
            not (self.min_kelvin <= t_final <= self.max_kelvin):
            if 298 < t_initial <= 300.0 and 298 < self.min_kelvin <= 300.0:
                # Special case for h2 plasma, check if the requested temp is close enough to the allowable range
                t_initial = self.min_kelvin
            elif 298 < t_final <= 300.0 and 298 < self.min_kelvin <= 300.0:
                # As above, special case
                t_final = self.min_kelvin
            else:
                s = f"ThermoData::delta_h: temperatures must be within the range of the heat capacity ({self.min_kelvin}K - {self.max_kelvin}K)"
                s += f" t_initial={t_initial}K, t_final={t_final}K"
                raise Exception(s)
        
        if math.isclose(moles, 0.0):
            return 0.0

        # ensure initial temp is always less than final, then flip if needed
        # keeps the maths simple
        flip_result = t_final < t_initial
        if flip_result:
            t_initial, t_final = t_final, t_initial

        delta_h = 0

        # Add the contributions from the latent heats
        for latent_heat in self.latent_heats:
            if t_initial <= latent_heat.temp_kelvin < t_final:
                delta_h += latent_heat.delta_h(moles)

        # Find the heat capacity that covers the initial temperature
        for heat_capacity in self.heat_capacities:
            if heat_capacity.min_kelvin <= t_initial <= heat_capacity.max_kelvin:
                if heat_capacity.min_kelvin <= t_final <= heat_capacity.max_kelvin:
                    # Result is entirlly within one heat capacity range
                    delta_h += heat_capacity.delta_h(moles, t_initial, t_final)
                    break
                else:
                    # Result spans multiple heat capacity ranges
                    delta_h += heat_capacity.delta_h(moles, t_initial, heat_capacity.max_kelvin)
                    t_initial = heat_capacity.max_kelvin              

        if flip_result:
            delta_h *= -1
        return delta_h

    def cp(self, t_kelvin) -> float:
        """
        The heat capacity [J / mol K]
        """
        for heat_capacity in self.heat_capacities:
            if heat_capacity.min_kelvin <= t_kelvin <= heat_capacity.max_kelvin:
                return heat_capacity.cp(t_kelvin)
        raise Exception(f"ThermoData::cp: No heat capacity data available at temp {t_kelvin}")
#!/usr/bin/env python3

def celsius_to_kelvin(temp):
    kelvin = temp + 273.15
    if kelvin < 0:
        raise ValueError("Temperature in Kelvin cannot be less than 0")
    return kelvin


def kelvin_to_celsius(temp):
    if temp < 0:
        raise ValueError("Temperature in Kelvin cannot be less than 0")
    return temp - 273.15


def differentiate_second_order_central(f, x, h):
    """
    Differentiate a function f(x) using the second order central difference method.
    """
    return (f(x + h) - 2 * f(x) + f(x - h)) / h**2

#!/usr/bin/env python3

from typing import List

import species

def delta_h_reaction(reactants: List[species.Species], products: List[species.Species], t_kelvin: float) -> float:
    """
    Args:
        reactants: list of reactants, with the required moles set
        products: list of products, with the required moles set
        t_kelvinn: The temperature of the reaction [K]
    Returns:
        float: the enthalpy of reaction [J]
    """
    for q in reactants + products:
        q.T = t_kelvin
    reactant_enthalpy = 0.0
    for reactant in reactants:
        reactant_enthalpy += reactant.moles * reactant.delta_h_formation
        reactant_enthalpy += reactant.enthalpy + reactant.latent_heat
    product_enthalpy = 0.0
    for product in products:
        product_enthalpy += product.moles * product.delta_h_formation
        product_enthalpy += product.enthalpy + product.latent_heat
    return product_enthalpy - reactant_enthalpy


def delta_h_2h2_o2_to_2h2o(t_kelvin: float = 298.15) -> float:
    """
    Returns the reaction enthalpy of the reaction [J]:
    2 H2(g) + O2(g) -> 2 H2O(g)
    """
    h2 = species.create_h2_mixture().species[0]
    h2.moles = 2
    o2 = species.create_o2_mixture().species[0]
    o2.moles = 1
    h2o = species.create_h2o_g_mixture().species[0]
    h2o.moles = 2
    return delta_h_reaction([h2, o2], [h2o], t_kelvin)


def delta_h_3fe2o3_h2_to_2fe3o4_h2o(t_kelvin: float = 298.15) -> float:
    """
    Returns the reaction enthalpy of the reaction [J]:
    3 Fe2O3(s) + H2(g) -> 2 Fe3O4(s) + H2O(g)
    """
    fe2o3 = species.create_fe2o3_s_mixture().species[0]
    fe2o3.moles = 3
    h2 = species.create_h2_mixture().species[0]
    h2.moles = 1
    fe3o4 = species.create_fe3o4_s_mixture().species[0]
    fe3o4.moles = 2
    h2o = species.create_h2o_g_mixture().species[0]
    h2o.moles = 1
    return delta_h_reaction([fe2o3, h2], [fe3o4, h2o], t_kelvin)

def delta_h_fe3o4_h2_to_3feo_h2o(t_kelvin: float = 298.15) -> float:
    """
    Returns the reaction enthalpy of the reaction [J]:
    Fe3O4(s) + H2(g) -> 3 FeO(s) + H2O(g)
    """
    fe3o4 = species.create_fe3o4_s_mixture().species[0]
    fe3o4.moles = 1
    h2 = species.create_h2_mixture().species[0]
    h2.moles = 1
    feo = species.create_feo_s_mixture().species[0]
    feo.moles = 3
    h2o = species.create_h2o_g_mixture().species[0]
    h2o.moles = 1
    return delta_h_reaction([fe3o4, h2], [feo, h2o], t_kelvin)

def delta_h_3fe2o3_h2_to_2fe3o4_h2o_factsage_973k() -> float:
    """
    Returns the reaction enthalpy [J] of the reaction at 700C, as calculated by FactSage:
    3 Fe2O3(s) + H2(g) -> 2 Fe3O4(s) + H2O(g)
    """
    return -2166.2

def delta_h_fe3o4_h2_to_3feo_h2o_factsage_973k() -> float:
    """
    Returns the reaction enthalpy [J] of the reaction at 700C, as calculated by FactSage:
    3 Fe2O3(s) + H2(g) -> 2 Fe3O4(s) + H2O(g)
    """
    return 52157.0

#!/usr/bin/env python3

from typing import List

import species

def delta_h_reaction(reactants: List[species.Species], products: List[species.Species], T: float) -> float:
    """
    Args:
        reactants: list of reactants, with the required moles set
        products: list of products, with the required moles set
        T: The temperature of the reaction [K]
    Returns:
        float: the enthalpy of reaction [J]
    """
    for q in reactants + products:
        q.T = T
    reactant_enthalpy = 0.0
    for reactant in reactants:
        reactant_enthalpy += reactant.moles * reactant.delta_h_formation
        reactant_enthalpy += reactant.enthalpy + reactant.latent_heat
    product_enthalpy = 0.0
    for product in products:
        product_enthalpy += product.moles * product.delta_h_formation
        product_enthalpy += product.enthalpy + reactant.latent_heat
    return product_enthalpy - reactant_enthalpy

def enthalpy_2h2_o2_to_2h2o(T: float = 298.15) -> float:
    """
    Returns the reaction enthalpy of the reaction:
    2 H2(g) + O2(g) => 2 H2O(g)

    Args:
        T (float): Temperature [K]
    """
    h2 = species.create_h2_mixture().species[0]
    h2.moles = 2
    o2 = species.create_o2_mixture().species[0]
    o2.moles = 1
    h2o = species.create_h2o_g_mixture().species[0]
    h2o.moles = 2
    return delta_h_reaction([h2, o2], [h2o], T)

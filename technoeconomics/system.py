#!/usr/bin/env python3

import graphviz
from typing import Optional, Type, Union, Dict

from technoeconomics.species import Species, Mixture
from technoeconomics.utils import celsius_to_kelvin

class EnergyFlow:
    """
    A flow of energy, typically electricity.
    energy is stored in joules
    """
    def __init__(self, name: str, energy: float = 0.0):
        self._name = name
        self._energy = energy

    def __repr__(self):
        return f"EnergyFlow({self._name}, {self._energy} J)"

    @property
    def name(self):
        return self._name

    @property
    def energy(self):
        return self._energy

    @energy.setter
    def energy(self, value):
        self._energy = value

    def set(self, other_energy_flow):
        self._name = other_energy_flow._name
        self._energy = other_energy_flow._energy


class Device:
    """
    The base class of a device. A device has a set of inputs and 
    outputs, representing mass or energy flow. A device may also 
    have a set of state variables.
    """

    def __init__(self, name: str):
        self._name = name
        self._inputs = {}
        self._outputs = {}

    def __repr__(self):
        s = f"Device({self.name}\n"
        s += f"    thermal_energy_balance (excl. losses) = {self.thermal_energy_balance():.2e}\n"
        s += f"    total_energy_balance (out - in) = {self.energy_balance():.2e}\n"
        s += f"    mass_balance (out - in) = {self.mass_balance():.2f} )"
        return s

    def report_flow(self):
        s = f"Device {self._name}:\n"
        s += "  Inputs: "
        for flow in self._inputs.values():
            s += f"{flow}, "
        s += "\n"
        s += "  Outputs: "
        for flow in self._outputs.values():
            s += f"{flow}, "
        return s

    @property
    def name(self):
        return self._name
    
    @property
    def inputs(self):
        return self._inputs
    
    @property
    def outputs(self):
        return self._outputs

    def add_input(self, flow: Union[Species, Mixture, EnergyFlow]):
        if flow.name in self._inputs:
            raise ValueError(f"Input flow with name {flow.name} already exists")
        self._inputs[flow.name] = flow
    
    def add_output(self, flow: Union[Species, Mixture, EnergyFlow]):
        if flow.name in self._outputs:
            raise ValueError(f"Output flow with name {flow.name} already exists")
        self._outputs[flow.name] = flow

    def outputs_containing_name(self, name: str):
        """
        Returns a list of the output flow names the given string.
        """
        return [key for key in self._outputs.keys() if name in key]
    
    def first_output_containing_name(self, name: str):
        flow_names = self.outputs_containing_name(name)
        if len(flow_names) == 0:
            raise ValueError(f"No output flows containing {name} found")
        elif len(flow_names) > 1:
            raise ValueError(f"Multiple output flows containing {name} found") # tmp to find where this is happening
        return self._outputs[flow_names[0]]

    def inputs_containing_name(self, name: str):
        """
        Returns a list of the input flow names the given string.
        """
        return [key for key in self._inputs.keys() if name in key]

    def first_input_containing_name(self, name: str):
        flow_names = self.inputs_containing_name(name)
        if len(flow_names) == 0:
            raise ValueError(f"No input flows containing {name} found")
        elif len(flow_names) > 1:
            raise ValueError(f"Multiple input flows containing {name} found")
        return self._inputs[flow_names[0]]

    def thermal_energy_balance(self):
        ref_temp = celsius_to_kelvin(25)

        final_thermal_energy = 0.0
        for flow in self.outputs.values():
            if not (isinstance(flow, Species) or isinstance(flow, Mixture)):
                continue
            # negative becuase heat_energy will calc energy required to cool
            # to the ref temp
            final_thermal_energy -= flow.heat_energy(ref_temp)

        initial_thermal_energy = 0.0
        for flow in self.inputs.values():
            if not (isinstance(flow, Species) or isinstance(flow, Mixture)):
                continue
            initial_thermal_energy -= flow.heat_energy(ref_temp)
        
        return final_thermal_energy - initial_thermal_energy

    def energy_balance(self):
        energy_out = 0.0
        for flow in self._outputs.values():
            if not isinstance(flow, EnergyFlow):
                continue
            energy_out += flow.energy

        energy_in = 0.0
        for flow in self._inputs.values():
            if not isinstance(flow, EnergyFlow):
                continue
            energy_in += flow.energy
        return self.thermal_energy_balance() + energy_out - energy_in

    def mass_balance(self):
        mass_out = 0.0
        for flow in self._outputs.values():
            if not (isinstance(flow, Species) or isinstance(flow, Mixture)):
                continue
            mass_out += flow.mass

        mass_in = 0.0
        for flow in self._inputs.values():
            if not (isinstance(flow, Species) or isinstance(flow, Mixture)):
                continue
            mass_in += flow.mass
        return mass_out - mass_in
    
    def electrical_energy_in(self):
        electricity_in = 0.0
        for flow in self._inputs.values():
            if not isinstance(flow, EnergyFlow):
                continue
            if 'electric' in flow.name:
                electricity_in += flow.energy
        return electricity_in    


class System:
    """
    A system is a collection of devices. It comprises everything 
    within the system boundary of the technoeconomic analysis.
    """
    _input_node_suffix = " __dummyinput__"
    _output_node_suffix = " __dummyoutput__"

    def __init__(self, name: str):
        self._name = name
        self._graph_dot = graphviz.Digraph()
        self._devices = {}
        self._flows = {}
        self._system_vars = {}

    def __repr__(self):
        s = f"System({self.name}"
        for device in self._devices.values():
            if device.name.endswith(self._input_node_suffix) or \
                device.name.endswith(self._output_node_suffix):
                continue
            s += f"\n  {device} )"
        return s

    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, value):
        self._name = value

    @property
    def devices(self):
        return self._devices
    
    @property
    def system_vars(self):
        return self._system_vars

    def add_device(self, device: Type[Device]):
        if device.name in self._devices:
            raise ValueError(f"Device with name {device.name} already exists")
        self._devices[device.name] = device

        if self._input_node_suffix in device.name or self._output_node_suffix in device.name:
            self._graph_dot.node(device.name, "", shape="none", height="1.5", width="1.5")
        else:
            self._graph_dot.node(device.name)

    def remove_device(self, device_name: str):
        self._devices.pop(device_name, None)
        self._graph_dot.remove_node(device_name + self._input_node_suffix)
        self._graph_dot.remove_node(device_name + self._output_node_suffix)
        self._graph_dot.remove_node(device_name)
        self._graph_dot.remove_node(device_name + self._input_node_suffix)
        self._graph_dot.remove_node(device_name + self._output_node_suffix)

    def add_flow(self, from_device_name: Optional[str], to_device_name: Optional[str], flow: Union[Species, Mixture, EnergyFlow]):
        if from_device_name is None and to_device_name is None:
            raise ValueError("Cannot add flow without a source or destination")

        if from_device_name is None:
            from_device_name = to_device_name + self._input_node_suffix
            if from_device_name not in self._devices:
                self.add_device(Device(from_device_name))
        elif to_device_name is None:
            to_device_name = from_device_name + self._output_node_suffix
            if to_device_name not in self._devices:
                self.add_device(Device(to_device_name))

        if from_device_name not in self._devices:
            raise ValueError(f"Cannot add flow to {from_device_name}. Device does not exist.")
        if to_device_name not in self._devices:
            raise ValueError(f"Cannot add flow to {to_device_name}. Device does not exist.")

        if (from_device_name, to_device_name, flow.name) in self._flows:
            # Maybe add support to add to the existing flows. Difficult to do at the moment
            # since it's not clear the flow types will support the __add__ operator.
            raise Exception(f"{flow.name} flow between devices {from_device_name} and {to_device_name} already exists.")
        else:
            # Add to the graph viz object
            color = "black"
            if "losses" in flow.name:
                color = "red"
            elif "electricity" in flow.name:
                color = "gold"
            self._graph_dot.edge(from_device_name, to_device_name, flow.name, color=color)

            # Add to the internal data structure. The system holds the master copy.
            # The flow here should be passed by reference, so changes to one copy will
            # be reflected in the other.
            self._flows[(from_device_name, to_device_name, flow.name)] = flow
            self._devices[to_device_name].add_input(flow)
            self._devices[from_device_name].add_output(flow)
        
    def add_input(self, device: Type[Device], flow: Union[Species, Mixture, EnergyFlow]):
        self.add_flow(None, device, flow)

    def add_output(self, device: Type[Device], flow: Union[Species, Mixture, EnergyFlow]):
        self.add_flow(device, None, flow)

    def get_flow(self, from_device_name: str, to_device_name: str, flow_name: str):
        flow_key = (from_device_name, to_device_name, flow_name)
        if flow_key not in self._flows:
            raise ValueError(f"{flow_name} flow between devices {from_device_name} and {to_device_name} does not exist")
        return self._flows[flow_key]

    def get_input(self, to_device_name: str, flow_name: str):
        from_device_name = to_device_name + self._input_node_suffix
        return self.get_flow(from_device_name, to_device_name, flow_name)
    
    def get_output(self, from_device_name: str, flow_name: str):
        to_device_name = from_device_name + self._output_node_suffix
        return self.get_flow(from_device_name, to_device_name, flow_name)

    def render(self, view=True, output_directory: Optional[str]=None):
        if output_directory is None:
            # File still created? TODO: Fix this, don't want anything on disk 
            # after exit.
            self._graph_dot.render(view=view)
        else:
            filename = self._name.replace(" ", "_")
            self._graph_dot.render(directory=output_directory, view=view, filename=filename)

    def devices_containing_name(self, name: str):
        """
        Returns a list of the device names containing the given string.
        """
        device_names = []
        for key in self._devices.keys():
            if name not in key:
                continue
            if self._input_node_suffix in key or self._output_node_suffix in key:
                continue
            device_names.append(key)

        return device_names
    
    def system_inputs(self, ignore_flows_named=[], separate_mixtures_named=[], mass_flow_only=False) -> Dict[str, float]:
        """
        Returns the mass of each input (kg) or energy (J) rather than the 
        species or mixture or energyflow object.
        """
        inputs = {}
        for device_name in self._devices.keys():
            if self._input_node_suffix not in device_name:
                continue
            # Note; outputs of the dummy input devices are system inputs
            for flow in self._devices[device_name].outputs.values():
                if isinstance(flow, Species) or isinstance(flow, Mixture):
                    if flow.name in ignore_flows_named:
                        continue

                    if flow.name in separate_mixtures_named and isinstance(flow, Mixture):
                        for species in flow._species:
                            if species.name not in inputs:
                                inputs[species.name] = 0.0
                            inputs[species.name] += species.mass
                        continue

                    if flow.name not in inputs:
                        inputs[flow.name] = 0.0
                    inputs[flow.name] += flow.mass
                
                if not mass_flow_only and isinstance(flow, EnergyFlow):
                    if flow.name in ignore_flows_named:
                        continue

                    if flow.name not in inputs:
                        inputs[flow.name] = 0.0
                    inputs[flow.name] += flow.energy

        return inputs
                    

    def system_outputs(self, ignore_flows_named=[], separate_mixtures_named=[], mass_flow_only=False) -> Dict[str, float]:
        """
        Returns the mass of each output (kg) or energy (J) rather than the 
        species or mixture or energyflow object.
        """
        outputs = {}
        for device_name in self._devices.keys():
            if self._output_node_suffix not in device_name:
                continue
            # Note; inputs of the dummy output devices are system outputs
            for flow in self._devices[device_name].inputs.values():
                if isinstance(flow, Species) or isinstance(flow, Mixture):
                    if flow.name in ignore_flows_named:
                        continue

                    if flow.name in separate_mixtures_named and isinstance(flow, Mixture):
                        for species in flow._species:
                            if species.name not in outputs:
                                outputs[species.name] = 0.0
                            outputs[species.name] += species.mass
                        continue

                    if flow.name not in outputs:
                        outputs[flow.name] = 0.0
                    outputs[flow.name] += flow.mass

                if not mass_flow_only and isinstance(flow, EnergyFlow):
                    if flow.name in ignore_flows_named:
                        continue

                    if flow.name not in outputs:
                        outputs[flow.name] = 0.0
                    outputs[flow.name] += flow.energy

        return outputs
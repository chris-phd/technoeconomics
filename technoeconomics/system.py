#!/usr/bin/env python3

import copy
from enum import Enum
import graphviz
from typing import Optional, Type


class Flow:
    """
    A mass or energy flow between two devices, or an input/output
    to/from the system.
    """
    def __init__(self, name: str, mass = None, energy = None):
        self._name = name
        self._mass = mass
        self._energy = energy

    @property
    def name(self):
        return self._name

    @property
    def mass(self):
        return self._mass
    
    @mass.setter
    def mass(self, value):
        self._mass = value

    @property
    def energy(self):
        return self._energy
    
    @energy.setter
    def energy(self, value):
        self._energy = value


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
        return f"Device({self._name})"

    def report_flow(self):
        s = f"Device {self._name}:\n"
        s += "  Inputs: "
        for flow in self._inputs.values():
            s += f"{flow.name}, "
        s += "\n"
        s += "  Outputs: "
        for flow in self._outputs.values():
            s += f"{flow.name}, "
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

    def add_input(self, flow: Type[Flow]):
        self._inputs[flow.name] = flow
    
    def add_output(self, flow: Type[Flow]):
        self._outputs[flow.name] = flow


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

    def add_flow(self, from_device_name: Optional[str], to_device_name: Optional[str], flow: Type[Flow]):
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
        
    def add_input(self, device: Type[Device], flow: Type[Flow]):
        self.add_flow(None, device, flow)

    def add_output(self, device: Type[Flow], flow: Type[Flow]):
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
        if output_directory:
            filename = self._name.replace(" ", "_")
            self._graph_dot.render(directory=output_directory, view=view, filename=filename)
        else:
            self._graph_dot.render(view=view)